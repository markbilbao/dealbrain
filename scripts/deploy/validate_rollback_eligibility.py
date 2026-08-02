#!/usr/bin/env python3
"""Validate staging rollback eligibility before host mutation (Sprint 25b.5).

Authority is the immutable Build Image release-manifest plus staging S3 state.
Mutable image tags are never accepted as authority.

Invoke from the repository root as a module:

  python -m scripts.deploy.validate_rollback_eligibility [options]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.deploy.evidence import EvidenceError, normalize_alembic_revision
from scripts.deploy.prior_staging_evidence import (
    MIGRATION_AUTHORITY_DEPLOY_VERSION,
    MIGRATION_AUTHORITY_VALIDATED_PRIOR,
    MigrationAuthorityResult,
    PriorEvidenceError,
    ValidatedPriorStagingEvidence,
    discover_candidate_pairs,
    load_prior_evidence_with_sidecar,
    resolve_target_migration_revision,
    select_authoritative_prior_staging_evidence,
    validate_prior_staging_ok_bindings,
)
from scripts.deploy.validate_staging_release import StagingIngestError, validate_for_staging
from scripts.release.manifest import DIGEST_RE, GIT_SHA_RE, RELEASE_ID_RE

_MUTABLE_TAG_RE = re.compile(r":(latest|ci-latest|staging|production|main)$", re.IGNORECASE)
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_ACCOUNT_RE = re.compile(r"^[0-9]{12}$")
_BUCKET_RE = re.compile(r"^dealbrain-staging-release-artifacts-[0-9]{12}$")
_INSTANCE_RE = re.compile(r"^i-[0-9a-f]{8,17}$")

ALLOWED_MIGRATION_AUTHORITIES = frozenset(
    {MIGRATION_AUTHORITY_DEPLOY_VERSION, MIGRATION_AUTHORITY_VALIDATED_PRIOR}
)


class RollbackEligibilityError(ValueError):
    """Raised when a rollback target is not eligible."""


@dataclass(frozen=True)
class RollbackEligibilityResult:
    release_id: str
    image_digest: str
    prior: ValidatedPriorStagingEvidence
    migration: MigrationAuthorityResult


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RollbackEligibilityError(f"{path} must be a JSON object")
    return data


def assert_no_mutable_tag_authority(image_repository: str, image_ref: str | None = None) -> None:
    """Fail closed if a mutable tag is offered as image authority."""
    repo = image_repository.rstrip("/").lower()
    if "@" in repo or ":" in repo.split("/")[-1]:
        raise RollbackEligibilityError(
            "mutable tag or digest suffix forbidden in image_repository authority"
        )
    if _MUTABLE_TAG_RE.search(repo):
        raise RollbackEligibilityError("mutable tag marker forbidden in image_repository")
    if image_ref:
        lowered = image_ref.lower()
        if "@sha256:" not in lowered:
            raise RollbackEligibilityError(
                "image reference must use digest authority (@sha256:...), not a mutable tag"
            )
        tag_part = lowered.split("@", 1)[0]
        if _MUTABLE_TAG_RE.search(tag_part) or tag_part.endswith(":latest"):
            pass
        if re.search(r":[A-Za-z0-9._-]+$", tag_part) and "@sha256:" not in image_ref:
            raise RollbackEligibilityError("mutable tag cannot become rollback authority")


def validate_target_manifest_authority(
    manifest: dict,
    *,
    expected_build_run_id: str,
    expected_git_sha: str | None = None,
    expected_release_id: str | None = None,
    expected_image_repository: str | None = None,
    expected_image_digest: str | None = None,
    expected_manifest_sha256: str | None = None,
) -> dict:
    """Validate target release-manifest as the sole image authority."""
    try:
        validate_for_staging(
            manifest,
            expected_build_run_id=expected_build_run_id,
            expected_git_sha=expected_git_sha,
            expected_release_id=expected_release_id,
            expected_image_repository=expected_image_repository,
        )
    except StagingIngestError as exc:
        raise RollbackEligibilityError(str(exc)) from exc

    release_id = str(manifest.get("release_id", ""))
    if not RELEASE_ID_RE.fullmatch(release_id):
        raise RollbackEligibilityError("invalid target release_id")
    if expected_release_id and release_id != expected_release_id:
        raise RollbackEligibilityError(
            f"target release_id mismatch: manifest={release_id} expected={expected_release_id}"
        )

    digest = str(manifest.get("image_digest", ""))
    if not DIGEST_RE.fullmatch(digest):
        raise RollbackEligibilityError("invalid target image_digest")
    if expected_image_digest and digest != expected_image_digest:
        raise RollbackEligibilityError(
            f"target digest mismatch: manifest={digest} expected={expected_image_digest}"
        )

    manifest_sha = str(manifest.get("manifest_sha256", ""))
    if not _SHA256_HEX_RE.fullmatch(manifest_sha):
        raise RollbackEligibilityError("invalid target manifest_sha256")
    if expected_manifest_sha256 and manifest_sha != expected_manifest_sha256:
        raise RollbackEligibilityError("target release-manifest checksum mismatch")

    git_sha = str(manifest.get("git_sha", ""))
    if not GIT_SHA_RE.fullmatch(git_sha):
        raise RollbackEligibilityError("invalid target git_sha")

    repo = str(manifest.get("image_repository", "")).rstrip("/").lower()
    assert_no_mutable_tag_authority(repo, f"{repo}@{digest}")
    return manifest


def validate_staging_identity(
    *,
    aws_account_id: str,
    aws_region: str,
    expected_account_id: str,
    expected_region: str,
    ec2_instance_id: str,
    bundle_bucket: str,
    image_repository: str,
    expected_image_repository: str,
) -> None:
    """Fail closed on account/region/instance/bucket/repository mismatch."""
    if not _ACCOUNT_RE.fullmatch(aws_account_id):
        raise RollbackEligibilityError("invalid aws_account_id")
    if aws_account_id != expected_account_id:
        raise RollbackEligibilityError(
            f"wrong AWS account: got {aws_account_id} expected {expected_account_id}"
        )
    if not aws_region or aws_region != expected_region:
        raise RollbackEligibilityError(
            f"wrong AWS region: got {aws_region} expected {expected_region}"
        )
    if not _INSTANCE_RE.fullmatch(ec2_instance_id):
        raise RollbackEligibilityError("invalid ec2_instance_id")
    if "production" in ec2_instance_id.lower():
        raise RollbackEligibilityError("production identifier in ec2_instance_id")
    if not _BUCKET_RE.fullmatch(bundle_bucket):
        raise RollbackEligibilityError(
            f"bundle bucket must match dealbrain-staging-release-artifacts-<account>, "
            f"got {bundle_bucket!r}"
        )
    expected_bucket = f"dealbrain-staging-release-artifacts-{expected_account_id}"
    if bundle_bucket != expected_bucket:
        raise RollbackEligibilityError(
            f"wrong bundle bucket: got {bundle_bucket} expected {expected_bucket}"
        )
    repo = image_repository.rstrip("/").lower()
    expected_repo = expected_image_repository.rstrip("/").lower()
    if repo != expected_repo:
        raise RollbackEligibilityError(
            f"wrong image repository: got {repo} expected {expected_repo}"
        )
    if "production" in repo:
        raise RollbackEligibilityError("production image repository forbidden")


def validate_target_differs_from_current(
    *,
    target_release_id: str,
    target_image_digest: str,
    current_release_id: str | None,
    current_image_digest: str | None,
) -> None:
    if not current_release_id or not current_image_digest:
        raise RollbackEligibilityError(
            "current active release and digest must be known before rollback"
        )
    if not RELEASE_ID_RE.fullmatch(current_release_id):
        raise RollbackEligibilityError("invalid current release_id")
    if not DIGEST_RE.fullmatch(current_image_digest):
        raise RollbackEligibilityError("invalid current image_digest")
    if target_release_id == current_release_id:
        raise RollbackEligibilityError("target release equals currently active release")
    if target_image_digest == current_image_digest:
        raise RollbackEligibilityError("target digest equals currently active digest")


def validate_prior_staging_approval(prior_deploy_evidence: dict) -> None:
    """Require a prior successful staging_ok evidence for the target release."""
    if prior_deploy_evidence.get("final_status") != "staging_ok":
        raise RollbackEligibilityError(
            "target release was not previously deployed/approved for staging "
            f"(final_status={prior_deploy_evidence.get('final_status')!r})"
        )
    release_id = str(prior_deploy_evidence.get("release_id", ""))
    if not RELEASE_ID_RE.fullmatch(release_id):
        raise RollbackEligibilityError("prior deploy evidence has invalid release_id")


def validate_bundle_checksum_file(checksum_text: str, expected_checksum: str) -> str:
    token = checksum_text.strip().split()[0] if checksum_text.strip() else ""
    if not _SHA256_HEX_RE.fullmatch(token):
        raise RollbackEligibilityError("bundle.sha256 is missing or malformed")
    if token != expected_checksum:
        raise RollbackEligibilityError("bundle checksum does not match expected value")
    return token


def validate_database_compatibility(
    *,
    current_db_revision: str,
    target_recorded_revision: str,
) -> None:
    """Fail closed when current DB revision differs from target's recorded revision."""
    if not current_db_revision or not target_recorded_revision:
        raise RollbackEligibilityError(
            "database compatibility cannot be proven: missing revision evidence"
        )
    if current_db_revision != target_recorded_revision:
        raise RollbackEligibilityError(
            "database_incompatible: current revision "
            f"{current_db_revision!r} != target recorded revision "
            f"{target_recorded_revision!r}; refusing API replacement "
            "(no automatic database downgrade)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--build-workflow-run-id", required=True)
    parser.add_argument("--release-id", default="")
    parser.add_argument("--git-sha", default="")
    parser.add_argument("--image-repository", required=True)
    parser.add_argument("--image-digest", default="")
    parser.add_argument("--manifest-sha256", default="")
    parser.add_argument("--aws-account-id", required=True)
    parser.add_argument("--expected-account-id", required=True)
    parser.add_argument("--aws-region", required=True)
    parser.add_argument("--expected-region", required=True)
    parser.add_argument("--ec2-instance-id", required=True)
    parser.add_argument("--bundle-bucket", required=True)
    parser.add_argument("--prior-deploy-evidence", type=Path, default=None)
    parser.add_argument("--prior-candidates-dir", type=Path, default=None)
    parser.add_argument("--deploy-version", type=Path, default=None)
    parser.add_argument("--eligibility-out", type=Path, default=None)
    parser.add_argument("--current-release-id", default="")
    parser.add_argument("--current-image-digest", default="")
    parser.add_argument("--require-current-known", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifest = _load_json(args.manifest)
        validate_target_manifest_authority(
            manifest,
            expected_build_run_id=args.build_workflow_run_id,
            expected_git_sha=args.git_sha or None,
            expected_release_id=args.release_id or None,
            expected_image_repository=args.image_repository,
            expected_image_digest=args.image_digest or None,
            expected_manifest_sha256=args.manifest_sha256 or None,
        )
        validate_staging_identity(
            aws_account_id=args.aws_account_id,
            aws_region=args.aws_region,
            expected_account_id=args.expected_account_id,
            expected_region=args.expected_region,
            ec2_instance_id=args.ec2_instance_id,
            bundle_bucket=args.bundle_bucket,
            image_repository=str(manifest["image_repository"]),
            expected_image_repository=args.image_repository,
        )

        release_id = str(manifest["release_id"])
        image_digest = str(manifest["image_digest"])
        image_repository = str(manifest["image_repository"]).rstrip("/").lower()
        source_manifest_sha = str(manifest.get("manifest_sha256", ""))

        try:
            if args.prior_candidates_dir is not None:
                pairs = discover_candidate_pairs(args.prior_candidates_dir)
                prior = select_authoritative_prior_staging_evidence(
                    pairs,
                    expected_release_id=release_id,
                    expected_image_digest=image_digest,
                    expected_image_repository=image_repository,
                    expected_aws_account_id=args.expected_account_id,
                    expected_aws_region=args.expected_region,
                    expected_ec2_instance_id=args.ec2_instance_id,
                    expected_source_manifest_sha256=source_manifest_sha or None,
                )
            elif args.prior_deploy_evidence is not None:
                sidecar = args.prior_deploy_evidence.with_suffix(
                    args.prior_deploy_evidence.suffix + ".sha256"
                )
                payload = load_prior_evidence_with_sidecar(args.prior_deploy_evidence, sidecar)
                validate_prior_staging_ok_bindings(
                    payload,
                    expected_release_id=release_id,
                    expected_image_digest=image_digest,
                    expected_image_repository=image_repository,
                    expected_aws_account_id=args.expected_account_id,
                    expected_aws_region=args.expected_region,
                    expected_ec2_instance_id=args.ec2_instance_id,
                    expected_source_manifest_sha256=source_manifest_sha or None,
                )
                prior = ValidatedPriorStagingEvidence(
                    evidence=payload,
                    evidence_key=str(args.prior_deploy_evidence),
                    evidence_sha256=str(payload["evidence_sha256"]),
                    deploy_workflow_run_id=str(payload["deploy_workflow_run_id"]),
                    ssm_command_id=str(payload["ssm_command_id"]),
                    migration_revision_after=normalize_alembic_revision(
                        str(payload["migration_revision_after"])
                    ),
                    deployment_finished_at=str(payload["deployment_finished_at"]),
                )
            else:
                raise RollbackEligibilityError(
                    "either --prior-candidates-dir or --prior-deploy-evidence is required"
                )

            migration = resolve_target_migration_revision(
                deploy_version_path=args.deploy_version,
                validated_prior=prior,
            )
        except PriorEvidenceError as exc:
            raise RollbackEligibilityError(str(exc)) from exc

        if args.require_current_known or args.current_release_id or args.current_image_digest:
            validate_target_differs_from_current(
                target_release_id=release_id,
                target_image_digest=image_digest,
                current_release_id=args.current_release_id or None,
                current_image_digest=args.current_image_digest or None,
            )

        result = RollbackEligibilityResult(
            release_id=release_id,
            image_digest=image_digest,
            prior=prior,
            migration=migration,
        )
        if args.eligibility_out is not None:
            payload_out = {
                "release_id": result.release_id,
                "image_digest": result.image_digest,
                "prior_evidence_key": result.prior.evidence_key,
                "prior_evidence_sha256": result.prior.evidence_sha256,
                "prior_deploy_workflow_run_id": result.prior.deploy_workflow_run_id,
                "prior_ssm_command_id": result.prior.ssm_command_id,
                "prior_deployment_finished_at": result.prior.deployment_finished_at,
                "target_migration_revision": result.migration.migration_revision,
                "target_migration_revision_authority": result.migration.authority,
            }
            args.eligibility_out.parent.mkdir(parents=True, exist_ok=True)
            args.eligibility_out.write_text(
                json.dumps(payload_out, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except (OSError, json.JSONDecodeError, RollbackEligibilityError, EvidenceError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    rid = result.release_id
    digest = result.image_digest
    prior_run = result.prior.deploy_workflow_run_id
    auth = result.migration.authority
    rev = result.migration.migration_revision
    print(f"ok: rollback eligible release_id={rid} digest={digest}")
    print(f"ok: prior_run={prior_run} migration_authority={auth} migration={rev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Re-export selection helpers for tests/importers.
__all__ = [
    "ALLOWED_MIGRATION_AUTHORITIES",
    "MigrationAuthorityResult",
    "RollbackEligibilityError",
    "RollbackEligibilityResult",
    "ValidatedPriorStagingEvidence",
    "assert_no_mutable_tag_authority",
    "discover_candidate_pairs",
    "load_prior_evidence_with_sidecar",
    "resolve_target_migration_revision",
    "select_authoritative_prior_staging_evidence",
    "validate_bundle_checksum_file",
    "validate_database_compatibility",
    "validate_prior_staging_approval",
    "validate_prior_staging_ok_bindings",
    "validate_staging_identity",
    "validate_target_differs_from_current",
    "validate_target_manifest_authority",
]
