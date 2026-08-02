"""Sprint 25b.5g — Alembic percent-URL escape, secret redaction, evidence load."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from configparser import ConfigParser
from pathlib import Path

import pytest
from app.infrastructure.database.alembic_url import (
    escape_alembic_config_url,
    sanitize_database_url_message,
    set_alembic_sqlalchemy_url,
)
from scripts.deploy import evidence as evidence_mod
from scripts.deploy.build_staging_bundle import INCLUDE_FILES, build_bundle
from scripts.deploy.evidence import (
    REQUIRED_EVIDENCE_KEYS,
    EvidenceError,
    compute_evidence_sha256,
    create_evidence,
    resolve_schema_path,
    validate_evidence,
)
from scripts.deploy.log_redaction import redact_deploy_text
from scripts.deploy.verify_staging_bundle import REQUIRED_MEMBERS, verify_bundle
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
HOST_SCRIPTS = ROOT / "scripts/deploy/host"
DEPLOY_SH = HOST_SCRIPTS / "dealbrain-staging-deploy.sh"
ALEMBIC_ENV = ROOT / "alembic" / "env.py"
PROD_TF = ROOT / "infra/terraform/environments/production"
WORKFLOWS = ROOT / ".github/workflows"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"

# Synthetic credentials for encoding tests — never real secrets.
_PASS_SPECIAL = "p@ss:/%# word?"


def _valid_failed_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="a" * 64,
        deploy_workflow_run_id="1",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-1-staging",
        ec2_instance_id="i-0123456789abcdef0",
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
        deployment_started_at="2026-07-31T12:00:00Z",
        deployment_finished_at="2026-07-31T12:01:00Z",
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
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="999",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-999-staging",
        ec2_instance_id="i-0123456789abcdef0",
        ssm_command_id="cmd-1",
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


def _decision(payload: dict, *, use_jsonschema: bool) -> bool:
    """Return True if validate_evidence accepts the payload on the chosen path."""
    previous = evidence_mod._HAS_JSONSCHEMA
    evidence_mod._HAS_JSONSCHEMA = use_jsonschema
    try:
        validate_evidence(copy.deepcopy(payload))
        return True
    except EvidenceError:
        return False
    finally:
        evidence_mod._HAS_JSONSCHEMA = previous


def _parity_corpus() -> list[tuple[str, dict, bool]]:
    """(name, payload, expect_accept) fixtures for jsonschema/stdlib parity."""
    base_failed = _valid_failed_evidence()
    base_ok = _valid_success_evidence()
    cases: list[tuple[str, dict, bool]] = [
        ("valid_failed", base_failed, True),
        ("valid_success", base_ok, True),
        ("unknown_field_extra_note", _valid_failed_evidence(extra_note="x"), False),
        (
            "localhost_live_yes",
            _valid_failed_evidence(localhost_live="yes"),
            False,
        ),
        (
            "localhost_live_int",
            _valid_failed_evidence(localhost_live=1),
            False,
        ),
        (
            "aws_region_null",
            _valid_failed_evidence(aws_region=None),
            False,
        ),
        (
            "duration_bool",
            _valid_failed_evidence(deployment_duration_seconds=True),
            False,
        ),
        (
            "duration_string",
            _valid_failed_evidence(deployment_duration_seconds="60"),
            False,
        ),
        (
            "invalid_enum",
            _valid_failed_evidence(final_status="ok"),
            False,
        ),
        (
            "invalid_release_id",
            _valid_failed_evidence(release_id="rel-bad"),
            False,
        ),
        (
            "invalid_git_sha",
            _valid_failed_evidence(git_sha="notasha"),
            False,
        ),
        (
            "invalid_account",
            _valid_failed_evidence(aws_account_id="123"),
            False,
        ),
        (
            "secret_bearing_value",
            _valid_failed_evidence(failure_reason="boom postgresql+asyncpg://u:p@h/db"),
            False,
        ),
        (
            "production_value",
            _valid_failed_evidence(role_session_name="gha-production-run"),
            False,
        ),
        (
            "inconsistent_failed_gates",
            _valid_failed_evidence(
                localhost_live=True,
                localhost_ready=True,
                alb_target_healthy=True,
                smoke_ok=True,
            ),
            False,
        ),
    ]
    secret_field = copy.deepcopy(base_failed)
    secret_field["db_password"] = "x"
    secret_field["evidence_sha256"] = compute_evidence_sha256(secret_field)
    cases.append(("secret_like_field", secret_field, False))
    # Missing each required field one at a time.
    for key in REQUIRED_EVIDENCE_KEYS:
        payload = copy.deepcopy(base_failed)
        del payload[key]
        if "evidence_sha256" in payload:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
        cases.append((f"missing_{key}", payload, False))
    return cases


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _built_manifest() -> dict:
    return create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-07-31T12:00:00Z",
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
    )


def _percent_encoded_url(*, password: str = _PASS_SPECIAL) -> str:
    from urllib.parse import quote_plus

    user = quote_plus("db/user@name", safe="")
    pw = quote_plus(password, safe="")
    return f"postgresql+asyncpg://{user}:{pw}@db.example:5432/dealbrain"


# ---------------------------------------------------------------------------
# A. Alembic ConfigParser URL escaping
# ---------------------------------------------------------------------------


def test_escape_alembic_config_url_doubles_percents() -> None:
    url = _percent_encoded_url()
    assert "%" in url
    escaped = escape_alembic_config_url(url)
    assert "%%" in escaped
    assert escaped == url.replace("%", "%%")


def test_percent_encoded_url_survives_configparser_roundtrip() -> None:
    url = _percent_encoded_url()
    parser = ConfigParser()
    parser.add_section("alembic")
    with pytest.raises(ValueError, match="interpolation"):
        parser.set("alembic", "sqlalchemy.url", url)

    parser.set("alembic", "sqlalchemy.url", escape_alembic_config_url(url))
    assert parser.get("alembic", "sqlalchemy.url") == url


def test_set_alembic_sqlalchemy_url_accepts_encoded_credentials() -> None:
    from urllib.parse import quote_plus

    password = "a%b@c:d/e?f#g h"
    url = _percent_encoded_url(password=password)
    encoded = quote_plus(password, safe="")
    assert "%" in encoded
    for fragment in ("%25", "%40", "%3A", "%2F", "%3F", "%23", "+"):
        assert fragment in encoded
    assert encoded in url

    class _Cfg:
        def __init__(self) -> None:
            self._p = ConfigParser()
            self._p.add_section("alembic")

        def set_main_option(self, key: str, value: str) -> None:
            self._p.set("alembic", key, value)

        def get_main_option(self, key: str) -> str:
            return self._p.get("alembic", key)

    cfg = _Cfg()
    set_alembic_sqlalchemy_url(cfg, url)
    assert cfg.get_main_option("sqlalchemy.url") == url


def test_set_alembic_sqlalchemy_url_sanitizes_value_error() -> None:
    class _Boom:
        def set_main_option(self, key: str, value: str) -> None:
            raise ValueError(f"invalid interpolation syntax in {value!r}")

    secret_url = _percent_encoded_url()
    with pytest.raises(ValueError) as excinfo:
        set_alembic_sqlalchemy_url(_Boom(), secret_url)
    msg = str(excinfo.value)
    assert "credentials redacted" in msg
    assert secret_url not in msg
    assert _PASS_SPECIAL not in msg
    assert "p%40ss" not in msg


def test_alembic_env_uses_helper_not_raw_set_main_option() -> None:
    text = _read(ALEMBIC_ENV)
    assert "set_alembic_sqlalchemy_url" in text
    assert "escape_alembic_config_url" in text or "set_alembic_sqlalchemy_url" in text
    assert 'config.set_main_option("sqlalchemy.url", settings.database_url)' not in text


# ---------------------------------------------------------------------------
# B. Structural secret redaction
# ---------------------------------------------------------------------------


def test_sanitize_database_url_message_redacts_urls_and_assignments() -> None:
    url = _percent_encoded_url()
    raw = f"ValueError: invalid interpolation syntax in '{url}'\nDATABASE_URL={url}"
    cleaned = sanitize_database_url_message(raw)
    assert url not in cleaned
    assert _PASS_SPECIAL not in cleaned
    assert "postgresql+asyncpg://" not in cleaned
    assert "***REDACTED_DATABASE_URL***" in cleaned
    assert "DATABASE_URL=***REDACTED***" in cleaned


def test_log_redaction_is_structural_not_password_specific() -> None:
    unknown_pw = "Zx9!not-a-known-fixture-password%40end"
    from urllib.parse import quote_plus

    url = f"postgresql+asyncpg://u:{quote_plus(unknown_pw, safe='')}@h:5432/db"
    text = f"migrate boom {url} password={unknown_pw}"
    out = redact_deploy_text(text)
    assert unknown_pw not in out
    assert url not in out
    assert "***REDACTED_DATABASE_URL***" in out
    assert "password=***REDACTED***" in out


def test_deploy_script_redacts_migrate_output_and_leaves_api_untouched() -> None:
    text = _read(DEPLOY_SH)
    assert "log_redaction.py" in text
    assert "MIGRATE_LOG" in text
    assert "API left untouched" in text
    assert "force-recreate --no-deps api" in text
    # API recreate must appear after migration success gate.
    migrate_idx = text.index("migration_failed")
    api_idx = text.index("force-recreate --no-deps api")
    assert migrate_idx < api_idx


def test_failure_reason_is_sanitized_token_not_url() -> None:
    text = _read(DEPLOY_SH)
    assert 'FAILURE_REASON="migration_failed"' in text
    assert "DATABASE_URL" not in text.split("FAILURE_REASON=")[1].split("\n")[0]


# ---------------------------------------------------------------------------
# C. Canonical evidence module (bundle layout, no sys.path hacks)
# ---------------------------------------------------------------------------


def test_evidence_schema_resolves_bundle_sibling(tmp_path: Path) -> None:
    schema_src = ROOT / "schemas" / "staging-deploy-evidence.schema.json"
    sibling = tmp_path / "staging-deploy-evidence.schema.json"
    shutil.copy2(schema_src, sibling)
    # Pretend module lives in the temp bin dir.
    fake_module = tmp_path / "evidence.py"
    fake_module.write_text("# placeholder\n", encoding="utf-8")
    resolved = resolve_schema_path(fake_module)
    assert resolved == sibling


def test_write_staging_evidence_loads_sibling_without_sys_path_mutation(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(ROOT / "scripts/deploy/evidence.py", bin_dir / "evidence.py")
    shutil.copy2(
        ROOT / "schemas/staging-deploy-evidence.schema.json",
        bin_dir / "staging-deploy-evidence.schema.json",
    )
    shutil.copy2(
        HOST_SCRIPTS / "write-staging-evidence.py",
        bin_dir / "write-staging-evidence.py",
    )
    out = tmp_path / "evidence.json"
    env = {
        k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "DEALBRAIN_FAILURE_REASON"}
    }
    env.update(
        {
            "PYTHONPATH": "",
            "DEALBRAIN_EVIDENCE_OUT": str(out),
            "DEALBRAIN_RELEASE_ID": f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
            "DEALBRAIN_GIT_SHA": SAMPLE_SHA,
            "DEALBRAIN_IMAGE_REPOSITORY": SAMPLE_REPO,
            "DEALBRAIN_IMAGE_DIGEST": SAMPLE_DIGEST,
            "DEALBRAIN_DEPLOY_RUN_ID": "42",
            "DEALBRAIN_STARTED_AT": "2026-07-31T12:00:00Z",
            "DEALBRAIN_FINISHED_AT": "2026-07-31T12:01:00Z",
            "DEALBRAIN_DURATION": "60",
            "DEALBRAIN_FINAL_STATUS": "failed",
            "DEALBRAIN_FAILURE_REASON": "migration_failed",
            "DEALBRAIN_INSTANCE_ID": "i-0123456789abcdef0",
            "DEALBRAIN_AWS_ACCOUNT_ID": "123456789012",
            "DEALBRAIN_REGION": "us-east-1",
            "DEALBRAIN_SOURCE_MANIFEST_SHA256": "a" * 64,
        }
    )
    # Isolate from editable-install .pth by clearing path to site packages' dealbrain?
    # importlib sibling load does not need the package; only jsonschema (optional).
    proc = subprocess.run(
        [sys.executable, str(bin_dir / "write-staging-evidence.py")],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    payload = out.read_text(encoding="utf-8")
    assert "migration_failed" in payload
    assert "DATABASE_URL" not in payload
    assert _PASS_SPECIAL not in payload
    assert "postgresql+asyncpg://" not in payload


def test_write_staging_evidence_uses_importlib_not_sys_path_insert() -> None:
    text = _read(HOST_SCRIPTS / "write-staging-evidence.py")
    assert "importlib.util.spec_from_file_location" in text
    assert "sys.path.insert" not in text
    assert "os.environ" not in text or 'os.environ["PYTHONPATH"]' not in text
    assert "os.environ.setdefault" not in text


def test_bundle_requires_evidence_writer_schema_and_redactor() -> None:
    assert "bin/write-staging-evidence.py" in REQUIRED_MEMBERS
    assert "bin/staging-deploy-evidence.schema.json" in REQUIRED_MEMBERS
    assert "bin/log_redaction.py" in REQUIRED_MEMBERS
    assert ("scripts/deploy/log_redaction.py", "bin/log_redaction.py") in INCLUDE_FILES


def test_bundle_includes_evidence_contract_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        man_path = Path(tmp) / "release-manifest.json"
        import json

        man_path.write_text(json.dumps(_built_manifest()), encoding="utf-8")
        out = Path(tmp) / "out"
        tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
        checksum = checksum_path.read_text(encoding="utf-8").split()[0]
        verify_bundle(
            tarball,
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
        )
        import tarfile

        with tarfile.open(tarball, "r:gz") as archive:
            names = set(archive.getnames())
        assert "bin/evidence.py" in names
        assert "bin/write-staging-evidence.py" in names
        assert "bin/staging-deploy-evidence.schema.json" in names
        assert "bin/log_redaction.py" in names


def test_failed_evidence_has_sanitized_reason_and_no_credentials() -> None:
    from scripts.deploy.evidence import EvidenceError, validate_evidence

    payload = create_evidence(
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="a" * 64,
        deploy_workflow_run_id="1",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/x",
        role_session_name="gha-1-staging",
        ec2_instance_id="i-0123456789abcdef0",
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
        deployment_started_at="2026-07-31T12:00:00Z",
        deployment_finished_at="2026-07-31T12:01:00Z",
        deployment_duration_seconds=60,
        final_status="failed",
        failure_reason="migration_failed",
    )
    assert payload["failure_reason"] == "migration_failed"
    dumped = str(payload)
    assert "DATABASE_URL" not in dumped
    assert "postgresql" not in dumped.lower()
    assert _PASS_SPECIAL not in dumped

    poisoned = dict(payload)
    poisoned["database_url"] = _percent_encoded_url()
    with pytest.raises(EvidenceError, match="secret-like"):
        validate_evidence(poisoned)


# ---------------------------------------------------------------------------
# D. Deployment safety / production isolation
# ---------------------------------------------------------------------------


def test_no_production_workflow_or_compose_in_staging_paths() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").exists()
    text = _read(DEPLOY_SH)
    assert "docker-compose.production.yml" in text  # forbidden check
    assert "production overlay forbidden" in text or "production compose" in text.lower()
    assert PROD_TF.is_dir()
    # Staging deploy must not reference production env apply.
    assert "terraform apply" not in text


def test_digest_only_image_and_release_id_checks_remain() -> None:
    text = _read(DEPLOY_SH)
    assert "sha256:" in text
    assert "mutable tag" in text.lower() or "mutable tag or digest" in text
    assert re.search(r"rel-\[0-9\]\{8\}T\[0-9\]\{6\}Z", text)
    assert "compose up -d --force-recreate --no-deps api" in text


def test_assemble_encoding_still_covers_special_password_chars() -> None:
    path = HOST_SCRIPTS / "assemble-runtime-env.py"
    spec = importlib.util.spec_from_file_location("assemble_25b5g", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from urllib.parse import quote_plus, unquote_plus

    password = "p% @:/?#x"
    url = mod.build_database_url(
        username="u/n",
        password=password,
        host="db.example",
        port=5432,
        database="dealbrain",
    )
    assert quote_plus(password, safe="") in url
    # Driver-facing URL keeps single-percent encoding (not ConfigParser-escaped).
    assert "%%" not in url
    # Round-trip decode of password segment recovers original.
    userinfo = url.split("://", 1)[1].split("@", 1)[0]
    pw_enc = userinfo.split(":", 1)[1]
    assert unquote_plus(pw_enc) == password


# ---------------------------------------------------------------------------
# E. Stdlib evidence schema fallback (no jsonschema) + parity
# ---------------------------------------------------------------------------


def test_stdlib_fallback_rejects_unknown_missing_and_wrong_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(evidence_mod, "_HAS_JSONSCHEMA", False)
    assert evidence_mod._HAS_JSONSCHEMA is False

    validate_evidence(_valid_failed_evidence())
    validate_evidence(_valid_success_evidence())

    with pytest.raises(EvidenceError, match="additional properties"):
        validate_evidence(_valid_failed_evidence(extra_note="x"))
    with pytest.raises(EvidenceError, match="missing required"):
        payload = _valid_failed_evidence()
        del payload["aws_account_id"]
        validate_evidence(payload)
    with pytest.raises(EvidenceError, match="localhost_live"):
        validate_evidence(_valid_failed_evidence(localhost_live="yes"))

    for key in REQUIRED_EVIDENCE_KEYS:
        payload = _valid_failed_evidence()
        del payload[key]
        with pytest.raises(EvidenceError):
            validate_evidence(payload)

    with pytest.raises(EvidenceError, match="type"):
        validate_evidence(_valid_failed_evidence(localhost_live=1))
    with pytest.raises(EvidenceError, match="type"):
        validate_evidence(_valid_failed_evidence(deployment_duration_seconds="60"))
    with pytest.raises(EvidenceError, match="type"):
        validate_evidence(_valid_failed_evidence(aws_region=None))
    with pytest.raises(EvidenceError, match="enum"):
        validate_evidence(_valid_failed_evidence(final_status="ok"))
    with pytest.raises(EvidenceError, match="pattern"):
        validate_evidence(_valid_failed_evidence(git_sha="zzzz"))
    with pytest.raises(EvidenceError, match="secret-like"):
        payload = _valid_failed_evidence()
        payload["api_token"] = "x"
        payload["evidence_sha256"] = compute_evidence_sha256(payload)
        validate_evidence(payload)
    with pytest.raises(EvidenceError, match="secret-bearing"):
        validate_evidence(_valid_failed_evidence(failure_reason="postgresql://u:p@h/db"))
    with pytest.raises(EvidenceError, match="production"):
        validate_evidence(_valid_failed_evidence(role_session_name="env-production"))


def test_jsonschema_and_stdlib_parity_corpus() -> None:
    assert evidence_mod._HAS_JSONSCHEMA is True
    for name, payload, expect_accept in _parity_corpus():
        js = _decision(payload, use_jsonschema=True)
        std = _decision(payload, use_jsonschema=False)
        assert js == std == expect_accept, (
            f"parity mismatch for {name}: jsonschema={js} stdlib={std} expected={expect_accept}"
        )


def test_subprocess_jsonschema_import_fails_rejects_invalid_evidence(
    tmp_path: Path,
) -> None:
    """Force ImportError for jsonschema via a shadowing module on sys.path[0]."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(ROOT / "scripts/deploy/evidence.py", bin_dir / "evidence.py")
    shutil.copy2(
        ROOT / "schemas/staging-deploy-evidence.schema.json",
        bin_dir / "staging-deploy-evidence.schema.json",
    )
    # Shadow jsonschema so the host-like ImportError path is taken.
    (bin_dir / "jsonschema.py").write_text(
        'raise ImportError("jsonschema unavailable in stdlib harness")\n',
        encoding="utf-8",
    )
    payload = _valid_failed_evidence(extra_note="should-fail")
    probe = bin_dir / "probe_validate.py"
    probe.write_text(
        "\n".join(
            [
                "import json, sys",
                "from pathlib import Path",
                "import importlib.util",
                "ev_path = Path(__file__).resolve().parent / 'evidence.py'",
                "spec = importlib.util.spec_from_file_location('ev', ev_path)",
                "mod = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(mod)",
                "assert mod._HAS_JSONSCHEMA is False, 'expected stdlib path'",
                "payload = json.loads(Path(sys.argv[1]).read_text())",
                "try:",
                "    mod.validate_evidence(payload)",
                "except mod.EvidenceError as exc:",
                "    print('REJECTED', exc)",
                "    raise SystemExit(2)",
                "print('ACCEPTED')",
                "raise SystemExit(0)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payload_path = tmp_path / "bad.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = ""
    proc = subprocess.run(
        [sys.executable, str(probe), str(payload_path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "REJECTED" in proc.stdout


def test_write_staging_evidence_stdlib_only_subprocess(tmp_path: Path) -> None:
    """Bundle-style writer with no jsonschema and no PYTHONPATH mutation."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(ROOT / "scripts/deploy/evidence.py", bin_dir / "evidence.py")
    shutil.copy2(
        ROOT / "schemas/staging-deploy-evidence.schema.json",
        bin_dir / "staging-deploy-evidence.schema.json",
    )
    shutil.copy2(
        HOST_SCRIPTS / "write-staging-evidence.py",
        bin_dir / "write-staging-evidence.py",
    )
    (bin_dir / "jsonschema.py").write_text(
        'raise ImportError("jsonschema unavailable in stdlib harness")\n',
        encoding="utf-8",
    )
    out = tmp_path / "evidence.json"
    env = {
        k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "DEALBRAIN_FAILURE_REASON"}
    }
    env.update(
        {
            "PYTHONPATH": "",
            "DEALBRAIN_EVIDENCE_OUT": str(out),
            "DEALBRAIN_RELEASE_ID": f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
            "DEALBRAIN_GIT_SHA": SAMPLE_SHA,
            "DEALBRAIN_IMAGE_REPOSITORY": SAMPLE_REPO,
            "DEALBRAIN_IMAGE_DIGEST": SAMPLE_DIGEST,
            "DEALBRAIN_DEPLOY_RUN_ID": "42",
            "DEALBRAIN_STARTED_AT": "2026-07-31T12:00:00Z",
            "DEALBRAIN_FINISHED_AT": "2026-07-31T12:01:00Z",
            "DEALBRAIN_DURATION": "60",
            "DEALBRAIN_FINAL_STATUS": "failed",
            "DEALBRAIN_FAILURE_REASON": "migration_failed",
            "DEALBRAIN_INSTANCE_ID": "i-0123456789abcdef0",
            "DEALBRAIN_AWS_ACCOUNT_ID": "123456789012",
            "DEALBRAIN_REGION": "us-east-1",
            "DEALBRAIN_SOURCE_MANIFEST_SHA256": "a" * 64,
        }
    )
    proc = subprocess.run(
        [sys.executable, str(bin_dir / "write-staging-evidence.py")],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["final_status"] == "failed"
    assert written["failure_reason"] == "migration_failed"
    assert "extra_note" not in written


# ---------------------------------------------------------------------------
# F. MIGRATE_LOG EXIT cleanup + failure-status preservation
# ---------------------------------------------------------------------------


def test_deploy_script_cleans_migrate_log_on_exit() -> None:
    text = _read(DEPLOY_SH)
    assert 'MIGRATE_LOG=""' in text
    on_exit = text.split("on_exit() {", 1)[1].split("trap on_exit EXIT", 1)[0]
    assert "MIGRATE_LOG:-" in on_exit or "${MIGRATE_LOG" in on_exit
    assert "rm -f" in on_exit
    # Success path clears the variable so EXIT is idempotent.
    assert re.search(r'rm -f -- "\$MIGRATE_LOG"\s*\nMIGRATE_LOG=""', text)


def test_migrate_log_cleanup_preserves_failure_status(tmp_path: Path) -> None:
    log_path = tmp_path / "migrate.log"
    script = tmp_path / "cleanup_status.sh"
    script.write_text(
        f"""#!/bin/bash
set -euo pipefail
MIGRATE_LOG=""
on_exit() {{
  local code=$?
  if [[ -n "${{MIGRATE_LOG:-}}" ]]; then
    rm -f -- "$MIGRATE_LOG" || true
    MIGRATE_LOG=""
  fi
  exit "$code"
}}
trap on_exit EXIT
MIGRATE_LOG="{log_path}"
printf 'postgresql://u:p@h/db\\n' >"$MIGRATE_LOG"
MIGRATE_RC=7
# Simulate redaction-then-clear omitted (crash before rm) — EXIT must scrub + keep status.
exit "$MIGRATE_RC"
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["bash", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 7
    assert not log_path.exists()


def test_migrate_log_cleanup_handles_unset_and_does_not_promote_success(
    tmp_path: Path,
) -> None:
    script = tmp_path / "cleanup_unset.sh"
    script.write_text(
        """#!/bin/bash
set -euo pipefail
# Unset MIGRATE_LOG — cleanup must not throw or flip status.
on_exit() {
  local code=$?
  if [[ -n "${MIGRATE_LOG:-}" ]]; then
    rm -f -- "$MIGRATE_LOG" || true
    MIGRATE_LOG=""
  fi
  exit "$code"
}
trap on_exit EXIT
false
""",
        encoding="utf-8",
    )
    proc = subprocess.run(["bash", str(script)], check=False, capture_output=True, text=True)
    assert proc.returncode == 1


# ---------------------------------------------------------------------------
# G. Alembic exception-chain / traceback redaction
# ---------------------------------------------------------------------------


def test_sanitized_alembic_exception_suppresses_cause_and_traceback() -> None:
    class _Boom:
        def set_main_option(self, key: str, value: str) -> None:
            raise ValueError(f"invalid interpolation syntax in {value!r}")

    secret_url = _percent_encoded_url()
    with pytest.raises(ValueError) as excinfo:
        set_alembic_sqlalchemy_url(_Boom(), secret_url)

    err = excinfo.value
    assert err.__cause__ is None
    assert getattr(err, "__suppress_context__", False) is True
    assert secret_url not in str(err)
    assert _PASS_SPECIAL not in str(err)

    formatted = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    assert secret_url not in formatted
    assert _PASS_SPECIAL not in formatted
    assert "postgresql+asyncpg://" not in formatted
    assert "credentials redacted" in formatted


def test_dangerous_percent_chars_round_trip_via_configparser() -> None:
    from urllib.parse import quote_plus, unquote_plus

    password = "a%b@c:d/e?f#g h"
    url = _percent_encoded_url(password=password)
    parser = ConfigParser()
    parser.add_section("alembic")
    parser.set("alembic", "sqlalchemy.url", escape_alembic_config_url(url))
    restored = parser.get("alembic", "sqlalchemy.url")
    assert restored == url
    assert "%%" not in restored
    userinfo = restored.split("://", 1)[1].split("@", 1)[0]
    pw_enc = userinfo.split(":", 1)[1]
    assert unquote_plus(pw_enc) == password
    assert quote_plus(password, safe="") == pw_enc
