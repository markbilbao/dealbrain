"""Sprint 25b.1 release manifest creation and integrity validation.

Deterministic serialization and SHA-256 checksum (manifest_sha256 omitted from
the hashed payload). Mutable image tags are never accepted as authority.

Validation runs in two layers:
1. JSON Schema (``schemas/release-manifest.schema.json``) via ``jsonschema``
2. Semantic / integrity checks (formats, built-state invariants, checksum)
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
    Path(__file__).resolve().parents[2] / "schemas" / "release-manifest.schema.json"
)

ALLOWED_ENVIRONMENTS: Final[frozenset[str]] = frozenset({"none", "staging", "production"})
ALLOWED_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "built",
        "staging_ok",
        "approved",
        "production_ok",
        "failed",
        "rolled_back",
    }
)
ALLOWED_VERIFICATION_RESULTS: Final[frozenset[str]] = frozenset(
    {"pending", "passed", "failed", "skipped"}
)

# Forbidden key substrings — manifests must never carry secret material.
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

GIT_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_TAG_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^sha-[0-9a-f]{40}$")
RELEASE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$")
# ghcr.io/<owner>/<name> with optional nested path segments; no tag/digest.
GHCR_REPO_RE: Final[re.Pattern[str]] = re.compile(
    r"^ghcr\.io/[a-z0-9]([a-z0-9._-]*/)+[a-z0-9._-]+$"
)
UTC_Z_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
RUN_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9]+$")

REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "release_id",
    "git_sha",
    "image_repository",
    "image_digest",
    "image_tag_sha",
    "build_workflow_run_id",
    "test_workflow_run_id",
    "staging_deployment_run_id",
    "staging_timestamp",
    "staging_verification",
    "production_approval_identity",
    "production_deployment_run_id",
    "migration_revision_before",
    "migration_revision_after",
    "rollback_digest",
    "environment",
    "final_status",
    "created_at",
    "manifest_sha256",
)

MUTABLE_TAG_MARKERS: Final[tuple[str, ...]] = (
    ":latest",
    ":ci-latest",
    ":staging",
    ":production",
    ":main",
)


class ManifestError(ValueError):
    """Raised when a release manifest fails integrity validation."""


def utc_now_z() -> str:
    """Return UTC timestamp as ``YYYY-MM-DDTHH:MM:SSZ`` (no fractional seconds)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_release_id(git_sha: str, created_at: str | None = None) -> str:
    """Build a collision-resistant release ID from UTC time and git SHA."""
    if not GIT_SHA_RE.fullmatch(git_sha):
        raise ManifestError(f"invalid git_sha for release_id: {git_sha!r}")
    stamp = (created_at or utc_now_z()).replace("-", "").replace(":", "")
    if not stamp.endswith("Z") or "T" not in stamp:
        raise ManifestError(f"invalid created_at for release_id: {created_at!r}")
    return f"rel-{stamp}-{git_sha[:12]}"


def canonicalize_for_checksum(payload: dict[str, Any]) -> str:
    """Return deterministic JSON with ``manifest_sha256`` forced to null."""
    data = dict(payload)
    data["manifest_sha256"] = None
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_manifest_sha256(payload: dict[str, Any]) -> str:
    """SHA-256 hex digest of the canonical payload (checksum field null)."""
    canonical = canonicalize_for_checksum(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pending_verification() -> dict[str, Any]:
    return {
        "live": None,
        "ready": None,
        "alb": None,
        "smoke": None,
        "result": "pending",
    }


def create_built_manifest(
    *,
    git_sha: str,
    image_repository: str,
    image_digest: str,
    build_workflow_run_id: str,
    test_workflow_run_id: str,
    created_at: str | None = None,
    release_id: str | None = None,
) -> dict[str, Any]:
    """Create a validated ``built``-state release manifest (checksum included)."""
    created = created_at or utc_now_z()
    rid = release_id or build_release_id(git_sha, created)
    tag_sha = f"sha-{git_sha}"
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "release_id": rid,
        "git_sha": git_sha,
        "image_repository": image_repository.rstrip("/").lower(),
        "image_digest": image_digest,
        "image_tag_sha": tag_sha,
        "build_workflow_run_id": str(build_workflow_run_id),
        "test_workflow_run_id": str(test_workflow_run_id),
        "staging_deployment_run_id": None,
        "staging_timestamp": None,
        "staging_verification": _pending_verification(),
        "production_approval_identity": None,
        "production_deployment_run_id": None,
        "migration_revision_before": None,
        "migration_revision_after": None,
        "rollback_digest": None,
        "environment": "none",
        "final_status": "built",
        "created_at": created,
        "manifest_sha256": None,
    }
    payload["manifest_sha256"] = compute_manifest_sha256(payload)
    validate_manifest(payload)
    return payload


def _reject_secret_like_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for fragment in FORBIDDEN_FIELD_FRAGMENTS:
                if fragment in lowered:
                    raise ManifestError(
                        f"secret-like field name forbidden at {path}.{key}: {key!r}"
                    )
            _reject_secret_like_keys(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            _reject_secret_like_keys(item, f"{path}[{idx}]")


def _reject_mutable_image_authority(manifest: dict[str, Any]) -> None:
    digest = manifest.get("image_digest")
    repo = manifest.get("image_repository")
    tag = manifest.get("image_tag_sha")
    for field_name, value in (
        ("image_digest", digest),
        ("image_repository", repo),
        ("image_tag_sha", tag),
    ):
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        for marker in MUTABLE_TAG_MARKERS:
            if marker in lowered:
                raise ManifestError(
                    f"mutable tag marker {marker!r} is not deployment authority "
                    f"(field {field_name})"
                )
        if field_name == "image_repository" and ("@" in value or value.count(":") > 1):
            raise ManifestError(
                "image_repository must be a bare GHCR repository (no tag or digest)"
            )
        if field_name == "image_digest" and not DIGEST_RE.fullmatch(value):
            # Allow through to the digest format check below for clearer errors.
            pass


@lru_cache(maxsize=1)
def load_release_manifest_schema() -> dict[str, Any]:
    """Load the binding JSON Schema for release manifests."""
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestError(f"unable to load release manifest schema: {exc}") from exc
    if not isinstance(schema, dict):
        raise ManifestError("release manifest schema root must be an object")
    return schema


def validate_manifest_schema(manifest: dict[str, Any]) -> None:
    """Validate ``manifest`` against ``schemas/release-manifest.schema.json``."""
    schema = load_release_manifest_schema()
    try:
        validator = Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        validator.validate(manifest)
    except SchemaError as exc:
        raise ManifestError(f"invalid release manifest schema: {exc.message}") from exc
    except JsonSchemaValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ManifestError(f"JSON Schema validation failed at {path}: {exc.message}") from exc


def validate_manifest(manifest: dict[str, Any], *, verify_checksum: bool = True) -> None:
    """Validate schema, required fields, formats, and optional checksum integrity."""
    if not isinstance(manifest, dict):
        raise ManifestError("manifest must be a JSON object")

    missing = [name for name in REQUIRED_FIELDS if name not in manifest]
    if missing:
        raise ManifestError(f"missing required fields: {', '.join(missing)}")

    _reject_secret_like_keys(manifest)
    _reject_mutable_image_authority(manifest)
    validate_manifest_schema(manifest)

    schema_version = manifest["schema_version"]
    if schema_version != SCHEMA_VERSION:
        raise ManifestError(
            f"unsupported schema_version: {schema_version!r} (expected {SCHEMA_VERSION})"
        )

    git_sha = manifest["git_sha"]
    if not isinstance(git_sha, str) or not GIT_SHA_RE.fullmatch(git_sha):
        raise ManifestError(f"invalid git_sha: {git_sha!r}")

    image_digest = manifest["image_digest"]
    if not isinstance(image_digest, str) or not DIGEST_RE.fullmatch(image_digest):
        raise ManifestError(
            f"invalid image_digest (expected sha256:<64 lowercase hex>): {image_digest!r}"
        )

    image_repository = manifest["image_repository"]
    if not isinstance(image_repository, str) or not GHCR_REPO_RE.fullmatch(image_repository):
        raise ManifestError(
            f"invalid image_repository (expected ghcr.io/<owner>/<name>): {image_repository!r}"
        )

    image_tag_sha = manifest["image_tag_sha"]
    if not isinstance(image_tag_sha, str) or not IMAGE_TAG_SHA_RE.fullmatch(image_tag_sha):
        raise ManifestError(f"invalid image_tag_sha: {image_tag_sha!r}")
    if image_tag_sha != f"sha-{git_sha}":
        raise ManifestError(f"image_tag_sha {image_tag_sha!r} does not match git_sha {git_sha!r}")

    for run_field in ("build_workflow_run_id", "test_workflow_run_id"):
        value = manifest[run_field]
        if not isinstance(value, str) or not RUN_ID_RE.fullmatch(value):
            raise ManifestError(f"missing or invalid {run_field}: {value!r}")

    release_id = manifest["release_id"]
    if not isinstance(release_id, str) or not RELEASE_ID_RE.fullmatch(release_id):
        raise ManifestError(f"invalid release_id: {release_id!r}")

    environment = manifest["environment"]
    if environment not in ALLOWED_ENVIRONMENTS:
        raise ManifestError(f"invalid environment: {environment!r}")

    final_status = manifest["final_status"]
    if final_status not in ALLOWED_STATUSES:
        raise ManifestError(f"invalid final_status: {final_status!r}")

    created_at = manifest["created_at"]
    if not isinstance(created_at, str) or not UTC_Z_RE.fullmatch(created_at):
        raise ManifestError(f"malformed created_at timestamp: {created_at!r}")

    staging_timestamp = manifest["staging_timestamp"]
    if staging_timestamp is not None:
        if not isinstance(staging_timestamp, str) or not UTC_Z_RE.fullmatch(staging_timestamp):
            raise ManifestError(f"malformed staging_timestamp: {staging_timestamp!r}")

    for optional_run in (
        "staging_deployment_run_id",
        "production_deployment_run_id",
    ):
        value = manifest[optional_run]
        if value is not None and (not isinstance(value, str) or not RUN_ID_RE.fullmatch(value)):
            raise ManifestError(f"invalid {optional_run}: {value!r}")

    rollback_digest = manifest["rollback_digest"]
    if rollback_digest is not None and (
        not isinstance(rollback_digest, str) or not DIGEST_RE.fullmatch(rollback_digest)
    ):
        raise ManifestError(f"invalid rollback_digest: {rollback_digest!r}")

    verification = manifest["staging_verification"]
    if not isinstance(verification, dict):
        raise ManifestError("staging_verification must be an object")
    for key in ("live", "ready", "alb", "smoke", "result"):
        if key not in verification:
            raise ManifestError(f"staging_verification missing {key}")
    if verification["result"] not in ALLOWED_VERIFICATION_RESULTS:
        raise ManifestError(f"invalid staging_verification.result: {verification['result']!r}")
    for probe in ("live", "ready", "alb", "smoke"):
        if verification[probe] is not None and not isinstance(verification[probe], bool):
            raise ManifestError(f"staging_verification.{probe} must be bool or null")

    if final_status == "built":
        if environment != "none":
            raise ManifestError("built status requires environment='none'")
        if manifest["staging_deployment_run_id"] is not None:
            raise ManifestError("built status must not set staging_deployment_run_id")
        if manifest["production_deployment_run_id"] is not None:
            raise ManifestError("built status must not set production_deployment_run_id")
        if manifest["production_approval_identity"] is not None:
            raise ManifestError("built status must not set production_approval_identity")

    if verify_checksum:
        expected = compute_manifest_sha256(manifest)
        actual = manifest.get("manifest_sha256")
        if not isinstance(actual, str) or not re.fullmatch(r"^[0-9a-f]{64}$", actual):
            raise ManifestError(f"invalid manifest_sha256: {actual!r}")
        if actual != expected:
            raise ManifestError("manifest_sha256 mismatch (tampered or non-canonical payload)")


def dumps_manifest(manifest: dict[str, Any]) -> str:
    """Deterministic pretty-stable serialization (sorted keys, 2-space indent)."""
    return json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write manifest JSON and a ``.sha256`` sidecar next to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dumps_manifest(manifest)
    path.write_text(text, encoding="utf-8")
    checksum = manifest["manifest_sha256"]
    sidecar = path.with_name(path.name + ".sha256")
    sidecar.write_text(f"{checksum}  {path.name}\n", encoding="utf-8")


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate a manifest file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be an object")
    validate_manifest(data)
    return data
