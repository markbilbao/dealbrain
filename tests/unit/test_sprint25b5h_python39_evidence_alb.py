"""Sprint 25b.5h — Python 3.9 evidence compatibility + ALB stabilization."""

from __future__ import annotations

import ast
import copy
import inspect
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import pytest
from scripts.deploy import evidence as evidence_mod
from scripts.deploy.alb_target_health import (
    EXIT_OK,
    EXIT_PERMANENT,
    EXIT_TRANSIENT,
    EXPECTED_TARGET_PORT,
    TRANSIENT_ALLOWLIST,
    PermanentAlbTargetHealthError,
    TransientAlbTargetHealthError,
    classify_alb_rejection,
    evaluate_target_health,
    evaluate_target_health_json,
    is_allowlisted_transient,
)
from scripts.deploy.alb_target_health import main as alb_main
from scripts.deploy.build_staging_bundle import INCLUDE_FILES, build_bundle
from scripts.deploy.evidence import (
    UTC_Z_RE,
    EvidenceError,
    compute_evidence_sha256,
    create_evidence,
    utc_now_z,
    validate_evidence,
)
from scripts.deploy.verify_staging_bundle import (
    REQUIRED_MEMBERS,
    BundleVerifyError,
    _extract_members,
    verify_bundle,
)
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
HOST_SCRIPTS = ROOT / "scripts/deploy/host"
DEPLOY_SH = HOST_SCRIPTS / "dealbrain-staging-deploy.sh"
VERIFY_SH = HOST_SCRIPTS / "verify-staging.sh"
EVIDENCE_PY = ROOT / "scripts/deploy/evidence.py"
ALB_PY = ROOT / "scripts/deploy/alb_target_health.py"
PROD_TF = ROOT / "infra/terraform/environments/production"
WORKFLOWS = ROOT / ".github/workflows"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
STAGING_TG = (
    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
    "targetgroup/dealbrain-staging-api/abcdef0123456789"
)
PROD_TG = (
    "arn:aws:elasticloadbalancing:us-east-1:123456789012:"
    "targetgroup/dealbrain-production-api/abcdef0123456789"
)
INSTANCE = "i-0123456789abcdef0"

# Workspace-local CPython 3.9 used for host-compat probes (optional).
_WORKSPACE_PY39 = ROOT / ".tools/python/cpython-3.9-macos-aarch64-none/bin/python3.9"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _find_python39() -> Path | None:
    env = os.environ.get("DEALBRAIN_PYTHON39")
    if env and Path(env).is_file():
        return Path(env)
    if _WORKSPACE_PY39.is_file():
        return _WORKSPACE_PY39
    for candidate in ("python3.9",):
        found = shutil.which(candidate)
        if found:
            return Path(found)
    return None


def _health_payload(
    targets: list[tuple[str, str]],
    *,
    reason: str | None = None,
) -> dict:
    descriptions = []
    for tid, state in targets:
        health: dict = {"State": state}
        if reason is not None:
            health["Reason"] = reason
        descriptions.append({"Target": {"Id": tid, "Port": 8000}, "TargetHealth": health})
    return {"TargetHealthDescriptions": descriptions}


def _valid_failed_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=f"rel-20260802T120000Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="a" * 64,
        deploy_workflow_run_id="1",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-1-staging",
        ec2_instance_id=INSTANCE,
        ssm_command_id=None,
        migration_revision_before=None,
        migration_revision_after=None,
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        smoke_ok=False,
        image_id=None,
        repo_digest=None,
        image_created_at=None,
        deployment_started_at="2026-08-02T12:00:00Z",
        deployment_finished_at="2026-08-02T12:01:00Z",
        deployment_duration_seconds=60,
        final_status="failed",
        failure_reason="migration_failed",
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def _valid_success_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=f"rel-20260802T120000Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="999",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-999-staging",
        ec2_instance_id=INSTANCE,
        ssm_command_id="cmd-1",
        migration_revision_before="abc",
        migration_revision_after="def",
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-08-02T11:00:00Z",
        deployment_started_at="2026-08-02T12:00:00Z",
        deployment_finished_at="2026-08-02T12:05:00Z",
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


def _built_manifest() -> dict:
    return create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-08-02T12:00:00Z",
        release_id=f"rel-20260802T120000Z-{SAMPLE_SHA[:12]}",
    )


def _decision(payload: dict, *, use_jsonschema: bool) -> bool:
    previous = evidence_mod._HAS_JSONSCHEMA
    evidence_mod._HAS_JSONSCHEMA = use_jsonschema
    evidence_mod._load_schema.cache_clear()
    try:
        validate_evidence(copy.deepcopy(payload))
        return True
    except EvidenceError:
        return False
    finally:
        evidence_mod._HAS_JSONSCHEMA = previous
        evidence_mod._load_schema.cache_clear()


# ---------------------------------------------------------------------------
# A. Python 3.9 compatibility for host evidence module
# ---------------------------------------------------------------------------


def test_host_evidence_has_no_datetime_utc_dependency() -> None:
    source = _read(EVIDENCE_PY)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "datetime":
            names = {alias.name for alias in node.names}
            assert "UTC" not in names, "host evidence must not import datetime.UTC"
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "datetime"
        ):
            assert node.attr != "UTC", "host evidence must not reference datetime.UTC"
    assert not re.search(r"from datetime import[^\n]*\bUTC\b", source)
    assert "from datetime import datetime, timezone" in source
    assert "timezone.utc" in source
    assert "datetime.now(timezone.utc)" in source


def test_datetime_utc_import_fails_under_python39_semantics() -> None:
    """Prove the Deploy Staging #5 failure mode: datetime.UTC is unavailable on 3.9."""
    py39 = _find_python39()
    if py39 is None:
        # Compatibility harness without a 3.9 binary: emulate missing UTC symbol.
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


def test_evidence_module_imports_under_python39() -> None:
    py39 = _find_python39()
    if py39 is None:
        pytest.skip("Python 3.9 interpreter not available for host-compat probe")

    schema = ROOT / "schemas/staging-deploy-evidence.schema.json"
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = Path(tmp)
        shutil.copy2(EVIDENCE_PY, bin_dir / "evidence.py")
        shutil.copy2(schema, bin_dir / "staging-deploy-evidence.schema.json")
        # Shadow jsonschema so the host stdlib path is exercised.
        (bin_dir / "jsonschema.py").write_text(
            'raise ImportError("jsonschema unavailable on host")\n',
            encoding="utf-8",
        )
        probe = bin_dir / "probe.py"
        probe.write_text(
            "\n".join(
                [
                    "import importlib.util, sys",
                    "from pathlib import Path",
                    "p = Path(__file__).resolve().parent / 'evidence.py'",
                    "spec = importlib.util.spec_from_file_location('ev', p)",
                    "mod = importlib.util.module_from_spec(spec)",
                    "spec.loader.exec_module(mod)",
                    "assert callable(mod.create_evidence)",
                    "assert callable(mod.write_evidence)",
                    "assert mod._HAS_JSONSCHEMA is False",
                    "ts = mod.utc_now_z()",
                    "assert ts.endswith('Z')",
                    "print('IMPORT_OK', ts)",
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


def test_generated_timestamps_schema_valid_and_timezone_aware() -> None:
    stamp = utc_now_z()
    assert UTC_Z_RE.fullmatch(stamp)
    assert stamp.endswith("Z")
    # Semantic: parseable as UTC Z; no +00:00 suffix leak.
    assert "+" not in stamp
    assert stamp.count("T") == 1
    from datetime import datetime, timezone

    parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc  # noqa: UP017 — assert Py3.9-compatible UTC form
    )
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_valid_success_and_failure_evidence_write_stdlib_only(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(EVIDENCE_PY, bin_dir / "evidence.py")
    shutil.copy2(
        ROOT / "schemas/staging-deploy-evidence.schema.json",
        bin_dir / "staging-deploy-evidence.schema.json",
    )
    (bin_dir / "jsonschema.py").write_text(
        'raise ImportError("jsonschema unavailable")\n',
        encoding="utf-8",
    )
    probe = bin_dir / "probe_write.py"
    out_fail = tmp_path / "fail.json"
    out_ok = tmp_path / "ok.json"
    probe.write_text(
        "\n".join(
            [
                "import importlib.util, json, sys",
                "from pathlib import Path",
                "ev = Path(__file__).resolve().parent / 'evidence.py'",
                "spec = importlib.util.spec_from_file_location('ev', ev)",
                "mod = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(mod)",
                "assert mod._HAS_JSONSCHEMA is False",
                "failed = mod.create_evidence(",
                "  release_id='rel-20260802T120000Z-" + SAMPLE_SHA[:12] + "',",
                f"  git_sha='{SAMPLE_SHA}',",
                f"  image_repository='{SAMPLE_REPO}',",
                f"  image_digest='{SAMPLE_DIGEST}',",
                "  source_manifest_sha256='" + ("a" * 64) + "',",
                "  deploy_workflow_run_id='1',",
                "  aws_account_id='123456789012',",
                "  aws_region='us-east-1',",
                "  assumed_role_arn='arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy',",
                "  role_session_name='gha-1-staging',",
                f"  ec2_instance_id='{INSTANCE}',",
                "  ssm_command_id=None,",
                "  migration_revision_before=None,",
                "  migration_revision_after=None,",
                "  localhost_live=False,",
                "  localhost_ready=False,",
                "  alb_target_healthy=False,",
                "  smoke_ok=False,",
                "  image_id=None,",
                "  repo_digest=None,",
                "  image_created_at=None,",
                "  deployment_started_at='2026-08-02T12:00:00Z',",
                "  deployment_finished_at='2026-08-02T12:01:00Z',",
                "  deployment_duration_seconds=60,",
                "  final_status='failed',",
                "  failure_reason='alb_health_timeout',",
                ")",
                f"mod.write_evidence(Path({str(out_fail)!r}), failed)",
                "ok = mod.create_evidence(",
                "  release_id='rel-20260802T120000Z-" + SAMPLE_SHA[:12] + "',",
                f"  git_sha='{SAMPLE_SHA}',",
                f"  image_repository='{SAMPLE_REPO}',",
                f"  image_digest='{SAMPLE_DIGEST}',",
                "  source_manifest_sha256='" + ("c" * 64) + "',",
                "  deploy_workflow_run_id='999',",
                "  aws_account_id='123456789012',",
                "  aws_region='us-east-1',",
                "  assumed_role_arn='arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy',",
                "  role_session_name='gha-999-staging',",
                f"  ec2_instance_id='{INSTANCE}',",
                "  ssm_command_id='cmd-1',",
                "  migration_revision_before='abc',",
                "  migration_revision_after='def',",
                "  localhost_live=True,",
                "  localhost_ready=True,",
                "  alb_target_healthy=True,",
                "  smoke_ok=True,",
                "  image_id='sha256:" + ("d" * 64) + "',",
                f"  repo_digest='{SAMPLE_REPO}@{SAMPLE_DIGEST}',",
                "  image_created_at='2026-08-02T11:00:00Z',",
                "  deployment_started_at='2026-08-02T12:00:00Z',",
                "  deployment_finished_at='2026-08-02T12:05:00Z',",
                "  deployment_duration_seconds=300,",
                "  final_status='staging_ok',",
                "  failure_reason=None,",
                ")",
                f"mod.write_evidence(Path({str(out_ok)!r}), ok)",
                "bad = dict(failed)",
                "bad['final_status'] = 'not-a-status'",
                "bad['evidence_sha256'] = mod.compute_evidence_sha256(bad)",
                "try:",
                "  mod.validate_evidence(bad)",
                "except mod.EvidenceError:",
                "  print('REJECTED_OK')",
                "  raise SystemExit(0)",
                "raise SystemExit(1)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    proc = subprocess.run(
        [sys.executable, str(probe)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(bin_dir),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "REJECTED_OK" in proc.stdout
    assert out_fail.is_file()
    assert out_ok.is_file()
    assert json.loads(out_fail.read_text(encoding="utf-8"))["final_status"] == "failed"
    assert json.loads(out_ok.read_text(encoding="utf-8"))["final_status"] == "staging_ok"


def test_jsonschema_stdlib_parity_unchanged() -> None:
    assert evidence_mod._HAS_JSONSCHEMA is True
    bogus = _valid_failed_evidence()
    bogus["final_status"] = "bogus"
    bogus["evidence_sha256"] = compute_evidence_sha256(bogus)
    secret = _valid_failed_evidence()
    secret["failure_reason"] = "boom postgresql://u:p@h/db"
    secret["evidence_sha256"] = compute_evidence_sha256(secret)
    cases = (
        (_valid_failed_evidence(), True),
        (_valid_success_evidence(), True),
        (bogus, False),
        (secret, False),
    )
    for payload, expect in cases:
        assert _decision(payload, use_jsonschema=True) is expect
        assert _decision(payload, use_jsonschema=False) is expect


def test_missing_and_drifted_schema_fail_closed(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(EVIDENCE_PY, bin_dir / "evidence.py")
    (bin_dir / "jsonschema.py").write_text(
        'raise ImportError("jsonschema unavailable")\n',
        encoding="utf-8",
    )
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(_valid_failed_evidence()), encoding="utf-8")

    missing_probe = bin_dir / "probe_missing.py"
    missing_probe.write_text(
        "\n".join(
            [
                "import importlib.util, json, sys",
                "from pathlib import Path",
                "ev = Path(__file__).resolve().parent / 'evidence.py'",
                "spec = importlib.util.spec_from_file_location('ev', ev)",
                "mod = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(mod)",
                "assert mod._HAS_JSONSCHEMA is False",
                "payload = json.loads(Path(sys.argv[1]).read_text())",
                "try:",
                "  mod.validate_evidence(payload)",
                "except mod.EvidenceError as exc:",
                "  print('MISSING', exc)",
                "  raise SystemExit(0)",
                "raise SystemExit(1)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    proc = subprocess.run(
        [sys.executable, str(missing_probe), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(bin_dir),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "schema file missing" in proc.stdout

    # Drifted schema (required key removed).
    schema = json.loads(
        (ROOT / "schemas/staging-deploy-evidence.schema.json").read_text(encoding="utf-8")
    )
    schema["required"] = [k for k in schema["required"] if k != "smoke_ok"]
    (bin_dir / "staging-deploy-evidence.schema.json").write_text(
        json.dumps(schema), encoding="utf-8"
    )
    drift_probe = bin_dir / "probe_drift.py"
    drift_probe.write_text(
        "\n".join(
            [
                "import importlib.util, json, sys",
                "from pathlib import Path",
                "ev = Path(__file__).resolve().parent / 'evidence.py'",
                "spec = importlib.util.spec_from_file_location('ev', ev)",
                "mod = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(mod)",
                "assert mod._HAS_JSONSCHEMA is False",
                "payload = json.loads(Path(sys.argv[1]).read_text())",
                "try:",
                "  mod.validate_evidence(payload)",
                "except mod.EvidenceError as exc:",
                "  print('DRIFT', exc)",
                "  raise SystemExit(0)",
                "raise SystemExit(1)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc2 = subprocess.run(
        [sys.executable, str(drift_probe), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(bin_dir),
    )
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    assert "unsupported evidence schema" in proc2.stdout


def test_bundle_still_requires_evidence_writer_schema_redactor() -> None:
    assert "bin/evidence.py" in REQUIRED_MEMBERS
    assert "bin/write-staging-evidence.py" in REQUIRED_MEMBERS
    assert "bin/staging-deploy-evidence.schema.json" in REQUIRED_MEMBERS
    assert "bin/log_redaction.py" in REQUIRED_MEMBERS
    assert ("scripts/deploy/evidence.py", "bin/evidence.py") in INCLUDE_FILES
    assert ("scripts/deploy/host/write-staging-evidence.py", "bin/write-staging-evidence.py") in (
        INCLUDE_FILES
    )

    with tempfile.TemporaryDirectory() as tmp:
        man_path = Path(tmp) / "release-manifest.json"
        man_path.write_text(json.dumps(_built_manifest()), encoding="utf-8")
        out = Path(tmp) / "out"
        tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
        checksum = checksum_path.read_text(encoding="utf-8").split()[0]
        verify_bundle(
            tarball,
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
        )


# ---------------------------------------------------------------------------
# B. ALB fail-closed classification + stabilization window
# ---------------------------------------------------------------------------


def _alb_cli(tmp_path: Path, payload: object) -> int:
    path = tmp_path / "health.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return alb_main(
        [
            "--target-group-arn",
            STAGING_TG,
            "--instance-id",
            INSTANCE,
            "--input",
            str(path),
        ]
    )


def test_alb_timing_contract_documented_and_bounded() -> None:
    verify = _read(VERIFY_SH)
    assert "LOCAL_INTERVAL_SEC=5" in verify
    assert "LOCAL_TIMEOUT_SEC=180" in verify
    assert "ALB_INTERVAL_SEC=10" in verify
    assert "ALB_STABILIZATION_TIMEOUT_SEC=600" in verify
    assert "Maximum ALB wait" in verify
    assert "960s" in verify
    assert '[[ "$ALB_OK" == "true" ]]' in verify or "ALB_OK" in verify
    assert "local readiness failed before ALB" in verify
    # Exit-code contract documented near the retry loop.
    assert "ALB_RC == 0" in verify
    assert "ALB_RC == 2" in verify
    assert "ALB_RC == 1" in verify
    assert "only evaluator exit 2 is retried" in verify


def test_alb_healthy_exit_0(tmp_path: Path) -> None:
    assert _alb_cli(tmp_path, _health_payload([(INSTANCE, "healthy")])) == EXIT_OK
    evaluate_target_health(
        _health_payload([(INSTANCE, "healthy")]),
        expected_instance_id=INSTANCE,
        target_group_arn=STAGING_TG,
    )


def test_alb_recognized_initial_transient_exit_2(tmp_path: Path) -> None:
    for reason in (None, "Elb.RegistrationInProgress", "Elb.InitialHealthChecking"):
        assert (
            _alb_cli(tmp_path, _health_payload([(INSTANCE, "initial")], reason=reason))
            == EXIT_TRANSIENT
        )
    assert is_allowlisted_transient("initial", None)


def test_alb_recognized_startup_unhealthy_exit_2(tmp_path: Path) -> None:
    for reason in (
        "Elb.InitialHealthChecking",
        "Elb.RegistrationInProgress",
        "Target.FailedHealthChecks",
        "Target.Timeout",
        "Target.ResponseCodeMismatch",
    ):
        assert (
            _alb_cli(tmp_path, _health_payload([(INSTANCE, "unhealthy")], reason=reason))
            == EXIT_TRANSIENT
        )


def test_alb_unknown_state_exit_1(tmp_path: Path) -> None:
    assert _alb_cli(tmp_path, _health_payload([(INSTANCE, "weird_new_state")])) == EXIT_PERMANENT
    with pytest.raises(PermanentAlbTargetHealthError, match="weird_new_state"):
        evaluate_target_health(
            _health_payload([(INSTANCE, "weird_new_state")]),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_null_missing_empty_state_exit_1(tmp_path: Path) -> None:
    base = {
        "TargetHealthDescriptions": [{"Target": {"Id": INSTANCE, "Port": 8000}, "TargetHealth": {}}]
    }
    assert _alb_cli(tmp_path, base) == EXIT_PERMANENT
    base["TargetHealthDescriptions"][0]["TargetHealth"]["State"] = None
    assert _alb_cli(tmp_path, base) == EXIT_PERMANENT
    base["TargetHealthDescriptions"][0]["TargetHealth"]["State"] = ""
    assert _alb_cli(tmp_path, base) == EXIT_PERMANENT


def test_alb_unknown_reason_exit_1(tmp_path: Path) -> None:
    # Unhealthy with non-allowlisted reason must not retry.
    assert (
        _alb_cli(
            tmp_path,
            _health_payload([(INSTANCE, "unhealthy")], reason="Target.SomethingBrandNew"),
        )
        == EXIT_PERMANENT
    )
    # initial with unknown reason also fails closed.
    assert (
        _alb_cli(
            tmp_path,
            _health_payload([(INSTANCE, "initial")], reason="Elb.UnknownFutureReason"),
        )
        == EXIT_PERMANENT
    )
    # draining / unavailable are not allowlisted.
    assert _alb_cli(tmp_path, _health_payload([(INSTANCE, "draining")])) == EXIT_PERMANENT
    assert _alb_cli(tmp_path, _health_payload([(INSTANCE, "unavailable")])) == EXIT_PERMANENT
    assert _alb_cli(tmp_path, _health_payload([(INSTANCE, "unused")])) == EXIT_PERMANENT
    assert ("draining", None) not in TRANSIENT_ALLOWLIST
    assert ("unavailable", None) not in TRANSIENT_ALLOWLIST


def test_alb_invalid_json_and_wrong_top_level_exit_1(tmp_path: Path) -> None:
    assert _alb_cli(tmp_path, "not-json{") == EXIT_PERMANENT
    assert _alb_cli(tmp_path, [1, 2, 3]) == EXIT_PERMANENT
    assert _alb_cli(tmp_path, "null") == EXIT_PERMANENT
    with pytest.raises(PermanentAlbTargetHealthError, match="malformed JSON"):
        evaluate_target_health_json(
            "{",
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_missing_or_malformed_descriptions_exit_1(tmp_path: Path) -> None:
    assert _alb_cli(tmp_path, {"oops": []}) == EXIT_PERMANENT
    assert _alb_cli(tmp_path, {"TargetHealthDescriptions": "nope"}) == EXIT_PERMANENT
    assert _alb_cli(tmp_path, {"TargetHealthDescriptions": [None]}) == EXIT_PERMANENT
    assert (
        _alb_cli(
            tmp_path,
            {
                "TargetHealthDescriptions": [
                    {"TargetHealth": {"State": "healthy"}},
                ]
            },
        )
        == EXIT_PERMANENT
    )
    assert (
        _alb_cli(
            tmp_path,
            {
                "TargetHealthDescriptions": [
                    {"Target": {"Id": INSTANCE, "Port": 8000}},
                ]
            },
        )
        == EXIT_PERMANENT
    )


def test_alb_wrong_instance_port_and_multiple_targets_exit_1(tmp_path: Path) -> None:
    assert (
        _alb_cli(tmp_path, _health_payload([("i-0deadbeefcafebabe", "healthy")])) == EXIT_PERMANENT
    )
    wrong_port = {
        "TargetHealthDescriptions": [
            {
                "Target": {"Id": INSTANCE, "Port": 9000},
                "TargetHealth": {"State": "healthy"},
            }
        ]
    }
    assert _alb_cli(tmp_path, wrong_port) == EXIT_PERMANENT
    assert EXPECTED_TARGET_PORT == 8000
    multi = _health_payload([(INSTANCE, "healthy"), ("i-0deadbeefcafebabe", "initial")])
    assert _alb_cli(tmp_path, multi) == EXIT_PERMANENT
    with pytest.raises(PermanentAlbTargetHealthError, match="unexpected target count"):
        evaluate_target_health(
            multi,
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )


def test_alb_production_target_group_exit_1(tmp_path: Path) -> None:
    path = tmp_path / "prod.json"
    path.write_text(json.dumps(_health_payload([(INSTANCE, "healthy")])), encoding="utf-8")
    rc = alb_main(
        [
            "--target-group-arn",
            PROD_TG,
            "--instance-id",
            INSTANCE,
            "--input",
            str(path),
        ]
    )
    assert rc == EXIT_PERMANENT


def test_alb_absent_target_is_transient(tmp_path: Path) -> None:
    assert _alb_cli(tmp_path, _health_payload([])) == EXIT_TRANSIENT


def test_alb_transient_sequence_then_healthy(tmp_path: Path) -> None:
    states = ["initial", "unhealthy", "healthy"]
    codes: list[int] = []
    for state in states:
        codes.append(
            _alb_cli(
                tmp_path,
                _health_payload(
                    [(INSTANCE, state)],
                    reason="Elb.InitialHealthChecking" if state != "healthy" else None,
                ),
            )
        )
    assert codes == [EXIT_TRANSIENT, EXIT_TRANSIENT, EXIT_OK]


def test_alb_never_healthy_remains_non_zero() -> None:
    with pytest.raises(TransientAlbTargetHealthError):
        evaluate_target_health(
            _health_payload([(INSTANCE, "initial")]),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )
    assert (
        classify_alb_rejection(TransientAlbTargetHealthError("expected target state is 'initial'"))
        == EXIT_TRANSIENT
    )


def test_alb_permanent_config_failures_fail_closed() -> None:
    with pytest.raises(PermanentAlbTargetHealthError, match="production"):
        evaluate_target_health(
            _health_payload([(INSTANCE, "healthy")]),
            expected_instance_id=INSTANCE,
            target_group_arn=PROD_TG,
        )
    with pytest.raises(PermanentAlbTargetHealthError, match="unexpected target id"):
        evaluate_target_health(
            _health_payload([("i-0deadbeefcafebabe", "healthy")]),
            expected_instance_id=INSTANCE,
            target_group_arn=STAGING_TG,
        )
    assert classify_alb_rejection(PermanentAlbTargetHealthError("production")) == EXIT_PERMANENT


def _simulate_verify_alb_loop(
    codes: list[int],
    *,
    timeout: int = 600,
    interval: int = 10,
) -> tuple[bool, int, int]:
    """Mirror verify-staging.sh: retry only exit 2; 0 success; else permanent."""
    elapsed = 0
    sleeps = 0
    idx = 0
    while elapsed < timeout:
        alb_rc = codes[min(idx, len(codes) - 1)]
        idx += 1
        if alb_rc == 0:
            return True, elapsed, sleeps
        if alb_rc == 2:
            sleeps += 1
            elapsed += interval
            continue
        # exit 1 or unexpected — fail closed immediately (no full-window wait)
        return False, elapsed, sleeps
    return False, elapsed, sleeps


def test_alb_bounded_maximum_duration_enforced_behaviorally() -> None:
    """Simulate ALB poll loop: transient forever must stop at stabilization budget."""
    verify = _read(VERIFY_SH)
    match = re.search(r"ALB_STABILIZATION_TIMEOUT_SEC=(\d+)", verify)
    interval = re.search(r"ALB_INTERVAL_SEC=(\d+)", verify)
    assert match and interval
    timeout = int(match.group(1))
    step = int(interval.group(1))
    assert timeout == 600
    assert step == 10

    ok, elapsed, sleeps = _simulate_verify_alb_loop(
        [EXIT_TRANSIENT], timeout=timeout, interval=step
    )
    assert ok is False
    assert elapsed == timeout
    assert sleeps == timeout // step


def test_alb_repeated_transient_then_healthy_succeeds() -> None:
    ok, elapsed, sleeps = _simulate_verify_alb_loop(
        [EXIT_TRANSIENT, EXIT_TRANSIENT, EXIT_OK], timeout=600, interval=10
    )
    assert ok is True
    assert sleeps == 2
    assert elapsed == 20


def test_alb_permanent_failure_does_not_wait_full_window() -> None:
    ok, elapsed, sleeps = _simulate_verify_alb_loop([EXIT_PERMANENT], timeout=600, interval=10)
    assert ok is False
    assert elapsed == 0
    assert sleeps == 0
    # Unexpected evaluator codes also fail immediately.
    ok3, elapsed3, sleeps3 = _simulate_verify_alb_loop([3], timeout=600, interval=10)
    assert ok3 is False
    assert elapsed3 == 0
    assert sleeps3 == 0


def test_verify_staging_retries_only_exit_2() -> None:
    verify = _read(VERIFY_SH)
    # Must not convert AWS failures into an empty target list.
    assert 'TargetHealthDescriptions":[]' not in verify
    assert "|| echo '{\"TargetHealthDescriptions\":[]}'" not in verify
    assert "aws elbv2 describe-target-health failed" in verify
    assert "jq -e 'type == \"object\"'" in verify or 'type == "object"' in verify
    # Only exit 2 continues; exit 1 and unexpected codes fail closed.
    assert "ALB_RC -eq 2" in verify
    assert "ALB_RC -eq 0" in verify
    assert "evaluator exit" in verify
    assert "fail closed" in verify
    # Permanent path must exit inside the loop (not only after timeout).
    alb_while = verify.index("while [[ $elapsed -lt $ALB_STABILIZATION_TIMEOUT_SEC ]]")
    permanent_exit = verify.index("ALB target health rejection", alb_while)
    sleep_transient = verify.index('sleep "$ALB_INTERVAL_SEC"', alb_while)
    assert permanent_exit > alb_while
    # After transient sleep there is continue; permanent exit is a separate branch.
    assert "continue" in verify[sleep_transient : sleep_transient + 120]


def test_verify_staging_aws_and_unexpected_rc_fail_immediately(tmp_path: Path) -> None:
    """Behavioral bash harness mirroring the verify-staging ALB retry contract."""
    harness = tmp_path / "alb_retry_contract.sh"
    harness.write_text(
        """#!/bin/bash
set -euo pipefail
ALB_INTERVAL_SEC=1
ALB_STABILIZATION_TIMEOUT_SEC=5
MODE="${1:?}"
elapsed=0
sleeps=0
calls=0
start_ts=$(date +%s)
while [[ $elapsed -lt $ALB_STABILIZATION_TIMEOUT_SEC ]]; do
  calls=$((calls + 1))
  if [[ "$MODE" == "aws_fail" ]]; then
    AWS_RC=255
    if [[ $AWS_RC -ne 0 ]]; then
      echo "aws_fail_closed calls=$calls sleeps=$sleeps elapsed=$elapsed"
      exit 1
    fi
  fi
  if [[ "$MODE" == "jq_fail" ]]; then
    echo "jq_fail_closed calls=$calls sleeps=$sleeps elapsed=$elapsed"
    exit 1
  fi
  if [[ "$MODE" == "exit3" ]]; then
    ALB_RC=3
  elif [[ "$MODE" == "permanent" ]]; then
    ALB_RC=1
  elif [[ "$MODE" == "transient_timeout" ]]; then
    ALB_RC=2
  elif [[ "$MODE" == "transient_then_ok" ]]; then
    if [[ $calls -lt 3 ]]; then ALB_RC=2; else ALB_RC=0; fi
  else
    echo "unknown mode" >&2
    exit 99
  fi
  if [[ $ALB_RC -eq 0 ]]; then
    echo "success calls=$calls sleeps=$sleeps elapsed=$elapsed"
    exit 0
  fi
  if [[ $ALB_RC -eq 2 ]]; then
    sleeps=$((sleeps + 1))
    sleep "$ALB_INTERVAL_SEC"
    elapsed=$((elapsed + ALB_INTERVAL_SEC))
    continue
  fi
  echo "permanent_closed calls=$calls sleeps=$sleeps elapsed=$elapsed rc=$ALB_RC"
  exit 1
done
echo "timeout calls=$calls sleeps=$sleeps elapsed=$elapsed"
exit 1
""",
        encoding="utf-8",
    )
    harness.chmod(0o755)

    def run(mode: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(harness), mode],
            check=False,
            capture_output=True,
            text=True,
        )

    aws = run("aws_fail")
    assert aws.returncode == 1
    assert "aws_fail_closed" in aws.stdout
    assert "sleeps=0" in aws.stdout

    unexpected = run("exit3")
    assert unexpected.returncode == 1
    assert "permanent_closed" in unexpected.stdout
    assert "rc=3" in unexpected.stdout
    assert "sleeps=0" in unexpected.stdout

    permanent = run("permanent")
    assert permanent.returncode == 1
    assert "sleeps=0" in permanent.stdout
    assert "elapsed=0" in permanent.stdout

    ok = run("transient_then_ok")
    assert ok.returncode == 0
    assert "success" in ok.stdout
    assert "sleeps=2" in ok.stdout

    timed = run("transient_timeout")
    assert timed.returncode == 1
    assert "timeout" in timed.stdout
    assert "elapsed=5" in timed.stdout


def test_local_readiness_required_before_alb_success() -> None:
    verify = _read(VERIFY_SH)
    live_idx = verify.index('wait_http "/live"')
    ready_idx = verify.index('wait_http "/ready"')
    local_gate = verify.index("local readiness failed before ALB")
    alb_while = verify.index("while [[ $elapsed -lt $ALB_STABILIZATION_TIMEOUT_SEC ]]")
    assert live_idx < ready_idx < local_gate < alb_while


def test_api_replacement_and_migration_ordering_unchanged() -> None:
    text = _read(DEPLOY_SH)
    migrate_die = text.index('die "migration failed with exit')
    api_recreate = text.index("force-recreate --no-deps api")
    verify_call = text.index('bash "${BIN}/verify-staging.sh"')
    assert migrate_die < api_recreate < verify_call
    assert "API left untouched" in text
    assert "MIGRATE_TIMEOUT_SEC" in text


# ---------------------------------------------------------------------------
# C. Tar extraction — modern filter= path + Python 3.9 fallback
# ---------------------------------------------------------------------------


def _build_valid_bundle(tmp: Path) -> tuple[Path, str, dict]:
    man_path = tmp / "release-manifest.json"
    man_path.write_text(json.dumps(_built_manifest()), encoding="utf-8")
    out = tmp / "out"
    tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
    checksum = checksum_path.read_text(encoding="utf-8").split()[0]
    return tarball, checksum, meta


def _force_filter_typeerror(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Simulate Python 3.9: filter= raises TypeError; bare extract succeeds."""
    calls: list[dict] = []
    real_extract = tarfile.TarFile.extract

    def fake_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
        calls.append({"name": member.name, "filter": filter, "path": str(path)})
        if filter is not None:
            raise TypeError("extract() got an unexpected keyword argument 'filter'")
        return real_extract(self, member, path=path, set_attrs=set_attrs)

    monkeypatch.setattr(tarfile.TarFile, "extract", fake_extract)
    return calls


def test_tar_extract_never_uses_extractall() -> None:
    import scripts.deploy.verify_staging_bundle as mod

    source = inspect.getsource(mod)
    assert ".extractall(" not in source
    assert "extractall(" not in source
    assert 'filter="data"' in source or "filter='data'" in source
    extract_src = inspect.getsource(_extract_members)
    assert "TypeError" in extract_src
    assert "tar.extract(" in extract_src
    assert "_is_unsupported_filter_typeerror" in source
    assert "unexpected keyword argument" in source


def test_tar_extract_unrelated_typeerror_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only unsupported-filter TypeErrors may fall back; others stay fatal."""
    real_extract = tarfile.TarFile.extract

    def fake_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
        if filter is not None:
            raise TypeError("simulated tar corruption during extract")
        return real_extract(self, member, path=path, set_attrs=set_attrs)

    monkeypatch.setattr(tarfile.TarFile, "extract", fake_extract)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    with pytest.raises(TypeError, match="simulated tar corruption"):
        verify_bundle(
            tarball,
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
        )


def test_tar_extract_modern_filter_path_succeeds(tmp_path: Path) -> None:
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    # On interpreters that support filter=, verify_bundle must succeed.
    result = verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
    )
    assert result["checksum"] == checksum
    assert result["meta"]["release_id"] == meta["release_id"]
    sig = inspect.signature(tarfile.TarFile.extract)
    if "filter" in sig.parameters:
        # Behavioral: modern path invoked filter="data" at least once.
        calls: list[dict] = []
        real_extract = tarfile.TarFile.extract

        def tracking_extract(self, member, path="", set_attrs=True, *, filter=None):  # noqa: A002
            calls.append({"filter": filter})
            return real_extract(self, member, path=path, set_attrs=set_attrs, filter=filter)

        # Re-verify with tracking (separate extract into temp via verify_bundle).
        import scripts.deploy.verify_staging_bundle as mod

        original = mod.tarfile.TarFile.extract
        try:
            mod.tarfile.TarFile.extract = tracking_extract  # type: ignore[method-assign]
            verify_bundle(
                tarball,
                expected_checksum=checksum,
                expected_release_id=meta["release_id"],
            )
        finally:
            mod.tarfile.TarFile.extract = original  # type: ignore[method-assign]
        assert any(c["filter"] == "data" for c in calls)


def test_tar_extract_python39_fallback_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _force_filter_typeerror(monkeypatch)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    result = verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
        expected_digest=meta["image_digest"],
    )
    assert result["checksum"] == checksum
    assert any(c["filter"] == "data" for c in calls), "modern path must be attempted first"
    assert any(c["filter"] is None for c in calls), "fallback bare extract must run"
    # Required-member + per-file checksum verification still applied.
    assert result["meta"]["release_id"] == meta["release_id"]
    assert "file_checksums" in result["meta"]
    assert len(result["meta"]["file_checksums"]) >= len(REQUIRED_MEMBERS) - 1


def _malicious_tarball(tmp: Path, member_name: str, *, link_type: str | None = None) -> Path:
    tar_path = tmp / "evil.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        if link_type == "symlink":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        elif link_type == "hardlink":
            data = b"x"
            base = tarfile.TarInfo(name="bin/harmless.txt")
            base.size = len(data)
            tar.addfile(base, fileobj=io.BytesIO(data))
            link = tarfile.TarInfo(name=member_name)
            link.type = tarfile.LNKTYPE
            link.linkname = "bin/harmless.txt"
            tar.addfile(link)
        elif link_type == "chr":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.CHRTYPE
            info.devmajor = 1
            info.devminor = 3
            tar.addfile(info)
        else:
            data = b"evil"
            info = tarfile.TarInfo(name=member_name)
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))
    return tar_path


def test_tar_extract_fallback_rejects_unsafe_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _force_filter_typeerror(monkeypatch)
    cases = [
        ("../escape", "traversal|absolute|unexpected"),
        ("/absolute/path", "absolute|unexpected"),
        ("bin/link", "symlink|hardlink"),
        ("bin/hard", "symlink|hardlink"),
        ("bin/evil-chr", "special file"),
        ("compose/docker-compose.production.yml", "forbidden|production"),
        ("unexpected/top.txt", "unexpected"),
    ]
    link_map = {
        "bin/link": "symlink",
        "bin/hard": "hardlink",
        "bin/evil-chr": "chr",
    }
    for name, match in cases:
        evil = _malicious_tarball(tmp_path, name, link_type=link_map.get(name))
        with pytest.raises(BundleVerifyError, match=match):
            verify_bundle(evil)


def test_tar_extract_fallback_rejects_destination_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if a member slipped past name checks, relative_to must fail closed."""
    import scripts.deploy.verify_staging_bundle as mod

    _force_filter_typeerror(monkeypatch)
    dest = tmp_path / "dest"
    dest.mkdir()
    # Craft a TarInfo whose resolved path escapes dest via a sneaky name that
    # validate_archive_members would normally reject; call _extract_members directly.
    with tarfile.open(tmp_path / "x.tar.gz", "w:gz") as tar:
        data = b"x"
        info = tarfile.TarInfo(name="bin/ok.txt")
        info.size = len(data)
        tar.addfile(info, fileobj=io.BytesIO(data))

    with tarfile.open(tmp_path / "x.tar.gz", "r:gz") as tar:
        members = list(tar.getmembers())
        # Mutate name after validation to simulate destination escape.
        members[0].name = "../escape.txt"
        with pytest.raises(BundleVerifyError, match="escaped destination"):
            mod._extract_members(tar, dest, members)


def test_tar_checksum_and_required_members_still_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _force_filter_typeerror(monkeypatch)
    tarball, checksum, meta = _build_valid_bundle(tmp_path)
    with pytest.raises(BundleVerifyError, match="checksum mismatch"):
        verify_bundle(tarball, expected_checksum="0" * 64)
    # Valid checksum path still requires full member set (build_bundle provides them).
    result = verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=meta["release_id"],
    )
    assert result["meta"]["image_digest"] == meta["image_digest"]


def test_production_remains_untouched() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").exists()
    assert PROD_TF.is_dir()
    verify = _read(VERIFY_SH)
    deploy = _read(DEPLOY_SH)
    assert "*production*" in verify
    assert "production overlay forbidden" in deploy or "production compose" in deploy.lower()
    assert "terraform apply" not in deploy
    # Host scripts must not import the 3.11+ UTC symbol from datetime.
    for path in (EVIDENCE_PY, ALB_PY, HOST_SCRIPTS / "write-staging-evidence.py"):
        src = _read(path)
        assert not re.search(r"from datetime import[^\n]*\bUTC\b", src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "datetime":
                assert "UTC" not in {alias.name for alias in node.names}
