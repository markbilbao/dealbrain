# Production rollback runbook (RB-prod-rollback)

**Audience:** operators rolling production back to a previously successful immutable release.

**Scope:** GitHub Actions **Rollback Production** only.

**This document does not authorize a rollback.** Owner dispatch only. Reconciliation and documentation tasks must **not** trigger this workflow.

Related:

- Workflow: [`.github/workflows/rollback-production.yml`](../../.github/workflows/rollback-production.yml)
- Deploy: [`PRODUCTION_DEPLOY.md`](PRODUCTION_DEPLOY.md)
- Current Sprint 41 status: [`../roadmap/evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md`](../roadmap/evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md)

## What “validated” means

A rollback workflow **existing** is not Sprint 41 rollback acceptance.

Rollback acceptance requires a `rollback_ok` evidence object after restoring a **real prior successful** `production_ok` release (retained S3 bundle + matching digest).

## Historical non-validation

Rollback Production #1 (2026-09-14, run `34879465584`) failed because the requested release object did not exist:

`s3://dealbrain-production-release-artifacts-941035169846/releases/rel-20260914T175147Z-dd1f9b6e816b/bundle.tar.gz`

That fail-closed outcome must **not** be counted as successful rollback validation.

As of 2026-09-18, no later Rollback Production run exists. Sprint 41 rollback acceptance remains **open**.

## What the workflow does

1. Must run from `refs/heads/main`.
2. Uses GitHub Environment `production`.
3. Shares concurrency group `production-release-mutation` with Deploy Production.
4. Target is a previously built immutable digest whose release bundle still exists.
5. Must not modify/delete RDS. Host uses `alembic current` only (no downgrade).
6. Aborts if live schema is incompatible with the target recorded revision.
7. Host writes authoritative production rollback evidence. GitHub must not fabricate `rollback_ok`.

## Theoretical current targets (not executed here)

After Deploy Production #5 and #6 succeeded, a later owner-controlled rollback could target the prior `production_ok` release (Deploy #5, SHA `10c0579b9b8a8653399193261d3ef9f188fed3c2`) while #6 is current. Eligibility still requires the retained S3 bundle and host tooling checks at dispatch time.

## Explicit non-actions

Do not: apply Terraform, change DNS, downgrade or restore RDS as part of application rollback, delete Early Access rows, target staging, or treat a missing-object failure as a passed rehearsal.
