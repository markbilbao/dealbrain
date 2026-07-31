#!/usr/bin/env python3
"""Validate a Sprint 25b.1 release manifest.

Runs JSON Schema validation (``schemas/release-manifest.schema.json``),
semantic checks, and ``manifest_sha256`` integrity verification.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.release.manifest import ManifestError, load_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help="Path to release-manifest.json",
    )
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.path)
    except (OSError, ManifestError, ValueError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1

    print(
        f"ok: release_id={manifest['release_id']} "
        f"status={manifest['final_status']} "
        f"digest={manifest['image_digest']} "
        f"manifest_sha256={manifest['manifest_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
