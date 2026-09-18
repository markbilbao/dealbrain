#!/usr/bin/env python3
"""Select the canonical staging RDS instance for Deploy Staging.

Deploy Staging must target exactly ``dealbrain-staging-postgres``. Do not
discover instances by identifier substring, and do not take the first
result from a list of staging databases.

Invoke from the repository root as a module so ``scripts.*`` imports resolve:

  python -m scripts.deploy.select_canonical_staging_rds \\
    --input .deploy-work/rds-describe.json \\
    --out .deploy-work/rds-nonsecret.json

Does not print or persist secret values. Writes only non-secret RDS metadata
used to assemble DATABASE_URL on the staging host.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CANONICAL_STAGING_DB_INSTANCE_IDENTIFIER = "dealbrain-staging-postgres"
RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER = "dealbrain-staging-postgres-recovery"
EXPECTED_DB_INSTANCE_STATUS = "available"
EXPECTED_DB_NAME = "dealbrain"
EXPECTED_ENDPOINT_PORT = 5432
EXPECTED_MASTER_USER_SECRET_STATUS = "active"

NONSECRET_KEYS = ("endpoint", "port", "db_name", "master_user_secret_arn")


class CanonicalStagingRdsError(ValueError):
    """Raised when the canonical staging RDS instance is missing or unhealthy."""


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or isinstance(value, bool):
        raise CanonicalStagingRdsError(f"malformed {label}")
    return value


def _require_nonempty_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or isinstance(value, bool):
        raise CanonicalStagingRdsError(f"{label} must be a non-empty string")
    text = value.strip()
    if not text:
        raise CanonicalStagingRdsError(f"{label} must be a non-empty string")
    return text


def _require_exact_str(value: Any, expected: str, label: str) -> str:
    text = _require_nonempty_str(value, label)
    if text != expected:
        raise CanonicalStagingRdsError(f"{label} must be {expected!r}, got {text!r}")
    return text


def select_canonical_staging_rds(payload: Any) -> dict[str, Any]:
    """Parse a describe-db-instances payload and return rds-nonsecret fields.

    Fail closed unless the payload contains exactly the canonical staging
    instance and every health/identity gate passes. Never falls back to
    ``dealbrain-staging-postgres-recovery`` or any other identifier.
    """
    document = _require_mapping(payload, "describe-db-instances payload")
    instances = document.get("DBInstances")
    if not isinstance(instances, list):
        raise CanonicalStagingRdsError("DBInstances must be a list")
    try:
        (instance,) = instances
    except ValueError as exc:
        raise CanonicalStagingRdsError(
            f"expected exactly one DB instance, got {len(instances)}"
        ) from exc

    instance = _require_mapping(instance, "DBInstances entry")
    identifier = _require_nonempty_str(instance.get("DBInstanceIdentifier"), "DBInstanceIdentifier")
    if identifier == RECOVERY_STAGING_DB_INSTANCE_IDENTIFIER:
        raise CanonicalStagingRdsError(
            "refusing recovery copy dealbrain-staging-postgres-recovery; "
            "Deploy Staging must use dealbrain-staging-postgres"
        )
    _require_exact_str(
        identifier,
        CANONICAL_STAGING_DB_INSTANCE_IDENTIFIER,
        "DBInstanceIdentifier",
    )
    _require_exact_str(
        instance.get("DBInstanceStatus"),
        EXPECTED_DB_INSTANCE_STATUS,
        "DBInstanceStatus",
    )
    _require_exact_str(instance.get("DBName"), EXPECTED_DB_NAME, "DBName")

    publicly_accessible = instance.get("PubliclyAccessible")
    if publicly_accessible is not False:
        raise CanonicalStagingRdsError("PubliclyAccessible must be false for canonical staging RDS")

    endpoint = _require_mapping(instance.get("Endpoint"), "Endpoint")
    address = _require_nonempty_str(endpoint.get("Address"), "Endpoint.Address")
    port = endpoint.get("Port")
    if isinstance(port, bool) or not isinstance(port, int) or port != EXPECTED_ENDPOINT_PORT:
        raise CanonicalStagingRdsError(
            f"Endpoint.Port must equal {EXPECTED_ENDPOINT_PORT}, got {port!r}"
        )

    secret = _require_mapping(instance.get("MasterUserSecret"), "MasterUserSecret")
    secret_arn = _require_nonempty_str(secret.get("SecretArn"), "MasterUserSecret.SecretArn")
    _require_exact_str(
        secret.get("SecretStatus"),
        EXPECTED_MASTER_USER_SECRET_STATUS,
        "MasterUserSecret.SecretStatus",
    )

    return {
        "endpoint": address,
        "port": EXPECTED_ENDPOINT_PORT,
        "db_name": EXPECTED_DB_NAME,
        "master_user_secret_arn": secret_arn,
    }


def load_describe_payload(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CanonicalStagingRdsError(f"malformed JSON: {exc}") from exc


def write_rds_nonsecret(path: Path, metadata: dict[str, Any]) -> None:
    missing = [key for key in NONSECRET_KEYS if key not in metadata]
    if missing:
        raise CanonicalStagingRdsError(f"rds-nonsecret missing keys: {missing}")
    extra = sorted(set(metadata) - set(NONSECRET_KEYS))
    if extra:
        raise CanonicalStagingRdsError(f"rds-nonsecret has unexpected keys: {extra}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="-",
        help="Path to describe-db-instances JSON, or '-' for stdin",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Path to write rds-nonsecret.json (endpoint/port/db_name/secret ARN only)",
    )
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            text = sys.stdin.read()
        else:
            text = Path(args.input).read_text(encoding="utf-8")
        metadata = select_canonical_staging_rds(load_describe_payload(text))
        write_rds_nonsecret(args.out, metadata)
    except (OSError, CanonicalStagingRdsError) as exc:
        print(f"FAIL: canonical staging RDS rejected ({exc})", file=sys.stderr)
        return 1
    print(
        "ok: canonical staging RDS "
        f"{CANONICAL_STAGING_DB_INSTANCE_IDENTIFIER} available "
        f"port={EXPECTED_ENDPOINT_PORT} db={EXPECTED_DB_NAME}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
