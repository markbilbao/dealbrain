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
| Password recovery | `implemented_verified` | 27.1 request+confirm+hashed single-use tokens; 2026-09-08 staging inbox E2E passed | 27 |
| Email verification | `implemented_verified` | 27.1 request+confirm; signup queues verify; 2026-09-08 staging inbox E2E passed | 27 |
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
| Returning-user experience | `implemented_needs_staging_proof` | Sessions exist; staging password recovery via real email passed 2026-09-08; consumer UX polish remains 29 | 27 / 29 |
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
| Transactional email provider | `implemented_verified` | Resend adapter + fail-closed staging/prod factory; staging `/health` `adapter=resend`; 2026-09-08 real inbox delivery. EXT-08 register row still `applied` (account-establishment screenshot) | 27 |
| Sender-domain verification | `implemented_verified` | EXT-09 **PASS / VERIFIED** 2026-09-08: public DKIM/SPF/MX/DMARC DNS plus owner-observed Resend domain **Verified**. Production email attach remains Sprint 41 | 27 |
| Password-reset email | `implemented_verified` | 2026-09-08 owner Gmail delivery + staging confirm + sign-in | 27 |
| Verification email | `implemented_verified` | 2026-09-08 owner Gmail delivery + confirm; Account `Email status: Verified` | 27 |
| Reset-token expiry / invalidation | `implemented_verified` | Confirm + expiry + consume tested; live reuse not operator-observed | 27 |
| Email-change verification | `implemented_verified` | 27.2 lifecycle + 27.4 Account UX; 2026-09-08 staging inbox confirm passed | 27 |
| Secure session cookies / documented session architecture | `implemented_verified` | Bearer sessions documented; cookies N/A unless introduced | 17 |
| Session rotation | `implemented_verified` | Login issues a new session; password-reset and email-change confirm revoke-all (tests). Refresh-token rotation is not a Sprint 27 launch AC | 27 |
| Session revocation | `implemented_verified` | Logout + password-reset / email-change confirm revoke-all | 27 |
| Auth rate limiting | `implemented_verified` | Per-process buckets | 22 |
| Account enumeration protection | `planned_underspecified` | Needs hardening review | 40 |
| Brute-force / credential-stuffing protection | `planned_underspecified` | Rate limit only; no lockout/bot | 40 |
| Terms of Service | `implemented_needs_staging_proof` | Publication gate exists; 2026-09-10 owner verified live `/terms` remains 404; production unpublished; counsel draft not served | 28 |
| Privacy Policy | `implemented_needs_staging_proof` | Publication gate exists; 2026-09-10 owner verified live `/privacy` remains 404; production unpublished; counsel draft not served | 28 |
| Cookie/tracking disclosure | `implemented_needs_staging_proof` | Factual cookie/storage inventory refreshed including account web-storage; counsel draft unpublished; no CMP banner; essential-only fail-closed hook | 28 |
| Analytics consent | `missing_from_roadmap` | Essential-only deny-by-default hook in Sprint 28; provider/CMP activation remains Sprint 39 / EXT-22 | 28 / 39 |
| Registration consent records | `implemented_needs_staging_proof` | Persist only when a published version exists; unpublished register stores none; owner-scoped inspection API exists; 2026-09-10 owner verified `/account#consents` empty state | 28 |
| Policy-version acceptance records | `implemented_needs_staging_proof` | Server-owned version + timestamp; production catalog empty | 28 |
| Account deletion + confirmation + propagation | `implemented_needs_staging_proof` | Authenticated delete + password re-auth; 28.2 staging HTTP evidence recorded | 28 |
| Data export | `implemented_needs_staging_proof` | Authenticated JSON export; 28.2 staging HTTP evidence recorded | 28 |
| Data retention policy | `implemented_needs_staging_proof` | Engineering TTL map exists; legal retention periods remain counsel-owned; no legal purge jobs | 28 |
| PII inventory | `implemented_needs_staging_proof` | Engineering inventory for current main; not a legal DPA | 28 |
| Privacy / support contact | `implemented_needs_staging_proof` | EXT-17/18 provisioned; `/support` wires `support@piqsavi.com` and `privacy@piqsavi.com`; 2026-09-10 owner verified live Support page; public policy publication still EXT-20/21 | 28 / 39 |
| Minimum age policy | `implemented_needs_staging_proof` | Fail-closed placeholder; no invented age; no DOB collection; counsel-owned activation | 28 |
| Country-specific notices | `implemented_needs_staging_proof` | Fail-closed empty catalog; substantive notices remain counsel / Sprint 37 | 28 / 37 |
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
| Query-time + background sync routing | `planned_sufficient_ac` | Documented Sprint 4 / Sprint 18 dual-run; September 15, 2026 disposition recorded 2026-09-05 — retain intentional dual implementations; not collapsed into one runtime | 31 |
| Normalized listing/offer contracts | `implemented_verified` | Present; unify producers | 18 / 31 |
| Provenance + freshness timestamp/policy | `implemented_verified` | Freshness model; keep | 18 |
| Merchant/credential configuration authority | `planned_underspecified` | Sprint 18 opaque refs exist; research planning has no credentials; live credentials remain later | 31 / 32–38 |
| Feature flags / duplicate registration prevention | `planned_underspecified` | Launch flags exist; research uniqueness enforced; Sprint 18 overwrite is P1; merchant kill switch incomplete | 31 / 38 |
| Sprint 4 and 18 path unification | `planned_sufficient_ac` | Recorded in [`../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md). “4/18” means Sprint 4 search vs Sprint 18 sync, not “4 of 18 items.” Dual-run documented; September 15, 2026 disposition recorded 2026-09-05: retain intentional dual implementations. Sprint 31 remains formally closed | 31 |
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
| Current-main staging deployment + smoke | `implemented_verified` — SHA `79bd03f` staging_ok packaged in [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md); Sprint 26 **COMPLETE / CLOSED** 2026-09-08 (EXT-01 `applied`) | 26 |
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

See [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md). Summary classes: EXT-01 is `applied` (2026-09-08 PH product-data requests; not approved/provisioned; September shopping launch still blocked until a useful PH path is certified). EXT-02…EXT-05 and EXT-07 are `n_a_beta` for the current PH-only beta. Sprint 26 technical staging proof is packaged and Sprint 26 is **COMPLETE / CLOSED** — see [`evidence/SPRINT_26_COMPLETION.md`](evidence/SPRINT_26_COMPLETION.md).

---

## Sprint 30 audit P0–P3 map

| ID | Priority | Finding | Owning sprint |
|----|----------|---------|---------------|
| P0-1 | P0 | No honest live merchant coverage | 32–36 (one primary market sprint per named market) |
| P0-2 | P0 | No production deploy path / production AWS | 41 |
| P0-3 | P0 | M30 observability / paging / restore / runbooks incomplete | 42 |
| P0-4 | P0 | Consumer legal + privacy minimum missing | 28 |
| P0-5 | P0 | Real transactional email + complete password reset | 27 |
| P0-6 | P0 | Current main not staging-proven | 26 — **technical proof packaged** ([`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); Sprint 26 **COMPLETE / CLOSED** 2026-09-08 (EXT-01 `applied`) |
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
| Sprint 26 | Historical 2026-08-24/2026-09-07 note: remained open; packaged staging proof is still SHA `79bd03f`. Later SHAs, including the then-current baseline and PR #114, are not Sprint 26 close evidence. Remaining close blocker after 2026-09-07 was EXT-01 PH product-data bootstrap. **Current (2026-09-08):** COMPLETE / CLOSED after EXT-01 `applied`. |
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
| EXT-01 / EXT-06 | EXT-01 unresolved (`not_started` product-data access). EXT-07 is `n_a_beta` for September. |
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

## 2026-09-06 Sprint 37.4 status addendum

This addendum does **not** rewrite earlier snapshots. It records the owner-authorized destination re-evaluation readiness slice.

| Field | Value |
|-------|-------|
| Sprint 37 | In progress. 37.1–37.3 merged. 37.4 destination-change fail-closed / re-evaluation readiness implemented. Live evidence-backed re-evaluation remains unavailable. Sprint 37 is **not complete**. |
| Destination comparison / invalidation | Implemented on existing `DeliveryContext` / `destination_key` |
| Re-evaluation-required state | Implemented (`required_unavailable` while live path is blocked) |
| Canonical decision immutability | Enforced / tested |
| Shipping / effective-cost truthfulness | Hardened |
| `DESTINATION_REEVALUATION_IMPLEMENTED` | False — live destination re-evaluation, not contract readiness |
| Certified shopping markets | 0 |
| Production FX quotes / providers | 0 |
| P1-1B / P1-2 | Not fully closed |
| Sprint 32 | Unchanged: in progress, blocked on external certification |
| Sprint 33–36 / 38 | Not started |
| Authority | [`sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md); [`../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../architecture/ADR_SPRINT_37_MARKETCONTEXT.md) |

---

## 2026-09-04 Sprint 28.1 status addendum

This addendum does **not** rewrite earlier snapshots. It records the owner-authorized consent/deletion/export/publication-gate slice.

| Field | Value |
|-------|-------|
| Sprint 28 | In progress. 28.1 legal publication gate, consent records, delete/export APIs, inventories, and private-URL noindex implemented. Sprint 28 is **not complete**. |
| Sprint 27 | In progress. 27.3 code/config cutover readiness implemented. EXT-09 DNS not verified. Real inbox E2E not done. Production secret attach remains Sprint 41. Sprint 27 is **not complete**. Snapshot date 2026-09-04; inbox-E2E sentences superseded by the 2026-09-08 addendum. |
| Sprint 37 | Unchanged: in progress, not complete |
| Sprint 32 | Unchanged: in progress, blocked on external certification |
| EXT-19 | Unchanged: `applied` — written approval not present |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md) |

---

## 2026-09-06 owner lock addendum — PH beta merchant neutrality and effective cost

This addendum does **not** rewrite earlier snapshots. It records owner decisions dated 2026-09-06. Documentation only; no merchant is certified by this lock.

| Field | Value |
|-------|-------|
| Owner target | Controlled Public Beta **no later than September 30, 2026** — unchanged |
| Initial validation focus | Philippines first (market priority, not a two-marketplace-only restriction) |
| Initial affiliate-monetization targets | Historical 2026-09-06: Shopee PH + Lazada PH. **Superseded for September launch by 2026-09-07:** no affiliate monetization required. |
| Merchant neutrality | Non-affiliate merchants remain fully eligible for routing / PiqScore / Best Piq / Recommendation. Eligibility is not a requirement to query every integrated merchant on every request. Affiliate status must never exclude or privilege an otherwise relevant legitimate source. |
| Search inclusion | Legitimate data access only; affiliate status is not the inclusion or exclusion test; no scraping workaround; Best Piq among the offers PiqSavi evaluated |
| Effective-cost evidence layers | Technical/source field exposure ≠ Sprint 31 policy authorization ≠ offer/shopper applicability. Do not treat `CapabilityPolicyState` as technical availability. |
| TikTok Shop PH | Not September-launch-critical; must not delay Sprint 45 |
| Effective purchase cost | Reuse Sprint 29 canonical economics; no second price model; no silent PiqScore rewrite |
| Shipping / voucher honesty | Unknown shipping ≠ ₱0/FREE; only verified applicable discounts/vouchers enter scored effective cost |
| Sprint 47 | Remains post-beta. Do not pull campaign prediction, Buy Now/Wait/Watch, or price-drop monitoring into September |
| Launch evidence | Sprint 45 verifies EC-31 on the frozen candidate using actual certified capabilities. Mixed affiliate/non-affiliate runtime proof is conditional (2026-09-07). |
| Authority | [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) §9.5; [`sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md); [`sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md); [`sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md`](sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md); [`sprints/SPRINT_47_OFFER_TIMING_PROMOTIONS_BUYING_ACTION.md`](sprints/SPRINT_47_OFFER_TIMING_PROMOTIONS_BUYING_ACTION.md) |

---

## 2026-09-07 owner lock addendum — public beta without affiliate monetization

This addendum does **not** rewrite earlier snapshots. It records the owner decision dated 2026-09-07. Primarily roadmap/policy reconciliation plus a narrow launch-UI honesty change that removes inactive affiliate-disclosure copy from canonical UUID pages; no merchant is certified; affiliate architecture is not deleted; Sprint 47 remains post-beta.

| Field | Value |
|-------|-------|
| Verdict | **PUBLIC BETA MONETIZATION DEFERRED — PRODUCT VALIDATION LAUNCH LOCKED** |
| Owner target | Controlled Public Beta **no later than September 30, 2026** — unchanged |
| Launch monetization | None required. Ordinary outbound merchant links. PiqSavi may earn ₱0. |
| Beta learning objective | Usefulness, recommendation quality, shopper trust, completed decisions, merchant click-through, repeat usage, demand. No affiliate conversion metric for launch acceptance. |
| Affiliate architecture | Retained for later downstream activation. Must not alter eligibility, evaluated set, PiqScore, Recommendation, Best Piq, or organic ordering. |
| Shopee / Lazada | No longer September affiliate launch dependencies. Product-data certification remains required. Historical affiliate/network evidence retained. |
| EC-31 mixed proof | Conditional: required only if affiliate-enabled merchants are active; otherwise architecture/tests prove affiliate economics are absent from scoring/recommendation. Effective-cost requirements unchanged. |
| Launch UI | No per-action “Affiliate link” / commission claim next to ordinary non-affiliate links. Legal Affiliate & Advertising Disclosure remains future-capable and unpublished. |
| Authority | [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) 2026-09-07 lock; [`sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md); [`sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md`](sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md); [`sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md`](sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md); [`sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md`](sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md) |

### Sprint 26 / PH-only additive reconciliation (same 2026-09-07 policy)

This subsection does **not** replace the owner lock above. It records the Sprint 26 PH validation-beta reconciliation as of 2026-09-07. Documentation only; no merchant is certified. Sprint 26 remained open on that date and later closed on 2026-09-08.

| Field | Value |
|-------|-------|
| Verdict | **SPRINT 26 TECHNICAL COMPLETE — PH DATA-ACCESS BOOTSTRAP REMAINS** (historical 2026-09-07). Current: **SPRINT 26 COMPLETE / CLOSED** (2026-09-08). |
| September supported-market target | Philippines only unless the owner later expands it |
| Launch monetization | Unchanged from the lock above. Affiliate revenue is not a launch acceptance requirement. |
| EXT-01 | Legitimate PH **product-data** access. Affiliate approval alone cannot satisfy it. Historical this snapshot: `not_started` / remaining Sprint 26 blocker. Current: `applied` 2026-09-08. |
| EXT-02…EXT-05 | `n_a_beta` — not required for initial PH beta; rows retained; not submitted |
| EXT-07 | `n_a_beta` / post-beta — not a September blocker |
| EXT-19 | Remains `applied`. Conditional comprehensive counsel review is not unconditional legal approval. |
| Authority | [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) 2026-09-07 lock; [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md); [`sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md); [`sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md); [`sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md`](sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md) |

---

## 2026-09-07 Sprint 27.4 consumer UX addendum

This addendum does **not** rewrite earlier snapshots. It records the consumer email-change / identity success-state slice.

| Field | Value |
|-------|-------|
| Sprint 27 | In progress. 27.4 exposes Account email-change and dedicated verification/reset/email-change success states. A 27.4 follow-up makes the shared account/auth header authentication-aware. This is implementation evidence only. EXT-09 DNS not verified. Real inbox E2E not done. Live staging email-change inbox E2E is still required. Production secret attach remains Sprint 41. Sprint 27 is **not complete**. |
| Authority | [`sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md) |

Inbox-E2E / “not complete” sentences in this **2026-09-07 snapshot** are **not** current. See the 2026-09-08 addendum below.

---


## 2026-09-08 Sprint 27 staging evidence reconciliation

This addendum does **not** rewrite earlier snapshots. It records the 2026-09-08 owner/operator staging inbox E2E plus independent HTTPS/DNS/health checks.

| Field | Value |
|-------|-------|
| Baseline `origin/main` | `55b4e6880875b87bb99bd3331fbe4040fe2483d0` (PR #119; PR #118 ancestor) |
| Staging deploy | Deploy Staging #31 success on that SHA; `https://staging.piqsavi.com` HTTPS 200 |
| Real inbox E2E | **Passed** — verification, password reset, and email-change via Gmail from `PiqSavi <no-reply@piqsavi.com>`; no demo tokens |
| Auth-aware header / logout | **Passed** after PR #119 |
| EXT-09 | **PASS / VERIFIED** — public Resend plan DNS rows plus owner-observed Resend domain **Verified** |
| `identity_email_ready` | Live staging `false` with `adapter=resend` — remaining Sprint 27 closure action is the designed production-code gate, then staging deploy and `/health` verification |
| Production secret attach | Still Sprint 41. Not a Sprint 27 blocker. Production email not claimed live |
| Sprint 27 / P0-5 | **Not closed** |
| Remaining closure action | Separate production-code PR for `identity_email_status().ready`; deploy staging; confirm `/health` `identity_email_ready=true` |
| Authority | [`sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md); [`evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md) |

This 2026-09-08 snapshot is **not** rewritten. The `identity_email_ready=false` / **Not closed** rows were true for Deploy Staging #31. See the Post-PR #121 addendum below.

---

## 2026-09-08 Sprint 27 Post-PR #121 closure addendum

This addendum does **not** rewrite earlier snapshots. It records live staging readiness health after PR #121 and Deploy Staging #32.

| Field | Value |
|-------|-------|
| Git SHA | `a5468ecf65be40bb36a053a97869cec97e3a529c` (PR #121 merge) |
| Build Image | Run `34230096725`; release `rel-20260908T130824Z-a5468ecf65be`; digest `sha256:0a0a3022ecb1f758a0f58aef821adf4dadf8b18834ed3971ee70dc45a2d72787` |
| Staging deploy | Deploy Staging #32 / run `34231964695` SUCCESS; `final_status=staging_ok` |
| Live `/health` | `https://staging.piqsavi.com/health` on 2026-09-08: `environment=staging`, `status=up`, `identity_email_adapter=resend`, `identity_email_ready=true` |
| Earlier #31 observation | Remains historically `identity_email_ready=false` on the previous digest |
| Production secret attach | Still Sprint 41. Production email not claimed live |
| Sprint 27 / P0-5 | **COMPLETE / CLOSED** |
| Authority | [`sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md); [`evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md) §9 |

---

## 2026-09-08 Sprint 26 EXT-01 close addendum

This addendum does **not** rewrite earlier snapshots. It records owner-supplied PH product-data request evidence dated 2026-09-08.

| Field | Value |
|-------|-------|
| EXT-01 | `not_started` → **`applied`**. Request date 2026-09-08. Not `approved` / not `provisioned`. |
| Providers contacted | Lazada Philippines (`affiliate@lazada.com.ph`, 11:09 PM PH); Shopee Philippines (`affiliate_ph@shopee.com`, 11:11 PM PH) |
| Evidence | [`evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md) |
| Sprint 26 | **COMPLETE / CLOSED** — [`evidence/SPRINT_26_COMPLETION.md`](evidence/SPRINT_26_COMPLETION.md) |
| Sprint 32 | Unchanged: in progress / blocked on external certification. A submitted email is not certification. |
| Affiliate monetization | Remains deferred. EXT-07 stays `n_a_beta`. |
| Authority | [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md); [`sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md); [`sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md) |

---

## 2026-09-09 Sprint 28 internal engineering closeout addendum

This addendum does **not** rewrite earlier snapshots. It records remaining internally controllable Sprint 28 readiness. It does **not** publish counsel drafts and does **not** close P0-4.

| Field | Value |
|-------|-------|
| Sprint 28 | **INTERNAL ENGINEERING COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. |
| 28.1 / 28.2 | Unchanged: engineering foundations + staging export/delete HTTP evidence |
| Consent/audit inspection | Owner-scoped `GET /api/v1/auth/account/consents`; non-PII `GET /api/v1/legal/publication-status`. Records stay empty until publication |
| Engineering retention map | [`../privacy/ENGINEERING_RETENTION.md`](../privacy/ENGINEERING_RETENTION.md) — technical TTLs only |
| Tracking | Essential-only fail-closed hook; no CMP banner; EXT-22 `not_started`; Sprint 39 owns activation |
| Eligibility placeholders | No invented minimum age; no DOB collection; country notices unpublished |
| Contacts | `/support` uses provisioned `support@piqsavi.com` and `privacy@piqsavi.com` only |
| EXT-19 | Unchanged: `applied` — written approval not present |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty; `/privacy` and `/terms` 404 |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md) |

---

## 2026-09-10 Sprint 28 internal staging verification addendum

This addendum does **not** rewrite earlier snapshots. It records owner-observed browser verification of the fail-closed legal/privacy state on live staging after PR #125 / Deploy Staging #34. It does **not** publish counsel drafts and does **not** close P0-4.

| Field | Value |
|-------|-------|
| Sprint 28 | **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. |
| Deployed SHA | `fc8be5fe2abb0c73e5db7389ce41c4d348f4ffa0` (PR #125) |
| Build Image | #106 / run `34431847533` SUCCESS; release `rel-20260910T030346Z-fc8be5fe2abb`; digest `sha256:7fadbea3c41fce984bb430bf18b320fd15eacedff10a6e212e72b1af2ea58534`; manifest `e57d424b9b8c0c50976fdac56fe9064e81e33634ce4e56ae6edf332094f71450` |
| Staging deploy | Deploy Staging #34 / run `34432570543` SUCCESS; host `status=staging_ok`; evidence SHA-256 `7165c1ca36d3fd902d44a31ed7378aca1841105dadd6c9fb9199b957eb0b8365` |
| Owner browser checks | 2026-09-10 on `https://staging.piqsavi.com`: `/health` fail-closed unpublished/essential-only; `/privacy` and `/terms` HTTP 404 with no counsel draft served; publication-status unpublished/privacy-safe and free of Sprint/EXT/counsel internals; `/support` exposes only `support@piqsavi.com` and `privacy@piqsavi.com`; signed-in `/account#consents` shows zero acknowledgements and the consumer empty state once |
| 28.1 / 28.2 | Unchanged: engineering foundations + staging export/delete HTTP evidence |
| EXT-17 / EXT-18 | Unchanged: `provisioned` |
| EXT-19 | Unchanged: `applied` — written approval not present |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty; `/privacy` and `/terms` remain 404 |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md); [`evidence/SPRINT_28_INTERNAL_STAGING_VERIFICATION_2026-09-10.md`](evidence/SPRINT_28_INTERNAL_STAGING_VERIFICATION_2026-09-10.md) |

---

## 2026-09-10 Early Access counsel-reconciliation addendum

This addendum does **not** rewrite earlier snapshots. It records the signed 2026-08-19 comprehensive counsel review now sanitized in-repo. It does **not** publish counsel drafts, does **not** close P0-4, and does **not** mark Sprint 32 / public beta complete.

| Field | Value |
|-------|-------|
| Sprint 28 | **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. |
| EXT-19 | Remains `applied`. Written **conditional** approval recorded. Not `approved`. Conditional comprehensive counsel review is not unconditional legal approval. |
| Evidence | [`evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md); [`evidence/EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md`](evidence/EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md) |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty; `/privacy` and `/terms` remain 404 |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Early Access legal links | Remain gated (`aria-disabled` / `data-legal-gated`) |
| Early Access signup assent | Unresolved — sanitized record does not specify the required mechanism |
| Production cutover | **HOLD** — production AWS/secrets/DNS/TLS/deploy workflow remain open |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md); [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) |

---

## 2026-09-11 Early Access legal publication-activation addendum

This addendum does **not** rewrite earlier snapshots. It records that the August 25 revised legal package was still absent from the agent workspace, so Privacy/Terms were **not** published and Early Access legal links were **not** activated. It does **not** close P0-4 and does **not** mark Sprint 32 / public beta complete.

| Field | Value |
|-------|-------|
| Sprint 28 | **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. |
| Result | `EARLY ACCESS LEGAL ACTIVATION BLOCKED — COUNSEL CONDITION REMAINS UNRESOLVED` |
| EXT-19 | Remains `applied`. Written **conditional** approval unchanged. Not `approved`. |
| Evidence | [`evidence/EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md`](evidence/EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md) |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty; `/privacy` and `/terms` remain 404 |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Early Access legal links | Remain gated (`aria-disabled` / `data-legal-gated`) |
| Early Access signup assent | **ASSENT DECISION REMAINS COUNSEL-AMBIGUOUS** |
| Legal/content ready | **No** |
| Production infrastructure ready | **No** — separate HOLD; production AWS/secrets/DNS/TLS/deploy workflow remain open |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md); [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) |

---

## 2026-09-11 Early Access working-draft intake addendum

This addendum does **not** rewrite earlier snapshots. It records that the August 25 revised legal package later arrived and was transcribed as review-only markdown. Privacy/Terms were still **not** published and Early Access legal links were still **not** activated. It does **not** close P0-4 and does **not** mark Sprint 32 / public beta complete.

| Field | Value |
|-------|-------|
| Sprint 28 | **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. |
| Result | `EARLY ACCESS LEGAL ACTIVATION BLOCKED — COUNSEL CONDITION REMAINS UNRESOLVED` |
| EXT-19 | Remains `applied`. Written **conditional** approval unchanged. Not `approved`. |
| Evidence | [`evidence/EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md`](evidence/EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md) |
| EXT-20 / EXT-21 | Unchanged: `not_started` — production published catalog empty; `/privacy` and `/terms` remain 404 |
| EXT-22 | Unchanged: `not_started` — no CMP/banner |
| Early Access legal links | Remain gated (`aria-disabled` / `data-legal-gated`) |
| Early Access signup assent | **ASSENT DECISION REMAINS COUNSEL-AMBIGUOUS** |
| Legal/content ready | **No** |
| Production infrastructure ready | **No** — separate HOLD; production AWS/secrets/DNS/TLS/deploy workflow remain open |
| Authority | [`sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md); [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) |
