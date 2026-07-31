"""Sprint 25b.3 staging deploy evidence creation and integrity validation.

Append-only evidence separate from the immutable build release-manifest.
Checksum model mirrors scripts/release/manifest.py (evidence_sha256 null during hash).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

SCHEMA_VERSION: Final[int] = 1
SCHEMA_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2] / "schemas" / "staging-deploy-evidence.schema.json"
)

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
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonicalize_for_checksum(payload: dict[str, Any]) -> str:
    data = dict(payload)
    data["evidence_sha256"] = None
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_evidence_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonicalize_for_checksum(payload).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
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


def _parse_utc_z(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


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
    try:
        Draft202012Validator.check_schema(_load_schema())
        Draft202012Validator(_load_schema()).validate(payload)
    except (JsonSchemaValidationError, SchemaError) as exc:
        raise EvidenceError(f"schema validation failed: {exc}") from exc

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
    if not isinstance(payload.get("deployment_duration_seconds"), int):
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
