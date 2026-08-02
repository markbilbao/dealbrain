#!/bin/bash
# Sprint 25b.5i — deployment atomicity state machine (sourcable).
#
# Design: candidate reconciliation after API replacement (OUTCOME 2).
# Forward migrations run before API replacement; rolling the previous
# application image back is NOT assumed schema-safe. After replacement
# begins, failure paths must align current + DEPLOY_VERSION to the
# immutable image that is actually running (or report an explicit
# unrecoverable invariant failure). Never pointer-only-rollback after
# replacement. Never claim staging_ok from reconciliation.
#
# Required caller variables:
#   ROOT RELEASE_DIR RELEASE_ID GIT_SHA IMAGE_DIGEST COMPOSE_PROJECT
# Optional:
#   PREVIOUS_CURRENT log()
#
# Mutated:
#   DEPLOY_PHASE API_REPLACEMENT_OCCURRED RELEASE_COMMITTED
#   RECONCILIATION_STATUS INVARIANT_OK FAILURE_REASON

# shellcheck disable=SC2034
: "${DEPLOY_PHASE:=PRE_MIGRATION}"
: "${API_REPLACEMENT_OCCURRED:=0}"
: "${RELEASE_COMMITTED:=0}"
: "${RECONCILIATION_STATUS:=}"
: "${INVARIANT_OK:=0}"
: "${IN_ON_EXIT_RECONCILE:=0}"
: "${IN_ON_EXIT_INVARIANT:=0}"

if ! declare -f log >/dev/null 2>&1; then
  log() { echo "[dealbrain-staging-deploy] $*"; }
fi

set_deploy_phase() {
  DEPLOY_PHASE="$1"
  log "deploy_phase=${DEPLOY_PHASE}"
}

# --- overridable primitives (tests may redefine before/after source) ---------

if ! declare -f _atomicity_running_api_cid >/dev/null 2>&1; then
  _atomicity_running_api_cid() {
    docker ps --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" \
      --filter "label=com.docker.compose.service=api" \
      --format '{{.ID}}' 2>/dev/null | head -1
  }
fi

if ! declare -f _atomicity_running_api_digest >/dev/null 2>&1; then
  _atomicity_running_api_digest() {
    local cid img repo_digest
    cid="$(_atomicity_running_api_cid)"
    [[ -n "$cid" ]] || return 1
    repo_digest="$(docker inspect "$cid" --format '{{index .Image}}' 2>/dev/null \
      | xargs -I{} docker image inspect {} --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"
    if [[ -n "$repo_digest" && "$repo_digest" == *sha256:* ]]; then
      # Prefer bare digest when RepoDigests carries repo@sha256:...
      if [[ "$repo_digest" == *@sha256:* ]]; then
        echo "${repo_digest##*@}"
      else
        echo "$repo_digest"
      fi
      return 0
    fi
    img="$(docker inspect "$cid" --format '{{.Config.Image}}' 2>/dev/null || true)"
    if [[ "$img" == *@sha256:* ]]; then
      echo "${img##*@}"
      return 0
    fi
    if [[ "$img" == sha256:* ]]; then
      echo "$img"
      return 0
    fi
    return 1
  }
fi

if ! declare -f _atomicity_readlink_current >/dev/null 2>&1; then
  _atomicity_readlink_current() {
    if [[ -L "${ROOT}/current" || -e "${ROOT}/current" ]]; then
      readlink -f "${ROOT}/current" 2>/dev/null || true
    fi
  }
fi

# --- DEPLOY_VERSION + atomic current -----------------------------------------

write_candidate_deploy_version() {
  local deployed_at
  deployed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cat >"${RELEASE_DIR}/DEPLOY_VERSION" <<EOF
{
  "release_id": "${RELEASE_ID}",
  "git_sha": "${GIT_SHA}",
  "image_digest": "${IMAGE_DIGEST}",
  "deployed_at": "${deployed_at}"
}
EOF
  chmod 0644 "${RELEASE_DIR}/DEPLOY_VERSION"
}

validate_deploy_version_file() {
  local path="$1"
  local expect_release="$2"
  local expect_sha="$3"
  local expect_digest="$4"
  [[ -f "$path" ]] || return 1
  python3 - "$path" "$expect_release" "$expect_sha" "$expect_digest" <<'PY'
import json, sys
path, rid, sha, digest = sys.argv[1:5]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
if data.get("release_id") != rid:
    raise SystemExit(1)
if data.get("git_sha") != sha:
    raise SystemExit(1)
if data.get("image_digest") != digest:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

atomic_point_current() {
  local target="$1"
  [[ -d "$target" ]] || return 1
  ln -sfn "$target" "${ROOT}/current.new"
  # Prefer GNU mv -Tf (staging EC2). Portable fallback for macOS unit-test hosts.
  if mv -Tf "${ROOT}/current.new" "${ROOT}/current" 2>/dev/null; then
    return 0
  fi
  local tmp="${ROOT}/current.prev.$$"
  if [[ -L "${ROOT}/current" || -e "${ROOT}/current" ]]; then
    mv -f "${ROOT}/current" "$tmp" || return 1
  fi
  if mv -f "${ROOT}/current.new" "${ROOT}/current"; then
    rm -f "$tmp"
    return 0
  fi
  if [[ -e "$tmp" || -L "$tmp" ]]; then
    mv -f "$tmp" "${ROOT}/current" || true
  fi
  return 1
}

verify_current_aligned_to() {
  local expect_dir="$1"
  local expect_release="$2"
  local expect_sha="$3"
  local expect_digest="$4"
  local cur
  cur="$(_atomicity_readlink_current)"
  [[ "$cur" == "$expect_dir" ]] || return 1
  validate_deploy_version_file \
    "${expect_dir}/DEPLOY_VERSION" "$expect_release" "$expect_sha" "$expect_digest" || return 1
  return 0
}

# Commit contract: DEPLOY_VERSION validated, atomic current, post-checks, then flag.
commit_release_pointer() {
  write_candidate_deploy_version || {
    FAILURE_REASON="deploy_version_write_failed"
    return 1
  }
  validate_deploy_version_file \
    "${RELEASE_DIR}/DEPLOY_VERSION" "$RELEASE_ID" "$GIT_SHA" "$IMAGE_DIGEST" || {
    FAILURE_REASON="deploy_version_validation_failed"
    return 1
  }
  atomic_point_current "$RELEASE_DIR" || {
    FAILURE_REASON="symlink_prepare_or_replace_failed"
    return 1
  }
  verify_current_aligned_to "$RELEASE_DIR" "$RELEASE_ID" "$GIT_SHA" "$IMAGE_DIGEST" || {
    FAILURE_REASON="symlink_verification_failed"
    return 1
  }
  local running_digest=""
  running_digest="$(_atomicity_running_api_digest 2>/dev/null || true)"
  if [[ -z "$running_digest" || "$running_digest" != "$IMAGE_DIGEST" ]]; then
    FAILURE_REASON="symlink_verification_failed"
    return 1
  fi
  RELEASE_COMMITTED=1
  set_deploy_phase "RELEASE_COMMITTED"
  log "release committed: current -> ${RELEASE_DIR} (API + DEPLOY_VERSION aligned)"
  return 0
}

# --- reconciliation (OUTCOME 2) ----------------------------------------------

_previous_deploy_digest() {
  local prev="${PREVIOUS_CURRENT:-}"
  [[ -n "$prev" && -f "${prev}/DEPLOY_VERSION" ]] || return 1
  python3 - "${prev}/DEPLOY_VERSION" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
digest = data.get("image_digest") or ""
print(digest)
raise SystemExit(0 if digest else 1)
PY
}

# Align current + DEPLOY_VERSION to the immutable image that is running.
# Keeps deployment failed — never sets FINAL_STATUS=staging_ok.
# Returns 0 when aligned; 1 when unrecoverable.
reconcile_post_replacement_state() {
  local running_digest="" cur="" prev_digest=""
  RECONCILIATION_STATUS="failed"

  running_digest="$(_atomicity_running_api_digest 2>/dev/null || true)"
  cur="$(_atomicity_readlink_current)"

  if [[ -n "$running_digest" && "$running_digest" == "$IMAGE_DIGEST" ]]; then
    # Candidate image is running — align pointer/metadata to candidate.
    if ! write_candidate_deploy_version; then
      log "CRITICAL: reconciliation could not write candidate DEPLOY_VERSION"
      RECONCILIATION_STATUS="failed"
      return 1
    fi
    if ! validate_deploy_version_file \
      "${RELEASE_DIR}/DEPLOY_VERSION" "$RELEASE_ID" "$GIT_SHA" "$IMAGE_DIGEST"; then
      log "CRITICAL: reconciliation DEPLOY_VERSION validation failed"
      RECONCILIATION_STATUS="failed"
      return 1
    fi
    if [[ "$cur" != "$RELEASE_DIR" ]]; then
      if ! atomic_point_current "$RELEASE_DIR"; then
        log "CRITICAL: reconciliation atomic current switch failed"
        RECONCILIATION_STATUS="failed"
        return 1
      fi
    fi
    if ! verify_current_aligned_to "$RELEASE_DIR" "$RELEASE_ID" "$GIT_SHA" "$IMAGE_DIGEST"; then
      log "CRITICAL: reconciliation post-switch verification failed"
      RECONCILIATION_STATUS="failed"
      return 1
    fi
    RECONCILIATION_STATUS="aligned_candidate"
    log "post-replacement reconciliation: current aligned to running candidate (deploy remains failed)"
    return 0
  fi

  # Previous image still running (recreate never took effect) — keep/restore previous.
  prev_digest="$(_previous_deploy_digest 2>/dev/null || true)"
  if [[ -n "$running_digest" && -n "$prev_digest" && "$running_digest" == "$prev_digest" \
     && -n "${PREVIOUS_CURRENT:-}" && -d "${PREVIOUS_CURRENT}" \
     && -f "${PREVIOUS_CURRENT}/DEPLOY_VERSION" ]]; then
    local prev_rid prev_sha
    prev_rid="$(python3 - "${PREVIOUS_CURRENT}/DEPLOY_VERSION" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f).get("release_id") or "")
PY
)"
    prev_sha="$(python3 - "${PREVIOUS_CURRENT}/DEPLOY_VERSION" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f).get("git_sha") or "")
PY
)"
    if [[ -z "$prev_rid" || -z "$prev_sha" ]]; then
      log "CRITICAL: previous DEPLOY_VERSION incomplete during reconciliation"
      RECONCILIATION_STATUS="failed"
      return 1
    fi
    if [[ "$cur" != "$PREVIOUS_CURRENT" ]]; then
      if ! atomic_point_current "$PREVIOUS_CURRENT"; then
        log "CRITICAL: reconciliation could not restore previous current pointer"
        RECONCILIATION_STATUS="failed"
        return 1
      fi
    fi
    if ! verify_current_aligned_to "$PREVIOUS_CURRENT" "$prev_rid" "$prev_sha" "$prev_digest"; then
      log "CRITICAL: previous release alignment verification failed"
      RECONCILIATION_STATUS="failed"
      return 1
    fi
    RECONCILIATION_STATUS="aligned_previous"
    log "post-replacement reconciliation: previous API still running; current retained/restored"
    return 0
  fi

  log "CRITICAL: cannot reconcile running API image to candidate or previous release"
  RECONCILIATION_STATUS="failed"
  return 1
}

# Secret-free alignment check: running digest ↔ current ↔ DEPLOY_VERSION.
# Does not inspect container environment variables.
check_release_invariant() {
  local cur running_digest dv_digest dv_release
  INVARIANT_OK=0
  cur="$(_atomicity_readlink_current)"
  [[ -n "$cur" && -d "$cur" ]] || {
    log "CRITICAL: release invariant: current symlink missing or invalid"
    return 1
  }
  [[ -f "${cur}/DEPLOY_VERSION" ]] || {
    log "CRITICAL: release invariant: current/DEPLOY_VERSION missing"
    return 1
  }
  running_digest="$(_atomicity_running_api_digest 2>/dev/null || true)"
  [[ -n "$running_digest" ]] || {
    log "CRITICAL: release invariant: running API digest unavailable"
    return 1
  }
  dv_digest="$(python3 - "${cur}/DEPLOY_VERSION" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f).get("image_digest") or "")
PY
)"
  dv_release="$(python3 - "${cur}/DEPLOY_VERSION" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f).get("release_id") or "")
PY
)"
  if [[ -z "$dv_digest" || "$dv_digest" != "$running_digest" ]]; then
    log "CRITICAL: release invariant: DEPLOY_VERSION image_digest != running API digest"
    return 1
  fi
  if [[ -z "$dv_release" ]]; then
    log "CRITICAL: release invariant: DEPLOY_VERSION release_id missing"
    return 1
  fi
  # current directory basename should match release_id when under releases/
  if [[ "$(basename "$cur")" != "$dv_release" ]]; then
    log "CRITICAL: release invariant: current directory/release_id mismatch"
    return 1
  fi
  INVARIANT_OK=1
  return 0
}

# Apply atomicity policy inside on_exit (does not change exit code).
# Caller must already have forced FINAL_STATUS=failed on non-zero paths.
atomicity_on_failure() {
  local code="$1"

  if [[ "$code" -eq 0 ]]; then
    return 0
  fi

  # Post-replacement, pre-commit: reconcile to running image (OUTCOME 2).
  if [[ "${RELEASE_COMMITTED:-0}" -eq 0 && "${API_REPLACEMENT_OCCURRED:-0}" -eq 1 \
     && "${IN_ON_EXIT_RECONCILE:-0}" -eq 0 ]]; then
    IN_ON_EXIT_RECONCILE=1
    if ! reconcile_post_replacement_state; then
      log "CRITICAL: post-replacement reconciliation failed (operator action required)"
      case "${FAILURE_REASON:-}" in
        post_replacement_*|release_alignment_*) ;;
        "") FAILURE_REASON="post_replacement_reconciliation_failed" ;;
        *)
          # Preserve original stage reason; mark reconciliation failure explicitly.
          FAILURE_REASON="post_replacement_reconciliation_failed"
          ;;
      esac
    else
      # Keep original failure reason; annotate only when empty.
      if [[ -z "${FAILURE_REASON:-}" ]]; then
        FAILURE_REASON="post_replacement_pre_commit_failed"
      fi
    fi
  elif [[ "${RELEASE_COMMITTED:-0}" -eq 1 ]]; then
    log "release committed; retaining current symlink (no pointer-only rollback)"
  fi
  return 0
}

atomicity_invariant_before_evidence() {
  if [[ "${IN_ON_EXIT_INVARIANT:-0}" -ne 0 ]]; then
    return 0
  fi
  IN_ON_EXIT_INVARIANT=1

  # Nothing to align yet: pre-replacement failure on a host without current.
  if [[ ! -L "${ROOT}/current" && ! -e "${ROOT}/current" \
     && "${API_REPLACEMENT_OCCURRED:-0}" -eq 0 && "${RELEASE_COMMITTED:-0}" -eq 0 ]]; then
    INVARIANT_OK=1
    return 0
  fi

  if check_release_invariant; then
    return 0
  fi
  FINAL_STATUS="failed"
  # Preserve the original stage failure reason; only fill when empty.
  if [[ -z "${FAILURE_REASON:-}" ]]; then
    FAILURE_REASON="release_alignment_invariant_failed"
  fi
  log "CRITICAL: release alignment invariant failed (original failure_reason retained when set)"
  return 1
}
