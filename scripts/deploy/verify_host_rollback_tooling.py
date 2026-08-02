#!/usr/bin/env python3
"""Verify staging host rollback tooling capability before mutation.

Fails closed when the trusted capability file is missing, outdated, or when
installed binary checksums do not match the capability inventory. Does not
execute arbitrary commands or touch secrets/production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_CAPABILITY = "staging-rollback"
EXPECTED_TOOLING_VERSION = "25b.5"
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_TOOLING_FILES = (
    "dealbrain-staging-rollback.sh",
    "deploy_atomicity.sh",
    "rollback_evidence.py",
    "write-staging-rollback-evidence.py",
    "prior_staging_evidence.py",
    "resolve-rollback-migration.py",
    "verify_host_rollback_tooling.py",
    "staging-rollback-evidence.schema.json",
    "verify_staging_bundle.py",
    "evidence.py",
)


class HostToolingError(ValueError):
    """Raised when host rollback tooling is absent or untrusted."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_host_tooling_capability(
    bin_dir: Path,
    *,
    tooling_version: str = EXPECTED_TOOLING_VERSION,
) -> dict:
    """Build a capability inventory for files installed under bin_dir."""
    root = bin_dir.resolve()
    required: dict[str, str] = {}
    for name in REQUIRED_TOOLING_FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise HostToolingError(f"required tooling binary missing: {name}")
        required[name] = _sha256_file(path)
    return {
        "schema_version": 1,
        "capability": EXPECTED_CAPABILITY,
        "tooling_version": tooling_version,
        "required_binaries": required,
    }


def write_host_tooling_capability(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_host_rollback_tooling(
    capability_path: Path,
    bin_dir: Path,
    *,
    expected_tooling_version: str = EXPECTED_TOOLING_VERSION,
) -> dict:
    """Verify capability file and on-disk checksums before rollback mutation."""
    if not capability_path.is_file():
        raise HostToolingError(
            f"host tooling capability missing: {capability_path} "
            "(Deploy Staging must refresh host tooling before rollback)"
        )
    try:
        payload = json.loads(capability_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HostToolingError(f"host tooling capability unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise HostToolingError("host tooling capability must be a JSON object")
    if payload.get("schema_version") != 1:
        raise HostToolingError("unsupported host tooling capability schema_version")
    if payload.get("capability") != EXPECTED_CAPABILITY:
        raise HostToolingError("host tooling capability mismatch")
    version = payload.get("tooling_version")
    if version != expected_tooling_version:
        raise HostToolingError(
            f"host tooling outdated or unexpected: got {version!r} "
            f"expected {expected_tooling_version!r}"
        )
    required = payload.get("required_binaries")
    if not isinstance(required, dict) or not required:
        raise HostToolingError("host tooling capability missing required_binaries")

    root = bin_dir.resolve()
    for name in REQUIRED_TOOLING_FILES:
        expected = required.get(name)
        if not isinstance(expected, str) or not SHA256_HEX_RE.fullmatch(expected):
            raise HostToolingError(f"host tooling capability missing checksum for {name}")
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise HostToolingError(f"required tooling binary missing on host: {name}")
        actual = _sha256_file(path)
        if actual != expected:
            raise HostToolingError(f"host tooling checksum mismatch for {name}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bin-dir",
        type=Path,
        default=Path("/opt/dealbrain/bin"),
    )
    parser.add_argument(
        "--capability-path",
        type=Path,
        default=None,
        help="Defaults to <bin-dir>/staging-host-tooling.json",
    )
    parser.add_argument(
        "--expected-tooling-version",
        default=EXPECTED_TOOLING_VERSION,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write/refresh the capability file from current bin-dir contents.",
    )
    args = parser.parse_args(argv)
    capability_path = args.capability_path or (args.bin_dir / "staging-host-tooling.json")
    try:
        if args.write:
            payload = build_host_tooling_capability(
                args.bin_dir,
                tooling_version=args.expected_tooling_version,
            )
            write_host_tooling_capability(capability_path, payload)
            print(f"ok: wrote host tooling capability {capability_path}")
            return 0
        payload = verify_host_rollback_tooling(
            capability_path,
            args.bin_dir,
            expected_tooling_version=args.expected_tooling_version,
        )
    except HostToolingError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "ok: host rollback tooling capability={cap} version={ver}".format(
            cap=payload["capability"],
            ver=payload["tooling_version"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
