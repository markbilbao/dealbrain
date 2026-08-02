"""Sprint 25b.3 staging deploy evidence creation and integrity validation.

Append-only evidence separate from the immutable build release-manifest.
Checksum model mirrors scripts/release/manifest.py (evidence_sha256 null during hash).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

# Host bootstrap runs Python 3.9 — prefer timezone.utc (UTC alias is 3.11+).
# ruff: noqa: UP017

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
    from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

    _HAS_JSONSCHEMA = True
except ImportError:  # Host bootstrap ships stdlib-only Python3.
    Draft202012Validator = None  # type: ignore[assignment, misc]
    SchemaError = Exception  # type: ignore[assignment, misc]
    JsonSchemaValidationError = Exception  # type: ignore[assignment, misc]
    _HAS_JSONSCHEMA = False

SCHEMA_VERSION: Final[int] = 1


def resolve_schema_path(module_file: Path | None = None) -> Path:
    """Resolve schema for repo layout and flat release-bundle ``bin/`` layout."""
    here = (module_file or Path(__file__)).resolve().parent
    candidates = (
        here / "staging-deploy-evidence.schema.json",
        here.parents[1] / "schemas" / "staging-deploy-evidence.schema.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[-1]


# Resolved at import for callers/tests; ``_load_schema`` re-resolves per process.
SCHEMA_PATH: Final[Path] = resolve_schema_path()

ALLOWED_STATUSES: Final[frozenset[str]] = frozenset({"staging_ok", "failed"})
GIT_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")
RELEASE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$")
SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
UTC_Z_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
# Docker image Created may include fractional seconds; accept and require parseable.
TIMESTAMP_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"
)
RUN_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9]+$")
GHCR_REPO_RE: Final[re.Pattern[str]] = re.compile(
    r"^ghcr\.io/[a-z0-9]([a-z0-9._-]*/)+[a-z0-9._-]+$"
)
INSTANCE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^i-[0-9a-f]{8,17}$")
ACCOUNT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9]{12}$")
MIGRATION_REV_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-fA-Z][0-9a-zA-Z_:-]{0,255}$")
# Secret-bearing values (URLs / credential assignments) — never accept in evidence.
SECRET_VALUE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:postgresql(?:\+\w+)?|postgres(?:\+\w+)?|mysql(?:\+\w+)?"
    r"|mariadb(?:\+\w+)?|sqlite(?:\+\w+)?|mssql(?:\+\w+)?)://"
    r"|DATABASE_URL\s*[:=]"
    r"|\b(?:password|passwd|secret|token|api_key|access_key)\s*[:=]\s*\S"
)
PRODUCTION_VALUE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:^|[^a-z0-9])production(?:[^a-z0-9]|$)"
)

FORBIDDEN_FIELD_FRAGMENTS: Final[tuple[str, ...]] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "private_key",
    "database_url",
    "access_key",
)

# Exact staging-deploy-evidence.schema.json contract (stdlib host fallback).
# Keep in lockstep with schemas/staging-deploy-evidence.schema.json — drift fails closed.
REQUIRED_EVIDENCE_KEYS: Final[tuple[str, ...]] = (
    "schema_version",
    "release_id",
    "git_sha",
    "image_repository",
    "image_digest",
    "source_manifest_sha256",
    "deploy_workflow_run_id",
    "aws_account_id",
    "aws_region",
    "assumed_role_arn",
    "role_session_name",
    "ec2_instance_id",
    "ssm_command_id",
    "migration_revision_before",
    "migration_revision_after",
    "localhost_live",
    "localhost_ready",
    "alb_target_healthy",
    "smoke_ok",
    "image_id",
    "repo_digest",
    "image_created_at",
    "deployment_started_at",
    "deployment_finished_at",
    "deployment_duration_seconds",
    "final_status",
    "failure_reason",
    "evidence_sha256",
)
ALLOWED_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(REQUIRED_EVIDENCE_KEYS)

# JSON-Schema-shaped field contract: types are JSON types (boolean ≠ integer).
_EVIDENCE_FIELD_CONTRACT: Final[dict[str, dict[str, Any]]] = {
    "schema_version": {"types": ("integer",), "const": 1},
    "release_id": {"types": ("string",), "pattern": RELEASE_ID_RE},
    "git_sha": {"types": ("string",), "pattern": GIT_SHA_RE},
    "image_repository": {"types": ("string",), "pattern": GHCR_REPO_RE},
    "image_digest": {"types": ("string",), "pattern": DIGEST_RE},
    "source_manifest_sha256": {"types": ("string",), "pattern": SHA256_HEX_RE},
    "deploy_workflow_run_id": {"types": ("string",), "pattern": RUN_ID_RE},
    "aws_account_id": {"types": ("string",), "pattern": ACCOUNT_RE},
    "aws_region": {"types": ("string",), "min_length": 1},
    "assumed_role_arn": {"types": ("string",), "min_length": 1},
    "role_session_name": {"types": ("string",), "min_length": 1},
    "ec2_instance_id": {"types": ("string",), "min_length": 1},
    "ssm_command_id": {"types": ("string", "null")},
    "migration_revision_before": {"types": ("string", "null")},
    "migration_revision_after": {"types": ("string", "null")},
    "localhost_live": {"types": ("boolean", "null")},
    "localhost_ready": {"types": ("boolean", "null")},
    "alb_target_healthy": {"types": ("boolean", "null")},
    "smoke_ok": {"types": ("boolean", "null")},
    "image_id": {"types": ("string", "null")},
    "repo_digest": {"types": ("string", "null")},
    "image_created_at": {"types": ("string", "null")},
    "deployment_started_at": {"types": ("string",), "pattern": UTC_Z_RE},
    "deployment_finished_at": {"types": ("string",), "pattern": UTC_Z_RE},
    "deployment_duration_seconds": {"types": ("integer",), "minimum": 0},
    "final_status": {"types": ("string",), "enum": ALLOWED_STATUSES},
    "failure_reason": {"types": ("string", "null")},
    "evidence_sha256": {"types": ("string",), "pattern": SHA256_HEX_RE},
}

# Post-gate failure reasons that may coexist with all health gates true.
POST_GATE_FAILURE_PREFIXES: Final[tuple[str, ...]] = (
    "post_gate_",
    "evidence_upload_",
    "deploy_version_",
    "symlink_",
)


class EvidenceError(ValueError):
    """Raised when staging deploy evidence fails validation."""


def utc_now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonicalize_for_checksum(payload: dict[str, Any]) -> str:
    data = dict(payload)
    data["evidence_sha256"] = None
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_evidence_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonicalize_for_checksum(payload).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    path = resolve_schema_path()
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _reject_secret_like_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for fragment in FORBIDDEN_FIELD_FRAGMENTS:
                if fragment in lowered:
                    raise EvidenceError(
                        f"secret-like field name forbidden at {path}.{key}: {key!r}"
                    )
            _reject_secret_like_keys(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _reject_secret_like_keys(item, f"{path}[{idx}]")
    elif isinstance(obj, str):
        if SECRET_VALUE_RE.search(obj):
            raise EvidenceError(f"secret-bearing value forbidden at {path or '<root>'}")
        if PRODUCTION_VALUE_RE.search(obj):
            raise EvidenceError(f"production environment value forbidden at {path or '<root>'}")


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    if type(value) is float:
        return "number"
    if type(value) is str:
        return "string"
    if type(value) is list:
        return "array"
    if type(value) is dict:
        return "object"
    return type(value).__name__


def _normalize_schema_types(type_field: Any) -> tuple[str, ...]:
    if isinstance(type_field, str):
        return (type_field,)
    if isinstance(type_field, list) and all(isinstance(item, str) for item in type_field):
        return tuple(type_field)
    raise EvidenceError("unsupported schema type declaration")


def _assert_supported_evidence_schema(schema: dict[str, Any]) -> None:
    """Fail closed if the on-disk schema drifts from the reviewed stdlib contract."""
    if schema.get("type") != "object":
        raise EvidenceError("unsupported evidence schema: root type")
    if schema.get("additionalProperties") is not False:
        raise EvidenceError("unsupported evidence schema: additionalProperties")
    required = schema.get("required")
    if required != list(REQUIRED_EVIDENCE_KEYS):
        raise EvidenceError("unsupported evidence schema: required properties")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or set(properties) != ALLOWED_EVIDENCE_KEYS:
        raise EvidenceError("unsupported evidence schema: properties set")

    for key, contract in _EVIDENCE_FIELD_CONTRACT.items():
        prop = properties[key]
        if not isinstance(prop, dict):
            raise EvidenceError(f"unsupported evidence schema: property {key}")
        schema_types = _normalize_schema_types(prop.get("type"))
        if set(schema_types) != set(contract["types"]):
            raise EvidenceError(f"unsupported evidence schema: types for {key}")
        if "const" in contract and prop.get("const") != contract["const"]:
            raise EvidenceError(f"unsupported evidence schema: const for {key}")
        if "enum" in contract and set(prop.get("enum", ())) != set(contract["enum"]):
            raise EvidenceError(f"unsupported evidence schema: enum for {key}")
        if "pattern" in contract and prop.get("pattern") != contract["pattern"].pattern:
            raise EvidenceError(f"unsupported evidence schema: pattern for {key}")
        if "min_length" in contract and prop.get("minLength") != contract["min_length"]:
            raise EvidenceError(f"unsupported evidence schema: minLength for {key}")
        if "minimum" in contract and prop.get("minimum") != contract["minimum"]:
            raise EvidenceError(f"unsupported evidence schema: minimum for {key}")


def _validate_field_against_contract(key: str, value: Any, contract: dict[str, Any]) -> None:
    allowed_types: tuple[str, ...] = contract["types"]
    actual = _json_type_name(value)
    if actual not in allowed_types:
        raise EvidenceError(
            f"schema validation failed: {key} type {actual!r} not in {allowed_types}"
        )
    if value is None:
        return
    if "const" in contract and value != contract["const"]:
        raise EvidenceError(f"schema validation failed: {key} must be {contract['const']!r}")
    if "enum" in contract and value not in contract["enum"]:
        raise EvidenceError(f"schema validation failed: {key} invalid enum value")
    if actual == "string":
        pattern = contract.get("pattern")
        if pattern is not None and not pattern.fullmatch(value):
            raise EvidenceError(f"schema validation failed: {key} failed pattern")
        min_length = contract.get("min_length")
        if min_length is not None and len(value) < min_length:
            raise EvidenceError(f"schema validation failed: {key} shorter than minLength")
    if actual == "integer":
        minimum = contract.get("minimum")
        if minimum is not None and value < minimum:
            raise EvidenceError(f"schema validation failed: {key} below minimum")


def _validate_evidence_schema_stdlib(payload: dict[str, Any]) -> None:
    """Strict stdlib-only validator for the fixed evidence JSON Schema contract."""
    schema_path = resolve_schema_path()
    if not schema_path.is_file():
        raise EvidenceError("evidence schema file missing; refusing validation")
    schema = _load_schema()
    _assert_supported_evidence_schema(schema)

    unknown = sorted(set(payload) - ALLOWED_EVIDENCE_KEYS)
    if unknown:
        raise EvidenceError(
            f"schema validation failed: additional properties not allowed: {unknown}"
        )
    missing = [key for key in REQUIRED_EVIDENCE_KEYS if key not in payload]
    if missing:
        raise EvidenceError(f"schema validation failed: missing required properties: {missing}")

    for key in REQUIRED_EVIDENCE_KEYS:
        _validate_field_against_contract(key, payload[key], _EVIDENCE_FIELD_CONTRACT[key])


def _parse_utc_z(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _require_nonempty_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{key} must be a non-empty string for staging_ok")
    return value


def _validate_staging_ok_semantics(payload: dict[str, Any]) -> None:
    reason = payload.get("failure_reason")
    if reason not in (None, ""):
        raise EvidenceError("staging_ok requires failure_reason null or empty")

    after = payload.get("migration_revision_after")
    if not isinstance(after, str) or not after.strip():
        raise EvidenceError("staging_ok requires non-empty migration_revision_after")
    if not MIGRATION_REV_RE.fullmatch(after.strip()):
        raise EvidenceError("staging_ok migration_revision_after failed migration contract")

    before = payload.get("migration_revision_before")
    if (
        before is not None
        and before != ""
        and (not isinstance(before, str) or not MIGRATION_REV_RE.fullmatch(before.strip()))
    ):
        raise EvidenceError("staging_ok migration_revision_before failed migration contract")

    for gate in ("localhost_live", "localhost_ready", "alb_target_healthy", "smoke_ok"):
        if payload.get(gate) is not True:
            raise EvidenceError(f"staging_ok requires {gate} == true")

    image_id = _require_nonempty_str(payload, "image_id")
    if not image_id.startswith("sha256:"):
        raise EvidenceError("staging_ok image_id must be a sha256 digest id")

    repo_digest = _require_nonempty_str(payload, "repo_digest")
    image_digest = str(payload.get("image_digest", ""))
    expected_suffix = f"@{image_digest}"
    if not repo_digest.endswith(expected_suffix) and image_digest not in repo_digest:
        raise EvidenceError("staging_ok repo_digest must match image_digest authority")

    created = _require_nonempty_str(payload, "image_created_at")
    if not TIMESTAMP_RE.fullmatch(created) and not UTC_Z_RE.fullmatch(created):
        raise EvidenceError("staging_ok image_created_at must be a valid timestamp")

    started = _require_nonempty_str(payload, "deployment_started_at")
    finished = _require_nonempty_str(payload, "deployment_finished_at")
    if not UTC_Z_RE.fullmatch(started):
        raise EvidenceError("staging_ok deployment_started_at must be UTC Z")
    if not UTC_Z_RE.fullmatch(finished):
        raise EvidenceError("staging_ok deployment_finished_at must be UTC Z")

    duration = payload.get("deployment_duration_seconds")
    if not isinstance(duration, int) or duration < 0:
        raise EvidenceError("staging_ok deployment_duration_seconds must be >= 0")
    start_dt = _parse_utc_z(started)
    finish_dt = _parse_utc_z(finished)
    if finish_dt < start_dt:
        raise EvidenceError("deployment_finished_at must be >= deployment_started_at")
    delta = int((finish_dt - start_dt).total_seconds())
    if abs(delta - duration) > 5:
        raise EvidenceError(
            f"deployment_duration_seconds inconsistent with timestamps "
            f"(got {duration}, expected ~{delta})"
        )

    instance_id = _require_nonempty_str(payload, "ec2_instance_id")
    if not INSTANCE_ID_RE.fullmatch(instance_id):
        raise EvidenceError("staging_ok requires a valid EC2 instance id")

    ssm_command_id = payload.get("ssm_command_id")
    if not isinstance(ssm_command_id, str) or not ssm_command_id.strip():
        raise EvidenceError("staging_ok requires non-empty ssm_command_id")

    _require_nonempty_str(payload, "assumed_role_arn")
    _require_nonempty_str(payload, "role_session_name")

    account = _require_nonempty_str(payload, "aws_account_id")
    if not ACCOUNT_RE.fullmatch(account):
        raise EvidenceError("staging_ok requires a 12-digit aws_account_id")
    _require_nonempty_str(payload, "aws_region")


def _validate_failed_semantics(payload: dict[str, Any]) -> None:
    reason = payload.get("failure_reason")
    if not isinstance(reason, str) or not reason.strip():
        raise EvidenceError("failed status requires non-empty failure_reason")

    gates = (
        payload.get("localhost_live") is True
        and payload.get("localhost_ready") is True
        and payload.get("alb_target_healthy") is True
        and payload.get("smoke_ok") is True
    )
    if gates and not any(reason.startswith(prefix) for prefix in POST_GATE_FAILURE_PREFIXES):
        raise EvidenceError(
            "failed evidence must not report all success gates true "
            "unless failure_reason records an explicit post-gate stage"
        )


def validate_evidence(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise EvidenceError("evidence must be a JSON object")
    _reject_secret_like_keys(payload)
    if _HAS_JSONSCHEMA:
        try:
            Draft202012Validator.check_schema(_load_schema())
            Draft202012Validator(_load_schema()).validate(payload)
        except (JsonSchemaValidationError, SchemaError) as exc:
            raise EvidenceError(f"schema validation failed: {exc}") from exc
    else:
        # Host bootstrap is stdlib-only: enforce the reviewed schema contract explicitly.
        _validate_evidence_schema_stdlib(payload)

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("unsupported schema_version")
    if not RELEASE_ID_RE.fullmatch(str(payload.get("release_id", ""))):
        raise EvidenceError("invalid release_id")
    if not GIT_SHA_RE.fullmatch(str(payload.get("git_sha", ""))):
        raise EvidenceError("invalid git_sha")
    if not GHCR_REPO_RE.fullmatch(str(payload.get("image_repository", ""))):
        raise EvidenceError("invalid image_repository")
    if not DIGEST_RE.fullmatch(str(payload.get("image_digest", ""))):
        raise EvidenceError("invalid image_digest")
    if not SHA256_HEX_RE.fullmatch(str(payload.get("source_manifest_sha256", ""))):
        raise EvidenceError("invalid source_manifest_sha256")
    if not RUN_ID_RE.fullmatch(str(payload.get("deploy_workflow_run_id", ""))):
        raise EvidenceError("invalid deploy_workflow_run_id")
    if payload.get("final_status") not in ALLOWED_STATUSES:
        raise EvidenceError("invalid final_status")
    for key in ("deployment_started_at", "deployment_finished_at"):
        if not UTC_Z_RE.fullmatch(str(payload.get(key, ""))):
            raise EvidenceError(f"invalid {key}")
    # bool is a subclass of int — require an exact integer (JSON Schema parity).
    if type(payload.get("deployment_duration_seconds")) is not int:
        raise EvidenceError("deployment_duration_seconds must be int")
    if payload["deployment_duration_seconds"] < 0:
        raise EvidenceError("deployment_duration_seconds must be >= 0")

    expected = compute_evidence_sha256(payload)
    actual = payload.get("evidence_sha256")
    if actual != expected:
        raise EvidenceError(f"evidence_sha256 mismatch: expected {expected}, got {actual!r}")

    status = payload.get("final_status")
    if status == "staging_ok":
        _validate_staging_ok_semantics(payload)
    elif status == "failed":
        _validate_failed_semantics(payload)


def validate_evidence_bindings(
    payload: dict[str, Any],
    *,
    release_id: str,
    git_sha: str,
    image_digest: str,
    image_repository: str,
    source_manifest_sha256: str,
    deploy_workflow_run_id: str,
    aws_account_id: str,
    aws_region: str,
    ec2_instance_id: str,
    ssm_command_id: str,
    require_staging_ok: bool = True,
) -> None:
    """Reject evidence bound to a different run/release/instance/digest/SHA."""
    validate_evidence(payload)
    checks = {
        "release_id": release_id,
        "git_sha": git_sha,
        "image_digest": image_digest,
        "image_repository": image_repository.rstrip("/").lower(),
        "source_manifest_sha256": source_manifest_sha256,
        "deploy_workflow_run_id": str(deploy_workflow_run_id),
        "aws_account_id": str(aws_account_id),
        "aws_region": aws_region,
        "ec2_instance_id": ec2_instance_id,
        "ssm_command_id": ssm_command_id,
    }
    for key, expected in checks.items():
        actual = payload.get(key)
        if actual != expected:
            raise EvidenceError(f"evidence binding mismatch for {key}: {actual!r} != {expected!r}")
    if require_staging_ok and payload.get("final_status") != "staging_ok":
        raise EvidenceError(
            f"authoritative evidence final_status must be staging_ok, "
            f"got {payload.get('final_status')!r}"
        )


def create_evidence(
    *,
    release_id: str,
    git_sha: str,
    image_repository: str,
    image_digest: str,
    source_manifest_sha256: str,
    deploy_workflow_run_id: str,
    aws_account_id: str,
    aws_region: str,
    assumed_role_arn: str,
    role_session_name: str,
    ec2_instance_id: str,
    ssm_command_id: str | None,
    migration_revision_before: str | None,
    migration_revision_after: str | None,
    localhost_live: bool | None,
    localhost_ready: bool | None,
    alb_target_healthy: bool | None,
    smoke_ok: bool | None,
    image_id: str | None,
    repo_digest: str | None,
    image_created_at: str | None,
    deployment_started_at: str,
    deployment_finished_at: str,
    deployment_duration_seconds: int,
    final_status: str,
    failure_reason: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "release_id": release_id,
        "git_sha": git_sha,
        "image_repository": image_repository.rstrip("/").lower(),
        "image_digest": image_digest,
        "source_manifest_sha256": source_manifest_sha256,
        "deploy_workflow_run_id": str(deploy_workflow_run_id),
        "aws_account_id": str(aws_account_id),
        "aws_region": aws_region,
        "assumed_role_arn": assumed_role_arn,
        "role_session_name": role_session_name,
        "ec2_instance_id": ec2_instance_id,
        "ssm_command_id": ssm_command_id,
        "migration_revision_before": migration_revision_before,
        "migration_revision_after": migration_revision_after,
        "localhost_live": localhost_live,
        "localhost_ready": localhost_ready,
        "alb_target_healthy": alb_target_healthy,
        "smoke_ok": smoke_ok,
        "image_id": image_id,
        "repo_digest": repo_digest,
        "image_created_at": image_created_at,
        "deployment_started_at": deployment_started_at,
        "deployment_finished_at": deployment_finished_at,
        "deployment_duration_seconds": int(deployment_duration_seconds),
        "final_status": final_status,
        "failure_reason": failure_reason,
        "evidence_sha256": None,
    }
    payload["evidence_sha256"] = compute_evidence_sha256(payload)
    validate_evidence(payload)
    return payload


def write_evidence(path: Path, payload: dict[str, Any]) -> None:
    validate_evidence(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(payload["evidence_sha256"] + "\n", encoding="utf-8")


def load_evidence(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_evidence(payload)
    return payload
