"""Sprint 25b.5s — enforce AWS account allowlist in staging mutation workflows.

Root cause: Deploy Staging and Rollback Staging passed
``allowed-account-ids`` to ``aws-actions/configure-aws-credentials@v4``,
but v4 does not declare that input. GitHub warned
\"Unexpected input(s) 'allowed-account-ids'\" and the allowlist was ignored.

Fix: pin both workflows to immutable configure-aws-credentials v6.2.3
(``e6de054238d6b7531b4efff3b6587d9aade6a06c``), which declares and enforces
``allowed-account-ids``, while preserving explicit STS account/role assertions.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
ROLLBACK_WF = WORKFLOWS / "rollback.yml"

APPROVED_ACTION_SHA = "e6de054238d6b7531b4efff3b6587d9aade6a06c"
APPROVED_ACTION_REF = f"aws-actions/configure-aws-credentials@{APPROVED_ACTION_SHA}"
LEGACY_V4_REFS = (
    "aws-actions/configure-aws-credentials@v4",
    "aws-actions/configure-aws-credentials@4",
)
STAGING_MUTATION_WORKFLOWS = (DEPLOY_WF, ROLLBACK_WF)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _configure_aws_steps(workflow: dict) -> list[dict]:
    steps: list[dict] = []
    for job in (workflow.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            uses = step.get("uses") or ""
            if "configure-aws-credentials" in uses:
                steps.append(step)
    return steps


def _on_block(workflow: dict) -> dict:
    # PyYAML 1.1 treats bare `on` as boolean True.
    on_block = workflow.get("on", workflow.get(True))
    assert isinstance(on_block, dict)
    return on_block


def _non_comment_lines(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
    )


def test_deploy_staging_uses_approved_immutable_sha() -> None:
    text = _read(DEPLOY_WF)
    assert APPROVED_ACTION_REF in text
    assert text.count(APPROVED_ACTION_SHA) == 1
    for legacy in LEGACY_V4_REFS:
        assert legacy not in text


def test_rollback_staging_uses_approved_immutable_sha() -> None:
    text = _read(ROLLBACK_WF)
    assert APPROVED_ACTION_REF in text
    assert text.count(APPROVED_ACTION_SHA) == 1
    for legacy in LEGACY_V4_REFS:
        assert legacy not in text


def test_both_workflows_retain_allowed_account_ids_bound_to_staging_authority() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        data = yaml.safe_load(text)
        steps = _configure_aws_steps(data)
        assert len(steps) == 1, f"{path.name}: expected one credential step"
        step = steps[0]
        assert step["uses"] == APPROVED_ACTION_REF
        with_block = step["with"]
        assert with_block["allowed-account-ids"] == "${{ vars.AWS_ACCOUNT_ID }}"
        assert with_block["role-to-assume"] == "${{ vars.AWS_ROLE_ARN }}"
        assert with_block["aws-region"] == "${{ vars.AWS_REGION }}"
        assert with_block["audience"] == "sts.amazonaws.com"
        assert "allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}" in text


def test_explicit_sts_account_and_role_assertions_remain() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        assert "aws sts get-caller-identity" in text
        assert "EXPECTED_ACCOUNT: ${{ vars.AWS_ACCOUNT_ID }}" in text
        assert 'test "$ACCOUNT" = "$EXPECTED_ACCOUNT"' in text
        assert "grep -q 'dealbrain-staging-gha-deploy'" in text
        assert "grep -qv 'dealbrain-production-gha-deploy'" in text
        assert "grep -qv 'production'" in text
        assert "Assert staging role identity" in text


def test_oidc_permissions_and_no_static_credentials() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        data = yaml.safe_load(text)
        assert data["permissions"]["id-token"] == "write"
        assert "AWS_ACCESS_KEY_ID" not in text
        assert "AWS_SECRET_ACCESS_KEY" not in text
        assert "secrets.AWS" not in text
        assert "role-chaining:" not in text


def test_production_isolation_preserved() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        assert re.search(r"(?m)^\s+environment:\s+staging\s*$", text)
        assert "environment: production" not in text
        assert "AWS_ROLE_ARN_PRODUCTION" not in text
        assert "deploy-production" not in text
        # Production role string may appear only inside negative grep assertions.
        assert "grep -qv 'dealbrain-production-gha-deploy'" in text
        assert text.count("dealbrain-production-gha-deploy") == 1
    assert not (WORKFLOWS / "deploy-production.yml").is_file()


def test_staging_concurrency_controls_preserved() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        data = yaml.safe_load(text)
        assert data["concurrency"]["group"] == "staging-release-mutation"
        assert data["concurrency"]["cancel-in-progress"] is False


def test_no_terraform_sendcommand_expansion_or_auto_rollback_introduced() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        active = _non_comment_lines(text).lower()
        assert "terraform apply" not in active
        assert "terraform plan" not in active
        assert "terraform destroy" not in active
        # Pre-existing single SendCommand path retained; not expanded by this sprint.
        assert text.count("aws ssm send-command") == 1
        on_block = _on_block(yaml.safe_load(text))
        assert list(on_block.keys()) == ["workflow_dispatch"]
        assert "workflow_run" not in on_block
        assert "push" not in on_block
        assert "schedule" not in on_block
        if path == DEPLOY_WF:
            assert "automatic rollback" not in active
            assert "auto-rollback" not in active
            assert "rollback on failure" not in active
            assert "on-failure:" not in active


def test_workflow_yaml_remains_valid() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        data = yaml.safe_load(_read(path))
        assert isinstance(data, dict)
        assert "jobs" in data
        assert _on_block(data)
        jobs = data["jobs"]
        assert isinstance(jobs, dict) and jobs
        for job in jobs.values():
            assert job.get("runs-on") == "ubuntu-latest"
            assert isinstance(job.get("steps"), list) and job["steps"]


def test_approved_sha_absent_from_unrelated_workflows() -> None:
    """Scope: only staging mutation workflows receive the v6.2.3 pin."""
    for name in ("ci.yml", "build-image.yml"):
        path = WORKFLOWS / name
        if not path.is_file():
            continue
        text = _read(path)
        assert "configure-aws-credentials" not in text
        assert APPROVED_ACTION_SHA not in text


def test_floating_v6_tag_not_used() -> None:
    for path in STAGING_MUTATION_WORKFLOWS:
        text = _read(path)
        assert "configure-aws-credentials@v6" not in text
        assert "configure-aws-credentials@v6.2.3" not in text
        # Comment may mention v6.2.3; uses: line must be the full SHA.
        uses_line = next(
            line.strip()
            for line in text.splitlines()
            if "uses:" in line and "configure-aws-credentials" in line
        )
        assert uses_line.startswith(f"uses: {APPROVED_ACTION_REF}")
