"""Sprint 25b.5j — GHA evidence validator must run as a module.

Direct path execution (``python scripts/deploy/write_gha_staging_evidence.py``)
puts ``scripts/deploy/`` on ``sys.path[0]`` and does not make the repository
root importable, so ``from scripts.deploy.evidence import …`` fails in GHA
(which installs only ``jsonschema``, not an editable checkout).

Correct contract: ``python -m scripts.deploy.write_gha_staging_evidence`` from
the repository root.
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.deploy.evidence import compute_evidence_sha256, create_evidence

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
VALIDATOR_MODULE = "scripts.deploy.write_gha_staging_evidence"
VALIDATOR_SCRIPT = ROOT / "scripts/deploy/write_gha_staging_evidence.py"
FOLLOWON_MODULE = "scripts.deploy.validate_staging_evidence"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
SAMPLE_MANIFEST_SHA = "c" * 64
SAMPLE_RELEASE_ID = f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}"
SAMPLE_RUN_ID = "999"
SAMPLE_ACCOUNT = "123456789012"
SAMPLE_REGION = "us-east-1"
SAMPLE_INSTANCE = "i-0123456789abcdef0"
SAMPLE_SSM = "cmd-1"

# Exact CLI flags the Deploy Staging workflow must pass (order-insensitive presence).
REQUIRED_WORKFLOW_ARGS = (
    "--evidence",
    "--release-id",
    "--git-sha",
    "--image-repository",
    "--image-digest",
    "--source-manifest-sha256",
    "--deploy-run-id",
    "--aws-account-id",
    "--aws-region",
    "--ec2-instance-id",
    "--ssm-command-id",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _evidence_step(text: str) -> str:
    marker = "Collect and validate authoritative host evidence"
    assert marker in text
    after = text.split(marker, 1)[1]
    next_step = re.search(r"\n      - name:", after)
    assert next_step is not None
    return after[: next_step.start()]


def _sample_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=SAMPLE_RELEASE_ID,
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256=SAMPLE_MANIFEST_SHA,
        deploy_workflow_run_id=SAMPLE_RUN_ID,
        aws_account_id=SAMPLE_ACCOUNT,
        aws_region=SAMPLE_REGION,
        assumed_role_arn=f"arn:aws:iam::{SAMPLE_ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name=f"gha-{SAMPLE_RUN_ID}-staging",
        ec2_instance_id=SAMPLE_INSTANCE,
        ssm_command_id=SAMPLE_SSM,
        migration_revision_before="abc",
        migration_revision_after="def",
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-07-31T11:00:00Z",
        deployment_started_at="2026-07-31T12:00:00Z",
        deployment_finished_at="2026-07-31T12:05:00Z",
        deployment_duration_seconds=300,
        final_status="staging_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def _write_evidence(path: Path, **overrides: object) -> dict:
    payload = _sample_evidence(**overrides)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return payload


def _clean_env() -> dict[str, str]:
    """Subprocess env without PYTHONPATH injection."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    return env


def _binding_args(evidence_path: Path, **overrides: str) -> list[str]:
    values = {
        "--evidence": str(evidence_path),
        "--release-id": SAMPLE_RELEASE_ID,
        "--git-sha": SAMPLE_SHA,
        "--image-repository": SAMPLE_REPO,
        "--image-digest": SAMPLE_DIGEST,
        "--source-manifest-sha256": SAMPLE_MANIFEST_SHA,
        "--deploy-run-id": SAMPLE_RUN_ID,
        "--aws-account-id": SAMPLE_ACCOUNT,
        "--aws-region": SAMPLE_REGION,
        "--ec2-instance-id": SAMPLE_INSTANCE,
        "--ssm-command-id": SAMPLE_SSM,
    }
    values.update({f"--{k.replace('_', '-')}": v for k, v in overrides.items()})
    # Flat argv preserving REQUIRED_WORKFLOW_ARGS order.
    argv: list[str] = []
    for flag in REQUIRED_WORKFLOW_ARGS:
        argv.extend([flag, values[flag]])
    return argv


def _run_module(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", VALIDATOR_MODULE, *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=_clean_env(),
    )


def test_path_style_execution_cannot_import_scripts_package() -> None:
    """Reproduce Deploy Staging run: path execution lacks repo-root imports."""
    probe = f"""
import runpy
import sys
from pathlib import Path

root = Path({str(ROOT)!r}).resolve()
script = root / "scripts/deploy/write_gha_staging_evidence.py"
# Mirror path-style: script dir first; drop repo root (editable install) and ''.
sys.path[:] = [
    str(script.parent),
    *[
        p
        for p in sys.path
        if p not in ("", str(root)) and Path(p).resolve() != root
    ],
]
sys.argv = [str(script), "--help"]
try:
    runpy.run_path(str(script), run_name="__main__")
except ModuleNotFoundError as exc:
    print(f"{{type(exc).__name__}}: {{exc}}", file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(0)
"""
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=_clean_env(),
    )
    assert proc.returncode != 0
    assert "No module named 'scripts'" in proc.stderr


def test_module_help_succeeds_from_repo_root() -> None:
    proc = _run_module(["--help"])
    assert proc.returncode == 0, proc.stderr
    for flag in REQUIRED_WORKFLOW_ARGS:
        assert flag in proc.stdout


def test_module_valid_evidence_succeeds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        payload = _write_evidence(evidence)
        proc = _run_module(_binding_args(evidence))
        assert proc.returncode == 0, proc.stderr
        assert f"ok: host evidence accepted release_id={payload['release_id']}" in proc.stdout
        assert f"status={payload['final_status']}" in proc.stdout
        assert f"sha={payload['evidence_sha256']}" in proc.stdout
        assert proc.stderr == ""


def test_module_invalid_checksum_binding_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence, evidence_sha256="0" * 64)
        proc = _run_module(_binding_args(evidence))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert proc.stdout == ""


def test_module_wrong_release_id_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        proc = _run_module(_binding_args(evidence, release_id="rel-20990101T000000Z-deadbeef"))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "release_id" in proc.stderr


def test_module_wrong_git_sha_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        proc = _run_module(_binding_args(evidence, git_sha="f" * 40))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "git_sha" in proc.stderr


def test_module_wrong_image_digest_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        proc = _run_module(_binding_args(evidence, image_digest="sha256:" + ("a" * 64)))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "image_digest" in proc.stderr


def test_module_wrong_source_manifest_sha_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        proc = _run_module(_binding_args(evidence, source_manifest_sha256="a" * 64))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "source_manifest_sha256" in proc.stderr


def test_module_wrong_deploy_run_id_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        proc = _run_module(_binding_args(evidence, deploy_run_id="11111111111"))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "deploy_workflow_run_id" in proc.stderr


def test_module_wrong_aws_bindings_fail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(evidence)
        cases = (
            {"aws_account_id": "999999999999"},
            {"aws_region": "eu-west-1"},
            {"ec2_instance_id": "i-deadbeefdeadbeef0"},
            {"ssm_command_id": "cmd-wrong"},
        )
        for overrides in cases:
            proc = _run_module(_binding_args(evidence, **overrides))
            assert proc.returncode == 1, overrides
            assert "FAIL:" in proc.stderr
            assert "binding mismatch" in proc.stderr


def test_module_non_staging_ok_fails_where_success_required() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "staging-deploy-evidence.json"
        _write_evidence(
            evidence,
            final_status="failed",
            failure_reason="migration_failed",
            localhost_live=False,
            localhost_ready=False,
            alb_target_healthy=False,
            smoke_ok=False,
            migration_revision_after=None,
            image_id=None,
            repo_digest=None,
            image_created_at=None,
        )
        proc = _run_module(_binding_args(evidence))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "staging_ok" in proc.stderr


def test_module_missing_evidence_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "staging-deploy-evidence.json"
        proc = _run_module(_binding_args(missing))
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "refusing to fabricate staging_ok" in proc.stderr
        assert not missing.exists()


def test_deploy_staging_uses_module_invocation_from_repo_root() -> None:
    step = _evidence_step(_read(DEPLOY_WF))
    assert "python -m scripts.deploy.write_gha_staging_evidence" in step
    assert "python scripts/deploy/write_gha_staging_evidence.py" not in step
    assert "python3 scripts/deploy/write_gha_staging_evidence.py" not in step
    # Follow-on schema validator has the same import contract.
    assert "python -m scripts.deploy.validate_staging_evidence" in step
    assert "python scripts/deploy/validate_staging_evidence.py" not in step
    # Checkout lands at the workspace root; no cd away before the module run.
    assert not re.search(r"^\s*cd\s+", step, flags=re.MULTILINE)
    # No PYTHONPATH / sys.path mutation hacks introduced for this fix.
    assert "PYTHONPATH" not in step
    assert "sys.path.insert" not in step
    assert "sys.path.append" not in step


def test_deploy_staging_preserves_evidence_argument_list() -> None:
    step = _evidence_step(_read(DEPLOY_WF))
    for flag in REQUIRED_WORKFLOW_ARGS:
        assert flag in step
    # Binding value sources remain the workflow contract (not hard-coded literals).
    assert '--evidence "$EVIDENCE_PATH"' in step
    assert '--release-id "$RELEASE_ID"' in step
    assert '--git-sha "${{ steps.manifest.outputs.git_sha }}"' in step
    assert '--image-repository "${{ steps.manifest.outputs.image_repository }}"' in step
    assert '--image-digest "${{ steps.manifest.outputs.image_digest }}"' in step
    assert '--source-manifest-sha256 "${{ steps.manifest.outputs.manifest_sha256 }}"' in step
    assert '--deploy-run-id "${{ github.run_id }}"' in step
    assert '--aws-account-id "$EXPECTED_ACCOUNT"' in step
    assert '--aws-region "$EXPECTED_REGION"' in step
    assert '--ec2-instance-id "${{ steps.targets.outputs.instance_id }}"' in step
    assert '--ssm-command-id "$COMMAND_ID"' in step
    # Authoritative host-evidence + sidecar + fail-closed gates preserved.
    assert "aws s3api head-object" in step
    assert "Refusing to fabricate staging_ok" in step
    assert "${EVIDENCE_KEY}.sha256" in step
    assert "jq -r '.evidence_sha256'" in step
    assert "Upload staging evidence GitHub artifact" not in step  # next step boundary


def test_workflow_keeps_main_checkout_and_staging_isolation() -> None:
    text = _read(DEPLOY_WF)
    assert "Checkout deploy tooling (main)" in text
    assert "ref: main" in text
    assert "environment: staging" in text
    assert "environment: production" not in text
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    assert not (WORKFLOWS / "rollback.yml").is_file()


def test_validator_script_documents_module_invocation() -> None:
    text = _read(VALIDATOR_SCRIPT)
    assert "python -m scripts.deploy.write_gha_staging_evidence" in text
    assert "sys.path.insert" not in text
    assert "PYTHONPATH" not in text
    # Canonical evidence.py remains the validation authority.
    assert "from scripts.deploy.evidence import" in text
    assert "validate_evidence_bindings" in text
    assert "require_staging_ok=True" in text
    # No secret / env dump logging.
    assert "os.environ" not in text
    assert "printenv" not in text


def test_followon_validate_staging_evidence_module_help() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", FOLLOWON_MODULE, "--help"],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=_clean_env(),
    )
    assert proc.returncode == 0, proc.stderr
    assert "staging-deploy-evidence" in proc.stdout.lower() or "path" in proc.stdout.lower()
