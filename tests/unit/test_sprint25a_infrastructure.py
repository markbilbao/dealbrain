"""Sprint 25a — production infrastructure foundation tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from app.core.config import Settings
from app.core.validation import (
    exportable_settings,
    run_startup_validation,
    validate_settings,
)
from app.domain.exceptions import ConfigurationValidationError

ROOT = Path(__file__).resolve().parents[2]

STRONG_DB = "postgresql+asyncpg://dealbrain:Str0ngProdPass!99@rds.example:5432/dealbrain"
STRONG_SECRET = "prod-ops-secret-key-value-32chars!!"


def _prod_settings(**overrides: object) -> Settings:
    base = {
        "_env_file": None,
        "APP_ENV": "production",
        "APP_DEBUG": "false",
        "APP_LOG_LEVEL": "INFO",
        "DATABASE_URL": STRONG_DB,
        "APP_SECRET_KEY": STRONG_SECRET,
        "CORS_ORIGINS": "https://api.dealbrain.example",
        "TRUSTED_HOSTS": "api.dealbrain.example",
        "LAUNCH_STRICT_STARTUP": "true",
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
        "RESEND_API_KEY": "re_sprint27_1_configured_key_not_real",
        "TRANSACTIONAL_EMAIL_FROM": "no-reply@piqsavi.com",
        "TRANSACTIONAL_EMAIL_FROM_NAME": "PiqSavi",
        "PUBLIC_APP_BASE_URL": "https://piqsavi.com",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_production_valid_config_passes() -> None:
    result = validate_settings(_prod_settings())
    assert result.ok is True
    assert result.environment == "production"


def test_production_rejects_debug() -> None:
    result = validate_settings(_prod_settings(APP_DEBUG="true"))
    assert result.ok is False
    assert any("APP_DEBUG" in e for e in result.errors)


def test_production_rejects_placeholder_database_password() -> None:
    result = validate_settings(
        _prod_settings(DATABASE_URL="postgresql+asyncpg://dealbrain:CHANGE_ME@host:5432/dealbrain")
    )
    assert result.ok is False
    assert any("DATABASE_URL" in e for e in result.errors)
    # Must not echo the secret value
    joined = " ".join(result.errors).lower()
    assert "change_me" not in joined


def test_production_rejects_weak_app_secret() -> None:
    result = validate_settings(_prod_settings(APP_SECRET_KEY="short"))
    assert result.ok is False
    assert any("APP_SECRET_KEY" in e for e in result.errors)


def test_production_rejects_wildcard_cors() -> None:
    result = validate_settings(_prod_settings(CORS_ORIGINS="*"))
    assert result.ok is False
    assert any("CORS_ORIGINS" in e for e in result.errors)


def test_production_requires_strict_startup() -> None:
    result = validate_settings(_prod_settings(LAUNCH_STRICT_STARTUP="false"))
    assert result.ok is False
    assert any("LAUNCH_STRICT_STARTUP" in e for e in result.errors)


def test_production_rejects_demo_seed_and_mock() -> None:
    result = validate_settings(
        _prod_settings(SEED_DEMO_DATA="true", PRICE_HISTORY_SEED_DEMO_MOCK="true")
    )
    assert result.ok is False
    assert any("SEED_DEMO_DATA" in e for e in result.errors)
    assert any("PRICE_HISTORY_SEED_DEMO_MOCK" in e for e in result.errors)


def test_production_rejects_debug_log_level() -> None:
    result = validate_settings(_prod_settings(APP_LOG_LEVEL="DEBUG"))
    assert result.ok is False
    assert any("APP_LOG_LEVEL" in e for e in result.errors)


def test_production_requires_structured_logging() -> None:
    result = validate_settings(_prod_settings(STRUCTURED_LOGGING_ENABLED="false"))
    assert result.ok is False
    assert any("STRUCTURED_LOGGING_ENABLED" in e for e in result.errors)


def test_production_rejects_non_postgres_dsn() -> None:
    result = validate_settings(_prod_settings(DATABASE_URL="sqlite+aiosqlite:///:memory:"))
    assert result.ok is False
    assert any("PostgreSQL" in e or "DATABASE_URL" in e for e in result.errors)


def test_strict_startup_raises_on_invalid_production() -> None:
    cfg = _prod_settings(APP_DEBUG="true", LAUNCH_STRICT_STARTUP="true")
    with pytest.raises(ConfigurationValidationError):
        run_startup_validation(cfg)


def test_production_invalid_raises_even_when_strict_flag_false() -> None:
    """M4: production fail-closed must not depend on LAUNCH_STRICT_STARTUP."""
    cfg = _prod_settings(APP_DEBUG="true", LAUNCH_STRICT_STARTUP="false")
    with pytest.raises(ConfigurationValidationError) as exc_info:
        run_startup_validation(cfg)
    message = str(exc_info.value)
    assert "APP_DEBUG" in message
    assert "LAUNCH_STRICT_STARTUP" in message
    assert STRONG_SECRET not in message
    assert "Str0ngProdPass" not in message


def test_production_invalid_raises_when_strict_flag_true() -> None:
    cfg = _prod_settings(CORS_ORIGINS="*", LAUNCH_STRICT_STARTUP="true")
    with pytest.raises(ConfigurationValidationError) as exc_info:
        run_startup_validation(cfg)
    assert "CORS_ORIGINS" in str(exc_info.value)


def test_valid_production_startup_validation_passes() -> None:
    result = run_startup_validation(_prod_settings())
    assert result.ok is True
    assert result.errors == ()


def test_development_remains_usable_without_cloud_secrets() -> None:
    cfg = Settings(
        _env_file=None,
        APP_ENV="development",
        APP_DEBUG="true",
        APP_SECRET_KEY="",
        DATABASE_URL="postgresql+asyncpg://dealbrain:dealbrain@localhost:5432/dealbrain",
        CORS_ORIGINS="http://localhost:8000",
        LAUNCH_STRICT_STARTUP="false",
        SEED_DEMO_DATA="true",
        DEMO_LAUNCHER_ENABLED="true",
    )
    result = validate_settings(cfg)
    assert result.ok is True
    # Direct helper must not raise for soft development config.
    assert run_startup_validation(cfg).ok is True


def test_development_strict_startup_raises_on_malformed_database_url() -> None:
    cfg = Settings(
        _env_file=None,
        APP_ENV="development",
        APP_DEBUG="true",
        DATABASE_URL="not-a-url",
        LAUNCH_STRICT_STARTUP="true",
    )
    with pytest.raises(ConfigurationValidationError):
        run_startup_validation(cfg)


def test_validation_errors_redact_secret_values() -> None:
    cfg = _prod_settings(APP_SECRET_KEY="tooshort", DATABASE_URL=STRONG_DB)
    with pytest.raises(ConfigurationValidationError) as exc_info:
        run_startup_validation(cfg)
    text = str(exc_info.value)
    assert "APP_SECRET_KEY" in text
    assert "tooshort" not in text
    assert STRONG_SECRET not in text
    assert "Str0ngProdPass" not in text


def test_lifespan_uses_authoritative_startup_validation() -> None:
    main_src = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "run_startup_validation" in main_src
    # Must not re-raise ConfigurationValidationError from validation.errors —
    # the helper itself is fail-closed for production.
    assert "ConfigurationValidationError(list(validation.errors))" not in main_src
    assert "from app.domain.exceptions import ConfigurationValidationError" not in main_src


def test_export_redacts_app_secret() -> None:
    cfg = _prod_settings()
    payload = exportable_settings(cfg)
    assert payload["app_secret_key"] == "***REDACTED***"
    assert payload["database_url"] == "***REDACTED***"
    assert payload["resend_api_key"] == "***REDACTED***"
    assert STRONG_SECRET not in str(payload)
    assert "Str0ngProdPass" not in str(payload)
    assert "re_sprint27_1_configured_key_not_real" not in str(payload)


def test_production_requires_resend_identity_email() -> None:
    result = validate_settings(_prod_settings(TRANSACTIONAL_EMAIL_PROVIDER="null"))
    assert result.ok is False
    assert any("TRANSACTIONAL_EMAIL_PROVIDER" in error for error in result.errors)


def test_api_startup_does_not_run_alembic() -> None:
    """Static check: lifespan must not invoke Alembic migrations."""
    main_src = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "alembic" not in main_src.lower()
    tree = ast.parse(main_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            assert name not in {"upgrade", "command"}, f"unexpected migrate call {name}"


def test_dockerfile_healthcheck_uses_live() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "/live" in text
    assert "HEALTHCHECK" in text


def test_compose_overlays_define_api_and_migrate() -> None:
    base = (ROOT / "infra/compose/docker-compose.base.yml").read_text(encoding="utf-8")
    assert "services:" in base
    assert re.search(r"(?m)^\s+api:", base)
    assert re.search(r"(?m)^\s+migrate:", base)
    assert "alembic" in base
    assert "postgres:" not in base.lower() or "postgresql+asyncpg" in base
    # No in-container Postgres service
    assert "image: postgres" not in base
    prod = (ROOT / "infra/compose/docker-compose.production.yml").read_text(encoding="utf-8")
    assert "APP_ENV: production" in prod
    assert "LAUNCH_STRICT_STARTUP" in prod


def test_terraform_environments_exist() -> None:
    for env in ("staging", "production"):
        path = ROOT / "infra/terraform/environments" / env / "main.tf"
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        assert 'health_check_path = "/ready"' in text
        assert 'module "rds"' in text
        assert 'module "alb"' in text
        assert 'module "secrets"' in text
        assert "db_password" not in text
        assert "master_user_secret_arn" in text


def test_alb_module_requires_ready_health_check() -> None:
    text = (ROOT / "infra/terraform/modules/alb/variables.tf").read_text(encoding="utf-8")
    assert "/ready" in text


def test_rds_not_publicly_accessible() -> None:
    text = (ROOT / "infra/terraform/modules/rds/main.tf").read_text(encoding="utf-8")
    assert "publicly_accessible" in text
    assert "false" in text


def test_rds_uses_aws_managed_master_password() -> None:
    rds_main = (ROOT / "infra/terraform/modules/rds/main.tf").read_text(encoding="utf-8")
    rds_vars = (ROOT / "infra/terraform/modules/rds/variables.tf").read_text(encoding="utf-8")
    rds_out = (ROOT / "infra/terraform/modules/rds/outputs.tf").read_text(encoding="utf-8")
    assert "manage_master_user_password" in rds_main
    assert "true" in rds_main
    assert "password = var." not in rds_main
    assert "variable \"db_password\"" not in rds_vars
    assert "master_user_secret_arn" in rds_out
    assert "sensitive" in rds_out


def test_no_db_password_terraform_variable_anywhere() -> None:
    tf_root = ROOT / "infra/terraform"
    for path in tf_root.rglob("*"):
        if not path.is_file() or ".terraform" in path.parts:
            continue
        # Configuration inputs only — docs may name the forbidden pattern as absent.
        if path.suffix != ".tf" and "tfvars" not in path.name:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "db_password" not in text, f"db_password must not appear in {path}"
        assert "TF_VAR_db_password" not in text, f"TF_VAR_db_password must not appear in {path}"


def test_tfvars_examples_have_no_password_like_values() -> None:
    patterns = [
        re.compile(r"(?i)password\s*="),
        re.compile(r"(?i)TF_VAR_db"),
        re.compile(r"(?i)db_password"),
        re.compile(r"(?i)secret\s*=\s*\"[^\"]{8,}\""),
    ]
    for env in ("staging", "production"):
        path = ROOT / "infra/terraform/environments" / env / "terraform.tfvars.example"
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            assert pattern.search(text) is None, f"{path} matched {pattern.pattern}"


def test_rds_secret_outputs_are_arns_only() -> None:
    for env in ("staging", "production"):
        text = (ROOT / "infra/terraform/environments" / env / "outputs.tf").read_text(
            encoding="utf-8"
        )
        assert "rds_master_user_secret_arn" in text
        assert "sensitive" in text
        # Must not invent password / secret-value outputs
        assert "db_password" not in text
        assert "master_password" not in text
        assert "secret_string" not in text


def test_secrets_module_omits_conflicting_database_url_container() -> None:
    text = (ROOT / "infra/terraform/modules/secrets/variables.tf").read_text(encoding="utf-8")
    assert '"database_url"' not in text


def test_iam_includes_rds_managed_secret_and_env_isolation() -> None:
    iam = (ROOT / "infra/terraform/modules/iam/main.tf").read_text(encoding="utf-8")
    assert "ReadEnvironmentSecrets" in iam
    assert "DenyOtherEnvironmentSecrets" in iam
    assert "dealbrain/" in iam
    for env in ("staging", "production"):
        main = (ROOT / "infra/terraform/environments" / env / "main.tf").read_text(
            encoding="utf-8"
        )
        assert "module.rds.master_user_secret_arn" in main
        assert "module.secrets.secret_arns" in main


def test_rds_security_group_has_explicit_empty_egress() -> None:
    text = (ROOT / "infra/terraform/modules/security_groups/main.tf").read_text(encoding="utf-8")
    assert "egress = []" in text
    assert "count = 0" not in text


def test_ci_workflow_exists_with_required_gates() -> None:
    path = ROOT / ".github/workflows/ci.yml"
    assert path.is_file(), "Phase 25a requires .github/workflows/ci.yml"
    text = path.read_text(encoding="utf-8")
    for needle in (
        "pull_request",
        "pytest",
        "ruff",
        "check_ruff_baseline",
        "terraform fmt",
        "terraform validate",
        "docker compose",
        "build-push-action",
        "secret_scan_25a",
        "test_openapi_drift",
        "test_sprint25a_infrastructure",
        "test_sprint25b1_image_publication",
        "test_sprint25b2_oidc_iam",
    ):
        assert needle in text, f"CI missing required gate mention: {needle}"
    # Must not deploy or apply AWS in Phase 25a CI
    assert "terraform apply" not in text
    assert "deploy-staging" not in text
    assert "deploy-production" not in text
    assert "role-to-assume" not in text
    assert "id-token: write" not in text
    # Releasable GHCR publish is owned by build-image.yml (Sprint 25b.1)
    assert "Push CI digest foundation to GHCR" not in text
    assert "packages: write" not in text
    # Must not enforce raw full-tree ruff without the baseline gate
    assert "ruff check app tests" not in text
    assert "ruff format --check app tests" not in text


def test_ruff_baseline_artifact_exists() -> None:
    baseline = ROOT / "tests/lint/baselines/ruff.baseline.json"
    script = ROOT / "scripts/check_ruff_baseline.py"
    assert script.is_file()
    assert baseline.is_file()
    data = json.loads(baseline.read_text(encoding="utf-8"))
    assert data.get("version") == 1
    assert isinstance(data.get("check"), dict)
    assert isinstance(data.get("format_unformatted"), list)
    assert data.get("totals", {}).get("check", 0) >= 1


def test_infra_files_have_no_embedded_secrets() -> None:
    """Static scan of tracked infra for high-confidence secret patterns."""
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"aws_secret_access_key\s*=\s*\"[^\"]+\""),
        re.compile(r"password\s*=\s*\"(?!CHANGE_ME|REPLACE_ME|use-a-strong)[^\"]{8,}\"", re.I),
    ]
    roots = [ROOT / "infra"]
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".png", ".jpg", ".zip"} or path.name.startswith(".terraform"):
                continue
            if path.name in {".gitignore"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                match = pattern.search(text)
                assert match is None, f"Possible secret in {path}: {pattern.pattern}"


def test_architecture_lock_mentions_sprint_25() -> None:
    lock = (ROOT / "docs/architecture/ARCHITECTURE_LOCK.md").read_text(encoding="utf-8")
    assert "Sprint 25" in lock or "25" in lock
