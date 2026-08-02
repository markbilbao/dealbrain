#!/usr/bin/env python3
"""Accept authoritative host staging rollback evidence — never synthesize success.

Missing evidence fails closed. This script refuses to create rollback_ok.

Invoke from the repository root as a module:

  python -m scripts.deploy.write_gha_staging_rollback_evidence [options]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.deploy.evidence import EvidenceError
from scripts.deploy.rollback_evidence import (
    load_rollback_evidence,
    validate_rollback_evidence_bindings,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=Path,
        required=True,
        help="Path to host-authored staging-rollback-evidence.json (must already exist)",
    )
    parser.add_argument("--target-release-id", required=True)
    parser.add_argument("--target-git-sha", required=True)
    parser.add_argument("--target-image-repository", required=True)
    parser.add_argument("--target-image-digest", required=True)
    parser.add_argument("--target-manifest-sha256", required=True)
    parser.add_argument("--rollback-run-id", required=True)
    parser.add_argument("--aws-account-id", required=True)
    parser.add_argument("--aws-region", required=True)
    parser.add_argument("--ec2-instance-id", required=True)
    parser.add_argument("--ssm-command-id", required=True)
    args = parser.parse_args(argv)

    if not args.evidence.is_file():
        print(
            f"FAIL: authoritative host rollback evidence missing at {args.evidence} "
            "(refusing to fabricate rollback_ok)",
            file=sys.stderr,
        )
        return 1

    try:
        payload = load_rollback_evidence(args.evidence)
        validate_rollback_evidence_bindings(
            payload,
            target_release_id=args.target_release_id,
            target_git_sha=args.target_git_sha,
            target_image_digest=args.target_image_digest,
            target_image_repository=args.target_image_repository,
            target_manifest_sha256=args.target_manifest_sha256,
            rollback_workflow_run_id=args.rollback_run_id,
            aws_account_id=args.aws_account_id,
            aws_region=args.aws_region,
            ec2_instance_id=args.ec2_instance_id,
            ssm_command_id=args.ssm_command_id,
            require_rollback_ok=True,
        )
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(
        "ok: host rollback evidence accepted target_release_id={rid} "
        "status={status} sha={sha}".format(
            rid=payload["target_release_id"],
            status=payload["final_status"],
            sha=payload["evidence_sha256"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
