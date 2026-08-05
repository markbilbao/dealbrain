#!/usr/bin/env python3
"""Resolve rollback target migration revision with validated prior evidence.

Host entrypoint (flat bin/ layout). Prefer DEPLOY_VERSION.migration_revision;
else use migration_revision_after from the exact fully validated staging_ok
evidence selected under --prior-candidates-dir (sidecar + identity bindings).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_prior_module():
    sibling = Path(__file__).resolve().parent / "prior_staging_evidence.py"
    if sibling.is_file():
        spec = importlib.util.spec_from_file_location(
            "dealbrain_prior_staging_evidence_host", sibling
        )
        if spec is not None and spec.loader is not None:
            # Register before exec_module: @dataclass on Python 3.9 resolves
            # annotations via sys.modules[cls.__module__].
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                sys.modules.pop(spec.name, None)
                raise
            return module
    try:
        from scripts.deploy import prior_staging_evidence as module

        return module
    except ImportError as exc:
        print("FAIL: prior_staging_evidence module unavailable", file=sys.stderr)
        raise SystemExit(1) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deploy-version", type=Path, default=None)
    parser.add_argument("--prior-candidates-dir", type=Path, default=None)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--image-repository", required=True)
    parser.add_argument("--aws-account-id", required=True)
    parser.add_argument("--aws-region", required=True)
    parser.add_argument("--ec2-instance-id", required=True)
    parser.add_argument("--source-manifest-sha256", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    mod = _load_prior_module()
    prior = None
    try:
        # Prefer DEPLOY_VERSION without requiring prior candidates.
        migration = mod.resolve_target_migration_revision(
            deploy_version_path=args.deploy_version,
            validated_prior=None,
        )
    except Exception:
        migration = None

    if migration is None or migration.authority != mod.MIGRATION_AUTHORITY_DEPLOY_VERSION:
        if args.prior_candidates_dir is None:
            print(
                "FAIL: DEPLOY_VERSION migration_revision missing and "
                "no --prior-candidates-dir provided",
                file=sys.stderr,
            )
            return 1
        try:
            pairs = mod.discover_candidate_pairs(args.prior_candidates_dir)
            prior = mod.select_authoritative_prior_staging_evidence(
                pairs,
                expected_release_id=args.release_id,
                expected_image_digest=args.image_digest,
                expected_image_repository=args.image_repository,
                expected_aws_account_id=args.aws_account_id,
                expected_aws_region=args.aws_region,
                expected_ec2_instance_id=args.ec2_instance_id,
                expected_source_manifest_sha256=args.source_manifest_sha256 or None,
            )
            migration = mod.resolve_target_migration_revision(
                deploy_version_path=args.deploy_version,
                validated_prior=prior,
            )
        except Exception as exc:  # noqa: BLE001 — host fail-closed boundary
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1

    payload = {
        "migration_revision": migration.migration_revision,
        "authority": migration.authority,
        "prior_evidence_key": prior.evidence_key if prior is not None else None,
        "prior_evidence_sha256": prior.evidence_sha256 if prior is not None else None,
        "prior_deploy_workflow_run_id": (
            prior.deploy_workflow_run_id if prior is not None else None
        ),
        "prior_ssm_command_id": prior.ssm_command_id if prior is not None else None,
        "prior_deployment_finished_at": (
            prior.deployment_finished_at if prior is not None else None
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ok: migration={migration.migration_revision} authority={migration.authority}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
