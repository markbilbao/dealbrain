#!/usr/bin/env bash
# Sprint 25b.5n — shared constants and fail-closed helpers for the staging
# EC2 maintenance apply gate. Sourced by capture/apply operator scripts.
# shellcheck shell=bash

# Canonical maintenance acknowledgement — compared byte-for-byte (no trim,
# whitespace normalization, case folding, line-break flexibility, or substrings).
STAGING_MAINTENANCE_ACK_CANONICAL='I authorize temporary staging downtime caused by one EC2 stop/start for i-0edd57f32296aa323. I do not authorize replacement, destroy, production changes, or unrelated infrastructure changes.'

# Distinct recovery-readiness acknowledgement — also exact byte-for-byte.
STAGING_MAINTENANCE_RECOVERY_ACK_CANONICAL='I confirm a backup operator and same-instance recovery procedure are available for staging instance i-0edd57f32296aa323.'

STAGING_MAINTENANCE_ACCOUNT_ID='941035169846'
STAGING_MAINTENANCE_REGION='us-east-1'
STAGING_MAINTENANCE_WORKSPACE='default'
STAGING_MAINTENANCE_STATE_KEY='staging/terraform.tfstate'
STAGING_MAINTENANCE_BACKEND_BUCKET='dealbrain-terraform-state-941035169846'
STAGING_MAINTENANCE_INSTANCE_ID='i-0edd57f32296aa323'
STAGING_MAINTENANCE_EXPECTED_CREATE=1
STAGING_MAINTENANCE_EXPECTED_UPDATE=2
STAGING_MAINTENANCE_EXPECTED_REPLACE=0
STAGING_MAINTENANCE_EXPECTED_DESTROY=0
STAGING_MAINTENANCE_EXPECTED_READ=1
STAGING_MAINTENANCE_EC2_ADDRESS='module.ec2.aws_instance.api'
STAGING_MAINTENANCE_SSM_ADDRESS='module.ssm_rollback_document.aws_ssm_document.staging_rollback'
STAGING_MAINTENANCE_IAM_ADDRESS='module.github_deploy_role.aws_iam_role_policy.deploy_allow'
STAGING_MAINTENANCE_DATA_ADDRESS='module.github_deploy_role.data.aws_iam_policy_document.deploy_allow'
STAGING_MAINTENANCE_STAGING_TF_REL='infra/terraform/environments/staging'
STAGING_MAINTENANCE_SSM_DOC_NAME='DealBrain-StagingRollback'
STAGING_MAINTENANCE_SSM_DEPLOY_DOC_NAME='DealBrain-StagingDeploy'
STAGING_MAINTENANCE_IAM_ROLE_NAME='dealbrain-staging-gha-deploy'
STAGING_MAINTENANCE_IAM_ALLOW_POLICY_NAME='dealbrain-staging-gha-deploy-allow'
STAGING_MAINTENANCE_IAM_DENY_POLICY_NAME='dealbrain-staging-gha-deploy-deny'
STAGING_MAINTENANCE_RUN_NONCE=''
STAGING_MAINTENANCE_PLAN_IDENTITY_FILE=''

# shellcheck disable=SC2120
_staging_maintenance_lib_dir() {
  local src="${BASH_SOURCE[0]}"
  cd "$(dirname "$src")" && pwd
}

STAGING_MAINTENANCE_ASSERT_PY="$(
  _staging_maintenance_lib_dir
)/staging_maintenance_assert.py"

STAGING_MAINTENANCE_PHASE="${STAGING_MAINTENANCE_PHASE:-preflight}"
STAGING_MAINTENANCE_WORK_DIR="${STAGING_MAINTENANCE_WORK_DIR:-}"
STAGING_MAINTENANCE_WORK_OWNED=0
STAGING_MAINTENANCE_FAILED=0
STAGING_MAINTENANCE_DIAG_PRESERVED=0

_staging_maintenance_note() {
  printf '==> %s\n' "$*"
}

staging_maintenance_set_phase() {
  STAGING_MAINTENANCE_PHASE="$1"
}

staging_maintenance_fail() {
  # usage: staging_maintenance_fail <phase> <message...>
  local phase="$1"
  shift
  STAGING_MAINTENANCE_FAILED=1
  STAGING_MAINTENANCE_PHASE="$phase"
  printf 'FAIL_PHASE=%s\n' "$phase" >&2
  printf 'FAIL: %s\n' "$*" >&2
  printf '%s\n' \
    'RECOVERY: Follow the documented same-instance recovery procedure in docs/runbooks/STAGING_ROLLBACK.md.' \
    'Do not recreate the instance, perform state surgery, use terraform -target, ignore_changes,' \
    'automatic EC2 start unless separately authorized, Deploy Staging, Rollback Staging, or touch production.' \
    >&2
  exit 1
}

_staging_maintenance_die() {
  # Backward-compatible helper; defaults to current phase.
  staging_maintenance_fail "${STAGING_MAINTENANCE_PHASE:-preflight}" "$*"
}

staging_maintenance_require_no_target_flag() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      -target | -target=* | --target | --target=*)
        staging_maintenance_fail preflight "terraform -target is forbidden for this maintenance apply"
        ;;
    esac
  done
}

staging_maintenance_require_exact_string() {
  # Exact byte-for-byte equality; no normalization.
  local label="$1"
  local got="$2"
  local expected="$3"
  [[ -n "$got" ]] || staging_maintenance_fail preflight "${label} is required"
  if [[ "$got" != "$expected" ]]; then
    staging_maintenance_fail preflight "${label} does not match the canonical value (exact byte-for-byte match required; no whitespace/case/line-break flexibility)"
  fi
}

staging_maintenance_require_ack() {
  staging_maintenance_require_exact_string \
    "STAGING_MAINTENANCE_ACK" \
    "${STAGING_MAINTENANCE_ACK:-}" \
    "$STAGING_MAINTENANCE_ACK_CANONICAL"
}

staging_maintenance_require_recovery_ack() {
  staging_maintenance_require_exact_string \
    "STAGING_MAINTENANCE_RECOVERY_ACK" \
    "${STAGING_MAINTENANCE_RECOVERY_ACK:-}" \
    "$STAGING_MAINTENANCE_RECOVERY_ACK_CANONICAL"
}

staging_maintenance_require_demo_clear() {
  [[ "${STAGING_MAINTENANCE_DEMO_CLEAR:-}" == "1" ]] || staging_maintenance_fail preflight \
    "set STAGING_MAINTENANCE_DEMO_CLEAR=1 only when staging is not in a critical demo/test session"
}

staging_maintenance_require_apply_gates() {
  staging_maintenance_require_ack
  staging_maintenance_require_demo_clear
  staging_maintenance_require_recovery_ack
}

staging_maintenance_redact_line() {
  case "$1" in
    *DATABASE_URL* | *Password=* | *password=* | *SECRET* | *token=* | *Token=* | \
      *PRIVATE_KEY* | *BEGIN*PRIVATE* | *AWS_SECRET_ACCESS_KEY* | *AWS_SESSION_TOKEN*)
      printf '%s\n' "[REDACTED]"
      ;;
    *)
      printf '%s\n' "$1"
      ;;
  esac
}

staging_maintenance_create_work_dir() {
  local prefix="${1:-staging-maint}"
  local dir
  dir="$(mktemp -d "${TMPDIR:-/tmp}/${prefix}.XXXXXX")"
  chmod 700 "$dir"
  # Refuse to proceed if mktemp somehow returned a symlink path component abuse.
  if [[ -L "$dir" ]]; then
    rm -rf "$dir"
    staging_maintenance_fail preflight "work directory must not be a symlink"
  fi
  STAGING_MAINTENANCE_WORK_DIR="$dir"
  STAGING_MAINTENANCE_WORK_OWNED=1
  printf '%s\n' "$dir"
}

staging_maintenance_cleanup_work_dir() {
  local dir="${STAGING_MAINTENANCE_WORK_DIR:-}"
  [[ "$STAGING_MAINTENANCE_WORK_OWNED" == "1" ]] || return 0
  [[ -n "$dir" ]] || return 0
  # Only delete the mktemp directory we created; never a caller-supplied path.
  case "$dir" in
    /tmp/* | "${TMPDIR:-/tmp}"/*) ;;
    *)
      printf 'WARN: refusing to delete non-temp work dir %s\n' "$dir" >&2
      return 0
      ;;
  esac
  if [[ "$STAGING_MAINTENANCE_FAILED" == "1" ]]; then
    if [[ "$STAGING_MAINTENANCE_DIAG_PRESERVED" != "1" ]]; then
      printf '==> Non-secret diagnostics retained at %s (failed phase=%s)\n' \
        "$dir" "${STAGING_MAINTENANCE_PHASE:-unknown}" >&2
      STAGING_MAINTENANCE_DIAG_PRESERVED=1
    fi
    return 0
  fi
  rm -rf "$dir"
  STAGING_MAINTENANCE_WORK_DIR=""
  STAGING_MAINTENANCE_WORK_OWNED=0
}

staging_maintenance_install_exit_trap() {
  # shellcheck disable=SC2064
  trap 'staging_maintenance_cleanup_work_dir' EXIT
}

staging_maintenance_assert_py() {
  # Runs assert helper; on failure maps FAIL_PHASE from stderr when present.
  local default_phase="${STAGING_MAINTENANCE_PHASE:-preflight}"
  local err_file rc err_text phase
  [[ -f "$STAGING_MAINTENANCE_ASSERT_PY" ]] || staging_maintenance_fail preflight \
    "missing assert helper: ${STAGING_MAINTENANCE_ASSERT_PY}"
  err_file="$(mktemp "${TMPDIR:-/tmp}/staging-maint-assert.XXXXXX")"
  set +e
  python3 "$STAGING_MAINTENANCE_ASSERT_PY" "$@" 2>"$err_file"
  rc=$?
  set -e
  if [[ "$rc" -eq 0 ]]; then
    rm -f "$err_file"
    return 0
  fi
  err_text="$(cat "$err_file" 2>/dev/null || true)"
  rm -f "$err_file"
  printf '%s\n' "$err_text" >&2
  phase="$(printf '%s\n' "$err_text" | sed -n 's/^FAIL_PHASE=//p' | tail -n 1)"
  [[ -n "$phase" ]] || phase="$default_phase"
  staging_maintenance_fail "$phase" "assert helper failed (${default_phase})"
}

staging_maintenance_generate_run_nonce() {
  # Cryptographically strong nonce owned by this run's temp workspace.
  # Caller-supplied STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE is never authoritative.
  local work_dir="${1:-${STAGING_MAINTENANCE_WORK_DIR:-}}"
  local nonce_file nonce
  [[ -n "$work_dir" && -d "$work_dir" ]] || staging_maintenance_fail host_evidence_nonce \
    "work directory required before nonce generation"
  if [[ -n "${STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE:-}" ]]; then
    staging_maintenance_fail host_evidence_nonce \
      "STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE is not permitted; the run generates its own nonce"
  fi
  nonce_file="${work_dir}/host-evidence.nonce"
  if [[ -f "$nonce_file" ]]; then
    staging_maintenance_fail host_evidence_nonce \
      "refusing to regenerate nonce; host-evidence.nonce already exists for this run"
  fi
  nonce="$(python3 "$STAGING_MAINTENANCE_ASSERT_PY" generate-nonce)" \
    || staging_maintenance_fail host_evidence_nonce "nonce generation failed"
  # Strict format: 32 lowercase hex chars.
  [[ "$nonce" =~ ^[0-9a-f]{32}$ ]] || staging_maintenance_fail host_evidence_nonce \
    "generated nonce failed format check"
  umask 077
  printf '%s\n' "$nonce" >"$nonce_file"
  chmod 600 "$nonce_file"
  STAGING_MAINTENANCE_RUN_NONCE="$nonce"
  printf '%s\n' "$nonce"
}

staging_maintenance_write_host_evidence_collect_snippet() {
  # Writes a Session Manager collection snippet that embeds the run nonce.
  local out_path="$1"
  local phase="$2"
  local nonce="${3:-$STAGING_MAINTENANCE_RUN_NONCE}"
  local repo_sha="${4:-}"
  [[ -n "$nonce" ]] || staging_maintenance_fail host_evidence_nonce "run nonce required for collect snippet"
  [[ "$phase" == "pre-apply" || "$phase" == "post-apply" ]] \
    || staging_maintenance_fail host_evidence_phase "collect snippet phase must be pre-apply or post-apply"
  cat >"$out_path" <<EOF
#!/usr/bin/env bash
# Read-only Session Manager collection for staging maintenance host evidence.
# Instance: ${STAGING_MAINTENANCE_INSTANCE_ID}
# Phase: ${phase}
# Run nonce (embed exactly; do not invent another): ${nonce}
# Do not dump env, DATABASE_URL, tokens, or secrets. Do not use SSM SendCommand.
# Rollback-marker existence may use passwordless sudo (-n) for a read-only
# test -e only; never create/remove/chmod/chown/alter the marker.
set -Eeuo pipefail
python3 - <<'PY'
import json, subprocess, time
from pathlib import Path

ROLLBACK_MARKER_PATH = "/opt/dealbrain/runtime/rollback-execution.marker"

def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()

def rollback_marker_present() -> bool:
    """Read-only sudo-assisted marker existence check. Fail closed on ambiguity.

    Unprivileged Path.exists() is not authoritative: PermissionError while
    traversing /opt/dealbrain/runtime must not be treated as absence.
    """
    try:
        probe = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(
            f"sudo probe failed for rollback-marker check: {exc}"
        ) from exc
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout or "").strip()
        raise SystemExit(
            "passwordless sudo unavailable for rollback-marker check"
            + (f": {detail}" if detail else "")
        )

    try:
        check = subprocess.run(
            ["sudo", "-n", "test", "-e", ROLLBACK_MARKER_PATH],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(
            f"rollback-marker existence check failed: {exc}"
        ) from exc

    # Explicit classification only:
    #   0 -> present
    #   1 with empty stderr -> absent (POSIX test false)
    #   anything else -> fail closed (do not map all nonzero to absent)
    if check.returncode == 0:
        return True
    if check.returncode == 1:
        err = (check.stderr or "").strip()
        if err:
            raise SystemExit(
                f"rollback-marker existence check denied or failed: {err}"
            )
        return False
    detail = (check.stderr or check.stdout or "").strip()
    raise SystemExit(
        f"ambiguous rollback-marker existence check (rc={check.returncode}"
        + (f": {detail}" if detail else "")
        + ")"
    )

boot_id = read_text("/proc/sys/kernel/random/boot_id")
uptime_seconds = int(float(read_text("/proc/uptime").split()[0]))
cloud = "cloud-init-missing"
if Path("/usr/bin/cloud-init").exists() or Path("/usr/local/bin/cloud-init").exists():
    out = subprocess.check_output(["cloud-init", "status"], text=True, stderr=subprocess.STDOUT)
    line = out.strip().splitlines()[-1]
    cloud = line.split(":", 1)[-1].strip() if ":" in line else line

current = Path("/opt/dealbrain/current")
if not current.exists():
    raise SystemExit("missing /opt/dealbrain/current")
current_target = current.resolve().name
previous = Path("/opt/dealbrain/previous")
previous_pointer = previous.resolve().name if previous.exists() else None

dv = json.loads((current / "DEPLOY_VERSION").read_text(encoding="utf-8"))
release_id = dv["release_id"]
image_digest = dv.get("image_digest") or dv.get("digest")
marker = rollback_marker_present()

payload = {
    "schema_version": 1,
    "phase": "${phase}",
    "instance_id": "${STAGING_MAINTENANCE_INSTANCE_ID}",
    "account_id": "${STAGING_MAINTENANCE_ACCOUNT_ID}",
    "region": "${STAGING_MAINTENANCE_REGION}",
    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "nonce": "${nonce}",
    "boot_id": boot_id,
    "uptime_seconds": uptime_seconds,
    "cloud_init_status": cloud,
    "release_id": release_id,
    "image_digest": image_digest,
    "current_pointer": current_target,
    "previous_pointer": previous_pointer,
    "rollback_execution_marker_present": bool(marker),
}
repo_sha = "${repo_sha}"
if repo_sha:
    payload["repository_sha"] = repo_sha
print(json.dumps(payload, indent=2, sort_keys=True))
PY
EOF
  chmod 700 "$out_path"
}

staging_maintenance_validate_plan_json() {
  local plan_json="$1"
  staging_maintenance_set_phase plan_validation
  staging_maintenance_assert_py validate-plan "$plan_json"
}

staging_maintenance_plan_sha256() {
  staging_maintenance_assert_py sha256 "$1"
}

staging_maintenance_record_plan_identity() {
  local plan_path="$1"
  local work_dir="${2:-$STAGING_MAINTENANCE_WORK_DIR}"
  local identity_file="${work_dir}/plan.identity.json"
  staging_maintenance_set_phase plan_validation
  # Terraform may create the plan with a umask-derived mode; force 0600 first.
  chmod 600 "$plan_path" || staging_maintenance_fail plan_identity_mode \
    "failed to chmod plan to 0600"
  staging_maintenance_assert_py record-plan-identity "$plan_path" \
    --work-dir "$work_dir" --out "$identity_file"
  STAGING_MAINTENANCE_PLAN_IDENTITY_FILE="$identity_file"
}

staging_maintenance_verify_plan_file() {
  local plan_path="$1"
  local work_dir="${2:-$STAGING_MAINTENANCE_WORK_DIR}"
  local identity_file="${3:-${STAGING_MAINTENANCE_PLAN_IDENTITY_FILE}}"
  [[ -n "$identity_file" && -f "$identity_file" ]] \
    || staging_maintenance_fail plan_identity_checksum "missing plan identity record"
  staging_maintenance_set_phase plan_identity_checksum
  staging_maintenance_assert_py verify-plan-identity "$plan_path" \
    --identity-file "$identity_file" --work-dir "$work_dir"
}

staging_maintenance_require_artifact_mode_0600() {
  local path="$1"
  staging_maintenance_assert_py verify-artifact-mode "$path" --mode 600 \
    || staging_maintenance_fail plan_identity_mode "artifact mode must be 0600: ${path}"
}

staging_maintenance_require_plan_checksum_confirm() {
  local expected_sha="$1"
  local got="${STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM:-}"
  [[ -n "$got" ]] || staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM is required (exact SHA-256 of the reviewed plan)"
  [[ "$got" == "$expected_sha" ]] || staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM does not match the reviewed plan checksum"
}

staging_maintenance_validate_approved_plan_workdir() {
  # Fail-closed validation of the independently audited plan-only workdir.
  # usage: staging_maintenance_validate_approved_plan_workdir <repo_sha> <metadata_out>
  local repo_sha="$1"
  local metadata_out="$2"
  local approved="${STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR:-}"
  local checksum="${STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM:-}"
  staging_maintenance_set_phase preflight
  [[ -n "$approved" ]] || staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR is required in apply mode (exact audited plan-only workdir)"
  [[ -n "$repo_sha" ]] || staging_maintenance_fail preflight \
    "repository SHA required to validate approved plan workdir"
  [[ -n "$metadata_out" ]] || staging_maintenance_fail preflight \
    "approved-plan metadata output path required"
  [[ -n "$checksum" ]] || staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM is required (exact SHA-256 of the reviewed plan)"
  staging_maintenance_assert_py \
    validate-approved-plan-workdir "$approved" \
    --repository-sha "$repo_sha" \
    --plan-checksum "$checksum" \
    --out "$metadata_out"
}

staging_maintenance_write_plan_only_authority() {
  # Persist plan-only completion authority into the retained workdir.
  # usage: staging_maintenance_write_plan_only_authority <work_dir> <nonce> <repo_sha>
  local work_dir="$1"
  local nonce="$2"
  local repo_sha="$3"
  local authority="${work_dir}/plan-only.authority.log"
  local complete="${work_dir}/plan-only.complete"
  local repo_file="${work_dir}/repository.sha"
  [[ -n "$work_dir" && -d "$work_dir" ]] || staging_maintenance_fail preflight \
    "work directory required for plan-only authority marker"
  [[ -n "$nonce" ]] || staging_maintenance_fail host_evidence_nonce \
    "plan-only nonce required for authority marker"
  [[ -n "$repo_sha" ]] || staging_maintenance_fail preflight \
    "repository SHA required for plan-only authority marker"
  umask 077
  printf '%s\n' "$repo_sha" >"$repo_file"
  chmod 600 "$repo_file"
  {
    printf 'HOST_EVIDENCE_RUN_NONCE=%s\n' "$nonce"
    printf 'REPOSITORY_SHA=%s\n' "$repo_sha"
    printf 'Plan-only mode complete. Apply NOT executed.\n'
  } >"$authority"
  chmod 600 "$authority"
  printf 'Plan-only mode complete. Apply NOT executed.\n' >"$complete"
  chmod 600 "$complete"
}

staging_maintenance_host_evidence_ok() {
  # Non-fatal check (exit 0/1) for wait loops. Does not call staging_maintenance_fail.
  local path="$1"
  local phase="$2"
  local nonce="$3"
  local repo_sha="${4:-}"
  local args=(validate-host-evidence "$path" --phase "$phase" --nonce "$nonce")
  [[ -n "$repo_sha" ]] && args+=(--repository-sha "$repo_sha")
  [[ -f "$STAGING_MAINTENANCE_ASSERT_PY" ]] || return 1
  [[ -n "$path" && -f "$path" ]] || return 1
  python3 "$STAGING_MAINTENANCE_ASSERT_PY" "${args[@]}" >/dev/null 2>&1
}

staging_maintenance_validate_host_evidence() {
  local path="$1"
  local phase="$2"
  local nonce="${3:-$STAGING_MAINTENANCE_RUN_NONCE}"
  local repo_sha="${4:-}"
  local wait_s="${STAGING_MAINTENANCE_EVIDENCE_WAIT_SECONDS:-0}"
  local i=0
  local args=(validate-host-evidence "$path" --phase "$phase")
  [[ -n "$nonce" ]] || staging_maintenance_fail host_evidence_nonce \
    "run nonce required for host evidence validation"
  args+=(--nonce "$nonce")
  [[ -n "$repo_sha" ]] && args+=(--repository-sha "$repo_sha")
  staging_maintenance_set_phase host_evidence
  if [[ "$wait_s" -gt 0 ]]; then
    _staging_maintenance_note \
      "Waiting up to ${wait_s}s for ${phase} host evidence at ${path} (nonce=${nonce})"
    while [[ "$i" -le "$wait_s" ]]; do
      if staging_maintenance_host_evidence_ok "$path" "$phase" "$nonce" "$repo_sha"; then
        break
      fi
      if [[ "$i" -eq "$wait_s" ]]; then
        break
      fi
      sleep 1
      i=$((i + 1))
    done
  fi
  staging_maintenance_assert_py "${args[@]}"
}

staging_maintenance_retain_host_evidence() {
  # After external evidence passes validation, atomically retain a byte-identical
  # copy inside the authoritative work directory. Fail closed on any retention error.
  # usage: staging_maintenance_retain_host_evidence <source> <phase> [nonce] [repo_sha] [work_dir]
  local source_path="$1"
  local phase="$2"
  local nonce="${3:-$STAGING_MAINTENANCE_RUN_NONCE}"
  local repo_sha="${4:-}"
  local work_dir="${5:-$STAGING_MAINTENANCE_WORK_DIR}"
  local args
  [[ -n "$source_path" ]] || staging_maintenance_fail host_evidence_retention \
    "source host-evidence path required for retention"
  [[ -n "$work_dir" && -d "$work_dir" ]] || staging_maintenance_fail host_evidence_retention \
    "work directory required for host-evidence retention"
  [[ -n "$nonce" ]] || staging_maintenance_fail host_evidence_nonce \
    "run nonce required for host-evidence retention"
  [[ "$phase" == "pre-apply" || "$phase" == "post-apply" ]] \
    || staging_maintenance_fail host_evidence_phase \
      "retention phase must be pre-apply or post-apply"
  staging_maintenance_set_phase host_evidence_retention
  args=(
    retain-host-evidence "$source_path"
    --work-dir "$work_dir"
    --phase "$phase"
    --nonce "$nonce"
  )
  [[ -n "$repo_sha" ]] && args+=(--repository-sha "$repo_sha")
  staging_maintenance_assert_py "${args[@]}"
}

staging_maintenance_compare_host_evidence() {
  local pre="$1"
  local post="$2"
  local nonce="${3:-$STAGING_MAINTENANCE_RUN_NONCE}"
  local repo_sha="${4:-}"
  local args=(compare-host-evidence "$pre" "$post")
  [[ -n "$nonce" ]] && args+=(--nonce "$nonce")
  [[ -n "$repo_sha" ]] && args+=(--repository-sha "$repo_sha")
  staging_maintenance_set_phase release_integrity
  staging_maintenance_assert_py "${args[@]}"
}

staging_maintenance_verify_iam_policies() {
  local allow_json="$1"
  local deny_json="$2"
  staging_maintenance_set_phase iam_policy_verification
  staging_maintenance_assert_py validate-iam-allowlist "$allow_json" --deny-path "$deny_json"
}

staging_maintenance_verify_ssm_document() {
  local meta_json="$1"
  local content_json="$2"
  local version="${3:-}"
  staging_maintenance_set_phase ssm_document_content_verification
  staging_maintenance_assert_py validate-ssm-document "$meta_json" \
    --name "$STAGING_MAINTENANCE_SSM_DOC_NAME"
  local args=(validate-ssm-content "$content_json" --name "$STAGING_MAINTENANCE_SSM_DOC_NAME")
  [[ -n "$version" ]] && args+=(--version "$version")
  staging_maintenance_assert_py "${args[@]}"
}

staging_maintenance_backend_key_from_local_state() {
  python3 - <<'PY'
import json
from pathlib import Path
p = Path(".terraform/terraform.tfstate")
if not p.is_file():
    raise SystemExit("missing .terraform/terraform.tfstate after init")
data = json.loads(p.read_text(encoding="utf-8"))
backend = data.get("backend") or {}
cfg = backend.get("config") or {}
bucket = cfg.get("bucket") or ""
key = cfg.get("key") or ""
region = cfg.get("region") or ""
print(f"{bucket}\t{key}\t{region}")
PY
}

staging_maintenance_verify_backend_workspace() {
  local bucket key region ws meta
  staging_maintenance_set_phase preflight
  [[ -f .terraform/terraform.tfstate ]] || staging_maintenance_fail preflight \
    "terraform init did not produce .terraform/terraform.tfstate"
  meta="$(staging_maintenance_backend_key_from_local_state)" \
    || staging_maintenance_fail preflight "failed to parse backend metadata"
  IFS=$'\t' read -r bucket key region <<<"$meta"
  [[ "$bucket" == "$STAGING_MAINTENANCE_BACKEND_BUCKET" ]] || staging_maintenance_fail preflight \
    "backend bucket ${bucket} is not ${STAGING_MAINTENANCE_BACKEND_BUCKET}"
  [[ "$key" == "$STAGING_MAINTENANCE_STATE_KEY" ]] || staging_maintenance_fail preflight \
    "state key ${key} is not ${STAGING_MAINTENANCE_STATE_KEY}"
  [[ "$region" == "$STAGING_MAINTENANCE_REGION" ]] || staging_maintenance_fail preflight \
    "backend region ${region} is not ${STAGING_MAINTENANCE_REGION}"
  ws="$(terraform workspace show)" \
    || staging_maintenance_fail preflight "terraform workspace show failed"
  [[ "$ws" == "$STAGING_MAINTENANCE_WORKSPACE" ]] || staging_maintenance_fail preflight \
    "workspace ${ws} is not ${STAGING_MAINTENANCE_WORKSPACE}"
}

staging_maintenance_require_live_ec2_healthy() {
  local label="$1"
  local instance_json state sys inst
  staging_maintenance_set_phase preflight
  instance_json="$(aws ec2 describe-instances \
    --region "$STAGING_MAINTENANCE_REGION" \
    --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].{Id:InstanceId,State:State.Name}' \
    --output json)" \
    || staging_maintenance_fail preflight "${label}: describe-instances failed"
  state="$(printf '%s' "$instance_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["Id"]+"\t"+d["State"])')" \
    || staging_maintenance_fail preflight "${label}: parse instance json failed"
  local id
  IFS=$'\t' read -r id state <<<"$state"
  [[ "$id" == "$STAGING_MAINTENANCE_INSTANCE_ID" ]] || staging_maintenance_fail preflight \
    "${label}: instance id mismatch"
  [[ "$state" == "running" ]] || staging_maintenance_fail preflight \
    "${label}: EC2 state is ${state} (must be running)"
  sys="$(aws ec2 describe-instance-status \
    --region "$STAGING_MAINTENANCE_REGION" \
    --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
    --include-all-instances \
    --query 'InstanceStatuses[0].SystemStatus.Status' \
    --output text)" \
    || staging_maintenance_fail preflight "${label}: describe-instance-status (system) failed"
  inst="$(aws ec2 describe-instance-status \
    --region "$STAGING_MAINTENANCE_REGION" \
    --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
    --include-all-instances \
    --query 'InstanceStatuses[0].InstanceStatus.Status' \
    --output text)" \
    || staging_maintenance_fail preflight "${label}: describe-instance-status (instance) failed"
  [[ "$sys" == "ok" ]] || staging_maintenance_fail preflight \
    "${label}: EC2 system status is ${sys} (must be ok)"
  [[ "$inst" == "ok" ]] || staging_maintenance_fail preflight \
    "${label}: EC2 instance status is ${inst} (must be ok)"
  _staging_maintenance_note "${label}: EC2 ${id} running system=ok instance=ok"
}

staging_maintenance_require_live_alb_and_app() {
  local label="$1"
  local tg_arn alb_dns health target_id code
  staging_maintenance_set_phase preflight
  tg_arn="$(terraform output -raw alb_target_group_arn)" \
    || staging_maintenance_fail preflight "${label}: terraform output alb_target_group_arn failed"
  alb_dns="$(terraform output -raw alb_dns_name)" \
    || staging_maintenance_fail preflight "${label}: terraform output alb_dns_name failed"
  staging_maintenance_assert_py validate-tg-arn "$tg_arn" >/dev/null \
    || staging_maintenance_fail preflight "${label}: target group ARN rejected"
  staging_maintenance_assert_py validate-alb-dns "$alb_dns" >/dev/null \
    || staging_maintenance_fail preflight "${label}: ALB DNS rejected"
  health="$(aws elbv2 describe-target-health \
    --region "$STAGING_MAINTENANCE_REGION" \
    --target-group-arn "$tg_arn" \
    --output json)" \
    || staging_maintenance_fail preflight "${label}: describe-target-health failed"
  target_id="$(
    TARGET_HEALTH_JSON="$health" INSTANCE_ID="$STAGING_MAINTENANCE_INSTANCE_ID" python3 - <<'PY'
import json, os
data = json.loads(os.environ["TARGET_HEALTH_JSON"])
want = os.environ["INSTANCE_ID"]
matched = None
for th in data.get("TargetHealthDescriptions") or []:
    t = th.get("Target") or {}
    if t.get("Id") == want:
        matched = th
        break
if matched is None:
    print("MISSING")
    raise SystemExit(0)
state = ((matched.get("TargetHealth") or {}).get("State")) or "unknown"
print(state)
PY
  )" || staging_maintenance_fail preflight "${label}: parse target health failed"
  [[ "$target_id" != "MISSING" ]] || staging_maintenance_fail preflight \
    "${label}: instance ${STAGING_MAINTENANCE_INSTANCE_ID} not registered in target group"
  [[ "$target_id" == "healthy" ]] || staging_maintenance_fail preflight \
    "${label}: ALB target state is ${target_id} (must be healthy)"
  for path in /live /ready; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "http://${alb_dns}${path}")" \
      || staging_maintenance_fail application_health "${label}: curl ${path} failed"
    [[ "$code" == "200" ]] || staging_maintenance_fail application_health \
      "${label}: ${path} returned HTTP ${code} (want 200)"
  done
  STAGING_MAINTENANCE_TG_ARN="$tg_arn"
  STAGING_MAINTENANCE_ALB_DNS="$alb_dns"
  _staging_maintenance_note "${label}: ALB healthy; /live and /ready returned 200"
}

staging_maintenance_wait_ec2_healthy() {
  local attempts="${STAGING_MAINTENANCE_EC2_ATTEMPTS:-60}"
  local sleep_s="${STAGING_MAINTENANCE_POLL_SECONDS:-15}"
  local i state sys inst
  staging_maintenance_set_phase ec2_recovery_timeout
  for i in $(seq 1 "$attempts"); do
    state="$(aws ec2 describe-instances \
      --region "$STAGING_MAINTENANCE_REGION" \
      --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].State.Name' \
      --output text)" \
      || staging_maintenance_fail ec2_recovery_timeout "describe-instances failed during wait"
    sys="$(aws ec2 describe-instance-status \
      --region "$STAGING_MAINTENANCE_REGION" \
      --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
      --include-all-instances \
      --query 'InstanceStatuses[0].SystemStatus.Status' \
      --output text)" \
      || staging_maintenance_fail ec2_recovery_timeout "system status query failed during wait"
    inst="$(aws ec2 describe-instance-status \
      --region "$STAGING_MAINTENANCE_REGION" \
      --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
      --include-all-instances \
      --query 'InstanceStatuses[0].InstanceStatus.Status' \
      --output text)" \
      || staging_maintenance_fail ec2_recovery_timeout "instance status query failed during wait"
    _staging_maintenance_note "EC2 wait ${i}/${attempts} state=${state} system=${sys} instance=${inst}"
    if [[ "$state" == "running" && "$sys" == "ok" && "$inst" == "ok" ]]; then
      return 0
    fi
    if [[ "$i" -lt "$attempts" ]]; then
      sleep "$sleep_s"
    fi
  done
  staging_maintenance_fail ec2_recovery_timeout \
    "EC2 did not become running/ok/ok within ${attempts} attempts"
}

staging_maintenance_wait_alb_healthy() {
  local tg_arn="$1"
  local attempts="${STAGING_MAINTENANCE_ALB_ATTEMPTS:-40}"
  local sleep_s="${STAGING_MAINTENANCE_POLL_SECONDS:-15}"
  local i health
  staging_maintenance_set_phase alb_recovery_timeout
  for i in $(seq 1 "$attempts"); do
    health="$(aws elbv2 describe-target-health \
      --region "$STAGING_MAINTENANCE_REGION" \
      --target-group-arn "$tg_arn" \
      --output json)" \
      || staging_maintenance_fail alb_recovery_timeout "describe-target-health failed during wait"
    local state
    state="$(
      TARGET_HEALTH_JSON="$health" INSTANCE_ID="$STAGING_MAINTENANCE_INSTANCE_ID" python3 - <<'PY'
import json, os
data = json.loads(os.environ["TARGET_HEALTH_JSON"])
want = os.environ["INSTANCE_ID"]
for th in data.get("TargetHealthDescriptions") or []:
    t = th.get("Target") or {}
    if t.get("Id") == want:
        print(((th.get("TargetHealth") or {}).get("State")) or "unknown")
        raise SystemExit(0)
print("MISSING")
PY
    )" || staging_maintenance_fail alb_recovery_timeout "parse target health failed during wait"
    _staging_maintenance_note "ALB wait ${i}/${attempts} target=${STAGING_MAINTENANCE_INSTANCE_ID} state=${state}"
    if [[ "$state" == "healthy" ]]; then
      return 0
    fi
    if [[ "$i" -lt "$attempts" ]]; then
      sleep "$sleep_s"
    fi
  done
  staging_maintenance_fail alb_recovery_timeout \
    "ALB target did not become healthy within ${attempts} attempts"
}

staging_maintenance_probe_live_ready() {
  local alb_dns="$1"
  local label="${2:-post-apply}"
  local path code
  staging_maintenance_set_phase application_health
  staging_maintenance_assert_py validate-alb-dns "$alb_dns" >/dev/null \
    || staging_maintenance_fail application_health "${label}: ALB DNS rejected"
  for path in /live /ready; do
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "http://${alb_dns}${path}")" \
      || staging_maintenance_fail application_health "${label}: curl ${path} failed"
    [[ "$code" == "200" ]] || staging_maintenance_fail application_health \
      "${label}: ${path} returned HTTP ${code} (want 200)"
  done
}
