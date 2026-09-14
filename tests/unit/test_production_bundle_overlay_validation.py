"""Production bundle verifier overlay contracts.

Regresses the Deploy Production #1 (run 34838217618) failure:
verify_release_directory rejected compose/docker-compose.production.yml
with a stale staging-copied check while APPLICATION_RUNTIME_MEMBERS
required that same file.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from scripts.deploy.build_production_bundle import INCLUDE_FILES, build_bundle
from scripts.deploy.verify_production_bundle import (
    APPLICATION_RUNTIME_MEMBERS,
    CURRENT_BUNDLE_SCHEMA_VERSION,
    FORBIDDEN,
    HISTORICAL_BUNDLE_SCHEMA_VERSION,
    REQUIRED_MEMBERS,
    BundleVerifyError,
    extract_validated_bundle,
    main,
    verify_bundle,
    verify_release_directory,
)
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts/deploy/verify_production_bundle.py"
BUILDER = ROOT / "scripts/deploy/build_production_bundle.py"
WORKFLOW = ROOT / ".github/workflows/deploy-production.yml"

SAMPLE_SHA = "37418968e23320129020015d7e70f2a883672a0b"
SAMPLE_DIGEST = "sha256:b8fd76d2e4ff69f94568097790a1dae5dd9de6ea598c6ae81d0ed001fb9f19e4"
SAMPLE_REPO = "ghcr.io/markbilbao/dealbrain"
BASELINE_RELEASE = f"rel-20260911T084953Z-{SAMPLE_SHA[:12]}"
MANIFEST_SHA = "c" * 64


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finalize_meta(release: Path, meta: dict) -> None:
    meta_path = release / "bundle-meta.json"
    _write_json(meta_path, meta)
    meta["file_checksums"]["bundle-meta.json"] = _sha(meta_path)
    _write_json(meta_path, meta)


def _historical_production_release_tree(tmp_path: Path) -> Path:
    """Schema-1 production tree: runtime members only, no staging overlay."""
    release = tmp_path / "releases" / BASELINE_RELEASE
    (release / "compose").mkdir(parents=True)
    (release / "manifest").mkdir(parents=True)
    (release / "bin").mkdir(parents=True)
    (release / "compose" / "docker-compose.base.yml").write_text("services: {}\n", encoding="utf-8")
    (release / "compose" / "docker-compose.production.yml").write_text(
        "services:\n  api: {}\n", encoding="utf-8"
    )
    _write_json(
        release / "manifest" / "release-manifest.json",
        {
            "release_id": BASELINE_RELEASE,
            "git_sha": SAMPLE_SHA,
            "image_repository": SAMPLE_REPO,
            "image_digest": SAMPLE_DIGEST,
        },
    )
    (release / "bin" / "ghcr-login.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    files = {
        "compose/docker-compose.base.yml": _sha(release / "compose/docker-compose.base.yml"),
        "compose/docker-compose.production.yml": _sha(
            release / "compose/docker-compose.production.yml"
        ),
        "manifest/release-manifest.json": _sha(release / "manifest/release-manifest.json"),
        "bin/ghcr-login.sh": _sha(release / "bin/ghcr-login.sh"),
    }
    meta = {
        "schema_version": HISTORICAL_BUNDLE_SCHEMA_VERSION,
        "release_id": BASELINE_RELEASE,
        "git_sha": SAMPLE_SHA,
        "image_repository": SAMPLE_REPO,
        "image_digest": SAMPLE_DIGEST,
        "source_manifest_sha256": MANIFEST_SHA,
        "file_checksums": files,
        "created_at": "2026-09-11T08:49:53Z",
    }
    _finalize_meta(release, meta)
    return release


def _tar_release(release: Path, tarball: Path, *, exclude: set[str] | None = None) -> Path:
    skip = exclude or set()
    with tarfile.open(tarball, "w:gz") as tar:
        for path in sorted(release.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(release).as_posix()
            if arcname in skip:
                continue
            tar.add(path, arcname=arcname)
    return tarball


def _malicious_tarball(tmp: Path, member_name: str, *, link_type: str | None = None) -> Path:
    tar_path = tmp / "evil.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        if link_type == "symlink":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        elif link_type == "hardlink":
            data = b"x"
            base = tarfile.TarInfo(name="bin/harmless.txt")
            base.size = len(data)
            tar.addfile(base, fileobj=io.BytesIO(data))
            link = tarfile.TarInfo(name=member_name)
            link.type = tarfile.LNKTYPE
            link.linkname = "bin/harmless.txt"
            tar.addfile(link)
        else:
            data = b"evil"
            info = tarfile.TarInfo(name=member_name)
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))
    return tar_path


def _built_schema2_bundle(tmp_path: Path) -> tuple[Path, Path, dict]:
    manifest = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="34838217618",
        test_workflow_run_id="222",
        created_at="2026-09-11T08:49:53Z",
        release_id=BASELINE_RELEASE,
    )
    man_path = tmp_path / "release-manifest.json"
    _write_json(man_path, manifest)
    tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=tmp_path / "out")
    return tarball, checksum_path, meta


def test_verifier_source_no_longer_contradicts_production_overlay() -> None:
    text = VERIFIER.read_text(encoding="utf-8")
    assert "compose/docker-compose.production.yml" in APPLICATION_RUNTIME_MEMBERS
    assert "docker-compose.staging.yml" in FORBIDDEN
    assert "docker-compose.production.yml" not in FORBIDDEN
    assert "production overlay must not be present" not in text
    assert "staging compose overlays missing" not in text
    assert "compose_staging" not in text
    assert "compose_production" in text
    assert "staging overlay must not be present" in text
    assert "production compose overlays missing" in text
    builder = BUILDER.read_text(encoding="utf-8")
    assert "infra/compose/docker-compose.production.yml" in builder
    assert "docker-compose.staging.yml" in builder
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "verify_production_bundle.py" in workflow
    assert "production overlay missing from production bundle" in workflow
    assert "staging overlay present in production bundle" in workflow


def test_production_overlay_present_passes(tmp_path: Path) -> None:
    release = _historical_production_release_tree(tmp_path)
    meta = verify_release_directory(
        release,
        expected_release_id=BASELINE_RELEASE,
        expected_git_sha=SAMPLE_SHA,
        expected_image_repository=SAMPLE_REPO,
        expected_digest=SAMPLE_DIGEST,
        expected_source_manifest_sha256=MANIFEST_SHA,
    )
    assert meta["schema_version"] == HISTORICAL_BUNDLE_SCHEMA_VERSION
    tarball = _tar_release(release, tmp_path / "hist.tar.gz")
    result = verify_bundle(
        tarball,
        expected_checksum=_sha(tarball),
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert result["meta"]["release_id"] == BASELINE_RELEASE


def test_staging_overlay_present_fails(tmp_path: Path) -> None:
    release = _historical_production_release_tree(tmp_path)
    staging = release / "compose" / "docker-compose.staging.yml"
    staging.write_text("services:\n  leaked: {}\n", encoding="utf-8")
    with pytest.raises(BundleVerifyError, match="staging overlay must not be present"):
        verify_release_directory(release, expected_release_id=BASELINE_RELEASE)

    tarball = tmp_path / "with-staging.tar.gz"
    _tar_release(release, tarball)
    with pytest.raises(BundleVerifyError, match="forbidden member"):
        verify_bundle(tarball)

    with pytest.raises(BundleVerifyError, match="forbidden|staging"):
        verify_bundle(_malicious_tarball(tmp_path, "compose/docker-compose.staging.yml"))


def test_production_overlay_missing_fails(tmp_path: Path) -> None:
    release = _historical_production_release_tree(tmp_path)
    (release / "compose" / "docker-compose.production.yml").unlink()
    with pytest.raises(BundleVerifyError, match="missing required member|production compose"):
        verify_release_directory(release, expected_release_id=BASELINE_RELEASE)

    intact = _historical_production_release_tree(tmp_path / "packed")
    tarball = _tar_release(
        intact,
        tmp_path / "missing-prod.tar.gz",
        exclude={"compose/docker-compose.production.yml"},
    )
    with pytest.raises(BundleVerifyError, match="missing required member|production compose"):
        verify_bundle(tarball)


def test_current_schema2_production_bundle_verifies(tmp_path: Path) -> None:
    tarball, checksum_path, meta = _built_schema2_bundle(tmp_path)
    assert meta["schema_version"] == CURRENT_BUNDLE_SCHEMA_VERSION
    for rel in REQUIRED_MEMBERS:
        assert rel in meta["file_checksums"]
    assert "compose/docker-compose.production.yml" in meta["file_checksums"]
    assert "compose/docker-compose.staging.yml" not in meta["file_checksums"]
    checksum = checksum_path.read_text(encoding="utf-8").split()[0]
    with tarfile.open(tarball, "r:gz") as archive:
        names = archive.getnames()
    assert "compose/docker-compose.production.yml" in names
    assert "compose/docker-compose.base.yml" in names
    assert not any("docker-compose.staging.yml" in name for name in names)
    result = verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert result["meta"]["schema_version"] == CURRENT_BUNDLE_SCHEMA_VERSION
    dest = tmp_path / "extracted"
    extracted = extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert extracted["meta"]["release_id"] == BASELINE_RELEASE
    for _src_rel, dst_rel in INCLUDE_FILES:
        assert (dest / dst_rel).is_file()


def test_retained_release_directory_follows_same_overlay_rules(tmp_path: Path) -> None:
    tarball, checksum_path, _meta = _built_schema2_bundle(tmp_path)
    dest = tmp_path / "retained"
    extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum_path.read_text(encoding="utf-8").split()[0],
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    verify_release_directory(
        dest,
        expected_release_id=BASELINE_RELEASE,
        expected_git_sha=SAMPLE_SHA,
        expected_image_repository=SAMPLE_REPO,
        expected_digest=SAMPLE_DIGEST,
    )
    assert main(["--verify-release-dir", str(dest), "--release-id", BASELINE_RELEASE]) == 0

    leaked = dest / "compose" / "docker-compose.staging.yml"
    leaked.write_text("leaked\n", encoding="utf-8")
    with pytest.raises(BundleVerifyError, match="staging overlay must not be present"):
        verify_release_directory(dest, expected_release_id=BASELINE_RELEASE)
    leaked.unlink()

    production = dest / "compose" / "docker-compose.production.yml"
    production.unlink()
    with pytest.raises(BundleVerifyError, match="missing required member|production compose"):
        verify_release_directory(dest, expected_release_id=BASELINE_RELEASE)


def test_archive_still_rejects_traversal_links_specials_and_secrets(tmp_path: Path) -> None:
    with pytest.raises(BundleVerifyError, match="traversal|absolute|unexpected"):
        verify_bundle(_malicious_tarball(tmp_path, "../escape"))
    with pytest.raises(BundleVerifyError, match="absolute|unexpected"):
        verify_bundle(_malicious_tarball(tmp_path, "/absolute/path"))
    with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
        verify_bundle(_malicious_tarball(tmp_path, "bin/link", link_type="symlink"))
    with pytest.raises(BundleVerifyError, match="symlink|hardlink"):
        verify_bundle(_malicious_tarball(tmp_path, "bin/hard", link_type="hardlink"))
    with pytest.raises(BundleVerifyError, match="forbidden"):
        verify_bundle(_malicious_tarball(tmp_path, "compose/.env"))
    with pytest.raises(BundleVerifyError, match="forbidden"):
        verify_bundle(_malicious_tarball(tmp_path, "manifest/terraform.tfstate"))
    with pytest.raises(BundleVerifyError, match="forbidden"):
        verify_bundle(_malicious_tarball(tmp_path, "compose/.git/HEAD"))
    with pytest.raises(BundleVerifyError, match="forbidden"):
        verify_bundle(_malicious_tarball(tmp_path, "compose/docker-compose.staging.yml"))


def test_application_runtime_members_require_production_not_staging() -> None:
    assert "compose/docker-compose.production.yml" in APPLICATION_RUNTIME_MEMBERS
    assert "compose/docker-compose.base.yml" in APPLICATION_RUNTIME_MEMBERS
    assert "compose/docker-compose.staging.yml" not in APPLICATION_RUNTIME_MEMBERS
    assert "compose/docker-compose.staging.yml" not in REQUIRED_MEMBERS
