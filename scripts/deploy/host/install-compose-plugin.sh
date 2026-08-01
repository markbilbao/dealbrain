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
