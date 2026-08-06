"""Sprint 25b.5x — Build Image manual dispatch explicit repository identity.

Root cause: workflow_dispatch resolution ran ``gh run list`` before
``actions/checkout`` without ``GH_REPO`` / ``--repo``. GitHub CLI then
attempted local ``.git`` discovery and failed with:

  failed to determine base repo: failed to run git:
  fatal: not a git repository (or any of the parent directories): .git

Fix: bind ``GH_REPO: ${{ github.repository }}`` on the resolve step and pass
``--repo "$GH_REPO"`` to ``gh run list``. Automatic ``workflow_run`` continues
to use event-context CI authority and does not call ``gh run list``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
BUILD_WF = WORKFLOWS / "build-image.yml"
CI_WF = WORKFLOWS / "ci.yml"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_SHA = "fedcba9876543210fedcba9876543210fedcba98"
SUCCESS_RUN_ID = "31019003439"
FAILED_RUN_ID = "99900011122"
IN_PROGRESS_RUN_ID = "88800011122"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _on_block(workflow: dict) -> dict:
    # PyYAML 1.1 treats bare `on` as boolean True.
    on_block = workflow.get("on", workflow.get(True))
    assert isinstance(on_block, dict)
    return on_block


def _load_build_workflow() -> dict:
    data = yaml.safe_load(_read(BUILD_WF))
    assert isinstance(data, dict)
    return data


def _publish_steps(workflow: dict) -> list[dict]:
    jobs = workflow.get("jobs") or {}
    publish = jobs.get("publish")
    assert isinstance(publish, dict), "publish job missing"
    steps = publish.get("steps") or []
    assert isinstance(steps, list) and steps
    return steps


def _step_by_id(steps: list[dict], step_id: str) -> dict:
    for step in steps:
        if step.get("id") == step_id:
            return step
    raise AssertionError(f"step id={step_id!r} not found")


def _checkout_index(steps: list[dict]) -> int:
    for idx, step in enumerate(steps):
        if "actions/checkout" in (step.get("uses") or ""):
            return idx
    raise AssertionError("actions/checkout step not found")


def _resolve_step(workflow: dict | None = None) -> dict:
    steps = _publish_steps(workflow or _load_build_workflow())
    return _step_by_id(steps, "resolve")


def _dispatch_script_fragment(run_script: str) -> str:
    """Return the else-branch body that performs manual CI lookup."""
    # workflow_run path is the if-true arm; dispatch is the else arm.
    match = re.search(
        r'if \[ "\$\{\{ github\.event_name \}\}" = "workflow_run" \]; then\n'
        r"(.*?)\n"
        r"\s*else\n"
        r"(.*?)\n"
        r"\s*fi\n"
        r'\s*if ! \[\[ "\$SHA"',
        run_script,
        re.DOTALL,
    )
    assert match is not None, "could not parse workflow_run / dispatch branches"
    return match.group(2)


def _workflow_run_script_fragment(run_script: str) -> str:
    match = re.search(
        r'if \[ "\$\{\{ github\.event_name \}\}" = "workflow_run" \]; then\n'
        r"(.*?)\n"
        r"\s*else\n",
        run_script,
        re.DOTALL,
    )
    assert match is not None, "could not parse workflow_run branch"
    return match.group(1)


def _extract_ci_select_jq(run_script: str) -> str:
    match = re.search(r"--jq '([^']+)'", run_script)
    assert match is not None, "gh run list --jq expression missing"
    return match.group(1)


def _select_ci_run_id(rows: list[dict], jq_expr: str | None = None) -> str:
    """Execute the workflow's jq selector against sample gh run list JSON."""
    if shutil.which("jq") is None:
        pytest.skip("jq not installed")
    expr = jq_expr or _extract_ci_select_jq(_resolve_step()["run"])
    proc = subprocess.run(
        ["jq", "-r", expr],
        input=json.dumps(rows),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_build_image_workflow_yaml_parses() -> None:
    data = _load_build_workflow()
    assert "jobs" in data
    assert "publish" in data["jobs"]
    on_block = _on_block(data)
    assert "workflow_run" in on_block
    assert "workflow_dispatch" in on_block


def test_resolve_step_is_before_immutable_checkout() -> None:
    steps = _publish_steps(_load_build_workflow())
    resolve_idx = next(i for i, s in enumerate(steps) if s.get("id") == "resolve")
    checkout_idx = _checkout_index(steps)
    assert resolve_idx == 0
    assert checkout_idx == 1
    assert resolve_idx < checkout_idx
    checkout = steps[checkout_idx]
    assert checkout["with"]["ref"] == "${{ steps.resolve.outputs.git_sha }}"


def test_resolve_step_does_not_require_checkout_or_local_git() -> None:
    steps = _publish_steps(_load_build_workflow())
    resolve = _step_by_id(steps, "resolve")
    checkout_idx = _checkout_index(steps)
    resolve_idx = steps.index(resolve)
    assert resolve_idx < checkout_idx
    run = resolve["run"]
    assert "actions/checkout" not in run
    assert ".git" not in run or "no local .git" in run.lower() or "cannot discover" in run
    # Must not move checkout earlier merely to provide repository discovery.
    assert not any("actions/checkout" in (s.get("uses") or "") for s in steps[:resolve_idx])


def test_dispatch_ci_lookup_uses_explicit_repository_identity() -> None:
    resolve = _resolve_step()
    env = resolve.get("env") or {}
    assert env.get("GH_REPO") == "${{ github.repository }}"
    assert env.get("GH_TOKEN") == "${{ github.token }}"
    dispatch = _dispatch_script_fragment(resolve["run"])
    assert '--repo "$GH_REPO"' in dispatch or '--repo "$GH_REPO"' in resolve["run"]
    assert re.search(r"(?m)^\s*gh run list \\\s*$", resolve["run"])
    # Ensure --repo appears on the gh run list invocation, not only elsewhere.
    gh_block = re.search(
        r"gh run list \\\n(?:[ \t]+.+\n)+",
        resolve["run"],
    )
    assert gh_block is not None
    assert '--repo "$GH_REPO"' in gh_block.group(0)
    assert "--workflow ci.yml" in gh_block.group(0)
    assert '--commit "$SHA"' in gh_block.group(0)
    assert "--branch main" in gh_block.group(0)


def test_repository_identity_comes_only_from_github_repository() -> None:
    data = _load_build_workflow()
    on_block = _on_block(data)
    dispatch_inputs = (on_block.get("workflow_dispatch") or {}).get("inputs") or {}
    assert list(dispatch_inputs.keys()) == ["git_sha"]
    assert "repository" not in dispatch_inputs
    assert "repo" not in dispatch_inputs
    resolve = _resolve_step(data)
    env = resolve.get("env") or {}
    assert env["GH_REPO"] == "${{ github.repository }}"
    assert "inputs." not in env["GH_REPO"]
    assert "github.event.inputs" not in env["GH_REPO"]
    run = resolve["run"]
    assert "inputs.repository" not in run
    assert "inputs.repo" not in run
    # Must not derive identity from local checkout metadata.
    assert "git remote" not in run
    assert "git config" not in run


def test_user_inputs_cannot_redirect_github_repository() -> None:
    data = _load_build_workflow()
    on_block = _on_block(data)
    inputs = (on_block.get("workflow_dispatch") or {}).get("inputs") or {}
    forbidden = {
        "repository",
        "repo",
        "owner",
        "gh_repo",
        "github_repository",
        "remote",
    }
    assert forbidden.isdisjoint(set(inputs))
    resolve = _resolve_step(data)
    assert resolve["env"]["GH_REPO"] == "${{ github.repository }}"
    assert "${{ inputs." not in resolve["env"]["GH_REPO"]


def test_workflow_run_path_uses_event_context_not_gh_run_list() -> None:
    resolve = _resolve_step()
    run = resolve["run"]
    workflow_run_body = _workflow_run_script_fragment(run)
    assert "github.event.workflow_run.head_sha" in workflow_run_body
    assert "github.event.workflow_run.id" in workflow_run_body
    assert "gh run list" not in workflow_run_body
    assert "--repo" not in workflow_run_body
    # gh run list exists only on the dispatch path.
    dispatch_body = _dispatch_script_fragment(run)
    assert "gh run list" in dispatch_body
    assert run.count("gh run list") == 1


def test_manual_dispatch_requires_successful_completed_ci_for_exact_sha() -> None:
    resolve = _resolve_step()
    run = resolve["run"]
    dispatch = _dispatch_script_fragment(run)
    assert '--commit "$SHA"' in dispatch
    assert "--branch main" in dispatch
    assert 'select(.conclusion=="success" and .status=="completed")' in dispatch
    assert "No successful CI workflow run found for commit $SHA on main." in dispatch
    assert "Refusing to publish a releasable image without CI evidence." in dispatch
    assert "exit 1" in dispatch
    # Full SHA validation remains after both paths resolve.
    assert r"^[0-9a-f]{40}$" in run


def test_jq_selector_accepts_only_successful_completed_runs() -> None:
    selected = _select_ci_run_id(
        [
            {
                "databaseId": int(SUCCESS_RUN_ID),
                "conclusion": "success",
                "status": "completed",
                "event": "push",
            }
        ]
    )
    assert selected == SUCCESS_RUN_ID


def test_jq_selector_rejects_missing_matching_ci_run() -> None:
    assert _select_ci_run_id([]) == ""


def test_jq_selector_rejects_failed_ci_run() -> None:
    assert (
        _select_ci_run_id(
            [
                {
                    "databaseId": int(FAILED_RUN_ID),
                    "conclusion": "failure",
                    "status": "completed",
                    "event": "push",
                }
            ]
        )
        == ""
    )


def test_jq_selector_rejects_in_progress_ci_run() -> None:
    assert (
        _select_ci_run_id(
            [
                {
                    "databaseId": int(IN_PROGRESS_RUN_ID),
                    "conclusion": "",
                    "status": "in_progress",
                    "event": "push",
                }
            ]
        )
        == ""
    )


def test_dispatch_lookup_pins_commit_and_main_branch() -> None:
    """Another SHA/branch cannot satisfy authority: gh filters before jq."""
    resolve = _resolve_step()
    gh_block = re.search(r"gh run list \\\n(?:[ \t]+.+\n)+", resolve["run"])
    assert gh_block is not None
    block = gh_block.group(0)
    assert '--commit "$SHA"' in block
    assert "--branch main" in block
    # SHA comes from inputs.git_sha or github.sha — not an unresolved branch head.
    dispatch = _dispatch_script_fragment(resolve["run"])
    assert "github.ref" not in dispatch
    assert "github.head_ref" not in dispatch
    assert "origin/main" not in dispatch


def test_dispatch_fail_closed_when_selected_run_id_empty() -> None:
    dispatch = _dispatch_script_fragment(_resolve_step()["run"])
    assert 'if [ -z "$TEST_RUN_ID" ]; then' in dispatch
    assert "exit 1" in dispatch


def test_build_and_publication_gated_on_successful_resolution() -> None:
    steps = _publish_steps(_load_build_workflow())
    resolve_idx = next(i for i, s in enumerate(steps) if s.get("id") == "resolve")
    names_after = [s.get("name") for s in steps[resolve_idx + 1 :]]
    assert "Checkout exact commit" in names_after
    assert "Build and push immutable image" in names_after
    assert "Create release manifest" in names_after
    assert "Upload release manifest artifact" in names_after
    # Default shell steps fail the job when a prior required step fails; no
    # continue-on-error on resolve or publication path.
    for step in steps:
        assert step.get("continue-on-error") in (None, False)


def test_manifest_generation_binds_authority_fields() -> None:
    steps = _publish_steps(_load_build_workflow())
    manifest = _step_by_id(steps, "manifest")
    env = manifest.get("env") or {}
    assert env["GIT_SHA"] == "${{ steps.resolve.outputs.git_sha }}"
    assert env["DIGEST"] == "${{ steps.digest.outputs.image_digest }}"
    assert env["BUILD_RUN_ID"] == "${{ github.run_id }}"
    assert env["TEST_RUN_ID"] == "${{ steps.resolve.outputs.test_workflow_run_id }}"
    run = manifest["run"]
    assert '--git-sha "$GIT_SHA"' in run
    assert '--image-repository "$IMAGE"' in run
    assert '--image-digest "$DIGEST"' in run
    assert '--build-workflow-run-id "$BUILD_RUN_ID"' in run
    assert '--test-workflow-run-id "$TEST_RUN_ID"' in run
    assert "create_release_manifest.py" in run
    assert "validate_release_manifest.py" in run
    # Image repository for OCI prep still uses github.repository (trusted).
    prep = _step_by_id(steps, "prep")
    assert "github.repository" in prep["run"]


def test_permissions_and_main_only_guards_preserved() -> None:
    data = _load_build_workflow()
    perms = data["permissions"]
    assert perms["contents"] == "read"
    assert perms["packages"] == "write"
    assert perms["actions"] == "read"
    assert "id-token" not in perms
    publish = data["jobs"]["publish"]
    if_expr = " ".join(str(publish["if"]).split())
    assert "github.event.repository.fork == false" in if_expr
    assert "github.event.workflow_run.conclusion == 'success'" in if_expr
    assert "github.event.workflow_run.head_branch == 'main'" in if_expr
    assert "github.ref == 'refs/heads/main'" in if_expr


def test_no_deploy_staging_rollback_terraform_ssm_aws_or_production_path() -> None:
    text = _read(BUILD_WF)
    active = "\n".join(
        line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ).lower()
    for needle in (
        "deploy-staging",
        "rollback.yml",
        "terraform apply",
        "terraform plan",
        "aws ssm",
        "configure-aws-credentials",
        "role-to-assume",
        "environment: production",
        "environment: staging",
        "deploy-production",
        "secretsmanager",
    ):
        assert needle not in active, f"unexpected infrastructure path: {needle}"
    data = _load_build_workflow()
    assert "environment" not in data["jobs"]["publish"]


def test_ci_authority_not_weakened_to_branch_head_fallback() -> None:
    resolve = _resolve_step()
    run = resolve["run"]
    dispatch = _dispatch_script_fragment(run)
    assert "gh run list" in dispatch
    assert '--commit "$SHA"' in dispatch
    # Must not accept latest branch head as authority when CI is missing.
    assert re.search(r"gh run list(?![\s\S]*--commit)", dispatch) is None
    assert "workflow_run.head_sha" not in dispatch
    assert "github.ref_name" not in dispatch
    # Empty TEST_RUN_ID still fails closed.
    assert 'if [ -z "$TEST_RUN_ID" ]; then' in dispatch


def test_shell_interpolation_uses_quoted_gh_repo() -> None:
    resolve = _resolve_step()
    # Prefer quoted expansion to avoid word-splitting / injection.
    assert '--repo "$GH_REPO"' in resolve["run"]
    assert "--repo $GH_REPO" not in resolve["run"].replace('--repo "$GH_REPO"', "")
    assert '--commit "$SHA"' in resolve["run"]


def test_existing_ci_green_mechanism_contract_still_holds() -> None:
    """Compatibility with Sprint 25b.1 image-publication contract markers."""
    text = _read(BUILD_WF)
    assert "workflow_run" in text
    assert 'workflows: ["CI"]' in text or "workflows: ['CI']" in text
    assert "test_workflow_run_id" in text
    assert "gh run list" in text
    assert "GH_REPO: ${{ github.repository }}" in text
    assert CI_WF.is_file()


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (
            [
                {
                    "databaseId": 1,
                    "conclusion": "cancelled",
                    "status": "completed",
                    "event": "push",
                },
                {
                    "databaseId": 2,
                    "conclusion": "success",
                    "status": "completed",
                    "event": "push",
                },
            ],
            "2",
        ),
        (
            [
                {
                    "databaseId": 3,
                    "conclusion": "success",
                    "status": "completed",
                    "event": "pull_request",
                }
            ],
            "3",
        ),
    ],
)
def test_jq_selector_picks_first_successful_completed(rows: list[dict], expected: str) -> None:
    assert _select_ci_run_id(rows) == expected


def test_sample_sha_constants_remain_distinct_for_authority_docs() -> None:
    # Keep fixture SHAs available for future executable resolution tests.
    assert SAMPLE_SHA != OTHER_SHA
    assert re.fullmatch(r"[0-9a-f]{40}", SAMPLE_SHA)
    assert re.fullmatch(r"[0-9a-f]{40}", OTHER_SHA)
