# DealBrain Architecture Lock

**Status:** Locked as of Sprint 23; Sprint 24 API-contract ownership added (additive); Sprint 25 production infrastructure ownership added (additive); Sprint 25b.2 OIDC/deploy IAM ownership added (additive); Sprint 25b.3 staging deployment pipeline ownership added (additive); Global Public Beta roadmap ownership added (additive, documentation)

**Launch roadmap endpoint (current):** Sprint 46 — see [`docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)

**Historical note:** A prior **hard endpoint at Sprint 40** is **superseded for launch sequencing** (identities 1–40 preserved). Sprint 30 “public launch” target is **reclassified** as a readiness audit (NOT READY).

**Runtime enforcement:** This document is a change-control policy. It is **not** enforced by a separate runtime policy engine unless a specific check is implemented and documented elsewhere.

---

## 1. Purpose

This lock freezes domain ownership and architectural invariants established by the Sprint 1–22 architecture audit. Future sprints may harden adapters, operations, and integrations, but must not silently redistribute ownership or change ranking/recommendation semantics.

Sprint 23 may **replace adapters**, not **domain owners**. Persistence changes must be **behavior-preserving**. Any future ownership change requires **explicit architecture review**. Launch sequencing through Global Public Beta is governed by the [Global Public Beta Master Roadmap](../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) (**endpoint Sprint 46**). The former Sprint 40 hard endpoint remains a historical identity marker only.

Sprint 24 owns **API contracts only** (OpenAPI, response shapes, pagination/filter/sort conventions, error documentation, compatibility gates). It does **not** take domain or persistence ownership from Sprints 1–23.

---

## 2. Locked ownership matrix

| Sprint | Canonical ownership |
|--------|---------------------|
| 1–3 | Product Identity, Product Registry, Product Matching |
| 4 | Marketplace Search, Marketplace Intelligence |
| 5 | DealScore |
| 6 | Recommendation decisions (Buy / Wait / Consider / Avoid) |
| 7 | Historical Price Data, Price Statistics, Price Trends |
| 8 | Marketplace Collection (historical collection) |
| 9 | Collection Operations, Pause / Resume, Manual Runs, Operational Health |
| 10 | Watchlists; Legacy Alerts during migration |
| 11 | Reviews |
| 12 | Review Summaries |
| 13 | Shopping Assistant ranking and presentation |
| 14 | Community |
| 15 | Knowledge Graph |
| 16 | Personal AI and personal presentation |
| 17 | Consumer Users, Authentication, Sessions, Account Profiles, Account Preferences |
| 18 | Current Marketplace Offers, Marketplace Synchronization, Sync Checkpoints, Marketplace Freshness |
| 19 | Alert Rules, Alert Evaluation, Alert Events, Notification Preferences, Notification Delivery Orchestration |
| 20 | Affiliate Partners, Affiliate Link Generation, Click and Conversion Attribution |
| 21 | Merchant Organizations, Merchant Accounts, Merchant Catalog, Merchant Offers, Merchant Campaigns, Merchant Moderation |
| 22 | Launch Infrastructure, Startup Validation, Health and Readiness, Logging, Rate Limiting, Launch Cache, Diagnostics |
| 23 | Production persistence adapters, migrations, transaction infrastructure, durable operational state, persistence validation, restart recovery, production configuration hardening, deeper readiness checks related to persistence |
| 24 | API contracts, endpoint consistency, DTO/OpenAPI standardization, pagination/filtering/sorting conventions, error-response documentation, API integration/contract tests, API documentation, OpenAPI drift detection, compatibility gate — **not** domain engines or persistence adapters |
| 25 | Production infrastructure and operations on the selected AWS single-region Compose+RDS stack: Terraform/Compose/Actions, secrets injection, promotion by digest, migrate jobs, observability, backup/DR/rollback, runbooks — **does not** own domain engines, API contracts, persistence adapters, or readiness semantics |
| 26–29, 31–46 | Global Public Beta delivery sprints (identity/email, privacy/legal, consumer UI, merchant unification, market certifications, MarketContext/FX, reliability, analytics, security hardening, production cutover evidence, capacity, launch control, stabilization) — **additive**; must not silently take DealScore/Recommendation/affiliate/merchant-neutrality ownership from Sprints 5/6/20/21 |
| 30 | **Historical:** Public Beta Readiness Audit (2026-08-06) — closed; NOT a completed public shopping launch |

Sprint 23 must **not** take ownership of Sprints 1–22 domain logic.

Sprint 24 must **not** take ownership of Sprints 1–23 domain logic or persistence.

Sprint 25 must **not** take ownership of Sprints 1–24 domain logic, API contracts, persistence adapters, or readiness probe semantics.

---

## 3. Protected architectural invariants

1. Sprint 5 remains the only DealScore owner.
2. Sprint 6 remains the only owner of organic recommendation decisions.
3. Affiliate metadata must be attached only after organic selection and ranking.
4. Affiliate commission, partner priority, or conversion value must never influence candidate inclusion, DealScore, Recommendation, organic ordering, or Shopping Assistant ordering.
5. Merchant data must not modify organic visibility, DealScore, Buy/Wait/Consider/Avoid, Marketplace Search ranking, or historical prices.
6. Sponsored merchant content must remain separate and clearly labeled.
7. Sprint 18 owns current synchronized offers.
8. Sprint 7 owns canonical historical prices.
9. Sprint 8 owns historical marketplace collection.
10. Sprint 19 is the canonical new alert-rule engine.
11. Sprint 10 legacy alert behavior must remain compatible until a later proven migration.
12. AI remains downstream from deterministic product identity, DealScore, and Recommendation.
13. Repositories persist domain state but must not contain domain decision logic.
14. Sprint 22 remains infrastructure only.
15. Persistence must not change domain output for identical inputs.

---

## 4. Allowed Sprint 23 changes

- Production persistence adapters implementing existing repository ports
- Deterministic Alembic migrations for operational tables
- Transaction / unit-of-work helpers for atomic repository operations
- Explicit environment-aware adapter selection via dependency injection
- Persistence-related readiness checks consumed by Sprint 22
- Production configuration hardening (fail-closed secrets/backends)
- Tests proving contract parity, restart recovery, concurrency, and neutrality
- Documentation of persistence, migrations, operations, and deferred work

---

## 5. Forbidden Sprint 23 changes

- Architecture redesign or domain ownership transfers
- Feature expansion, AI improvement, ranking improvement, marketplace feature expansion, or UI redesign
- Changing DealScore formulas, weights, or recommendation decisions
- Changing organic result ordering or Shopping Assistant ranking policy
- Letting affiliate or merchant data affect organic ranking
- Merging consumer and merchant identity systems
- Adding speculative abstractions without runtime use
- Deleting Sprint 10 compatibility paths without proven migration
- Silently changing API contracts
- Introducing a second ORM or migration system unless the existing stack is unusable (it is usable)

---

## 6. Repository rules

1. Services depend on **ports/interfaces**, not concrete ORM adapters.
2. Persistent adapters translate storage concerns only; they do not implement ranking, DealScore, or recommendation policy.
3. Production must use persistent adapters by default and must not silently fall back to in-memory storage.
4. In-memory adapters remain valid for tests and explicit development/demo configuration.
5. Uniqueness and ownership constraints should be enforced at the database where concurrent safety requires it.
6. Stable identifiers and existing API semantics must be preserved.

---

## 7. Ranking-neutrality rules

Persistence and operational data must not alter:

- Marketplace Search organic ordering (Sprint 4)
- DealScore computation (Sprint 5)
- Recommendation decisions (Sprint 6)
- Shopping Assistant ranking policy (Sprint 13)
- Personal AI ranking ownership (Sprint 16)

---

## 8. Affiliate-neutrality rules

- Affiliate attachment remains post-selection.
- Commission, partner priority, and conversion value are attribution/reporting concerns only.
- Affiliate tables and repositories must not be read by DealScore or Recommendation engines.

---

## 9. Merchant-neutrality rules

- Merchant catalog/offers/campaigns must not write into organic search, DealScore, Recommendation, or Sprint 7 historical prices.
- Sponsored rails remain separate and labeled.
- Cross-merchant access is denied; admin moderation remains explicit.

---

## 10. AI-boundary rules

- AI consumes deterministic identity, DealScore, and Recommendation outputs; it does not redefine them.
- Persistence of AI conversation/profile stores (if any) is out of Sprint 23 ownership unless already required by Sprints 17–21 operational durability (Sprint 23 focuses on 17–21 operational stores).

---

## 11. Compatibility and deprecation policy

- Existing APIs remain compatible unless a change is explicitly documented.
- Sprint 10 legacy alerts remain until a later sprint proves migration with callers and tests.
- Demo shortcuts may remain behind development/demo flags only.
- Deprecations require docs, dual-run or adapter selection, and tests before removal.

---

## 12. Change-control policy through Global Public Beta (Sprint 46)

1. Propose ownership or invariant changes in architecture review before coding.
2. Prefer adapter and operations work over domain rewrites.
3. Keep scope controlled so Global Public Beta can launch by **Sprint 45** and stabilize in **Sprint 46**, per the [master roadmap](../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md).
4. Do not absorb deferred roadmap items into persistence or unrelated sprints without explicit re-scoping and a single owning sprint in the master roadmap.
5. Document limitations rather than silently changing behavior.
6. **Supersession note:** The former “hard endpoint: Sprint 40” rule is superseded for launch sequencing. Sprint identities 1–40 remain historical and must not be renumbered.
7. Roadmap additions require: gap ID, single primary owning sprint, acceptance evidence, beta-blocker classification, and Architecture Lock review when invariants/ownership change.

**Remember:** Sprint 23 replaces adapters, not domain owners. Persistence must be behavior-preserving. Ownership changes require explicit architecture review. Launch roadmap endpoint: **Sprint 46** (see master roadmap).

---

## 13. Sprint 24 — API contract ownership (additive)

Sprint 24 is an **additive** stability sprint. It freezes and documents HTTP contracts without redistributing domain or persistence ownership.

### 13.1 What Sprint 24 owns

- Public API contracts and OpenAPI as the implementation contract
- Shared pagination / filtering / sorting conventions at the HTTP boundary
- Error-response documentation (Sprint 22 `ErrorBody` envelope preserved)
- Dual-run collection compatibility (`named key` + optional `items` / `pagination`)
- OpenAPI drift detection and the compatibility gate
- API integration / contract test coverage matrix

### 13.2 Compatibility guarantees

- Existing clients must keep working without mandatory changes
- No path removals; no `/api/v2`
- No global success envelope (`{data, meta}`)
- Bare-list endpoints remain bare lists
- Named collection keys remain primary
- Pagination / sort / dual-run fields are **optional and additive**
- Caller `sort` never influences DealScore, Recommendation, Marketplace Search organic order, or Shopping Assistant ranking

### 13.3 Unchanged ownership

- **Persistence (Sprint 23):** adapters, migrations, and durable stores are unchanged by Sprint 24
- **Business / domain ownership (Sprints 1–22):** DealScore, Recommendation, Shopping Assistant ranking, affiliate attachment order, merchant neutrality, and all other locked domain owners remain as in §§2–10
- Sprint 24 may wrap HTTP presentation only; it must not change domain outputs for identical inputs

---

## 14. Sprint 25 — Production infrastructure ownership (additive)

Sprint 25 is an **additive** operations sprint. It owns the AWS single-region runtime platform and operational practices without redistributing domain, API, or persistence ownership.

### 14.1 What Sprint 25 owns

- Terraform / Compose / GitHub Actions deployment topology for staging and production
- Secrets Manager injection, environment isolation, image digest promotion
- Dedicated migrate jobs (API does not migrate at startup)
- Observability, backup/DR/rollback evidence, and operational runbooks

### 14.1a Sprint 25b.1 (implemented slice)

Sprint 25b.1 owns **immutable GHCR image publication** and the **release manifest**
build evidence only (`build-image.yml`, `scripts/release/*`,
`schemas/release-manifest.schema.json`).

| Concern | Owner |
|---------|--------|
| Validation (lint, tests, contracts, docker build without push) | `ci.yml` |
| Releasable GHCR publication | `build-image.yml` only |
| Authoritative image identity | Digest `sha256:…` + immutable tag `sha-<full_git_sha>` |
| Mutable tags (`latest`, `ci-latest`, env aliases) | Informational only — **no** deployment authority |

Sprint 25b.1 does **not** own staging/production deploy, OIDC, SSM, migration
execution in AWS, or rollback workflows (25b.2–25b.5).

### 14.1b Sprint 25b.2 (implemented slice)

Sprint 25b.2 owns the **authorization foundation** for later SSM deploys:

| Concern | Owner |
|---------|--------|
| Account-level GitHub Actions OIDC provider | `infra/terraform/account/` + `modules/github_oidc/` (exactly once) |
| Staging / production deploy IAM roles + OIDC trust | `modules/github_deploy_role/` via environment roots |
| Staging immutable GitHub OIDC `sub` (owner_id/repo_id) | Sprint 25b.5f — staging root ID inputs; production legacy until migrated |
| Deploy-role orchestration permissions (SSM SendCommand prep + describe) | Sprint 25b.2 — **no** secret value reads, **no** `rds:CreateDBSnapshot` |
| EC2 host SSM managed-instance capability | `modules/iam` attaches `AmazonSSMManagedInstanceCore` |
| GHCR pull secret **containers** (`dealbrain/<env>/ghcr_pull`) | `modules/secrets` — values out-of-band only |
| GitHub Environment hard gates (`main`-only; prod reviewers; bypass policy) | **Live operator prerequisite** — documented; not Terraform |

Sprint 25b.2 does **not** own executable deploy workflows, SSM command execution,
`DATABASE_URL` assembly, migration runs, production approval workflows, rollback,
or live AWS/GitHub UI configuration. Roles modeled in Terraform are **not
operationally approved** until GitHub Environment hard gates are verified.

### 14.1c Sprint 25b.3 (implemented slice)

Sprint 25b.3 owns the **staging-only deployment pipeline** (repository model):

| Concern | Owner |
|---------|--------|
| Staging deploy workflow (`workflow_dispatch`, Environment `staging`) | `.github/workflows/deploy-staging.yml` |
| Release-manifest ingestion + digest authority checks | `scripts/deploy/validate_staging_release.py` (+ 25b.1 validator) |
| Staging release bundle + S3 artifacts bucket | `scripts/deploy/build_staging_bundle.py`, `modules/release_artifacts/` |
| Custom SSM document `DealBrain-StagingDeploy` | `modules/ssm_deploy_document/` (staging root wiring) |
| Host bootstrap (`user_data_base64` gzip) | `infra/ec2/user_data/staging.sh` (Terraform `base64gzip`; cloud-init runs original) |
| Signed Compose plugin install (AL2023 staging) | `scripts/deploy/host/install-compose-plugin.sh` (Sprint 25b.5a) |
| Host-side secret assembly + GHCR stdin login | `scripts/deploy/host/assemble-runtime-env.py`, `ghcr-login.sh` |
| One-shot migrate then API recreate + health gates | `scripts/deploy/host/dealbrain-staging-deploy.sh`, `verify-staging.sh` |
| Append-only staging evidence | `schemas/staging-deploy-evidence.schema.json`, `scripts/deploy/evidence.py` |

Sprint 25b.3 does **not** own production deploy/approval/snapshot/rollback,
CloudWatch/synthetics (25c), or live AWS/GitHub UI configuration. Repository
implementation does **not** imply a live staging deploy has occurred.

### 14.1d Sprint 25b.4a (implemented slice)

Sprint 25b.4a owns **pre-live repository refinements** only:

| Concern | Owner |
|---------|--------|
| Remove S3 `head-bucket` preflight (exact object ops remain authoritative) | `.github/workflows/deploy-staging.yml` |
| Strict ALB target-health (expected instance, state exactly `healthy`) | `scripts/deploy/alb_target_health.py`, `verify-staging.sh` |
| Evidence writer import fail-closed (no inline fallback) | `scripts/deploy/host/write-staging-evidence.py` |
| Host IAM variable description hygiene; unused GHA SSM list actions removed | `modules/iam/variables.tf`, `modules/github_deploy_role/` |

Sprint 25b.4a does **not** apply Terraform, configure GitHub Environments, populate
secrets, send SSM commands, or perform a live deploy. **25b.4b+** remains gated.

### 14.2 Unchanged ownership

- **Readiness semantics (Sprint 22):** `/live`, `/ready`, `/health` meanings unchanged; ALB uses `/ready`, container HEALTHCHECK uses `/live`
- **Persistence (Sprint 23):** Alembic schema and adapters unchanged by infrastructure work
- **API contracts (Sprint 24):** no `/api/v2`, no response body redesign
- **Domain engines (Sprints 1–21):** DealScore, Recommendation, Shopping Assistant ranking, Personal AI, affiliate/merchant neutrality untouched
- **Image publication (Sprint 25b.1):** digest authority and `build-image.yml` contract unchanged by 25b.2/25b.3 IAM/deploy work
- **Sprint 25a networking / RDS secret ownership:** unchanged; 25b.3 only consumes ARNs/outputs for host assembly
- **Sprint 25b.2 trust-policy boundaries:** staging custom SSM allowlist narrows SendCommand; production interim `AWS-RunShellScript` default retained until 25b.4
