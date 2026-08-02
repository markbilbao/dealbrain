"""Sprint 25b.5d — deploy-staging release-manifest fetch --dest contract."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
FETCH_SCRIPT = ROOT / "scripts/deploy/fetch_release_artifact.py"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _manifest_step(text: str) -> str:
    marker = "Fetch and validate Build Image release manifest"
    assert marker in text
    after = text.split(marker, 1)[1]
    # Next top-level step name under jobs.deploy.steps
    next_step = re.search(r"\n      - name:", after)
    assert next_step is not None
    return after[: next_step.start()]


def test_fetch_cli_requires_dest_even_with_assert_only() -> None:
    """Reproduce the observed argparse failure: --dest is always required."""
    proc = subprocess.run(
        [
            sys.executable,
            str(FETCH_SCRIPT),
            "--build-workflow-run-id",
            "123",
            "--assert-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "required: --dest" in proc.stderr


def test_fetch_cli_accepts_dest_with_assert_only_help_contract() -> None:
    help_proc = subprocess.run(
        [sys.executable, str(FETCH_SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--dest DEST" in help_proc.stdout
    assert "--build-workflow-run-id" in help_proc.stdout
    assert "--assert-only" in help_proc.stdout


def test_deploy_staging_passes_dest_on_every_fetch_invocation() -> None:
    step = _manifest_step(_read(DEPLOY_WF))
    invocations = [
        block
        for block in re.split(r"(?=python scripts/deploy/fetch_release_artifact\.py)", step)
        if "fetch_release_artifact.py" in block
    ]
    assert len(invocations) == 2
    for block in invocations:
        assert re.search(
            r'--dest\s+"\$ARTIFACT_DEST"',
            block,
        ), f"fetch invocation missing quoted --dest $ARTIFACT_DEST:\n{block}"


def test_deploy_staging_dest_is_deterministic_workspace_path() -> None:
    step = _manifest_step(_read(DEPLOY_WF))
    assert 'ARTIFACT_DEST=".deploy-work/artifact"' in step
    assert 'mkdir -p .deploy-work "$ARTIFACT_DEST"' in step
    # Download and assert-only share the same destination variable.
    assert step.count('"$ARTIFACT_DEST"') >= 3


def test_deploy_staging_supplies_build_workflow_run_id() -> None:
    text = _read(DEPLOY_WF)
    assert "build_workflow_run_id:" in text
    step = _manifest_step(text)
    assert "BUILD_RUN_ID: ${{ inputs.build_workflow_run_id }}" in text
    assert step.count('"$BUILD_RUN_ID"') >= 2
    for block in re.split(r"(?=python scripts/deploy/fetch_release_artifact\.py)", step):
        if "fetch_release_artifact.py" not in block:
            continue
        assert "--build-workflow-run-id" in block
        assert '"$BUILD_RUN_ID"' in block


def test_deploy_staging_release_id_cross_check_intact() -> None:
    text = _read(DEPLOY_WF)
    step = _manifest_step(text)
    assert "OPTIONAL_RELEASE_ID: ${{ inputs.release_id }}" in text
    assert 'if [ -n "${OPTIONAL_RELEASE_ID}" ]; then' in step
    assert 'EXTRA_ARGS+=(--release-id "$OPTIONAL_RELEASE_ID")' in step
    assert "python -m scripts.deploy.validate_staging_release" in step


def test_deploy_staging_manifest_validation_fail_closed() -> None:
    step = _manifest_step(_read(DEPLOY_WF))
    assert "python -m scripts.deploy.validate_staging_release" in step
    assert "imagetools inspect" in step
    assert 'test "$BUILD_CONCLUSION" = "success"' in step
    assert 'test "$BUILD_BRANCH" = "main"' in step
    # No mutable tag fallback in the manifest step.
    assert "latest" not in step
    assert "ci-latest" not in step
    assert "@${IMAGE_DIGEST}" in step or "@${IMAGE_DIGEST}" in _read(DEPLOY_WF)


def test_deploy_staging_downstream_consumes_manifest_path() -> None:
    text = _read(DEPLOY_WF)
    assert "manifest_path=$MANIFEST_PATH" in text
    assert "MANIFEST_PATH: ${{ steps.manifest.outputs.manifest_path }}" in text
    assert "build_staging_bundle.py" in text
    assert '--manifest "$MANIFEST_PATH"' in text
    # Digest / release_id remain fail-closed outputs consumed later.
    assert "steps.manifest.outputs.release_id" in text
    assert "steps.manifest.outputs.image_digest" in text


def test_production_workflow_untouched() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    assert not (WORKFLOWS / "rollback.yml").is_file()
    text = _read(DEPLOY_WF)
    assert "environment: production" not in text
    assert "dealbrain-production-gha-deploy" in text  # negative assert only
    assert "grep -qv 'dealbrain-production-gha-deploy'" in text
