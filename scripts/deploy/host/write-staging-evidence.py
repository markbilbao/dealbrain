#!/usr/bin/env python3
"""Write append-only staging deploy evidence with deterministic checksum."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow importing evidence helpers from the same bin/ directory (bundle layout).
_BIN = Path(__file__).resolve().parent
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    from evidence import create_evidence, write_evidence
except ImportError:
    try:
        from scripts.deploy.evidence import create_evidence, write_evidence
    except ImportError:
        # Bundle layout: bin/ next to evidence.py sibling may not exist on host;
        # fall back to inline minimal writer matching schema.
        from hashlib import sha256

        def _canonicalize(payload: dict) -> str:
            data = dict(payload)
            data["evidence_sha256"] = None
            return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

        def create_evidence(**kwargs):  # type: ignore[no-redef]
            payload = dict(kwargs)
            payload["schema_version"] = 1
            payload["evidence_sha256"] = sha256(_canonicalize(payload).encode()).hexdigest()
            return payload

        def write_evidence(path: Path, payload: dict) -> None:  # type: ignore[no-redef]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )


def _boolish(value: str) -> bool | None:
    if value in ("true", "True", "1"):
        return True
    if value in ("false", "False", "0"):
        return False
    if value in ("", "None", "null"):
        return None
    return None


def main() -> int:
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
    role_session = os.environ.get(
        "DEALBRAIN_ROLE_SESSION_NAME", f"gha-{deploy_run_id}-staging"
    )

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
