#!/usr/bin/env python3
"""Write append-only staging deploy evidence with deterministic checksum.

Fail closed if the canonical evidence module cannot be loaded. Never fall
back to an inline writer (Sprint 25b.4a / 25b.5g).

Loads the sibling ``evidence.py`` via ``importlib`` (bundle ``bin/`` layout)
or the ``scripts.deploy.evidence`` package (repository checkout). No
``PYTHONPATH`` / ``sys.path`` mutation is required for the sibling contract.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _load_evidence_api():
    """Import canonical evidence helpers only — no duplicate fallback writer."""
    sibling = Path(__file__).resolve().parent / "evidence.py"
    if sibling.is_file():
        spec = importlib.util.spec_from_file_location(
            "dealbrain_canonical_staging_evidence", sibling
        )
        if spec is not None and spec.loader is not None:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                create_evidence = getattr(module, "create_evidence", None)
                write_evidence = getattr(module, "write_evidence", None)
                if callable(create_evidence) and callable(write_evidence):
                    return create_evidence, write_evidence
            except Exception:
                # Fall through to package import / fail-closed below.
                # Do not print exception text — it may embed paths or env hints.
                pass

    try:
        from scripts.deploy.evidence import create_evidence, write_evidence

        return create_evidence, write_evidence
    except ImportError as exc:
        print(
            "ERROR: canonical evidence module unavailable; refusing to write deployment evidence",
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


def main() -> int:
    create_evidence, write_evidence = _load_evidence_api()

    out = Path(os.environ["DEALBRAIN_EVIDENCE_OUT"])
    release_id = os.environ["DEALBRAIN_RELEASE_ID"]
    git_sha = os.environ["DEALBRAIN_GIT_SHA"]
    image_repository = os.environ["DEALBRAIN_IMAGE_REPOSITORY"]
    image_digest = os.environ["DEALBRAIN_IMAGE_DIGEST"]
    source_manifest_sha256 = os.environ.get("DEALBRAIN_SOURCE_MANIFEST_SHA256", "")
    deploy_run_id = os.environ["DEALBRAIN_DEPLOY_RUN_ID"]

    # Non-secret AWS identity from instance metadata / env (optional in unit tests).
    aws_account = os.environ.get("DEALBRAIN_AWS_ACCOUNT_ID", "000000000000")
    aws_region = os.environ.get("DEALBRAIN_REGION", "us-east-1")
    assumed_role = os.environ.get(
        "DEALBRAIN_ASSUMED_ROLE_ARN",
        f"arn:aws:iam::{aws_account}:role/dealbrain-staging-gha-deploy",
    )
    role_session = os.environ.get("DEALBRAIN_ROLE_SESSION_NAME", f"gha-{deploy_run_id}-staging")

    payload = create_evidence(
        release_id=release_id,
        git_sha=git_sha,
        image_repository=image_repository,
        image_digest=image_digest,
        source_manifest_sha256=source_manifest_sha256 or ("0" * 64),
        deploy_workflow_run_id=str(deploy_run_id),
        aws_account_id=aws_account,
        aws_region=aws_region,
        assumed_role_arn=assumed_role,
        role_session_name=role_session,
        ec2_instance_id=os.environ.get("DEALBRAIN_INSTANCE_ID", "i-unknown"),
        ssm_command_id=os.environ.get("DEALBRAIN_SSM_COMMAND_ID") or None,
        migration_revision_before=os.environ.get("DEALBRAIN_MIGRATION_BEFORE") or None,
        migration_revision_after=os.environ.get("DEALBRAIN_MIGRATION_AFTER") or None,
        localhost_live=_boolish(os.environ.get("DEALBRAIN_LOCAL_LIVE", "")),
        localhost_ready=_boolish(os.environ.get("DEALBRAIN_LOCAL_READY", "")),
        alb_target_healthy=_boolish(os.environ.get("DEALBRAIN_ALB_HEALTH", "")),
        smoke_ok=_boolish(os.environ.get("DEALBRAIN_SMOKE_OK", "")),
        image_id=os.environ.get("DEALBRAIN_IMAGE_ID") or None,
        repo_digest=os.environ.get("DEALBRAIN_REPO_DIGEST") or None,
        image_created_at=os.environ.get("DEALBRAIN_IMAGE_CREATED_AT") or None,
        deployment_started_at=os.environ["DEALBRAIN_STARTED_AT"],
        deployment_finished_at=os.environ["DEALBRAIN_FINISHED_AT"],
        deployment_duration_seconds=int(os.environ["DEALBRAIN_DURATION"]),
        final_status=os.environ.get("DEALBRAIN_FINAL_STATUS", "failed"),
        failure_reason=os.environ.get("DEALBRAIN_FAILURE_REASON") or None,
    )
    write_evidence(out, payload)
    print(f"ok: evidence {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
