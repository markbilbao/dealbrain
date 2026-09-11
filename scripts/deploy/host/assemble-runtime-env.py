#!/usr/bin/env python3
"""Assemble Compose runtime env from Secrets Manager (host-side only).

Supports staging and production. Never prints secret values. Writes atomically
to a 0600 env file. Fail closed on missing production configuration.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from urllib.parse import quote_plus, urlparse

STAGING_PUBLIC_BASE_URL = "https://staging.piqsavi.com"
PRODUCTION_PUBLIC_BASE_URL = "https://piqsavi.com"
PRODUCTION_TRUSTED_HOSTS = "piqsavi.com,www.piqsavi.com"
PRODUCTION_LEGAL_PRIVACY_VERSION = "privacy-2026-09-11"
PRODUCTION_LEGAL_TERMS_VERSION = "terms-2026-09-11"
PUBLIC_SUPPORT_EMAIL = "support@piqsavi.com"
PUBLIC_PRIVACY_EMAIL = "privacy@piqsavi.com"
TRANSACTIONAL_EMAIL_FROM = "no-reply@piqsavi.com"
TRANSACTIONAL_EMAIL_FROM_NAME = "PiqSavi"

_LOCAL_DB_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "postgres",
        "db",
        "database",
        "host.docker.internal",
    }
)


class SecretAssemblyError(RuntimeError):
    """Raised when required secrets cannot be assembled."""


def _aws_get_secret_string(secret_id: str, region: str) -> str:
    # Avoid placing secret material in process argv beyond the secret id/name.
    cmd = [
        "aws",
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        secret_id,
        "--region",
        region,
        "--query",
        "SecretString",
        "--output",
        "text",
    ]
    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        # Redact any accidental secret material from stderr.
        raise SecretAssemblyError(
            f"failed to retrieve secret {secret_id!r}: exit {exc.returncode}"
        ) from None
    value = proc.stdout.strip()
    if not value or value == "None":
        raise SecretAssemblyError(f"empty secret value for {secret_id!r}")
    return value


def _get_json_secret(secret_id: str, region: str) -> dict:
    raw = _aws_get_secret_string(secret_id, region)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SecretAssemblyError(f"secret {secret_id!r} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise SecretAssemblyError(f"secret {secret_id!r} JSON must be an object")
    return data


def _get_plain_secret(secret_id: str, region: str) -> str:
    return _aws_get_secret_string(secret_id, region)


def _usable_resend_api_key(value: str) -> bool:
    """Return True only for a non-empty, non-placeholder Resend key.

    Host script stays standalone — do not import application validation.
    """
    key = (value or "").strip()
    if not key:
        return False
    lowered = key.lower()
    if lowered in {
        "change_me",
        "changeme",
        "replace_me",
        "password",
        "secret",
        "todo",
        "placeholder",
        "example",
        "test",
        "dev",
    }:
        return False
    if "change_me" in lowered or "replace_me" in lowered:
        return False
    if lowered.startswith("<") and lowered.endswith(">"):
        return False
    return not (lowered.startswith("${") and lowered.endswith("}"))


def build_database_url(
    *,
    username: str,
    password: str,
    host: str,
    port: int | str,
    database: str,
) -> str:
    """Construct postgresql+asyncpg URL with correct URL-encoding."""
    user_q = quote_plus(username, safe="")
    pass_q = quote_plus(password, safe="")
    return f"postgresql+asyncpg://{user_q}:{pass_q}@{host}:{port}/{database}"


def _database_host_is_ephemeral_or_local(host: str) -> bool:
    normalized = (host or "").strip().lower().rstrip(".")
    if not normalized:
        return True
    if normalized in _LOCAL_DB_HOSTS:
        return True
    if normalized.endswith(".local"):
        return True
    return False


def _atomic_write_env(
    path: Path, mapping: dict[str, str], *, tmp_prefix: str = ".staging.env."
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=tmp_prefix, dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for key in sorted(mapping):
                value = mapping[key]
                # Escape for dotenv-style KEY=VALUE (no export).
                escaped = value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
                handle.write(f'{key}="{escaped}"\n')
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        with suppress(PermissionError):
            # Non-root unit tests; host deploy runs as root.
            os.chown(tmp_path, 0, 0)
        tmp_path.replace(path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        with suppress(PermissionError):
            os.chown(path, 0, 0)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def assemble(
    *,
    env_file: Path,
    region: str,
    rds_nonsecret: Path,
    secrets_prefix: str = "dealbrain/staging",
    environment: str = "staging",
) -> None:
    environment = (environment or "staging").strip().lower()
    if environment not in {"staging", "production"}:
        raise SecretAssemblyError("environment must be staging or production")

    prefix = secrets_prefix.strip().rstrip("/")
    if environment == "staging":
        if "production" in prefix:
            raise SecretAssemblyError("refusing to read production secrets on staging host")
        if prefix != "dealbrain/staging":
            raise SecretAssemblyError("staging secrets prefix must be dealbrain/staging")
    else:
        if "staging" in prefix:
            raise SecretAssemblyError("refusing to read staging secrets on production host")
        if prefix != "dealbrain/production":
            raise SecretAssemblyError("production secrets prefix must be dealbrain/production")

    with rds_nonsecret.open(encoding="utf-8") as handle:
        rds_meta = json.load(handle)
    host = rds_meta["endpoint"]
    port = rds_meta["port"]
    db_name = rds_meta["db_name"]
    rds_secret_arn = rds_meta.get("master_user_secret_arn") or rds_meta.get(
        "master_user_secret_id"
    )
    if not rds_secret_arn:
        raise SecretAssemblyError("rds-nonsecret.json missing master_user_secret_arn")

    if environment == "production" and _database_host_is_ephemeral_or_local(str(host)):
        raise SecretAssemblyError(
            "production DATABASE_URL host must be durable RDS (not localhost/ephemeral)"
        )

    rds_secret = _get_json_secret(rds_secret_arn, region)
    username = rds_secret.get("username")
    password = rds_secret.get("password")
    if not username or password is None:
        raise SecretAssemblyError("RDS managed secret missing username/password")

    database_url = build_database_url(
        username=username,
        password=password,
        host=host,
        port=port,
        database=db_name,
    )
    parsed = urlparse(database_url.replace("postgresql+asyncpg", "postgresql", 1))
    if environment == "production":
        db_host = (parsed.hostname or "").lower()
        if _database_host_is_ephemeral_or_local(db_host):
            raise SecretAssemblyError(
                "production cannot start with an ephemeral/local Early Access store"
            )
        scheme = (parsed.scheme or "").lower()
        if "postgres" not in scheme:
            raise SecretAssemblyError("production DATABASE_URL must be PostgreSQL")

    # Required application secrets
    app_secret_key = _get_plain_secret(f"{prefix}/app_secret_key", region)
    cors_origins = _get_plain_secret(f"{prefix}/cors_origins", region)
    if not app_secret_key.strip():
        raise SecretAssemblyError("app_secret_key is empty")
    if environment == "production" and len(app_secret_key.strip()) < 32:
        raise SecretAssemblyError("production app_secret_key must be at least 32 characters")
    if not cors_origins.strip():
        raise SecretAssemblyError("cors_origins is empty")

    mapping: dict[str, str] = {
        "APP_ENV": environment,
        "DATABASE_URL": database_url,
        "CORS_ORIGINS": cors_origins,
        "APP_SECRET_KEY": app_secret_key,
        "DEALBRAIN_IMAGE": os.environ.get("DEALBRAIN_IMAGE", ""),
    }
    if not mapping["DEALBRAIN_IMAGE"]:
        raise SecretAssemblyError("DEALBRAIN_IMAGE must be set in the environment")

    # Optional AI credentials — empty allowed when live HTTP disabled.
    for leaf, env_name in (
        ("openai_api_key", "OPENAI_API_KEY"),
        ("anthropic_api_key", "ANTHROPIC_API_KEY"),
        ("gemini_api_key", "GEMINI_API_KEY"),
        ("resend_api_key", "RESEND_API_KEY"),
    ):
        try:
            mapping[env_name] = _get_plain_secret(f"{prefix}/{leaf}", region)
        except SecretAssemblyError:
            mapping[env_name] = ""

    # Sprint 27.3 non-secret identity-email contract. The Resend API key is
    # injected only from Secrets Manager leaf `{prefix}/resend_api_key`.
    # Never write a placeholder that could pass startup validation.
    mapping["ALLOW_DEMO_RESET_TOKENS"] = "false"
    mapping["TRANSACTIONAL_EMAIL_FROM"] = TRANSACTIONAL_EMAIL_FROM
    mapping["TRANSACTIONAL_EMAIL_FROM_NAME"] = TRANSACTIONAL_EMAIL_FROM_NAME
    resend_key = mapping.get("RESEND_API_KEY", "")
    if environment == "staging":
        mapping["PUBLIC_APP_BASE_URL"] = STAGING_PUBLIC_BASE_URL
        if _usable_resend_api_key(resend_key):
            mapping["TRANSACTIONAL_EMAIL_PROVIDER"] = "resend"
            mapping["RESEND_API_KEY"] = resend_key.strip()
        else:
            mapping["TRANSACTIONAL_EMAIL_PROVIDER"] = "null"
            mapping["RESEND_API_KEY"] = ""
    else:
        mapping["PUBLIC_APP_BASE_URL"] = PRODUCTION_PUBLIC_BASE_URL
        mapping["TRUSTED_HOSTS"] = PRODUCTION_TRUSTED_HOSTS
        mapping["LEGAL_PRIVACY_PUBLISHED_VERSION_ID"] = PRODUCTION_LEGAL_PRIVACY_VERSION
        mapping["LEGAL_TERMS_PUBLISHED_VERSION_ID"] = PRODUCTION_LEGAL_TERMS_VERSION
        mapping["PUBLIC_SUPPORT_EMAIL"] = PUBLIC_SUPPORT_EMAIL
        mapping["PUBLIC_PRIVACY_EMAIL"] = PUBLIC_PRIVACY_EMAIL
        mapping["APP_DEBUG"] = "false"
        mapping["LAUNCH_STRICT_STARTUP"] = "true"
        mapping["PERSISTENCE_BACKEND"] = "sqlalchemy"
        mapping["SEED_DEMO_DATA"] = "false"
        mapping["DEMO_LAUNCHER_ENABLED"] = "false"
        mapping["AWS_REGION"] = region
        if not _usable_resend_api_key(resend_key):
            raise SecretAssemblyError(
                "production requires a usable Resend API key in dealbrain/production/resend_api_key"
            )
        mapping["TRANSACTIONAL_EMAIL_PROVIDER"] = "resend"
        mapping["RESEND_API_KEY"] = resend_key.strip()

    tmp_prefix = f".{environment}.env."
    _atomic_write_env(env_file, mapping, tmp_prefix=tmp_prefix)
    mode = stat.S_IMODE(env_file.stat().st_mode)
    if mode != 0o600:
        raise SecretAssemblyError(f"env file mode is {oct(mode)}, expected 0o600")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--rds-endpoint-file", type=Path, required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--environment", default="staging", choices=("staging", "production"))
    parser.add_argument("--secrets-prefix", default=None)
    args = parser.parse_args(argv)
    prefix = args.secrets_prefix or f"dealbrain/{args.environment}"
    try:
        assemble(
            env_file=args.env_file,
            region=args.region,
            rds_nonsecret=args.rds_endpoint_file,
            secrets_prefix=prefix,
            environment=args.environment,
        )
    except SecretAssemblyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"ok: wrote runtime env to {args.env_file} (mode 0600)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
