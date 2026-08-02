"""Sprint 25b.5e — staging release validator must run as a module.

Direct path execution (``python scripts/deploy/validate_staging_release.py``)
puts ``scripts/deploy/`` on ``sys.path[0]`` and does not make the repository
root importable, so ``from scripts.release.manifest import …`` fails in GHA
(which installs only ``jsonschema``, not an editable checkout).

Correct contract: ``python -m scripts.deploy.validate_staging_release`` from
the repository root.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
VALIDATOR_MODULE = "scripts.deploy.validate_staging_release"
VALIDATOR_SCRIPT = ROOT / "scripts/deploy/validate_staging_release.py"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _manifest_step(text: str) -> str:
    marker = "Fetch and validate Build Image release manifest"
    assert marker in text
    after = text.split(marker, 1)[1]
    next_step = re.search(r"\n      - name:", after)
    assert next_step is not None
    return after[: next_step.start()]


def _write_built_manifest(path: Path, **overrides: object) -> dict:
    payload = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-07-31T12:00:00Z",
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
    )
    if overrides:
        payload = dict(payload)
        payload.update(overrides)
        from scripts.release.manifest import compute_manifest_sha256

        if "manifest_sha256" not in overrides:
            payload["manifest_sha256"] = compute_manifest_sha256(payload)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return payload


def _clean_env() -> dict[str, str]:
    """Subprocess env without PYTHONPATH injection."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    return env


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
    """Reproduce Deploy Staging #2: path execution lacks repo-root imports."""
    # Undo the editable-install .pth that adds ROOT locally; GHA has no such pth.
    probe = f"""
import runpy
import sys
from pathlib import Path

root = Path({str(ROOT)!r}).resolve()
script = root / "scripts/deploy/validate_staging_release.py"
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


def test_module_execution_resolves_imports_from_repo_root() -> None:
    proc = _run_module(["--help"])
    assert proc.returncode == 0, proc.stderr
    assert "manifest" in proc.stdout
    assert "--build-workflow-run-id" in proc.stdout
    assert "--release-id" in proc.stdout
    assert "--git-sha" in proc.stdout
    assert "--image-repository" in proc.stdout


def test_module_execution_valid_manifest_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        man = Path(tmp) / "release-manifest.json"
        payload = _write_built_manifest(man)
        proc = _run_module(
            [
                str(man),
                "--build-workflow-run-id",
                "111",
                "--git-sha",
                SAMPLE_SHA,
                "--release-id",
                payload["release_id"],
                "--image-repository",
                SAMPLE_REPO,
            ]
        )
        assert proc.returncode == 0, proc.stderr
        assert f"ok: release_id={payload['release_id']}" in proc.stdout
        assert f"digest={SAMPLE_DIGEST}" in proc.stdout
        assert f"manifest_sha256={payload['manifest_sha256']}" in proc.stdout


def test_module_execution_invalid_manifest_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        man = Path(tmp) / "bad-manifest.json"
        _write_built_manifest(man, final_status="staging_ok", environment="staging")
        proc = _run_module([str(man), "--build-workflow-run-id", "111"])
        assert proc.returncode == 1
        assert proc.stdout == ""
        assert "FAIL:" in proc.stderr


def test_module_execution_release_id_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        man = Path(tmp) / "release-manifest.json"
        _write_built_manifest(man)
        proc = _run_module(
            [
                str(man),
                "--release-id",
                "rel-20990101T000000Z-deadbeef",
            ]
        )
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr
        assert "release_id mismatch" in proc.stderr


def test_module_execution_rejects_mutable_tag_authority() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        man = Path(tmp) / "release-manifest.json"
        # Corrupt digest into a tag-like value after creation — schema/semantic fail.
        payload = _write_built_manifest(man)
        payload["image_digest"] = "latest"
        from scripts.release.manifest import compute_manifest_sha256

        payload["manifest_sha256"] = compute_manifest_sha256(payload)
        man.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        proc = _run_module([str(man)])
        assert proc.returncode == 1
        assert "FAIL:" in proc.stderr


def test_deploy_staging_uses_module_invocation() -> None:
    step = _manifest_step(_read(DEPLOY_WF))
    assert "python -m scripts.deploy.validate_staging_release" in step
    # Path-style invocation must not remain for this validator.
    assert "python scripts/deploy/validate_staging_release.py" not in step
    assert "$MANIFEST_PATH" in step
    assert '"${EXTRA_ARGS[@]}"' in step


def test_deploy_staging_keeps_digest_and_release_id_gates() -> None:
    text = _read(DEPLOY_WF)
    step = _manifest_step(text)
    assert "--build-workflow-run-id" in step
    assert "--git-sha" in step
    assert "--image-repository" in step
    assert 'EXTRA_ARGS+=(--release-id "$OPTIONAL_RELEASE_ID")' in step
    assert "imagetools inspect" in step
    assert "@${IMAGE_DIGEST}" in text
    # No mutable-tag fallback introduced by this sprint.
    assert ":latest" not in step
    assert "ci-latest" not in step


def test_production_paths_untouched() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    assert not (WORKFLOWS / "rollback.yml").is_file()
    text = _read(DEPLOY_WF)
    assert "environment: production" not in text
    assert "environment: staging" in text
    # Negative production role assert remains; no production assume path.
    assert "grep -qv 'dealbrain-production-gha-deploy'" in text
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in text
    prod_tf = ROOT / "infra/terraform/environments/production/main.tf"
    assert prod_tf.is_file()
    prod = _read(prod_tf)
    assert "ssm_deploy_document" not in prod
    assert "release_artifacts" not in prod


def test_validator_script_documents_module_invocation() -> None:
    text = _read(VALIDATOR_SCRIPT)
    assert "python -m scripts.deploy.validate_staging_release" in text
    # No broad PYTHONPATH / sys.path mutation in the validator itself.
    assert "sys.path.insert" not in text
    assert "PYTHONPATH" not in text
