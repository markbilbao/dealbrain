#!/usr/bin/env python3
"""Mandatory SHA-256 sidecar verification for host rollback evidence (GHA).

Checksum-only gate: semantic validation must run after this succeeds.

  python -m scripts.deploy.verify_rollback_evidence_sidecar \
    --evidence PATH --sidecar PATH.sha256
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.deploy.evidence import EvidenceError
from scripts.deploy.rollback_evidence import verify_rollback_evidence_sidecar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=Path,
        required=True,
        help="Path to staging-rollback-evidence.json",
    )
    parser.add_argument(
        "--sidecar",
        type=Path,
        default=None,
        help="Path to staging-rollback-evidence.json.sha256 (default: <evidence>.sha256)",
    )
    args = parser.parse_args(argv)
    try:
        token = verify_rollback_evidence_sidecar(args.evidence, args.sidecar)
    except (OSError, EvidenceError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"ok: rollback evidence sidecar checksum verified evidence_sha256={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
