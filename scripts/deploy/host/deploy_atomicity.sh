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
  local migration_revision="${MIGRATION_AFTER:-${MIGRATION_REVISION:-}}"
  deployed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # migration_revision is recorded when known so rollback can prove DB compatibility
  # without inventing a separate release authority.
  if [[ -n "$migration_revision" ]]; then
    cat >"${RELEASE_DIR}/DEPLOY_VERSION" <<EOF
{
  "release_id": "${RELEASE_ID}",
  "git_sha": "${GIT_SHA}",
  "image_digest": "${IMAGE_DIGEST}",
  "deployed_at": "${deployed_at}",
  "migration_revision": "${migration_revision}"
}
EOF
  else
    cat >"${RELEASE_DIR}/DEPLOY_VERSION" <<EOF
{
  "release_id": "${RELEASE_ID}",
  "git_sha": "${GIT_SHA}",
  "image_digest": "${IMAGE_DIGEST}",
  "deployed_at": "${deployed_at}"
}
EOF
  fi
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

_atomic_point_symlink() {
  local link_name="$1"
  local target="$2"
  [[ -d "$target" ]] || return 1
  ln -sfn "$target" "${ROOT}/${link_name}.new"
  # Prefer GNU mv -Tf (staging EC2). Portable fallback for macOS unit-test hosts.
  if mv -Tf "${ROOT}/${link_name}.new" "${ROOT}/${link_name}" 2>/dev/null; then
    return 0
  fi
  local tmp="${ROOT}/${link_name}.prev.$$"
  if [[ -L "${ROOT}/${link_name}" || -e "${ROOT}/${link_name}" ]]; then
    mv -f "${ROOT}/${link_name}" "$tmp" || return 1
  fi
  if mv -f "${ROOT}/${link_name}.new" "${ROOT}/${link_name}"; then
    rm -f "$tmp"
    return 0
  fi
  if [[ -e "$tmp" || -L "$tmp" ]]; then
    mv -f "$tmp" "${ROOT}/${link_name}" || true
  fi
  return 1
}

atomic_point_current() {
  _atomic_point_symlink current "$1"
}

atomic_point_previous() {
  _atomic_point_symlink previous "$1"
}

_atomicity_readlink_previous() {
  if [[ -L "${ROOT}/previous" || -e "${ROOT}/previous" ]]; then
    readlink -f "${ROOT}/previous" 2>/dev/null || true
  fi
}

# Validate a path is a release directory under the approved release root.
_assert_release_dir_under_root() {
  local path="$1"
  [[ -n "$path" && -d "$path" ]] || return 1
  local releases="${ROOT}/releases"
  local resolved
  resolved="$(readlink -f "$path" 2>/dev/null || true)"
  [[ -n "$resolved" && -d "$resolved" ]] || return 1
  case "$resolved" in
    "${releases}"/*) return 0 ;;
    *) return 1 ;;
  esac
}

# Restore one pointer to its exact pre-mutation state (path or absent).
# Two symlinks are not one filesystem transaction; this is compensating restore.
_restore_pointer_state() {
  local link_name="$1"
  local original_target="$2" # empty => must be absent
  local had_link="$3"        # 1 if link existed before mutation
  rm -f "${ROOT}/${link_name}.new" || true
  if [[ "$had_link" -eq 1 && -n "$original_target" ]]; then
    _assert_release_dir_under_root "$original_target" || return 1
    _atomic_point_symlink "$link_name" "$original_target" || return 1
    return 0
  fi
  # Original was absent — restore absence (no fabricated pointer).
  rm -f "${ROOT}/${link_name}" || return 1
  if [[ -L "${ROOT}/${link_name}" || -e "${ROOT}/${link_name}" ]]; then
    return 1
  fi
  return 0
}

# After health success: previous <- displaced current (if any), current <- candidate.
# Pointers mutate only here for successful deploy/rollback commit paths.
#
# Compensating transaction (honest dual-symlink model):
#   1) Capture exact original current/previous states (path or absence)
#   2) Validate intended release directories under ROOT/releases
#   3) Prepare/replace each pointer atomically
#   4) On any failure, restore BOTH pointers to their exact originals
# Two symlink replacements are not a single filesystem transaction.
commit_current_and_previous_pointers() {
  local new_dir="$1"
  local displaced_dir="${2:-}"
  [[ -d "$new_dir" ]] || return 1
  _assert_release_dir_under_root "$new_dir" || {
    FAILURE_REASON="pointer_target_not_under_releases"
    return 1
  }

  local orig_current="" orig_previous=""
  local had_current=0 had_previous=0
  if [[ -L "${ROOT}/current" || -e "${ROOT}/current" ]]; then
    had_current=1
    orig_current="$(_atomicity_readlink_current || true)"
  fi
  if [[ -L "${ROOT}/previous" || -e "${ROOT}/previous" ]]; then
    had_previous=1
    orig_previous="$(_atomicity_readlink_previous || true)"
  fi

  if [[ "$had_current" -eq 1 ]]; then
    _assert_release_dir_under_root "$orig_current" || {
      FAILURE_REASON="pointer_original_current_invalid"
      return 1
    }
  fi
  if [[ "$had_previous" -eq 1 ]]; then
    _assert_release_dir_under_root "$orig_previous" || {
      FAILURE_REASON="pointer_original_previous_invalid"
      return 1
    }
  fi
  if [[ -n "$displaced_dir" && -d "$displaced_dir" && "$displaced_dir" != "$new_dir" ]]; then
    _assert_release_dir_under_root "$displaced_dir" || {
      FAILURE_REASON="pointer_displaced_not_under_releases"
      return 1
    }
  fi

  _compensate_restore_pointer_pair() {
    local restore_rc=0
    if ! _restore_pointer_state current "$orig_current" "$had_current"; then
      restore_rc=1
    fi
    if ! _restore_pointer_state previous "$orig_previous" "$had_previous"; then
      restore_rc=1
    fi
    rm -f "${ROOT}/current.new" "${ROOT}/previous.new" || true
    return "$restore_rc"
  }

  if [[ -n "$displaced_dir" && -d "$displaced_dir" && "$displaced_dir" != "$new_dir" ]]; then
    if ! atomic_point_previous "$displaced_dir"; then
      FAILURE_REASON="pointer_previous_update_failed"
      if ! _compensate_restore_pointer_pair; then
        FAILURE_REASON="pointer_pair_restore_failed"
      fi
      return 1
    fi
  fi

  if ! atomic_point_current "$new_dir"; then
    FAILURE_REASON="symlink_prepare_or_replace_failed"
    if ! _compensate_restore_pointer_pair; then
      FAILURE_REASON="pointer_pair_restore_failed"
    fi
    return 1
  fi
  return 0
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

# Commit contract: DEPLOY_VERSION validated, atomic current(+previous), post-checks, then flag.
# previous is updated only when a displaced prior release directory exists.
commit_release_pointer() {
  local displaced="${PREVIOUS_CURRENT:-}"
  write_candidate_deploy_version || {
    FAILURE_REASON="deploy_version_write_failed"
    return 1
  }
  validate_deploy_version_file \
    "${RELEASE_DIR}/DEPLOY_VERSION" "$RELEASE_ID" "$GIT_SHA" "$IMAGE_DIGEST" || {
    FAILURE_REASON="deploy_version_validation_failed"
    return 1
  }
  if [[ -z "$displaced" ]]; then
    displaced="$(_atomicity_readlink_current)"
  fi
  commit_current_and_previous_pointers "$RELEASE_DIR" "$displaced" || return 1
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
  # When a prior release was displaced, previous must point at it (forward-recovery).
  if [[ -n "$displaced" && -d "$displaced" && "$displaced" != "$RELEASE_DIR" ]]; then
    local prev_link
    prev_link="$(_atomicity_readlink_previous)"
    if [[ "$prev_link" != "$displaced" ]]; then
      FAILURE_REASON="pointer_previous_verification_failed"
      return 1
    fi
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
