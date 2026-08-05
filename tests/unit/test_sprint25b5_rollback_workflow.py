"""Sprint 25b.5 — staging rollback workflow, atomicity, evidence, retention."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from scripts.deploy.build_staging_bundle import build_bundle
from scripts.deploy.evidence import EvidenceError, create_evidence
from scripts.deploy.rollback_evidence import (
    compute_rollback_evidence_sha256,
    create_rollback_evidence,
    read_strict_rollback_evidence_sidecar_sha256,
    validate_rollback_evidence,
    validate_rollback_evidence_bindings,
    verify_rollback_evidence_sidecar,
    write_rollback_evidence,
)
from scripts.deploy.validate_rollback_eligibility import (
    RollbackEligibilityError,
    assert_no_mutable_tag_authority,
    validate_database_compatibility,
    validate_prior_staging_approval,
    validate_staging_identity,
    validate_target_differs_from_current,
    validate_target_manifest_authority,
)
from scripts.deploy.verify_staging_bundle import REQUIRED_MEMBERS, verify_bundle
from scripts.release.manifest import compute_manifest_sha256, create_built_manifest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
ROLLBACK_WF = WORKFLOWS / "rollback.yml"
DEPLOY_WF = WORKFLOWS / "deploy-staging.yml"
HOST_SCRIPTS = ROOT / "scripts/deploy/host"
ROLLBACK_SH = HOST_SCRIPTS / "dealbrain-staging-rollback.sh"
ATOMICITY_SH = HOST_SCRIPTS / "deploy_atomicity.sh"
DEPLOY_SH = HOST_SCRIPTS / "dealbrain-staging-deploy.sh"
SSM_ROLLBACK = ROOT / "infra/terraform/modules/ssm_rollback_document"
STAGING_TF = ROOT / "infra/terraform/environments/staging"
PROD_TF = ROOT / "infra/terraform/environments/production"
RUNBOOK = ROOT / "docs/runbooks/STAGING_ROLLBACK.md"

SAMPLE_SHA = "83bfc6c57fd99a43445b6edaddcaf863fabf3473"
SAMPLE_DIGEST = "sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f"
OTHER_SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_DIGEST = "sha256:" + ("b" * 64)
SAMPLE_REPO = "ghcr.io/example-org/dealbrain"
CANON_REV = "d4e5f6a7b8c9"
BASELINE_RELEASE = f"rel-20260802T093246Z-{SAMPLE_SHA[:12]}"
SECOND_RELEASE = f"rel-20260802T120000Z-{OTHER_SHA[:12]}"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing: {path}"
    return path.read_text(encoding="utf-8")


def _built_manifest(**overrides: object) -> dict:
    manifest = create_built_manifest(
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        build_workflow_run_id="30741970067",
        test_workflow_run_id="222",
        created_at="2026-08-02T09:32:46Z",
        release_id=BASELINE_RELEASE,
    )
    if overrides:
        manifest = copy.deepcopy(manifest)
        manifest.update(overrides)
        if "manifest_sha256" not in overrides:
            manifest["manifest_sha256"] = compute_manifest_sha256(manifest)
    return manifest


def _prior_deploy_evidence(**overrides: object) -> dict:
    payload = create_evidence(
        release_id=BASELINE_RELEASE,
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="11",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-11-staging",
        ec2_instance_id="i-0123456789abcdef0",
        ssm_command_id="11111111-1111-1111-1111-111111111111",
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-08-02T09:00:00Z",
        deployment_started_at="2026-08-02T09:30:00Z",
        deployment_finished_at="2026-08-02T09:35:00Z",
        deployment_duration_seconds=300,
        final_status="staging_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        from scripts.deploy.evidence import compute_evidence_sha256

        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def _ok_rollback_evidence(**overrides: object) -> dict:
    payload = create_rollback_evidence(
        rollback_workflow_run_id="555",
        aws_account_id="123456789012",
        aws_region="us-east-1",
        assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
        role_session_name="gha-555-staging-rollback",
        ec2_instance_id="i-0123456789abcdef0",
        ssm_command_id="22222222-2222-2222-2222-222222222222",
        rollback_started_at="2026-08-02T13:00:00Z",
        rollback_finished_at="2026-08-02T13:05:00Z",
        rollback_duration_seconds=300,
        source_release_id=SECOND_RELEASE,
        source_image_digest=OTHER_DIGEST,
        target_release_id=BASELINE_RELEASE,
        target_image_digest=SAMPLE_DIGEST,
        target_git_sha=SAMPLE_SHA,
        target_image_repository=SAMPLE_REPO,
        target_manifest_sha256="a" * 64,
        migration_revision_before=CANON_REV,
        migration_revision_after=CANON_REV,
        target_migration_revision_authority="deploy_version",
        current_pointer_before=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
        current_pointer_after=f"/opt/dealbrain/releases/{BASELINE_RELEASE}",
        previous_pointer_before=f"/opt/dealbrain/releases/{BASELINE_RELEASE}",
        previous_pointer_after=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
        running_digest_after=SAMPLE_DIGEST,
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        final_status="rollback_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_rollback_evidence_sha256(payload)
    return payload


# ---------------------------------------------------------------------------
# Workflow contract (1–9, 34)
# ---------------------------------------------------------------------------


def test_rollback_workflow_valid_yaml() -> None:
    data = yaml.safe_load(_read(ROLLBACK_WF))
    assert data["name"] == "Rollback Staging"
    # PyYAML 1.1 treats bare `on` as boolean True.
    on_block = data.get("on", data.get(True))
    assert on_block is not None
    assert "workflow_dispatch" in on_block


def test_rollback_workflow_manual_dispatch_only() -> None:
    text = _read(ROLLBACK_WF)
    data = yaml.safe_load(text)
    on_block = data.get("on", data.get(True))
    assert list(on_block.keys()) == ["workflow_dispatch"]
    assert "pull_request:" not in text
    assert "workflow_run:" not in text
    assert not re.search(r"(?m)^  push:", text)


def test_rollback_workflow_requires_main() -> None:
    text = _read(ROLLBACK_WF)
    assert "refs/heads/main" in text
    assert "Rollback Staging must run from refs/heads/main" in text


def test_rollback_workflow_environment_staging() -> None:
    text = _read(ROLLBACK_WF)
    assert re.search(r"(?m)^\s+environment:\s+staging\s*$", text)
    assert "environment: production" not in text


def test_rollback_workflow_rejects_forks() -> None:
    text = _read(ROLLBACK_WF)
    assert "github.event.repository.fork == false" in text
    assert "Fork repositories cannot rollback staging" in text


def test_rollback_workflow_uses_oidc() -> None:
    text = _read(ROLLBACK_WF)
    assert (
        "aws-actions/configure-aws-credentials@e6de054238d6b7531b4efff3b6587d9aade6a06c"
        in text
    )
    assert "id-token: write" in text
    assert "role-to-assume: ${{ vars.AWS_ROLE_ARN }}" in text


def test_rollback_workflow_no_static_aws_credentials() -> None:
    text = _read(ROLLBACK_WF)
    assert "AWS_ACCESS_KEY_ID" not in text
    assert "AWS_SECRET_ACCESS_KEY" not in text
    assert "secrets.AWS" not in text


def test_rollback_workflow_does_not_reference_production() -> None:
    text = _read(ROLLBACK_WF)
    # Negative assertions / grep -qv only.
    assert "environment: production" not in text
    assert "dealbrain-production-gha-deploy" in text  # rejected via grep -qv
    assert "grep -qv 'dealbrain-production-gha-deploy'" in text
    assert "grep -qv 'production'" in text
    assert "AWS_ROLE_ARN_PRODUCTION" not in text
    assert "deploy-production" not in text


def test_concurrent_deploy_and_rollback_share_group() -> None:
    rollback = _read(ROLLBACK_WF)
    deploy = _read(DEPLOY_WF)
    assert "group: staging-release-mutation" in rollback
    assert "group: staging-release-mutation" in deploy
    assert "cancel-in-progress: false" in rollback
    assert "cancel-in-progress: false" in deploy
    assert "staging-deploy.lock" in _read(ROLLBACK_SH)
    assert "staging-deploy.lock" in _read(DEPLOY_SH)


def test_production_remains_untouched() -> None:
    assert not (WORKFLOWS / "deploy-production.yml").is_file()
    assert not (PROD_TF / "rollback").exists()
    rollback_tf = _read(SSM_ROLLBACK / "variables.tf")
    assert 'var.environment == "staging"' in rollback_tf
    staging_main = _read(STAGING_TF / "main.tf")
    assert "ssm_rollback_document" in staging_main
    assert "DealBrain-StagingRollback" in _read(SSM_ROLLBACK / "variables.tf")
    assert "dealbrain-staging-rollback.sh" in _read(SSM_ROLLBACK / "main.tf")
    # No production terraform references rollback module.
    for path in PROD_TF.rglob("*.tf"):
        assert "ssm_rollback" not in path.read_text(encoding="utf-8")
        assert "DealBrain-StagingRollback" not in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Eligibility / authority (10–19, 32)
# ---------------------------------------------------------------------------


def test_target_manifest_must_exist_and_match(tmp_path: Path) -> None:
    manifest = _built_manifest()
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    validate_target_manifest_authority(
        loaded,
        expected_build_run_id="30741970067",
        expected_release_id=BASELINE_RELEASE,
        expected_image_digest=SAMPLE_DIGEST,
        expected_image_repository=SAMPLE_REPO,
        expected_manifest_sha256=manifest["manifest_sha256"],
    )
    with pytest.raises(RollbackEligibilityError, match="release_id mismatch"):
        validate_target_manifest_authority(
            loaded,
            expected_build_run_id="30741970067",
            expected_release_id=SECOND_RELEASE,
            expected_image_repository=SAMPLE_REPO,
        )


def test_target_digest_must_match_manifest() -> None:
    manifest = _built_manifest()
    with pytest.raises(RollbackEligibilityError, match="digest mismatch"):
        validate_target_manifest_authority(
            manifest,
            expected_build_run_id="30741970067",
            expected_image_digest=OTHER_DIGEST,
            expected_image_repository=SAMPLE_REPO,
        )


def test_mutable_tags_cannot_become_authority() -> None:
    with pytest.raises(RollbackEligibilityError):
        assert_no_mutable_tag_authority(f"{SAMPLE_REPO}:latest")
    with pytest.raises(RollbackEligibilityError):
        assert_no_mutable_tag_authority(SAMPLE_REPO, f"{SAMPLE_REPO}:staging")
    assert_no_mutable_tag_authority(SAMPLE_REPO, f"{SAMPLE_REPO}@{SAMPLE_DIGEST}")


def test_wrong_aws_account_region_instance_fail() -> None:
    with pytest.raises(RollbackEligibilityError, match="wrong AWS account"):
        validate_staging_identity(
            aws_account_id="999999999999",
            aws_region="us-east-1",
            expected_account_id="123456789012",
            expected_region="us-east-1",
            ec2_instance_id="i-0123456789abcdef0",
            bundle_bucket="dealbrain-staging-release-artifacts-123456789012",
            image_repository=SAMPLE_REPO,
            expected_image_repository=SAMPLE_REPO,
        )
    with pytest.raises(RollbackEligibilityError, match="wrong AWS region"):
        validate_staging_identity(
            aws_account_id="123456789012",
            aws_region="us-west-2",
            expected_account_id="123456789012",
            expected_region="us-east-1",
            ec2_instance_id="i-0123456789abcdef0",
            bundle_bucket="dealbrain-staging-release-artifacts-123456789012",
            image_repository=SAMPLE_REPO,
            expected_image_repository=SAMPLE_REPO,
        )
    with pytest.raises(RollbackEligibilityError, match="invalid ec2_instance_id"):
        validate_staging_identity(
            aws_account_id="123456789012",
            aws_region="us-east-1",
            expected_account_id="123456789012",
            expected_region="us-east-1",
            ec2_instance_id="i-bad",
            bundle_bucket="dealbrain-staging-release-artifacts-123456789012",
            image_repository=SAMPLE_REPO,
            expected_image_repository=SAMPLE_REPO,
        )


def test_missing_target_release_fails_in_workflow() -> None:
    text = _read(ROLLBACK_WF)
    assert "missing target release object" in text
    assert "head-object" in text
    assert "bundle.tar.gz" in text


def test_target_equal_to_current_fails() -> None:
    with pytest.raises(RollbackEligibilityError, match="equals currently active"):
        validate_target_differs_from_current(
            target_release_id=BASELINE_RELEASE,
            target_image_digest=SAMPLE_DIGEST,
            current_release_id=BASELINE_RELEASE,
            current_image_digest=SAMPLE_DIGEST,
        )
    host = _read(ROLLBACK_SH)
    assert "target_equals_current" in host


def test_database_incompatibility_fails_before_api_replacement() -> None:
    with pytest.raises(RollbackEligibilityError, match="database_incompatible"):
        validate_database_compatibility(
            current_db_revision="newerrev001",
            target_recorded_revision=CANON_REV,
        )
    validate_database_compatibility(
        current_db_revision=CANON_REV,
        target_recorded_revision=CANON_REV,
    )
    host = _read(ROLLBACK_SH)
    assert "database_incompatible" in host
    # Compatibility check appears before the primary API replacement (not restore helper).
    marker = "# 5. Database compatibility"
    replacement = "# 6–11. Replace API with target"
    assert host.index(marker) < host.index(replacement)
    assert "alembic downgrade" not in host.lower()


def test_prior_staging_approval_required() -> None:
    validate_prior_staging_approval(_prior_deploy_evidence())
    with pytest.raises(RollbackEligibilityError, match="not previously deployed"):
        validate_prior_staging_approval(_prior_deploy_evidence(final_status="failed"))


def test_build_image_15_can_be_retained_as_rollback_target() -> None:
    text = _read(RUNBOOK)
    assert "30741970067" in text
    assert "rel-20260802T093246Z-83bfc6c57fd9" in text
    assert SAMPLE_DIGEST in text
    assert "HISTORICAL BUILD IMAGE #15 RECONSTRUCTION IS SAFE" in text
    assert "schema version `1`" in text or "schema version 1" in text.lower()
    deploy = _read(DEPLOY_SH)
    assert "previous" in deploy
    assert "retained" in deploy
    assert "staging-host-tooling.json" in deploy


# ---------------------------------------------------------------------------
# Host rollback / atomicity / evidence (20–31, 33)
# ---------------------------------------------------------------------------


def test_host_rollback_health_and_digest_gates() -> None:
    host = _read(ROLLBACK_SH)
    assert "running_digest_mismatch" in host
    assert "localhost_live_failed" in host
    assert "localhost_ready_failed" in host
    assert "alb_health_failed" in host
    assert "verify-staging.sh" in host
    assert "/live" in _read(HOST_SCRIPTS / "verify-staging.sh")


def test_pointer_update_only_after_health_success() -> None:
    host = _read(ROLLBACK_SH)
    live_idx = host.index('LOCAL_LIVE" == "true"')
    commit_idx = host.index("commit_release_pointer")
    assert live_idx < commit_idx
    atom = _read(ATOMICITY_SH)
    assert "commit_current_and_previous_pointers" in atom
    assert "atomic_point_previous" in atom


def test_failed_rollback_restores_or_preserves_current() -> None:
    host = _read(ROLLBACK_SH)
    assert "restore_source_api" in host
    assert "API_REPLACEMENT_OCCURRED" in host
    assert "never leave current pointing" in host.lower() or "restored source API" in host
    # Pre-replacement failures do not call restore (API untouched).
    assert "target_equals_current" in host
    assert "database_incompatible" in host


def test_successful_rollback_produces_rollback_ok() -> None:
    payload = _ok_rollback_evidence()
    validate_rollback_evidence(payload)
    assert payload["final_status"] == "rollback_ok"
    host = _read(ROLLBACK_SH)
    assert 'FINAL_STATUS="rollback_ok"' in host


def test_failed_rollback_cannot_produce_rollback_ok() -> None:
    with pytest.raises(Exception, match="failed status requires non-empty failure_reason"):
        create_rollback_evidence(
            rollback_workflow_run_id="555",
            aws_account_id="123456789012",
            aws_region="us-east-1",
            assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
            role_session_name="gha-555-staging-rollback",
            ec2_instance_id="i-0123456789abcdef0",
            ssm_command_id="22222222-2222-2222-2222-222222222222",
            rollback_started_at="2026-08-02T13:00:00Z",
            rollback_finished_at="2026-08-02T13:05:00Z",
            rollback_duration_seconds=300,
            source_release_id=SECOND_RELEASE,
            source_image_digest=OTHER_DIGEST,
            target_release_id=BASELINE_RELEASE,
            target_image_digest=SAMPLE_DIGEST,
            target_git_sha=SAMPLE_SHA,
            target_image_repository=SAMPLE_REPO,
            target_manifest_sha256="a" * 64,
            migration_revision_before=CANON_REV,
            migration_revision_after=CANON_REV,
            target_migration_revision_authority=None,
            current_pointer_before=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
            current_pointer_after=f"/opt/dealbrain/releases/{BASELINE_RELEASE}",
            previous_pointer_before=f"/opt/dealbrain/releases/{BASELINE_RELEASE}",
            previous_pointer_after=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
            running_digest_after=SAMPLE_DIGEST,
            localhost_live=False,
            localhost_ready=False,
            alb_target_healthy=False,
            final_status="failed",
            failure_reason=None,  # invalid: failed needs reason
        )
    # Cannot claim rollback_ok when health gates are false.
    with pytest.raises(Exception, match="rollback_ok requires localhost_live"):
        create_rollback_evidence(
            rollback_workflow_run_id="555",
            aws_account_id="123456789012",
            aws_region="us-east-1",
            assumed_role_arn="arn:aws:iam::123456789012:role/dealbrain-staging-gha-deploy",
            role_session_name="gha-555-staging-rollback",
            ec2_instance_id="i-0123456789abcdef0",
            ssm_command_id="22222222-2222-2222-2222-222222222222",
            rollback_started_at="2026-08-02T13:00:00Z",
            rollback_finished_at="2026-08-02T13:05:00Z",
            rollback_duration_seconds=300,
            source_release_id=SECOND_RELEASE,
            source_image_digest=OTHER_DIGEST,
            target_release_id=BASELINE_RELEASE,
            target_image_digest=SAMPLE_DIGEST,
            target_git_sha=SAMPLE_SHA,
            target_image_repository=SAMPLE_REPO,
            target_manifest_sha256="a" * 64,
            migration_revision_before=CANON_REV,
            migration_revision_after=CANON_REV,
            target_migration_revision_authority="deploy_version",
            current_pointer_before=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
            current_pointer_after=f"/opt/dealbrain/releases/{SECOND_RELEASE}",
            previous_pointer_before=None,
            previous_pointer_after=None,
            running_digest_after=OTHER_DIGEST,
            localhost_live=False,
            localhost_ready=False,
            alb_target_healthy=False,
            final_status="rollback_ok",
            failure_reason=None,
        )
    host = _read(ROLLBACK_SH)
    assert 'FINAL_STATUS="failed"' in host
    assert "Refusing to fabricate rollback_ok" in _read(ROLLBACK_WF)


def test_evidence_checksum_and_binding_mismatches_fail() -> None:
    payload = _ok_rollback_evidence()
    payload["evidence_sha256"] = "0" * 64
    with pytest.raises(Exception, match="evidence_sha256 mismatch"):
        validate_rollback_evidence(payload)

    good = _ok_rollback_evidence()
    with pytest.raises(Exception, match="rollback_workflow_run_id"):
        validate_rollback_evidence_bindings(
            good,
            target_release_id=BASELINE_RELEASE,
            target_git_sha=SAMPLE_SHA,
            target_image_digest=SAMPLE_DIGEST,
            target_image_repository=SAMPLE_REPO,
            target_manifest_sha256="a" * 64,
            rollback_workflow_run_id="999999",
            aws_account_id="123456789012",
            aws_region="us-east-1",
            ec2_instance_id="i-0123456789abcdef0",
            ssm_command_id="22222222-2222-2222-2222-222222222222",
        )
    with pytest.raises(Exception, match="ssm_command_id"):
        validate_rollback_evidence_bindings(
            good,
            target_release_id=BASELINE_RELEASE,
            target_git_sha=SAMPLE_SHA,
            target_image_digest=SAMPLE_DIGEST,
            target_image_repository=SAMPLE_REPO,
            target_manifest_sha256="a" * 64,
            rollback_workflow_run_id="555",
            aws_account_id="123456789012",
            aws_region="us-east-1",
            ec2_instance_id="i-0123456789abcdef0",
            ssm_command_id="33333333-3333-3333-3333-333333333333",
        )


def _rollback_evidence_step(text: str) -> str:
    marker = "Collect and validate authoritative host rollback evidence"
    assert marker in text
    after = text.split(marker, 1)[1]
    next_step = re.search(r"\n      - name:", after)
    assert next_step is not None
    return after[: next_step.start()]


def test_rollback_evidence_sidecar_is_mandatory() -> None:
    text = _read(ROLLBACK_WF)
    step = _rollback_evidence_step(text)
    assert "${EVIDENCE_KEY}.sha256" in step
    assert "verify_rollback_evidence_sidecar" in step
    assert "checksum sidecar missing or download failed" in step
    # Must not treat the sidecar as optional via head-object gating.
    assert "if aws s3api head-object" not in step
    assert "awk '{print $1}'" not in step
    # Download is unconditional fail-closed (if ! aws s3 cp ...sha256).
    assert "if ! aws s3 cp" in step
    assert step.index("if ! aws s3 cp") < step.index("verify_rollback_evidence_sidecar")


def test_evidence_artifact_uploads_only_after_validation() -> None:
    text = _read(ROLLBACK_WF)
    step = _rollback_evidence_step(text)
    sidecar_idx = step.index("verify_rollback_evidence_sidecar")
    semantic_idx = step.index("write_gha_staging_rollback_evidence")
    validate_idx = step.index("validate_staging_rollback_evidence")
    artifact_idx = text.index("Upload staging rollback evidence GitHub artifact")
    collect_idx = text.index("Collect and validate authoritative host rollback evidence")
    assert sidecar_idx < semantic_idx < validate_idx
    assert collect_idx < artifact_idx
    assert text.index("verify_rollback_evidence_sidecar") < artifact_idx
    assert text.index("validate_staging_rollback_evidence") < artifact_idx
    assert "if-no-files-found: error" in text


def test_missing_rollback_evidence_sidecar_fails(tmp_path: Path) -> None:
    evidence = tmp_path / "staging-rollback-evidence.json"
    write_rollback_evidence(evidence, _ok_rollback_evidence())
    evidence.with_suffix(evidence.suffix + ".sha256").unlink()
    with pytest.raises(EvidenceError, match="missing rollback evidence checksum sidecar"):
        verify_rollback_evidence_sidecar(evidence)


def test_malformed_rollback_evidence_sidecar_fails(tmp_path: Path) -> None:
    evidence = tmp_path / "staging-rollback-evidence.json"
    write_rollback_evidence(evidence, _ok_rollback_evidence())
    sidecar = evidence.with_suffix(evidence.suffix + ".sha256")
    cases = [
        (b"", "empty"),
        (b"\n", "empty after newline"),
        (("DEADBEEF" + ("0" * 56) + "\n").encode("ascii"), "canonical lowercase"),
        ((("a" * 64) + "  evidence.json\n").encode("ascii"), "whitespace"),
        ((("a" * 64) + "\n" + ("b" * 64) + "\n").encode("ascii"), "single line"),
        (b" not-a-hash \n", "whitespace|canonical lowercase"),
        ((("a" * 63) + "\n").encode("ascii"), "canonical lowercase"),
    ]
    for body, match in cases:
        sidecar.write_bytes(body)
        with pytest.raises(EvidenceError, match=match):
            read_strict_rollback_evidence_sidecar_sha256(sidecar)


def test_mismatched_rollback_evidence_sidecar_fails(tmp_path: Path) -> None:
    evidence = tmp_path / "staging-rollback-evidence.json"
    payload = _ok_rollback_evidence()
    write_rollback_evidence(evidence, payload)
    sidecar = evidence.with_suffix(evidence.suffix + ".sha256")
    sidecar.write_text(("0" * 64) + "\n", encoding="utf-8")
    with pytest.raises(EvidenceError, match="checksum sidecar mismatch"):
        verify_rollback_evidence_sidecar(evidence)


def test_valid_rollback_evidence_sidecar_accepts_lf_or_crlf(tmp_path: Path) -> None:
    evidence = tmp_path / "staging-rollback-evidence.json"
    payload = _ok_rollback_evidence()
    write_rollback_evidence(evidence, payload)
    sidecar = evidence.with_suffix(evidence.suffix + ".sha256")
    digest = payload["evidence_sha256"]
    sidecar.write_bytes((digest + "\n").encode("ascii"))
    assert verify_rollback_evidence_sidecar(evidence) == digest
    sidecar.write_bytes((digest + "\r\n").encode("ascii"))
    assert verify_rollback_evidence_sidecar(evidence) == digest
    sidecar.write_bytes(digest.encode("ascii"))
    assert verify_rollback_evidence_sidecar(evidence) == digest


def test_sidecar_download_failure_fails_before_semantic_and_artifact() -> None:
    text = _read(ROLLBACK_WF)
    step = _rollback_evidence_step(text)
    download_fail = step.index("checksum sidecar missing or download failed")
    verify_idx = step.index("verify_rollback_evidence_sidecar")
    semantic_idx = step.index("write_gha_staging_rollback_evidence")
    assert download_fail < verify_idx < semantic_idx
    # Artifact upload is a later workflow step; failure in this step prevents it.
    assert "Upload staging rollback evidence GitHub artifact" not in step


def test_semantic_validation_cannot_run_before_checksum_success() -> None:
    text = _read(ROLLBACK_WF)
    step = _rollback_evidence_step(text)
    assert step.index("verify_rollback_evidence_sidecar") < step.index(
        "validate_staging_rollback_evidence"
    )
    assert step.index("verify_rollback_evidence_sidecar") < step.index(
        "write_gha_staging_rollback_evidence"
    )


def test_verify_rollback_evidence_sidecar_module_cli(tmp_path: Path) -> None:
    evidence = tmp_path / "staging-rollback-evidence.json"
    write_rollback_evidence(evidence, _ok_rollback_evidence())
    sidecar = evidence.with_suffix(evidence.suffix + ".sha256")
    good = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.deploy.verify_rollback_evidence_sidecar",
            "--evidence",
            str(evidence),
            "--sidecar",
            str(sidecar),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert good.returncode == 0, good.stderr
    sidecar.unlink()
    missing = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.deploy.verify_rollback_evidence_sidecar",
            "--evidence",
            str(evidence),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert missing.returncode != 0
    assert "missing" in missing.stderr.lower() or "FAIL" in missing.stderr


def test_second_release_remains_for_forward_recovery() -> None:
    host = _read(ROLLBACK_SH)
    assert "PREVIOUS_AFTER" in host
    assert "previous pointer not on displaced source" in host
    assert "forward recovery" in _read(RUNBOOK).lower() or "previous" in host
    atom = _read(ATOMICITY_SH)
    assert "atomic_point_previous" in atom


def test_bash_syntax_rollback_scripts() -> None:
    for path in (ROLLBACK_SH, ATOMICITY_SH, DEPLOY_SH):
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"{path}: {proc.stderr}"


def test_bundle_includes_rollback_artifacts(tmp_path: Path) -> None:
    manifest = _built_manifest()
    man_path = tmp_path / "release-manifest.json"
    man_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "out"
    tarball, checksum_path, _meta = build_bundle(manifest_path=man_path, out_dir=out)
    checksum = checksum_path.read_text(encoding="utf-8").split()[0]
    verify_bundle(
        tarball,
        expected_checksum=checksum,
        expected_release_id=BASELINE_RELEASE,
        expected_digest=SAMPLE_DIGEST,
    )
    assert "bin/dealbrain-staging-rollback.sh" in REQUIRED_MEMBERS
    assert "bin/rollback_evidence.py" in REQUIRED_MEMBERS
    assert "bin/staging-rollback-evidence.schema.json" in REQUIRED_MEMBERS


def test_pointer_atomicity_shell_harness(tmp_path: Path) -> None:
    """Executable harness: previous+current commit and pre-health non-mutation."""
    root = tmp_path / "opt" / "dealbrain"
    rel_a = root / "releases" / BASELINE_RELEASE
    rel_b = root / "releases" / SECOND_RELEASE
    rel_a.mkdir(parents=True)
    rel_b.mkdir(parents=True)
    (rel_a / "DEPLOY_VERSION").write_text(
        json.dumps(
            {
                "release_id": BASELINE_RELEASE,
                "git_sha": SAMPLE_SHA,
                "image_digest": SAMPLE_DIGEST,
                "deployed_at": "2026-08-02T09:32:46Z",
                "migration_revision": CANON_REV,
            }
        ),
        encoding="utf-8",
    )
    (rel_b / "DEPLOY_VERSION").write_text(
        json.dumps(
            {
                "release_id": SECOND_RELEASE,
                "git_sha": OTHER_SHA,
                "image_digest": OTHER_DIGEST,
                "deployed_at": "2026-08-02T12:00:00Z",
                "migration_revision": CANON_REV,
            }
        ),
        encoding="utf-8",
    )
    script = textwrap.dedent(
        f"""
        set -euo pipefail
        ROOT="{root}"
        RELEASE_DIR="{rel_a}"
        RELEASE_ID="{BASELINE_RELEASE}"
        GIT_SHA="{SAMPLE_SHA}"
        IMAGE_DIGEST="{SAMPLE_DIGEST}"
        PREVIOUS_CURRENT="{rel_b}"
        MIGRATION_AFTER="{CANON_REV}"
        source "{ATOMICITY_SH}"
        # Simulate current on B before rollback commit.
        ln -sfn "{rel_b}" "$ROOT/current"
        # Health not yet done — do not commit yet; only verify helper exists.
        test "$(readlink -f "$ROOT/current")" = "{rel_b}"
        # After health: commit pointers.
        _atomicity_running_api_digest() {{ echo "{SAMPLE_DIGEST}"; }}
        commit_release_pointer
        test "$(readlink -f "$ROOT/current")" = "{rel_a}"
        test "$(readlink -f "$ROOT/previous")" = "{rel_b}"
        echo OK
        """
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "OK" in proc.stdout


def test_gha_refuses_to_fabricate_rollback_ok(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "scripts.deploy.write_gha_staging_rollback_evidence",
            "--evidence",
            str(missing),
            "--target-release-id",
            BASELINE_RELEASE,
            "--target-git-sha",
            SAMPLE_SHA,
            "--target-image-repository",
            SAMPLE_REPO,
            "--target-image-digest",
            SAMPLE_DIGEST,
            "--target-manifest-sha256",
            "a" * 64,
            "--rollback-run-id",
            "555",
            "--aws-account-id",
            "123456789012",
            "--aws-region",
            "us-east-1",
            "--ec2-instance-id",
            "i-0123456789abcdef0",
            "--ssm-command-id",
            "22222222-2222-2222-2222-222222222222",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "refusing to fabricate rollback_ok" in proc.stderr.lower()


def test_runbook_exists_and_is_document_only() -> None:
    text = _read(RUNBOOK)
    assert "Phase 1" in text
    assert "Phase 5" in text
    assert "Do not execute" in text or "document only" in text.lower()
    assert "No production promotion" in text
