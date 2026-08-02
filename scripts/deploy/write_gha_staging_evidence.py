#!/usr/bin/env python3
"""Accept authoritative host staging evidence — never synthesize success.

The workflow downloads host-uploaded evidence from the release/run-specific S3
key and validates schema, checksum, semantic gates, and authority bindings.
Missing evidence fails closed. This script refuses to create staging_ok.

Invoke from the repository root as a module so ``scripts.*`` imports resolve:

  python -m scripts.deploy.write_gha_staging_evidence [options]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.deploy.evidence import EvidenceError, load_evidence, validate_evidence_bindings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=Path,
        required=True,
        help="Path to host-authored staging-deploy-evidence.json (must already exist)",
    )
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--image-repository", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--deploy-run-id", required=True)
    parser.add_argument("--aws-account-id", required=True)
    parser.add_argument("--aws-region", required=True)
    parser.add_argument("--ec2-instance-id", required=True)
    parser.add_argument("--ssm-command-id", required=True)
    args = parser.parse_args(argv)

    if not args.evidence.is_file():
        print(
            f"FAIL: authoritative host evidence missing at {args.evidence} "
            "(refusing to fabricate staging_ok)",
            file=sys.stderr,
        )
        return 1

    try:
        payload = load_evidence(args.evidence)
        validate_evidence_bindings(
            payload,
            release_id=args.release_id,
            git_sha=args.git_sha,
            image_digest=args.image_digest,
            image_repository=args.image_repository,
            source_manifest_sha256=args.source_manifest_sha256,
            deploy_workflow_run_id=args.deploy_run_id,
            aws_account_id=args.aws_account_id,
            aws_region=args.aws_region,
            ec2_instance_id=args.ec2_instance_id,
            ssm_command_id=args.ssm_command_id,
            require_staging_ok=True,
        )
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(
        "ok: host evidence accepted release_id={rid} status={status} sha={sha}".format(
            rid=payload["release_id"],
            status=payload["final_status"],
            sha=payload["evidence_sha256"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
