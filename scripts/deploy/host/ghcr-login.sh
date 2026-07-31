#!/bin/bash
# Host-side GHCR login using staging Secrets Manager classic PAT (Sprint 25b.3).
# Token never echoed; docker login uses --password-stdin.
set -euo pipefail
set +x

REGION=""
SECRET_ID="dealbrain/staging/ghcr_pull"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --secret-id) SECRET_ID="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$REGION" ]] || { echo "ERROR: --region required" >&2; exit 1; }
case "$SECRET_ID" in
  *production*) echo "ERROR: refusing production GHCR secret" >&2; exit 1 ;;
esac

RAW="$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ID" \
  --region "$REGION" \
  --query SecretString \
  --output text)"

USERNAME="$(printf '%s' "$RAW" | jq -r '.username // empty')"
TOKEN="$(printf '%s' "$RAW" | jq -r '.token // empty')"
unset RAW

[[ -n "$USERNAME" ]] || { echo "ERROR: ghcr_pull.username missing" >&2; exit 1; }
[[ -n "$TOKEN" ]] || { echo "ERROR: ghcr_pull.token missing" >&2; exit 1; }

printf '%s' "$TOKEN" | docker login ghcr.io -u "$USERNAME" --password-stdin
unset TOKEN

# Harden docker config permissions
if [[ -f /root/.docker/config.json ]]; then
  chmod 0600 /root/.docker/config.json
  chown root:root /root/.docker/config.json
fi

echo "ok: ghcr.io login succeeded (credentials redacted)"
