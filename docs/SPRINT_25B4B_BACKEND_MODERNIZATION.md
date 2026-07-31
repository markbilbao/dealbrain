# Sprint 25b.4b — Terraform Backend Modernization (acceptance fixes)

**Status:** Repository acceptance fixes complete; **no** `terraform plan` / `apply` / AWS create  
**Scope:** Align CI, docs, and operator workflow with the modernized account + staging backends

## Summary

| Area | Change |
|------|--------|
| Terraform version | Roots `account/` and `environments/staging` require `>= 1.11.0` |
| State locking | S3 native lockfiles (`use_lockfile = true`); DynamoDB lock tables obsolete |
| Backend shape | Partial S3 backend; `bucket` / `key` / `region` via `-backend-config` at init |
| CI | `.github/workflows/ci.yml` pins Terraform `1.15.8` (was `1.9.8`) |
| Production | Backend migration **intentionally deferred** until production rollout |

## Operator notes

- Prefer [`infra/terraform/README.md`](../infra/terraform/README.md) as the current source of truth.
- `terraform init -backend=false` is for validation and CI only.
- Do not create `dealbrain-terraform-locks` (or any DynamoDB lock table) for new work.

## Explicit non-goals

- No Terraform plan/apply/import/destroy
- No production backend enablement
- No AWS resource creation
