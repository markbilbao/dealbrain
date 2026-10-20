#!/usr/bin/env bash
# Install pinned Trivy 0.76.0 for linux/amd64 from the official GitHub release.
# The archive SHA-256 is checked against the published checksum file and the
# pin in this script before tar extracts anything. No sudo. No unpinned installer.
set -euo pipefail

TRIVY_VERSION="0.76.0"
TRIVY_LINUX_AMD64_SHA256="e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7"
ASSET="trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
CHECKSUMS="trivy_${TRIVY_VERSION}_checksums.txt"
BASE_URL="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "install_trivy.sh: refusing to install; this pin is the official Linux-64bit archive" >&2
  exit 1
fi

for tool in curl sha256sum tar grep; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "install_trivy.sh: missing required tool: $tool" >&2
    exit 1
  fi
done

DEST="${TRIVY_INSTALL_DIR:-${RUNNER_TEMP:-/tmp}/trivy-${TRIVY_VERSION}}"
mkdir -p "$DEST"
WORK="$(mktemp -d)"
cleanup() {
  rm -rf "$WORK"
}
trap cleanup EXIT

curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  "${BASE_URL}/${CHECKSUMS}" -o "${WORK}/${CHECKSUMS}"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  "${BASE_URL}/${ASSET}" -o "${WORK}/${ASSET}"

tr -d '\r' < "${WORK}/${CHECKSUMS}" > "${WORK}/checksums.normalized"
EXPECTED="${TRIVY_LINUX_AMD64_SHA256}  ${ASSET}"
if ! grep -qxF "$EXPECTED" "${WORK}/checksums.normalized"; then
  echo "install_trivy.sh: published checksums do not contain the pinned SHA-256 for ${ASSET}" >&2
  exit 1
fi

printf '%s\n' "$EXPECTED" > "${WORK}/expected.sha256"
(
  cd "$WORK"
  sha256sum -c expected.sha256
)

while IFS= read -r member; do
  if [[ "$member" == /* || "$member" == *..* ]]; then
    echo "install_trivy.sh: refusing archive member: ${member}" >&2
    exit 1
  fi
done < <(tar -tzf "${WORK}/${ASSET}")

tar -xzf "${WORK}/${ASSET}" -C "$DEST" trivy
chmod 0755 "${DEST}/trivy"

if ! "${DEST}/trivy" --version | grep -Eq "^Version:[[:space:]]+${TRIVY_VERSION}$"; then
  echo "install_trivy.sh: extracted binary is not Trivy ${TRIVY_VERSION}" >&2
  exit 1
fi

if [[ -n "${GITHUB_PATH:-}" ]]; then
  printf '%s\n' "$DEST" >> "$GITHUB_PATH"
fi

echo "trivy_install: OK version=${TRIVY_VERSION} sha256=${TRIVY_LINUX_AMD64_SHA256}"
