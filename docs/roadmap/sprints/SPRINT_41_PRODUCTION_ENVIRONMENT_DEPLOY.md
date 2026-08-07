# Sprint 41 — Production Environment & Deploy Path

**Status:** Planned
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

Go if prod dry-run + rollback evidenced

## Rollback or contingency

Do not attach public DNS until 45

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
