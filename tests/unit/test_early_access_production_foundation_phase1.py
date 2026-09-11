"""Early Access production foundation Phase 1 contracts."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from app.core.config import Settings
from app.core.validation import validate_settings
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
PROD_TF = ROOT / "infra/terraform/environments/production"
STAGING_TF = ROOT / "infra/terraform/environments/staging"
PROD_DEPLOY = WORKFLOWS / "deploy-production.yml"
PROD_ROLLBACK = WORKFLOWS / "rollback-production.yml"
STAGING_DEPLOY = WORKFLOWS / "deploy-staging.yml"
ASSEMBLE = ROOT / "scripts/deploy/host/assemble-runtime-env.py"
PROD_COMPOSE = ROOT / "infra/compose/docker-compose.production.yml"
STAGING_COMPOSE = ROOT / "infra/compose/docker-compose.staging.yml"
EVIDENCE = ROOT / "docs/roadmap/evidence/EARLY_ACCESS_PRODUCTION_FOUNDATION_PHASE1_2026-09-11.md"
GITHUB_ENV_DOC = ROOT / "docs/runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md"
BACKUP_DOC = ROOT / "docs/runbooks/PRODUCTION_RDS_BACKUP_RESTORE.md"
LOGGING_DOC = ROOT / "docs/runbooks/PRODUCTION_LOGGING.md"

STARTING_MAIN = "d886409d1282b31670b09dd04dd664d0dd2edb37"
LOCKED_DIGEST = "sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa"
STRONG_DB = (
    "postgresql+asyncpg://dealbrain:Str0ngProdPass!99@"
    "dealbrain-production.xxxx.us-east-1.rds.amazonaws.com:5432/dealbrain"
)
STRONG_SECRET = "prod-ops-secret-key-value-32chars!!"
RESEND_KEY = "re_phase1_configured_key_not_real"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _load_assemble():
    spec = importlib.util.spec_from_file_location("assemble_runtime_env_phase1", ASSEMBLE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _prod_settings(**overrides: object) -> Settings:
    base = {
        "_env_file": None,
        "APP_ENV": "production",
        "APP_DEBUG": "false",
        "APP_LOG_LEVEL": "INFO",
        "DATABASE_URL": STRONG_DB,
        "APP_SECRET_KEY": STRONG_SECRET,
        "CORS_ORIGINS": "https://piqsavi.com",
        "TRUSTED_HOSTS": "piqsavi.com,www.piqsavi.com",
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
        "RESEND_API_KEY": RESEND_KEY,
        "TRANSACTIONAL_EMAIL_FROM": "no-reply@piqsavi.com",
        "TRANSACTIONAL_EMAIL_FROM_NAME": "PiqSavi",
        "PUBLIC_APP_BASE_URL": "https://piqsavi.com",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _patch_production_surfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.consumer.mode.get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )


# ---------------------------------------------------------------------------
# Evidence / docs
# ---------------------------------------------------------------------------


def test_phase1_evidence_records_starting_sha_and_owner_controls() -> None:
    text = _read(EVIDENCE)
    assert STARTING_MAIN in text
    assert "OWNER INFRASTRUCTURE PROVISIONING REQUIRED" in text
    assert "No Terraform apply" in text or "did not:** apply production Terraform" in text
    assert "No production deploy" in text or "did not:** apply production Terraform" in text
    assert "DNS" in text
    assert GITHUB_ENV_DOC.is_file()
    assert BACKUP_DOC.is_file()
    assert LOGGING_DOC.is_file()
    backup = _read(BACKUP_DOC)
    assert "does not claim a restore rehearsal occurred" in backup.lower() or (
        "not claim a restore rehearsal" in backup.lower()
    )
    assert "alembic downgrade" in backup.lower()
    logging = _read(LOGGING_DOC)
    assert "/dealbrain/production/api" in logging
    assert "EXT-16" in logging
    assert "EXT-24" in logging
    gh = _read(GITHUB_ENV_DOC)
    assert "Settings → Environments" in gh
    assert "AWS_ROLE_ARN" in gh
    assert "PRODUCTION_TARGET_GROUP_ARN" in gh
    assert "AWS_ACCESS_KEY_ID" in gh  # forbidden; documented as must-not-exist
    assert "never GitHub" in gh.lower() or "Do **not** put application secrets" in gh


# ---------------------------------------------------------------------------
# Terraform
# ---------------------------------------------------------------------------


def test_production_terraform_is_isolated_and_durable() -> None:
    main = _read(PROD_TF / "main.tf")
    variables = _read(PROD_TF / "variables.tf")
    example = _read(PROD_TF / "terraform.tfvars.example")
    assert "required_version" in main
    assert "use_lockfile = true" in main
    assert 'backend "s3"' in main
    assert 'environment = "production"' in main
    assert "10.20.0.0/16" in variables
    assert "10.10.0.0/16" not in variables
    assert 'module "rds"' in main
    assert 'module "alb"' in main
    assert 'module "ec2"' in main
    assert 'module "logging"' in main
    assert 'module "release_artifacts"' in main
    assert 'source = "../../modules/ssm_production_deploy_document"' in main
    assert 'source = "../../modules/ssm_production_rollback_document"' in main
    assert 'source = "../../modules/ssm_deploy_document"' not in main
    assert 'source = "../../modules/ssm_rollback_document"' not in main
    assert "AWS-RunShellScript" not in main
    assert "DealBrain-StagingDeploy" not in main
    assert "ecs" not in main.lower()
    assert "user_data_base64" in main
    assert "ec2/user_data/production.sh" in main
    assert "ec2/user_data/staging.sh" not in main
    assert "storage_encrypted" in _read(ROOT / "infra/terraform/modules/rds/main.tf")
    assert "publicly_accessible    = false" in _read(ROOT / "infra/terraform/modules/rds/main.tf")
    assert "backup_retention_days >= 30" in variables
    assert "deletion_protection" in variables
    assert "multi_az" in variables
    assert "skip_final_snapshot == false" in variables
    assert "db_password" not in example
    assert "manage_master_user_password" in _read(ROOT / "infra/terraform/modules/rds/main.tf")
    assert "309556720" in example
    assert "1314423275" in example
    staging = _read(STAGING_TF / "main.tf")
    assert "10.10.0.0/16" in _read(STAGING_TF / "variables.tf") or "10.10.0.0/16" in staging
    assert "DealBrain-StagingDeploy" in staging or "ssm_deploy_document" in staging


def test_production_terraform_fmt_and_validate_when_available() -> None:
    if subprocess.run(["bash", "-c", "command -v terraform"], capture_output=True).returncode != 0:
        pytest.skip("terraform CLI not installed")
    fmt = subprocess.run(
        ["terraform", "fmt", "-check", "-recursive", str(ROOT / "infra/terraform")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr
    proc = subprocess.run(
        ["terraform", "init", "-backend=false", "-input=false"],
        cwd=PROD_TF,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = subprocess.run(
        ["terraform", "validate"],
        cwd=PROD_TF,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# Runtime assembler
# ---------------------------------------------------------------------------


def test_staging_runtime_assembly_still_works(tmp_path: Path) -> None:
    mod = _load_assemble()
    env_file = tmp_path / "staging.env"
    rds = tmp_path / "rds.json"
    rds.write_text(
        json.dumps(
            {
                "endpoint": "staging-db.example",
                "port": 5432,
                "db_name": "dealbrain",
                "master_user_secret_arn": "arn:aws:secretsmanager:us-east-1:1:secret:rds",
            }
        ),
        encoding="utf-8",
    )

    def fake_plain(secret_id: str, _region: str) -> str:
        mapping = {
            "dealbrain/staging/app_secret_key": "staging-only-not-for-production-use-32c",
            "dealbrain/staging/cors_origins": "https://staging.piqsavi.com",
        }
        if secret_id not in mapping:
            raise mod.SecretAssemblyError(f"missing {secret_id}")
        return mapping[secret_id]

    previous = os.environ.get("DEALBRAIN_IMAGE")
    os.environ["DEALBRAIN_IMAGE"] = f"ghcr.io/markbilbao/dealbrain@{LOCKED_DIGEST}"
    try:
        mod._get_plain_secret = fake_plain
        mod._get_json_secret = lambda *_a, **_k: {
            "username": "dealbrain",
            "password": "staging-db-password-ok",
        }
        mod.assemble(
            env_file=env_file,
            region="us-east-1",
            rds_nonsecret=rds,
            secrets_prefix="dealbrain/staging",
        )
    finally:
        if previous is None:
            os.environ.pop("DEALBRAIN_IMAGE", None)
        else:
            os.environ["DEALBRAIN_IMAGE"] = previous
    written = env_file.read_text(encoding="utf-8")
    assert 'APP_ENV="staging"' in written
    assert 'PUBLIC_APP_BASE_URL="https://staging.piqsavi.com"' in written
    assert "staging-db-password-ok" in written
    assert RESEND_KEY not in written


def test_production_runtime_assembly_fail_closed(tmp_path: Path) -> None:
    mod = _load_assemble()
    env_file = tmp_path / "production.env"
    rds = tmp_path / "rds.json"
    rds.write_text(
        json.dumps(
            {
                "endpoint": "localhost",
                "port": 5432,
                "db_name": "dealbrain",
                "master_user_secret_arn": "arn:aws:secretsmanager:us-east-1:1:secret:rds",
            }
        ),
        encoding="utf-8",
    )
    previous = os.environ.get("DEALBRAIN_IMAGE")
    os.environ["DEALBRAIN_IMAGE"] = f"ghcr.io/markbilbao/dealbrain@{LOCKED_DIGEST}"
    try:
        with pytest.raises(mod.SecretAssemblyError, match="durable RDS"):
            mod.assemble(
                env_file=env_file,
                region="us-east-1",
                rds_nonsecret=rds,
                secrets_prefix="dealbrain/production",
                environment="production",
            )
    finally:
        if previous is None:
            os.environ.pop("DEALBRAIN_IMAGE", None)
        else:
            os.environ["DEALBRAIN_IMAGE"] = previous
    assert not env_file.exists()


def test_production_runtime_assembly_requires_resend_and_writes_contract(
    tmp_path: Path,
) -> None:
    mod = _load_assemble()
    env_file = tmp_path / "production.env"
    rds = tmp_path / "rds.json"
    rds.write_text(
        json.dumps(
            {
                "endpoint": "dealbrain-production.xxxx.us-east-1.rds.amazonaws.com",
                "port": 5432,
                "db_name": "dealbrain",
                "master_user_secret_arn": "arn:aws:secretsmanager:us-east-1:1:secret:rds",
            }
        ),
        encoding="utf-8",
    )

    def fake_plain(secret_id: str, _region: str) -> str:
        mapping = {
            "dealbrain/production/app_secret_key": STRONG_SECRET,
            "dealbrain/production/cors_origins": "https://piqsavi.com",
            "dealbrain/production/resend_api_key": RESEND_KEY,
        }
        if secret_id not in mapping:
            raise mod.SecretAssemblyError(f"missing {secret_id}")
        return mapping[secret_id]

    previous = os.environ.get("DEALBRAIN_IMAGE")
    os.environ["DEALBRAIN_IMAGE"] = f"ghcr.io/markbilbao/dealbrain@{LOCKED_DIGEST}"
    try:
        mod._get_plain_secret = fake_plain
        mod._get_json_secret = lambda *_a, **_k: {
            "username": "dealbrain",
            "password": "production-db-password-ok12",
        }
        missing = tmp_path / "missing-resend.env"
        rds_ok = rds

        def fake_plain_no_resend(secret_id: str, _region: str) -> str:
            if "resend" in secret_id:
                raise mod.SecretAssemblyError("missing resend")
            return fake_plain(secret_id, _region)

        mod._get_plain_secret = fake_plain_no_resend
        with pytest.raises(mod.SecretAssemblyError, match="Resend"):
            mod.assemble(
                env_file=missing,
                region="us-east-1",
                rds_nonsecret=rds_ok,
                secrets_prefix="dealbrain/production",
                environment="production",
            )
        mod._get_plain_secret = fake_plain
        mod.assemble(
            env_file=env_file,
            region="us-east-1",
            rds_nonsecret=rds,
            secrets_prefix="dealbrain/production",
            environment="production",
        )
    finally:
        if previous is None:
            os.environ.pop("DEALBRAIN_IMAGE", None)
        else:
            os.environ["DEALBRAIN_IMAGE"] = previous
    written = env_file.read_text(encoding="utf-8")
    assert 'APP_ENV="production"' in written
    assert 'PUBLIC_APP_BASE_URL="https://piqsavi.com"' in written
    assert "privacy-2026-09-11" in written
    assert "terms-2026-09-11" in written
    assert "support@piqsavi.com" in written
    assert "privacy@piqsavi.com" in written
    assert 'TRANSACTIONAL_EMAIL_PROVIDER="resend"' in written
    assert STRONG_SECRET in written
    assert "ERROR:" not in written


def test_production_cannot_start_with_ephemeral_store() -> None:
    result = validate_settings(
        _prod_settings(
            DATABASE_URL="postgresql+asyncpg://dealbrain:Str0ngProdPass!99@postgres:5432/dealbrain"
        )
    )
    assert result.ok is False
    sqlite = validate_settings(_prod_settings(DATABASE_URL="sqlite+aiosqlite:///:memory:"))
    assert sqlite.ok is False
    ok = validate_settings(_prod_settings())
    assert ok.ok is True


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


def test_production_deploy_workflow_immutable_digest_not_staging() -> None:
    text = _read(PROD_DEPLOY)
    data = yaml.safe_load(text)
    on_block = data.get("on", data.get(True))
    assert list(on_block.keys()) == ["workflow_dispatch"]
    assert data["jobs"]["deploy"]["environment"] == "production"
    assert data["concurrency"]["group"] == "production-release-mutation"
    assert data["permissions"]["id-token"] == "write"
    assert "AWS_ACCESS_KEY_ID" not in text
    assert "AWS_SECRET_ACCESS_KEY" not in text
    assert "docker/build-push-action" not in text
    assert "docker build " not in text.lower()
    assert "imagetools inspect" in text
    assert "image_digest" in text
    assert "DealBrain-ProductionDeploy" in text
    assert "DealBrain-StagingDeploy" not in text
    assert "terraform apply" not in text
    assert "PRODUCTION_TARGET_GROUP_ARN" in text
    assert "grep -qv 'dealbrain-staging-gha-deploy'" in text
    assert "grep -qv staging" in text
    assert "environment: staging" not in text
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in text
    assert "allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}" in text
    ci = _read(WORKFLOWS / "ci.yml")
    assert "deploy-production" not in ci


def test_production_rollback_preserves_database() -> None:
    text = _read(PROD_ROLLBACK)
    data = yaml.safe_load(text)
    on_block = data.get("on", data.get(True))
    assert list(on_block.keys()) == ["workflow_dispatch"]
    assert data["jobs"]["rollback"]["environment"] == "production"
    assert data["concurrency"]["group"] == "production-release-mutation"
    assert "DealBrain-ProductionRollback" in text
    assert "terraform apply" not in text
    lowered = text.lower()
    assert "deletedbinstance" not in lowered
    assert "modifydbinstance" not in lowered
    assert "alembic downgrade" not in lowered
    host = _read(ROOT / "scripts/deploy/host/dealbrain-production-rollback.sh")
    assert "alembic downgrade" not in host.lower()
    assert "alembic current" in host
    assert "DeleteDBInstance" not in host
    assert "drop database" not in host.lower()
    src = _read(ROOT / "scripts/deploy/validate_production_rollback_eligibility.py")
    assert "validate_production_identity" in src
    assert 'if "staging" in repo' in src
    assert 'if "production" in repo' not in src or "staging" in src


def test_production_compose_logging_and_public_url() -> None:
    text = _read(PROD_COMPOSE)
    assert "https://piqsavi.com" in text
    assert "piqsavi.com,www.piqsavi.com" in text
    assert "privacy-2026-09-11" in text
    assert "awslogs" in text
    assert "/dealbrain/production/api" in text
    staging = _read(STAGING_COMPOSE)
    assert "awslogs" not in staging
    assert "https://staging.piqsavi.com" in staging


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def test_production_disables_demo_search_and_shopping(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_production_surfaces(monkeypatch)
    with TestClient(create_app()) as client:
        demo = client.get("/demo", follow_redirects=False)
        assert demo.status_code == 303
        assert demo.headers["location"] == "/"
        search = client.get("/search", follow_redirects=False)
        assert search.status_code == 303
        assert search.headers["location"] == "/"
        assert "/results/" not in search.headers["location"]
        results = client.get("/results/headphones-standard", follow_redirects=False)
        assert results.status_code == 303
        assert results.headers["location"] == "/"
        compare = client.get("/compare/headphones-standard", follow_redirects=False)
        assert compare.status_code == 303
        why = client.get("/why-best-piq/headphones-standard", follow_redirects=False)
        assert why.status_code == 303
        home = client.get("/")
        assert home.status_code == 200
        assert "PiqSavi" in home.text
        privacy = client.get("/privacy")
        assert privacy.status_code == 200
        terms = client.get("/terms")
        assert terms.status_code == 200
        live = client.get("/live")
        assert live.status_code == 200
        legal = _read(ROOT / "app/legal/routes.py")
        assert "unfinished_html_surfaces_enabled" not in legal
        probes = _read(ROOT / "app/api/probes.py")
        assert "unfinished_html_surfaces_enabled" not in probes
        from app.legal.publication import catalog_from_settings

        catalog = catalog_from_settings(Settings(_env_file=None))
        assert catalog.published("terms") is not None
        assert catalog.published("privacy") is not None
        paths = {getattr(route, "path", "") for route in client.app.routes}
        assert "/api/v1/early-access" in paths or any(
            path.endswith("/early-access") for path in paths
        )


def test_development_demo_and_search_remain_available() -> None:
    with TestClient(create_app()) as client:
        demo = client.get("/demo", follow_redirects=False)
        assert demo.status_code == 200
        search = client.get("/search", follow_redirects=False)
        assert search.status_code in {303, 307, 302}
        assert "/results/" in search.headers["location"]


def test_host_scripts_bash_syntax() -> None:
    for path in (
        ROOT / "infra/ec2/user_data/production.sh",
        ROOT / "scripts/deploy/host/dealbrain-production-deploy.sh",
        ROOT / "scripts/deploy/host/dealbrain-production-rollback.sh",
        ROOT / "scripts/deploy/host/verify-production.sh",
        ROOT / "scripts/deploy/host/ghcr-login.sh",
    ):
        proc = subprocess.run(
            ["bash", "-n", str(path)], capture_output=True, text=True, check=False
        )
        assert proc.returncode == 0, f"{path}: {proc.stderr}"
