#!/usr/bin/env python3
"""Validate staging rollback evidence (schema + checksum).

Invoke from the repository root as a module so ``scripts.*`` imports resolve:

  python -m scripts.deploy.validate_staging_rollback_evidence PATH
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.deploy.evidence import EvidenceError
from scripts.deploy.rollback_evidence import load_rollback_evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to staging-rollback-evidence.json")
    args = parser.parse_args(argv)
    try:
        payload = load_rollback_evidence(args.path)
    except (OSError, json.JSONDecodeError, EvidenceError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "ok: target_release_id={rid} status={status} evidence_sha256={sha}".format(
            rid=payload["target_release_id"],
            status=payload["final_status"],
            sha=payload["evidence_sha256"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
