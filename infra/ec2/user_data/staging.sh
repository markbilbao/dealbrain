#!/bin/bash
# DealBrain staging EC2 user_data bootstrap (Sprint 25b.3).
# Amazon Linux 2023 — idempotent, no secrets, no GitHub credentials.
#
# Installs packages, directory layout, and a thin fixed SSM entrypoint that
# acquires the deploy lock, safely extracts the release bundle, then runs the
# release orchestrator.
set -euo pipefail

LOG=/var/log/dealbrain/bootstrap.log
mkdir -p /var/log/dealbrain
exec >>"$LOG" 2>&1

echo "=== dealbrain staging bootstrap start $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Directories
install -d -o root -g root -m 0755 /opt/dealbrain
install -d -o root -g root -m 0755 /opt/dealbrain/releases
install -d -o root -g root -m 0700 /opt/dealbrain/runtime
install -d -o root -g root -m 0755 /opt/dealbrain/locks
install -d -o root -g root -m 0755 /opt/dealbrain/bin
install -d -o root -g root -m 0755 /var/log/dealbrain

# Packages (AL2023)
dnf -y update || true
dnf -y install \
  docker \
  awscli \
  jq \
  curl \
  python3 \
  tar \
  gzip \
  findutils \
  util-linux \
  coreutils

# Docker Compose plugin — AL2023 package only; fail closed (no unsigned binary).
if ! docker compose version >/dev/null 2>&1; then
  dnf -y install docker-compose-plugin
fi
docker compose version >/dev/null

systemctl enable docker
systemctl start docker

command -v docker >/dev/null
docker --version
docker compose version
command -v aws >/dev/null
aws --version
command -v jq >/dev/null
command -v curl >/dev/null
command -v python3 >/dev/null
command -v flock >/dev/null
command -v timeout >/dev/null

# Fixed safe-extract helper (mirrors scripts/deploy/verify_staging_bundle.py contract).
# Updated from release bundles after first successful extract.
cat >/opt/dealbrain/bin/verify_staging_bundle.py << 'SAFEEXTRACT'
#!/usr/bin/env python3
"""Bootstrap copy of staging bundle verifier (safe extract only)."""
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

FORBIDDEN = (
    "docker-compose.production.yml",
    ".env",
    "terraform.tfstate",
    ".git/",
)
ALLOWED_TOP_LEVEL = frozenset({"compose", "bin", "manifest", "bundle-meta.json"})
REQUIRED_MEMBERS = (
    "compose/docker-compose.base.yml",
    "compose/docker-compose.staging.yml",
    "bin/dealbrain-staging-deploy.sh",
    "bin/assemble-runtime-env.py",
    "bin/ghcr-login.sh",
    "bin/verify-staging.sh",
    "manifest/release-manifest.json",
    "bundle-meta.json",
)


class BundleVerifyError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_archive_members(tar: tarfile.TarFile):
    members = tar.getmembers()
    if not members:
        raise BundleVerifyError("archive is empty")
    seen = set()
    for member in members:
        name = member.name
        if not name or name == ".":
            raise BundleVerifyError(f"invalid archive member name: {name!r}")
        if name in seen:
            raise BundleVerifyError(f"duplicate archive member: {name}")
        seen.add(name)
        if name.startswith("/") or name.startswith("\\") or Path(name).is_absolute():
            raise BundleVerifyError(f"absolute path rejected: {name}")
        parts = Path(name).parts
        if ".." in parts:
            raise BundleVerifyError(f"path traversal rejected: {name}")
        if parts[0] not in ALLOWED_TOP_LEVEL:
            raise BundleVerifyError(f"unexpected top-level member: {name}")
        if member.issym() or member.islnk():
            raise BundleVerifyError(f"symlink/hardlink rejected: {name}")
        if member.isdev() or member.ischr() or member.isblk() or member.isfifo():
            raise BundleVerifyError(f"special file rejected: {name}")
        if not (member.isfile() or member.isdir()):
            raise BundleVerifyError(f"unsupported archive member type: {name}")
        for forbidden in FORBIDDEN:
            if forbidden in name:
                raise BundleVerifyError(f"forbidden member in bundle: {name}")
    return members


def _extract_members(tar, dest: Path, members) -> None:
    dest = dest.resolve()
    for member in members:
        target = (dest / member.name).resolve()
        try:
            target.relative_to(dest)
        except ValueError as exc:
            raise BundleVerifyError(f"extract path escaped destination: {member.name}") from exc
        tar.extract(member, path=dest, filter="data")


def extract_validated_bundle(tarball, dest_dir, *, expected_checksum, expected_release_id=None, expected_digest=None):
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
        meta_path = tmp_root / "bundle-meta.json"
        if not meta_path.is_file():
            raise BundleVerifyError("bundle-meta.json missing")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if expected_release_id and meta.get("release_id") != expected_release_id:
            raise BundleVerifyError("release_id mismatch")
        if expected_digest and meta.get("image_digest") != expected_digest:
            raise BundleVerifyError("image_digest mismatch")
        for rel in REQUIRED_MEMBERS:
            if not (tmp_root / rel).is_file():
                raise BundleVerifyError(f"missing required member: {rel}")
        if (tmp_root / "compose/docker-compose.production.yml").exists():
            raise BundleVerifyError("production overlay must not be present")
        for path in tmp_root.rglob("*"):
            if path.is_symlink():
                raise BundleVerifyError(f"symlink present after extract: {path}")
        for rel, expected in meta.get("file_checksums", {}).items():
            path = tmp_root / rel
            if not path.is_file():
                raise BundleVerifyError(f"checksum map references missing file: {rel}")
            if rel == "bundle-meta.json":
                continue
            if _sha256_file(path) != expected:
                raise BundleVerifyError(f"file checksum mismatch for {rel}")
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
    os.chmod(dest_dir, 0o755)
    return {"checksum": actual, "meta": meta}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tarball", type=Path)
    parser.add_argument("--checksum", required=True)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--image-digest", default=None)
    parser.add_argument("--extract-to", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = extract_validated_bundle(
            args.tarball,
            args.extract_to,
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
SAFEEXTRACT
chmod 0755 /opt/dealbrain/bin/verify_staging_bundle.py

# Thin fixed SSM entrypoint: lock → safe extract → run release orchestrator.
# Full deploy logic lives in the release bundle (scripts/deploy/host/).
cat >/opt/dealbrain/bin/dealbrain-staging-deploy.sh << 'ENTRYPOINT'
#!/bin/bash
set -euo pipefail
set +x

die() { echo "[dealbrain-staging-entrypoint] ERROR: $*" >&2; exit 1; }

: "${DEALBRAIN_RELEASE_ID:?}"
: "${DEALBRAIN_GIT_SHA:?}"
: "${DEALBRAIN_IMAGE_REPOSITORY:?}"
: "${DEALBRAIN_IMAGE_DIGEST:?}"
: "${DEALBRAIN_BUNDLE_CHECKSUM:?}"
: "${DEALBRAIN_DEPLOY_RUN_ID:?}"
: "${DEALBRAIN_BUNDLE_BUCKET:?}"
: "${DEALBRAIN_BUNDLE_KEY:?}"

[[ -f /opt/dealbrain/bootstrap.ok ]] || die "bootstrap.ok missing"

RELEASE_ID="$DEALBRAIN_RELEASE_ID"
BUNDLE_BUCKET="$DEALBRAIN_BUNDLE_BUCKET"
BUNDLE_KEY="$DEALBRAIN_BUNDLE_KEY"
BUNDLE_CHECKSUM="$DEALBRAIN_BUNDLE_CHECKSUM"
IMAGE_DIGEST="$DEALBRAIN_IMAGE_DIGEST"
RELEASE_DIR="/opt/dealbrain/releases/${RELEASE_ID}"
LOCK_DIR="/opt/dealbrain/locks"
LOCK_FILE="${LOCK_DIR}/staging-deploy.lock"

TOKEN="$(curl -sS -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")"
REGION="$(curl -sS -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/meta-data/placement/region)"

# Acquire flock before download/extract (inherited by child via DEALBRAIN_LOCK_HELD).
mkdir -p "$LOCK_DIR"
exec 9>"$LOCK_FILE"
flock -w 30 9 || die "could not acquire staging deploy lock within 30s"
export DEALBRAIN_LOCK_HELD=1

ORCH="${RELEASE_DIR}/bin/dealbrain-staging-deploy.sh"
if [[ -x "$ORCH" && "${DEALBRAIN_SKIP_FETCH:-}" == "1" ]]; then
  # Hold lock in this process; run orchestrator as child (do not exec).
  bash "$ORCH"
  exit $?
fi

TMP_BUNDLE="$(mktemp /tmp/dealbrain-bundle.XXXXXX.tar.gz)"
trap 'rm -f "$TMP_BUNDLE"' EXIT
aws s3 cp "s3://${BUNDLE_BUCKET}/${BUNDLE_KEY}" "$TMP_BUNDLE" --region "$REGION"
ACTUAL="$(sha256sum "$TMP_BUNDLE" | awk '{print $1}')"
[[ "$ACTUAL" == "$BUNDLE_CHECKSUM" ]] || die "bundle checksum mismatch"

[[ -x /opt/dealbrain/bin/verify_staging_bundle.py || -f /opt/dealbrain/bin/verify_staging_bundle.py ]] \
  || die "verify_staging_bundle.py missing"
python3 /opt/dealbrain/bin/verify_staging_bundle.py "$TMP_BUNDLE" \
  --checksum "$BUNDLE_CHECKSUM" \
  --release-id "$RELEASE_ID" \
  --image-digest "$IMAGE_DIGEST" \
  --extract-to "$RELEASE_DIR"
rm -f "$TMP_BUNDLE"
trap - EXIT

[[ -x "${RELEASE_DIR}/bin/dealbrain-staging-deploy.sh" ]] || die "orchestrator missing in bundle"

# Refresh fixed helpers from release for subsequent deploys.
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/dealbrain-staging-deploy.sh" \
  /opt/dealbrain/bin/dealbrain-staging-deploy.orchestrator.sh
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/verify_staging_bundle.py" \
  /opt/dealbrain/bin/verify_staging_bundle.py 2>/dev/null || true

# Do NOT update /opt/dealbrain/current here — orchestrator updates it only after health gates.
export DEALBRAIN_BUNDLE_ALREADY_EXTRACTED=1
bash "${RELEASE_DIR}/bin/dealbrain-staging-deploy.sh"
exit $?
ENTRYPOINT
chmod 0755 /opt/dealbrain/bin/dealbrain-staging-deploy.sh

touch /opt/dealbrain/bootstrap.ok
chmod 0644 /opt/dealbrain/bootstrap.ok
echo "=== dealbrain staging bootstrap ok $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
