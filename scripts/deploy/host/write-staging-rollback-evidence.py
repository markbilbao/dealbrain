#!/usr/bin/env python3
"""Write append-only staging rollback evidence with deterministic checksum.

Fail closed if the canonical rollback evidence module cannot be loaded.
Never fall back to an inline writer. Never fabricate rollback_ok.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _load_rollback_evidence_api():
    sibling = Path(__file__).resolve().parent / "rollback_evidence.py"
    if sibling.is_file():
        spec = importlib.util.spec_from_file_location(
            "dealbrain_canonical_staging_rollback_evidence", sibling
        )
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                create_fn = getattr(module, "create_rollback_evidence", None)
                write_fn = getattr(module, "write_rollback_evidence", None)
                if callable(create_fn) and callable(write_fn):
                    return create_fn, write_fn
            except Exception:
                pass

    try:
        from scripts.deploy.rollback_evidence import (
            create_rollback_evidence,
            write_rollback_evidence,
        )

        return create_rollback_evidence, write_rollback_evidence
    except ImportError as exc:
        print(
            "ERROR: canonical rollback evidence module unavailable; "
            "refusing to write rollback evidence",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def _boolish(value: str) -> bool | None:
    if value in ("true", "True", "1"):
        return True
    if value in ("false", "False", "0"):
        return False
    if value in ("", "None", "null"):
        return None
    return None


def _optional(value: str) -> str | None:
    if value in ("", "None", "null"):
        return None
    return value


def main() -> int:
    create_rollback_evidence, write_rollback_evidence = _load_rollback_evidence_api()

    out = Path(os.environ["DEALBRAIN_EVIDENCE_OUT"])
    rollback_run_id = os.environ["DEALBRAIN_ROLLBACK_RUN_ID"]
    aws_account = os.environ.get("DEALBRAIN_AWS_ACCOUNT_ID", "000000000000")
    aws_region = os.environ.get("DEALBRAIN_REGION", "us-east-1")
    assumed_role = os.environ.get(
        "DEALBRAIN_ASSUMED_ROLE_ARN",
        f"arn:aws:iam::{aws_account}:role/dealbrain-staging-gha-deploy",
    )
    role_session = os.environ.get(
        "DEALBRAIN_ROLE_SESSION_NAME", f"gha-{rollback_run_id}-staging-rollback"
    )

    payload = create_rollback_evidence(
        rollback_workflow_run_id=str(rollback_run_id),
        aws_account_id=aws_account,
        aws_region=aws_region,
        assumed_role_arn=assumed_role,
        role_session_name=role_session,
        ec2_instance_id=os.environ.get("DEALBRAIN_INSTANCE_ID", "i-unknown"),
        ssm_command_id=os.environ.get("DEALBRAIN_SSM_COMMAND_ID") or None,
        rollback_started_at=os.environ["DEALBRAIN_STARTED_AT"],
        rollback_finished_at=os.environ["DEALBRAIN_FINISHED_AT"],
        rollback_duration_seconds=int(os.environ["DEALBRAIN_DURATION"]),
        source_release_id=_optional(os.environ.get("DEALBRAIN_SOURCE_RELEASE_ID", "")),
        source_image_digest=_optional(os.environ.get("DEALBRAIN_SOURCE_IMAGE_DIGEST", "")),
        target_release_id=os.environ["DEALBRAIN_TARGET_RELEASE_ID"],
        target_image_digest=os.environ["DEALBRAIN_TARGET_IMAGE_DIGEST"],
        target_git_sha=os.environ["DEALBRAIN_TARGET_GIT_SHA"],
        target_image_repository=os.environ["DEALBRAIN_TARGET_IMAGE_REPOSITORY"],
        target_manifest_sha256=os.environ["DEALBRAIN_TARGET_MANIFEST_SHA256"],
        migration_revision_before=_optional(os.environ.get("DEALBRAIN_MIGRATION_BEFORE", "")),
        migration_revision_after=_optional(os.environ.get("DEALBRAIN_MIGRATION_AFTER", "")),
        target_migration_revision_authority=_optional(
            os.environ.get("DEALBRAIN_MIGRATION_AUTHORITY", "")
        ),
        current_pointer_before=_optional(os.environ.get("DEALBRAIN_CURRENT_BEFORE", "")),
        current_pointer_after=_optional(os.environ.get("DEALBRAIN_CURRENT_AFTER", "")),
        previous_pointer_before=_optional(os.environ.get("DEALBRAIN_PREVIOUS_BEFORE", "")),
        previous_pointer_after=_optional(os.environ.get("DEALBRAIN_PREVIOUS_AFTER", "")),
        running_digest_after=_optional(os.environ.get("DEALBRAIN_RUNNING_DIGEST_AFTER", "")),
        localhost_live=_boolish(os.environ.get("DEALBRAIN_LOCAL_LIVE", "")),
        localhost_ready=_boolish(os.environ.get("DEALBRAIN_LOCAL_READY", "")),
        alb_target_healthy=_boolish(os.environ.get("DEALBRAIN_ALB_HEALTH", "")),
        final_status=os.environ["DEALBRAIN_FINAL_STATUS"],
        failure_reason=_optional(os.environ.get("DEALBRAIN_FAILURE_REASON", "")),
    )
    write_rollback_evidence(out, payload)
    print(f"wrote rollback evidence: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
