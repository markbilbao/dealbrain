#!/usr/bin/env bash
# Sprint 25b.5n — fail-closed read-only pre-apply capture for the staging
# maintenance gate.
# Hard identity: account 941035169846 | region us-east-1 | workspace default
# state key staging/terraform.tfstate | instance i-0edd57f32296aa323
# Does not run terraform apply, does not stop/start EC2, does not deploy,
# and does not SendCommand (host facts are collected via Session Manager into
# a strict host-evidence JSON file).
set -Eeuo pipefail

ROOT="${STAGING_MAINTENANCE_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
# shellcheck source=staging_maintenance_gate_lib.sh
source "${ROOT}/scripts/deploy/staging_maintenance_gate_lib.sh"

staging_maintenance_set_phase preflight
staging_maintenance_require_no_target_flag "$@"

if [[ -n "${STAGING_MAINTENANCE_SKIP_INIT:-}" ]]; then
  staging_maintenance_fail preflight \
    "STAGING_MAINTENANCE_SKIP_INIT is not permitted"
fi

[[ -d "${ROOT}/${STAGING_MAINTENANCE_STAGING_TF_REL}" ]] || staging_maintenance_fail preflight \
  "missing staging Terraform root"
command -v terraform >/dev/null 2>&1 || staging_maintenance_fail preflight "terraform is required"
command -v aws >/dev/null 2>&1 || staging_maintenance_fail preflight "aws CLI is required"
command -v python3 >/dev/null 2>&1 || staging_maintenance_fail preflight "python3 is required"
command -v curl >/dev/null 2>&1 || staging_maintenance_fail preflight "curl is required"

OUT_DIR="$(staging_maintenance_create_work_dir staging-maint-capture)"
# Capture artifacts are retained for operator review (do not install deletion trap).
STAGING_MAINTENANCE_WORK_OWNED=0
chmod 700 "$OUT_DIR"
REPORT="${OUT_DIR}/pre-apply-capture.txt"
: >"$REPORT"

log() {
  staging_maintenance_redact_line "$1" | tee -a "$REPORT" >/dev/null
  staging_maintenance_redact_line "$1"
}

section() {
  log ""
  log "### $1"
}

_staging_maintenance_note "Pre-apply capture (read-only, fail-closed) → ${OUT_DIR}"

section "Repository"
cd "$ROOT"
log "branch: $(git branch --show-current)"
log "sha: $(git rev-parse HEAD)"
if [[ -z "$(git status --porcelain)" ]]; then
  log "working_tree: clean"
else
  log "working_tree: dirty"
  git status --porcelain | while IFS= read -r line; do log "  ${line}"; done
fi
git rev-parse --verify origin/main >/dev/null 2>&1 \
  || staging_maintenance_fail preflight "origin/main is required"
log "origin_main_sha: $(git rev-parse origin/main)"
if [[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]]; then
  log "origin_main_sync: yes"
else
  log "origin_main_sync: no"
fi

section "AWS caller (identity only)"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)" \
  || staging_maintenance_fail preflight "aws sts get-caller-identity failed"
REGION="$(aws configure get region 2>/dev/null || true)"
if [[ -z "$REGION" ]]; then
  REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-}}"
fi
[[ -n "$REGION" ]] || staging_maintenance_fail preflight "configured AWS region is unavailable"
log "caller_account: ${ACCOUNT}"
log "configured_region: ${REGION}"
[[ "$ACCOUNT" == "$STAGING_MAINTENANCE_ACCOUNT_ID" ]] || staging_maintenance_fail preflight \
  "account ${ACCOUNT} is not ${STAGING_MAINTENANCE_ACCOUNT_ID}"
[[ "$REGION" == "$STAGING_MAINTENANCE_REGION" ]] || staging_maintenance_fail preflight \
  "region ${REGION} is not ${STAGING_MAINTENANCE_REGION}"

section "EC2 (identity / health — no secrets)"
INSTANCE_ID="$STAGING_MAINTENANCE_INSTANCE_ID"
log "expected_instance_id: ${INSTANCE_ID}"
aws ec2 describe-instances \
  --region "$STAGING_MAINTENANCE_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].{InstanceId:InstanceId,State:State.Name,Az:Placement.AvailabilityZone,PrivateIp:PrivateIpAddress,PublicIp:PublicIpAddress,LaunchTime:LaunchTime}' \
  --output json >"${OUT_DIR}/ec2-describe.json" \
  || staging_maintenance_fail preflight "ec2 describe-instances failed"
aws ec2 describe-instance-status \
  --region "$STAGING_MAINTENANCE_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --include-all-instances \
  --query 'InstanceStatuses[0].{InstanceState:InstanceState.Name,SystemStatus:SystemStatus.Status,InstanceStatus:InstanceStatus.Status}' \
  --output json >"${OUT_DIR}/ec2-status.json" \
  || staging_maintenance_fail preflight "ec2 describe-instance-status failed"
python3 - <<PY
import json
from pathlib import Path
desc = json.loads(Path("${OUT_DIR}/ec2-describe.json").read_text(encoding="utf-8"))
status = json.loads(Path("${OUT_DIR}/ec2-status.json").read_text(encoding="utf-8"))
assert desc.get("InstanceId") == "${INSTANCE_ID}", desc
assert desc.get("State") == "running", desc
assert status.get("SystemStatus") == "ok", status
assert status.get("InstanceStatus") == "ok", status
# PublicIp may be absent/null — that is explicitly valid.
print("OK ec2 identity/health")
PY
log "ec2_describe: ${OUT_DIR}/ec2-describe.json"
log "ec2_status: ${OUT_DIR}/ec2-status.json"

section "Host evidence (operator Session Manager — no SendCommand)"
if [[ -n "${STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE:-}" ]]; then
  staging_maintenance_fail host_evidence_nonce \
    "STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE is not permitted; capture generates its own nonce"
fi
# Capture-owned nonce for the collect snippet. Controlled apply generates a
# separate authoritative nonce for the apply run; do not treat this capture
# nonce as apply authority across runs.
HOST_SNIPPET="${OUT_DIR}/host-evidence-collect.sh"
NONCE="$(staging_maintenance_generate_run_nonce "$OUT_DIR")"
staging_maintenance_write_host_evidence_collect_snippet \
  "$HOST_SNIPPET" "pre-apply" "$NONCE"
log "host_evidence_collect: ${HOST_SNIPPET}"
log "host_evidence_nonce: ${NONCE}"
log "host_evidence_schema: schema_version=1 phase=pre-apply bound to instance/account/region/nonce"
log "ssm_send_command: forbidden_in_this_capture_script"
log "note: controlled apply generates its own run nonce; use that apply run's collect snippets for apply evidence"

if [[ -n "${STAGING_MAINTENANCE_HOST_EVIDENCE_PRE:-}" ]]; then
  staging_maintenance_validate_host_evidence \
    "$STAGING_MAINTENANCE_HOST_EVIDENCE_PRE" "pre-apply" "$NONCE"
  cp "$STAGING_MAINTENANCE_HOST_EVIDENCE_PRE" "${OUT_DIR}/host-evidence-pre.json"
  chmod 600 "${OUT_DIR}/host-evidence-pre.json"
  log "host_evidence_pre: ${OUT_DIR}/host-evidence-pre.json"
else
  log "host_evidence_pre: NOT_SUPPLIED (required before controlled apply)"
fi

section "ALB / probes"
cd "${ROOT}/${STAGING_MAINTENANCE_STAGING_TF_REL}"
# Init is mandatory so outputs/backend identity are authoritative.
terraform init -input=false \
  -backend-config="bucket=${STAGING_MAINTENANCE_BACKEND_BUCKET}" \
  -backend-config="key=${STAGING_MAINTENANCE_STATE_KEY}" \
  -backend-config="region=${STAGING_MAINTENANCE_REGION}" \
  || staging_maintenance_fail preflight "terraform init failed"
staging_maintenance_verify_backend_workspace
TG_ARN="$(terraform output -raw alb_target_group_arn)" \
  || staging_maintenance_fail preflight "terraform output alb_target_group_arn failed"
ALB_DNS="$(terraform output -raw alb_dns_name)" \
  || staging_maintenance_fail preflight "terraform output alb_dns_name failed"
staging_maintenance_assert_py validate-tg-arn "$TG_ARN" \
  || staging_maintenance_fail preflight "target group ARN rejected"
staging_maintenance_assert_py validate-alb-dns "$ALB_DNS" \
  || staging_maintenance_fail preflight "ALB DNS rejected"
log "alb_dns_name: ${ALB_DNS}"
log "target_group_arn: ${TG_ARN}"
aws elbv2 describe-target-health \
  --region "$STAGING_MAINTENANCE_REGION" \
  --target-group-arn "$TG_ARN" \
  --output json >"${OUT_DIR}/alb-target-health.json" \
  || staging_maintenance_fail preflight "describe-target-health failed"
aws elbv2 describe-target-groups \
  --region "$STAGING_MAINTENANCE_REGION" \
  --target-group-arns "$TG_ARN" \
  --query 'TargetGroups[0].{TargetGroupArn:TargetGroupArn,TargetGroupName:TargetGroupName,Port:Port,Protocol:Protocol,VpcId:VpcId}' \
  --output json >"${OUT_DIR}/alb-target-group.json" \
  || staging_maintenance_fail preflight "describe-target-groups failed"
python3 - <<PY
import json
from pathlib import Path
health = json.loads(Path("${OUT_DIR}/alb-target-health.json").read_text(encoding="utf-8"))
want = "${INSTANCE_ID}"
matched = None
for th in health.get("TargetHealthDescriptions") or []:
    if (th.get("Target") or {}).get("Id") == want:
        matched = th
        break
if matched is None:
    raise SystemExit(f"instance {want} not registered in target group")
state = ((matched.get("TargetHealth") or {}).get("State")) or "unknown"
if state != "healthy":
    raise SystemExit(f"ALB target state {state} != healthy")
print("OK alb target healthy")
PY
for path in /live /ready; do
  code="$(curl -sS -o "${OUT_DIR}/probe${path//\//-}.body" -w '%{http_code}' \
    --max-time 10 "http://${ALB_DNS}${path}")" \
    || staging_maintenance_fail application_health "curl ${path} failed"
  [[ "$code" == "200" ]] || staging_maintenance_fail application_health \
    "probe ${path} returned HTTP ${code}"
  log "probe_${path}: http_status=${code}"
done

section "RDS (identity/status only — no credentials)"
aws rds describe-db-instances \
  --region "$STAGING_MAINTENANCE_REGION" \
  --query 'DBInstances[?contains(DBInstanceIdentifier, `staging`)].{Id:DBInstanceIdentifier,Status:DBInstanceStatus,Engine:Engine,MultiAZ:MultiAZ,Class:DBInstanceClass}' \
  --output json >"${OUT_DIR}/rds-status.json" \
  || staging_maintenance_fail preflight "rds describe-db-instances failed"
log "rds_status: ${OUT_DIR}/rds-status.json"

section "Terraform backend / workspace / plan summary"
log "backend_bucket: ${STAGING_MAINTENANCE_BACKEND_BUCKET}"
log "state_key: ${STAGING_MAINTENANCE_STATE_KEY}"
log "workspace: $(terraform workspace show)"
PLAN_OUT="${OUT_DIR}/staging-maintenance.tfplan"
PLAN_TXT="${OUT_DIR}/staging-maintenance.plan.txt"
PLAN_JSON="${OUT_DIR}/staging-maintenance.plan.json"
umask 077
terraform plan -input=false -lock=false -out "$PLAN_OUT" >"$PLAN_TXT" 2>&1 \
  || staging_maintenance_fail plan_validation "terraform plan failed"
terraform show -no-color "$PLAN_OUT" >>"$PLAN_TXT" \
  || staging_maintenance_fail plan_validation "terraform show text failed"
terraform show -json "$PLAN_OUT" >"$PLAN_JSON" \
  || staging_maintenance_fail plan_validation "terraform show -json failed"
chmod 600 "$PLAN_OUT" "$PLAN_JSON" "$PLAN_TXT"
staging_maintenance_require_artifact_mode_0600 "$PLAN_OUT"
staging_maintenance_require_artifact_mode_0600 "$PLAN_JSON"
staging_maintenance_require_artifact_mode_0600 "$PLAN_TXT"
staging_maintenance_validate_plan_json "$PLAN_JSON"
staging_maintenance_record_plan_identity "$PLAN_OUT" "$OUT_DIR"
PLAN_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8"))["sha256"])' \
  "$STAGING_MAINTENANCE_PLAN_IDENTITY_FILE")"
log "plan_text: ${PLAN_TXT}"
log "plan_json: ${PLAN_JSON}"
log "plan_sha256: ${PLAN_SHA}"
log "plan_identity: ${STAGING_MAINTENANCE_PLAN_IDENTITY_FILE}"
log "plan_counts: create=1 update=2 replace=0 destroy=0 read=1"

section "Secret hygiene"
log "credentials: not printed"
log "DATABASE_URL: not printed"
log "environment dumps: not printed"
log "tokens_private_keys_passwords: not printed"

_staging_maintenance_note "Capture complete: ${REPORT}"
_staging_maintenance_note "Retain host-evidence JSON from Session Manager before apply."
printf '%s\n' "$OUT_DIR"
