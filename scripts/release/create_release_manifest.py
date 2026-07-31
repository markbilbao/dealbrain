#!/usr/bin/env python3
"""Create a Sprint 25b.1 built-state release manifest.

Example:
  uv run python scripts/release/create_release_manifest.py \\
    --git-sha \"$GITHUB_SHA\" \\
    --image-repository \"ghcr.io/$GITHUB_REPOSITORY\" \\
    --image-digest \"$DIGEST\" \\
    --build-workflow-run-id \"$GITHUB_RUN_ID\" \\
    --test-workflow-run-id \"$TEST_RUN_ID\" \\
    --output release-manifest.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python scripts/release/create_release_manifest.py` without install.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.release.manifest import (  # noqa: E402
    ManifestError,
    create_built_manifest,
    dumps_manifest,
    write_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-sha", required=True, help="Full 40-char git commit SHA")
    parser.add_argument(
        "--image-repository",
        required=True,
        help="Canonical GHCR repository, e.g. ghcr.io/org/dealbrain",
    )
    parser.add_argument(
        "--image-digest",
        required=True,
        help="Immutable digest sha256:<64 hex>",
    )
    parser.add_argument("--build-workflow-run-id", required=True)
    parser.add_argument("--test-workflow-run-id", required=True)
    parser.add_argument(
        "--created-at",
        default=None,
        help="UTC timestamp YYYY-MM-DDTHH:MM:SSZ (default: now)",
    )
    parser.add_argument(
        "--release-id",
        default=None,
        help="Optional release id (default: derived from created-at + sha)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("release-manifest.json"),
        help="Output path (default: ./release-manifest.json)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Also print the manifest JSON to stdout",
    )
    args = parser.parse_args(argv)

    try:
        manifest = create_built_manifest(
            git_sha=args.git_sha.lower(),
            image_repository=args.image_repository,
            image_digest=args.image_digest.lower(),
            build_workflow_run_id=args.build_workflow_run_id,
            test_workflow_run_id=args.test_workflow_run_id,
            created_at=args.created_at,
            release_id=args.release_id,
        )
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_manifest(args.output, manifest)
    print(f"wrote {args.output}", file=sys.stderr)
    print(f"manifest_sha256={manifest['manifest_sha256']}", file=sys.stderr)
    print(f"release_id={manifest['release_id']}", file=sys.stderr)
    if args.stdout:
        sys.stdout.write(dumps_manifest(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
