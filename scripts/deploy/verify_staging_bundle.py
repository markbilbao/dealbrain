#!/usr/bin/env python3
"""Verify and safely extract a staging release bundle tarball."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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

# Historical Build Image #15-era bundles (schema 1) predate rollback tooling.
HISTORICAL_BUNDLE_SCHEMA_VERSION = 1
# Current bundles ship application runtime + host deploy/rollback tooling.
CURRENT_BUNDLE_SCHEMA_VERSION = 2
SUPPORTED_BUNDLE_SCHEMA_VERSIONS = frozenset(
    {HISTORICAL_BUNDLE_SCHEMA_VERSION, CURRENT_BUNDLE_SCHEMA_VERSION}
)

# Runtime artifacts required to start/validate a target application release.
APPLICATION_RUNTIME_MEMBERS = (
    "compose/docker-compose.base.yml",
    "compose/docker-compose.staging.yml",
    "manifest/release-manifest.json",
    "bundle-meta.json",
)

# Host deploy/rollback tooling members delivered by current (schema 2) bundles.
HOST_TOOLING_MEMBERS = (
    "bin/dealbrain-staging-deploy.sh",
    "bin/dealbrain-staging-rollback.sh",
    "bin/deploy_atomicity.sh",
    "bin/assemble-runtime-env.py",
    "bin/ghcr-login.sh",
    "bin/verify-staging.sh",
    "bin/alb_target_health.py",
    "bin/evidence.py",
    "bin/rollback_evidence.py",
    "bin/write-staging-evidence.py",
    "bin/write-staging-rollback-evidence.py",
    "bin/prior_staging_evidence.py",
    "bin/verify_host_rollback_tooling.py",
    "bin/resolve-rollback-migration.py",
    "bin/staging-deploy-evidence.schema.json",
    "bin/staging-rollback-evidence.schema.json",
    "bin/log_redaction.py",
)

# Full required set for current schema-2 bundles / deploy verify paths.
REQUIRED_MEMBERS = APPLICATION_RUNTIME_MEMBERS + HOST_TOOLING_MEMBERS

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_ID_RE = re.compile(r"^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GHCR_REPO_RE = re.compile(r"^ghcr\.io/[a-z0-9]([a-z0-9._-]*/)+[a-z0-9._-]+$")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def required_members_for_schema(schema_version: int) -> tuple[str, ...]:
    """Return required members for a declared bundle schema version."""
    if schema_version == HISTORICAL_BUNDLE_SCHEMA_VERSION:
        return APPLICATION_RUNTIME_MEMBERS
    if schema_version == CURRENT_BUNDLE_SCHEMA_VERSION:
        return REQUIRED_MEMBERS
    raise BundleVerifyError(f"unsupported bundle schema_version: {schema_version!r}")


def normalize_checksum_relpath(rel: str) -> str:
    """Normalize and reject unsafe checksum map paths."""
    if not isinstance(rel, str) or not rel or rel.strip() != rel:
        raise BundleVerifyError(f"unsafe checksum path: {rel!r}")
    if rel.startswith("/") or rel.startswith("\\") or Path(rel).is_absolute():
        raise BundleVerifyError(f"absolute checksum path rejected: {rel}")
    if "\\" in rel or "//" in rel or rel.startswith("./"):
        raise BundleVerifyError(f"unsafe checksum path: {rel}")
    parts = Path(rel).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise BundleVerifyError(f"path traversal rejected in checksum map: {rel}")
    normalized = "/".join(parts)
    if normalized != rel:
        raise BundleVerifyError(f"non-normalized checksum path rejected: {rel}")
    top = parts[0]
    if top not in ALLOWED_TOP_LEVEL and normalized != "bundle-meta.json":
        raise BundleVerifyError(f"unexpected checksum path top-level: {rel}")
    return normalized


def resolve_under_release_root(release_root: Path, rel: str) -> Path:
    """Resolve rel under release_root; reject escapes and unsafe symlinks."""
    normalized = normalize_checksum_relpath(rel)
    root = release_root.resolve()
    cur = root
    for part in Path(normalized).parts:
        cur = cur / part
        if cur.is_symlink():
            linked = cur.resolve()
            try:
                linked.relative_to(root)
            except ValueError as exc:
                raise BundleVerifyError(f"symlink escapes release root: {normalized}") from exc
    candidate = root / normalized
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise BundleVerifyError(f"checksum path escapes release root: {normalized}") from exc
    return candidate


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


def _validate_bundle_meta_identity(
    meta: dict,
    *,
    expected_release_id: str | None = None,
    expected_git_sha: str | None = None,
    expected_image_repository: str | None = None,
    expected_digest: str | None = None,
    expected_source_manifest_sha256: str | None = None,
) -> None:
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

    schema_version = meta["schema_version"]
    if type(schema_version) is not int:
        raise BundleVerifyError("bundle-meta schema_version must be int")
    if schema_version not in SUPPORTED_BUNDLE_SCHEMA_VERSIONS:
        raise BundleVerifyError(f"unsupported bundle schema_version: {schema_version!r}")

    release_id = str(meta["release_id"])
    if not _RELEASE_ID_RE.fullmatch(release_id):
        raise BundleVerifyError("invalid bundle-meta release_id")
    if expected_release_id and release_id != expected_release_id:
        raise BundleVerifyError("release_id mismatch")

    git_sha = str(meta["git_sha"])
    if not _GIT_SHA_RE.fullmatch(git_sha):
        raise BundleVerifyError("invalid bundle-meta git_sha")
    if expected_git_sha and git_sha != expected_git_sha:
        raise BundleVerifyError("git_sha mismatch")

    repo = str(meta["image_repository"]).rstrip("/").lower()
    if not _GHCR_REPO_RE.fullmatch(repo):
        raise BundleVerifyError("invalid bundle-meta image_repository")
    if expected_image_repository and repo != expected_image_repository.rstrip("/").lower():
        raise BundleVerifyError("image_repository mismatch")

    digest = str(meta["image_digest"])
    if not _DIGEST_RE.fullmatch(digest):
        raise BundleVerifyError("invalid bundle-meta image_digest")
    if expected_digest and digest != expected_digest:
        raise BundleVerifyError("image_digest mismatch")

    manifest_sha = str(meta["source_manifest_sha256"])
    if not _SHA256_HEX_RE.fullmatch(manifest_sha):
        raise BundleVerifyError("invalid bundle-meta source_manifest_sha256")
    if expected_source_manifest_sha256 and manifest_sha != expected_source_manifest_sha256:
        raise BundleVerifyError("source_manifest_sha256 mismatch")

    checksums = meta["file_checksums"]
    if not isinstance(checksums, dict) or not checksums:
        raise BundleVerifyError("file_checksums must be a non-empty object")


def verify_file_checksums_map(release_root: Path, file_checksums: dict) -> None:
    """Verify every file_checksums entry under release_root (path-safe)."""
    if not isinstance(file_checksums, dict) or not file_checksums:
        raise BundleVerifyError("file_checksums must be a non-empty object")

    root = release_root.resolve()
    seen_normalized: set[str] = set()
    for rel, expected in file_checksums.items():
        if not isinstance(expected, str) or not _SHA256_HEX_RE.fullmatch(expected):
            raise BundleVerifyError(f"malformed checksum for {rel!r}")
        normalized = normalize_checksum_relpath(str(rel))
        if normalized in seen_normalized:
            raise BundleVerifyError(f"duplicate normalized checksum path: {normalized}")
        seen_normalized.add(normalized)

        path = resolve_under_release_root(root, normalized)
        if path.is_symlink():
            raise BundleVerifyError(f"symlink rejected in release tree: {normalized}")
        if not path.is_file():
            raise BundleVerifyError(f"checksum map references missing file: {normalized}")
        # bundle-meta.json checksum is self-referential after final write; skip bytes check.
        if normalized == "bundle-meta.json":
            continue
        got = _sha256_file(path)
        if got != expected:
            raise BundleVerifyError(f"file checksum mismatch for {normalized}")


def verify_release_directory(
    release_dir: Path,
    *,
    expected_release_id: str | None = None,
    expected_git_sha: str | None = None,
    expected_image_repository: str | None = None,
    expected_digest: str | None = None,
    expected_source_manifest_sha256: str | None = None,
    require_deploy_version: bool = False,
) -> dict:
    """Fully verify a retained local release directory against bundle-meta.json.

    Historical schema-1 releases are accepted when application runtime members
    and their declared file_checksums verify. Rollback host tooling is not
    required inside historical target trees (it comes from the host install).
    """
    dest = release_dir.resolve()
    if not dest.is_dir():
        raise BundleVerifyError(f"release directory missing: {dest}")

    meta_path = dest / "bundle-meta.json"
    if not meta_path.is_file():
        raise BundleVerifyError("bundle-meta.json missing")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BundleVerifyError("bundle-meta.json is not valid JSON") from exc
    if not isinstance(meta, dict):
        raise BundleVerifyError("bundle-meta.json must be a JSON object")

    _validate_bundle_meta_identity(
        meta,
        expected_release_id=expected_release_id,
        expected_git_sha=expected_git_sha,
        expected_image_repository=expected_image_repository,
        expected_digest=expected_digest,
        expected_source_manifest_sha256=expected_source_manifest_sha256,
    )

    schema_version = int(meta["schema_version"])
    for rel in required_members_for_schema(schema_version):
        path = dest / rel
        if path.is_symlink():
            raise BundleVerifyError(f"symlink rejected for required member: {rel}")
        if not path.is_file():
            raise BundleVerifyError(f"missing required member: {rel}")

    if (dest / "compose/docker-compose.production.yml").exists():
        raise BundleVerifyError("production overlay must not be present")

    for path in dest.rglob("*"):
        if path.is_symlink():
            raise BundleVerifyError(f"symlink present in release directory: {path}")

    verify_file_checksums_map(dest, meta["file_checksums"])

    compose_base = dest / "compose/docker-compose.base.yml"
    compose_staging = dest / "compose/docker-compose.staging.yml"
    if not compose_base.is_file() or not compose_staging.is_file():
        raise BundleVerifyError("staging compose overlays missing")

    if require_deploy_version:
        dv = dest / "DEPLOY_VERSION"
        if not dv.is_file():
            raise BundleVerifyError("DEPLOY_VERSION missing")
        try:
            deploy_version = json.loads(dv.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BundleVerifyError("DEPLOY_VERSION is not valid JSON") from exc
        if deploy_version.get("release_id") != meta["release_id"]:
            raise BundleVerifyError("DEPLOY_VERSION release_id mismatch")
        if deploy_version.get("image_digest") != meta["image_digest"]:
            raise BundleVerifyError("DEPLOY_VERSION image_digest mismatch")
        if deploy_version.get("git_sha") != meta["git_sha"]:
            raise BundleVerifyError("DEPLOY_VERSION git_sha mismatch")

    return meta


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
    expected_git_sha: str | None = None,
    expected_image_repository: str | None = None,
    expected_source_manifest_sha256: str | None = None,
) -> dict:
    return verify_release_directory(
        dest,
        expected_release_id=expected_release_id,
        expected_git_sha=expected_git_sha,
        expected_image_repository=expected_image_repository,
        expected_digest=expected_digest,
        expected_source_manifest_sha256=expected_source_manifest_sha256,
        require_deploy_version=False,
    )


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
    parser.add_argument("tarball", type=Path, nargs="?")
    parser.add_argument("--checksum", default=None)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--image-digest", default=None)
    parser.add_argument(
        "--extract-to",
        type=Path,
        default=None,
        help="When set, safely extract into this release directory after validation.",
    )
    parser.add_argument(
        "--verify-release-dir",
        type=Path,
        default=None,
        help="When set, verify an already-extracted/retained release directory.",
    )
    parser.add_argument("--git-sha", default=None)
    parser.add_argument("--image-repository", default=None)
    parser.add_argument("--source-manifest-sha256", default=None)
    parser.add_argument("--require-deploy-version", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify_release_dir is not None:
            meta = verify_release_directory(
                args.verify_release_dir,
                expected_release_id=args.release_id,
                expected_git_sha=args.git_sha,
                expected_image_repository=args.image_repository,
                expected_digest=args.image_digest,
                expected_source_manifest_sha256=args.source_manifest_sha256,
                require_deploy_version=args.require_deploy_version,
            )
            print(
                "ok: release_dir={rid} digest={digest} schema={schema}".format(
                    rid=meta["release_id"],
                    digest=meta["image_digest"],
                    schema=meta["schema_version"],
                )
            )
            return 0
        if args.tarball is None:
            raise BundleVerifyError("tarball path is required unless --verify-release-dir is set")
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
