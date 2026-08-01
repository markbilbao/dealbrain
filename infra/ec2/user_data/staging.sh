#!/bin/bash
# DealBrain staging EC2 user_data bootstrap (Sprint 25b.3 / 25b.4c / 25b.5a).
# Amazon Linux 2023 — idempotent, no secrets, no GitHub credentials.
#
# Installs AL2023 packages, directory layout, signed Docker Compose plugin
# (Sprint 25b.5a), and a thin fixed SSM entrypoint that acquires the deploy
# lock, safely extracts the release bundle, then runs the release orchestrator.
#
# Compose is installed via scripts/deploy/host/install-compose-plugin.sh
# (embedded below): Docker Inc RHEL9 plugin RPM only, Amazon docker engine
# retained. Unsigned GitHub Compose binaries remain forbidden. bootstrap.ok
# is written only after `docker compose version` succeeds.
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

# Packages (AL2023 default repos only — fail closed on missing packages).
dnf -y update || true
# AL2023 ships curl-minimal; installing the full `curl` package conflicts and
# aborts bootstrap (bootstrap.ok never written). Prefer the preinstalled curl.
# Do NOT install docker-compose-plugin from AL2023 default repos (unavailable).
# Compose plugin is installed later via the reviewed Docker Inc signed path
# (install-compose-plugin.sh). Never install docker-ce / docker-ce-cli here.
dnf -y install \
  docker \
  awscli \
  jq \
  python3 \
  tar \
  gzip \
  findutils \
  util-linux \
  coreutils \
  gnupg2

systemctl enable docker
systemctl start docker

# Fail closed on bootstrap-owned runtime tools (Amazon engine + host utilities).
command -v docker >/dev/null
docker --version
rpm -q docker >/dev/null
command -v aws >/dev/null
aws --version
command -v jq >/dev/null
command -v curl >/dev/null
command -v python3 >/dev/null
command -v flock >/dev/null
command -v timeout >/dev/null
command -v gpg >/dev/null

# Sprint 25b.5a — signed Compose plugin install (fail-closed before bootstrap.ok).
# Source of truth: scripts/deploy/host/install-compose-plugin.sh (embedded).
cat >/opt/dealbrain/bin/install-compose-plugin.sh << 'COMPOSEPLUGIN'
#!/bin/bash
# Sprint 25b.5a — install Docker Compose plugin on Amazon Linux 2023 (staging).
#
# Contract:
#   - Install ONLY docker-compose-plugin from Docker Inc RHEL 9 stable RPMs
#   - Keep Amazon Linux Docker Engine (`docker` RPM); never install docker-ce*
#   - Never pass dnf allowerasing / package-erasure overrides
#   - Verify Docker Inc GPG fingerprint before trusting/importing the key
#   - Require exactly one primary fingerprint; exact pin match before rpm --import
#   - Repo: gpgcheck=1, repo_gpgcheck=1, includepkgs=docker-compose-plugin
#   - After enable: every exit path restores enabled=0 + lockdown knobs (fail-safe)
#   - Idempotent; fail-closed (non-zero exit on any failed assert)
#
# Forbidden: docker-ce / docker-ce-cli / containerd.io / docker-buildx-plugin
# install targets, Docker convenience install script, unsigned GitHub binaries.
set -euo pipefail
set +x

die() { echo "[install-compose-plugin] ERROR: $*" >&2; exit 1; }
log() { echo "[install-compose-plugin] $*"; }

EXPECTED_DOCKER_GPG_FINGERPRINT="060A61C51B558A7F742B77AAC52FEB6B621E9F35"
# Spaced form (human-readable pin from Docker Inc docs / design review):
# 060A 61C5 1B55 8A7F 742B 77AA C52F EB6B 621E 9F35
DOCKER_GPG_URL="https://download.docker.com/linux/rhel/gpg"
DOCKER_GPG_PATH="/etc/pki/rpm-gpg/RPM-GPG-KEY-docker"
REPO_FILE="/etc/yum.repos.d/docker-ce.repo"
REPO_ID="docker-ce-stable"
PLUGIN_PKG="docker-compose-plugin"

# Set once the Docker Inc repo has been (or is about to be) written enabled=1.
# EXIT trap restores the locked disabled configuration on every exit path.
_DOCKER_REPO_ENABLE_ACTIVE=0

normalize_fp() {
  # Strip spaces/colons; uppercase for stable compare.
  printf '%s' "$1" | tr -d '[:space:]:' | tr '[:lower:]' '[:upper:]'
}

assert_amazon_engine() {
  rpm -q docker >/dev/null 2>&1 || die "Amazon Linux docker RPM missing"
  if rpm -q docker-ce >/dev/null 2>&1; then
    die "docker-ce is installed (Amazon engine must be retained)"
  fi
  if rpm -q docker-ce-cli >/dev/null 2>&1; then
    die "docker-ce-cli is installed (Amazon engine must be retained)"
  fi
}

repo_locked_disabled() {
  [[ -f "$REPO_FILE" ]] || return 1
  grep -q "^\\[${REPO_ID}\\]" "$REPO_FILE" || return 1
  grep -Eq '^enabled=0([[:space:]]|$)' "$REPO_FILE" || return 1
  grep -Eq "^includepkgs=${PLUGIN_PKG}([[:space:]]|$)" "$REPO_FILE" || return 1
  grep -Eq '^gpgcheck=1([[:space:]]|$)' "$REPO_FILE" || return 1
  grep -Eq '^repo_gpgcheck=1([[:space:]]|$)' "$REPO_FILE" || return 1
}

already_satisfied() {
  docker compose version >/dev/null 2>&1 || return 1
  rpm -q "$PLUGIN_PKG" >/dev/null 2>&1 || return 1
  assert_amazon_engine
  repo_locked_disabled || return 1
  return 0
}

write_docker_repo() {
  local enabled="${1:?enabled 0|1 required}"
  [[ "$enabled" == "0" || "$enabled" == "1" ]] || die "invalid repo enabled value: ${enabled}"
  cat >"$REPO_FILE" <<EOF
[${REPO_ID}]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/rhel/9/\$basearch/stable
enabled=${enabled}
gpgcheck=1
repo_gpgcheck=1
gpgkey=file://${DOCKER_GPG_PATH}
includepkgs=${PLUGIN_PKG}
EOF
  chmod 0644 "$REPO_FILE"
}

# Best-effort restore used by EXIT trap. Must not call die/exit (re-entrancy).
restore_repo_locked_disabled() {
  cat >"$REPO_FILE" <<EOF
[${REPO_ID}]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/rhel/9/\$basearch/stable
enabled=0
gpgcheck=1
repo_gpgcheck=1
gpgkey=file://${DOCKER_GPG_PATH}
includepkgs=${PLUGIN_PKG}
EOF
  chmod 0644 "$REPO_FILE"
}

_cleanup_docker_repo() {
  local status=$?
  # Disarm first so nested failures cannot recurse.
  trap - EXIT
  if [[ "${_DOCKER_REPO_ENABLE_ACTIVE}" -eq 1 ]]; then
    local cleanup_rc=0
    set +e
    restore_repo_locked_disabled
    cleanup_rc=$?
    set -e
    if [[ "$cleanup_rc" -ne 0 ]]; then
      echo "[install-compose-plugin] ERROR: failed to restore locked disabled Docker Inc repo (rc=${cleanup_rc})" >&2
      # Never convert an original failure into success; only escalate success→failure.
      if [[ "$status" -eq 0 ]]; then
        status=1
      fi
    fi
  fi
  exit "$status"
}

extract_primary_fingerprints() {
  # Emit one primary-key fingerprint per pub: block (ignore subkey fpr: lines).
  gpg --show-keys --with-colons "$1" | awk -F: '
    /^pub:/ { want=1; next }
    /^sub:/ { want=0; next }
    /^fpr:/ {
      if (want && $10 != "") {
        print $10
        want=0
      }
      next
    }
  '
}

verify_and_import_docker_gpg() {
  command -v curl >/dev/null || die "curl missing"
  if ! command -v gpg >/dev/null 2>&1; then
    log "installing gnupg2 from AL2023 default repos (fingerprint gate)"
    dnf -y install gnupg2
    command -v gpg >/dev/null || die "gpg missing after gnupg2 install"
  fi

  local tmp_key
  tmp_key="$(mktemp)"
  curl -fsSL "$DOCKER_GPG_URL" -o "$tmp_key" || {
    rm -f "$tmp_key"
    die "Docker GPG key download failed"
  }
  [[ -s "$tmp_key" ]] || {
    rm -f "$tmp_key"
    die "Docker GPG key download empty"
  }

  local fps_raw fps_count actual expected
  fps_raw="$(extract_primary_fingerprints "$tmp_key" || true)"
  if [[ -z "${fps_raw}" ]]; then
    rm -f "$tmp_key"
    die "could not parse Docker GPG fingerprint (empty or malformed key material)"
  fi
  fps_count="$(printf '%s\n' "$fps_raw" | grep -c .)"
  if [[ "$fps_count" -ne 1 ]]; then
    rm -f "$tmp_key"
    die "expected exactly one primary Docker GPG fingerprint, got ${fps_count}"
  fi

  actual="$(normalize_fp "$fps_raw")"
  [[ "$actual" =~ ^[0-9A-F]{40}$ ]] || {
    rm -f "$tmp_key"
    die "malformed Docker GPG fingerprint: ${actual}"
  }
  expected="$(normalize_fp "$EXPECTED_DOCKER_GPG_FINGERPRINT")"
  if [[ "$actual" != "$expected" ]]; then
    rm -f "$tmp_key"
    die "Docker GPG fingerprint mismatch: got ${actual}, expected ${expected}"
  fi

  install -o root -g root -m 0644 "$tmp_key" "$DOCKER_GPG_PATH"
  rm -f "$tmp_key"
  rpm --import "$DOCKER_GPG_PATH"
  log "Docker GPG fingerprint verified and imported (${actual})"
}

install_plugin() {
  # Explicit package name only — never docker-ce / docker-ce-cli / meta packages.
  # Do not pass dnf package-erasure overrides (forbidden).
  dnf -y install "$PLUGIN_PKG"
}

final_asserts() {
  command -v docker >/dev/null || die "docker binary missing"
  docker --version >/dev/null || die "docker --version failed"
  assert_amazon_engine
  rpm -q "$PLUGIN_PKG" >/dev/null 2>&1 || die "${PLUGIN_PKG} RPM not installed"
  docker compose version >/dev/null || die "docker compose version failed"
  docker compose version
  repo_locked_disabled || die "${REPO_FILE} must be enabled=0 with includepkgs=${PLUGIN_PKG} gpgcheck=1 repo_gpgcheck=1"
  log "ok: compose plugin present; Amazon docker retained; Docker Inc repo disabled"
}

main() {
  [[ "$(id -u)" -eq 0 ]] || die "must run as root"

  # Engine must already be installed from AL2023 repos by staging user_data.
  rpm -q docker >/dev/null 2>&1 || die "Amazon Linux docker RPM required before compose plugin install"
  command -v docker >/dev/null || die "docker binary missing"
  if ! systemctl is-active --quiet docker; then
    systemctl enable docker
    systemctl start docker
  fi

  if already_satisfied; then
    log "idempotent skip: plugin + Amazon engine + locked disabled repo already OK"
    docker compose version
    exit 0
  fi

  verify_and_import_docker_gpg

  # From this point, every exit path must leave the repo locked and disabled.
  trap _cleanup_docker_repo EXIT
  _DOCKER_REPO_ENABLE_ACTIVE=1
  write_docker_repo 1
  install_plugin
  write_docker_repo 0
  final_asserts
  # EXIT trap re-asserts locked disabled state and preserves success status.
}

main "$@"

COMPOSEPLUGIN
chmod 0755 /opt/dealbrain/bin/install-compose-plugin.sh
/opt/dealbrain/bin/install-compose-plugin.sh

# Hard gate: Compose must succeed before bootstrap.ok (fail-closed).
docker compose version >/dev/null
docker compose version
rpm -q docker-compose-plugin >/dev/null
rpm -q docker >/dev/null
if rpm -q docker-ce >/dev/null 2>&1; then
  echo "ERROR: docker-ce installed — aborting bootstrap" >&2
  exit 1
fi
if rpm -q docker-ce-cli >/dev/null 2>&1; then
  echo "ERROR: docker-ce-cli installed — aborting bootstrap" >&2
  exit 1
fi

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
