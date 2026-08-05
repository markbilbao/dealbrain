"""Sprint 25b.5t — Python 3.9 compatibility for rollback prior-evidence helper."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts.deploy.build_staging_bundle import INCLUDE_FILES
from scripts.deploy.evidence import (
    UTC_Z_RE,
    compute_evidence_sha256,
    create_evidence,
    write_evidence,
)
from scripts.deploy.prior_staging_evidence import (
    PriorEvidenceError,
    _parse_utc_z,
    discover_candidate_pairs,
    load_prior_evidence_with_sidecar,
    select_authoritative_prior_staging_evidence,
)
from scripts.deploy.rollback_evidence import (
    EvidenceError as RollbackEvidenceError,
)
from scripts.deploy.rollback_evidence import (
    create_rollback_evidence,
    validate_rollback_evidence,
)

# Tests intentionally assert timezone.utc (host Python 3.9 contract).
# ruff: noqa: UP017

ROOT = Path(__file__).resolve().parents[2]
PRIOR_PY = ROOT / "scripts/deploy/prior_staging_evidence.py"
EVIDENCE_PY = ROOT / "scripts/deploy/evidence.py"
ROLLBACK_EVIDENCE_PY = ROOT / "scripts/deploy/rollback_evidence.py"
RESOLVE_PY = ROOT / "scripts/deploy/host/resolve-rollback-migration.py"
ROLLBACK_SH = ROOT / "scripts/deploy/host/dealbrain-staging-rollback.sh"
DEPLOY_SH = ROOT / "scripts/deploy/host/dealbrain-staging-deploy.sh"
WORKFLOWS = ROOT / ".github/workflows"
PROD_TF = ROOT / "infra/terraform/environments/production"

_WORKSPACE_PY39 = ROOT / ".tools/python/cpython-3.9-macos-aarch64-none/bin/python3.9"

SAMPLE_SHA = "83bfc6c57fd99a43445b6edaddcaf863fabf3473"
SAMPLE_DIGEST = "sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f"
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
BASELINE_RELEASE = f"rel-20260802T093246Z-{SAMPLE_SHA[:12]}"
ACCOUNT = "123456789012"
REGION = "us-east-1"
INSTANCE = "i-0123456789abcdef0"
MANIFEST_SHA = "c" * 64
CANON_REV = "d4e5f6a7b8c9"

# Schema-2 host-executed Python helpers delivered under bin/.
HOST_EXECUTED_PY = sorted(
    {dst for _src, dst in INCLUDE_FILES if dst.startswith("bin/") and dst.endswith(".py")}
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _find_python39() -> Path | None:
    env = os.environ.get("DEALBRAIN_PYTHON39")
    if env and Path(env).is_file():
        return Path(env)
    if _WORKSPACE_PY39.is_file():
        return _WORKSPACE_PY39
    found = shutil.which("python3.9")
    return Path(found) if found else None


def _assert_no_datetime_utc(source: str, *, label: str) -> None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "datetime":
            names = {alias.name for alias in node.names}
            assert "UTC" not in names, f"{label} must not import datetime.UTC"
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "datetime"
        ):
            assert node.attr != "UTC", f"{label} must not reference datetime.UTC"
    assert not re.search(r"from datetime import[^\n]*\bUTC\b", source), label


def _prior(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=BASELINE_RELEASE,
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256=MANIFEST_SHA,
        deploy_workflow_run_id="11",
        aws_account_id=ACCOUNT,
        aws_region=REGION,
        assumed_role_arn=f"arn:aws:iam::{ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-11-staging",
        ec2_instance_id=INSTANCE,
        ssm_command_id="11111111-1111-1111-1111-111111111111",
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-08-02T09:00:00Z",
        deployment_started_at="2026-08-02T09:30:00Z",
        deployment_finished_at="2026-08-02T09:35:00Z",
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


def _write_candidate(dir_path: Path, run_id: str, payload: dict) -> tuple[Path, Path, str]:
    run_dir = dir_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "staging-deploy-evidence.json"
    write_evidence(json_path, payload)
    sidecar = json_path.with_suffix(json_path.suffix + ".sha256")
    assert sidecar.is_file()
    return json_path, sidecar, f"{run_id}/staging-deploy-evidence.json"


def _select(candidates_dir: Path, **binding_overrides: object):
    pairs = discover_candidate_pairs(candidates_dir)
    kwargs = dict(
        expected_release_id=BASELINE_RELEASE,
        expected_image_digest=SAMPLE_DIGEST,
        expected_image_repository=SAMPLE_REPO,
        expected_aws_account_id=ACCOUNT,
        expected_aws_region=REGION,
        expected_ec2_instance_id=INSTANCE,
        expected_source_manifest_sha256=MANIFEST_SHA,
    )
    kwargs.update(binding_overrides)
    return select_authoritative_prior_staging_evidence(pairs, **kwargs)


# ---------------------------------------------------------------------------
# 1–3. Python 3.9 import / datetime.UTC absence / timezone-aware UTC
# ---------------------------------------------------------------------------


def test_prior_staging_evidence_has_no_datetime_utc_dependency() -> None:
    source = _read(PRIOR_PY)
    _assert_no_datetime_utc(source, label="prior_staging_evidence.py")
    assert "from datetime import datetime, timezone" in source
    assert "timezone.utc" in source
    assert "tzinfo=timezone.utc" in source


def test_host_executed_scripts_have_no_datetime_utc_import() -> None:
    """No schema-2 host-executed Python helper may import datetime.UTC."""
    assert "bin/prior_staging_evidence.py" in HOST_EXECUTED_PY
    for dst in HOST_EXECUTED_PY:
        src_rel = next(src for src, d in INCLUDE_FILES if d == dst)
        source = _read(ROOT / src_rel)
        _assert_no_datetime_utc(source, label=dst)


def test_parse_utc_z_returns_timezone_aware_utc() -> None:
    parsed = _parse_utc_z("2026-08-02T09:35:00Z")
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    assert parsed.utcoffset().total_seconds() == 0
    assert parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == "2026-08-02T09:35:00Z"
    assert UTC_Z_RE.fullmatch(parsed.strftime("%Y-%m-%dT%H:%M:%SZ"))


def test_timestamp_serialization_format_unchanged() -> None:
    """Selection still emits canonical UTC Z strings (no +00:00 leak)."""
    finished = "2026-08-02T10:05:00Z"
    with tempfile.TemporaryDirectory() as tmp:
        candidates = Path(tmp)
        _write_candidate(
            candidates,
            "12",
            _prior(
                deploy_workflow_run_id="12",
                deployment_started_at="2026-08-02T10:00:00Z",
                deployment_finished_at=finished,
                deployment_duration_seconds=300,
                role_session_name="gha-12-staging",
                ssm_command_id="12121212-1212-1212-1212-121212121212",
            ),
        )
        selected = _select(candidates)
    assert selected.deployment_finished_at == finished
    assert selected.deployment_finished_at.endswith("Z")
    assert "+" not in selected.deployment_finished_at
    assert UTC_Z_RE.fullmatch(selected.deployment_finished_at)


def test_prior_helper_imports_and_executes_under_python39() -> None:
    py39 = _find_python39()
    if py39 is None:
        pytest.skip("Python 3.9 interpreter not available for host-compat probe")

    schema = ROOT / "schemas/staging-deploy-evidence.schema.json"
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = Path(tmp)
        shutil.copy2(PRIOR_PY, bin_dir / "prior_staging_evidence.py")
        shutil.copy2(EVIDENCE_PY, bin_dir / "evidence.py")
        shutil.copy2(schema, bin_dir / "staging-deploy-evidence.schema.json")
        (bin_dir / "jsonschema.py").write_text(
            'raise ImportError("jsonschema unavailable on host")\n',
            encoding="utf-8",
        )
        probe = bin_dir / "probe.py"
        probe.write_text(
            "\n".join(
                [
                    "import importlib.util",
                    "import sys",
                    "from pathlib import Path",
                    "p = Path(__file__).resolve().parent / 'prior_staging_evidence.py'",
                    "spec = importlib.util.spec_from_file_location('prior', p)",
                    "mod = importlib.util.module_from_spec(spec)",
                    "sys.modules[spec.name] = mod",
                    "spec.loader.exec_module(mod)",
                    "parsed = mod._parse_utc_z('2026-08-02T09:35:00Z')",
                    "assert parsed.tzinfo is not None",
                    "assert parsed.utcoffset().total_seconds() == 0",
                    "assert parsed.strftime('%Y-%m-%dT%H:%M:%SZ') == '2026-08-02T09:35:00Z'",
                    "print('IMPORT_OK', parsed.isoformat())",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["PYTHONPATH"] = ""
        proc = subprocess.run(
            [str(py39), str(probe)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(bin_dir),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "IMPORT_OK" in proc.stdout


def test_datetime_utc_import_still_fails_under_python39_semantics() -> None:
    """Reproduce the failed rollback ImportError boundary on Python 3.9."""
    py39 = _find_python39()
    if py39 is None:
        probe = (
            "import datetime as d\n"
            "import types\n"
            "fake = types.ModuleType('datetime')\n"
            "fake.datetime = d.datetime\n"
            "fake.timezone = d.timezone\n"
            "import sys\n"
            "sys.modules['datetime'] = fake\n"
            "try:\n"
            "    from datetime import UTC\n"
            "except ImportError as exc:\n"
            "    print('UTC_FAIL', exc)\n"
            "    raise SystemExit(0)\n"
            "print('UTC_OK')\n"
            "raise SystemExit(1)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "UTC_FAIL" in proc.stdout
        return

    proc = subprocess.run(
        [
            str(py39),
            "-c",
            "try:\n"
            " from datetime import UTC\n"
            " print('UTC_OK')\n"
            "except ImportError as e:\n"
            " print('UTC_FAIL', e)\n",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "UTC_FAIL" in proc.stdout
    assert "cannot import name 'UTC'" in proc.stdout


# ---------------------------------------------------------------------------
# 4–6. Canonical checksum / validation fail-closed regressions
# ---------------------------------------------------------------------------


def test_canonical_evidence_hash_and_sidecar_unchanged(tmp_path: Path) -> None:
    payload = _prior()
    expected_hash = compute_evidence_sha256(payload)
    assert payload["evidence_sha256"] == expected_hash
    json_path, sidecar, _key = _write_candidate(tmp_path, "11", payload)
    loaded = load_prior_evidence_with_sidecar(json_path, sidecar)
    assert loaded["evidence_sha256"] == expected_hash
    assert sidecar.read_text(encoding="utf-8").strip().split()[0] == expected_hash
    # Recompute from disk bytes path via canonicalize authority.
    again = compute_evidence_sha256(loaded)
    assert again == expected_hash


def test_prior_rejects_malformed_json(tmp_path: Path) -> None:
    run_dir = tmp_path / "11"
    run_dir.mkdir()
    json_path = run_dir / "staging-deploy-evidence.json"
    sidecar = json_path.with_suffix(json_path.suffix + ".sha256")
    json_path.write_text("{not-json", encoding="utf-8")
    digest = hashlib.sha256(json_path.read_bytes()).hexdigest()
    # Sidecar present but JSON malformed — must fail closed before selection.
    sidecar.write_text(digest + "\n", encoding="utf-8")
    with pytest.raises(PriorEvidenceError, match="unreadable|JSON"):
        load_prior_evidence_with_sidecar(json_path, sidecar)


def test_prior_rejects_wrong_release_and_digest(tmp_path: Path) -> None:
    _write_candidate(tmp_path, "11", _prior())
    with pytest.raises(PriorEvidenceError, match="release_id"):
        _select(tmp_path, expected_release_id="rel-20260804T152521Z-da17ebbffd47")
    with pytest.raises(PriorEvidenceError, match="image_digest"):
        _select(tmp_path, expected_image_digest="sha256:" + ("e" * 64))


def test_prior_rejects_wrong_account_region_instance(tmp_path: Path) -> None:
    _write_candidate(tmp_path, "11", _prior())
    with pytest.raises(PriorEvidenceError, match="aws_account_id"):
        _select(tmp_path, expected_aws_account_id="999999999999")
    with pytest.raises(PriorEvidenceError, match="aws_region"):
        _select(tmp_path, expected_aws_region="us-west-2")
    with pytest.raises(PriorEvidenceError, match="ec2_instance_id"):
        _select(tmp_path, expected_ec2_instance_id="i-0deadbeefdeadbeef")


def test_prior_rejects_invalid_timestamp(tmp_path: Path) -> None:
    with pytest.raises(PriorEvidenceError, match="malformed UTC timestamp"):
        _parse_utc_z("2026-08-02T09:35:00+00:00")
    with pytest.raises(PriorEvidenceError, match="malformed UTC timestamp"):
        _parse_utc_z("not-a-timestamp")
    with pytest.raises(PriorEvidenceError, match="malformed UTC timestamp"):
        _parse_utc_z("")
    # Bypass write_evidence so invalid stamps reach prior validation fail-closed.
    bad = _prior()
    bad["deployment_finished_at"] = "2026-08-02T09:35:00+00:00"
    bad["evidence_sha256"] = compute_evidence_sha256(bad)
    run_dir = tmp_path / "11"
    run_dir.mkdir()
    json_path = run_dir / "staging-deploy-evidence.json"
    sidecar = json_path.with_suffix(json_path.suffix + ".sha256")
    json_path.write_text(json.dumps(bad, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sidecar.write_text(bad["evidence_sha256"] + "\n", encoding="utf-8")
    with pytest.raises(PriorEvidenceError):
        _select(tmp_path)


def test_prior_rejects_stale_candidate_when_newer_valid_exists(tmp_path: Path) -> None:
    """Older (stale relative) valid evidence must not win over a newer finished_at."""
    _write_candidate(
        tmp_path,
        "10",
        _prior(
            deploy_workflow_run_id="10",
            deployment_started_at="2026-08-02T08:00:00Z",
            deployment_finished_at="2026-08-02T08:05:00Z",
            deployment_duration_seconds=300,
            role_session_name="gha-10-staging",
        ),
    )
    _write_candidate(
        tmp_path,
        "12",
        _prior(
            deploy_workflow_run_id="12",
            deployment_started_at="2026-08-02T10:00:00Z",
            deployment_finished_at="2026-08-02T10:05:00Z",
            deployment_duration_seconds=300,
            role_session_name="gha-12-staging",
            ssm_command_id="12121212-1212-1212-1212-121212121212",
        ),
    )
    selected = _select(tmp_path)
    assert selected.deploy_workflow_run_id == "12"
    assert selected.deployment_finished_at == "2026-08-02T10:05:00Z"


def test_rollback_failure_evidence_remains_valid_and_fail_closed() -> None:
    payload = create_rollback_evidence(
        rollback_workflow_run_id="31004783285",
        aws_account_id=ACCOUNT,
        aws_region=REGION,
        assumed_role_arn=f"arn:aws:iam::{ACCOUNT}:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-rollback-1",
        ec2_instance_id=INSTANCE,
        ssm_command_id="7cb947e0-7f9d-4b25-9054-da8952d503c3",
        rollback_started_at="2026-08-05T12:00:00Z",
        rollback_finished_at="2026-08-05T12:01:00Z",
        rollback_duration_seconds=60,
        source_release_id="rel-20260804T152521Z-da17ebbffd47",
        source_image_digest="sha256:" + ("a" * 64),
        target_release_id=BASELINE_RELEASE,
        target_image_digest=SAMPLE_DIGEST,
        target_git_sha=SAMPLE_SHA,
        target_image_repository=SAMPLE_REPO,
        target_manifest_sha256=MANIFEST_SHA,
        migration_revision_before=None,
        migration_revision_after=None,
        target_migration_revision_authority=None,
        current_pointer_before="/opt/dealbrain/releases/rel-20260804T152521Z-da17ebbffd47",
        current_pointer_after="/opt/dealbrain/releases/rel-20260804T152521Z-da17ebbffd47",
        previous_pointer_before="/opt/dealbrain/releases/rel-20260802T093246Z-83bfc6c57fd9",
        previous_pointer_after="/opt/dealbrain/releases/rel-20260802T093246Z-83bfc6c57fd9",
        running_digest_after="sha256:" + ("a" * 64),
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        final_status="failed",
        failure_reason="prior_staging_evidence_resolution_failed",
    )
    validate_rollback_evidence(payload)
    assert payload["final_status"] == "failed"
    assert payload["failure_reason"]
    # Fail-closed: cannot mint rollback_ok without health gates / migration authority.
    with pytest.raises(RollbackEvidenceError):
        create_rollback_evidence(
            rollback_workflow_run_id="31004783285",
            aws_account_id=ACCOUNT,
            aws_region=REGION,
            assumed_role_arn=f"arn:aws:iam::{ACCOUNT}:role/dealbrain-staging-gha-deploy",
            role_session_name="gha-rollback-1",
            ec2_instance_id=INSTANCE,
            ssm_command_id="7cb947e0-7f9d-4b25-9054-da8952d503c3",
            rollback_started_at="2026-08-05T12:00:00Z",
            rollback_finished_at="2026-08-05T12:01:00Z",
            rollback_duration_seconds=60,
            source_release_id="rel-20260804T152521Z-da17ebbffd47",
            source_image_digest="sha256:" + ("a" * 64),
            target_release_id=BASELINE_RELEASE,
            target_image_digest=SAMPLE_DIGEST,
            target_git_sha=SAMPLE_SHA,
            target_image_repository=SAMPLE_REPO,
            target_manifest_sha256=MANIFEST_SHA,
            migration_revision_before=None,
            migration_revision_after=None,
            target_migration_revision_authority=None,
            current_pointer_before="/opt/dealbrain/releases/rel-20260804T152521Z-da17ebbffd47",
            current_pointer_after="/opt/dealbrain/releases/rel-20260804T152521Z-da17ebbffd47",
            previous_pointer_before="/opt/dealbrain/releases/rel-20260802T093246Z-83bfc6c57fd9",
            previous_pointer_after="/opt/dealbrain/releases/rel-20260802T093246Z-83bfc6c57fd9",
            running_digest_after="sha256:" + ("a" * 64),
            localhost_live=False,
            localhost_ready=False,
            alb_target_healthy=False,
            final_status="rollback_ok",
            failure_reason=None,
        )


# ---------------------------------------------------------------------------
# 7–9. Ordering / packaging / no infra mutation
# ---------------------------------------------------------------------------


def test_no_pointer_commit_before_migration_evidence_resolution() -> None:
    host = _read(ROLLBACK_SH)
    mig_idx = host.index("resolve_target_recorded_migration")
    api_idx = host.index("API_REPLACEMENT_OCCURRED=1")
    ptr_idx = host.index("commit_release_pointer")
    assert mig_idx < api_idx < ptr_idx
    # Host prefers installed ROOT/bin resolver (Deploy Staging tooling), not target bundle.
    assert 'ROOT}/bin/resolve-rollback-migration.py"' in host
    assert "prior_staging_evidence.py" in _read(DEPLOY_SH)


def test_packaging_installs_prior_helper_from_deploy_staging_schema2() -> None:
    assert ("scripts/deploy/prior_staging_evidence.py", "bin/prior_staging_evidence.py") in (
        INCLUDE_FILES
    )
    deploy = _read(DEPLOY_SH)
    assert 'prior_staging_evidence.py" \\' in deploy or "prior_staging_evidence.py" in deploy
    assert "${ROOT}/bin/prior_staging_evidence.py" in deploy
    # Rollback optional helper refresh from target must NOT overwrite prior helper
    # from historical schema-1 targets — host copy remains Deploy Staging authority.
    rollback = _read(ROLLBACK_SH)
    refresh_block = rollback.split("Host tooling remains authoritative")[1].split(
        "export DEALBRAIN_IMAGE"
    )[0]
    assert "prior_staging_evidence.py" not in refresh_block
    assert "resolve-rollback-migration.py" not in refresh_block


def test_no_terraform_ssm_or_auto_rollback_path_introduced() -> None:
    prior_src = _read(PRIOR_PY)
    resolve_src = _read(RESOLVE_PY)
    for src in (prior_src, resolve_src):
        assert "boto3" not in src
        assert "SendCommand" not in src
        assert "terraform" not in src.lower()
    assert not (WORKFLOWS / "deploy-production.yml").exists()
    assert PROD_TF.is_dir()
    # No new workflow files in this sprint scope.
    assert (WORKFLOWS / "rollback.yml").is_file()
    assert (WORKFLOWS / "deploy-staging.yml").is_file()


def test_flat_bin_layout_loads_sibling_prior_module(tmp_path: Path) -> None:
    """Host flat bin/ layout loads prior_staging_evidence.py as a sibling."""
    shutil.copy2(PRIOR_PY, tmp_path / "prior_staging_evidence.py")
    shutil.copy2(EVIDENCE_PY, tmp_path / "evidence.py")
    shutil.copy2(
        ROOT / "schemas/staging-deploy-evidence.schema.json",
        tmp_path / "staging-deploy-evidence.schema.json",
    )
    shutil.copy2(RESOLVE_PY, tmp_path / "resolve-rollback-migration.py")
    spec = importlib.util.spec_from_file_location(
        "dealbrain_prior_staging_evidence_host",
        tmp_path / "prior_staging_evidence.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
        parsed = mod._parse_utc_z("2026-08-02T09:35:00Z")
        assert isinstance(parsed, datetime)
        assert parsed.tzinfo is timezone.utc or parsed.utcoffset().total_seconds() == 0
    finally:
        sys.modules.pop(spec.name, None)


def test_resolve_entrypoint_loads_under_python39(tmp_path: Path) -> None:
    """Host resolve-rollback-migration.py importlib path works on Python 3.9."""
    py39 = _find_python39()
    if py39 is None:
        pytest.skip("Python 3.9 interpreter not available for host-compat probe")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(PRIOR_PY, bin_dir / "prior_staging_evidence.py")
    shutil.copy2(EVIDENCE_PY, bin_dir / "evidence.py")
    shutil.copy2(
        ROOT / "schemas/staging-deploy-evidence.schema.json",
        bin_dir / "staging-deploy-evidence.schema.json",
    )
    shutil.copy2(RESOLVE_PY, bin_dir / "resolve-rollback-migration.py")
    (bin_dir / "jsonschema.py").write_text(
        'raise ImportError("jsonschema unavailable on host")\n',
        encoding="utf-8",
    )
    deploy_version = tmp_path / "DEPLOY_VERSION"
    deploy_version.write_text(
        json.dumps(
            {
                "release_id": BASELINE_RELEASE,
                "git_sha": SAMPLE_SHA,
                "image_digest": SAMPLE_DIGEST,
                "migration_revision": CANON_REV,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "migration.json"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    proc = subprocess.run(
        [
            str(py39),
            str(bin_dir / "resolve-rollback-migration.py"),
            "--deploy-version",
            str(deploy_version),
            "--release-id",
            BASELINE_RELEASE,
            "--image-digest",
            SAMPLE_DIGEST,
            "--image-repository",
            SAMPLE_REPO,
            "--aws-account-id",
            ACCOUNT,
            "--aws-region",
            REGION,
            "--ec2-instance-id",
            INSTANCE,
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(bin_dir),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["migration_revision"] == CANON_REV
    assert payload["authority"] == "deploy_version"
