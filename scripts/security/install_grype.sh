#!/usr/bin/env bash
# Install pinned Grype 0.120.1 for linux/amd64 from the official GitHub release.
# The archive SHA-256 is checked against the published checksum file and the
# pin in this script before tar extracts anything. No sudo. No unpinned installer.
set -euo pipefail

GRYPE_VERSION="0.120.1"
GRYPE_LINUX_AMD64_SHA256="0a9ee97ef5ae2ee953b0a80098105052e846cdbe319a57d808b519c33cd1343d"
ASSET="grype_${GRYPE_VERSION}_linux_amd64.tar.gz"
CHECKSUMS="grype_${GRYPE_VERSION}_checksums.txt"
BASE_URL="https://github.com/anchore/grype/releases/download/v${GRYPE_VERSION}"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "install_grype.sh: refusing to install; this pin is the official linux_amd64 archive" >&2
  exit 1
fi

for tool in curl sha256sum tar grep; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "install_grype.sh: missing required tool: $tool" >&2
    exit 1
  fi
done

DEST="${GRYPE_INSTALL_DIR:-${RUNNER_TEMP:-/tmp}/grype-${GRYPE_VERSION}}"
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
EXPECTED="${GRYPE_LINUX_AMD64_SHA256}  ${ASSET}"
if ! grep -qxF "$EXPECTED" "${WORK}/checksums.normalized"; then
  echo "install_grype.sh: published checksums do not contain the pinned SHA-256 for ${ASSET}" >&2
  exit 1
fi

printf '%s\n' "$EXPECTED" > "${WORK}/expected.sha256"
(
  cd "$WORK"
  sha256sum -c expected.sha256
)

while IFS= read -r member; do
  if [[ "$member" == /* || "$member" == *..* ]]; then
    echo "install_grype.sh: refusing archive member: ${member}" >&2
    exit 1
  fi
done < <(tar -tzf "${WORK}/${ASSET}")

tar -xzf "${WORK}/${ASSET}" -C "$DEST" grype
chmod 0755 "${DEST}/grype"

if ! "${DEST}/grype" version | grep -Eq "^Version:[[:space:]]+${GRYPE_VERSION}$"; then
  echo "install_grype.sh: extracted binary is not Grype ${GRYPE_VERSION}" >&2
  exit 1
fi

if [[ -n "${GITHUB_PATH:-}" ]]; then
  printf '%s\n' "$DEST" >> "$GITHUB_PATH"
fi

echo "grype_install: OK version=${GRYPE_VERSION} sha256=${GRYPE_LINUX_AMD64_SHA256}"
