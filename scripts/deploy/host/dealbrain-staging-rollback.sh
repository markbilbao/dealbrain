#!/bin/bash
# DealBrain staging host rollback orchestrator (Sprint 25b.5).
# Invoked by SSM document DealBrain-StagingRollback via /opt/dealbrain/bin/.
# No image rebuild, no DB downgrade, no production path. Secrets never printed.
set -euo pipefail

umask 077

log() { echo "[dealbrain-staging-rollback] $*"; }
die() { echo "[dealbrain-staging-rollback] ERROR: $*" >&2; exit 1; }

set +x

require_env() {
  local name="$1"
  local value="${!name:-}"
  [[ -n "$value" ]] || die "missing required env: $name"
}

require_env DEALBRAIN_RELEASE_ID
require_env DEALBRAIN_GIT_SHA
require_env DEALBRAIN_IMAGE_REPOSITORY
require_env DEALBRAIN_IMAGE_DIGEST
require_env DEALBRAIN_BUNDLE_CHECKSUM
require_env DEALBRAIN_DEPLOY_RUN_ID
require_env DEALBRAIN_BUNDLE_BUCKET
require_env DEALBRAIN_BUNDLE_KEY
require_env DEALBRAIN_SOURCE_MANIFEST_SHA256

# Target identity (immutable authority from validated release-manifest).
TARGET_RELEASE_ID="$DEALBRAIN_RELEASE_ID"
TARGET_GIT_SHA="$DEALBRAIN_GIT_SHA"
IMAGE_REPOSITORY="$DEALBRAIN_IMAGE_REPOSITORY"
IMAGE_DIGEST="$DEALBRAIN_IMAGE_DIGEST"
BUNDLE_CHECKSUM="$DEALBRAIN_BUNDLE_CHECKSUM"
ROLLBACK_RUN_ID="$DEALBRAIN_DEPLOY_RUN_ID"
BUNDLE_BUCKET="$DEALBRAIN_BUNDLE_BUCKET"
BUNDLE_KEY="$DEALBRAIN_BUNDLE_KEY"
TARGET_MANIFEST_SHA256="$DEALBRAIN_SOURCE_MANIFEST_SHA256"

[[ "$TARGET_RELEASE_ID" =~ ^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]] || die "invalid ReleaseId"
[[ "$TARGET_GIT_SHA" =~ ^[0-9a-f]{40}$ ]] || die "invalid GitSha"
[[ "$IMAGE_REPOSITORY" =~ ^ghcr\.io/[a-z0-9._/-]+$ ]] || die "invalid ImageRepository"
[[ "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || die "invalid ImageDigest"
[[ "$BUNDLE_CHECKSUM" =~ ^[0-9a-f]{64}$ ]] || die "invalid BundleChecksum"
[[ "$ROLLBACK_RUN_ID" =~ ^[0-9]+$ ]] || die "invalid RollbackRunId"
[[ "$BUNDLE_BUCKET" =~ ^dealbrain-staging-release-artifacts-[0-9]{12}$ ]] || die "invalid BundleBucket"
[[ "$BUNDLE_KEY" == "releases/${TARGET_RELEASE_ID}/bundle.tar.gz" ]] || die "BundleKey/ReleaseId mismatch"
[[ "$TARGET_MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "invalid SourceManifestSha256"

case "$IMAGE_REPOSITORY" in
  *:latest|*:ci-latest|*:staging|*:production|*:main|*@*|*:* )
    die "mutable tag or digest suffix forbidden in ImageRepository"
    ;;
esac

ROOT=/opt/dealbrain
RELEASES_DIR="${ROOT}/releases"
TARGET_DIR="${RELEASES_DIR}/${TARGET_RELEASE_ID}"
RUNTIME_DIR="${ROOT}/runtime"
LOCK_DIR="${ROOT}/locks"
LOCK_FILE="${LOCK_DIR}/staging-deploy.lock"
LOCK_INFO="${LOCK_DIR}/staging-deploy.lock.info"
EVIDENCE_DIR="${ROOT}/runtime/evidence"
COMPOSE_PROJECT=dealbrain-staging
ENV_FILE="${RUNTIME_DIR}/staging.env"

[[ -f "${ROOT}/bootstrap.ok" ]] || die "bootstrap.ok missing — host not bootstrapped"
command -v docker >/dev/null || die "docker missing"
docker compose version >/dev/null || die "docker compose missing"
command -v aws >/dev/null || die "aws cli missing"
command -v jq >/dev/null || die "jq missing"
command -v python3 >/dev/null || die "python3 missing"
command -v flock >/dev/null || die "flock missing"

# Host tooling preflight — fail before mutation when rollback tooling is absent/outdated.
TOOLING_PREFLIGHT="${ROOT}/bin/verify_host_rollback_tooling.py"
[[ -f "$TOOLING_PREFLIGHT" ]] || die "verify_host_rollback_tooling.py missing on host"
python3 "$TOOLING_PREFLIGHT" \
  --bin-dir "${ROOT}/bin" \
  --capability-path "${ROOT}/bin/staging-host-tooling.json" \
  --expected-tooling-version "${DEALBRAIN_EXPECTED_TOOLING_VERSION:-25b.5}" \
  || die "host rollback tooling preflight failed"

TOKEN="$(curl -sS -X PUT 'http://169.254.169.254/latest/api/token' \
  -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')"
INSTANCE_ID="$(curl -sS -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id)"
REGION="$(curl -sS -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region)"
IDENTITY_DOC="$(curl -sS -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/dynamic/instance-identity/document)"
AWS_ACCOUNT_ID="$(echo "$IDENTITY_DOC" | jq -r '.accountId')"
[[ "$AWS_ACCOUNT_ID" =~ ^[0-9]{12}$ ]] || die "could not resolve aws account id"
[[ "$BUNDLE_BUCKET" == "dealbrain-staging-release-artifacts-${AWS_ACCOUNT_ID}" ]] \
  || die "bundle bucket/account mismatch"

ENV_TAG="$(aws ec2 describe-tags --region "$REGION" \
  --filters "Name=resource-id,Values=${INSTANCE_ID}" "Name=key,Values=Environment" \
  --query 'Tags[0].Value' --output text)"
ROLE_TAG="$(aws ec2 describe-tags --region "$REGION" \
  --filters "Name=resource-id,Values=${INSTANCE_ID}" "Name=key,Values=Role" \
  --query 'Tags[0].Value' --output text)"
PROJECT_TAG="$(aws ec2 describe-tags --region "$REGION" \
  --filters "Name=resource-id,Values=${INSTANCE_ID}" "Name=key,Values=Project" \
  --query 'Tags[0].Value' --output text)"
[[ "$ENV_TAG" == "staging" ]] || die "host Environment tag is not staging (got ${ENV_TAG})"
[[ "$ROLE_TAG" == "api-compose-host" ]] || die "host Role tag mismatch"
[[ "$PROJECT_TAG" == "dealbrain" ]] || die "host Project tag mismatch"
case "$ENV_TAG" in
  *production*) die "production identifier on staging host" ;;
esac

# shellcheck source=deploy_atomicity.sh
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATOMICITY_LIB=""
if [[ -f "${_SCRIPT_DIR}/deploy_atomicity.sh" ]]; then
  ATOMICITY_LIB="${_SCRIPT_DIR}/deploy_atomicity.sh"
elif [[ -f "${ROOT}/bin/deploy_atomicity.sh" ]]; then
  ATOMICITY_LIB="${ROOT}/bin/deploy_atomicity.sh"
fi
[[ -n "$ATOMICITY_LIB" && -f "$ATOMICITY_LIB" ]] || die "deploy_atomicity.sh missing"
# shellcheck disable=SC1090
source "$ATOMICITY_LIB"

RELEASE_ID="$TARGET_RELEASE_ID"
GIT_SHA="$TARGET_GIT_SHA"
RELEASE_DIR="$TARGET_DIR"

ROLLBACK_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FAILURE_REASON=""
FINAL_STATUS="failed"
MIGRATION_BEFORE=""
MIGRATION_AFTER=""
LOCAL_LIVE=""
LOCAL_READY=""
ALB_HEALTH=""
RUNNING_DIGEST_AFTER=""
SSM_COMMAND_ID=""
EVIDENCE_UPLOADED=0
RELEASE_COMMITTED=0
API_REPLACEMENT_OCCURRED=0
IN_ON_EXIT_EVIDENCE=0
SOURCE_RELEASE_ID=""
SOURCE_IMAGE_DIGEST=""
SOURCE_DIR=""
CURRENT_BEFORE=""
CURRENT_AFTER=""
PREVIOUS_BEFORE=""
PREVIOUS_AFTER=""
TARGET_RECORDED_MIGRATION=""
MIGRATION_AUTHORITY=""
POINTER_RESTORE_FAILED=0

parse_canonical_ssm_command_id_file() {
  local path="$1"
  python3 -c '
import sys, uuid
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_bytes()
if not raw:
    print("FAIL: ssm-command-id.txt is empty", file=sys.stderr); raise SystemExit(1)
try:
    text = raw.decode("ascii")
except UnicodeDecodeError:
    print("FAIL: ssm-command-id.txt is not ASCII", file=sys.stderr); raise SystemExit(1)
if text.endswith("\r\n"): body = text[:-2]
elif text.endswith("\n"): body = text[:-1]
else: body = text
if not body or any(ch in body for ch in " \t\r\n\v\f"):
    print("FAIL: ssm-command-id.txt must be exactly one canonical UUID line", file=sys.stderr)
    raise SystemExit(1)
parsed = uuid.UUID(body)
canonical = str(parsed)
if body != canonical:
    print("FAIL: ssm-command-id.txt is not canonical UUID form", file=sys.stderr)
    raise SystemExit(1)
sys.stdout.write(canonical)
' "$path"
}

discover_ssm_command_id() {
  local binder="evidence/${TARGET_RELEASE_ID}/${ROLLBACK_RUN_ID}/ssm-command-id.txt"
  local tmp err rc err_text aws_err_code temporary_absence=0
  tmp="$(mktemp)"; err="$(mktemp)"
  set +e
  aws s3 cp "s3://${BUNDLE_BUCKET}/${binder}" "$tmp" --region "$REGION" --only-show-errors \
    >/dev/null 2>"$err"
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    err_text="$(tr '\n' ' ' <"$err" 2>/dev/null | head -c 400 || true)"
    rm -f "$tmp" "$err"
    if [[ "$err_text" =~ An\ error\ occurred\ \(([A-Za-z0-9]+)\) ]]; then
      aws_err_code="${BASH_REMATCH[1]}"
    fi
    case "$aws_err_code" in
      NoSuchKey) temporary_absence=1 ;;
      404)
        if [[ "$err_text" == *"HeadObject"* || "$err_text" == *"GetObject"* ]]; then
          temporary_absence=1
        fi
        ;;
    esac
    if [[ "$temporary_absence" -eq 1 ]]; then
      echo ""
      return 0
    fi
    echo "ssm-command-id binder download failed (permanent; fail closed)" >&2
    echo ""
    return 1
  fi
  local found
  if found="$(parse_canonical_ssm_command_id_file "$tmp")"; then
    rm -f "$tmp" "$err"
    echo "$found"
    return 0
  fi
  rm -f "$tmp" "$err"
  echo "ssm-command-id binder content malformed (fail closed)" >&2
  echo ""
  return 1
}

SSM_BINDER_POLL_INTERVAL_SEC=2
SSM_BINDER_POLL_ATTEMPTS=60

resolve_ssm_command_id_for_evidence() {
  local discovered="" attempt
  if [[ -n "${SSM_COMMAND_ID:-}" ]]; then
    return 0
  fi
  for attempt in $(seq 1 "$SSM_BINDER_POLL_ATTEMPTS"); do
    if ! discovered="$(discover_ssm_command_id)"; then
      FAILURE_REASON="evidence_upload_ssm_command_id_binder_failed"
      die "ssm_command_id binder discovery failed permanently"
    fi
    if [[ -n "$discovered" ]]; then
      SSM_COMMAND_ID="$discovered"
      return 0
    fi
    sleep "$SSM_BINDER_POLL_INTERVAL_SEC"
  done
  FAILURE_REASON="evidence_upload_ssm_command_id_missing"
  die "ssm_command_id unavailable for rollback_ok evidence (binder wait expired)"
}

if ! SSM_COMMAND_ID="$(discover_ssm_command_id)"; then
  die "ssm_command_id binder discovery failed permanently at rollback start"
fi

_evidence_py() {
  if [[ -f "${TARGET_DIR}/bin/evidence.py" ]]; then
    echo "${TARGET_DIR}/bin/evidence.py"
  elif [[ -f "${ROOT}/bin/evidence.py" ]]; then
    echo "${ROOT}/bin/evidence.py"
  else
    return 1
  fi
}

normalize_alembic_revision() {
  local raw="$1"
  local evidence_py
  evidence_py="$(_evidence_py)" || die "evidence.py missing; cannot normalize alembic revision"
  DEALBRAIN_ALEMBIC_RAW="$raw" python3 - "$evidence_py" <<'PY'
import importlib.util, os, sys
path = sys.argv[1]
spec = importlib.util.spec_from_file_location("dealbrain_staging_evidence", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
try:
    print(mod.normalize_alembic_revision(os.environ.get("DEALBRAIN_ALEMBIC_RAW", "")))
except Exception as exc:
    print(f"invalid alembic revision output: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
PY
}

read_deploy_version_field() {
  local path="$1" field="$2"
  [[ -f "$path" ]] || return 1
  python3 - "$path" "$field" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
val = data.get(sys.argv[2]) or ""
print(val)
raise SystemExit(0 if val else 1)
PY
}

download_prior_evidence_candidates() {
  # Download every staging-deploy-evidence.json AND its .sha256 sidecar.
  # Selection/authority happens only after sidecar + identity validation.
  local dest="$1"
  local prefix="evidence/${TARGET_RELEASE_ID}/"
  local keys key base run_dir
  mkdir -p "$dest"
  keys="$(aws s3api list-objects-v2 --bucket "$BUNDLE_BUCKET" --prefix "$prefix" \
    --query "Contents[?ends_with(Key, 'staging-deploy-evidence.json')].Key" --output text 2>/dev/null || true)"
  [[ -n "$keys" && "$keys" != "None" ]] || return 1
  for key in $keys; do
    [[ "$key" == *"/staging-deploy-evidence.json" ]] || continue
    base="$(basename "$(dirname "$key")")"
    run_dir="${dest}/${base}"
    mkdir -p "$run_dir"
    if ! aws s3 cp "s3://${BUNDLE_BUCKET}/${key}" \
      "${run_dir}/staging-deploy-evidence.json" --region "$REGION" --only-show-errors >/dev/null 2>&1; then
      rm -rf "$run_dir"
      continue
    fi
    if ! aws s3 cp "s3://${BUNDLE_BUCKET}/${key}.sha256" \
      "${run_dir}/staging-deploy-evidence.json.sha256" --region "$REGION" --only-show-errors >/dev/null 2>&1; then
      # Missing sidecar — leave incomplete pair; selector rejects it.
      rm -f "${run_dir}/staging-deploy-evidence.json"
      rmdir "$run_dir" 2>/dev/null || true
      continue
    fi
  done
  # At least one JSON+sidecar pair must exist.
  compgen -G "${dest}/*/staging-deploy-evidence.json" >/dev/null \
    && compgen -G "${dest}/*/staging-deploy-evidence.json.sha256" >/dev/null
}

# --- BEGIN resolve_target_recorded_migration (test-extractable) ---
resolve_target_recorded_migration() {
  # Prefer DEPLOY_VERSION; fallback only to fully validated prior staging_ok evidence.
  # Assigns TARGET_RECORDED_MIGRATION and MIGRATION_AUTHORITY in the calling shell.
  # Must be invoked directly (not via command substitution) so both survive.
  local candidates_dir out resolver
  TARGET_RECORDED_MIGRATION=""
  MIGRATION_AUTHORITY=""
  candidates_dir="$(mktemp -d "${RUNTIME_DIR}/.prior-evidence.XXXXXX")"
  out="${RUNTIME_DIR}/rollback-migration-authority-${TARGET_RELEASE_ID}.json"
  resolver=""
  if [[ -f "${ROOT}/bin/resolve-rollback-migration.py" ]]; then
    resolver="${ROOT}/bin/resolve-rollback-migration.py"
  elif [[ -f "${TARGET_DIR}/bin/resolve-rollback-migration.py" ]]; then
    resolver="${TARGET_DIR}/bin/resolve-rollback-migration.py"
  else
    rm -rf "$candidates_dir"
    return 1
  fi
  if ! download_prior_evidence_candidates "$candidates_dir"; then
    # DEPLOY_VERSION-only path still allowed when migration_revision present.
    if [[ ! -f "${TARGET_DIR}/DEPLOY_VERSION" ]]; then
      rm -rf "$candidates_dir"
      return 1
    fi
  fi
  set +e
  python3 "$resolver" \
    --deploy-version "${TARGET_DIR}/DEPLOY_VERSION" \
    --prior-candidates-dir "$candidates_dir" \
    --release-id "$TARGET_RELEASE_ID" \
    --image-digest "$IMAGE_DIGEST" \
    --image-repository "$IMAGE_REPOSITORY" \
    --aws-account-id "$AWS_ACCOUNT_ID" \
    --aws-region "$REGION" \
    --ec2-instance-id "$INSTANCE_ID" \
    --source-manifest-sha256 "$TARGET_MANIFEST_SHA256" \
    --out "$out"
  local rc=$?
  set -e
  rm -rf "$candidates_dir"
  [[ "$rc" -eq 0 && -f "$out" ]] || return 1
  TARGET_RECORDED_MIGRATION="$(jq -r '.migration_revision // empty' "$out")"
  MIGRATION_AUTHORITY="$(jq -r '.authority // empty' "$out")"
  [[ -n "$TARGET_RECORDED_MIGRATION" ]] || return 1
  [[ -n "$MIGRATION_AUTHORITY" ]] || return 1
  case "$MIGRATION_AUTHORITY" in
    deploy_version|validated_prior_staging_evidence) ;;
    *)
      TARGET_RECORDED_MIGRATION=""
      MIGRATION_AUTHORITY=""
      return 1
      ;;
  esac
  return 0
}
# --- END resolve_target_recorded_migration (test-extractable) ---

capture_migration_revision() {
  local label="$1"
  local allow_empty="${2:-0}"
  local out rc normalized
  set +e
  out="$(compose --profile migrate run --rm --no-deps migrate alembic current 2>/dev/null | tr -d '\r')"
  rc=$?
  set -e
  if [[ $rc -ne 0 || -z "${out//[[:space:]]/}" ]]; then
    if [[ "$allow_empty" -eq 1 ]]; then
      echo ""
      return 0
    fi
    die "alembic current failed for migration_revision_${label}"
  fi
  normalized="$(normalize_alembic_revision "$out")" || die "migration_revision_${label} normalization failed"
  echo "$normalized"
}

# --- BEGIN restore_source_api (test-extractable) ---
restore_source_api() {
  # Best-effort restore of pre-rollback API after a failed post-replacement rollback.
  [[ -n "$SOURCE_DIR" && -d "$SOURCE_DIR" ]] || return 1
  local src_digest
  src_digest="$SOURCE_IMAGE_DIGEST"
  [[ -n "$src_digest" ]] || return 1
  # Prefer host-installed compose helpers; use source release compose files.
  local base="${SOURCE_DIR}/compose/docker-compose.base.yml"
  local staging="${SOURCE_DIR}/compose/docker-compose.staging.yml"
  [[ -f "$base" && -f "$staging" ]] || return 1
  export DEALBRAIN_IMAGE="${IMAGE_REPOSITORY}@${src_digest}"
  docker compose \
    --project-name "$COMPOSE_PROJECT" \
    --env-file "$ENV_FILE" \
    -f "$base" \
    -f "$staging" \
    up -d --force-recreate --no-deps api || return 1
  # Restore pointer pair to exact pre-rollback states (compensating restore).
  # Never leave current on unhealthy/unverified target.
  atomic_point_current "$SOURCE_DIR" || return 1
  if [[ -n "${PREVIOUS_BEFORE:-}" && -d "$PREVIOUS_BEFORE" ]]; then
    atomic_point_previous "$PREVIOUS_BEFORE" || return 1
  else
    rm -f "${ROOT}/previous" "${ROOT}/previous.new" || return 1
  fi
  return 0
}
# --- END restore_source_api (test-extractable) ---

write_evidence() {
  local finished duration out evidence_key
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  duration="$(python3 - <<PY
from datetime import datetime
start = datetime.strptime("${ROLLBACK_STARTED_AT}", "%Y-%m-%dT%H:%M:%SZ")
end = datetime.strptime("${finished}", "%Y-%m-%dT%H:%M:%SZ")
print(int((end - start).total_seconds()))
PY
)"
  CURRENT_AFTER="$(_atomicity_readlink_current || true)"
  PREVIOUS_AFTER="$(_atomicity_readlink_previous || true)"
  RUNNING_DIGEST_AFTER="$(_atomicity_running_api_digest 2>/dev/null || true)"
  mkdir -p "$EVIDENCE_DIR"
  out="${EVIDENCE_DIR}/staging-rollback-evidence-${TARGET_RELEASE_ID}-${ROLLBACK_RUN_ID}.json"

  local writer=""
  if [[ -f "${TARGET_DIR}/bin/write-staging-rollback-evidence.py" ]]; then
    writer="${TARGET_DIR}/bin/write-staging-rollback-evidence.py"
  elif [[ -f "${ROOT}/bin/write-staging-rollback-evidence.py" ]]; then
    writer="${ROOT}/bin/write-staging-rollback-evidence.py"
  else
    log "rollback evidence writer missing; cannot write evidence"
    return 1
  fi

  DEALBRAIN_EVIDENCE_OUT="$out" \
  DEALBRAIN_FINAL_STATUS="$FINAL_STATUS" \
  DEALBRAIN_FAILURE_REASON="$FAILURE_REASON" \
  DEALBRAIN_MIGRATION_BEFORE="$MIGRATION_BEFORE" \
  DEALBRAIN_MIGRATION_AFTER="$MIGRATION_AFTER" \
  DEALBRAIN_MIGRATION_AUTHORITY="${MIGRATION_AUTHORITY}" \
  DEALBRAIN_LOCAL_LIVE="$LOCAL_LIVE" \
  DEALBRAIN_LOCAL_READY="$LOCAL_READY" \
  DEALBRAIN_ALB_HEALTH="$ALB_HEALTH" \
  DEALBRAIN_STARTED_AT="$ROLLBACK_STARTED_AT" \
  DEALBRAIN_FINISHED_AT="$finished" \
  DEALBRAIN_DURATION="$duration" \
  DEALBRAIN_INSTANCE_ID="$INSTANCE_ID" \
  DEALBRAIN_REGION="$REGION" \
  DEALBRAIN_AWS_ACCOUNT_ID="$AWS_ACCOUNT_ID" \
  DEALBRAIN_SSM_COMMAND_ID="$SSM_COMMAND_ID" \
  DEALBRAIN_ROLLBACK_RUN_ID="$ROLLBACK_RUN_ID" \
  DEALBRAIN_SOURCE_RELEASE_ID="${SOURCE_RELEASE_ID}" \
  DEALBRAIN_SOURCE_IMAGE_DIGEST="${SOURCE_IMAGE_DIGEST}" \
  DEALBRAIN_TARGET_RELEASE_ID="$TARGET_RELEASE_ID" \
  DEALBRAIN_TARGET_IMAGE_DIGEST="$IMAGE_DIGEST" \
  DEALBRAIN_TARGET_GIT_SHA="$TARGET_GIT_SHA" \
  DEALBRAIN_TARGET_IMAGE_REPOSITORY="$IMAGE_REPOSITORY" \
  DEALBRAIN_TARGET_MANIFEST_SHA256="$TARGET_MANIFEST_SHA256" \
  DEALBRAIN_CURRENT_BEFORE="${CURRENT_BEFORE}" \
  DEALBRAIN_CURRENT_AFTER="${CURRENT_AFTER}" \
  DEALBRAIN_PREVIOUS_BEFORE="${PREVIOUS_BEFORE}" \
  DEALBRAIN_PREVIOUS_AFTER="${PREVIOUS_AFTER}" \
  DEALBRAIN_RUNNING_DIGEST_AFTER="${RUNNING_DIGEST_AFTER}" \
  DEALBRAIN_ASSUMED_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/dealbrain-staging-gha-deploy" \
  DEALBRAIN_ROLE_SESSION_NAME="gha-${ROLLBACK_RUN_ID}-staging-rollback" \
  python3 "$writer" || return 1

  evidence_key="evidence/${TARGET_RELEASE_ID}/${ROLLBACK_RUN_ID}/staging-rollback-evidence.json"
  aws s3 cp "$out" "s3://${BUNDLE_BUCKET}/${evidence_key}" --region "$REGION"
  if [[ -f "${out}.sha256" ]]; then
    aws s3 cp "${out}.sha256" "s3://${BUNDLE_BUCKET}/${evidence_key}.sha256" --region "$REGION"
  fi
  EVIDENCE_UPLOADED=1
  log "rollback evidence uploaded: s3://${BUNDLE_BUCKET}/${evidence_key}"
}

on_exit() {
  local code=$?
  if [[ $code -ne 0 ]]; then
    FINAL_STATUS="failed"
    if [[ -z "$FAILURE_REASON" ]]; then
      if [[ "${RELEASE_COMMITTED:-0}" -eq 1 ]]; then
        FAILURE_REASON="evidence_upload_failed"
      else
        FAILURE_REASON="host_script_exit_${code}"
      fi
    fi
    if [[ "$LOCAL_LIVE" == "true" && "$LOCAL_READY" == "true" && "$ALB_HEALTH" == "true" ]]; then
      case "$FAILURE_REASON" in
        post_gate_*|evidence_upload_*|deploy_version_*|symlink_*|pointer_*|post_replacement_*|release_alignment_*) ;;
        *) FAILURE_REASON="post_gate_${FAILURE_REASON}" ;;
      esac
    fi
  fi

  # Failure after API replacement: restore SOURCE where safely possible.
  # Never leave current pointing at an unhealthy target. Never claim rollback_ok.
  if [[ $code -ne 0 && "${RELEASE_COMMITTED:-0}" -eq 0 && "${API_REPLACEMENT_OCCURRED:-0}" -eq 1 ]]; then
    log "rollback failed after API replacement; attempting source restore"
    if restore_source_api; then
      log "restored source API and current/previous pointer pair"
    else
      log "CRITICAL: source restore failed (operator action required)"
      POINTER_RESTORE_FAILED=1
      FAILURE_REASON="post_replacement_source_restore_failed"
    fi
  fi

  if [[ "$EVIDENCE_UPLOADED" -eq 0 && "${IN_ON_EXIT_EVIDENCE:-0}" -eq 0 ]]; then
    IN_ON_EXIT_EVIDENCE=1
    if ! write_evidence; then
      log "rollback evidence write/upload failed (best-effort on error path)"
      # Success path already fails closed; error path must not claim zero via evidence.
      if [[ $code -eq 0 ]]; then
        code=1
      fi
    fi
  fi
  # No failure path may return zero while current points at unverified/unhealthy target.
  if [[ $code -eq 0 && "${FINAL_STATUS}" != "rollback_ok" ]]; then
    code=1
  fi
  if [[ "${POINTER_RESTORE_FAILED:-0}" -eq 1 ]]; then
    code=1
  fi
  exit "$code"
}
trap on_exit EXIT

# -------------------------------------------------------------------------
# 1. Shared flock with deploy (concurrency protection on host).
# -------------------------------------------------------------------------
if [[ "${DEALBRAIN_LOCK_HELD:-}" != "1" ]]; then
  mkdir -p "$LOCK_DIR"
  exec 9>"$LOCK_FILE"
  if ! flock -w 30 9; then
    die "could not acquire staging deploy/rollback lock within 30s"
  fi
fi
cat >"$LOCK_INFO" <<EOF
{"operation":"rollback","release_id":"${TARGET_RELEASE_ID}","rollback_run_id":"${ROLLBACK_RUN_ID}","pid":$$,"started_at":"${ROLLBACK_STARTED_AT}","instance_id":"${INSTANCE_ID}"}
EOF
chmod 0644 "$LOCK_INFO"
log "acquired flock for rollback ${TARGET_RELEASE_ID}"

# -------------------------------------------------------------------------
# 2. Resolve and verify current active release (fail closed if unknown).
# -------------------------------------------------------------------------
CURRENT_BEFORE="$(_atomicity_readlink_current || true)"
PREVIOUS_BEFORE="$(_atomicity_readlink_previous || true)"
[[ -n "$CURRENT_BEFORE" && -d "$CURRENT_BEFORE" ]] || {
  FAILURE_REASON="current_release_unknown"
  die "current active release unknown; refusing rollback"
}
[[ -f "${CURRENT_BEFORE}/DEPLOY_VERSION" ]] || {
  FAILURE_REASON="current_deploy_version_missing"
  die "current/DEPLOY_VERSION missing"
}
SOURCE_DIR="$CURRENT_BEFORE"
SOURCE_RELEASE_ID="$(read_deploy_version_field "${SOURCE_DIR}/DEPLOY_VERSION" release_id)" \
  || die "cannot read current release_id"
SOURCE_IMAGE_DIGEST="$(read_deploy_version_field "${SOURCE_DIR}/DEPLOY_VERSION" image_digest)" \
  || die "cannot read current image_digest"
PREVIOUS_CURRENT="$SOURCE_DIR"

if [[ "$SOURCE_RELEASE_ID" == "$TARGET_RELEASE_ID" ]]; then
  FAILURE_REASON="target_equals_current"
  die "target release equals currently active release"
fi
if [[ "$SOURCE_IMAGE_DIGEST" == "$IMAGE_DIGEST" ]]; then
  FAILURE_REASON="target_equals_current"
  die "target digest equals currently active digest"
fi
log "source_release=${SOURCE_RELEASE_ID} target_release=${TARGET_RELEASE_ID}"

# -------------------------------------------------------------------------
# 3. Ensure target release directory (reuse local or reconstruct from S3).
# -------------------------------------------------------------------------
SAFE_EXTRACT=""
if [[ -f "${ROOT}/bin/verify_staging_bundle.py" ]]; then
  SAFE_EXTRACT="${ROOT}/bin/verify_staging_bundle.py"
fi

if [[ -f "${TARGET_DIR}/bundle-meta.json" && -f "${TARGET_DIR}/compose/docker-compose.staging.yml" ]]; then
  log "target release directory present; verifying full file_checksums identity"
else
  # Historical Build Image #15 reconstruction is schema-aware: schema 1 application
  # runtime members + original file_checksums; host-installed rollback tooling operates it.
  [[ -n "$SAFE_EXTRACT" ]] || die "verify_staging_bundle.py missing — refusing raw tar extract"
  TMP_BUNDLE="$(mktemp /tmp/dealbrain-rollback-bundle.XXXXXX.tar.gz)"
  aws s3 cp "s3://${BUNDLE_BUCKET}/${BUNDLE_KEY}" "$TMP_BUNDLE" --region "$REGION"
  ACTUAL_SUM="$(sha256sum "$TMP_BUNDLE" | awk '{print $1}')"
  [[ "$ACTUAL_SUM" == "$BUNDLE_CHECKSUM" ]] || {
    FAILURE_REASON="bundle_checksum_mismatch"
    rm -f "$TMP_BUNDLE"
    die "bundle SHA-256 mismatch"
  }
  python3 "$SAFE_EXTRACT" "$TMP_BUNDLE" \
    --checksum "$BUNDLE_CHECKSUM" \
    --release-id "$TARGET_RELEASE_ID" \
    --image-digest "$IMAGE_DIGEST" \
    --extract-to "$TARGET_DIR"
  rm -f "$TMP_BUNDLE"
fi

# Complete local release verification (identity + every file_checksums entry).
# Historical schema-1 targets need not contain rollback binaries.
python3 "${ROOT}/bin/verify_staging_bundle.py" \
  --verify-release-dir "$TARGET_DIR" \
  --release-id "$TARGET_RELEASE_ID" \
  --git-sha "$TARGET_GIT_SHA" \
  --image-repository "$IMAGE_REPOSITORY" \
  --image-digest "$IMAGE_DIGEST" \
  --source-manifest-sha256 "$TARGET_MANIFEST_SHA256" \
  || {
    FAILURE_REASON="target_release_checksum_verification_failed"
    die "target release directory failed complete verification"
  }

COMPOSE_BASE="${TARGET_DIR}/compose/docker-compose.base.yml"
COMPOSE_STAGING="${TARGET_DIR}/compose/docker-compose.staging.yml"
[[ -f "$COMPOSE_BASE" && -f "$COMPOSE_STAGING" ]] || {
  FAILURE_REASON="target_release_incomplete"
  die "compose overlays missing"
}
[[ ! -f "${TARGET_DIR}/compose/docker-compose.production.yml" ]] || die "production compose forbidden"

# Host tooling remains authoritative for rollback. Optionally refresh non-rollback
# helpers from a schema-2 target; never require historical targets to supply them.
for helper in \
  verify-staging.sh ghcr-login.sh assemble-runtime-env.py evidence.py \
  verify_staging_bundle.py log_redaction.py alb_target_health.py \
  staging-deploy-evidence.schema.json
do
  if [[ -f "${TARGET_DIR}/bin/${helper}" ]]; then
    install -o root -g root -m 0755 \
      "${TARGET_DIR}/bin/${helper}" "${ROOT}/bin/${helper}" 2>/dev/null || true
  fi
done

export DEALBRAIN_IMAGE="${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"
export APP_ENV=staging

# Ensure runtime env exists (assembled during prior deploy; refresh non-secret RDS if needed).
if [[ ! -f "$ENV_FILE" ]]; then
  python3 "${TARGET_DIR}/bin/assemble-runtime-env.py" \
    --env-file "$ENV_FILE" \
    --rds-endpoint-file "${TARGET_DIR}/manifest/rds-nonsecret.json" \
    --region "$REGION"
fi

compose() {
  docker compose \
    --project-name "$COMPOSE_PROJECT" \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_STAGING" \
    "$@"
}

# -------------------------------------------------------------------------
# 4. Pull/verify target immutable image by digest.
# -------------------------------------------------------------------------
GHCR_LOGIN="${ROOT}/bin/ghcr-login.sh"
[[ -f "$GHCR_LOGIN" ]] || GHCR_LOGIN="${TARGET_DIR}/bin/ghcr-login.sh"
[[ -f "$GHCR_LOGIN" ]] || die "ghcr-login.sh missing on host and target"
bash "$GHCR_LOGIN" --region "$REGION"
docker pull "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"
REPO_DIGEST="$(docker image inspect "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" --format '{{index .RepoDigests 0}}')"
echo "$REPO_DIGEST" | grep -q "${IMAGE_DIGEST}" || {
  FAILURE_REASON="target_image_digest_mismatch"
  die "RepoDigest does not contain target digest"
}

# -------------------------------------------------------------------------
# 5. Database compatibility — never downgrade; fail before API replacement.
# -------------------------------------------------------------------------
# Call in the parent shell: command substitution would discard MIGRATION_AUTHORITY.
if ! resolve_target_recorded_migration; then
  FAILURE_REASON="database_compatibility_unknown"
  die "cannot resolve target recorded migration revision from DEPLOY_VERSION or validated prior evidence"
fi
[[ -n "$TARGET_RECORDED_MIGRATION" ]] || {
  FAILURE_REASON="database_compatibility_unknown"
  die "target recorded migration unset after resolution"
}
[[ -n "$MIGRATION_AUTHORITY" ]] || {
  FAILURE_REASON="database_compatibility_unknown"
  die "migration authority unset after resolution"
}
case "$MIGRATION_AUTHORITY" in
  deploy_version|validated_prior_staging_evidence) ;;
  *)
    FAILURE_REASON="database_compatibility_unknown"
    die "unsupported migration authority after resolution: ${MIGRATION_AUTHORITY}"
    ;;
esac
MIGRATION_BEFORE="$(capture_migration_revision before 0)"
if [[ "$MIGRATION_BEFORE" != "$TARGET_RECORDED_MIGRATION" ]]; then
  FAILURE_REASON="database_incompatible"
  die "database incompatible for rollback: live=${MIGRATION_BEFORE} target_recorded=${TARGET_RECORDED_MIGRATION}"
fi
MIGRATION_AFTER="$MIGRATION_BEFORE"
log "database compatibility confirmed at revision ${MIGRATION_BEFORE} (authority=${MIGRATION_AUTHORITY})"

# -------------------------------------------------------------------------
# 6–11. Replace API with target; verify digest + health. Pointers unchanged yet.
# -------------------------------------------------------------------------
API_REPLACEMENT_OCCURRED=1
compose up -d --force-recreate --no-deps api

TG_ARN_FILE="${TARGET_DIR}/manifest/alb-nonsecret.json"
if [[ ! -f "$TG_ARN_FILE" && -f "${SOURCE_DIR}/manifest/alb-nonsecret.json" ]]; then
  TG_ARN_FILE="${SOURCE_DIR}/manifest/alb-nonsecret.json"
fi
[[ -f "$TG_ARN_FILE" ]] || { FAILURE_REASON="alb_metadata_missing"; die "alb-nonsecret.json missing"; }

VERIFY_STAGING="${ROOT}/bin/verify-staging.sh"
[[ -f "$VERIFY_STAGING" ]] || VERIFY_STAGING="${TARGET_DIR}/bin/verify-staging.sh"
[[ -f "$VERIFY_STAGING" ]] || die "verify-staging.sh missing on host and target"
bash "$VERIFY_STAGING" \
  --env-file "$ENV_FILE" \
  --image-digest "$IMAGE_DIGEST" \
  --image-repository "$IMAGE_REPOSITORY" \
  --compose-project "$COMPOSE_PROJECT" \
  --target-group-json "$TG_ARN_FILE" \
  --region "$REGION" \
  --instance-id "$INSTANCE_ID" \
  --out-json "${EVIDENCE_DIR}/verify-rollback-${TARGET_RELEASE_ID}.json"

LOCAL_LIVE="$(jq -r '.localhost_live' "${EVIDENCE_DIR}/verify-rollback-${TARGET_RELEASE_ID}.json")"
LOCAL_READY="$(jq -r '.localhost_ready' "${EVIDENCE_DIR}/verify-rollback-${TARGET_RELEASE_ID}.json")"
ALB_HEALTH="$(jq -r '.alb_target_healthy' "${EVIDENCE_DIR}/verify-rollback-${TARGET_RELEASE_ID}.json")"
RUNNING_DIGEST_AFTER="$(_atomicity_running_api_digest 2>/dev/null || true)"

[[ "$RUNNING_DIGEST_AFTER" == "$IMAGE_DIGEST" ]] || {
  FAILURE_REASON="running_digest_mismatch"
  die "running digest mismatch after rollback recreate"
}
[[ "$LOCAL_LIVE" == "true" ]] || { FAILURE_REASON="localhost_live_failed"; die "localhost /live failed"; }
[[ "$LOCAL_READY" == "true" ]] || { FAILURE_REASON="localhost_ready_failed"; die "localhost /ready failed"; }
[[ "$ALB_HEALTH" == "true" ]] || { FAILURE_REASON="alb_health_failed"; die "ALB target unhealthy"; }

# -------------------------------------------------------------------------
# 12–13. Atomic pointer update only after health success.
#     current -> target; previous -> displaced source (forward recovery).
# -------------------------------------------------------------------------
MIGRATION_AFTER="$MIGRATION_BEFORE"
export MIGRATION_AFTER
PREVIOUS_CURRENT="$SOURCE_DIR"
if ! commit_release_pointer; then
  die "release pointer commit failed (${FAILURE_REASON:-unknown})"
fi
CURRENT_AFTER="$(_atomicity_readlink_current || true)"
PREVIOUS_AFTER="$(_atomicity_readlink_previous || true)"
[[ "$CURRENT_AFTER" == "$TARGET_DIR" ]] || {
  FAILURE_REASON="pointer_current_verification_failed"
  die "current pointer not on target after commit"
}
[[ "$PREVIOUS_AFTER" == "$SOURCE_DIR" ]] || {
  FAILURE_REASON="pointer_previous_verification_failed"
  die "previous pointer not on displaced source after commit"
}

# Retain current + previous only.
python3 - <<'PY'
import shutil
from pathlib import Path
root = Path("/opt/dealbrain")
releases = root / "releases"
keep = set()
for name in ("current", "previous"):
    link = root / name
    if link.exists() or link.is_symlink():
        try:
            keep.add(link.resolve())
        except OSError:
            pass
for p in releases.iterdir() if releases.is_dir() else []:
    if p.is_dir() and p.resolve() not in keep:
        shutil.rmtree(p, ignore_errors=True)
print("retained:", ", ".join(sorted(str(k) for k in keep)))
PY

# -------------------------------------------------------------------------
# 14–16. Finalize rollback_ok evidence.
# -------------------------------------------------------------------------
resolve_ssm_command_id_for_evidence
[[ -n "$SSM_COMMAND_ID" ]] || {
  FAILURE_REASON="evidence_upload_ssm_command_id_missing"
  die "ssm_command_id unavailable for rollback_ok evidence"
}

FINAL_STATUS="rollback_ok"
FAILURE_REASON=""
if ! write_evidence; then
  FINAL_STATUS="failed"
  FAILURE_REASON="evidence_upload_failed"
  die "success evidence write/upload failed after rollback pointer commit"
fi
log "staging rollback succeeded to ${TARGET_RELEASE_ID}"
rm -f "$LOCK_INFO"
trap on_exit EXIT
