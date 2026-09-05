# DealBrain — Global Public Beta Gap Inventory

**Status:** Authoritative Phase 1 inventory for roadmap expansion
**Base HEAD audited:** `fd25cc927236807ae1fe412fa0c4eac2429fbc50`
**Sprint 30 audit source:** [`SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md`](SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md) (2026-08-06; verdict NOT READY, 3/10)
**Master roadmap:** [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Classification date:** 2026-08-06

This inventory records every material Global Public Beta requirement and its coverage state.
**Primary ownership** of each gap is assigned in the master roadmap (**exactly one primary owning sprint** per P0/P1 ID; P1-1 split into P1-1A/P1-1B).

## Classification legend

| Class | Meaning |
|-------|---------|
| `implemented_verified` | Code + tests (and/or ops evidence) support the claim |
| `implemented_needs_staging_proof` | Implemented on main; current-main staging evidence missing |
| `planned_sufficient_ac` | Already planned with acceptance criteria adequate for beta |
| `planned_underspecified` | Mentioned or deferred, but lacking sprint ownership / AC |
| `missing_from_roadmap` | Required for Global Public Beta and not adequately planned |
| `externally_blocked` | Depends on third-party approval or external provider |
| `post_beta_improvement` | Explicitly out of Global Public Beta scope |

---

## Executive gap summary

| Domain | Dominant class | Launch impact |
|--------|----------------|---------------|
| A Consumer journey / UI | `missing_from_roadmap` | Blocks public UX |
| B Identity / email / privacy / legal | Mix of partial + missing | Blocks public self-serve |
| C Merchant platform unification | `planned_underspecified` | Blocks honest multi-path ops |
| D Real merchant coverage (PH/US/SG/UK/CA) | `missing_from_roadmap` / `externally_blocked` | Blocks named markets |
| E MarketContext / currency / localization | `missing_from_roadmap` | Blocks multinational honesty |
| F Connector reliability | Partial design; missing for live HTTP | Blocks live connectors |
| G Recommendation integrity | `implemented_verified` | Gate/certify only |
| H Analytics / beta learning | `missing_from_roadmap` | Blocks learning loop |
| I Security / abuse | Partial; HIGH findings open | Blocks public traffic |
| J Production infra / ops | Staging partial; prod missing | Blocks production launch |
| K Performance / capacity | `missing_from_roadmap` | Blocks announced capacity |
| L Public claims / launch control | `missing_from_roadmap` | Blocks marketing honesty |
| M External dependencies | Mostly unregistered | Blocks markets / launch |

**Prior roadmap endpoint:** Sprint 40 hard endpoint (`ARCHITECTURE_LOCK.md`) with Sprint 30 “public launch” target (`SPRINT_25_PRODUCTION_INFRASTRUCTURE.md`).
**Finding:** Sprints 26–29 and 31–39 were undefined; Sprint 40 was an endpoint without product scope; Sprint 30 as launch was not achieved.

---

## A. Consumer product and user journey

| Requirement | Class | Evidence / notes | Owning sprint |
|-------------|-------|------------------|---------------|
| Production consumer web application | `missing_from_roadmap` | Only `app/static/demo.html`; no frontend package | 29 |
| Responsive mobile web experience | `missing_from_roadmap` | No production UI | 29 |
| Registration | `implemented_verified` | Auth API + tests; staging lifecycle proven on `79bd03f`; UI pending | 17 (impl); 29 (UI); 26 (staging) |
| Login | `implemented_verified` | Same | 17 / 29 / 26 |
| Logout | `implemented_verified` | Session revoke; staging logout→401 re-verified in Sprint 26 smoke | 17 / 29 / 26 |
| Durable sessions | `implemented_verified` | SQLAlchemy store staging-proven on current main (`79bd03f`); see [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) | 17 (impl); 26 (staging) |
| Session expiry and revocation | `implemented_verified` | Expiry + logout revoke; revoke-all hardening → 27; logout revoke re-verified in Sprint 26 authenticated smoke | 17 / 27 / 26 |
| Password recovery | `implemented_needs_staging_proof` | 27.1 request+confirm+hashed single-use tokens; inbox E2E still required | 27 |
| Email verification | `implemented_needs_staging_proof` | 27.1 request+confirm; signup queues verify; inbox E2E still required | 27 |
| Duplicate-account handling | `implemented_verified` | Email uniqueness | 17 |
| Failed-login handling | `implemented_verified` | Errors + rate limit | 17 / 22 |
| Account lockout | `missing_from_roadmap` | Rate limit only | 40 |
| Account persistence | `implemented_verified` | Sprint 23 adapters; SQLAlchemy user-platform binding staging-proven (`79bd03f`) | 23 / 26 |
| Selected-market persistence | `missing_from_roadmap` | No MarketContext | 37 (P1-1B) |
| Search journey | `implemented_verified` | Mock connectors; zero-mutation + authenticated DealScore search staging-proven; UI pending | 4 / 26 / 29 |
| Normalized results | `implemented_verified` | Normalization docs/tests | 18 |
| DealScore display | `implemented_verified` | Engine + API; UI pending | 5 / 29 |
| Recommendation display | `implemented_verified` | Engine + API; UI pending | 6 / 29 |
| AI explanation | `implemented_verified` | Assistant + fallback | 13 |
| AI failure fallback | `implemented_verified` | Deterministic fallback | 13 |
| Merchant-link redirect | `implemented_needs_staging_proof` | Demo affiliate templates | 20 / 32–36 |
| Affiliate disclosure | `planned_underspecified` | Placeholder disclosure; not legal-final | 28 / 44 |
| Returning-user experience | `planned_underspecified` | Sessions exist; no email recovery for real users | 27 / 29 |
| Loading / empty / error / timeout / partial / stale / unsupported-market states | `missing_from_roadmap` | Demo partial only | 29 / 38 |
| Feedback / bug reports / support contact | `missing_from_roadmap` | Merchant field only | 39 |
| Accessibility baseline | `missing_from_roadmap` | No a11y program | 29 |
| Browser compatibility | `missing_from_roadmap` | No matrix | 29 |
| Frontend production build validation | `missing_from_roadmap` | No frontend package | 29 |
| End-to-end user-journey testing | `missing_from_roadmap` | No e2e suite | 29 / 45 |

---

## B. Identity, email, privacy, and legal

| Requirement | Class | Evidence / notes | Owning sprint |
|-------------|-------|------------------|---------------|
| Transactional email provider | `implemented_needs_staging_proof` | Resend adapter + fail-closed staging/prod factory; EXT-08 still `applied` not provisioned | 27 |
| Sender-domain verification | `externally_blocked` | EXT-09 DNS **plan** only; not applied/verified | 27 |
| Password-reset email | `implemented_needs_staging_proof` | Resend-backed send path; no staging inbox evidence yet | 27 |
| Verification email | `implemented_needs_staging_proof` | Same | 27 |
| Reset-token expiry / invalidation | `implemented_needs_staging_proof` | Confirm + expiry + consume; inbox E2E still required | 27 |
| Email-change verification | `missing_from_roadmap` | Deferred — not in 27.1 | 27 |
| Secure session cookies / documented session architecture | `implemented_verified` | Bearer sessions documented; cookies N/A unless introduced | 17 |
| Session rotation | `planned_underspecified` | Login still issues a new session; no refresh-token rotation | 27 |
| Session revocation | `implemented_verified` | Logout + password-reset confirm revoke-all | 27 |
| Auth rate limiting | `implemented_verified` | Per-process buckets | 22 |
| Account enumeration protection | `planned_underspecified` | Needs hardening review | 40 |
| Brute-force / credential-stuffing protection | `planned_underspecified` | Rate limit only; no lockout/bot | 40 |
| Terms of Service | `implemented_needs_staging_proof` | Publication gate exists; production unpublished; counsel draft not served | 28 |
| Privacy Policy | `implemented_needs_staging_proof` | Publication gate exists; production unpublished; counsel draft not served | 28 |
| Cookie/tracking disclosure | `missing_from_roadmap` | Factual cookie inventory refreshed; counsel draft still unpublished; no CMP | 28 |
| Analytics consent | `missing_from_roadmap` | — | 28 / 39 |
| Registration consent records | `implemented_needs_staging_proof` | Persist only when a published version exists; unpublished register stores none | 28 |
| Policy-version acceptance records | `implemented_needs_staging_proof` | Server-owned version + timestamp; production catalog empty | 28 |
| Account deletion + confirmation + propagation | `implemented_needs_staging_proof` | Authenticated delete + password re-auth; staging E2E not done | 28 |
| Data export | `implemented_needs_staging_proof` | Authenticated JSON export; staging E2E not done | 28 |
| Data retention policy | `missing_from_roadmap` | Engineering checklist only; retention periods counsel-owned | 28 |
| PII inventory | `implemented_needs_staging_proof` | Engineering inventory for current main; not a legal DPA | 28 |
| Privacy / support contact | `missing_from_roadmap` | — | 28 / 39 |
| Minimum age policy | `missing_from_roadmap` | — | 28 |
| Country-specific notices | `missing_from_roadmap` | — | 28 / 37 |
| Legal review and approval | `externally_blocked` | Counsel | 28 / 44 |
| Published legal document URLs | `missing_from_roadmap` | — | 28 / 45 |
| Data-processing / vendor register | `missing_from_roadmap` | — | 28 |

---

## C. Merchant platform unification

| Requirement | Class | Evidence / notes | Owning sprint |
|-------------|-------|------------------|---------------|
| One canonical MerchantConnector contract | `planned_sufficient_ac` | ADR rejects one mega-interface; Sprint 4 search, Sprint 18 sync, Sprint 8 collection, and Sprint 31 research remain separate implementations with shared contracts | 31 |
| One MerchantRegistry | `planned_sufficient_ac` | Family-local registries retained; research registry rejects duplicate `provider_id`; optional Sprint 18 duplicate-overwrite fix is P1, not a 31 closer | 31 |
| One MarketRouter | `planned_sufficient_ac` | Authorized-research execution router merged (planning only); capability, certification, and routing-policy catalogs are separate; Sprint 4/18 remain dual-run | 31 |
| MerchantCapability / supported-market metadata | `planned_sufficient_ac` | Sprint 31 research-provider technical capability/market metadata implemented; certification is a separate catalog; unsupported-market product policy still finalizes in 37; production providers uncertified | 31 |
| Merchant contractual capability/policy (fail-closed; distinct from technical ConnectorCapability) | `planned_sufficient_ac` | Sprint 31 fail-closed trusted certification/policy catalog exported (empty in production); Sprints 32–36 still own provider/market evidence; affiliate ≠ data permission | 31 / 32–36 / 45 |
| Merchant-country mapping | `planned_sufficient_ac` | Research certification/descriptors use exact ISO markets; search/sync remain family-local; product policy finalizes in 37 | 31 / 37 |
| Query-time + background sync routing | `planned_sufficient_ac` | Documented Sprint 4 / Sprint 18 dual-run; disposition deadline 2026-09-15; not collapsed into one runtime | 31 |
| Normalized listing/offer contracts | `implemented_verified` | Present; unify producers | 18 / 31 |
| Provenance + freshness timestamp/policy | `implemented_verified` | Freshness model; keep | 18 |
| Merchant/credential configuration authority | `planned_underspecified` | Sprint 18 opaque refs exist; research planning has no credentials; live credentials remain later | 31 / 32–38 |
| Feature flags / duplicate registration prevention | `planned_underspecified` | Launch flags exist; research uniqueness enforced; Sprint 18 overwrite is P1; merchant kill switch incomplete | 31 / 38 |
| Sprint 4 and 18 path unification | `planned_sufficient_ac` | Recorded in [`../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md). “4/18” means Sprint 4 search vs Sprint 18 sync, not “4 of 18 items.” Dual-run documented; hard disposition date **September 15, 2026** | 31 |
| Connector certification suite | `planned_sufficient_ac` | Sprint 31 fail-closed harness/tests exist; real-path evidence remains 32–36 | 31 / 32–36 |
| Merchant legal/terms documentation | `planned_sufficient_ac` | Non-secret checklist in [`../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../runbooks/MERCHANT_PROVIDER_ONBOARDING.md); provider evidence in 32–36; consumer ToS/Privacy remain 28 — not conflated | 31 / 32–36 / 28 |
| Merchant onboarding runbook | `planned_sufficient_ac` | [`../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../runbooks/MERCHANT_PROVIDER_ONBOARDING.md) — operational docs only; no production provider onboarded | 31 |
| Merchant deactivation / kill switch | `missing_from_roadmap` | Research kill-switch hooks exist; marketplace deactivation remains 38 | 38 |
| DealScore / Recommendation / affiliate neutrality boundaries | `implemented_verified` | Preserve; certify | 5 / 6 / 20 / 44 |
| Shipping-cost / unknown-shipping honesty (P1-2) | `planned_underspecified` | Enrichment free-shipping default risk | 37 |

---

## D. Real merchant coverage

| Market | Class | Evidence / notes | Owning sprint |
|--------|-------|------------------|---------------|
| Philippines — merchant selection through production validation | `missing_from_roadmap` / `externally_blocked` | Mock Shopee/Lazada only | 32 |
| United States — full path | `missing_from_roadmap` / `externally_blocked` | Stubs only | 33 |
| Singapore — full path | `missing_from_roadmap` / `externally_blocked` | Stubs only | 34 |
| United Kingdom — full path | `missing_from_roadmap` / `externally_blocked` | Affiliate allow-list only | 35 |
| Canada — full path | `missing_from_roadmap` / `externally_blocked` | None | 36 |
| Public coverage disclosure | `planned_underspecified` | Demo honesty present | 44 / 45 |
| Fixture-as-live prevention | `implemented_verified` | Freshness gates; must remain | 18 / 38 / 45 |

Per-market sub-requirements (provider selection, legal review, credentials, sandbox, real endpoint, mapping, matching, rate limits, quotas, timeouts, retries, credential/quota/outage handling, circuit breaker, provenance, freshness, shipping/availability, affiliate validation, merchant contractual capability/policy evidence, monitoring, staging/limited/production validation, disclosure) are **all** owned by the market certification sprint for that market, with platform primitives from Sprints 31 and 38. Application/approval/credentials/technical connectivity/contractual usability/production certification remain distinct stages; provider approval does not imply blanket capability approval.

---

## E. Market context, currency, and localization

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Coherent MarketContext (account/detected/selected market, delivery, currencies, locale, language, timezone, tax, shipping) | `missing_from_roadmap` | 37 |
| Country/market selector + persistence + safe defaults | `missing_from_roadmap` | 37 |
| Supported/unsupported market configuration + disclosure (P1-1B) | `missing_from_roadmap` | 37 |
| Currency / number / date formatting; original currency preservation | `planned_underspecified` | 37 |
| Mixed-currency fail-closed | `implemented_verified` | Keep; extend UI | 5 / 6 / 37 |
| FX provider, timestamp, staleness, missing-rate, rounding, comparison policy | `missing_from_roadmap` | 37 |
| Taxes/duties/delivery/shipping disclosures; landed-cost limitations | `missing_from_roadmap` | 37 |
| Regional variants (model, voltage/plug, warranty, seller-region) | `missing_from_roadmap` | 37 |
| Localization QA for PH/US/SG/UK/CA; English baseline | `missing_from_roadmap` | 37 |
| French-Canadian scope decision and disclosure | `missing_from_roadmap` | 37 |

---

## F. Connector reliability and honest degradation

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Timeout budgets / retry / exponential backoff | `planned_underspecified` | 38 |
| Rate-limit / quota / credential / outage handling | `planned_underspecified` | 38 |
| Circuit breakers | `missing_from_roadmap` | 38 |
| Connector health model + per-market health | `implemented_verified` (in-process) | 18 / 38 |
| Partial-result aggregation + stale-cache + last-updated | `planned_underspecified` | 38 |
| Incomplete-coverage / no-merchant-available UI disclosure | `missing_from_roadmap` | 29 / 38 |
| Kill switch / merchant feature flags | `planned_underspecified` | 38 |
| Alerting / synthetic probes / incident runbook / provider status | `planned_underspecified` | 38 / 42 |
| AI-provider and affiliate-provider failure behavior | `planned_underspecified` | 38 |
| App readiness ≠ full merchant availability | `implemented_verified` (principle) | 22 / 38 |

---

## G. Recommendation and commercial integrity

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Single DealScore authority; deterministic organic recommendation | `implemented_verified` | 5 / 6 |
| Merchant neutrality; affiliate post-selection only | `implemented_verified` | 20 / 21 |
| Sponsored separation/labeling; personalized/assistant separation | `implemented_verified` | 13 / 16 / 21 |
| Deterministic tie-breaking; missing-data / low-confidence disclosure | `implemented_verified` | 5 / 6 / 13 |
| Explanation consistency; AI fallback; prompt-injection protection | `implemented_verified` | 13 |
| Commercial-term isolation | `implemented_verified` | Lock + tests |
| Public “independent/neutral” claim review | `missing_from_roadmap` | 44 |
| Production monitoring for ranking-integrity violations | `missing_from_roadmap` | 42 / 44 |
| Free-shipping enrichment default disclosure/fix | `planned_underspecified` | 37 (P1-2; 44 verifies wording) |

---

## H. Analytics and beta learning

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Analytics provider decision; consent-gated init | `missing_from_roadmap` | 39 |
| Event schema; identity strategy; deduplication | `missing_from_roadmap` | 39 |
| Registrations / verified / login success-failure | `missing_from_roadmap` | 39 |
| DAU/MAU; searches; success/failure/zero/partial; latency | `missing_from_roadmap` | 39 |
| Merchant/market coverage metrics | `missing_from_roadmap` | 39 |
| Recommendation/DealScore/explanation views; CTR; affiliate attribution | `planned_underspecified` | 20 / 39 |
| Funnel abandonment; retention | `missing_from_roadmap` | 39 |
| Frontend/backend/merchant/AI errors; slow pages/endpoints | `planned_underspecified` | 39 / 42 |
| Quality feedback; bug reports; support requests | `missing_from_roadmap` | 39 |
| Account deletion metrics; privacy consent state; retention | `missing_from_roadmap` | 28 / 39 |
| Dashboards; beta-learning review cadence | `missing_from_roadmap` | 39 / 46 |
| Logging ≠ analytics | `implemented_verified` (principle) | — |

---

## I. Security and abuse protection

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| AuthN/AuthZ / object-level authorization review | `planned_underspecified` | 40 |
| Session security | `implemented_needs_staging_proof` | 27 / 40 |
| Secure headers / CSP / CORS | `implemented_verified` (gaps: CSP unsafe-inline) | 22 / 40 |
| CSRF | `planned_underspecified` | Bearer N/A or enforce if cookies | 40 |
| XSS / SQLi / SSRF / redirect validation / URL allowlisting | `planned_underspecified` | 40 |
| Command injection / log redaction / body logging policy / PII | `planned_underspecified` | 22 / 40 |
| Secret / dependency / SAST / container / Terraform scanning | `missing_from_roadmap` | 40 |
| Supply-chain provenance; immutable-image authority | `implemented_verified` (GHCR digest) | 25b.1 / 40 |
| Least-privilege IAM; AWS OIDC restrictions | `implemented_needs_staging_proof` | 25b.2 / 41 |
| Encryption in transit/at rest; DB network isolation | `planned_sufficient_ac` | 25 / 41 |
| Distributed rate limiting; bot protection; click-fraud | `planned_underspecified` / `post_beta_improvement` for deep WAF | 40 / post-beta |
| AI prompt-injection; merchant-content sanitation | `implemented_verified` (baseline) | 13 / 40 |
| Pen-test readiness; security IR runbook; vuln response | `missing_from_roadmap` | 40 / 42 |
| Every HIGH / launch-blocking MEDIUM finding closed | `missing_from_roadmap` | 40 / 44 |

### Sprint 30 audit security findings mapped

| Severity | Finding | Owning sprint |
|----------|---------|---------------|
| HIGH | No production deploy/isolation path | 41 |
| HIGH | Demo-grade auth/email/reset not production-safe | 27 |
| HIGH | In-process rate limits only | 40 |
| HIGH | No CloudWatch/security paging | 42 |
| HIGH | Production OIDC/SSM interim vs staging hardening | 41 |
| MEDIUM | CSRF not enforced | 40 |
| MEDIUM | CSP `'unsafe-inline'` | 40 |
| MEDIUM | No Dependabot/CodeQL/Trivy/pip-audit | 40 |
| MEDIUM | URL validation / SSRF hardening incomplete | 40 |
| MEDIUM | No account deletion / GDPR path | 28 |

---

## J. Production infrastructure and operations

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Current-main staging deployment + smoke | `implemented_verified` — SHA `79bd03f` staging_ok packaged in [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md); Sprint 26 still open for EXT bootstrap | 26 |
| Production AWS / VPC / DB / secrets / IAM / OIDC / pull / ALB | `planned_sufficient_ac` (TF partial; not applied) | 41 |
| Domain / DNS / TLS | `externally_blocked` + planned | 41 |
| CDN / WAF decision | `planned_underspecified` | 41 (decision); deep WAF `post_beta_improvement` |
| Static asset delivery | `missing_from_roadmap` | 29 / 41 |
| Production deployment + approval gates + evidence | `missing_from_roadmap` | 41 |
| Production rollback workflow | `planned_underspecified` | 41 |
| DB migration / rollback-compat policy | `planned_sufficient_ac` | 25 / 41 |
| Backup / retention / PITR / restore procedure / successful restore rehearsal | `planned_sufficient_ac` (not evidenced) | 42 |
| DR plan; RTO/RPO | `planned_sufficient_ac` | 42 |
| Logging / structured logs / correlation IDs | `implemented_verified` (app); shipping pending | 22 / 42 |
| Error tracking / metrics / dashboards / alerting / paging | `planned_underspecified` | 42 |
| Synthetic monitoring; connector/AI monitoring; audit logs | `planned_underspecified` | 38 / 42 |
| Incident-response plan; runbooks; escalation ownership | `planned_underspecified` | 42 |
| Maintenance mode; feature flags; kill switches; launch freeze | `planned_underspecified` | 42 / 45 |
| Production launch rehearsal; rollback rehearsal; post-launch window | `missing_from_roadmap` | 44 / 45 / 46 |

**Note:** Staging deploy/rollback architecture for older digests is proven. Preserve it. Do not mark production complete from Terraform alone.

---

## K. Performance and capacity

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Load-test tooling; representative staging dataset | `missing_from_roadmap` | 43 |
| API concurrency; search burst; merchant/AI slowdown/outage tests | `missing_from_roadmap` | 43 |
| DB pool/limits/indexes/slow queries | `planned_underspecified` | 43 |
| Cache design; distributed cache decision | `planned_underspecified` | 43 |
| Queue/worker/retry/DLQ/idempotency | `planned_underspecified` / `post_beta_improvement` for full workers | 43 |
| Horizontal scaling / autoscaling / single-instance risk | `planned_underspecified` | 43 |
| Static assets / bundle / images / CDN | `missing_from_roadmap` | 29 / 41 / 43 |
| Rate-limit capacity; AI/merchant quotas; graceful overload | `missing_from_roadmap` | 38 / 43 |
| Celebrity/creator spike simulation | `missing_from_roadmap` | 43 |
| Evidence gates: 1k users, 1k DAU, 10k users, 10k DAU, spike | `missing_from_roadmap` | 43 / 45 |

---

## L. Public claims, marketing, and launch control

| Requirement | Class | Owning sprint |
|-------------|-------|---------------|
| Public coverage matrix; named markets/merchants; unsupported disclosure | `missing_from_roadmap` | 44 |
| Price freshness / shipping-tax / affiliate / sponsored / AI disclosures | `planned_underspecified` | 28 / 44 |
| Privacy/legal links; support; status/incident communication | `missing_from_roadmap` | 28 / 39 / 42 / 44 |
| Launch description / marketing / social claim review | `missing_from_roadmap` | 44 |
| Launch checklist; final legal/security/ops approvals; go/no-go | `planned_underspecified` | 44 / 45 |
| Rollback decision authority; limited rollout %; launch monitoring | `missing_from_roadmap` | 45 |
| Post-launch stabilization sprint | `missing_from_roadmap` | 46 |

Claim-specific matrix lives in the master roadmap.

---

## M. External dependencies

See [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md). Summary classes: mostly `externally_blocked` or still `not_started`. Sprint 26 technical staging proof is packaged; external bootstrap actions remain — see [`evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md). No EXT status was advanced by evidence packaging alone.

---

## Sprint 30 audit P0–P3 map

| ID | Priority | Finding | Owning sprint |
|----|----------|---------|---------------|
| P0-1 | P0 | No honest live merchant coverage | 32–36 (one primary market sprint per named market) |
| P0-2 | P0 | No production deploy path / production AWS | 41 |
| P0-3 | P0 | M30 observability / paging / restore / runbooks incomplete | 42 |
| P0-4 | P0 | Consumer legal + privacy minimum missing | 28 |
| P0-5 | P0 | Real transactional email + complete password reset | 27 |
| P0-6 | P0 | Current main not staging-proven | 26 — **technical proof packaged** ([`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); Sprint 26 remains open for EXT bootstrap |
| P1-1A | P1 | Canonical merchant registration/routing unification | 31 |
| P1-1B | P1 | Unsupported-market product behavior | 37 |
| P1-2 | P1 | Shipping-cost and unknown-shipping honesty | 37 (44 verifies public wording only) |
| P1-3 | P1 | Dependency/container scanning | 40 |
| P1-4 | P1 | Product analytics + feedback/bug path | 39 |
| P1-5 | P1 | Account lockout / distributed rate limits | 40 |
| P1-6 | P1 | Consumer UI beyond demo.html | 29 |
| P1-7 | P1 | Current launch-candidate staging promotion discipline | 26 technical proof packaged ([evidence](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); 45 final verification only |
| P2-* | P2 | FX/MarketContext; WAF/CDN depth; MFA/OAuth | 37 / 41 / post-beta |
| P3-* | P3 | Multi-region DR; autoscaling depth; formal compliance | post-beta (25h / FUT) |

---

## Already adequate for beta (certify, do not rebuild)

- DealScore engine (Sprint 5)
- Organic recommendation engine (Sprint 6)
- Affiliate post-rank attachment + neutrality tests (Sprint 20)
- Merchant/sponsored separation (Sprint 21)
- Shopping Assistant safety / AI fallback (Sprint 13)
- Data freshness honesty for fixtures (Sprint 18)
- Staging deploy + rollback architecture (Sprint 25b.3 / 25b.5*) — **preserve**
- Immutable GHCR digest authority (Sprint 25b.1)
- API contract stability (Sprint 24)

---

## Post-beta improvements (explicit non-goals for Global Public Beta)

- Every retailer worldwide / complete merchant coverage per country
- Worldwide shipping from every merchant
- Always-current prices; guaranteed lowest price
- Automatic scam detection (unless separately proven later)
- Native iOS/Android app stores
- Multi-region active-active
- Full Redis shared-limit / deep CDN-WAF program (beyond launch decision)
- Billing / subscriptions / payments (unless later required)
- MFA/OAuth (unless risk acceptance changes)
- Formal compliance certifications (SOC2, ISO, etc.)
- **P2-OT-01** Offer timing, promotions, and Buying Action intelligence — now numbered **Sprint 47**; post-beta; not a Sprint 45 blocker

---

## 2026-08-24 roadmap reconciliation addendum

This addendum does **not** rewrite the 2026-08-06 audit as if it never happened. It records later merged engineering and the owner public-launch lock.

| Field | Value |
|-------|-------|
| Owner lock | Controlled Global Public Beta Launch no later than **September 30, 2026** |
| Public launch gate | Sprint 45 |
| Immediate post-launch | Sprint 46 |
| Numbered stop | Sprint 47 (P2-OT-01; not a launch prerequisite) |
| Current approved engineering baseline | `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0` — 2977 passed / 0 failed / 0 skipped / 168 warnings (approved merged suite evidence; no newer full-suite run claimed here) |
| Sprint 26 | Remains open. Packaged staging proof is still SHA `79bd03f`. Later SHAs, including the current baseline, are not Sprint 26 close evidence. |
| Sprint 29 | Purpose updated to Production Consumer Decision Experience & Conversational Continuity. 29.0–29.4C, Product Foundation, economics, UUID presentation, schema 1.2, and research authorization handoff are **merged**. Live research remains 31–38. |
| Sprint 31 | Router/provider contract merged (PR #96). Unification ADR and onboarding runbook recorded. Closure evidence implemented; **pending owner close review**. Sprint 32 **NOT STARTED**. Production certified providers remain zero. |
| Consumer UI class update | Section A “Production consumer web application = missing_from_roadmap / only demo.html” is **stale as of this addendum**. Product Foundation surfaces are merged. Staging/launch proof is still pending. |
| Frontend architecture | FastAPI semantic HTML + shared CSS + vanilla-JS ES modules. Mandatory React/Next/Vite/TypeScript/SPA/Node production build is not required. |
| SEO | Explicitly owned across 29 / 39 / 44 / 45 / 46. No separate pre-launch SEO sprint. Private UUID routes must remain non-indexable. |
| Live decision creation | Launch-critical across 29 / 31 / 38. Fixture-created UUIDs are not sufficient for Sprint 45. |
| Market scope | Sprint 45 does not require all five planned markets. ≥1 certified useful market is required for shopping launch. |
| Authority | [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) |

---

## 2026-09-02 Sprint 31 / 32 status addendum

This addendum does **not** rewrite the 2026-08-24 snapshot. It records later owner close and Sprint 32 foundation work.

| Field | Value |
|-------|-------|
| Sprint 31 | Formally owner-closed. Historical 2026-08-24 row (“pending owner close”; “Sprint 32 NOT STARTED”) is no longer current operational status. |
| Sprint 32 | In progress. Foundation slices 32.1–32.5 complete. Sprint 32 is **not complete**. |
| Production catalogs | Certification 0; production evidence 0; providers 0; routing 0 |
| PH documentary evidence | 15 incomplete records; not loaded by production factories |
| PH gate | Still requires a real legally usable merchant-data path. Fixtures cannot close Sprint 32. |
| EXT-01 / EXT-06 / EXT-07 | Unresolved |
| Authority | [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md); [`sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md) |

---

## 2026-09-03 Sprint 37.1 status addendum

This addendum does **not** rewrite earlier snapshots. It records the owner-authorized PH MarketContext foundation slice.

| Field | Value |
|-------|-------|
| Sprint 37 | In progress. 37.1 foundation implemented. Sprint 37 is **not complete**. |
| P1-1B / P1-2 | Not fully closed. Empty certified-market catalog and shipping-unknown honesty exist; five-market selector, FX, and live re-evaluation do not. |
| Certified shopping markets | 0. Default PH context is not PH certification. |
| `DESTINATION_REEVALUATION_IMPLEMENTED` | False |
| Sprint 32 | Unchanged: in progress, blocked on external certification |
| Sprint 33–36 / 38 | Not started |
| Authority | [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md); [`sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md); [`../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../architecture/ADR_SPRINT_37_MARKETCONTEXT.md) |

---

## 2026-09-04 Sprint 37.2 status addendum

This addendum does **not** rewrite earlier snapshots. It records the owner-authorized shopping-market selection and coverage-disclosure slice.

| Field | Value |
|-------|-------|
| Sprint 37 | In progress. 37.1 merged. 37.2 selection + coverage disclosure implemented. Sprint 37 is **not complete**. |
| P1-1B | Partially progressed. Selection persists; unsupported coverage is disclosed; connector invocation remains ineligible. Five-market selector is not implemented. **Not closed.** |
| P1-2 | Unchanged: not fully closed |
| Certified shopping markets | 0. Selected or default PH is not PH certification. |
| Sprint 32 | Unchanged: in progress, blocked on external certification |
| Sprint 33–36 / 38 | Not started |
| Authority | [`sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md); [`../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../architecture/ADR_SPRINT_37_MARKETCONTEXT.md) |

---

## 2026-09-04 Sprint 37.3 status addendum

This addendum does **not** rewrite earlier snapshots. It records the owner-authorized currency-authority and conversion-unavailable foundation.

| Field | Value |
|-------|-------|
| Sprint 37 | In progress. 37.1 and 37.2 merged. 37.3 currency authority implemented. Production FX conversion is **unavailable**. Sprint 37 is **not complete**. |
| EXT-23 | Remains `not_started`. 37.3 adds domain conversion state, fail-closed mixed-currency behavior, and disclosure. It does **not** provide a live FX provider, production quotes, credentials, or operational rate evidence. |
| P1-1B | Unchanged: not fully closed |
| P1-2 | Unchanged: not fully closed |
| Certified shopping markets | 0 |
| Production FX quotes / providers | 0 |
| Sprint 32 | Unchanged: in progress, blocked on external certification |
| Sprint 33–36 / 38 | Not started |
| Authority | [`sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md); [`../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../architecture/ADR_SPRINT_37_MARKETCONTEXT.md) |

---

## 2026-09-04 Sprint 28.1 status addendum

This addendum does **not** rewrite earlier snapshots. It records the owner-authorized consent/deletion/export/publication-gate slice.

| Field | Value |
|-------|-------|
| Sprint 28 | In progress. 28.1 legal publication gate, consent records, delete/export APIs, inventories, and private-URL noindex implemented. Sprint 28 is **not complete**. |
| Sprint 27 | Unchanged: in progress, not complete |
| Sprint 37 | Unchanged: in progress, not complete |
| Sprint 32 | Unchanged: in progress, blocked on external certification |
| EXT-19 | Unchanged: `applied` — written approval not present |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md) |
