# Sprint 41 — Production Environment & Deploy Path

**Status:** `SPRINT 41 PARTIALLY COMPLETE — PRODUCTION LIVE; ROLLBACK VALIDATION, WWW CANONICALIZATION, CDN/WAF OWNER DECISION, STAGING PRESERVATION, AND LIVE IAM SIMULATION REMAIN OPEN`

Sprint 41 is **not** COMPLETE / CLOSED. Live production after Early Access is not automatic closure.

**Current-main reconciliation (2026-09-18):** [`../evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md`](../evidence/SPRINT_41_CURRENT_MAIN_RECONCILIATION_2026-09-18.md) against `origin/main` `4a4fe65fa7438c75208a0052f52b77f929ee3903`. Live production digest remains Deploy Production #6 / SHA `3c514943a8a0ec34d1df97d5a329d3acb4a86e07`. Rollback is **not** validated. `www` does **not** redirect to apex. CDN/WAF is a proposal only. No production mutation in that reconciliation.

**Primary owner / domain:** Ops (extends Sprint 25 infra ownership; additive)
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-2

## Objective

Provision isolated production AWS and validate production deploy/rollback workflows without claiming domain ownership changes.

## Included requirements

- Production VPC/networking/DB/secrets/IAM/OIDC/container pull/ALB
- Domain/DNS/TLS; CDN/WAF decision recorded
- Static asset delivery for consumer UI
- Production deployment workflow + approval gates + evidence artifact
- Production rollback workflow
- DB migration policy + rollback compatibility confirmation
- Environment isolation proof (staging cannot read prod secrets)
- Preserve staging deploy/rollback architecture
- Launch acceptance requires **real evidence** for: isolated production AWS; DB; secrets; IAM; deploy path; rollback path; DNS; TLS; public hostname; migration strategy; appropriate CORS/host/security configuration
- Infrastructure-as-code alone is not launch proof

## Explicit non-goals

- Multi-region
- Redefining /ready semantics
- Domain engine changes

## External dependencies

- EXT-10
- EXT-11
- EXT-12
- EXT-13
- EXT-14

## Implementation deliverables

- Production Terraform apply (when authorized in that sprint's execution)
- deploy-production workflow
- Prod rollback workflow

## Documentation deliverables

- PRODUCTION.md updates
- Prod runbooks RB-prod-deploy/rollback
- Isolation evidence

## Required tests

- Workflow dry tests
- Isolation IAM tests where feasible

## Required staging evidence

- Staging remains green on same digest lineage

## Required production evidence

- Production-equivalent dry-run /ready
- Rollback path validated on prod or approved dry-run window

## Acceptance criteria

- Prod dry-run /ready READY
- Digest promotion from staging evidenced
- Rollback workflow validated
- Isolation proof filed
- CDN/WAF decision recorded

### Additive PiqSavi production-host criteria (not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- Canonical public hostname = `piqsavi.com`
- `www` redirects to canonical apex
- Production API hostname decision/config matches approved host map
- DNS verified
- TLS verified
- HTTP→HTTPS verified
- CORS uses approved PiqSavi origins
- `TRUSTED_HOSTS` uses approved public hostnames
- CSP supports approved frontend/API topology
- Reset/verification links resolve to PiqSavi
- Internal Terraform/AWS/SSM/resource naming remains DealBrain
- No infrastructure rename is required for public-brand launch

Do not perform DNS/TLS/AWS changes from documentation-only brand-lock tasks.

## Predecessor sprints

26, 40 recommended

## Parallelizable work

42 tooling prep

## Go / no-go gate

Go if prod dry-run + rollback evidenced.

**2026-09-18 current reading:** production `/ready` is live READY (stronger than a dry-run). Rollback workflow exists but is **not** evidenced against a real prior `production_ok` release. Accidental Rollback Production #1 (missing release object) is **not** validation. Gate remains **no-go for Sprint 41 close**.

## Rollback or contingency

Historical lock sentence: “Do not attach public DNS until 45.”

**2026-09-18 current reading:** Early Access already attached public DNS for `piqsavi.com` / `www.piqsavi.com` to the production ALB. That historical contingency is superseded as operational fact. It is **not** permission to close Sprint 41, Sprint 45, or shopping beta. Application rollback remains the production rollback workflow; DNS revert remains owner-controlled. Do not dispatch rollback from documentation tasks.

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
