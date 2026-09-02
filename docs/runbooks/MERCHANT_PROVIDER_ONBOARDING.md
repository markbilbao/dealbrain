# Merchant / provider onboarding runbook

**Audience:** engineering and owner reviewers preparing a future merchant/provider for evidence-backed certification
**Status:** Sprint 31 formally owner-closed. This runbook does **not** onboard any production provider.
**Sprint 32 status:** In progress; **not complete**. Blocked on external merchant certification.
**Production certified research providers:** **zero**

This is operational documentation only. No application, credential, or certification record is created by this document.

**Related:**

- [`../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md)
- [`../architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md`](../architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md)
- [`../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md`](../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md)
- [`../roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)
- [`../roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](../roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md)
- [`../roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md`](../roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md)

## Purpose

Define how a future merchant/provider moves from **technically integrated** to **eligible for evidence-backed production certification** without bypassing trust gates.

A technically functional connector is **not** enough for production certification.

## Authority boundaries

| Question | Authority |
|----------|-----------|
| What can the implementation do? | Technical provider / connector descriptor |
| May PiqSavi use that capability for this market and source? | Trusted server certification / policy catalog |
| If several providers are already eligible, which order? | Trusted server routing-policy catalog |
| Who executes live research? | Sprint 38, after certification |

Provider implementations do **not** decide whether contractual use is allowed.

Trusted certification / policy review does.

Providers cannot self-certify. Providers cannot self-prioritize.

Affiliate economics may not influence technical certification, legal/policy approval, provider eligibility, routing priority, evaluated-set inclusion, PiqScore, or Recommendation. Affiliate processing remains downstream.

## Isolation rules

- Test providers stay test-only.
- Test certification records stay test-only.
- Test routing policies stay test-only.
- Fixture / demo / simulated-live data may never become live production evidence.
- Production remains fail-closed when no certified provider exists.
- Browser input cannot choose provider, market, certification, or routing priority.

## Onboarding stages

Not every provider has the same API model. Skip inapplicable mechanism steps honestly; do not invent an API.

| Stage | Action | Fail-closed note |
|------:|--------|------------------|
| 1 | Identify merchant/source and intended market (ISO 3166-1 alpha-2) | US does not imply PH or SG |
| 2 | Define provider technical capabilities | Technical support is not permission |
| 3 | Verify source identity | Shopee does not certify Amazon |
| 4 | Identify requested PiqSavi capabilities | Pricing does not certify shipping |
| 5 | Verify API / access mechanism | Official access only; scraping is not a default path |
| 6 | Review legal / contractual use (checklist below) | Engineering interpretation is not counsel approval |
| 7 | Configure secrets **outside** the repository | Credentials ≠ certification |
| 8 | Validate test / sandbox behavior | Sandbox success is not production evidence |
| 9 | Validate provenance / trace expectations | Sprint 38 owns populated traces |
| 10 | Validate reliability requirements against Sprint 31 contract types | Sprint 38 owns runtime retries / breakers |
| 11 | Validate market-specific behavior | Exact-market review required |
| 12 | Collect non-secret evidence references | No privileged legal advice in Git |
| 13 | Create `ResearchProviderCertification` only after approval | Do not create records in this Sprint 31 task |
| 14 | Configure routing policy separately if needed | Certification is not routing preference |
| 15 | Controlled staging validation | Fixture-as-live is forbidden |
| 16 | Production approval | Empty catalog remains the production default until then |

First planned market certification sprint is **Philippines in Sprint 32**. This runbook does not start or close that sprint. Sprint 32 is in progress and remains blocked on external certification.

## Legal / terms evidence checklist (non-secret)

Do not record legal conclusions that do not exist. Each row needs a state and an evidence reference.

Allowed states: `pending` · `reviewed` · `allowed` · `restricted` · `prohibited`

Unknown or unverified permission must not enable production functionality. Use `pending` or treat as not allowed until evidence exists.

| Topic | State | Evidence reference (non-secret) | Review / expiration date |
|-------|-------|----------------------------------|--------------------------|
| Terms of Service / API terms reviewed | | | |
| Allowed automated access confirmed | | | |
| Scraping restrictions reviewed where relevant | | | |
| API licensing restrictions | | | |
| Data retention restrictions | | | |
| Redistribution / display rights | | | |
| Price / display requirements | | | |
| Attribution requirements | | | |
| Rate-limit requirements | | | |
| Geographic restrictions | | | |
| User-data / privacy considerations | | | |
| Credential storage requirements | | | |
| Prohibited-use clauses | | | |
| Affiliate agreement independence (affiliate ≠ product-data permission) | | | |
| Written approval / evidence location | | | |

Sensitive or high-risk uses (reviews, AI reuse of merchant content, comparison where terms are ambiguous, caching beyond explicit documentation, material transformation) remain unapproved unless supported by suitable evidence.

Do not store privileged legal advice or production secrets in Git.

## Certification checklist

Do **not** create a real `ResearchProviderCertification` from this runbook.

Before a later sprint creates one, record:

| Field | Required |
|-------|----------|
| `provider_id` | Yes |
| Capability (exact `ResearchCapability`) | Yes |
| Exact market (ISO 3166-1 alpha-2) | Yes |
| Exact source, or explicit `source_agnostic` scope | Yes — source-agnostic does **not** mean every source |
| Status (`certified` / `revoked` / `disabled` / `pending` / `expired`) | Yes — only `certified` may plan, and only with `allowed` |
| Contractual policy (`allowed` / `restricted` / `prohibited` / `unknown`) | Yes — only `allowed` may plan |
| Certification version | Yes |
| Evidence references (non-secret) | Yes |
| Reviewer / owner | Yes |
| Test / sandbox results | Yes — not production proof by themselves |
| Known limitations | Yes |
| Test-fixture flag | Must be false for production |

Matching is exact:

- a US certification does not certify PH or SG
- a Shopee certification does not certify Amazon
- a pricing certification does not certify shipping

Production catalogs stay empty until Sprints 32–36 add evidence-backed records.

## Routing-policy checklist

Certification does **not** determine routing preference.

If multiple providers are already eligible, any explicit priority must come from the trusted server routing-policy catalog.

| Check | Required |
|-------|----------|
| Provider is already certified `allowed` for the exact requirement | Yes |
| Routing record authored by trusted server policy, not the provider | Yes |
| Commercial / affiliate payout did not set priority | Yes |
| Test routing policies excluded from production | Yes |

An empty production routing catalog is valid. Unconfigured eligible providers may still be ordered by stable `provider_id`. That is not self-prioritization.

## Credential handling

- Never put production secrets in docs or Git.
- Use approved secrets management for the target environment.
- Credentials are separate from certification metadata.
- Having credentials does not imply certification.
- Certification must not expose credentials.
- Opaque credential references may exist on Sprint 18 configuration; they are not research certification.

This runbook adds **no** credential values.

## Provenance / execution-trace expectations

Production certification should establish how **future** Sprint 38 execution will support:

- provider / source identity
- attempted versus not attempted
- checked / freshness timestamp
- evidence provenance
- partial failures
- truthful degradation

Sprint 31 exports the empty trace / plan contracts. Sprint 38 owns populated traces and live execution. Do not claim execution is implemented.

## Reliability checklist

Reference existing Sprint 31 contract types in `app/domain/entities/connector_reliability.py`.

Onboarding / certification should account for:

- timeout behavior
- bounded retry policy
- exponential backoff policy
- quota / rate-limit results
- credential-failure results (no secret values in messages)
- partial results
- kill-switch
- circuit-breaker snapshot compatibility

Actual production runtime retries, timeouts-as-executors, circuit breaking, and degradation orchestration remain **Sprint 38**.

## Market-specific review

Every certification is exact by market.

A provider certified for **US** is not automatically certified for **PH** or **SG**.

Unsupported-market product policy finalizes in Sprint 37. Until then, missing trusted market context must block destination-sensitive planning honestly.

## Source-specific and capability-specific review

Every certification is exact by source and capability unless `source_scope=source_agnostic` is explicit — and source-agnostic still does not mean every named source.

Keep capability / source / market scope written on the record. Do not infer wildcards.

## Affiliate neutrality

Affiliate economics may **not** influence:

- technical certification
- legal / policy approval
- provider eligibility
- routing priority
- evaluated-set inclusion
- PiqScore
- Recommendation

Affiliate permission is independent of product-data permission. Reduced modes remain possible:

- data/compare permitted, affiliate not permitted → organic comparison may operate without monetization
- affiliate permitted, product-data comparison not permitted → destination-only; cannot independently satisfy named-market current-data claims

## Later-sprint ownership

| Sprint | Owns | Do not do in this runbook |
|--------|------|---------------------------|
| 32–36 | Country / merchant certification evidence. First planned market: **Philippines (Sprint 32)** | Create PH or other production certifications |
| 37 | MarketContext, currency, location / destination-sensitive behavior | Implement destination re-evaluation |
| 38 | Live execution, runtime reliability, retries / circuit breakers, truthful degradation, populated execution traces | Execute research or add live HTTP |

Sprint 32 is in progress and is **not complete**. This runbook still creates no production certifications.
