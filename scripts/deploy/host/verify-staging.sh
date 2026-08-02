#!/bin/bash
# Staging post-deploy verification gates (Sprint 25b.3 / 25b.4a / 25b.5h).
# Does not alter application /live or /ready semantics.
# ALB acceptance is strict: sole expected instance target must be exactly healthy.
#
# Health-gate timing contract (bounded; no infinite wait):
#   LOCAL_INTERVAL_SEC=5
#   LOCAL_TIMEOUT_SEC=180          # per local probe (/live, then /ready)
#   ALB_INTERVAL_SEC=10
#   ALB_STABILIZATION_TIMEOUT_SEC=600  # ALB window after local readiness
#   Maximum local wait:  2 * LOCAL_TIMEOUT_SEC = 360s
#   Maximum ALB wait:    ALB_STABILIZATION_TIMEOUT_SEC = 600s
#   Maximum health-gate total: 960s
# ALB evaluator exit-code contract (alb_target_health.py):
#   0 — healthy (success)
#   2 — explicitly allowlisted transient state (sleep + retry in-window)
#   1 — permanent / malformed / unknown (fail closed immediately)
#   any other code — unexpected evaluator failure (fail closed immediately)
# AWS CLI / jq parse failures are also permanent (never converted to empty targets).
set -euo pipefail
set +x

ENV_FILE=""
IMAGE_DIGEST=""
IMAGE_REPOSITORY=""
COMPOSE_PROJECT="dealbrain-staging"
TG_JSON=""
REGION=""
INSTANCE_ID=""
OUT_JSON="/tmp/dealbrain-verify.json"

# Named retry/timeout contract (Sprint 25b.5h).
LOCAL_INTERVAL_SEC=5
LOCAL_TIMEOUT_SEC=180
ALB_INTERVAL_SEC=10
ALB_STABILIZATION_TIMEOUT_SEC=600
# Backward-compatible aliases referenced by older docs/tests.
LOCAL_INTERVAL="$LOCAL_INTERVAL_SEC"
LOCAL_TIMEOUT="$LOCAL_TIMEOUT_SEC"
ALB_TIMEOUT="$ALB_STABILIZATION_TIMEOUT_SEC"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --image-digest) IMAGE_DIGEST="$2"; shift 2 ;;
    --image-repository) IMAGE_REPOSITORY="$2"; shift 2 ;;
    --compose-project) COMPOSE_PROJECT="$2"; shift 2 ;;
    --target-group-json) TG_JSON="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --instance-id) INSTANCE_ID="$2"; shift 2 ;;
    --out-json) OUT_JSON="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$ENV_FILE" && -f "$ENV_FILE" ]] || { echo "ERROR: --env-file required" >&2; exit 1; }
[[ "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "ERROR: bad digest" >&2; exit 1; }
[[ -n "$IMAGE_REPOSITORY" ]] || { echo "ERROR: --image-repository required" >&2; exit 1; }
[[ -n "$TG_JSON" && -f "$TG_JSON" ]] || { echo "ERROR: --target-group-json required" >&2; exit 1; }
[[ -n "$REGION" ]] || { echo "ERROR: --region required" >&2; exit 1; }
[[ -n "$INSTANCE_ID" ]] || { echo "ERROR: --instance-id required" >&2; exit 1; }
[[ "$INSTANCE_ID" =~ ^i-[0-9a-f]+$ ]] || { echo "ERROR: bad instance id" >&2; exit 1; }

TG_ARN="$(jq -r '.target_group_arn' "$TG_JSON")"
[[ -n "$TG_ARN" && "$TG_ARN" != "null" ]] || { echo "ERROR: target_group_arn missing" >&2; exit 1; }
[[ "$TG_ARN" =~ ^arn:aws:elasticloadbalancing:[a-z0-9-]+:[0-9]{12}:targetgroup/.+ ]] \
  || { echo "ERROR: target_group_arn is not a valid ELBv2 target group ARN" >&2; exit 1; }
case "$TG_ARN" in
  *production*) echo "ERROR: production target group identifier" >&2; exit 1 ;;
esac
case "$TG_ARN" in
  *staging*|*dealbrain-staging*) ;;
  *) echo "ERROR: target group ARN must identify staging" >&2; exit 1 ;;
esac

# Resolve strict ALB evaluator (bundle bin/ or repo scripts/deploy/).
ALB_EVAL="${SCRIPT_DIR}/alb_target_health.py"
if [[ ! -f "$ALB_EVAL" ]]; then
  ALB_EVAL="$(cd "${SCRIPT_DIR}/.." && pwd)/alb_target_health.py"
fi
[[ -f "$ALB_EVAL" ]] || { echo "ERROR: alb_target_health.py missing" >&2; exit 1; }

probe_live() {
  local body="$1"
  # Sprint 22 LiveResponse: require live == true (not HTTP 200 alone).
  jq -e '
    (type == "object")
    and (.live == true)
    and ((.status | type) == "string")
    and ((.status | length) > 0)
    and ((.service | type) == "string")
    and ((.service | length) > 0)
  ' "$body" >/dev/null 2>&1
}

probe_ready() {
  local body="$1"
  jq -e '
    (type == "object")
    and (.ready == true)
    and ((.status | type) == "string")
    and ((.status | length) > 0)
  ' "$body" >/dev/null 2>&1
}

wait_http() {
  local path="$1"
  local kind="$2"
  local elapsed=0
  while [[ $elapsed -lt $LOCAL_TIMEOUT_SEC ]]; do
    if curl -fsS "http://127.0.0.1:8000${path}" -o /tmp/dealbrain-probe.json; then
      if [[ "$kind" == "live" ]] && probe_live /tmp/dealbrain-probe.json; then
        return 0
      fi
      if [[ "$kind" == "ready" ]] && probe_ready /tmp/dealbrain-probe.json; then
        return 0
      fi
    fi
    sleep "$LOCAL_INTERVAL_SEC"
    elapsed=$((elapsed + LOCAL_INTERVAL_SEC))
  done
  return 1
}

LOCAL_LIVE=false
LOCAL_READY=false
ALB_OK=false
SMOKE_OK=false

# Local container readiness must pass before ALB acceptance.
if wait_http "/live" "live"; then
  LOCAL_LIVE=true
fi
if wait_http "/ready" "ready"; then
  LOCAL_READY=true
fi

# Compose service running + APP_ENV + digest
CID="$(docker ps --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" \
  --filter "label=com.docker.compose.service=api" \
  --format '{{.ID}}' | head -1)"
[[ -n "$CID" ]] || { echo "ERROR: api container not running" >&2; exit 1; }

APP_ENV_VAL="$(docker inspect "$CID" --format '{{range .Config.Env}}{{println .}}{{end}}' | awk -F= '$1=="APP_ENV"{print $2}')"
[[ "$APP_ENV_VAL" == "staging" ]] || { echo "ERROR: APP_ENV is not staging" >&2; exit 1; }

RUNNING_DIGEST="$(docker inspect "$CID" --format '{{index .Image}}' | xargs -I{} docker image inspect {} --format '{{index .RepoDigests 0}}')"
echo "$RUNNING_DIGEST" | grep -q "$IMAGE_DIGEST" || {
  IMG="$(docker inspect "$CID" --format '{{.Config.Image}}')"
  echo "$IMG" | grep -q "$IMAGE_DIGEST" || {
    echo "ERROR: running container digest mismatch" >&2
    exit 1
  }
}

# Require local readiness before spending the ALB stabilization window.
if [[ "$LOCAL_LIVE" != "true" || "$LOCAL_READY" != "true" ]]; then
  echo "ERROR: local readiness failed before ALB stabilization window" >&2
  jq -n \
    --argjson live "$LOCAL_LIVE" \
    --argjson ready "$LOCAL_READY" \
    --argjson alb false \
    --argjson smoke false \
    '{localhost_live:$live, localhost_ready:$ready, alb_target_healthy:$alb, smoke_ok:$smoke}' \
    >"$OUT_JSON"
  exit 1
fi

# Strict ALB target health — one structured acceptance path only.
# No substring "healthy" fallback. Bounded poll; timeout fails closed.
#
# Retry contract (only evaluator exit 2 is retried):
#   ALB_RC == 0 → success
#   ALB_RC == 2 → sleep ALB_INTERVAL_SEC and retry until ALB_STABILIZATION_TIMEOUT_SEC
#   ALB_RC == 1 → immediate permanent failure
#   any other ALB_RC / AWS CLI failure / jq parse failure → immediate permanent failure
_write_alb_fail_json() {
  jq -n \
    --argjson live "$LOCAL_LIVE" \
    --argjson ready "$LOCAL_READY" \
    --argjson alb false \
    --argjson smoke false \
    '{localhost_live:$live, localhost_ready:$ready, alb_target_healthy:$alb, smoke_ok:$smoke}' \
    >"$OUT_JSON"
}

elapsed=0
while [[ $elapsed -lt $ALB_STABILIZATION_TIMEOUT_SEC ]]; do
  set +e
  HEALTH_JSON="$(
    aws elbv2 describe-target-health \
      --region "$REGION" \
      --target-group-arn "$TG_ARN" \
      --output json 2>/tmp/dealbrain-alb-aws.err
  )"
  AWS_RC=$?
  set -e
  if [[ $AWS_RC -ne 0 ]]; then
    echo "ERROR: aws elbv2 describe-target-health failed (exit ${AWS_RC}; fail closed)" >&2
    _write_alb_fail_json
    exit 1
  fi
  if ! printf '%s' "$HEALTH_JSON" | jq -e 'type == "object"' >/dev/null 2>&1; then
    echo "ERROR: describe-target-health returned malformed/non-object JSON (fail closed)" >&2
    _write_alb_fail_json
    exit 1
  fi

  set +e
  printf '%s' "$HEALTH_JSON" | python3 "$ALB_EVAL" \
    --target-group-arn "$TG_ARN" \
    --instance-id "$INSTANCE_ID" \
    --input -
  ALB_RC=$?
  set -e
  if [[ $ALB_RC -eq 0 ]]; then
    ALB_OK=true
    break
  fi
  if [[ $ALB_RC -eq 2 ]]; then
    # Explicitly allowlisted transient stabilization state — retry in-window.
    sleep "$ALB_INTERVAL_SEC"
    elapsed=$((elapsed + ALB_INTERVAL_SEC))
    continue
  fi
  # Exit 1 (permanent) or any unexpected evaluator code — fail closed immediately.
  echo "ERROR: ALB target health rejection (evaluator exit ${ALB_RC}; fail closed)" >&2
  _write_alb_fail_json
  exit 1
done

# Stable read-only smoke: /live again with content verification
if curl -fsS "http://127.0.0.1:8000/live" -o /tmp/dealbrain-smoke.json \
  && probe_live /tmp/dealbrain-smoke.json; then
  SMOKE_OK=true
fi

jq -n \
  --argjson live "$LOCAL_LIVE" \
  --argjson ready "$LOCAL_READY" \
  --argjson alb "$ALB_OK" \
  --argjson smoke "$SMOKE_OK" \
  '{localhost_live:$live, localhost_ready:$ready, alb_target_healthy:$alb, smoke_ok:$smoke}' \
  >"$OUT_JSON"

[[ "$LOCAL_LIVE" == "true" ]] || exit 1
[[ "$LOCAL_READY" == "true" ]] || exit 1
[[ "$ALB_OK" == "true" ]] || {
  echo "ERROR: ALB target did not become healthy within ${ALB_STABILIZATION_TIMEOUT_SEC}s" >&2
  exit 1
}
[[ "$SMOKE_OK" == "true" ]] || exit 1

echo "ok: staging verification gates passed"
