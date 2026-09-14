"""Production bootstrap SAFEEXTRACT evidence-member contract.

Regresses Deploy Production run 34879715228 / SSM command
3d00417a-d5b0-4f44-b3e7-5a5b57679bf7:

  FAIL: missing required member: bin/evidence.py

The production bundle builder ships scripts/deploy/production_evidence.py as
bin/production_evidence.py. Staging's scripts/deploy/evidence.py -> bin/evidence.py
must remain staging-only. The embedded production SAFEEXTRACT list is a
duplicated subset of the canonical schema-2 verifier; this module derives and
compares those sets so the drift cannot return silently.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from types import ModuleType

import pytest
from scripts.deploy.build_production_bundle import INCLUDE_FILES, build_bundle
from scripts.deploy.build_staging_bundle import INCLUDE_FILES as STAGING_INCLUDE_FILES
from scripts.deploy.verify_production_bundle import (
    CURRENT_BUNDLE_SCHEMA_VERSION,
    FORBIDDEN,
    required_members_for_schema,
)
from scripts.deploy.verify_production_bundle import (
    REQUIRED_MEMBERS as CANONICAL_REQUIRED,
)
from scripts.deploy.verify_production_bundle import (
    BundleVerifyError as CanonicalBundleVerifyError,
)
from scripts.deploy.verify_production_bundle import (
    extract_validated_bundle as canonical_extract,
)
from scripts.deploy.verify_production_bundle import (
    verify_bundle as canonical_verify_bundle,
)
from scripts.deploy.verify_staging_bundle import REQUIRED_MEMBERS as STAGING_REQUIRED
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
PROD_USER_DATA = ROOT / "infra/ec2/user_data/production.sh"
STAGING_USER_DATA = ROOT / "infra/ec2/user_data/staging.sh"
BUILDER = ROOT / "scripts/deploy/build_production_bundle.py"
CANONICAL_PY = ROOT / "scripts/deploy/verify_production_bundle.py"
STAGING_EVIDENCE_SRC = ROOT / "scripts/deploy/evidence.py"
PROD_EVIDENCE_SRC = ROOT / "scripts/deploy/production_evidence.py"
PROD_DEPLOY_SH = ROOT / "scripts/deploy/host/dealbrain-production-deploy.sh"

SAMPLE_SHA = "37418968e23320129020015d7e70f2a883672a0b"
SAMPLE_DIGEST = "sha256:b8fd76d2e4ff69f94568097790a1dae5dd9de6ea598c6ae81d0ed001fb9f19e4"
SAMPLE_REPO = "ghcr.io/markbilbao/dealbrain"
BASELINE_RELEASE = f"rel-20260911T084953Z-{SAMPLE_SHA[:12]}"

PRODUCTION_EVIDENCE_MEMBER = "bin/production_evidence.py"
STAGING_EVIDENCE_MEMBER = "bin/evidence.py"
PRODUCTION_EVIDENCE_SOURCE = "scripts/deploy/production_evidence.py"
STAGING_EVIDENCE_SOURCE = "scripts/deploy/evidence.py"

# Members always written by build_production_bundle.py in addition to INCLUDE_FILES.
GENERATED_ALWAYS_MEMBERS = frozenset(
    {
        "manifest/release-manifest.json",
        "bundle-meta.json",
    }
)

# Baseline bootstrap gate: deploy-time members only. Rollback tooling is
# delivered by schema-2 bundles and is intentionally not required here.
PRODUCTION_BOOTSTRAP_BASELINE_REQUIRED_MEMBERS = (
    "compose/docker-compose.base.yml",
    "compose/docker-compose.production.yml",
    "bin/dealbrain-production-deploy.sh",
    "bin/deploy_atomicity.sh",
    "bin/assemble-runtime-env.py",
    "bin/ghcr-login.sh",
    "bin/verify-production.sh",
    "bin/alb_target_health.py",
    "bin/production_evidence.py",
    "bin/write-production-evidence.py",
    "bin/production-deploy-evidence.schema.json",
    "bin/log_redaction.py",
    "manifest/release-manifest.json",
    "bundle-meta.json",
)

PRODUCTION_ROLLBACK_ONLY_REQUIRED_MEMBERS = (
    "bin/dealbrain-production-rollback.sh",
    "bin/production_rollback_evidence.py",
    "bin/write-production-rollback-evidence.py",
    "bin/prior_production_evidence.py",
    "bin/verify_host_production_rollback_tooling.py",
    "bin/resolve-production-rollback-migration.py",
    "bin/production-rollback-evidence.schema.json",
)

STAGING_ONLY_MEMBERS = (
    "bin/evidence.py",
    "bin/write-staging-evidence.py",
    "bin/staging-deploy-evidence.schema.json",
    "bin/dealbrain-staging-deploy.sh",
    "bin/verify-staging.sh",
    "compose/docker-compose.staging.yml",
    "bin/dealbrain-staging-rollback.sh",
    "bin/rollback_evidence.py",
    "bin/write-staging-rollback-evidence.py",
    "bin/prior_staging_evidence.py",
    "bin/verify_host_rollback_tooling.py",
    "bin/resolve-rollback-migration.py",
    "bin/staging-rollback-evidence.schema.json",
)

EXTRACT_CONTRACT_MARKERS = (
    "path traversal rejected",
    "symlink/hardlink rejected",
    "special file rejected",
    "forbidden member in bundle",
    "bundle checksum mismatch",
    "missing required member",
    "staging overlay must not be present",
    "release_id mismatch",
    "image_digest mismatch",
)


def _extract_safeextract_source() -> str:
    text = PROD_USER_DATA.read_text(encoding="utf-8")
    marker = "cat >/opt/dealbrain/bin/verify_production_bundle.py << 'SAFEEXTRACT'\n"
    start = text.index(marker) + len(marker)
    end = text.index("\nSAFEEXTRACT\n", start)
    source = text[start:end]
    assert source.startswith("#!/usr/bin/env python3"), "SAFEEXTRACT shebang missing"
    return source


def _load_embedded_verifier() -> ModuleType:
    source = _extract_safeextract_source()
    module = ModuleType("dealbrain_production_bootstrap_safeextract")
    compiled = compile(source, "<SAFEEXTRACT:production.sh>", "exec")
    exec(compiled, module.__dict__)  # noqa: S102 — intentional behavioral load
    return module


def _builder_emitted_members() -> frozenset[str]:
    return frozenset(dst for _src, dst in INCLUDE_FILES) | GENERATED_ALWAYS_MEMBERS


def _built_schema2_bundle(tmp_path: Path) -> tuple[Path, str, dict]:
    manifest = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="34879715228",
        test_workflow_run_id="222",
        created_at="2026-09-11T08:49:53Z",
        release_id=BASELINE_RELEASE,
    )
    man_path = tmp_path / "release-manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=tmp_path / "out")
    checksum = checksum_path.read_text(encoding="utf-8").split()[0]
    return tarball, checksum, meta


def _malicious_tarball(
    tmp: Path,
    member_name: str,
    *,
    link_type: str | None = None,
) -> Path:
    tar_path = tmp / f"evil-{hashlib.sha256(member_name.encode()).hexdigest()[:10]}.tar.gz"
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
        elif link_type == "chr":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.CHRTYPE
            info.devmajor = 1
            info.devminor = 3
            tar.addfile(info)
        elif link_type == "fifo":
            info = tarfile.TarInfo(name=member_name)
            info.type = tarfile.FIFOTYPE
            tar.addfile(info)
        else:
            data = b"evil"
            info = tarfile.TarInfo(name=member_name)
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))
    return tar_path


def test_bootstrap_requires_production_evidence_not_staging_evidence() -> None:
    mod = _load_embedded_verifier()
    assert PRODUCTION_EVIDENCE_MEMBER in mod.REQUIRED_MEMBERS
    assert STAGING_EVIDENCE_MEMBER not in mod.REQUIRED_MEMBERS
    source = _extract_safeextract_source()
    assert f'"{PRODUCTION_EVIDENCE_MEMBER}"' in source
    assert f'"{STAGING_EVIDENCE_MEMBER}"' not in source


def test_production_member_sets_cannot_silently_drift() -> None:
    """Derive and compare duplicated production member lists.

    Catches the class of bug where production.sh SAFEEXTRACT, the bundle
    builder, and the canonical schema-2 verifier diverge on required names.
    """
    bootstrap = frozenset(_load_embedded_verifier().REQUIRED_MEMBERS)
    emitted = _builder_emitted_members()
    canonical = frozenset(CANONICAL_REQUIRED)
    schema2 = frozenset(required_members_for_schema(CURRENT_BUNDLE_SCHEMA_VERSION))
    expected_bootstrap = frozenset(PRODUCTION_BOOTSTRAP_BASELINE_REQUIRED_MEMBERS)
    expected_rollback = frozenset(PRODUCTION_ROLLBACK_ONLY_REQUIRED_MEMBERS)

    assert bootstrap == expected_bootstrap
    assert schema2 == canonical
    assert bootstrap <= emitted
    assert bootstrap <= canonical
    assert canonical - bootstrap == expected_rollback
    assert expected_rollback.isdisjoint(bootstrap)
    assert PRODUCTION_EVIDENCE_MEMBER in bootstrap
    assert PRODUCTION_EVIDENCE_MEMBER in emitted
    assert PRODUCTION_EVIDENCE_MEMBER in canonical
    assert STAGING_EVIDENCE_MEMBER not in bootstrap
    assert STAGING_EVIDENCE_MEMBER not in emitted
    assert STAGING_EVIDENCE_MEMBER not in canonical
    for rel in STAGING_ONLY_MEMBERS:
        assert rel not in bootstrap
        assert rel not in emitted
        assert rel not in canonical


def test_bootstrap_required_members_are_emitted_and_schema2_compatible() -> None:
    emitted = _builder_emitted_members()
    canonical = frozenset(CANONICAL_REQUIRED)
    for rel in PRODUCTION_BOOTSTRAP_BASELINE_REQUIRED_MEMBERS:
        assert rel in emitted, f"bootstrap member not emitted by builder: {rel}"
        assert rel in canonical, f"bootstrap member missing from schema-2 verifier: {rel}"


def test_staging_evidence_module_remains_staging_only() -> None:
    assert STAGING_EVIDENCE_SRC.is_file()
    assert PROD_EVIDENCE_SRC.is_file()
    assert STAGING_EVIDENCE_SRC.read_bytes() != PROD_EVIDENCE_SRC.read_bytes()
    assert (STAGING_EVIDENCE_SOURCE, STAGING_EVIDENCE_MEMBER) in STAGING_INCLUDE_FILES
    assert STAGING_EVIDENCE_MEMBER in STAGING_REQUIRED
    staging_ud = STAGING_USER_DATA.read_text(encoding="utf-8")
    assert f'"{STAGING_EVIDENCE_MEMBER}"' in staging_ud
    assert (STAGING_EVIDENCE_SOURCE, STAGING_EVIDENCE_MEMBER) not in INCLUDE_FILES
    assert (PRODUCTION_EVIDENCE_SOURCE, PRODUCTION_EVIDENCE_MEMBER) in INCLUDE_FILES
    builder = BUILDER.read_text(encoding="utf-8")
    assert STAGING_EVIDENCE_SOURCE not in builder
    assert PRODUCTION_EVIDENCE_SOURCE in builder
    canonical = CANONICAL_PY.read_text(encoding="utf-8")
    assert f'"{STAGING_EVIDENCE_MEMBER}"' not in canonical
    assert f'"{PRODUCTION_EVIDENCE_MEMBER}"' in canonical
    deploy = PROD_DEPLOY_SH.read_text(encoding="utf-8")
    assert "bin/production_evidence.py" in deploy
    assert "bin/evidence.py" not in deploy


def test_production_bundle_contains_no_staging_evidence_module(tmp_path: Path) -> None:
    tarball, _checksum, meta = _built_schema2_bundle(tmp_path)
    with tarfile.open(tarball, "r:gz") as archive:
        names = archive.getnames()
    assert PRODUCTION_EVIDENCE_MEMBER in names
    assert STAGING_EVIDENCE_MEMBER not in names
    assert not any(name.endswith("/evidence.py") for name in names)
    assert PRODUCTION_EVIDENCE_MEMBER in meta["file_checksums"]
    assert STAGING_EVIDENCE_MEMBER not in meta["file_checksums"]
    for rel in STAGING_ONLY_MEMBERS:
        assert rel not in names
        assert rel not in meta["file_checksums"]


def test_production_overlay_required_staging_overlay_forbidden() -> None:
    mod = _load_embedded_verifier()
    assert "compose/docker-compose.production.yml" in mod.REQUIRED_MEMBERS
    assert "compose/docker-compose.staging.yml" not in mod.REQUIRED_MEMBERS
    assert "docker-compose.staging.yml" in mod.FORBIDDEN
    assert "docker-compose.production.yml" not in FORBIDDEN
    assert "staging overlay must not be present" in _extract_safeextract_source()
    assert "production overlay must not be present" not in _extract_safeextract_source()


def test_embedded_safeextract_still_fail_closed_on_unsafe_archives(tmp_path: Path) -> None:
    mod = _load_embedded_verifier()
    cases = [
        ("../escape", None, "traversal|absolute|unexpected"),
        ("/absolute/path", None, "absolute|unexpected"),
        ("bin/link", "symlink", "symlink|hardlink"),
        ("bin/hard", "hardlink", "symlink|hardlink"),
        ("bin/evil-chr", "chr", "special file"),
        ("bin/evil-fifo", "fifo", "special file"),
        ("compose/.env", None, "forbidden"),
        ("manifest/terraform.tfstate", None, "forbidden"),
        ("compose/.git/HEAD", None, "forbidden"),
        ("compose/docker-compose.staging.yml", None, "forbidden|staging"),
    ]
    for name, link_type, match in cases:
        evil = _malicious_tarball(tmp_path, name, link_type=link_type)
        with pytest.raises(mod.BundleVerifyError, match=match):
            mod.extract_validated_bundle(
                evil,
                tmp_path / f"dest-{hashlib.sha256(name.encode()).hexdigest()[:8]}",
                expected_checksum=hashlib.sha256(evil.read_bytes()).hexdigest(),
            )
        with pytest.raises(CanonicalBundleVerifyError, match=match):
            canonical_verify_bundle(
                evil,
                expected_checksum=hashlib.sha256(evil.read_bytes()).hexdigest(),
            )


def test_schema2_production_bundle_passes_canonical_and_bootstrap(
    tmp_path: Path,
) -> None:
    mod = _load_embedded_verifier()
    tarball, checksum, meta = _built_schema2_bundle(tmp_path)
    assert meta["schema_version"] == CURRENT_BUNDLE_SCHEMA_VERSION
    for rel in PRODUCTION_BOOTSTRAP_BASELINE_REQUIRED_MEMBERS:
        assert rel in meta["file_checksums"]
    for rel in CANONICAL_REQUIRED:
        assert rel in meta["file_checksums"]
    assert PRODUCTION_EVIDENCE_MEMBER in meta["file_checksums"]
    assert STAGING_EVIDENCE_MEMBER not in meta["file_checksums"]

    canon = canonical_verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    dest = tmp_path / "bootstrap-extract"
    embedded = mod.extract_validated_bundle(
        tarball,
        dest,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert canon["meta"]["release_id"] == embedded["meta"]["release_id"]
    assert canon["checksum"] == embedded["checksum"]
    assert (dest / PRODUCTION_EVIDENCE_MEMBER).is_file()
    assert not (dest / STAGING_EVIDENCE_MEMBER).exists()
    assert (dest / "compose/docker-compose.production.yml").is_file()
    assert not (dest / "compose/docker-compose.staging.yml").exists()

    dest2 = tmp_path / "canonical-extract"
    canonical_extract(
        tarball,
        dest2,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert (dest2 / PRODUCTION_EVIDENCE_MEMBER).is_file()


def test_embedded_checksum_release_id_and_digest_still_enforced(tmp_path: Path) -> None:
    mod = _load_embedded_verifier()
    tarball, checksum, meta = _built_schema2_bundle(tmp_path)
    with pytest.raises(mod.BundleVerifyError, match="checksum mismatch"):
        mod.extract_validated_bundle(
            tarball,
            tmp_path / "bad-checksum",
            expected_checksum="0" * 64,
        )
    with pytest.raises(mod.BundleVerifyError, match="release_id mismatch"):
        mod.extract_validated_bundle(
            tarball,
            tmp_path / "bad-rid",
            expected_checksum=checksum,
            expected_release_id="rel-not-this",
        )
    with pytest.raises(mod.BundleVerifyError, match="image_digest mismatch"):
        mod.extract_validated_bundle(
            tarball,
            tmp_path / "bad-digest",
            expected_checksum=checksum,
            expected_release_id=meta["release_id"],
            expected_digest="sha256:" + ("a" * 64),
        )


def test_embedded_extract_contract_markers_preserved() -> None:
    source = _extract_safeextract_source()
    for marker in EXTRACT_CONTRACT_MARKERS:
        assert marker in source, f"bootstrap missing marker: {marker}"
    assert "extractall(" not in source
    for forbidden in (".env", "terraform.tfstate", ".git/"):
        assert forbidden in source


def test_no_production_evidence_alias_was_added() -> None:
    builder = BUILDER.read_text(encoding="utf-8")
    assert 'bin/evidence.py"' not in builder
    include_dst = {dst for _src, dst in INCLUDE_FILES}
    assert STAGING_EVIDENCE_MEMBER not in include_dst
    assert PRODUCTION_EVIDENCE_MEMBER in include_dst
    source = _extract_safeextract_source()
    assert "bin/evidence.py" not in source
