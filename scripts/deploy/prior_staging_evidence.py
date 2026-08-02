"""Authoritative prior staging_ok evidence selection (Sprint 25b.5 audit hardening).

Host-safe: loads the deploy evidence module from the package or a sibling file.
Never trusts evidence JSON without a SHA-256 sidecar and exact identity bindings.
"""

from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load_deploy_evidence_module():
    try:
        from scripts.deploy import evidence as module

        return module
    except ImportError:
        pass
    sibling = Path(__file__).resolve().parent / "evidence.py"
    if sibling.is_file():
        spec = importlib.util.spec_from_file_location(
            "dealbrain_staging_deploy_evidence_for_prior", sibling
        )
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ImportError("canonical deploy evidence module unavailable")


_evid = _load_deploy_evidence_module()
EvidenceError = _evid.EvidenceError
MIGRATION_REV_RE = _evid.MIGRATION_REV_RE
RUN_ID_RE = _evid.RUN_ID_RE
UTC_Z_RE = _evid.UTC_Z_RE
load_evidence = _evid.load_evidence
normalize_alembic_revision = _evid.normalize_alembic_revision
validate_evidence = _evid.validate_evidence
SHA256_HEX_RE = _evid.SHA256_HEX_RE

MIGRATION_AUTHORITY_DEPLOY_VERSION = "deploy_version"
MIGRATION_AUTHORITY_VALIDATED_PRIOR = "validated_prior_staging_evidence"


class PriorEvidenceError(ValueError):
    """Raised when prior staging evidence cannot be trusted."""


@dataclass(frozen=True)
class ValidatedPriorStagingEvidence:
    evidence: dict[str, Any]
    evidence_key: str
    evidence_sha256: str
    deploy_workflow_run_id: str
    ssm_command_id: str
    migration_revision_after: str
    deployment_finished_at: str


@dataclass(frozen=True)
class MigrationAuthorityResult:
    migration_revision: str
    authority: str
    prior: ValidatedPriorStagingEvidence | None = None


def _parse_utc_z(value: str) -> datetime:
    if not isinstance(value, str) or not UTC_Z_RE.fullmatch(value):
        raise PriorEvidenceError(f"malformed UTC timestamp: {value!r}")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise PriorEvidenceError(f"malformed UTC timestamp: {value!r}") from exc


def read_sidecar_sha256(sidecar_path: Path) -> str:
    if not sidecar_path.is_file():
        raise PriorEvidenceError(f"missing evidence checksum sidecar: {sidecar_path}")
    text = sidecar_path.read_text(encoding="utf-8")
    token = text.strip().split()[0] if text.strip() else ""
    if not SHA256_HEX_RE.fullmatch(token):
        raise PriorEvidenceError("evidence checksum sidecar missing or malformed")
    return token


def load_prior_evidence_with_sidecar(json_path: Path, sidecar_path: Path | None = None) -> dict:
    """Load deploy evidence only after SHA-256 sidecar verification."""
    path = Path(json_path)
    if not path.is_file():
        raise PriorEvidenceError(f"prior evidence JSON missing: {path}")
    side = (
        Path(sidecar_path)
        if sidecar_path is not None
        else path.with_suffix(path.suffix + ".sha256")
    )
    sidecar_token = read_sidecar_sha256(side)
    try:
        raw_obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PriorEvidenceError(f"prior evidence JSON unreadable: {exc}") from exc
    if not isinstance(raw_obj, dict):
        raise PriorEvidenceError("prior evidence must be a JSON object")
    embedded = raw_obj.get("evidence_sha256")
    if embedded != sidecar_token:
        raise PriorEvidenceError(
            f"prior evidence checksum sidecar mismatch: sidecar={sidecar_token} "
            f"embedded={embedded!r}"
        )
    try:
        return load_evidence(path)
    except EvidenceError as exc:
        raise PriorEvidenceError(f"prior evidence failed canonical validation: {exc}") from exc


def validate_prior_staging_ok_bindings(
    prior: dict[str, Any],
    *,
    expected_release_id: str,
    expected_image_digest: str,
    expected_image_repository: str,
    expected_aws_account_id: str,
    expected_aws_region: str,
    expected_ec2_instance_id: str,
    expected_source_manifest_sha256: str | None = None,
) -> None:
    try:
        validate_evidence(prior)
    except EvidenceError as exc:
        raise PriorEvidenceError(f"prior evidence invalid: {exc}") from exc

    if prior.get("final_status") != "staging_ok":
        raise PriorEvidenceError(
            "target release was not previously deployed/approved for staging "
            f"(final_status={prior.get('final_status')!r})"
        )

    checks = {
        "release_id": expected_release_id,
        "image_digest": expected_image_digest,
        "image_repository": expected_image_repository.rstrip("/").lower(),
        "aws_account_id": str(expected_aws_account_id),
        "aws_region": expected_aws_region,
        "ec2_instance_id": expected_ec2_instance_id,
    }
    for key, expected in checks.items():
        actual = prior.get(key)
        if actual != expected:
            raise PriorEvidenceError(
                f"prior evidence binding mismatch for {key}: {actual!r} != {expected!r}"
            )

    if (
        expected_source_manifest_sha256 is not None
        and prior.get("source_manifest_sha256") != expected_source_manifest_sha256
    ):
        raise PriorEvidenceError("prior evidence source_manifest_sha256 mismatch")

    deploy_run = str(prior.get("deploy_workflow_run_id", ""))
    if not RUN_ID_RE.fullmatch(deploy_run):
        raise PriorEvidenceError("prior evidence missing valid deploy_workflow_run_id")

    ssm_command_id = prior.get("ssm_command_id")
    if not isinstance(ssm_command_id, str) or not ssm_command_id.strip():
        raise PriorEvidenceError("prior evidence missing canonical ssm_command_id")

    after = prior.get("migration_revision_after")
    if not isinstance(after, str) or not after.strip():
        raise PriorEvidenceError("prior evidence missing migration_revision_after")
    try:
        normalized = normalize_alembic_revision(after)
    except EvidenceError as exc:
        raise PriorEvidenceError(f"prior evidence migration revision invalid: {exc}") from exc
    if not MIGRATION_REV_RE.fullmatch(normalized):
        raise PriorEvidenceError("prior evidence migration_revision_after failed contract")

    _parse_utc_z(str(prior.get("deployment_finished_at", "")))
    _parse_utc_z(str(prior.get("deployment_started_at", "")))


def select_authoritative_prior_staging_evidence(
    candidates: list[tuple[Path, Path, str]],
    *,
    expected_release_id: str,
    expected_image_digest: str,
    expected_image_repository: str,
    expected_aws_account_id: str,
    expected_aws_region: str,
    expected_ec2_instance_id: str,
    expected_source_manifest_sha256: str | None = None,
) -> ValidatedPriorStagingEvidence:
    """Select the unique latest fully validated staging_ok prior evidence."""
    if not candidates:
        raise PriorEvidenceError("no prior staging evidence candidates provided")

    valid: list[ValidatedPriorStagingEvidence] = []
    errors: list[str] = []
    for json_path, sidecar_path, evidence_key in candidates:
        try:
            payload = load_prior_evidence_with_sidecar(json_path, sidecar_path)
            validate_prior_staging_ok_bindings(
                payload,
                expected_release_id=expected_release_id,
                expected_image_digest=expected_image_digest,
                expected_image_repository=expected_image_repository,
                expected_aws_account_id=expected_aws_account_id,
                expected_aws_region=expected_aws_region,
                expected_ec2_instance_id=expected_ec2_instance_id,
                expected_source_manifest_sha256=expected_source_manifest_sha256,
            )
            finished = str(payload["deployment_finished_at"])
            migration = normalize_alembic_revision(str(payload["migration_revision_after"]))
            valid.append(
                ValidatedPriorStagingEvidence(
                    evidence=payload,
                    evidence_key=evidence_key,
                    evidence_sha256=str(payload["evidence_sha256"]),
                    deploy_workflow_run_id=str(payload["deploy_workflow_run_id"]),
                    ssm_command_id=str(payload["ssm_command_id"]),
                    migration_revision_after=migration,
                    deployment_finished_at=finished,
                )
            )
        except (PriorEvidenceError, EvidenceError, OSError, json.JSONDecodeError) as exc:
            errors.append(f"{evidence_key}: {exc}")

    if not valid:
        detail = "; ".join(errors[:5]) if errors else "none"
        raise PriorEvidenceError(
            "no fully validated prior staging_ok evidence for target release/digest/identity "
            f"({detail})"
        )

    def sort_key(item: ValidatedPriorStagingEvidence) -> datetime:
        return _parse_utc_z(item.deployment_finished_at)

    latest_ts = max(sort_key(item) for item in valid)
    winners = [item for item in valid if sort_key(item) == latest_ts]
    if len(winners) != 1:
        keys = sorted({w.evidence_key for w in winners})
        raise PriorEvidenceError(
            "ambiguous prior staging_ok evidence: multiple fully valid candidates share "
            f"deployment_finished_at={latest_ts.strftime('%Y-%m-%dT%H:%M:%SZ')} keys={keys}"
        )
    return winners[0]


def resolve_target_migration_revision(
    *,
    deploy_version_path: Path | None,
    validated_prior: ValidatedPriorStagingEvidence | None,
) -> MigrationAuthorityResult:
    """Prefer DEPLOY_VERSION; else validated prior staging_ok migration_revision_after."""
    if deploy_version_path is not None and deploy_version_path.is_file():
        try:
            data = json.loads(deploy_version_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if isinstance(data, dict):
            raw = data.get("migration_revision")
            if isinstance(raw, str) and raw.strip():
                try:
                    normalized = normalize_alembic_revision(raw)
                except EvidenceError as exc:
                    raise PriorEvidenceError(
                        f"DEPLOY_VERSION migration_revision invalid: {exc}"
                    ) from exc
                if not MIGRATION_REV_RE.fullmatch(normalized):
                    raise PriorEvidenceError(
                        "DEPLOY_VERSION migration_revision failed migration contract"
                    )
                return MigrationAuthorityResult(
                    migration_revision=normalized,
                    authority=MIGRATION_AUTHORITY_DEPLOY_VERSION,
                    prior=validated_prior,
                )

    if validated_prior is None:
        raise PriorEvidenceError(
            "migration authority unavailable: DEPLOY_VERSION.migration_revision missing "
            "and no validated prior staging evidence selected"
        )
    return MigrationAuthorityResult(
        migration_revision=validated_prior.migration_revision_after,
        authority=MIGRATION_AUTHORITY_VALIDATED_PRIOR,
        prior=validated_prior,
    )


def discover_candidate_pairs(candidates_dir: Path) -> list[tuple[Path, Path, str]]:
    pairs: list[tuple[Path, Path, str]] = []
    if not candidates_dir.is_dir():
        raise PriorEvidenceError(f"candidates directory missing: {candidates_dir}")
    for json_path in sorted(candidates_dir.glob("**/staging-deploy-evidence.json")):
        sidecar = json_path.with_suffix(json_path.suffix + ".sha256")
        rel = json_path.relative_to(candidates_dir).as_posix()
        pairs.append((json_path, sidecar, rel))
    return pairs


# Silence unused import lint for re when type-checkers look at this module.
_ = re
