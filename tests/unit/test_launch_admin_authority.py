"""Launch-admin authority is external in staging and production.

The published local bearer is development-only. It is not a staging or
production credential, and it is not APP_SECRET_KEY.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings, settings
from app.core.dependencies import get_db
from app.core.validation import exportable_settings, run_startup_validation, validate_settings
from app.domain.exceptions import ConfigurationValidationError, LaunchAuthorizationError
from app.launch.internal_auth import (
    launch_admin_token_is_acceptable,
    require_internal_launch_admin,
)
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parents[2]
ASSEMBLE = ROOT / "scripts/deploy/host/assemble-runtime-env.py"
AUTH_SOURCE = ROOT / "app/launch/internal_auth.py"

LOCAL_DEVELOPMENT_BEARER = "demo-token-internal-admin"
INJECTED = "injected-launch-admin-authority-32chars"
APP_SECRET = "prod-ops-secret-key-value-32chars!!"
STRONG_DB = "postgresql+asyncpg://dealbrain:Str0ngProdPass!99@rds.example:5432/dealbrain"
PLACEHOLDER = "CHANGE_ME_UNIQUE_LAUNCH_ADMIN_VALUE_32CHARS"
SHORT_TOKEN = "unique-bad-token"


def _load_assemble():
    spec = importlib.util.spec_from_file_location("assemble_runtime_env_launch_admin", ASSEMBLE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shared_settings(environment: str, **overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "APP_ENV": environment,
        "APP_DEBUG": "false",
        "APP_LOG_LEVEL": "INFO",
        "DATABASE_URL": STRONG_DB,
        "APP_SECRET_KEY": APP_SECRET,
        "CORS_ORIGINS": "https://piqsavi.com",
        "TRUSTED_HOSTS": "piqsavi.com",
        "LAUNCH_STRICT_STARTUP": "true" if environment == "production" else "false",
        "LAUNCH_READINESS_ENABLED": "true",
        "LAUNCH_ADMIN_TOKEN": INJECTED,
        "STRUCTURED_LOGGING_ENABLED": "true",
        "DEMO_LAUNCHER_ENABLED": "false",
        "ALLOW_DEMO_RESET_TOKENS": "false",
        "SEED_DEMO_DATA": "false",
        "PRICE_HISTORY_SEED_DEMO_MOCK": "false",
        "PERSISTENCE_BACKEND": "sqlalchemy",
        "USER_PLATFORM_BACKEND": "sqlalchemy",
        "MARKETPLACE_DATA_BACKEND": "sqlalchemy",
        "ALERTS_BACKEND": "sqlalchemy",
        "NOTIFICATIONS_BACKEND": "sqlalchemy",
        "AFFILIATE_BACKEND": "sqlalchemy",
        "MERCHANT_BACKEND": "sqlalchemy",
        "TRANSACTIONAL_EMAIL_PROVIDER": "resend",
        "RESEND_API_KEY": "re_launch_admin_test_key_not_real",
        "TRANSACTIONAL_EMAIL_FROM": "no-reply@piqsavi.com",
        "TRANSACTIONAL_EMAIL_FROM_NAME": "PiqSavi",
        "PUBLIC_APP_BASE_URL": "https://piqsavi.com",
        "TRUSTED_PROXY_CIDRS": "10.20.0.0/24,172.16.0.0/12",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _development_settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "_env_file": None,
        "APP_ENV": "development",
        "LAUNCH_READINESS_ENABLED": "true",
        "LAUNCH_ADMIN_TOKEN": "",
        "DATABASE_URL": "postgresql+asyncpg://dealbrain:dealbrain@localhost:5432/dealbrain",
        "CORS_ORIGINS": "http://localhost:8000",
    }
    payload.update(overrides)
    return Settings(**payload)  # type: ignore[arg-type]


def _bearer(token: str) -> str:
    return f"Bearer {token}"


def _client() -> TestClient:
    app = create_app()
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_source_has_no_committed_launch_admin_credential_constant() -> None:
    text = AUTH_SOURCE.read_text(encoding="utf-8")
    assert "INTERNAL_LAUNCH_ADMIN_TOKEN" not in text
    assert "cfg.app_secret_key" not in text
    assert ".app_secret_key" not in text
    assert '_LOCAL_DEVELOPMENT_GATE = "demo-token-internal-admin"' in text


def test_development_demo_bearer_works_only_when_unconfigured() -> None:
    development = _development_settings()
    require_internal_launch_admin(_bearer(LOCAL_DEVELOPMENT_BEARER), development)
    with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
        require_internal_launch_admin(_bearer("wrong-bearer"), development)
    with pytest.raises(LaunchAuthorizationError, match="Admin bearer token required"):
        require_internal_launch_admin(None, development)
    with pytest.raises(LaunchAuthorizationError, match="Admin bearer token required"):
        require_internal_launch_admin("Bearer ", development)

    configured = _development_settings(LAUNCH_ADMIN_TOKEN=INJECTED)
    require_internal_launch_admin(_bearer(INJECTED), configured)
    with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
        require_internal_launch_admin(_bearer(LOCAL_DEVELOPMENT_BEARER), configured)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_shared_environments_reject_demo_missing_and_placeholder(environment: str) -> None:
    for token in ("", LOCAL_DEVELOPMENT_BEARER, PLACEHOLDER, SHORT_TOKEN):
        cfg = _shared_settings(environment, LAUNCH_ADMIN_TOKEN=token)
        result = validate_settings(cfg)
        assert result.ok is False
        assert any(error.startswith("LAUNCH_ADMIN_TOKEN") for error in result.errors)
        joined = " ".join(result.errors)
        if token:
            assert token not in joined
        assert LOCAL_DEVELOPMENT_BEARER not in joined
        assert INJECTED not in joined
        with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
            require_internal_launch_admin(_bearer(LOCAL_DEVELOPMENT_BEARER), cfg)
        with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
            require_internal_launch_admin(_bearer(token or "present"), cfg)
        with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
            require_internal_launch_admin(_bearer(INJECTED), cfg)
        with pytest.raises(LaunchAuthorizationError, match="Admin bearer token required"):
            require_internal_launch_admin(None, cfg)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_injected_authority_succeeds_and_wrong_bearer_fails(environment: str) -> None:
    cfg = _shared_settings(environment)
    result = validate_settings(cfg)
    assert result.ok is True, result.errors
    require_internal_launch_admin(_bearer(INJECTED), cfg)
    with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
        require_internal_launch_admin(_bearer(LOCAL_DEVELOPMENT_BEARER), cfg)
    with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
        require_internal_launch_admin(_bearer(APP_SECRET), cfg)
    with pytest.raises(LaunchAuthorizationError, match="Internal admin token required"):
        require_internal_launch_admin(_bearer("wrong-bearer-value"), cfg)
    assert launch_admin_token_is_acceptable(INJECTED) is True
    assert launch_admin_token_is_acceptable(LOCAL_DEVELOPMENT_BEARER) is False
    assert launch_admin_token_is_acceptable(PLACEHOLDER) is False
    assert launch_admin_token_is_acceptable("") is False


def test_disabled_surface_allows_missing_token_and_rejects_demo_at_startup() -> None:
    missing = _shared_settings(
        "production",
        LAUNCH_READINESS_ENABLED="false",
        LAUNCH_ADMIN_TOKEN="",
    )
    assert validate_settings(missing).ok is True
    demo = _shared_settings(
        "staging",
        LAUNCH_READINESS_ENABLED="false",
        LAUNCH_ADMIN_TOKEN=LOCAL_DEVELOPMENT_BEARER,
    )
    result = validate_settings(demo)
    assert result.ok is False
    assert LOCAL_DEVELOPMENT_BEARER not in " ".join(result.errors)


def test_staging_missing_authority_fails_startup_when_strict_is_false() -> None:
    cfg = _shared_settings("staging", LAUNCH_ADMIN_TOKEN="", LAUNCH_STRICT_STARTUP="false")
    with pytest.raises(ConfigurationValidationError) as exc_info:
        run_startup_validation(cfg)
    message = str(exc_info.value)
    assert "LAUNCH_ADMIN_TOKEN" in message
    assert LOCAL_DEVELOPMENT_BEARER not in message
    assert INJECTED not in message


def test_staging_email_findings_stay_nonfatal_when_launch_admin_is_not_required() -> None:
    cfg = _shared_settings(
        "staging",
        LAUNCH_STRICT_STARTUP="false",
        LAUNCH_READINESS_ENABLED="false",
        LAUNCH_ADMIN_TOKEN="",
        TRANSACTIONAL_EMAIL_PROVIDER="null",
        RESEND_API_KEY="",
    )
    result = run_startup_validation(cfg)
    assert result.ok is False
    assert any("TRANSACTIONAL_EMAIL_PROVIDER" in error for error in result.errors)


def test_production_startup_rejects_demo_without_echoing_it() -> None:
    cfg = _shared_settings("production", LAUNCH_ADMIN_TOKEN=LOCAL_DEVELOPMENT_BEARER)
    with pytest.raises(ConfigurationValidationError) as exc_info:
        run_startup_validation(cfg)
    message = str(exc_info.value)
    assert "LAUNCH_ADMIN_TOKEN" in message
    assert LOCAL_DEVELOPMENT_BEARER not in message
    assert APP_SECRET not in message


def test_export_redacts_launch_admin_token() -> None:
    cfg = _shared_settings("production")
    payload = exportable_settings(cfg)
    assert payload["launch_admin_token"] == "***REDACTED***"
    assert INJECTED not in str(payload)
    assert LOCAL_DEVELOPMENT_BEARER not in str(payload)


def test_sensitive_routes_reject_the_old_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "launch_readiness_enabled", True)
    monkeypatch.setattr(settings, "launch_admin_token", INJECTED)

    public = client.get("/api/v1/launch/meta")
    assert public.status_code == 200
    assert INJECTED not in public.text
    assert LOCAL_DEVELOPMENT_BEARER not in public.text

    missing = client.post("/api/v1/launch/config/export")
    assert missing.status_code == 401
    wrong = client.post(
        "/api/v1/launch/config/export",
        headers={"Authorization": _bearer("wrong-bearer")},
    )
    assert wrong.status_code == 401
    old = client.post(
        "/api/v1/launch/config/export",
        headers={"Authorization": _bearer(LOCAL_DEVELOPMENT_BEARER)},
    )
    assert old.status_code == 401
    assert LOCAL_DEVELOPMENT_BEARER not in old.text
    assert INJECTED not in old.text

    learning = client.get(
        "/api/v1/launch/product-learning",
        headers={"Authorization": _bearer(LOCAL_DEVELOPMENT_BEARER)},
    )
    assert learning.status_code == 401
    feedback = client.get(
        "/api/v1/launch/product-feedback",
        headers={"Authorization": _bearer(LOCAL_DEVELOPMENT_BEARER)},
    )
    assert feedback.status_code == 401

    exported = client.post(
        "/api/v1/launch/config/export",
        headers={"Authorization": _bearer(INJECTED)},
    )
    assert exported.status_code == 200
    assert exported.json()["payload"]["launch_admin_token"] == "***REDACTED***"
    assert INJECTED not in exported.text

    checklist = client.get("/api/v1/launch/checklist")
    assert checklist.status_code == 200
    item_id = checklist.json()["items"][0]["item_id"]
    denied = client.patch(
        f"/api/v1/launch/checklist/{item_id}",
        headers={"Authorization": _bearer(LOCAL_DEVELOPMENT_BEARER)},
        json={"completed": True},
    )
    assert denied.status_code == 401
    updated = client.patch(
        f"/api/v1/launch/checklist/{item_id}",
        headers={"Authorization": _bearer(INJECTED)},
        json={"completed": True, "notes": "external authority"},
    )
    assert updated.status_code == 200

    dashboard = client.get(
        "/api/v1/launch/dashboard",
        headers={"Authorization": _bearer(LOCAL_DEVELOPMENT_BEARER)},
    )
    assert dashboard.status_code == 401
    allowed = client.get(
        "/api/v1/launch/dashboard",
        headers={"Authorization": _bearer(INJECTED)},
    )
    assert allowed.status_code == 200
    assert INJECTED not in allowed.text


def test_disabled_launch_readiness_stays_404(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    monkeypatch.setattr(settings, "launch_readiness_enabled", False)
    monkeypatch.setattr(settings, "launch_admin_token", INJECTED)
    for path, method in (
        ("/api/v1/launch/meta", "get"),
        ("/api/v1/launch/dashboard", "get"),
        ("/api/v1/launch/config/export", "post"),
        ("/api/v1/launch/product-learning", "get"),
    ):
        response = getattr(client, method)(
            path,
            headers={"Authorization": _bearer(LOCAL_DEVELOPMENT_BEARER)},
        )
        assert response.status_code == 404
        assert LOCAL_DEVELOPMENT_BEARER not in response.text
        injected = getattr(client, method)(
            path,
            headers={"Authorization": _bearer(INJECTED)},
        )
        assert injected.status_code == 404


def test_public_status_does_not_echo_a_rejected_token(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "launch_admin_token", PLACEHOLDER)
    response = client.get("/api/v1/launch/system-status")
    assert response.status_code == 200
    assert PLACEHOLDER not in response.text
    assert LOCAL_DEVELOPMENT_BEARER not in response.text
    assert any(
        error.startswith("LAUNCH_ADMIN_TOKEN") for error in response.json()["validation"]["errors"]
    )


def test_authorization_failures_do_not_log_the_bearer(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    cfg = _shared_settings("production", LAUNCH_ADMIN_TOKEN=PLACEHOLDER)
    with pytest.raises(LaunchAuthorizationError):
        require_internal_launch_admin(_bearer(INJECTED), cfg)
    with pytest.raises(ConfigurationValidationError):
        run_startup_validation(cfg)
    assert INJECTED not in caplog.text
    assert PLACEHOLDER not in caplog.text
    assert LOCAL_DEVELOPMENT_BEARER not in caplog.text


def _rds(tmp_path: Path) -> Path:
    path = tmp_path / "rds.json"
    path.write_text(
        json.dumps(
            {
                "endpoint": "db.example",
                "port": 5432,
                "db_name": "dealbrain",
                "master_user_secret_arn": "arn:aws:secretsmanager:us-east-1:1:secret:rds",
            }
        ),
        encoding="utf-8",
    )
    return path


def _assemble_with(
    monkeypatch: pytest.MonkeyPatch,
    module,
    secrets: dict[str, str],
    env_file: Path,
    rds: Path,
    environment: str,
) -> None:
    def fake_plain(secret_id: str, _region: str) -> str:
        if secret_id not in secrets:
            raise module.SecretAssemblyError(f"missing {secret_id}")
        return secrets[secret_id]

    monkeypatch.setattr(module, "_get_plain_secret", fake_plain)
    monkeypatch.setattr(
        module,
        "_get_json_secret",
        lambda *_args, **_kwargs: {"username": "dealbrain", "password": "staging-db-password-ok"},
    )
    monkeypatch.setenv("DEALBRAIN_IMAGE", "ghcr.io/example/dealbrain@sha256:abc")
    module.assemble(
        env_file=env_file,
        region="us-east-1",
        rds_nonsecret=rds,
        secrets_prefix=f"dealbrain/{environment}",
        environment=environment,
    )


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_runtime_assembly_requires_usable_launch_admin_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    module = _load_assemble()
    base = {
        f"dealbrain/{environment}/app_secret_key": APP_SECRET,
        f"dealbrain/{environment}/cors_origins": "https://piqsavi.com",
        f"dealbrain/{environment}/resend_api_key": "re_launch_admin_test_key_not_real",
    }
    rds = _rds(tmp_path)
    for label, value in (
        ("missing", None),
        ("placeholder", PLACEHOLDER),
        ("demo", LOCAL_DEVELOPMENT_BEARER),
        ("short", SHORT_TOKEN),
    ):
        secrets = dict(base)
        if value is not None:
            secrets[f"dealbrain/{environment}/launch_admin_token"] = value
        env_file = tmp_path / f"{environment}-{label}.env"
        with pytest.raises(module.SecretAssemblyError) as exc_info:
            _assemble_with(monkeypatch, module, secrets, env_file, rds, environment)
        message = str(exc_info.value)
        assert "launch_admin_token" in message
        if value:
            assert value not in message
        assert not env_file.exists()

    secrets = dict(base)
    secrets[f"dealbrain/{environment}/launch_admin_token"] = INJECTED
    env_file = tmp_path / f"{environment}-ok.env"
    _assemble_with(monkeypatch, module, secrets, env_file, rds, environment)
    written = env_file.read_text(encoding="utf-8")
    assert f'LAUNCH_ADMIN_TOKEN="{INJECTED}"' in written
    assert LOCAL_DEVELOPMENT_BEARER not in written


def test_examples_do_not_publish_a_working_launch_admin_token() -> None:
    production = (ROOT / ".env.production.example").read_text(encoding="utf-8")
    staging = (ROOT / ".env.staging.example").read_text(encoding="utf-8")
    assert "LAUNCH_ADMIN_TOKEN=CHANGE_ME" in production
    assert "LAUNCH_ADMIN_TOKEN=CHANGE_ME" in staging
    assert LOCAL_DEVELOPMENT_BEARER not in production
    assert LOCAL_DEVELOPMENT_BEARER not in staging
    assert INJECTED not in production
    assert INJECTED not in staging
    compose = (ROOT / "infra/compose/docker-compose.base.yml").read_text(encoding="utf-8")
    assert "LAUNCH_ADMIN_TOKEN: ${LAUNCH_ADMIN_TOKEN:-}" in compose
    assert LOCAL_DEVELOPMENT_BEARER not in compose
    secrets = (ROOT / "infra/terraform/modules/secrets/variables.tf").read_text(encoding="utf-8")
    assert '"launch_admin_token"' in secrets
