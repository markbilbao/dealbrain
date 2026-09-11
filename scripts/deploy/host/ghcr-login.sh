#!/bin/bash
# Host-side GHCR login using Secrets Manager classic PAT.
# Token never echoed; docker login uses --password-stdin.
# Staging default refuses production secrets. Production must pass
# --allow-production with dealbrain/production/ghcr_pull.
set -euo pipefail
set +x

REGION=""
SECRET_ID="dealbrain/staging/ghcr_pull"
ALLOW_PRODUCTION=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --secret-id) SECRET_ID="$2"; shift 2 ;;
    --allow-production) ALLOW_PRODUCTION=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$REGION" ]] || { echo "ERROR: --region required" >&2; exit 1; }
if [[ "$ALLOW_PRODUCTION" -eq 1 ]]; then
  case "$SECRET_ID" in
    dealbrain/production/ghcr_pull) ;;
    *) echo "ERROR: production GHCR login requires dealbrain/production/ghcr_pull" >&2; exit 1 ;;
  esac
  case "$SECRET_ID" in
    *staging*) echo "ERROR: refusing staging GHCR secret on production host" >&2; exit 1 ;;
  esac
else
  case "$SECRET_ID" in
    *production*) echo "ERROR: refusing production GHCR secret" >&2; exit 1 ;;
  esac
fi

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
