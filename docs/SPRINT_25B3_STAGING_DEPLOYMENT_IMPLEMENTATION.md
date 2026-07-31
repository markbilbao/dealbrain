# Sprint 25b.3 — Staging Deployment Pipeline Implementation

**Status:** Repository implementation complete; live deployment **not** performed  
**Branch:** `sprint-25b3`  
**Architecture:** [SPRINT_25B3_STAGING_DEPLOYMENT_PIPELINE.md](architecture/SPRINT_25B3_STAGING_DEPLOYMENT_PIPELINE.md)

## What this sprint owns (repository)

| Deliverable | Path |
|-------------|------|
| Staging deploy workflow | `.github/workflows/deploy-staging.yml` |
| Manifest ingestion | `scripts/deploy/validate_staging_release.py`, `fetch_release_artifact.py` |
| Release bundle | `scripts/deploy/build_staging_bundle.py`, `verify_staging_bundle.py` |
| Host orchestrator + helpers | `scripts/deploy/host/*` |
| Staging evidence schema | `schemas/staging-deploy-evidence.schema.json`, `scripts/deploy/evidence.py` |
| Host bootstrap user_data | `infra/ec2/user_data/staging.sh` |
| Release-artifacts S3 module | `infra/terraform/modules/release_artifacts/` |
| Custom SSM document | `infra/terraform/modules/ssm_deploy_document/` (`DealBrain-StagingDeploy`) |
| Staging TF wiring | `infra/terraform/environments/staging/` |
| Tests | `tests/unit/test_sprint25b3_staging_deploy.py` |

## Explicit non-goals (unchanged)

- No production deploy / approval / snapshot / rollback workflows
- No Terraform apply, GitHub Environment UI configuration, live SSM, or live deploy
- No static AWS keys, public SSH, secrets in GitHub, or secrets in Terraform state
- No mutable-tag deployment authority; no image rebuild during deploy
- No Alembic during image build or API startup; no direct DB access from GitHub Actions
- Build `release-manifest.json` remains immutable (`final_status=built`, `environment=none`)

## Repository vs live Definition of Done

### Repository DoD (this sprint — complete when tests/docs green)

- Staging workflow exists; production/rollback workflows absent
- Digest-only deploy; staging OIDC role only; custom SSM document; RunShellScript removed from staging allowlist
- Host bootstrap + S3 bundle + host-side secrets + GHCR stdin login modeled
- Migrate-then-API sequence; `/live` + `/ready` + ALB gates; flock + concurrency
- Append-only checksummed staging evidence; `DEPLOY_VERSION`; current+previous retention

### Live prerequisites (operator — **not** done by this implementation)

1. Remote Terraform state bootstrapped (S3 + native lockfiles); account/staging
   initialized with `-backend-config` (see [`infra/terraform/README.md`](../infra/terraform/README.md))
2. `account/` + `environments/staging` Terraform **applied**
3. GitHub Environment exactly named `staging`, deployment branches **`main` only**
4. Environment vars: `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`, `STAGING_TARGET_GROUP_ARN`
5. Staging secrets populated (app + `ghcr_pull` classic PAT `read:packages`)
6. Instance SSM Agent Online; `bootstrap.ok` present after user_data
7. First successful digest deploy with evidence artifact + S3 object

## Operator first-deploy checklist

1. Confirm Build Image run succeeded on `main` and note its run ID  
2. Confirm GitHub Environment `staging` gates and OIDC vars  
3. Confirm staging stack applied (instance, TG, RDS, bucket, SSM doc, roles)  
4. Confirm secrets populated; never paste them into GitHub  
5. Dispatch **Deploy Staging** on `main` with `build_workflow_run_id`  
6. Wait for SSM Success; download `staging-evidence-*` artifact  
7. Verify `/live`, `/ready`, ALB healthy, `DEPLOY_VERSION` on host  

## Failure / recovery (staging)

- Migration failure or 20-minute migration timeout → API left on prior digest; `current` remains prior release; fix forward (no auto-downgrade)
- Missing host evidence → workflow fails closed (never fabricates `staging_ok`)
- Failed API recreate → manual restore from retained previous release directory
- Stale flock → Session Manager break-glass runbook (SSO); not automated in v1
- Automated rollback workflow → deferred to Sprint 25b.5

## Authoritative evidence transport

1. Host writes checksummed `staging-deploy-evidence.json` after gates (or truthful failure)
2. Host uploads to `s3://…/evidence/<release_id>/<run_id>/staging-deploy-evidence.json`
3. Workflow downloads that exact object, validates schema/checksum/bindings, uploads GitHub artifact
4. Workflow never creates synthetic success evidence

## Validation targets

```bash
make validate-staging-deploy
uv run pytest tests/unit/test_sprint25b3_staging_deploy.py \
  tests/unit/test_sprint25a_infrastructure.py \
  tests/unit/test_sprint25b1_image_publication.py \
  tests/unit/test_sprint25b2_oidc_iam.py -q
```

## Follow-on: Sprint 25b.4a

Pre-live repository refinements (head-bucket removal, strict ALB, evidence import fail-closed) are documented in [SPRINT_25B4A_PRE_LIVE_REFINEMENTS.md](SPRINT_25B4A_PRE_LIVE_REFINEMENTS.md). No live AWS action in 25b.4a; 25b.4b remains separately gated.
