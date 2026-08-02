#!/bin/bash
# DealBrain staging host deploy orchestrator (Sprint 25b.3).
# Invoked by SSM document DealBrain-StagingDeploy via /opt/dealbrain/bin/.
# Secrets never printed; shell tracing disabled around secret material.
set -euo pipefail

umask 077

log() { echo "[dealbrain-staging-deploy] $*"; }
die() { echo "[dealbrain-staging-deploy] ERROR: $*" >&2; exit 1; }

# Disable xtrace for the entire script (secrets may appear in env files).
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

RELEASE_ID="$DEALBRAIN_RELEASE_ID"
GIT_SHA="$DEALBRAIN_GIT_SHA"
IMAGE_REPOSITORY="$DEALBRAIN_IMAGE_REPOSITORY"
IMAGE_DIGEST="$DEALBRAIN_IMAGE_DIGEST"
BUNDLE_CHECKSUM="$DEALBRAIN_BUNDLE_CHECKSUM"
DEPLOY_RUN_ID="$DEALBRAIN_DEPLOY_RUN_ID"
BUNDLE_BUCKET="$DEALBRAIN_BUNDLE_BUCKET"
BUNDLE_KEY="$DEALBRAIN_BUNDLE_KEY"

# Re-validate patterns on host (defense in depth).
[[ "$RELEASE_ID" =~ ^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$ ]] || die "invalid ReleaseId"
[[ "$GIT_SHA" =~ ^[0-9a-f]{40}$ ]] || die "invalid GitSha"
[[ "$IMAGE_REPOSITORY" =~ ^ghcr\.io/[a-z0-9._/-]+$ ]] || die "invalid ImageRepository"
[[ "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || die "invalid ImageDigest"
[[ "$BUNDLE_CHECKSUM" =~ ^[0-9a-f]{64}$ ]] || die "invalid BundleChecksum"
[[ "$DEPLOY_RUN_ID" =~ ^[0-9]+$ ]] || die "invalid DeployRunId"
[[ "$BUNDLE_BUCKET" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]] || die "invalid BundleBucket"
[[ "$BUNDLE_KEY" =~ ^releases/rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}/bundle\.tar\.gz$ ]] || die "invalid BundleKey"
[[ "$BUNDLE_KEY" == "releases/${RELEASE_ID}/bundle.tar.gz" ]] || die "BundleKey/ReleaseId mismatch"

# Reject mutable-tag authority in repository string.
case "$IMAGE_REPOSITORY" in
  *:latest|*:ci-latest|*:staging|*:production|*:main|*@*|*:* )
    die "mutable tag or digest suffix forbidden in ImageRepository"
    ;;
esac

ROOT=/opt/dealbrain
RELEASES_DIR="${ROOT}/releases"
RELEASE_DIR="${RELEASES_DIR}/${RELEASE_ID}"
RUNTIME_DIR="${ROOT}/runtime"
LOCK_DIR="${ROOT}/locks"
LOCK_FILE="${LOCK_DIR}/staging-deploy.lock"
LOCK_INFO="${LOCK_DIR}/staging-deploy.lock.info"
EVIDENCE_DIR="${ROOT}/runtime/evidence"
COMPOSE_PROJECT=dealbrain-staging
ENV_FILE="${RUNTIME_DIR}/staging.env"
PRE_PULL_MIN_GIB=4
POST_PULL_MIN_GIB=2
MIGRATE_TIMEOUT_SEC=1200

[[ -f "${ROOT}/bootstrap.ok" ]] || die "bootstrap.ok missing — host not bootstrapped"
command -v docker >/dev/null || die "docker missing"
docker compose version >/dev/null || die "docker compose missing"
command -v aws >/dev/null || die "aws cli missing"
command -v jq >/dev/null || die "jq missing"
command -v python3 >/dev/null || die "python3 missing"
command -v timeout >/dev/null || die "timeout (coreutils) missing"
command -v flock >/dev/null || die "flock missing"

# Verify host environment via instance identity / tags (IMDSv2).
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

disk_free_gib() {
  df -BG --output=avail / | tail -1 | tr -dc '0-9'
}

require_disk_gib() {
  local need="$1"
  local label="$2"
  local free
  free="$(disk_free_gib)"
  log "disk free ${free} GiB (${label}; need >= ${need})"
  [[ "$free" -ge "$need" ]] || die "insufficient disk free space (${label}): ${free} GiB < ${need} GiB"
}

discover_ssm_command_id() {
  local found=""
  if [[ -n "${AWS_SSM_COMMAND_ID:-}" ]]; then
    echo "$AWS_SSM_COMMAND_ID"
    return 0
  fi
  # Prefer the workflow-published binder object (exact command id for this run).
  local binder="evidence/${RELEASE_ID}/${DEPLOY_RUN_ID}/ssm-command-id.txt"
  local tmp
  tmp="$(mktemp)"
  if aws s3 cp "s3://${BUNDLE_BUCKET}/${binder}" "$tmp" --region "$REGION" 2>/dev/null; then
    found="$(tr -d '[:space:]' <"$tmp")"
    rm -f "$tmp"
    if [[ -n "$found" ]]; then
      echo "$found"
      return 0
    fi
  fi
  rm -f "$tmp"
  # Best-effort discovery from SSM agent orchestration directories.
  local base="/var/lib/amazon/ssm/${INSTANCE_ID}/document/orchestration"
  if [[ -d "$base" ]]; then
    found="$(find "$base" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %f\n' 2>/dev/null \
      | sort -nr | head -1 | awk '{print $2}' || true)"
  fi
  echo "${found:-}"
}

DEPLOYMENT_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
FAILURE_REASON=""
FINAL_STATUS="failed"
MIGRATION_BEFORE=""
MIGRATION_AFTER=""
LOCAL_LIVE=""
LOCAL_READY=""
ALB_HEALTH=""
SMOKE_OK=""
IMAGE_ID=""
REPO_DIGEST=""
IMAGE_CREATED_AT=""
SSM_COMMAND_ID="$(discover_ssm_command_id)"
SOURCE_MANIFEST_SHA256=""
EVIDENCE_UPLOADED=0
# Deployment commit / atomicity contract (Sprint 25b.5i Design — OUTCOME 2):
# Forward migrations run before API replacement; previous-image rollback is NOT
# assumed schema-safe. After API replacement begins, every failure path must
# leave running API image, /opt/dealbrain/current, and current/DEPLOY_VERSION
# describing the same release (candidate reconciliation), or emit an explicit
# unrecoverable invariant failure. Pointer-only rollback after replacement is
# forbidden. Post-commit evidence failures retain the committed candidate.
# Reconciliation never claims staging_ok.
RELEASE_COMMITTED=0
IN_ON_EXIT_EVIDENCE=0
PREVIOUS_CURRENT=""
MIGRATE_LOG=""
if [[ -L "${ROOT}/current" || -e "${ROOT}/current" ]]; then
  PREVIOUS_CURRENT="$(readlink -f "${ROOT}/current" 2>/dev/null || true)"
fi

# Atomicity library ships beside the orchestrator in the release bundle.
# Prefer BASH_SOURCE dir (release bin/) so first deploy of this sprint works
# before helpers are copied into /opt/dealbrain/bin.
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
set_deploy_phase "PRE_MIGRATION"

normalize_image_created_at() {
  local raw="$1"
  python3 - <<PY
from datetime import datetime, timezone
import re
raw = """${raw}""".strip()
if not raw:
    raise SystemExit(1)
# Normalize fractional seconds to <=6 digits and Zulu/offset forms.
m = re.match(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$",
    raw,
)
if not m:
    raise SystemExit(1)
base, frac, off = m.group(1), m.group(2) or "", m.group(3) or "Z"
if frac:
    digits = frac[1:7].ljust(6, "0")
    frac = "." + digits
if off == "Z":
    dt = datetime.strptime(base + frac, "%Y-%m-%dT%H:%M:%S.%f" if frac else "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
else:
    off_norm = off if ":" in off else (off[:-2] + ":" + off[-2:])
    text = base + frac + off_norm
    dt = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f%z" if frac else "%Y-%m-%dT%H:%M:%S%z")
print(dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
}

# Resolve canonical evidence.py for revision normalization (release bin, then host bin).
_evidence_py() {
  if [[ -f "${RELEASE_DIR}/bin/evidence.py" ]]; then
    echo "${RELEASE_DIR}/bin/evidence.py"
  elif [[ -f "${ROOT}/bin/evidence.py" ]]; then
    echo "${ROOT}/bin/evidence.py"
  else
    return 1
  fi
}

# Strict Alembic revision normalization — fail closed (never first-token split).
normalize_alembic_revision() {
  local raw="$1"
  local evidence_py
  evidence_py="$(_evidence_py)" || die "evidence.py missing; cannot normalize alembic revision"
  DEALBRAIN_ALEMBIC_RAW="$raw" python3 - "$evidence_py" <<'PY'
import importlib.util
import os
import sys

path = sys.argv[1]
spec = importlib.util.spec_from_file_location("dealbrain_staging_evidence", path)
if spec is None or spec.loader is None:
    print("invalid alembic revision output: evidence module unreadable", file=sys.stderr)
    raise SystemExit(1)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
try:
    print(mod.normalize_alembic_revision(os.environ.get("DEALBRAIN_ALEMBIC_RAW", "")))
except Exception as exc:
    # Do not print raw alembic text — may include unexpected operator output.
    print(f"invalid alembic revision output: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
PY
}

# Capture ``alembic current``, normalize, fail closed. allow_empty=1 → "" on empty/soft-fail.
capture_migration_revision() {
  local label="$1"
  local allow_empty="${2:-0}"
  local out rc normalized
  # pipefail (script-wide) makes the substitution fail if alembic current fails.
  set +e
  out="$(compose --profile migrate run --rm --no-deps migrate alembic current 2>/dev/null | tr -d '\r')"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    if [[ "$allow_empty" -eq 1 ]]; then
      echo ""
      return 0
    fi
    die "alembic current failed for migration_revision_${label} (exit ${rc})"
  fi
  if [[ -z "${out//[[:space:]]/}" ]]; then
    if [[ "$allow_empty" -eq 1 ]]; then
      echo ""
      return 0
    fi
    die "migration_revision_${label} empty"
  fi
  set +e
  normalized="$(normalize_alembic_revision "$out")"
  rc=$?
  set -e
  if [[ $rc -ne 0 || -z "$normalized" ]]; then
    die "migration_revision_${label} failed revision normalization"
  fi
  echo "$normalized"
}

write_evidence() {
  local finished duration out evidence_key
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  duration="$(python3 - <<PY
from datetime import datetime
start = datetime.strptime("${DEPLOYMENT_STARTED_AT}", "%Y-%m-%dT%H:%M:%SZ")
end = datetime.strptime("${finished}", "%Y-%m-%dT%H:%M:%SZ")
print(int((end - start).total_seconds()))
PY
)"
  mkdir -p "$EVIDENCE_DIR"
  out="${EVIDENCE_DIR}/staging-deploy-evidence-${RELEASE_ID}-${DEPLOY_RUN_ID}.json"

  local writer=""
  if [[ -f "${RELEASE_DIR}/bin/write-staging-evidence.py" ]]; then
    writer="${RELEASE_DIR}/bin/write-staging-evidence.py"
  elif [[ -f "${ROOT}/bin/write-staging-evidence.py" ]]; then
    writer="${ROOT}/bin/write-staging-evidence.py"
  else
    log "evidence writer missing; cannot write evidence"
    return 1
  fi

  DEALBRAIN_EVIDENCE_OUT="$out" \
  DEALBRAIN_FINAL_STATUS="$FINAL_STATUS" \
  DEALBRAIN_FAILURE_REASON="$FAILURE_REASON" \
  DEALBRAIN_MIGRATION_BEFORE="$MIGRATION_BEFORE" \
  DEALBRAIN_MIGRATION_AFTER="$MIGRATION_AFTER" \
  DEALBRAIN_LOCAL_LIVE="$LOCAL_LIVE" \
  DEALBRAIN_LOCAL_READY="$LOCAL_READY" \
  DEALBRAIN_ALB_HEALTH="$ALB_HEALTH" \
  DEALBRAIN_SMOKE_OK="$SMOKE_OK" \
  DEALBRAIN_IMAGE_ID="$IMAGE_ID" \
  DEALBRAIN_REPO_DIGEST="$REPO_DIGEST" \
  DEALBRAIN_IMAGE_CREATED_AT="$IMAGE_CREATED_AT" \
  DEALBRAIN_STARTED_AT="$DEPLOYMENT_STARTED_AT" \
  DEALBRAIN_FINISHED_AT="$finished" \
  DEALBRAIN_DURATION="$duration" \
  DEALBRAIN_INSTANCE_ID="$INSTANCE_ID" \
  DEALBRAIN_REGION="$REGION" \
  DEALBRAIN_AWS_ACCOUNT_ID="$AWS_ACCOUNT_ID" \
  DEALBRAIN_SSM_COMMAND_ID="$SSM_COMMAND_ID" \
  DEALBRAIN_SOURCE_MANIFEST_SHA256="${SOURCE_MANIFEST_SHA256}" \
  DEALBRAIN_ASSUMED_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/dealbrain-staging-gha-deploy" \
  DEALBRAIN_ROLE_SESSION_NAME="gha-${DEPLOY_RUN_ID}-staging" \
  python3 "$writer" || return 1

  evidence_key="evidence/${RELEASE_ID}/${DEPLOY_RUN_ID}/staging-deploy-evidence.json"
  aws s3 cp "$out" "s3://${BUNDLE_BUCKET}/${evidence_key}" --region "$REGION"
  if [[ -f "${out}.sha256" ]]; then
    aws s3 cp "${out}.sha256" "s3://${BUNDLE_BUCKET}/${evidence_key}.sha256" --region "$REGION"
  fi
  EVIDENCE_UPLOADED=1
  log "evidence uploaded: s3://${BUNDLE_BUCKET}/${evidence_key}"
}

on_exit() {
  local code=$?
  # Always scrub migrate temp log (signals / die / abnormal exit). Never mask status.
  if [[ -n "${MIGRATE_LOG:-}" ]]; then
    rm -f -- "$MIGRATE_LOG" || true
    MIGRATE_LOG=""
  fi

  # Any trapped non-zero failure must force canonical failed status BEFORE evidence.
  # Preserves original exit code; never emit staging_ok + failure_reason.
  if [[ $code -ne 0 ]]; then
    FINAL_STATUS="failed"
    if [[ -z "$FAILURE_REASON" ]]; then
      if [[ "${RELEASE_COMMITTED:-0}" -eq 1 ]]; then
        FAILURE_REASON="evidence_upload_failed"
      else
        FAILURE_REASON="host_script_exit_${code}"
      fi
    fi
    # Post-health gates true ⇒ failure_reason must use an allowed post-gate prefix.
    if [[ "$LOCAL_LIVE" == "true" && "$LOCAL_READY" == "true" \
       && "$ALB_HEALTH" == "true" && "$SMOKE_OK" == "true" ]]; then
      case "$FAILURE_REASON" in
        post_gate_*|evidence_upload_*|deploy_version_*|symlink_*|post_replacement_*|release_alignment_*) ;;
        *) FAILURE_REASON="post_gate_${FAILURE_REASON}" ;;
      esac
    fi
  fi

  # Post-replacement pre-commit → candidate reconciliation (OUTCOME 2).
  # Post-commit → retain current (no pointer-only rollback).
  # Pre-replacement failures leave previous API + current untouched.
  if [[ $code -ne 0 ]]; then
    atomicity_on_failure "$code" || true
  fi

  # Secret-free invariant check before evidence. Does not overwrite exit code.
  if [[ "${IN_ON_EXIT_EVIDENCE:-0}" -eq 0 ]]; then
    atomicity_invariant_before_evidence || true
  fi

  # Best-effort evidence once. Guard against recursive/repeated trap execution
  # if evidence writing itself fails (do not re-enter the success evidence path).
  if [[ "$EVIDENCE_UPLOADED" -eq 0 && "${IN_ON_EXIT_EVIDENCE:-0}" -eq 0 ]]; then
    IN_ON_EXIT_EVIDENCE=1
    write_evidence || log "evidence write/upload failed (best-effort on error path)"
  fi
  exit "$code"
}
trap on_exit EXIT

# -------------------------------------------------------------------------
# 1. Acquire flock BEFORE download/extract/secrets/migrate/rollout.
# -------------------------------------------------------------------------
if [[ "${DEALBRAIN_LOCK_HELD:-}" != "1" ]]; then
  mkdir -p "$LOCK_DIR"
  exec 9>"$LOCK_FILE"
  if ! flock -w 30 9; then
    die "could not acquire staging deploy lock within 30s"
  fi
fi
cat >"$LOCK_INFO" <<EOF
{"release_id":"${RELEASE_ID}","deploy_run_id":"${DEPLOY_RUN_ID}","pid":$$,"started_at":"${DEPLOYMENT_STARTED_AT}","instance_id":"${INSTANCE_ID}"}
EOF
chmod 0644 "$LOCK_INFO"
log "acquired flock for ${RELEASE_ID}"

require_disk_gib "$PRE_PULL_MIN_GIB" "pre-bundle"

# -------------------------------------------------------------------------
# 2. Validate + extract into release-specific directory (no current update).
# -------------------------------------------------------------------------
SAFE_EXTRACT=""
if [[ -x "${ROOT}/bin/verify_staging_bundle.py" ]]; then
  SAFE_EXTRACT="${ROOT}/bin/verify_staging_bundle.py"
elif [[ -f "${ROOT}/bin/verify_staging_bundle.py" ]]; then
  SAFE_EXTRACT="${ROOT}/bin/verify_staging_bundle.py"
fi

if [[ "${DEALBRAIN_BUNDLE_ALREADY_EXTRACTED:-}" == "1" && -f "${RELEASE_DIR}/bundle-meta.json" ]]; then
  log "bundle already extracted by entrypoint; verifying layout"
  if [[ -n "$SAFE_EXTRACT" ]]; then
    # Re-verify checksum map from extracted tree via meta only (tarball gone).
    [[ -f "${RELEASE_DIR}/compose/docker-compose.base.yml" ]] || die "extracted bundle incomplete"
    [[ ! -f "${RELEASE_DIR}/compose/docker-compose.production.yml" ]] || die "production overlay forbidden"
  fi
else
  TMP_BUNDLE="$(mktemp /tmp/dealbrain-bundle.XXXXXX.tar.gz)"
  cleanup_tmp() {
    rm -f "$TMP_BUNDLE"
  }
  trap 'cleanup_tmp; on_exit' EXIT

  aws s3 cp "s3://${BUNDLE_BUCKET}/${BUNDLE_KEY}" "$TMP_BUNDLE" --region "$REGION"
  ACTUAL_SUM="$(sha256sum "$TMP_BUNDLE" | awk '{print $1}')"
  [[ "$ACTUAL_SUM" == "$BUNDLE_CHECKSUM" ]] || die "bundle SHA-256 mismatch"

  if [[ -z "$SAFE_EXTRACT" ]]; then
    die "verify_staging_bundle.py missing on host — refusing raw tar extract"
  fi
  python3 "$SAFE_EXTRACT" "$TMP_BUNDLE" \
    --checksum "$BUNDLE_CHECKSUM" \
    --release-id "$RELEASE_ID" \
    --image-digest "$IMAGE_DIGEST" \
    --extract-to "$RELEASE_DIR"
  cleanup_tmp
  trap on_exit EXIT
fi

# Install/update fixed helpers from this release for subsequent deploys.
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/assemble-runtime-env.py" \
  "${ROOT}/bin/assemble-runtime-env.py" 2>/dev/null || true
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/ghcr-login.sh" \
  "${ROOT}/bin/ghcr-login.sh"
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/verify-staging.sh" \
  "${ROOT}/bin/verify-staging.sh"
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/write-staging-evidence.py" \
  "${ROOT}/bin/write-staging-evidence.py" 2>/dev/null || true
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/evidence.py" \
  "${ROOT}/bin/evidence.py" 2>/dev/null || true
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/log_redaction.py" \
  "${ROOT}/bin/log_redaction.py" 2>/dev/null || true
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/verify_staging_bundle.py" \
  "${ROOT}/bin/verify_staging_bundle.py" 2>/dev/null || true
install -o root -g root -m 0755 \
  "${RELEASE_DIR}/bin/deploy_atomicity.sh" \
  "${ROOT}/bin/deploy_atomicity.sh" 2>/dev/null || true
install -o root -g root -m 0644 \
  "${RELEASE_DIR}/bin/staging-deploy-evidence.schema.json" \
  "${ROOT}/bin/staging-deploy-evidence.schema.json" 2>/dev/null || true

# Validate bundle-meta.json
META="${RELEASE_DIR}/bundle-meta.json"
[[ -f "$META" ]] || die "bundle-meta.json missing"
SOURCE_MANIFEST_SHA256="$(python3 - "$META" "$RELEASE_ID" "$GIT_SHA" "$IMAGE_REPOSITORY" "$IMAGE_DIGEST" "$BUNDLE_CHECKSUM" <<'PY'
import json, sys
meta_path, rid, sha, repo, digest, checksum = sys.argv[1:7]
with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)
assert meta.get("release_id") == rid, "release_id mismatch"
assert meta.get("git_sha") == sha, "git_sha mismatch"
assert meta.get("image_repository") == repo, "image_repository mismatch"
assert meta.get("image_digest") == digest, "image_digest mismatch"
assert "source_manifest_sha256" in meta
assert "file_checksums" in meta
print(meta["source_manifest_sha256"])
PY
)"

COMPOSE_BASE="${RELEASE_DIR}/compose/docker-compose.base.yml"
COMPOSE_STAGING="${RELEASE_DIR}/compose/docker-compose.staging.yml"
[[ -f "$COMPOSE_BASE" && -f "$COMPOSE_STAGING" ]] || die "compose overlays missing"
[[ ! -f "${RELEASE_DIR}/compose/docker-compose.production.yml" ]] || die "production compose overlay forbidden in staging bundle"

BIN="${RELEASE_DIR}/bin"
export DEALBRAIN_IMAGE="${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"
export APP_ENV=staging

# -------------------------------------------------------------------------
# 3–5. Assemble env, pull image, validate Compose (explicit release paths).
# -------------------------------------------------------------------------
python3 "${BIN}/assemble-runtime-env.py" \
  --env-file "$ENV_FILE" \
  --rds-endpoint-file "${RELEASE_DIR}/manifest/rds-nonsecret.json" \
  --region "$REGION"

require_disk_gib "$PRE_PULL_MIN_GIB" "before-pull"
bash "${BIN}/ghcr-login.sh" --region "$REGION"
docker pull "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}"
require_disk_gib "$POST_PULL_MIN_GIB" "after-pull"

IMAGE_ID="$(docker image inspect "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" --format '{{.Id}}')"
REPO_DIGEST="$(docker image inspect "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" --format '{{index .RepoDigests 0}}')"
RAW_CREATED="$(docker image inspect "${IMAGE_REPOSITORY}@${IMAGE_DIGEST}" --format '{{.Created}}')"
IMAGE_CREATED_AT="$(normalize_image_created_at "$RAW_CREATED")" \
  || die "could not normalize image_created_at"
echo "$REPO_DIGEST" | grep -q "${IMAGE_DIGEST}" || die "RepoDigest does not contain release digest"

compose() {
  docker compose \
    --project-name "$COMPOSE_PROJECT" \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_STAGING" \
    "$@"
}

compose config >/dev/null

# -------------------------------------------------------------------------
# 6. Migrate with 20-minute timeout — API untouched on failure.
# -------------------------------------------------------------------------
MIGRATION_BEFORE="$(capture_migration_revision before 1)"
log "migration_revision_before=${MIGRATION_BEFORE:-unknown}"

REDACT_BIN=""
if [[ -f "${BIN}/log_redaction.py" ]]; then
  REDACT_BIN="${BIN}/log_redaction.py"
elif [[ -f "${ROOT}/bin/log_redaction.py" ]]; then
  REDACT_BIN="${ROOT}/bin/log_redaction.py"
fi

MIGRATE_LOG="$(mktemp "${RUNTIME_DIR}/.migrate.XXXXXX.log")"
set +e
timeout --signal=TERM --kill-after=30s "$MIGRATE_TIMEOUT_SEC" \
  docker compose \
    --project-name "$COMPOSE_PROJECT" \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_STAGING" \
    --profile migrate run --rm migrate \
    >"$MIGRATE_LOG" 2>&1
MIGRATE_RC=$?
set -e
# Emit only structurally redacted migrate output (never raw DATABASE_URL).
if [[ -n "$REDACT_BIN" ]]; then
  python3 "$REDACT_BIN" <"$MIGRATE_LOG" || true
else
  log "migrate log redactor missing; suppressing raw migrate output"
fi
rm -f -- "$MIGRATE_LOG"
MIGRATE_LOG=""
if [[ $MIGRATE_RC -eq 124 || $MIGRATE_RC -eq 137 ]]; then
  FAILURE_REASON="migration_timeout"
  die "migration timed out after ${MIGRATE_TIMEOUT_SEC}s; API left untouched"
fi
if [[ $MIGRATE_RC -ne 0 ]]; then
  FAILURE_REASON="migration_failed"
  die "migration failed with exit ${MIGRATE_RC}; API left untouched"
fi

MIGRATION_AFTER="$(capture_migration_revision after 0)"
[[ -n "$MIGRATION_AFTER" ]] || die "migration_revision_after empty"
log "migration_revision_after=${MIGRATION_AFTER}"
set_deploy_phase "MIGRATION_COMPLETE"

# -------------------------------------------------------------------------
# 7–8. Recreate API only after migration success; verify health.
# -------------------------------------------------------------------------
# Mark replacement BEFORE compose up so a partial recreate failure is visible
# to the exit trap (do not infer solely from health variables).
set_deploy_phase "API_REPLACEMENT_STARTED"
API_REPLACEMENT_OCCURRED=1
compose up -d --force-recreate --no-deps api
set_deploy_phase "CANDIDATE_RUNNING"

TG_ARN_FILE="${RELEASE_DIR}/manifest/alb-nonsecret.json"
bash "${BIN}/verify-staging.sh" \
  --env-file "$ENV_FILE" \
  --image-digest "$IMAGE_DIGEST" \
  --image-repository "$IMAGE_REPOSITORY" \
  --compose-project "$COMPOSE_PROJECT" \
  --target-group-json "$TG_ARN_FILE" \
  --region "$REGION" \
  --instance-id "$INSTANCE_ID" \
  --out-json "${EVIDENCE_DIR}/verify-${RELEASE_ID}.json"

LOCAL_LIVE="$(jq -r '.localhost_live' "${EVIDENCE_DIR}/verify-${RELEASE_ID}.json")"
LOCAL_READY="$(jq -r '.localhost_ready' "${EVIDENCE_DIR}/verify-${RELEASE_ID}.json")"
ALB_HEALTH="$(jq -r '.alb_target_healthy' "${EVIDENCE_DIR}/verify-${RELEASE_ID}.json")"
SMOKE_OK="$(jq -r '.smoke_ok' "${EVIDENCE_DIR}/verify-${RELEASE_ID}.json")"

[[ "$LOCAL_LIVE" == "true" ]] || { FAILURE_REASON="localhost_live_failed"; die "localhost /live failed"; }
[[ "$LOCAL_READY" == "true" ]] || { FAILURE_REASON="localhost_ready_failed"; die "localhost /ready failed"; }
[[ "$ALB_HEALTH" == "true" ]] || { FAILURE_REASON="alb_health_failed"; die "ALB target unhealthy"; }
[[ "$SMOKE_OK" == "true" ]] || { FAILURE_REASON="smoke_check_failed"; die "smoke check failed"; }
set_deploy_phase "HEALTH_VERIFIED"

# -------------------------------------------------------------------------
# 9–10. DEPLOY_VERSION + atomic current (commit point) with post-checks.
# -------------------------------------------------------------------------
# commit_release_pointer writes/validates DEPLOY_VERSION, atomically switches
# current, verifies readlink + DEPLOY_VERSION + running digest, then sets
# RELEASE_COMMITTED=1. Evidence finalization must not pointer-only-rollback.
if ! commit_release_pointer; then
  die "release pointer commit failed (${FAILURE_REASON:-unknown})"
fi

# Retain current + previous; prune older.
python3 - <<'PY'
import shutil
from pathlib import Path
releases = Path("/opt/dealbrain/releases")
current = Path("/opt/dealbrain/current").resolve()
dirs = sorted([p for p in releases.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
keep = {current}
for p in dirs:
    if p.resolve() != current:
        keep.add(p)
        break
for p in dirs:
    if p.resolve() not in {k.resolve() for k in keep}:
        shutil.rmtree(p, ignore_errors=True)
print("retained:", ", ".join(sorted(str(k) for k in keep)))
PY

# -------------------------------------------------------------------------
# 11. Write/upload final success evidence.
# -------------------------------------------------------------------------
[[ -n "$SSM_COMMAND_ID" ]] || {
  # Poll for workflow-published binder (uploaded immediately after SendCommand).
  for _ in $(seq 1 60); do
    SSM_COMMAND_ID="$(discover_ssm_command_id)"
    [[ -n "$SSM_COMMAND_ID" ]] && break
    sleep 2
  done
}
[[ -n "$SSM_COMMAND_ID" ]] || {
  FAILURE_REASON="evidence_upload_ssm_command_id_missing"
  die "ssm_command_id unavailable for staging_ok evidence"
}

FINAL_STATUS="staging_ok"
FAILURE_REASON=""
if ! write_evidence; then
  # Host release state stays committed; workflow fails on missing/failed evidence.
  FINAL_STATUS="failed"
  FAILURE_REASON="evidence_upload_failed"
  die "success evidence write/upload failed after release commit"
fi
set_deploy_phase "FINALIZATION_COMPLETE"
log "staging deploy succeeded for ${RELEASE_ID}"

rm -f "$LOCK_INFO"
trap on_exit EXIT
