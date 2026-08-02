"""Sprint 25b.5 staging rollback evidence creation and integrity validation.

Host-authored evidence separate from deploy evidence and the build release-manifest.
Checksum model mirrors scripts/deploy/evidence.py (evidence_sha256 null during hash).
"""

from __future__ import annotations

import hashlib
import json
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


def _load_deploy_evidence_module():
    """Load deploy evidence helpers from package (repo) or sibling (host bundle)."""
    import importlib.util

    # Prefer the package import so EvidenceError identity matches scripts.deploy.evidence.
    try:
        from scripts.deploy import evidence as module

        return module
    except ImportError:
        pass

    sibling = Path(__file__).resolve().parent / "evidence.py"
    if sibling.is_file():
        spec = importlib.util.spec_from_file_location(
            "dealbrain_staging_deploy_evidence_for_rollback", sibling
        )
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ImportError("canonical deploy evidence module unavailable for rollback evidence")


_deploy_evidence = _load_deploy_evidence_module()
ACCOUNT_RE = _deploy_evidence.ACCOUNT_RE
DIGEST_RE = _deploy_evidence.DIGEST_RE
GIT_SHA_RE = _deploy_evidence.GIT_SHA_RE
GHCR_REPO_RE = _deploy_evidence.GHCR_REPO_RE
INSTANCE_ID_RE = _deploy_evidence.INSTANCE_ID_RE
MIGRATION_REV_RE = _deploy_evidence.MIGRATION_REV_RE
PRODUCTION_VALUE_RE = _deploy_evidence.PRODUCTION_VALUE_RE
RELEASE_ID_RE = _deploy_evidence.RELEASE_ID_RE
RUN_ID_RE = _deploy_evidence.RUN_ID_RE
SECRET_VALUE_RE = _deploy_evidence.SECRET_VALUE_RE
SHA256_HEX_RE = _deploy_evidence.SHA256_HEX_RE
UTC_Z_RE = _deploy_evidence.UTC_Z_RE
EvidenceError = _deploy_evidence.EvidenceError
FORBIDDEN_FIELD_FRAGMENTS = _deploy_evidence.FORBIDDEN_FIELD_FRAGMENTS
normalize_alembic_revision = _deploy_evidence.normalize_alembic_revision

SCHEMA_VERSION: Final[int] = 1
EVIDENCE_TYPE: Final[str] = "staging_rollback"
ALLOWED_STATUSES: Final[frozenset[str]] = frozenset({"rollback_ok", "failed"})

POST_GATE_FAILURE_PREFIXES: Final[tuple[str, ...]] = (
    "post_gate_",
    "evidence_upload_",
    "deploy_version_",
    "symlink_",
    "post_replacement_",
    "release_alignment_",
    "pointer_",
)


def resolve_rollback_schema_path(module_file: Path | None = None) -> Path:
    """Resolve schema for repo layout and flat release-bundle ``bin/`` layout."""
    here = (module_file or Path(__file__)).resolve().parent
    candidates = (
        here / "staging-rollback-evidence.schema.json",
        here.parents[1] / "schemas" / "staging-rollback-evidence.schema.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[-1]


SCHEMA_PATH: Final[Path] = resolve_rollback_schema_path()

REQUIRED_KEYS: Final[tuple[str, ...]] = (
    "schema_version",
    "evidence_type",
    "rollback_workflow_run_id",
    "aws_account_id",
    "aws_region",
    "assumed_role_arn",
    "role_session_name",
    "ec2_instance_id",
    "ssm_command_id",
    "rollback_started_at",
    "rollback_finished_at",
    "rollback_duration_seconds",
    "source_release_id",
    "source_image_digest",
    "target_release_id",
    "target_image_digest",
    "target_git_sha",
    "target_image_repository",
    "target_manifest_sha256",
    "migration_revision_before",
    "migration_revision_after",
    "target_migration_revision_authority",
    "current_pointer_before",
    "current_pointer_after",
    "previous_pointer_before",
    "previous_pointer_after",
    "running_digest_after",
    "localhost_live",
    "localhost_ready",
    "alb_target_healthy",
    "final_status",
    "failure_reason",
    "evidence_sha256",
)
ALLOWED_KEYS: Final[frozenset[str]] = frozenset(REQUIRED_KEYS)

_FIELD_CONTRACT: Final[dict[str, dict[str, Any]]] = {
    "schema_version": {"types": ("integer",), "const": 1},
    "evidence_type": {"types": ("string",), "const": EVIDENCE_TYPE},
    "rollback_workflow_run_id": {"types": ("string",), "pattern": RUN_ID_RE},
    "aws_account_id": {"types": ("string",), "pattern": ACCOUNT_RE},
    "aws_region": {"types": ("string",), "min_length": 1},
    "assumed_role_arn": {"types": ("string",), "min_length": 1},
    "role_session_name": {"types": ("string",), "min_length": 1},
    "ec2_instance_id": {"types": ("string",), "min_length": 1},
    "ssm_command_id": {"types": ("string", "null")},
    "rollback_started_at": {"types": ("string",), "pattern": UTC_Z_RE},
    "rollback_finished_at": {"types": ("string",), "pattern": UTC_Z_RE},
    "rollback_duration_seconds": {"types": ("integer",), "minimum": 0},
    "source_release_id": {"types": ("string", "null"), "pattern": RELEASE_ID_RE},
    "source_image_digest": {"types": ("string", "null"), "pattern": DIGEST_RE},
    "target_release_id": {"types": ("string",), "pattern": RELEASE_ID_RE},
    "target_image_digest": {"types": ("string",), "pattern": DIGEST_RE},
    "target_git_sha": {"types": ("string",), "pattern": GIT_SHA_RE},
    "target_image_repository": {"types": ("string",), "pattern": GHCR_REPO_RE},
    "target_manifest_sha256": {"types": ("string",), "pattern": SHA256_HEX_RE},
    "migration_revision_before": {"types": ("string", "null")},
    "migration_revision_after": {"types": ("string", "null")},
    "target_migration_revision_authority": {
        "types": ("string", "null"),
        "enum": ("deploy_version", "validated_prior_staging_evidence", None),
    },
    "current_pointer_before": {"types": ("string", "null")},
    "current_pointer_after": {"types": ("string", "null")},
    "previous_pointer_before": {"types": ("string", "null")},
    "previous_pointer_after": {"types": ("string", "null")},
    "running_digest_after": {"types": ("string", "null")},
    "localhost_live": {"types": ("boolean", "null")},
    "localhost_ready": {"types": ("boolean", "null")},
    "alb_target_healthy": {"types": ("boolean", "null")},
    "final_status": {"types": ("string",), "enum": ALLOWED_STATUSES},
    "failure_reason": {"types": ("string", "null")},
    "evidence_sha256": {"types": ("string",), "pattern": SHA256_HEX_RE},
}


def canonicalize_for_checksum(payload: dict[str, Any]) -> str:
    data = dict(payload)
    data["evidence_sha256"] = None
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_rollback_evidence_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonicalize_for_checksum(payload).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    path = resolve_rollback_schema_path()
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


def _validate_field(key: str, value: Any, contract: dict[str, Any]) -> None:
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


def _validate_stdlib(payload: dict[str, Any]) -> None:
    schema_path = resolve_rollback_schema_path()
    if not schema_path.is_file():
        raise EvidenceError("rollback evidence schema file missing; refusing validation")
    unknown = sorted(set(payload) - ALLOWED_KEYS)
    if unknown:
        raise EvidenceError(
            f"schema validation failed: additional properties not allowed: {unknown}"
        )
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise EvidenceError(f"schema validation failed: missing required properties: {missing}")
    for key in REQUIRED_KEYS:
        _validate_field(key, payload[key], _FIELD_CONTRACT[key])


def _parse_utc_z(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _require_nonempty_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{key} must be a non-empty string for rollback_ok")
    return value


def _validate_rollback_ok(payload: dict[str, Any]) -> None:
    if payload.get("failure_reason") not in (None, ""):
        raise EvidenceError("rollback_ok requires failure_reason null or empty")

    for gate in ("localhost_live", "localhost_ready", "alb_target_healthy"):
        if payload.get(gate) is not True:
            raise EvidenceError(f"rollback_ok requires {gate} == true")

    after = payload.get("migration_revision_after")
    if not isinstance(after, str) or not after.strip():
        raise EvidenceError("rollback_ok requires non-empty migration_revision_after")
    if not MIGRATION_REV_RE.fullmatch(after.strip()):
        raise EvidenceError("rollback_ok migration_revision_after failed migration contract")
    authority = payload.get("target_migration_revision_authority")
    if authority not in ("deploy_version", "validated_prior_staging_evidence"):
        raise EvidenceError(
            "rollback_ok requires target_migration_revision_authority "
            "deploy_version|validated_prior_staging_evidence"
        )

    before = payload.get("migration_revision_before")
    if (
        before is not None
        and before != ""
        and (not isinstance(before, str) or not MIGRATION_REV_RE.fullmatch(before.strip()))
    ):
        raise EvidenceError("rollback_ok migration_revision_before failed migration contract")
    if before and after and before.strip() != after.strip():
        raise EvidenceError(
            "rollback_ok requires migration_revision_before == migration_revision_after "
            "(database is never downgraded during rollback)"
        )

    running = _require_nonempty_str(payload, "running_digest_after")
    if running != payload.get("target_image_digest"):
        raise EvidenceError("rollback_ok running_digest_after must equal target_image_digest")

    current_after = _require_nonempty_str(payload, "current_pointer_after")
    if not current_after.endswith(f"/{payload['target_release_id']}"):
        raise EvidenceError("rollback_ok current_pointer_after must point at target release")

    source_rid = payload.get("source_release_id")
    previous_after = payload.get("previous_pointer_after")
    if (
        isinstance(source_rid, str)
        and source_rid
        and (not isinstance(previous_after, str) or not previous_after.endswith(f"/{source_rid}"))
    ):
        raise EvidenceError(
            "rollback_ok previous_pointer_after must point at displaced source release"
        )

    instance_id = _require_nonempty_str(payload, "ec2_instance_id")
    if not INSTANCE_ID_RE.fullmatch(instance_id):
        raise EvidenceError("rollback_ok requires a valid EC2 instance id")

    ssm_command_id = payload.get("ssm_command_id")
    if not isinstance(ssm_command_id, str) or not ssm_command_id.strip():
        raise EvidenceError("rollback_ok requires non-empty ssm_command_id")

    started = _require_nonempty_str(payload, "rollback_started_at")
    finished = _require_nonempty_str(payload, "rollback_finished_at")
    duration = payload.get("rollback_duration_seconds")
    if not isinstance(duration, int) or duration < 0:
        raise EvidenceError("rollback_ok rollback_duration_seconds must be >= 0")
    start_dt = _parse_utc_z(started)
    finish_dt = _parse_utc_z(finished)
    if finish_dt < start_dt:
        raise EvidenceError("rollback_finished_at must be >= rollback_started_at")
    delta = int((finish_dt - start_dt).total_seconds())
    if abs(delta - duration) > 5:
        raise EvidenceError(
            f"rollback_duration_seconds inconsistent with timestamps "
            f"(got {duration}, expected ~{delta})"
        )


def _validate_failed(payload: dict[str, Any]) -> None:
    reason = payload.get("failure_reason")
    if not isinstance(reason, str) or not reason.strip():
        raise EvidenceError("failed status requires non-empty failure_reason")
    if payload.get("final_status") == "rollback_ok":
        raise EvidenceError("failed evidence cannot report rollback_ok")
    gates = (
        payload.get("localhost_live") is True
        and payload.get("localhost_ready") is True
        and payload.get("alb_target_healthy") is True
    )
    if gates and not any(reason.startswith(prefix) for prefix in POST_GATE_FAILURE_PREFIXES):
        raise EvidenceError(
            "failed evidence must not report all success gates true "
            "unless failure_reason records an explicit post-gate stage"
        )


def validate_rollback_evidence(payload: dict[str, Any]) -> None:
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
        _validate_stdlib(payload)

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("unsupported schema_version")
    if payload.get("evidence_type") != EVIDENCE_TYPE:
        raise EvidenceError("invalid evidence_type")
    if payload.get("final_status") not in ALLOWED_STATUSES:
        raise EvidenceError("invalid final_status")
    if type(payload.get("rollback_duration_seconds")) is not int:
        raise EvidenceError("rollback_duration_seconds must be int")

    expected = compute_rollback_evidence_sha256(payload)
    actual = payload.get("evidence_sha256")
    if actual != expected:
        raise EvidenceError(f"evidence_sha256 mismatch: expected {expected}, got {actual!r}")

    status = payload.get("final_status")
    if status == "rollback_ok":
        _validate_rollback_ok(payload)
    elif status == "failed":
        _validate_failed(payload)


def validate_rollback_evidence_bindings(
    payload: dict[str, Any],
    *,
    target_release_id: str,
    target_git_sha: str,
    target_image_digest: str,
    target_image_repository: str,
    target_manifest_sha256: str,
    rollback_workflow_run_id: str,
    aws_account_id: str,
    aws_region: str,
    ec2_instance_id: str,
    ssm_command_id: str,
    require_rollback_ok: bool = True,
) -> None:
    """Reject evidence bound to a different run/release/instance/digest/SHA."""
    validate_rollback_evidence(payload)
    checks = {
        "target_release_id": target_release_id,
        "target_git_sha": target_git_sha,
        "target_image_digest": target_image_digest,
        "target_image_repository": target_image_repository.rstrip("/").lower(),
        "target_manifest_sha256": target_manifest_sha256,
        "rollback_workflow_run_id": str(rollback_workflow_run_id),
        "aws_account_id": str(aws_account_id),
        "aws_region": aws_region,
        "ec2_instance_id": ec2_instance_id,
        "ssm_command_id": ssm_command_id,
    }
    for key, expected in checks.items():
        actual = payload.get(key)
        if actual != expected:
            raise EvidenceError(f"evidence binding mismatch for {key}: {actual!r} != {expected!r}")
    if require_rollback_ok and payload.get("final_status") != "rollback_ok":
        raise EvidenceError(
            f"authoritative evidence final_status must be rollback_ok, "
            f"got {payload.get('final_status')!r}"
        )


def create_rollback_evidence(
    *,
    rollback_workflow_run_id: str,
    aws_account_id: str,
    aws_region: str,
    assumed_role_arn: str,
    role_session_name: str,
    ec2_instance_id: str,
    ssm_command_id: str | None,
    rollback_started_at: str,
    rollback_finished_at: str,
    rollback_duration_seconds: int,
    source_release_id: str | None,
    source_image_digest: str | None,
    target_release_id: str,
    target_image_digest: str,
    target_git_sha: str,
    target_image_repository: str,
    target_manifest_sha256: str,
    migration_revision_before: str | None,
    migration_revision_after: str | None,
    target_migration_revision_authority: str | None,
    current_pointer_before: str | None,
    current_pointer_after: str | None,
    previous_pointer_before: str | None,
    previous_pointer_after: str | None,
    running_digest_after: str | None,
    localhost_live: bool | None,
    localhost_ready: bool | None,
    alb_target_healthy: bool | None,
    final_status: str,
    failure_reason: str | None,
) -> dict[str, Any]:
    if migration_revision_before is not None and migration_revision_before != "":
        migration_revision_before = normalize_alembic_revision(migration_revision_before)
    elif migration_revision_before == "":
        migration_revision_before = None
    if migration_revision_after is not None and migration_revision_after != "":
        migration_revision_after = normalize_alembic_revision(migration_revision_after)
    elif migration_revision_after == "":
        migration_revision_after = None

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "evidence_type": EVIDENCE_TYPE,
        "rollback_workflow_run_id": str(rollback_workflow_run_id),
        "aws_account_id": str(aws_account_id),
        "aws_region": aws_region,
        "assumed_role_arn": assumed_role_arn,
        "role_session_name": role_session_name,
        "ec2_instance_id": ec2_instance_id,
        "ssm_command_id": ssm_command_id,
        "rollback_started_at": rollback_started_at,
        "rollback_finished_at": rollback_finished_at,
        "rollback_duration_seconds": int(rollback_duration_seconds),
        "source_release_id": source_release_id,
        "source_image_digest": source_image_digest,
        "target_release_id": target_release_id,
        "target_image_digest": target_image_digest,
        "target_git_sha": target_git_sha,
        "target_image_repository": target_image_repository.rstrip("/").lower(),
        "target_manifest_sha256": target_manifest_sha256,
        "migration_revision_before": migration_revision_before,
        "migration_revision_after": migration_revision_after,
        "target_migration_revision_authority": target_migration_revision_authority,
        "current_pointer_before": current_pointer_before,
        "current_pointer_after": current_pointer_after,
        "previous_pointer_before": previous_pointer_before,
        "previous_pointer_after": previous_pointer_after,
        "running_digest_after": running_digest_after,
        "localhost_live": localhost_live,
        "localhost_ready": localhost_ready,
        "alb_target_healthy": alb_target_healthy,
        "final_status": final_status,
        "failure_reason": failure_reason,
        "evidence_sha256": None,
    }
    payload["evidence_sha256"] = compute_rollback_evidence_sha256(payload)
    validate_rollback_evidence(payload)
    return payload


def write_rollback_evidence(path: Path, payload: dict[str, Any]) -> None:
    validate_rollback_evidence(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar.write_text(payload["evidence_sha256"] + "\n", encoding="utf-8")


def read_strict_rollback_evidence_sidecar_sha256(sidecar_path: Path) -> str:
    """Parse a mandatory evidence sidecar: exactly one canonical lowercase SHA-256.

    Contract: body is precisely 64 lowercase hex digits, optionally terminated by
    a single LF or CRLF. Rejects empty files, uppercase, whitespace, filenames,
    multiple hashes/lines, and shell-output padding.
    """
    path = Path(sidecar_path)
    if not path.is_file():
        raise EvidenceError(f"missing rollback evidence checksum sidecar: {path}")
    raw = path.read_bytes()
    if not raw:
        raise EvidenceError("rollback evidence checksum sidecar is empty")
    if raw.endswith(b"\r\n"):
        body = raw[:-2]
    elif raw.endswith(b"\n"):
        body = raw[:-1]
    else:
        body = raw
    if not body:
        raise EvidenceError("rollback evidence checksum sidecar empty after newline trim")
    if b"\n" in body or b"\r" in body:
        raise EvidenceError("rollback evidence checksum sidecar must be a single line")
    try:
        text = body.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EvidenceError("rollback evidence checksum sidecar is not ASCII") from exc
    if any(ch in text for ch in " \t\v\f"):
        raise EvidenceError("rollback evidence checksum sidecar must not contain whitespace")
    if not SHA256_HEX_RE.fullmatch(text):
        raise EvidenceError(
            "rollback evidence checksum sidecar must be exactly one canonical "
            "lowercase SHA-256 hex digest"
        )
    return text


def verify_rollback_evidence_sidecar(evidence_path: Path, sidecar_path: Path | None = None) -> str:
    """Verify mandatory sidecar against a locally recomputed evidence checksum.

    Checksum verification only — callers must run semantic validation afterwards.
    Never synthesizes or regenerates a missing sidecar.
    """
    path = Path(evidence_path)
    side = (
        Path(sidecar_path)
        if sidecar_path is not None
        else path.with_suffix(path.suffix + ".sha256")
    )
    if not path.is_file():
        raise EvidenceError(f"rollback evidence JSON missing: {path}")
    sidecar_token = read_strict_rollback_evidence_sidecar_sha256(side)
    try:
        raw_obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"rollback evidence JSON unreadable: {exc}") from exc
    if not isinstance(raw_obj, dict):
        raise EvidenceError("rollback evidence must be a JSON object")
    recomputed = compute_rollback_evidence_sha256(raw_obj)
    if sidecar_token != recomputed:
        raise EvidenceError(
            f"rollback evidence checksum sidecar mismatch: sidecar={sidecar_token} "
            f"recomputed={recomputed}"
        )
    embedded = raw_obj.get("evidence_sha256")
    if embedded != sidecar_token:
        raise EvidenceError(
            f"rollback evidence checksum sidecar mismatch: sidecar={sidecar_token} "
            f"embedded={embedded!r}"
        )
    return sidecar_token


def load_rollback_evidence(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_rollback_evidence(payload)
    return payload
