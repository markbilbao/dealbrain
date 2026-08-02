#!/usr/bin/env python3
"""Verify and safely extract a staging release bundle tarball."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
from pathlib import Path


class BundleVerifyError(ValueError):
    pass


FORBIDDEN = (
    "docker-compose.production.yml",
    ".env",
    "terraform.tfstate",
    ".git/",
)

# Expected top-level layout prefixes / files for a staging release bundle.
ALLOWED_TOP_LEVEL = frozenset({"compose", "bin", "manifest", "bundle-meta.json"})

REQUIRED_MEMBERS = (
    "compose/docker-compose.base.yml",
    "compose/docker-compose.staging.yml",
    "bin/dealbrain-staging-deploy.sh",
    "bin/assemble-runtime-env.py",
    "bin/ghcr-login.sh",
    "bin/verify-staging.sh",
    "bin/alb_target_health.py",
    "bin/evidence.py",
    "bin/write-staging-evidence.py",
    "bin/staging-deploy-evidence.schema.json",
    "bin/log_redaction.py",
    "manifest/release-manifest.json",
    "bundle-meta.json",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_archive_members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    """Reject absolute paths, traversal, links, devices, FIFOs, and layout surprises."""
    members = tar.getmembers()
    if not members:
        raise BundleVerifyError("archive is empty")

    seen_names: set[str] = set()
    for member in members:
        name = member.name
        if not name or name == ".":
            raise BundleVerifyError(f"invalid archive member name: {name!r}")
        if name in seen_names:
            raise BundleVerifyError(f"duplicate archive member: {name}")
        seen_names.add(name)

        # Absolute paths (Unix and Windows).
        if name.startswith("/") or name.startswith("\\") or Path(name).is_absolute():
            raise BundleVerifyError(f"absolute path rejected: {name}")
        if ":" in name.split("/")[0] and name[1:3] in (":/", ":\\"):
            raise BundleVerifyError(f"absolute path rejected: {name}")

        parts = Path(name).parts
        if ".." in parts:
            raise BundleVerifyError(f"path traversal rejected: {name}")

        top = parts[0]
        if top not in ALLOWED_TOP_LEVEL:
            raise BundleVerifyError(f"unexpected top-level member: {name}")

        if member.issym() or member.islnk():
            raise BundleVerifyError(f"symlink/hardlink rejected: {name}")
        if member.isdev() or member.ischr() or member.isblk() or member.isfifo():
            raise BundleVerifyError(f"special file rejected: {name}")
        if not (member.isfile() or member.isdir()):
            raise BundleVerifyError(f"unsupported archive member type: {name}")

        mode = member.mode
        if mode & (stat.S_ISUID | stat.S_ISGID | getattr(stat, "S_ISVTX", 0)):
            raise BundleVerifyError(f"setuid/setgid/sticky mode rejected: {name}")

        for forbidden in FORBIDDEN:
            if forbidden in name:
                raise BundleVerifyError(f"forbidden member in bundle: {name}")

    return members


def _is_unsupported_filter_typeerror(exc: TypeError) -> bool:
    """True only for interpreters that reject the ``filter=`` keyword."""
    msg = str(exc)
    return "unexpected keyword argument" in msg and "filter" in msg


def _extract_members(tar: tarfile.TarFile, dest: Path, members: list[tarfile.TarInfo]) -> None:
    """Extract pre-validated members one-by-one (never a raw bulk extract).

    Prefer ``filter="data"`` when the interpreter supports it (3.12+). On
    Python 3.9 the keyword raises TypeError; fall back to per-member extract
    only after ``validate_archive_members`` has rejected traversal, links,
    devices, and layout surprises. Unrelated TypeErrors stay fail-closed.
    """
    dest = dest.resolve()
    for member in members:
        target = (dest / member.name).resolve()
        try:
            target.relative_to(dest)
        except ValueError as exc:
            raise BundleVerifyError(f"extract path escaped destination: {member.name}") from exc
        try:
            tar.extract(member, path=dest, filter="data")
        except TypeError as exc:
            if not _is_unsupported_filter_typeerror(exc):
                raise
            # Python 3.9: no filter= support. Members already validated above.
            tar.extract(member, path=dest)


def verify_bundle(
    tarball: Path,
    *,
    expected_checksum: str | None = None,
    expected_release_id: str | None = None,
    expected_digest: str | None = None,
) -> dict:
    actual = _sha256_file(tarball)
    if expected_checksum and actual != expected_checksum:
        raise BundleVerifyError(f"bundle checksum mismatch: {actual} != {expected_checksum}")

    with tempfile.TemporaryDirectory(prefix="dealbrain-bundle-verify-") as tmp:
        dest = Path(tmp)
        with tarfile.open(tarball, "r:gz") as tar:
            members = validate_archive_members(tar)
            _extract_members(tar, dest, members)

        meta = _verify_extracted_layout(
            dest,
            expected_release_id=expected_release_id,
            expected_digest=expected_digest,
        )

    return {"checksum": actual, "meta": meta}


def _verify_extracted_layout(
    dest: Path,
    *,
    expected_release_id: str | None = None,
    expected_digest: str | None = None,
) -> dict:
    meta_path = dest / "bundle-meta.json"
    if not meta_path.is_file():
        raise BundleVerifyError("bundle-meta.json missing")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    for key in (
        "schema_version",
        "release_id",
        "git_sha",
        "image_repository",
        "image_digest",
        "source_manifest_sha256",
        "file_checksums",
        "created_at",
    ):
        if key not in meta:
            raise BundleVerifyError(f"bundle-meta missing {key}")

    if expected_release_id and meta["release_id"] != expected_release_id:
        raise BundleVerifyError("release_id mismatch")
    if expected_digest and meta["image_digest"] != expected_digest:
        raise BundleVerifyError("image_digest mismatch")

    for rel in REQUIRED_MEMBERS:
        if not (dest / rel).is_file():
            raise BundleVerifyError(f"missing required member: {rel}")
    if (dest / "compose/docker-compose.production.yml").exists():
        raise BundleVerifyError("production overlay must not be present")

    for path in dest.rglob("*"):
        if path.is_symlink():
            raise BundleVerifyError(f"symlink present after extract: {path}")

    for rel, expected in meta["file_checksums"].items():
        path = dest / rel
        if not path.is_file():
            raise BundleVerifyError(f"checksum map references missing file: {rel}")
        # bundle-meta.json checksum is self-referential after final write; verify others.
        if rel == "bundle-meta.json":
            continue
        got = _sha256_file(path)
        if got != expected:
            raise BundleVerifyError(f"file checksum mismatch for {rel}")

    return meta


def extract_validated_bundle(
    tarball: Path,
    dest_dir: Path,
    *,
    expected_checksum: str,
    expected_release_id: str | None = None,
    expected_digest: str | None = None,
) -> dict:
    """Validate archive, extract into a temp dir, then atomically replace dest_dir."""
    actual = _sha256_file(tarball)
    if actual != expected_checksum:
        raise BundleVerifyError(f"bundle checksum mismatch: {actual} != {expected_checksum}")

    dest_dir = dest_dir.resolve()
    parent = dest_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp_root = Path(tempfile.mkdtemp(prefix=f".{dest_dir.name}.extract-", dir=str(parent)))
    try:
        with tarfile.open(tarball, "r:gz") as tar:
            members = validate_archive_members(tar)
            _extract_members(tar, tmp_root, members)

        meta = _verify_extracted_layout(
            tmp_root,
            expected_release_id=expected_release_id,
            expected_digest=expected_digest,
        )

        # Atomic replace: move validated tree into place.
        if dest_dir.exists():
            backup = Path(tempfile.mkdtemp(prefix=f".{dest_dir.name}.bak-", dir=str(parent)))
            dest_dir.rename(backup)
            try:
                tmp_root.rename(dest_dir)
            except Exception:
                backup.rename(dest_dir)
                raise
            shutil.rmtree(backup, ignore_errors=True)
        else:
            tmp_root.rename(dest_dir)
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)

    # Restrict permissions on the release directory tree.
    os.chmod(dest_dir, 0o755)
    return {"checksum": actual, "meta": meta, "dest": str(dest_dir)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tarball", type=Path)
    parser.add_argument("--checksum", default=None)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--image-digest", default=None)
    parser.add_argument(
        "--extract-to",
        type=Path,
        default=None,
        help="When set, safely extract into this release directory after validation.",
    )
    args = parser.parse_args(argv)
    try:
        if args.extract_to is not None:
            if not args.checksum:
                raise BundleVerifyError("--checksum is required with --extract-to")
            result = extract_validated_bundle(
                args.tarball,
                args.extract_to,
                expected_checksum=args.checksum,
                expected_release_id=args.release_id,
                expected_digest=args.image_digest,
            )
        else:
            result = verify_bundle(
                args.tarball,
                expected_checksum=args.checksum,
                expected_release_id=args.release_id,
                expected_digest=args.image_digest,
            )
    except BundleVerifyError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "ok: release_id={rid} digest={digest} checksum={sha}".format(
            rid=result["meta"]["release_id"],
            digest=result["meta"]["image_digest"],
            sha=result["checksum"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
