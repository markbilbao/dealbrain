#!/usr/bin/env python3
"""Assemble staging Compose runtime env from Secrets Manager (host-side only).

Never prints secret values. Writes atomically to a 0600 env file.
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
from urllib.parse import quote_plus


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


def _atomic_write_env(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".staging.env.", dir=str(path.parent))
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
) -> None:
    if "production" in secrets_prefix:
        raise SecretAssemblyError("refusing to read production secrets on staging host")

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

    # Required application secrets
    app_secret_key = _get_plain_secret(f"{secrets_prefix}/app_secret_key", region)
    cors_origins = _get_plain_secret(f"{secrets_prefix}/cors_origins", region)
    if not app_secret_key.strip():
        raise SecretAssemblyError("app_secret_key is empty")
    if not cors_origins.strip():
        raise SecretAssemblyError("cors_origins is empty")

    mapping: dict[str, str] = {
        "APP_ENV": "staging",
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
            mapping[env_name] = _get_plain_secret(f"{secrets_prefix}/{leaf}", region)
        except SecretAssemblyError:
            mapping[env_name] = ""

    _atomic_write_env(env_file, mapping)
    mode = stat.S_IMODE(env_file.stat().st_mode)
    if mode != 0o600:
        raise SecretAssemblyError(f"env file mode is {oct(mode)}, expected 0o600")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--rds-endpoint-file", type=Path, required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--secrets-prefix", default="dealbrain/staging")
    args = parser.parse_args(argv)
    try:
        assemble(
            env_file=args.env_file,
            region=args.region,
            rds_nonsecret=args.rds_endpoint_file,
            secrets_prefix=args.secrets_prefix,
        )
    except SecretAssemblyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"ok: wrote runtime env to {args.env_file} (mode 0600)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
