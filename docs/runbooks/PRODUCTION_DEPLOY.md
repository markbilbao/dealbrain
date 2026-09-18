# Production deploy runbook (RB-prod-deploy)

**Audience:** operators dispatching an immutable production release after GitHub Environment `production` and production AWS exist.

**Scope:** GitHub Actions **Deploy Production** only.

**This document does not authorize a deploy.** Owner dispatch only. Do not run this workflow from documentation-only or reconciliation tasks.

Related:

- Workflow: [`.github/workflows/deploy-production.yml`](../../.github/workflows/deploy-production.yml)
- Rollback: [`PRODUCTION_ROLLBACK.md`](PRODUCTION_ROLLBACK.md)
- Environment UI: [`GITHUB_PRODUCTION_ENVIRONMENT.md`](GITHUB_PRODUCTION_ENVIRONMENT.md)
- Current Sprint 41 status: [`../roadmap/evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md`](../roadmap/evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md)

## What the workflow does

1. Must run from `refs/heads/main` on the canonical repository (not a fork).
2. Uses GitHub Environment `production` (OIDC; no GitHub application secrets).
3. Ingests a successful **Build Image** run’s checksummed release manifest.
4. Pulls the immutable GHCR digest (never `latest` / mutable tags).
5. Assumes `dealbrain-production-gha-deploy`.
6. Uploads a signed release bundle to `dealbrain-production-release-artifacts-<account>`.
7. Sends SSM document `DealBrain-ProductionDeploy` to the single production Compose host.
8. Host migrates (`alembic upgrade head`) **before** API replacement. Migration failure leaves the prior API in place.
9. Host writes authoritative `production-deploy-evidence.json` to S3. GitHub must not fabricate `production_ok`.

## Preconditions

- Successful CI + Build Image on the intended `main` SHA
- GitHub Environment `production` variables present (`AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`, `PRODUCTION_TARGET_GROUP_ARN`)
- Production secrets populated in `dealbrain/production/*` (values never in GitHub)
- No overlapping production-release-mutation run (shared concurrency with rollback)

## Evidence

Success requires host evidence `final_status=production_ok` at:

`s3://dealbrain-production-release-artifacts-<account>/evidence/<release_id>/<run_id>/production-deploy-evidence.json`

Last packaged success at reconciliation time: Deploy Production #6, SHA `3c514943a8a0ec34d1df97d5a329d3acb4a86e07`, evidence [`../roadmap/evidence/PRODUCTION_DEPLOY_6_EVIDENCE_2026-09-15.json`](../roadmap/evidence/PRODUCTION_DEPLOY_6_EVIDENCE_2026-09-15.json).

## Explicit non-actions

The workflow must not: rebuild images, `terraform apply`, change DNS, mutate RDS, read secret values in GitHub logs, or target staging.
