"""Production evidence may record the assumed-role ARN as identity metadata.

Regresses Deploy Production run 34909112181 error-path evidence:

  EvidenceError: production environment value forbidden at assumed_role_arn

``PRODUCTION_VALUE_RE`` treats ``production`` as a forbidden token. The live
role ``arn:aws:iam::<account>:role/dealbrain-production-gha-deploy`` is
required schema metadata, not a secret or production.env dump.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from scripts.deploy.production_evidence import (
    FORBIDDEN_FIELD_FRAGMENTS,
    PRODUCTION_TOKEN_ALLOWED_FIELDS,
    PRODUCTION_VALUE_RE,
    REQUIRED_EVIDENCE_KEYS,
    SECRET_VALUE_RE,
    EvidenceError,
    compute_evidence_sha256,
    create_evidence,
    validate_evidence,
)
from scripts.deploy.production_rollback_evidence import (
    create_rollback_evidence,
    validate_rollback_evidence,
)

SAMPLE_SHA = "69451595b92ca387877374e94b5f7ac82de97022"
SAMPLE_DIGEST = "sha256:" + ("a" * 64)
SAMPLE_REPO = "ghcr.io/markbilbao/dealbrain"
SAMPLE_ACCOUNT = "123456789012"
INTENDED_ROLE_ARN = f"arn:aws:iam::{SAMPLE_ACCOUNT}:role/dealbrain-production-gha-deploy"
INTENDED_SESSION = "gha-34909112181-production"


def _valid_failed_evidence(**overrides: object) -> dict[str, Any]:
    payload = create_evidence(
        release_id=f"rel-20260914T230733Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="b" * 64,
        deploy_workflow_run_id="34909112181",
        aws_account_id=SAMPLE_ACCOUNT,
        aws_region="us-east-1",
        assumed_role_arn=INTENDED_ROLE_ARN,
        role_session_name=INTENDED_SESSION,
        ec2_instance_id="i-0e49ddadd4ecc772d",
        ssm_command_id="302fc54a-9541-4c74-bab5-498cd81894a2",
        migration_revision_before=None,
        migration_revision_after=None,
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        smoke_ok=False,
        image_id=None,
        repo_digest=None,
        image_created_at=None,
        deployment_started_at="2026-09-14T23:07:33Z",
        deployment_finished_at="2026-09-14T23:08:33Z",
        deployment_duration_seconds=60,
        final_status="failed",
        failure_reason="migration_failed",
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def _valid_success_evidence(**overrides: object) -> dict[str, Any]:
    payload = create_evidence(
        release_id=f"rel-20260914T230733Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="c" * 64,
        deploy_workflow_run_id="34909112181",
        aws_account_id=SAMPLE_ACCOUNT,
        aws_region="us-east-1",
        assumed_role_arn=INTENDED_ROLE_ARN,
        role_session_name=INTENDED_SESSION,
        ec2_instance_id="i-0e49ddadd4ecc772d",
        ssm_command_id="302fc54a-9541-4c74-bab5-498cd81894a2",
        migration_revision_before="abc123",
        migration_revision_after="def456",
        localhost_live=True,
        localhost_ready=True,
        alb_target_healthy=True,
        smoke_ok=True,
        image_id="sha256:" + ("d" * 64),
        repo_digest=f"{SAMPLE_REPO}@{SAMPLE_DIGEST}",
        image_created_at="2026-09-14T22:00:00Z",
        deployment_started_at="2026-09-14T23:07:33Z",
        deployment_finished_at="2026-09-14T23:12:33Z",
        deployment_duration_seconds=300,
        final_status="production_ok",
        failure_reason=None,
    )
    if overrides:
        payload = copy.deepcopy(payload)
        payload.update(overrides)
        if "evidence_sha256" not in overrides:
            payload["evidence_sha256"] = compute_evidence_sha256(payload)
    return payload


def test_intended_assumed_role_arn_contains_production_token() -> None:
    assert PRODUCTION_VALUE_RE.search(INTENDED_ROLE_ARN)
    assert PRODUCTION_VALUE_RE.search(INTENDED_SESSION)
    assert "assumed_role_arn" in PRODUCTION_TOKEN_ALLOWED_FIELDS
    assert "role_session_name" in PRODUCTION_TOKEN_ALLOWED_FIELDS


def test_failed_evidence_with_intended_assumed_role_arn_validates() -> None:
    payload = _valid_failed_evidence()
    validate_evidence(payload)
    assert payload["assumed_role_arn"] == INTENDED_ROLE_ARN
    assert payload["role_session_name"] == INTENDED_SESSION
    assert payload["final_status"] == "failed"


def test_production_ok_evidence_with_intended_assumed_role_arn_validates() -> None:
    payload = _valid_success_evidence()
    validate_evidence(payload)
    assert payload["assumed_role_arn"] == INTENDED_ROLE_ARN


def test_create_evidence_accepts_live_identity_metadata() -> None:
    payload = create_evidence(
        release_id=f"rel-20260914T230733Z-{SAMPLE_SHA[:12]}",
        git_sha=SAMPLE_SHA,
        image_repository=SAMPLE_REPO,
        image_digest=SAMPLE_DIGEST,
        source_manifest_sha256="e" * 64,
        deploy_workflow_run_id="34909112181",
        aws_account_id=SAMPLE_ACCOUNT,
        aws_region="us-east-1",
        assumed_role_arn=INTENDED_ROLE_ARN,
        role_session_name=INTENDED_SESSION,
        ec2_instance_id="i-0e49ddadd4ecc772d",
        ssm_command_id="302fc54a-9541-4c74-bab5-498cd81894a2",
        migration_revision_before=None,
        migration_revision_after=None,
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        smoke_ok=False,
        image_id=None,
        repo_digest=None,
        image_created_at=None,
        deployment_started_at="2026-09-14T23:07:33Z",
        deployment_finished_at="2026-09-14T23:08:33Z",
        deployment_duration_seconds=60,
        final_status="failed",
        failure_reason="migration_failed",
    )
    assert payload["evidence_sha256"] == compute_evidence_sha256(payload)


def test_production_token_in_non_identity_field_still_rejected() -> None:
    with pytest.raises(EvidenceError, match="production environment value forbidden"):
        validate_evidence(_valid_failed_evidence(failure_reason="leaked production env dump"))


def test_allowlist_is_exact_schema_fields_only() -> None:
    assert (
        frozenset(
            {
                "assumed_role_arn",
                "role_session_name",
                "final_status",
                "evidence_type",
            }
        )
        == PRODUCTION_TOKEN_ALLOWED_FIELDS
    )
    assert "role" not in FORBIDDEN_FIELD_FRAGMENTS
    # Arbitrary keys containing "role" or "arn" are not exempt.
    with pytest.raises(EvidenceError, match="production environment value forbidden"):
        validate_evidence(_valid_failed_evidence(aws_region="us-production-1"))


def test_secret_like_field_names_still_rejected() -> None:
    for key, value in (
        ("aws_access_key_id", "AKIAIOSFODNN7EXAMPLE"),
        ("secret_access_key", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
        ("session_token", "FwoGZXIvYXdzEH0A"),
        ("api_token", "tok_example_not_real"),
        ("api_key", "re_example_not_real"),
        ("password", "hunter2"),
        ("database_url", "postgresql://u:p@h/db"),
    ):
        payload = _valid_failed_evidence()
        payload[key] = value
        payload["evidence_sha256"] = compute_evidence_sha256(payload)
        with pytest.raises(EvidenceError, match="secret-like"):
            validate_evidence(payload)


def test_secret_bearing_values_still_rejected() -> None:
    cases = (
        "postgresql+asyncpg://dealbrain:secret@db/dealbrain",
        "DATABASE_URL=postgresql://dealbrain:secret@db/dealbrain",
        "password=hunter2",
        "api_key=re_example_not_real",
        "access_key=AKIAexample",
        "token=session-token-value",
        "secret=production.env-value",
    )
    for value in cases:
        assert SECRET_VALUE_RE.search(value)
        with pytest.raises(EvidenceError, match="secret-bearing"):
            validate_evidence(_valid_failed_evidence(failure_reason=value))


def test_assumed_role_arn_still_rejects_embedded_secrets() -> None:
    with pytest.raises(EvidenceError, match="secret-bearing"):
        validate_evidence(
            _valid_failed_evidence(
                assumed_role_arn=f"{INTENDED_ROLE_ARN}?password=hunter2",
            )
        )
    with pytest.raises(EvidenceError, match="secret-bearing"):
        validate_evidence(
            _valid_failed_evidence(
                assumed_role_arn=f"{INTENDED_ROLE_ARN} access_key=AKIAexample",
            )
        )


def test_schema_validation_still_enforced() -> None:
    with pytest.raises(EvidenceError, match="additional properties|schema"):
        validate_evidence(_valid_failed_evidence(extra_note="x"))
    payload = _valid_failed_evidence()
    del payload["aws_account_id"]
    with pytest.raises(EvidenceError, match="missing required|schema"):
        validate_evidence(payload)
    with pytest.raises(EvidenceError, match="pattern|invalid git_sha"):
        validate_evidence(_valid_failed_evidence(git_sha="not-a-sha"))
    with pytest.raises(EvidenceError, match="enum|invalid final_status"):
        validate_evidence(_valid_failed_evidence(final_status="ok"))
    for key in REQUIRED_EVIDENCE_KEYS:
        missing = _valid_failed_evidence()
        del missing[key]
        with pytest.raises(EvidenceError):
            validate_evidence(missing)


def test_rollback_evidence_accepts_intended_assumed_role_arn() -> None:
    payload = create_rollback_evidence(
        rollback_workflow_run_id="34909112181",
        aws_account_id=SAMPLE_ACCOUNT,
        aws_region="us-east-1",
        assumed_role_arn=INTENDED_ROLE_ARN,
        role_session_name="gha-34909112181-production-rollback",
        ec2_instance_id="i-0e49ddadd4ecc772d",
        ssm_command_id="302fc54a-9541-4c74-bab5-498cd81894a2",
        rollback_started_at="2026-09-14T23:07:33Z",
        rollback_finished_at="2026-09-14T23:08:33Z",
        rollback_duration_seconds=60,
        source_release_id=None,
        source_image_digest=None,
        target_release_id=f"rel-20260914T230733Z-{SAMPLE_SHA[:12]}",
        target_image_digest=SAMPLE_DIGEST,
        target_git_sha=SAMPLE_SHA,
        target_image_repository=SAMPLE_REPO,
        target_manifest_sha256="f" * 64,
        migration_revision_before=None,
        migration_revision_after=None,
        target_migration_revision_authority=None,
        current_pointer_before=None,
        current_pointer_after=None,
        previous_pointer_before=None,
        previous_pointer_after=None,
        running_digest_after=None,
        localhost_live=False,
        localhost_ready=False,
        alb_target_healthy=False,
        final_status="failed",
        failure_reason="rollback_failed",
    )
    validate_rollback_evidence(payload)
    assert payload["assumed_role_arn"] == INTENDED_ROLE_ARN
