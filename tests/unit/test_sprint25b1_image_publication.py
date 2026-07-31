"""Sprint 25b.1 — immutable image publication and release manifest tests."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
from scripts.release.manifest import (
    ManifestError,
    canonicalize_for_checksum,
    compute_manifest_sha256,
    create_built_manifest,
    dumps_manifest,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[2]
BUILD_WORKFLOW = ROOT / ".github/workflows/build-image.yml"
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
SCHEMA_PATH = ROOT / "schemas/release-manifest.schema.json"

SAMPLE_SHA = "0123456789abcdef0123456789abcdef01234567"
SAMPLE_DIGEST = "sha256:" + ("a" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"


def _built_manifest(**overrides: object) -> dict:
    manifest = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-07-31T12:00:00Z",
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
    )
    if overrides:
        manifest = copy.deepcopy(manifest)
        manifest.update(overrides)
        if "manifest_sha256" not in overrides:
            manifest["manifest_sha256"] = compute_manifest_sha256(manifest)
    return manifest


def _workflow_text(path: Path) -> str:
    assert path.is_file(), f"missing workflow: {path}"
    return path.read_text(encoding="utf-8")


def test_build_image_workflow_exists() -> None:
    assert BUILD_WORKFLOW.is_file()


def test_build_image_publishes_only_from_main_or_dispatch() -> None:
    text = _workflow_text(BUILD_WORKFLOW)
    assert "workflow_run:" in text
    assert "workflow_dispatch:" in text
    assert "branches: [main]" in text
    # Must not publish from arbitrary feature-branch push triggers.
    assert re.search(r"(?m)^on:\n(?:  .*\n)*  push:", text) is None
    assert "pull_request:" not in text
    assert "refs/heads/main" in text
    assert "github.event.repository.fork == false" in text


def test_build_image_uses_ghcr_and_immutable_sha_tag() -> None:
    text = _workflow_text(BUILD_WORKFLOW)
    assert "ghcr.io" in text
    assert "sha-${SHA}" in text or "sha-${{" in text or "tag_sha=sha-" in text
    assert "packages: write" in text
    assert "contents: read" in text
    assert "actions: read" in text
    assert "cancel-in-progress: false" in text


def test_build_image_publishes_only_immutable_sha_tags() -> None:
    text = _workflow_text(BUILD_WORKFLOW)
    tags_match = re.search(r"(?m)^\s+tags:\s*\|\n((?:[ \t]+.+\n)+)", text)
    assert tags_match is not None, "build-push-action must declare a tags block"
    tags_block = tags_match.group(1)
    assert "tag_sha" in tags_block
    assert "latest" not in tags_block.lower()
    assert "ci-latest" not in tags_block.lower()
    # Must not publish mutable convenience tags from this workflow.
    assert re.search(r"(?m)^\s+tags:\s*\n\s+-\s+.+:latest\s*$", text) is None
    assert ":ci-latest" not in text
    assert re.search(r"tag_(?:ci_)?latest\s*=", text) is None


def test_build_image_captures_and_validates_digest() -> None:
    text = _workflow_text(BUILD_WORKFLOW)
    assert "steps.push.outputs.digest" in text
    assert r"^sha256:[0-9a-f]{64}$" in text
    assert "imagetools inspect" in text


def test_build_image_does_not_deploy_or_use_aws() -> None:
    text = _workflow_text(BUILD_WORKFLOW).lower()
    for needle in (
        "aws-actions",
        "configure-aws",
        "terraform apply",
        "deploy-staging",
        "deploy-production",
        "ssm:",
        "oidc",
        "role-to-assume",
        "secretsmanager",
    ):
        assert needle not in text, f"unexpected deploy/AWS content: {needle}"
    # No GitHub Environment deployment targets in this phase.
    assert re.search(r"(?m)^\s+environment:\s*", text) is None


def test_build_image_uploads_release_manifest_artifact() -> None:
    text = _workflow_text(BUILD_WORKFLOW)
    assert "upload-artifact" in text
    assert "release-manifest.json" in text
    assert "retention-days: 90" in text
    assert "create_release_manifest.py" in text


def test_build_image_records_ci_green_mechanism() -> None:
    text = _workflow_text(BUILD_WORKFLOW)
    assert "workflow_run" in text
    assert 'workflows: ["CI"]' in text or "workflows: ['CI']" in text
    assert "test_workflow_run_id" in text
    assert "gh run list" in text  # dispatch path explicit CI check


def test_staging_and_production_deploy_workflows_absent_or_no_build() -> None:
    workflows = ROOT / ".github/workflows"
    for name in ("deploy-staging.yml", "deploy-production.yml", "rollback.yml"):
        path = workflows / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "build-push-action" not in text
        # Digest inspect via buildx imagetools is allowed; image rebuild is not.
        assert "docker build " not in text
        assert "docker build\n" not in text
        assert "dockerfile" not in text or "imagetools" in text


def test_ci_no_longer_publishes_releasable_ghcr_images() -> None:
    text = _workflow_text(CI_WORKFLOW)
    assert "Push CI digest foundation to GHCR" not in text
    assert "Optional GHCR publish" not in text
    assert "packages: write" not in text
    # Still builds without pushing.
    assert "push: false" in text
    assert "build-push-action" in text
    assert "check_ruff_baseline" in text


def test_manifest_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == 1
    assert "image_digest" in schema["required"]
    assert "manifest_sha256" in schema["required"]


def test_manifest_rejects_additional_properties_via_json_schema() -> None:
    """Prove runtime validation loads and enforces the JSON Schema."""
    from scripts.release.manifest import validate_manifest_schema

    bad = _built_manifest()
    bad["unexpected_field"] = "not-in-schema"
    bad["manifest_sha256"] = compute_manifest_sha256(bad)
    with pytest.raises(ManifestError, match="JSON Schema validation failed"):
        validate_manifest_schema(bad)
    with pytest.raises(ManifestError, match="JSON Schema validation failed"):
        validate_manifest(bad)


def test_manifest_rejects_wrong_types_via_json_schema() -> None:
    bad = _built_manifest(schema_version="1")
    with pytest.raises(ManifestError, match="JSON Schema validation failed|schema_version"):
        validate_manifest(bad)


def test_valid_built_manifest_accepted() -> None:
    manifest = _built_manifest()
    validate_manifest(manifest)
    assert manifest["final_status"] == "built"
    assert manifest["environment"] == "none"
    assert manifest["staging_deployment_run_id"] is None
    assert manifest["production_approval_identity"] is None
    assert manifest["staging_verification"]["result"] == "pending"


def test_manifest_rejects_malformed_digest() -> None:
    with pytest.raises(ManifestError, match="image_digest"):
        validate_manifest(_built_manifest(image_digest="sha256:deadbeef"))


def test_manifest_rejects_mutable_only_image_reference() -> None:
    with pytest.raises(ManifestError, match="mutable tag|image_digest|image_repository"):
        validate_manifest(
            _built_manifest(
                image_digest="ghcr.io/example-org/dealbrain:latest",
            )
        )
    with pytest.raises(ManifestError, match="mutable tag|image_repository"):
        bad = _built_manifest()
        bad["image_repository"] = "ghcr.io/example-org/dealbrain:ci-latest"
        bad["manifest_sha256"] = compute_manifest_sha256(bad)
        validate_manifest(bad)


def test_manifest_rejects_invalid_git_sha() -> None:
    with pytest.raises(ManifestError, match="git_sha"):
        create_built_manifest(
            git_sha="not-a-sha",
            image_repository=SAMPLE_REPO,
            image_digest=SAMPLE_DIGEST,
            build_workflow_run_id="1",
            test_workflow_run_id="2",
        )


def test_manifest_rejects_missing_build_run_id() -> None:
    bad = _built_manifest(build_workflow_run_id="")
    with pytest.raises(ManifestError, match="build_workflow_run_id"):
        validate_manifest(bad)


def test_manifest_rejects_invalid_status_and_environment() -> None:
    with pytest.raises(ManifestError, match="final_status"):
        validate_manifest(_built_manifest(final_status="shipped"))
    with pytest.raises(ManifestError, match="environment"):
        validate_manifest(_built_manifest(environment="prod"))


def test_manifest_rejects_tampered_checksum() -> None:
    bad = _built_manifest(manifest_sha256="0" * 64)
    with pytest.raises(ManifestError, match="manifest_sha256 mismatch"):
        validate_manifest(bad)


def test_manifest_output_is_deterministic() -> None:
    a = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-07-31T12:00:00Z",
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
    )
    b = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="111",
        test_workflow_run_id="222",
        created_at="2026-07-31T12:00:00Z",
        release_id=f"rel-20260731T120000Z-{SAMPLE_SHA[:12]}",
    )
    assert a == b
    assert dumps_manifest(a) == dumps_manifest(b)
    assert canonicalize_for_checksum(a) == canonicalize_for_checksum(b)
    assert a["manifest_sha256"] == compute_manifest_sha256({**a, "manifest_sha256": None})


def test_manifest_has_no_secret_like_fields() -> None:
    manifest = _built_manifest()
    blob = json.dumps(manifest).lower()
    for fragment in (
        "password",
        "secret_key",
        "api_key",
        "database_url",
        "authorization",
        "private_key",
        "token",
    ):
        assert fragment not in blob
    # Field names themselves must not be secret-like.
    validate_manifest(manifest)


def test_manifest_rejects_unsupported_schema_version() -> None:
    with pytest.raises(ManifestError, match="schema_version"):
        validate_manifest(_built_manifest(schema_version=99))


def test_checksum_ignores_self_referential_field() -> None:
    base = _built_manifest()
    twin = copy.deepcopy(base)
    twin["manifest_sha256"] = "f" * 64
    assert compute_manifest_sha256(base) == compute_manifest_sha256(twin)


def test_architecture_lock_still_mentions_sprint_25() -> None:
    lock = (ROOT / "docs/architecture/ARCHITECTURE_LOCK.md").read_text(encoding="utf-8")
    assert "Sprint 25" in lock
    assert "DealScore" in lock


def test_image_publication_doc_exists() -> None:
    doc = ROOT / "docs/SPRINT_25B_IMAGE_PUBLICATION.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "digest" in text.lower()
    assert "build-image.yml" in text
    assert "deferred" in text.lower()
    assert "jsonschema" in text.lower() or "JSON Schema" in text
    assert "ci.yml" in text
    assert (
        "no longer" in text.lower()
        or "validation only" in text.lower()
        or "does not" in text.lower()
    )
    # Must not claim a live GHCR publish occurred during implementation.
    assert "successfully published to ghcr" not in text.lower()


def test_architecture_docs_reconcile_build_image_ownership() -> None:
    infra = (ROOT / "docs/architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md").read_text(
        encoding="utf-8"
    )
    lock = (ROOT / "docs/architecture/ARCHITECTURE_LOCK.md").read_text(encoding="utf-8")
    assert "build-image.yml" in infra
    assert "ci.yml" in infra
    assert (
        "build without push" in infra.lower()
        or "push: false" in infra.lower()
        or "without push" in infra.lower()
    )
    assert "sha-<full_git_sha>" in infra or "sha-<full_git_sha>" in lock
    assert (
        "no longer" in infra.lower()
        or "does **not** publish" in infra
        or "validation-only" in infra
    )
    assert "build-image.yml" in lock
    assert "ci.yml" in lock
    assert "Mutable tags" in lock or "mutable tags" in lock.lower()


def test_ci_still_enforces_ruff_baseline_not_full_tree_format() -> None:
    text = _workflow_text(CI_WORKFLOW)
    assert "check_ruff_baseline" in text
    assert "ruff check app tests" not in text
    assert "ruff format --check app tests" not in text


def test_create_and_validate_cli_roundtrip(tmp_path: Path) -> None:
    from scripts.release.create_release_manifest import main as create_main
    from scripts.release.validate_release_manifest import main as validate_main

    out = tmp_path / "release-manifest.json"
    rc = create_main(
        [
            "--git-sha",
            SAMPLE_SHA,
            "--image-repository",
            SAMPLE_REPO,
            "--image-digest",
            SAMPLE_DIGEST,
            "--build-workflow-run-id",
            "42",
            "--test-workflow-run-id",
            "43",
            "--created-at",
            "2026-07-31T12:00:00Z",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.is_file()
    assert out.with_name("release-manifest.json.sha256").is_file()
    assert validate_main([str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["image_tag_sha"] == f"sha-{SAMPLE_SHA}"
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", data["image_digest"])
