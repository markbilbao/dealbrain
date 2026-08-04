#!/usr/bin/env bash
# Sprint 25b.5n / 25b.5q — controlled staging maintenance apply (fail closed).
#
# Hard identity (enforced via staging_maintenance_gate_lib.sh):
#   account 941035169846 | region us-east-1 | workspace default
#   state key staging/terraform.tfstate | instance i-0edd57f32296aa323
#
# Default mode is plan-only validation. Terraform apply runs ONLY when ALL of:
#   1) EXECUTE_MAINTENANCE_APPLY=1
#   2) exact STAGING_MAINTENANCE_ACK (byte-for-byte canonical)
#   3) STAGING_MAINTENANCE_DEMO_CLEAR=1
#   4) exact STAGING_MAINTENANCE_RECOVERY_ACK
#   5) STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR = exact independently audited
#      plan-only workdir (immutable candidate plan; apply does not regenerate)
#   6) exact STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM for that audited plan
#   7) live EC2/ALB/live/ready healthy
#   8) valid pre/post host-evidence JSON bound to the apply-run generated nonce
#   9) structural plan authority via terraform show -json on the audited binary
#
# Forbidden: terraform -target, ignore_changes workarounds, production apply,
# Deploy Staging / Rollback Staging, STAGING_MAINTENANCE_SKIP_INIT, SSM SendCommand.
set -Eeuo pipefail

ROOT="${STAGING_MAINTENANCE_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck source=staging_maintenance_gate_lib.sh
source "${ROOT}/scripts/deploy/staging_maintenance_gate_lib.sh"

STAGING_DIR="${ROOT}/${STAGING_MAINTENANCE_STAGING_TF_REL}"

MODE="plan-only"
if [[ "${EXECUTE_MAINTENANCE_APPLY:-0}" == "1" ]]; then
  MODE="apply"
fi

staging_maintenance_set_phase preflight
staging_maintenance_require_no_target_flag "$@"

# Reject removed/unsafe bypasses if present in the environment.
if [[ -n "${STAGING_MAINTENANCE_SKIP_INIT:-}" ]]; then
  staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_SKIP_INIT is not permitted on any apply-capable path"
fi
if [[ -n "${STAGING_MAINTENANCE_HEALTH_CLEAR:-}" ]]; then
  staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_HEALTH_CLEAR is removed; live EC2/ALB/live/ready checks are mandatory"
fi
if [[ -n "${STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE:-}" ]]; then
  staging_maintenance_fail host_evidence_nonce \
    "STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE is not permitted; nonce is generated internally per run"
fi
if [[ "$MODE" != "apply" && -n "${STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR:-}" ]]; then
  staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR is apply-mode only; omit it for plan-only"
fi

[[ -d "$STAGING_DIR" ]] || staging_maintenance_fail preflight "missing staging Terraform root: ${STAGING_DIR}"
command -v terraform >/dev/null 2>&1 || staging_maintenance_fail preflight "terraform is required"
command -v aws >/dev/null 2>&1 || staging_maintenance_fail preflight "aws CLI is required"
command -v python3 >/dev/null 2>&1 || staging_maintenance_fail preflight "python3 is required"
command -v curl >/dev/null 2>&1 || staging_maintenance_fail preflight "curl is required"
command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1 \
  || staging_maintenance_fail preflight "sha256sum or shasum is required"

# Apply-run private workdir (evidence/nonce/logs). Never the approved plan workdir.
WORK_DIR="$(staging_maintenance_create_work_dir staging-maint-apply)"
staging_maintenance_install_exit_trap
chmod 700 "$WORK_DIR"

POST_PLAN_TXT="${WORK_DIR}/staging-post-apply.plan.txt"
POST_PLAN_JSON="${WORK_DIR}/staging-post-apply.plan.json"
INVOCATION_LOG="${WORK_DIR}/invocation.log"
: >"$INVOCATION_LOG"
chmod 600 "$INVOCATION_LOG"

# --- Internal run nonce (authoritative for THIS run; not caller-selectable) ---
RUN_NONCE="$(staging_maintenance_generate_run_nonce "$WORK_DIR")"
_staging_maintenance_note "Generated host-evidence run nonce (stored only in work dir, mode 0600)"
_staging_maintenance_note "HOST_EVIDENCE_RUN_NONCE=${RUN_NONCE}"
staging_maintenance_write_host_evidence_collect_snippet \
  "${WORK_DIR}/host-evidence-collect-pre.sh" "pre-apply" "$RUN_NONCE"
staging_maintenance_write_host_evidence_collect_snippet \
  "${WORK_DIR}/host-evidence-collect-post.sh" "post-apply" "$RUN_NONCE"
_staging_maintenance_note "Session Manager collect (pre): ${WORK_DIR}/host-evidence-collect-pre.sh"
_staging_maintenance_note "Session Manager collect (post): ${WORK_DIR}/host-evidence-collect-post.sh"
_staging_maintenance_note "Embed nonce ${RUN_NONCE} exactly in both pre and post host-evidence JSON."

_staging_maintenance_note "Controlled maintenance procedure mode=${MODE} work_dir=${WORK_DIR}"

# --- 1) Repository gates ---
cd "$ROOT"
SHA="$(git rev-parse HEAD)" \
  || staging_maintenance_fail preflight "git rev-parse HEAD failed"
_staging_maintenance_note "Repository SHA=${SHA}"
# Re-write collect snippets with repository SHA binding when represented.
staging_maintenance_write_host_evidence_collect_snippet \
  "${WORK_DIR}/host-evidence-collect-pre.sh" "pre-apply" "$RUN_NONCE" "$SHA"
staging_maintenance_write_host_evidence_collect_snippet \
  "${WORK_DIR}/host-evidence-collect-post.sh" "post-apply" "$RUN_NONCE" "$SHA"
if [[ -n "$(git status --porcelain)" ]]; then
  staging_maintenance_fail preflight "working tree is not clean"
fi
if ! git rev-parse --verify origin/main >/dev/null 2>&1; then
  staging_maintenance_fail preflight "origin/main is required and must be fetchable"
fi
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
  staging_maintenance_fail preflight "HEAD is not synchronized with origin/main"
fi
if [[ -n "${STAGING_MAINTENANCE_REQUIRED_SHA:-}" ]]; then
  [[ "$SHA" == "$STAGING_MAINTENANCE_REQUIRED_SHA" ]] || staging_maintenance_fail preflight \
    "HEAD ${SHA} != required ${STAGING_MAINTENANCE_REQUIRED_SHA}"
fi
# Persist repository SHA for plan-only authority; apply mode also records it in its workdir.
printf '%s\n' "$SHA" >"${WORK_DIR}/repository.sha"
chmod 600 "${WORK_DIR}/repository.sha"

# --- 2) AWS account / region ---
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)" \
  || staging_maintenance_fail preflight "aws sts get-caller-identity failed"
REGION="$(aws configure get region 2>/dev/null || true)"
if [[ -z "$REGION" ]]; then
  REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-}}"
fi
[[ -n "$REGION" ]] || staging_maintenance_fail preflight "configured AWS region is unavailable"
[[ "$ACCOUNT" == "$STAGING_MAINTENANCE_ACCOUNT_ID" ]] || staging_maintenance_fail preflight \
  "account ${ACCOUNT} is not ${STAGING_MAINTENANCE_ACCOUNT_ID}"
[[ "$REGION" == "$STAGING_MAINTENANCE_REGION" ]] || staging_maintenance_fail preflight \
  "region ${REGION} is not ${STAGING_MAINTENANCE_REGION}"

# --- 3) Backend / workspace (init always; no skip) ---
cd "$STAGING_DIR"
_staging_maintenance_note "terraform init against staging backend (required)"
terraform init -input=false \
  -backend-config="bucket=${STAGING_MAINTENANCE_BACKEND_BUCKET}" \
  -backend-config="key=${STAGING_MAINTENANCE_STATE_KEY}" \
  -backend-config="region=${STAGING_MAINTENANCE_REGION}" \
  || staging_maintenance_fail preflight "terraform init failed"
staging_maintenance_verify_backend_workspace

APPROVED_PLAN_WORKDIR=""
PLAN_OUT=""
PLAN_TXT=""
PLAN_JSON=""
PLAN_SHA=""
PLAN_ONLY_NONCE=""

if [[ "$MODE" == "apply" ]]; then
  # --- 4a) Exact independently audited plan reuse (Sprint 25b.5q) ---
  staging_maintenance_set_phase preflight
  [[ -n "${STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR:-}" ]] || staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR is required in apply mode (exact audited plan-only workdir)"
  APPROVED_META_FILE="${WORK_DIR}/approved-plan.meta.json"
  staging_maintenance_validate_approved_plan_workdir "$SHA" "$APPROVED_META_FILE"
  [[ -f "$APPROVED_META_FILE" && ! -L "$APPROVED_META_FILE" ]] || staging_maintenance_fail preflight \
    "approved plan metadata missing after validation"
  APPROVED_PLAN_WORKDIR="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["workdir"])' "$APPROVED_META_FILE")"
  PLAN_OUT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["plan_path"])' "$APPROVED_META_FILE")"
  PLAN_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["plan_sha256"])' "$APPROVED_META_FILE")"
  PLAN_ONLY_NONCE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["plan_only_nonce"])' "$APPROVED_META_FILE")"
  PLAN_JSON="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["plan_json"])' "$APPROVED_META_FILE")"
  PLAN_TXT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["plan_txt"])' "$APPROVED_META_FILE")"
  STAGING_MAINTENANCE_PLAN_IDENTITY_FILE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["identity_file"])' "$APPROVED_META_FILE")"

  [[ "$RUN_NONCE" != "$PLAN_ONLY_NONCE" ]] || staging_maintenance_fail host_evidence_nonce \
    "apply-run nonce must not reuse the plan-only nonce; collect fresh apply pre/post evidence"
  [[ "$APPROVED_PLAN_WORKDIR" != "$WORK_DIR" ]] || staging_maintenance_fail preflight \
    "approved plan workdir must not be the apply-run private workdir"
  [[ -f "$PLAN_OUT" && ! -L "$PLAN_OUT" ]] || staging_maintenance_fail plan_identity_checksum \
    "approved plan binary missing after validation"
  _staging_maintenance_note "Using exact independently audited plan at ${PLAN_OUT}"
  _staging_maintenance_note "Reviewed plan SHA-256: ${PLAN_SHA}"
  _staging_maintenance_note "Approved plan workdir (immutable): ${APPROVED_PLAN_WORKDIR}"
  _staging_maintenance_note "Apply-run private workdir (fresh evidence): ${WORK_DIR}"
  _staging_maintenance_note "Apply does NOT regenerate, copy, or replace the audited plan binary."

  # Read-only show against the exact retained binary into the apply workdir only.
  staging_maintenance_set_phase plan_validation
  SHOW_JSON="${WORK_DIR}/approved-plan.show.json"
  SHOW_TXT="${WORK_DIR}/approved-plan.show.txt"
  umask 077
  terraform show -no-color "$PLAN_OUT" | tee "$SHOW_TXT" \
    || staging_maintenance_fail plan_validation "terraform show text failed for approved plan"
  terraform show -json "$PLAN_OUT" >"$SHOW_JSON" \
    || staging_maintenance_fail plan_validation "terraform show -json failed for approved plan"
  chmod 600 "$SHOW_JSON" "$SHOW_TXT"
  staging_maintenance_require_artifact_mode_0600 "$SHOW_JSON"
  staging_maintenance_require_artifact_mode_0600 "$SHOW_TXT"
  staging_maintenance_validate_plan_json "$SHOW_JSON"
  # Retained plan JSON must still pass structural authority (byte inventory already checked).
  staging_maintenance_validate_plan_json "$PLAN_JSON"
  staging_maintenance_require_artifact_mode_0600 "$PLAN_OUT"
  staging_maintenance_require_artifact_mode_0600 "$PLAN_JSON"
  staging_maintenance_require_artifact_mode_0600 "$PLAN_TXT"
  staging_maintenance_verify_plan_file "$PLAN_OUT" "$APPROVED_PLAN_WORKDIR" \
    "$STAGING_MAINTENANCE_PLAN_IDENTITY_FILE"
else
  # --- 4b) Plan-only: generate immutable candidate plan into THIS workdir ---
  PLAN_OUT="${WORK_DIR}/staging-combined.tfplan"
  PLAN_TXT="${WORK_DIR}/staging-combined.plan.txt"
  PLAN_JSON="${WORK_DIR}/staging-combined.plan.json"

  PRE_EVIDENCE="${STAGING_MAINTENANCE_HOST_EVIDENCE_PRE:-}"
  [[ -n "$PRE_EVIDENCE" ]] || staging_maintenance_fail host_evidence \
    "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE must point to a pre-apply host-evidence JSON file (nonce=${RUN_NONCE})"
  staging_maintenance_validate_host_evidence "$PRE_EVIDENCE" "pre-apply" "$RUN_NONCE" "$SHA"
  staging_maintenance_retain_host_evidence "$PRE_EVIDENCE" "pre-apply" "$RUN_NONCE" "$SHA" "$WORK_DIR"
  RETAINED_PRE="${WORK_DIR}/host-evidence-pre.json"
  [[ -f "$RETAINED_PRE" && ! -L "$RETAINED_PRE" ]] || staging_maintenance_fail host_evidence_retention \
    "retained pre-apply host evidence missing after retention"
  _staging_maintenance_note "Retained validated pre-apply host evidence at ${RETAINED_PRE}"

  staging_maintenance_require_live_ec2_healthy "pre-plan"
  staging_maintenance_require_live_alb_and_app "pre-plan"

  staging_maintenance_set_phase plan_validation
  _staging_maintenance_note "Generating fresh saved plan (no -target)"
  umask 077
  terraform plan -input=false -lock=false -out "$PLAN_OUT" | tee "$PLAN_TXT" \
    || staging_maintenance_fail plan_validation "terraform plan failed"
  terraform show -no-color "$PLAN_OUT" | tee -a "$PLAN_TXT" \
    || staging_maintenance_fail plan_validation "terraform show text failed"
  terraform show -json "$PLAN_OUT" >"$PLAN_JSON" \
    || staging_maintenance_fail plan_validation "terraform show -json failed"
  chmod 600 "$PLAN_OUT" "$PLAN_JSON" "$PLAN_TXT"
  staging_maintenance_require_artifact_mode_0600 "$PLAN_OUT"
  staging_maintenance_require_artifact_mode_0600 "$PLAN_JSON"
  staging_maintenance_require_artifact_mode_0600 "$PLAN_TXT"
  staging_maintenance_validate_plan_json "$PLAN_JSON"

  staging_maintenance_record_plan_identity "$PLAN_OUT" "$WORK_DIR"
  PLAN_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["sha256"])' \
    "$STAGING_MAINTENANCE_PLAN_IDENTITY_FILE")" \
    || staging_maintenance_fail plan_identity_checksum "failed to read recorded plan checksum"
  _staging_maintenance_note "Reviewed plan SHA-256: ${PLAN_SHA}"
  _staging_maintenance_note "Reviewed plan identity: ${STAGING_MAINTENANCE_PLAN_IDENTITY_FILE} (uid/gid/mode=0600/dev/inode bound)"

  [[ -f "$RETAINED_PRE" && ! -L "$RETAINED_PRE" ]] || staging_maintenance_fail host_evidence_retention \
    "plan-only success requires retained ${WORK_DIR}/host-evidence-pre.json"
  staging_maintenance_write_plan_only_authority "$WORK_DIR" "$RUN_NONCE" "$SHA"
  _staging_maintenance_note "Plan-only mode complete. Apply NOT executed."
  _staging_maintenance_note "Host-evidence run nonce for this review: ${RUN_NONCE}"
  _staging_maintenance_note "Collect snippets (same nonce) are in ${WORK_DIR}."
  _staging_maintenance_note "Validated pre-apply host evidence retained at ${RETAINED_PRE}"
  _staging_maintenance_note "Plan-only retains pre-apply evidence only (no post-apply evidence invented)."
  _staging_maintenance_note "Do not manually inject evidence into a completed workdir."
  _staging_maintenance_note "Apply mode generates its own nonce; collect pre/post evidence with that run's snippets."
  _staging_maintenance_note "Do not set STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE (rejected)."
  _staging_maintenance_note "To apply after independent audit APPROVE + all gates + checksum confirm:"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR=${WORK_DIR}"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_ACK='…exact canonical string…'"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_RECOVERY_ACK='…exact recovery string…'"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_DEMO_CLEAR=1"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM=${PLAN_SHA}"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_HOST_EVIDENCE_PRE=/path/to/apply-run-pre.json"
  _staging_maintenance_note "  export STAGING_MAINTENANCE_HOST_EVIDENCE_POST=/path/to/apply-run-post.json"
  _staging_maintenance_note "  EXECUTE_MAINTENANCE_APPLY=1 bash scripts/deploy/staging_maintenance_controlled_apply.sh"
  _staging_maintenance_note "Deploy Staging remains AFTER Terraform verification. Rollback Staging unauthorized here."
  # Retain work dir on plan-only success (plan + identity + nonce + snippets + host-evidence-pre.json).
  STAGING_MAINTENANCE_WORK_OWNED=0
  _staging_maintenance_note "Plan-only artifacts retained at ${WORK_DIR}"
  exit 0
fi

# --- Apply path continues: fresh apply-run pre-evidence (separate from plan-only) ---
PRE_EVIDENCE="${STAGING_MAINTENANCE_HOST_EVIDENCE_PRE:-}"
[[ -n "$PRE_EVIDENCE" ]] || staging_maintenance_fail host_evidence \
  "STAGING_MAINTENANCE_HOST_EVIDENCE_PRE must point to a pre-apply host-evidence JSON file (nonce=${RUN_NONCE})"
# Refuse to treat the approved plan workdir's retained evidence as apply-run input by injection.
case "$PRE_EVIDENCE" in
  "${APPROVED_PLAN_WORKDIR}" | "${APPROVED_PLAN_WORKDIR}"/*)
    staging_maintenance_fail host_evidence \
      "apply-run host evidence must not be sourced from the approved plan workdir; collect fresh evidence"
    ;;
esac
staging_maintenance_validate_host_evidence "$PRE_EVIDENCE" "pre-apply" "$RUN_NONCE" "$SHA"
staging_maintenance_retain_host_evidence "$PRE_EVIDENCE" "pre-apply" "$RUN_NONCE" "$SHA" "$WORK_DIR"
RETAINED_PRE="${WORK_DIR}/host-evidence-pre.json"
[[ -f "$RETAINED_PRE" && ! -L "$RETAINED_PRE" ]] || staging_maintenance_fail host_evidence_retention \
  "retained pre-apply host evidence missing after retention"
_staging_maintenance_note "Retained validated pre-apply host evidence at ${RETAINED_PRE}"

staging_maintenance_require_live_ec2_healthy "pre-plan"
staging_maintenance_require_live_alb_and_app "pre-plan"
PRE_TG_ARN="$STAGING_MAINTENANCE_TG_ARN"
PRE_ALB_DNS="$STAGING_MAINTENANCE_ALB_DNS"

PRE_RELEASE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["release_id"])' "$RETAINED_PRE")"
PRE_DIGEST="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["image_digest"])' "$RETAINED_PRE")"
PRE_CURRENT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["current_pointer"])' "$RETAINED_PRE")"
PRE_PREVIOUS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1],encoding="utf-8")).get("previous_pointer"); print("" if v is None else v)' "$RETAINED_PRE")"

# --- Apply-capable gates ---
staging_maintenance_set_phase preflight
staging_maintenance_require_apply_gates
staging_maintenance_require_plan_checksum_confirm "$PLAN_SHA"
_staging_maintenance_note "Maintenance ACK + demo clearance + recovery ACK + plan checksum accepted"

# Re-verify live health immediately before apply.
staging_maintenance_require_live_ec2_healthy "pre-apply"
staging_maintenance_require_live_alb_and_app "pre-apply"
PRE_TG_ARN="$STAGING_MAINTENANCE_TG_ARN"
PRE_ALB_DNS="$STAGING_MAINTENANCE_ALB_DNS"

# Immutable plan identity immediately before apply (path/dev/inode/size/uid/gid/mode/sha256).
# Bind against the APPROVED plan workdir — never copy the plan into the apply workdir.
staging_maintenance_verify_plan_file "$PLAN_OUT" "$APPROVED_PLAN_WORKDIR" \
  "$STAGING_MAINTENANCE_PLAN_IDENTITY_FILE"
[[ ! -L "$PLAN_OUT" ]] || staging_maintenance_fail plan_identity_mode "plan path must not be a symlink"
[[ -f "$PLAN_OUT" ]] || staging_maintenance_fail plan_identity_checksum "plan path missing before apply"
staging_maintenance_require_artifact_mode_0600 "$PLAN_JSON"
staging_maintenance_require_artifact_mode_0600 "$PLAN_TXT"

# Apply eligibility requires retained validated pre-apply evidence already in apply work dir.
[[ -f "$RETAINED_PRE" && ! -L "$RETAINED_PRE" ]] || staging_maintenance_fail host_evidence_retention \
  "apply eligibility requires retained ${WORK_DIR}/host-evidence-pre.json"
staging_maintenance_require_artifact_mode_0600 "$RETAINED_PRE"
staging_maintenance_validate_host_evidence "$RETAINED_PRE" "pre-apply" "$RUN_NONCE" "$SHA"

# --- Apply exact audited saved plan (never regenerate / never copy) ---
staging_maintenance_set_phase apply
_staging_maintenance_note "Applying exact reviewed saved plan ${PLAN_OUT}"
printf 'terraform_apply %s\n' "$PLAN_OUT" >>"$INVOCATION_LOG"
# Terraform native saved-plan/state lineage + serial checks remain authoritative:
# a stale plan against newer state fails closed here without repository bypass.
terraform apply -input=false "$PLAN_OUT" \
  || staging_maintenance_fail apply "terraform apply failed (including native stale saved-plan rejection)"

# --- Post-apply monitoring (fail closed) ---
AFTER_ID="$(aws ec2 describe-instances \
  --region "$STAGING_MAINTENANCE_REGION" \
  --instance-ids "$STAGING_MAINTENANCE_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)" \
  || staging_maintenance_fail ec2_recovery_timeout "post-apply describe-instances failed"
[[ "$AFTER_ID" == "$STAGING_MAINTENANCE_INSTANCE_ID" ]] || staging_maintenance_fail ec2_recovery_timeout \
  "instance identity changed after apply — escalate (no recreate improvisation)"

staging_maintenance_wait_ec2_healthy
staging_maintenance_wait_alb_healthy "$PRE_TG_ARN"
staging_maintenance_probe_live_ready "$PRE_ALB_DNS" "post-apply"

POST_EVIDENCE="${STAGING_MAINTENANCE_HOST_EVIDENCE_POST:-}"
[[ -n "$POST_EVIDENCE" ]] || staging_maintenance_fail host_evidence \
  "STAGING_MAINTENANCE_HOST_EVIDENCE_POST must point to a post-apply host-evidence JSON file (nonce=${RUN_NONCE})"
case "$POST_EVIDENCE" in
  "${APPROVED_PLAN_WORKDIR}" | "${APPROVED_PLAN_WORKDIR}"/*)
    staging_maintenance_fail host_evidence \
      "apply-run host evidence must not be sourced from the approved plan workdir; collect fresh evidence"
    ;;
esac
# Same apply-run generated nonce — do not create a second nonce for post evidence.
staging_maintenance_validate_host_evidence "$POST_EVIDENCE" "post-apply" "$RUN_NONCE" "$SHA"
# Retain post evidence only after post validation succeeds (never invent in plan-only).
staging_maintenance_retain_host_evidence "$POST_EVIDENCE" "post-apply" "$RUN_NONCE" "$SHA" "$WORK_DIR"
RETAINED_POST="${WORK_DIR}/host-evidence-post.json"
[[ -f "$RETAINED_POST" && ! -L "$RETAINED_POST" ]] || staging_maintenance_fail host_evidence_retention \
  "retained post-apply host evidence missing after retention"
_staging_maintenance_note "Retained validated post-apply host evidence at ${RETAINED_POST}"

COMPARE_JSON="$(staging_maintenance_compare_host_evidence "$RETAINED_PRE" "$RETAINED_POST" "$RUN_NONCE" "$SHA")" \
  || staging_maintenance_fail release_integrity "host evidence comparison failed"
printf '%s\n' "$COMPARE_JSON" >"${WORK_DIR}/host-evidence-compare.json"
chmod 600 "${WORK_DIR}/host-evidence-compare.json"

POST_RELEASE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["release_id"])' "$RETAINED_POST")"
POST_DIGEST="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["image_digest"])' "$RETAINED_POST")"
POST_CURRENT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["current_pointer"])' "$RETAINED_POST")"
POST_PREVIOUS="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1],encoding="utf-8")).get("previous_pointer"); print("" if v is None else v)' "$RETAINED_POST")"
[[ "$POST_RELEASE" == "$PRE_RELEASE" ]] || staging_maintenance_fail release_integrity \
  "release_id changed (${PRE_RELEASE} -> ${POST_RELEASE})"
[[ "$POST_DIGEST" == "$PRE_DIGEST" ]] || staging_maintenance_fail release_integrity \
  "image_digest changed"
[[ "$POST_CURRENT" == "$PRE_CURRENT" ]] || staging_maintenance_fail release_integrity \
  "current_pointer changed"
[[ "$POST_PREVIOUS" == "$PRE_PREVIOUS" ]] || staging_maintenance_fail release_integrity \
  "previous_pointer changed"

# Terraform outputs — exact expected rollback SSM outputs
staging_maintenance_set_phase preflight
DOC_NAME="$(terraform output -raw ssm_rollback_document_name)" \
  || staging_maintenance_fail preflight "missing ssm_rollback_document_name output"
DOC_ARN="$(terraform output -raw ssm_rollback_document_arn)" \
  || staging_maintenance_fail preflight "missing ssm_rollback_document_arn output"
[[ "$DOC_NAME" == "$STAGING_MAINTENANCE_SSM_DOC_NAME" ]] || staging_maintenance_fail preflight \
  "ssm_rollback_document_name ${DOC_NAME} != ${STAGING_MAINTENANCE_SSM_DOC_NAME}"
[[ "$DOC_ARN" == arn:aws:ssm:${STAGING_MAINTENANCE_REGION}:${STAGING_MAINTENANCE_ACCOUNT_ID}:document/${STAGING_MAINTENANCE_SSM_DOC_NAME} ]] \
  || staging_maintenance_fail preflight "ssm_rollback_document_arn unexpected: ${DOC_ARN}"

# SSM metadata + exact document content (default active version)
aws ssm describe-document \
  --region "$STAGING_MAINTENANCE_REGION" \
  --name "$STAGING_MAINTENANCE_SSM_DOC_NAME" \
  --query '{Name:Name,Status:Status,DocumentType:DocumentType,DocumentVersion:DocumentVersion,DefaultVersion:DefaultVersion,Owner:Owner}' \
  --output json >"${WORK_DIR}/ssm-document.json" \
  || staging_maintenance_fail ssm_document_content_verification "ssm describe-document failed"
chmod 600 "${WORK_DIR}/ssm-document.json"
DOC_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["DocumentVersion"])' \
  "${WORK_DIR}/ssm-document.json")"
aws ssm get-document \
  --region "$STAGING_MAINTENANCE_REGION" \
  --name "$STAGING_MAINTENANCE_SSM_DOC_NAME" \
  --document-version "$DOC_VERSION" \
  --output json >"${WORK_DIR}/ssm-document-content.json" \
  || staging_maintenance_fail ssm_document_content_verification "ssm get-document failed"
chmod 600 "${WORK_DIR}/ssm-document-content.json"
# Document creation/describe/get must not invoke the document (no SendCommand).
if grep -E 'SendCommand|start-automation|StartAutomation' "$INVOCATION_LOG" >/dev/null 2>&1; then
  staging_maintenance_fail ssm_document_content_verification \
    "SSM document verification must not invoke the document"
fi
staging_maintenance_verify_ssm_document \
  "${WORK_DIR}/ssm-document.json" \
  "${WORK_DIR}/ssm-document-content.json" \
  "$DOC_VERSION"

# IAM structural verification (allow + deny)
aws iam get-role-policy \
  --role-name "$STAGING_MAINTENANCE_IAM_ROLE_NAME" \
  --policy-name "$STAGING_MAINTENANCE_IAM_ALLOW_POLICY_NAME" \
  --query 'PolicyDocument' \
  --output json >"${WORK_DIR}/iam-deploy-allow.json" \
  || staging_maintenance_fail iam_policy_verification "iam get-role-policy (allow) failed"
aws iam get-role-policy \
  --role-name "$STAGING_MAINTENANCE_IAM_ROLE_NAME" \
  --policy-name "$STAGING_MAINTENANCE_IAM_DENY_POLICY_NAME" \
  --query 'PolicyDocument' \
  --output json >"${WORK_DIR}/iam-deploy-deny.json" \
  || staging_maintenance_fail iam_policy_verification "iam get-role-policy (deny) failed"
chmod 600 "${WORK_DIR}/iam-deploy-allow.json" "${WORK_DIR}/iam-deploy-deny.json"
staging_maintenance_verify_iam_policies \
  "${WORK_DIR}/iam-deploy-allow.json" \
  "${WORK_DIR}/iam-deploy-deny.json"

# --- Fresh post-apply read-only plan: no unexplained residual drift ---
# This residual check is not a replacement for the audited maintenance plan.
staging_maintenance_set_phase post_plan_drift
set +e
terraform plan -input=false -lock=false -detailed-exitcode -out "${WORK_DIR}/post.tfplan" \
  >"$POST_PLAN_TXT" 2>&1
plan_code=$?
set -e
chmod 600 "$POST_PLAN_TXT" || true
if [[ "$plan_code" -eq 1 ]]; then
  staging_maintenance_fail post_plan_drift "post-apply terraform plan failed"
fi
if [[ "$plan_code" -eq 2 ]]; then
  terraform show -json "${WORK_DIR}/post.tfplan" >"$POST_PLAN_JSON" \
    || staging_maintenance_fail post_plan_drift "post-apply plan show -json failed"
  chmod 600 "$POST_PLAN_JSON" || true
  # Residual drift is forbidden after this maintenance apply.
  staging_maintenance_fail post_plan_drift \
    "post-apply plan shows residual changes — investigate before Deploy Staging"
fi
_staging_maintenance_note "Post-apply plan: no residual changes"

# --- Stop before Deploy Staging ---
[[ -f "$RETAINED_PRE" && ! -L "$RETAINED_PRE" ]] || staging_maintenance_fail host_evidence_retention \
  "apply success requires retained ${WORK_DIR}/host-evidence-pre.json"
[[ -f "$RETAINED_POST" && ! -L "$RETAINED_POST" ]] || staging_maintenance_fail host_evidence_retention \
  "apply success requires retained ${WORK_DIR}/host-evidence-post.json"
_staging_maintenance_note "STOP before Deploy Staging."
_staging_maintenance_note "Rollback Staging remains unauthorized until Deploy Staging installs tooling and later audits pass."
_staging_maintenance_note "Do not touch production."
_staging_maintenance_note "Do not manually inject evidence into a completed workdir."
_staging_maintenance_note "Validated host evidence retained: ${RETAINED_PRE} and ${RETAINED_POST}"
_staging_maintenance_note "Audited plan remained immutable at ${PLAN_OUT}"
_staging_maintenance_note "Maintenance apply verification complete (Terraform apply + health + integrity + IAM/SSM structural checks)."
# Retain apply work dir on success (fresh evidence + show artifacts; approved plan stays separate).
STAGING_MAINTENANCE_WORK_OWNED=0
_staging_maintenance_note "Apply artifacts retained at ${WORK_DIR}"
