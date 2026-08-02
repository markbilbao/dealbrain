#!/usr/bin/env python3
"""Validate a release manifest for staging ingestion (Sprint 25b.3).

Does not mutate the original build manifest. Rejects previously staged
manifests, mutable-tag authority, and mismatched workflow evidence.

Invoke from the repository root as a module so ``scripts.*`` imports resolve:

  python -m scripts.deploy.validate_staging_release MANIFEST [options]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.release.manifest import (
    DIGEST_RE,
    GIT_SHA_RE,
    IMAGE_TAG_SHA_RE,
    MUTABLE_TAG_MARKERS,
    ManifestError,
    compute_manifest_sha256,
    load_manifest,
    validate_manifest,
)

GHCR_REPO_RE = re.compile(r"^ghcr\.io/[a-z0-9]([a-z0-9._-]*/)+[a-z0-9._-]+$")


class StagingIngestError(ValueError):
    """Raised when a manifest is not eligible for staging deployment."""


def validate_for_staging(
    payload: dict,
    *,
    expected_build_run_id: str | None = None,
    expected_git_sha: str | None = None,
    expected_release_id: str | None = None,
    expected_image_repository: str | None = None,
    require_ci_run_id: bool = True,
) -> dict:
    """Validate schema/semantic checksum then staging-specific gates.

    Returns the validated payload unchanged (never mutates).
    """
    validate_manifest(payload)

    # Recompute checksum explicitly (validate_manifest already does; defense in depth).
    expected_checksum = compute_manifest_sha256(payload)
    if payload.get("manifest_sha256") != expected_checksum:
        raise StagingIngestError("manifest_sha256 recomputation mismatch")

    if payload.get("final_status") != "built":
        raise StagingIngestError(
            f"final_status must be 'built' for staging ingest, got {payload.get('final_status')!r}"
        )
    if payload.get("environment") != "none":
        raise StagingIngestError(
            f"environment must be 'none' for staging ingest, got {payload.get('environment')!r}"
        )

    # Reject previously staged manifests (built-state invariant).
    if payload.get("staging_deployment_run_id") is not None:
        raise StagingIngestError("manifest already has staging_deployment_run_id set")
    if payload.get("staging_timestamp") is not None:
        raise StagingIngestError("manifest already has staging_timestamp set")
    staging_verification = payload.get("staging_verification") or {}
    if staging_verification.get("result") not in (None, "pending"):
        got = staging_verification.get("result")
        raise StagingIngestError(
            f"staging_verification.result must be pending, got {got!r}"
        )

    git_sha = str(payload.get("git_sha", ""))
    if not GIT_SHA_RE.fullmatch(git_sha):
        raise StagingIngestError("invalid git_sha")
    if expected_git_sha and git_sha != expected_git_sha:
        raise StagingIngestError(
            f"git_sha mismatch: manifest={git_sha} expected={expected_git_sha}"
        )

    digest = str(payload.get("image_digest", ""))
    if not DIGEST_RE.fullmatch(digest):
        raise StagingIngestError("invalid image_digest")

    tag_sha = str(payload.get("image_tag_sha", ""))
    if not IMAGE_TAG_SHA_RE.fullmatch(tag_sha):
        raise StagingIngestError("invalid image_tag_sha")
    if tag_sha != f"sha-{git_sha}":
        raise StagingIngestError("image_tag_sha must equal sha-<git_sha>")

    repo = str(payload.get("image_repository", "")).rstrip("/").lower()
    if not GHCR_REPO_RE.fullmatch(repo):
        raise StagingIngestError("invalid image_repository")
    if expected_image_repository and repo != expected_image_repository.rstrip("/").lower():
        raise StagingIngestError(
            f"image_repository mismatch: manifest={repo} expected={expected_image_repository}"
        )

    # Mutable tags must never be deployment authority.
    haystack = f"{repo}:{tag_sha}"
    for marker in MUTABLE_TAG_MARKERS:
        if marker in haystack or marker in repo:
            raise StagingIngestError(f"mutable tag marker forbidden: {marker}")
    # Reject tag-only authority fields if someone stuffed a tag into digest.
    if ":" in digest and not digest.startswith("sha256:"):
        raise StagingIngestError("digest must be sha256:… only")

    build_run = str(payload.get("build_workflow_run_id", ""))
    if expected_build_run_id and build_run != str(expected_build_run_id):
        raise StagingIngestError(
            f"build_workflow_run_id mismatch: manifest={build_run} expected={expected_build_run_id}"
        )

    test_run = str(payload.get("test_workflow_run_id", ""))
    if require_ci_run_id and not test_run:
        raise StagingIngestError("test_workflow_run_id required")

    if expected_release_id and payload.get("release_id") != expected_release_id:
        raise StagingIngestError(
            f"release_id mismatch: manifest={payload.get('release_id')} "
            f"expected={expected_release_id}"
        )

    # Production fields must remain unset at staging ingest.
    if payload.get("production_approval_identity") is not None:
        raise StagingIngestError("production_approval_identity must be null at staging ingest")
    if payload.get("production_deployment_run_id") is not None:
        raise StagingIngestError("production_deployment_run_id must be null at staging ingest")

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--build-workflow-run-id", default=None)
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--image-repository", default=None)
    args = parser.parse_args(argv)
    try:
        payload = load_manifest(args.manifest)
        validate_for_staging(
            payload,
            expected_build_run_id=args.build_workflow_run_id,
            expected_git_sha=args.git_sha,
            expected_release_id=args.release_id or None,
            expected_image_repository=args.image_repository,
        )
    except (OSError, json.JSONDecodeError, ManifestError, StagingIngestError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "ok: release_id={rid} status={status} digest={digest} manifest_sha256={sha}".format(
            rid=payload["release_id"],
            status=payload["final_status"],
            digest=payload["image_digest"],
            sha=payload["manifest_sha256"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
