# Sprint 25b.4a — Pre-Live Repository Refinements

**Status:** Repository implementation complete; **no live AWS action**  
**Branch:** `sprint-25b4`  
**Scope:** Staging deploy hardening only — 25b.4b (apply / GitHub Environment / secrets / first deploy) remains separately gated

## Purpose

Resolve Sprint 25b.3 re-audit findings before any Terraform apply, Environment configuration, or live staging deploy.

## Changes

| Area | Change |
|------|--------|
| S3 preflight | Removed `aws s3api head-bucket` from `deploy-staging.yml`. Exact object Put/Get/Head under `releases/*` and `evidence/*` are the readiness and authorization checks. ListBucket was **not** broadened. |
| ALB health | Single structured acceptance path via `scripts/deploy/alb_target_health.py`. Expected staging instance must be the sole target with state exactly `healthy`. No substring `grep healthy` fallback. |
| Evidence writer | Removed inline fallback in `write-staging-evidence.py`. Canonical `evidence.py` import failure exits non-zero and writes nothing. |
| Host IAM docs | `modules/iam/variables.tf` describes releases read + evidence binder read + evidence write. |
| GHA SSM observe | Removed unused `ssm:ListCommands` / `ssm:ListCommandInvocations`; retained `SendCommand` + `GetCommandInvocation`. |
| Archive tests | Device (chr/blk) and FIFO rejection covered through the real verifier. |

## Explicit non-goals (unchanged)

- No Terraform plan/apply/import/destroy
- No GitHub Environment configuration or secret population
- No SSM SendCommand / live deploy
- No production workflow, snapshot gate, or rollback automation

## Validation

```bash
make validate-staging-deploy
uv run pytest \
  tests/unit/test_sprint25b4a_pre_live_refinements.py \
  tests/unit/test_sprint25b3_staging_deploy.py \
  tests/unit/test_sprint25a_infrastructure.py \
  tests/unit/test_sprint25b1_image_publication.py \
  tests/unit/test_sprint25b2_oidc_iam.py -q
```

## Next gate

**25b.4b** — remote state, account/staging apply, GitHub Environment vars, Secrets Manager values, then first digest deploy (operator-owned).
