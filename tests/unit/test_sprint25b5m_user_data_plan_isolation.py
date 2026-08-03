"""Sprint 25b.5m — bootstrap contract vs bundle-delivered rollback tooling.

Proves:
- staging user_data retains approved Sprint 25b.5h SAFEEXTRACT hardening
- only rollback-specific REQUIRED_MEMBERS were removed from bootstrap
- rollback host tooling is delivered by Deploy Staging schema-2 bundles
- Deploy Staging installs tooling and writes capability after install
- Rollback preflight rejects missing/outdated/mismatched tooling
- no EC2 lifecycle ignore_changes for user_data_base64
- documentation declares the combined SSM/IAM + user_data apply gate
- production paths remain untouched
- live EC2 user_data SHA is never sole bootstrap authority
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest
from scripts.deploy.build_staging_bundle import INCLUDE_FILES, build_bundle
from scripts.deploy.verify_host_rollback_tooling import (
    REQUIRED_TOOLING_FILES,
    HostToolingError,
    build_host_tooling_capability,
    verify_host_rollback_tooling,
    write_host_tooling_capability,
)
from scripts.deploy.verify_staging_bundle import (
    CURRENT_BUNDLE_SCHEMA_VERSION,
    HOST_TOOLING_MEMBERS,
    REQUIRED_MEMBERS,
    verify_bundle,
)
from scripts.release.manifest import create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
USER_DATA = ROOT / "infra/ec2/user_data/staging.sh"
EC2_MAIN = ROOT / "infra/terraform/modules/ec2/main.tf"
STAGING_MAIN = ROOT / "infra/terraform/environments/staging/main.tf"
PROD_TF = ROOT / "infra/terraform/environments/production"
DEPLOY_SH = ROOT / "scripts/deploy/host/dealbrain-staging-deploy.sh"
ROLLBACK_SH = ROOT / "scripts/deploy/host/dealbrain-staging-rollback.sh"
RUNBOOK = ROOT / "docs/runbooks/STAGING_ROLLBACK.md"
WORKFLOWS = ROOT / ".github/workflows"

SAMPLE_SHA = "83bfc6c57fd99a43445b6edaddcaf863fabf3473"
SAMPLE_DIGEST = "sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f"
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
BASELINE_RELEASE = f"rel-20260802T093246Z-{SAMPLE_SHA[:12]}"

# Pre-PR #40 / Sprint 25b.5h bootstrap REQUIRED_MEMBERS (declarative authority).
BOOTSTRAP_BASELINE_REQUIRED_MEMBERS = (
    "compose/docker-compose.base.yml",
    "compose/docker-compose.staging.yml",
    "bin/dealbrain-staging-deploy.sh",
    "bin/deploy_atomicity.sh",
    "bin/assemble-runtime-env.py",
    "bin/ghcr-login.sh",
    "bin/verify-staging.sh",
    "bin/alb_target_health.py",
    "bin/evidence.py",
    "bin/write-staging-evidence.py",
    "bin/staging-deploy-evidence.schema.json",
    "bin/log_redaction.py",
    "manifest/release-manifest.json",
    "bundle-meta.json",
)

ROLLBACK_USER_DATA_FORBIDDEN = (
    "bin/dealbrain-staging-rollback.sh",
    "bin/rollback_evidence.py",
    "bin/write-staging-rollback-evidence.py",
    "bin/prior_staging_evidence.py",
    "bin/verify_host_rollback_tooling.py",
    "bin/resolve-rollback-migration.py",
    "bin/staging-rollback-evidence.schema.json",
)

SAFEEXTRACT_HARDENING_MARKERS = (
    "_is_unsupported_filter_typeerror",
    "unexpected keyword argument",
    'filter="data"',
    "setuid/setgid/sticky mode rejected",
    "absolute path rejected",
    'name[1:3] in (":/", ":\\\\"):',
    "path traversal rejected",
    "symlink/hardlink rejected",
    "special file rejected",
    "duplicate archive member",
    "extract path escaped destination",
)

BUNDLE_ROLLBACK_MEMBERS = (
    "bin/dealbrain-staging-rollback.sh",
    "bin/resolve-rollback-migration.py",
    "bin/write-staging-rollback-evidence.py",
    "bin/staging-rollback-evidence.schema.json",
    "bin/rollback_evidence.py",
    "bin/prior_staging_evidence.py",
    "bin/verify_host_rollback_tooling.py",
    "bin/verify_staging_bundle.py",
    "bin/deploy_atomicity.sh",
    "bin/evidence.py",
)

# Rejected live-byte pin SHA (must not be treated as bootstrap authority).
_REJECTED_LIVE_BYTE_PIN_SHA256 = "e8cabf7e9693726825f3909ab4a65c73713bb95f65d6c108abfde48b6d8e912a"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safeextract_block() -> str:
    text = _read(USER_DATA)
    start = text.index("<< 'SAFEEXTRACT'")
    end = text.index("\nSAFEEXTRACT\n", start)
    return text[start:end]


def _extract_safeextract_required_members() -> tuple[str, ...]:
    safe = _safeextract_block()
    marker = "REQUIRED_MEMBERS = (\n"
    start = safe.index(marker) + len(marker)
    end = safe.index("\n)", start)
    return tuple(re.findall(r'"([^"]+)"', safe[start:end]))


def _built_manifest() -> dict:
    return create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="30741970067",
        test_workflow_run_id="222",
        created_at="2026-08-02T09:32:46Z",
        release_id=BASELINE_RELEASE,
    )


def test_approved_safeextract_hardening_present_in_user_data() -> None:
    safe = _safeextract_block()
    for marker in SAFEEXTRACT_HARDENING_MARKERS:
        assert marker in safe, f"missing approved hardening marker: {marker}"
    assert "extractall(" not in safe


def test_bootstrap_required_members_match_pre_pr_baseline_only() -> None:
    members = _extract_safeextract_required_members()
    assert members == BOOTSTRAP_BASELINE_REQUIRED_MEMBERS
    for rel in ROLLBACK_USER_DATA_FORBIDDEN:
        assert rel not in members
    # Only rollback-specific members were removed vs full canonical schema-2 set.
    assert frozenset(REQUIRED_MEMBERS) - frozenset(members) == frozenset(
        ROLLBACK_USER_DATA_FORBIDDEN
    )


def test_rollback_tooling_absent_from_staging_user_data_required_members() -> None:
    safe = _safeextract_block()
    for rel in ROLLBACK_USER_DATA_FORBIDDEN:
        assert f'"{rel}"' not in safe
    # Unrelated baseline deploy/evidence/ALB helpers must remain.
    for name in (
        "deploy_atomicity.sh",
        "alb_target_health.py",
        "write-staging-evidence.py",
        "staging-deploy-evidence.schema.json",
        "log_redaction.py",
        "_is_unsupported_filter_typeerror",
    ):
        assert name in safe


def test_live_ec2_user_data_sha_is_not_sole_authority() -> None:
    """Behavioral contract + baseline members are authority; live pin is rejected."""
    digest = hashlib.sha256(USER_DATA.read_bytes()).hexdigest()
    assert digest != _REJECTED_LIVE_BYTE_PIN_SHA256
    # Source checksum may exist as a secondary signal only after contract checks.
    assert _extract_safeextract_required_members() == BOOTSTRAP_BASELINE_REQUIRED_MEMBERS
    assert "_is_unsupported_filter_typeerror" in _safeextract_block()


def test_no_ec2_lifecycle_ignore_user_data_base64() -> None:
    ec2 = _read(EC2_MAIN)
    staging = _read(STAGING_MAIN)
    assert "ignore_changes = [ami]" in ec2
    assert "user_data_base64" not in ec2.split("lifecycle")[1].split("}")[0]
    assert "ignore_changes = [user_data_base64]" not in ec2
    assert "ignore_changes = [user_data_base64]" not in staging
    assert 'ignore_changes = ["user_data_base64"]' not in ec2 + staging


def test_bundle_includes_all_rollback_host_tooling(tmp_path: Path) -> None:
    man_path = tmp_path / "release-manifest.json"
    man_path.write_text(json.dumps(_built_manifest()), encoding="utf-8")
    out = tmp_path / "out"
    tarball, checksum_path, meta = build_bundle(manifest_path=man_path, out_dir=out)
    assert meta["schema_version"] == CURRENT_BUNDLE_SCHEMA_VERSION
    checksum = checksum_path.read_text(encoding="utf-8").split()[0]
    verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    bundled = {dst for _src, dst in INCLUDE_FILES}
    for rel in BUNDLE_ROLLBACK_MEMBERS:
        assert rel in bundled
        assert rel in meta["file_checksums"]
    for rel in HOST_TOOLING_MEMBERS:
        assert rel in meta["file_checksums"]
    for rel in REQUIRED_MEMBERS:
        assert rel in meta["file_checksums"]
    for rel in ROLLBACK_USER_DATA_FORBIDDEN:
        assert rel in meta["file_checksums"]


def test_deploy_staging_installs_rollback_tooling_and_writes_capability() -> None:
    deploy = _read(DEPLOY_SH)
    for name in (
        "dealbrain-staging-rollback.sh",
        "write-staging-rollback-evidence.py",
        "rollback_evidence.py",
        "staging-rollback-evidence.schema.json",
        "prior_staging_evidence.py",
        "verify_host_rollback_tooling.py",
        "resolve-rollback-migration.py",
        "verify_staging_bundle.py",
    ):
        assert f"${{RELEASE_DIR}}/bin/{name}" in deploy
        assert f"${{ROOT}}/bin/{name}" in deploy
    install_idx = deploy.index("dealbrain-staging-rollback.sh")
    write_idx = deploy.index("--write")
    assert install_idx < write_idx
    assert "staging-host-tooling.json" in deploy
    assert '--expected-tooling-version "25b.5"' in deploy
    assert "failed to write staging host tooling capability" in deploy


def test_deploy_install_paths_use_install_with_modes() -> None:
    deploy = _read(DEPLOY_SH)
    assert "install -o root -g root -m 0755" in deploy
    assert "install -o root -g root -m 0644" in deploy
    schema_block_start = deploy.index("staging-rollback-evidence.schema.json")
    nearby = deploy[max(0, schema_block_start - 120) : schema_block_start]
    assert "-m 0644" in nearby


def test_rollback_preflight_rejects_missing_tooling(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    with pytest.raises(HostToolingError, match="capability missing"):
        verify_host_rollback_tooling(bin_dir / "staging-host-tooling.json", bin_dir)
    host = _read(ROLLBACK_SH)
    assert "verify_host_rollback_tooling.py missing on host" in host
    assert host.index("verify_host_rollback_tooling.py") < host.index("acquired flock")


def test_rollback_preflight_rejects_outdated_and_checksum_mismatch(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in REQUIRED_TOOLING_FILES:
        (bin_dir / name).write_text(f"content-{name}\n", encoding="utf-8")
    cap_path = bin_dir / "staging-host-tooling.json"
    write_host_tooling_capability(
        cap_path,
        build_host_tooling_capability(bin_dir, tooling_version="25b.4"),
    )
    with pytest.raises(HostToolingError, match="outdated|unexpected"):
        verify_host_rollback_tooling(cap_path, bin_dir)
    write_host_tooling_capability(cap_path, build_host_tooling_capability(bin_dir))
    (bin_dir / "dealbrain-staging-rollback.sh").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(HostToolingError, match="checksum mismatch"):
        verify_host_rollback_tooling(cap_path, bin_dir)


def test_capability_written_only_via_verified_install_contract() -> None:
    """Deploy writes capability with --write after install; rollback never fabricates it."""
    deploy = _read(DEPLOY_SH)
    rollback = _read(ROLLBACK_SH)
    assert "--write" in deploy
    assert "staging-host-tooling.json" in deploy
    assert "--write" not in rollback
    assert "verify_host_rollback_tooling.py" in rollback


def test_runbook_declares_combined_apply_gate() -> None:
    text = _read(RUNBOOK)
    assert "Host tooling delivery model" in text
    assert "Combined infrastructure apply gate" in text
    assert "user_data_base64" in text
    assert "SAFEEXTRACT" in text
    assert "SSM/IAM-only" in text
    assert re.search(r"\*\*not\*\*\s*SSM/IAM-only", text) is not None
    assert "independent" in text.lower() and "audit" in text.lower()
    assert "Deploy Staging" in text
    assert "approved Terraform apply" in text
    # Must not claim live-byte pinning hides EC2 from the plan.
    assert "stays pinned to the currently applied host bootstrap bytes" not in text


def test_production_untouched_by_user_data_isolation() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").exists()
    prod_main = PROD_TF / "main.tf"
    assert prod_main.is_file()
    prod = _read(prod_main)
    assert "user_data" not in prod
    assert "user_data_base64" not in prod
    assert "ssm_rollback" not in prod
    for path in PROD_TF.rglob("*.tf"):
        text = path.read_text(encoding="utf-8")
        assert "dealbrain-staging-rollback" not in text
        assert "staging-host-tooling" not in text
        assert "ssm_rollback" not in text


def test_bash_syntax_user_data_and_host_scripts() -> None:
    for path in (USER_DATA, DEPLOY_SH, ROLLBACK_SH):
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"{path}: {proc.stderr}"
