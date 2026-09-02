# PiqSavi — Global Public Beta Master Roadmap

**Status:** Authoritative master roadmap (documentation only)
**Owner lock date:** 2026-08-24
**Lock branch:** `docs/lock-public-launch-roadmap-sept-2026`
**Current approved engineering baseline:** `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0`
**Supersedes:** Sprint 40 hard endpoint; Sprint 30 “public launch” target as launch achievement; prior Sprint 46 program-endpoint wording as the final numbered stop
**Preserves:** Sprint identities 1–40 as historical; Architecture Lock domain ownership for Sprints 1–25; Sprint 30 closed-audit identity
**Companion docs:** [`GAP_INVENTORY.md`](GAP_INVENTORY.md) · [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) · [`PIQSAVI_PUBLIC_BRAND_POLICY.md`](PIQSAVI_PUBLIC_BRAND_POLICY.md) · [`sprints/`](sprints/) · [`evidence/`](evidence/)
**Sprint 30 audit:** [`SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md`](SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md) — NOT READY (3/10)
**Sprint 26 technical evidence:** [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) — current-main staging proof verified for SHA `79bd03f`; Sprint 26 remains open for external bootstrap
**Public brand authority:** [`PIQSAVI_PUBLIC_BRAND_POLICY.md`](PIQSAVI_PUBLIC_BRAND_POLICY.md)

---

> **OWNER ROADMAP LOCK — 2026-08-24**
>
> PiqSavi targets Controlled Global Public Beta Launch no later than September 30, 2026.
>
> The roadmap is locked through Sprint 47.
>
> Sprint 45 remains the public-launch gate.
>
> Sprint 46 remains post-launch stabilization.
>
> Sprint 47 is post-beta buying-action intelligence and is not a launch prerequisite.
>
> New pre-launch sprints or major architectural scope may not be inserted without explicit owner approval.
>
> Launch-date pressure may reduce optional market/provider/feature scope but may not weaken truthfulness, privacy, security, legal, production, or evidence requirements.

---

## 0. Authority and change control

1. This document is the **sole authoritative Global Public Beta roadmap**.
2. Sprint definitions under `docs/roadmap/sprints/` are normative detail owned by this master; they must not conflict with it.
3. `docs/architecture/ARCHITECTURE_LOCK.md` remains the domain-ownership lock; this roadmap **extends** launch sequencing and does not silently redistribute DealScore / PiqScore, Recommendation, affiliate, or merchant neutrality ownership.
4. Future roadmap additions require: gap ID, single owning sprint, acceptance evidence, beta-blocker classification, and an Architecture Lock review if ownership/invariants change.
5. Do not claim incomplete work complete. Do not mark connectors complete without real provider evidence. Do not mark production complete from Terraform alone.
6. Do not create a competing second master roadmap.

### 0.1 Public brand authority

| Field | Value |
|-------|-------|
| Public product | **PiqSavi** |
| Public tagline | Your AI Personal Shopper |
| Primary public domain | piqsavi.com |
| Canonical public URL | https://piqsavi.com |
| Internal engineering codename | **DealBrain** |
| Public launch gate | **Sprint 45 — Controlled Global Public Beta Launch** |
| Owner target launch date | **September 30, 2026** |
| Immediate post-launch program | **Sprint 46 — Post-Launch Stabilization** |
| Roadmap numbered stop | **Sprint 47 — Offer Timing, Promotions & Buying Action Intelligence** (post-beta; not a launch prerequisite) |
| Brand policy | [`PIQSAVI_PUBLIC_BRAND_POLICY.md`](PIQSAVI_PUBLIC_BRAND_POLICY.md) |

Public consumer brand is PiqSavi; DealBrain remains the internal technical codename. Do not rewrite historical sprint descriptions solely to replace DealBrain. Do not alter sprint numbering. Infrastructure cosmetic renames are out of scope for public-brand launch. Do not add Sprints 48+ in this lock.

### 0.2 Date semantic — September 30, 2026

September 30, 2026 is the **OWNER TARGET LAUNCH DATE**.

It is **not** permission to:

- bypass security gates
- bypass privacy/legal gates
- fake merchant coverage
- call fixture/mock research live
- publish unsupported market claims
- weaken evidence standards
- skip production rehearsal
- skip production operations readiness

Where optional market/provider readiness threatens the date:

**reduce launch scope rather than reduce truthfulness or safety.**

Example: if only Philippines and United States are legitimately launch-ready, Sprint 45 may launch those supported markets and omit unsupported markets. Do not require all originally planned markets if this roadmap already allows market removal.

At least one truthful, genuinely useful supported market must exist for public shopping launch.

### 0.3 Current approved engineering baseline

| Field | Value |
|-------|-------|
| SHA | `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0` |
| Meaning | Latest approved **merged** baseline on `main` after PR #96 (certified research execution router contract) |
| Merge | PR #96 — Add certified research execution router contract |
| Verified suite | **2977 passed / 0 failed / 0 skipped / 168 warnings** (approved pre-merge feature evidence; no newer full-suite run is claimed here) |

This SHA replaces the prior merged baseline `d40b153a5accfbf54b2d6a5c9bd62ee17cd127fc` (PR #95). Historical PR #91 presentation work landed on `ab23d29e5f303bd5ecdfed60f7e7defe598d84d0` (suite 2819) and remains an ancestor.

It is **not**:

- the final launch candidate
- Sprint 26 close evidence
- a replacement for the packaged Sprint 26 staging proof at SHA `79bd03f`
- proof that live merchant research exists
- proof that any Philippines merchant path is production-certified
- Sprint 32 closure evidence

Phases 29.4B and 29.4C, the research authorization handoff (PR #95), and the Sprint 31 router contract (PR #96) are **merged**. Sprint 31 was formally owner-closed after this baseline was recorded. Sprint 32 is now in progress and is **not complete**. Live research execution remains unimplemented. Production certified research providers remain **zero**.

### 0.4 Status honesty

Do not mark work complete simply because it has a design or contract.

Use these distinctions:

| Status | Meaning |
|--------|---------|
| planned | Owned and specified; not implemented |
| in progress | Active implementation; not merged or not accepted |
| implemented | Code exists on a working branch or main |
| merged | Present on approved `main` |
| complete | Owning sprint acceptance criteria satisfied |
| staging-proven | Live staging deploy + required smoke/evidence for that capability |
| production-proven | Live production evidence under controlled rollout |
| launch-verified | Sprint 45 go/no-go recorded against the frozen candidate |
| externally blocked | Waiting on third-party approval, credentials, or publication |

Do **not** equate:

- mock = live
- code = production
- roadmap approval = external approval
- tests = legal approval
- fixture = merchant certification
- this engineering baseline = launch candidate

### 0.5 Launch blocker classification

| Class | Meaning | Date-pressure rule |
|-------|---------|--------------------|
| **NON-WAIVABLE P0** | Must be true for public shopping launch | Cannot be skipped to hit September 30 |
| **SCOPE-REDUCIBLE** | May be removed from launch claims | Remove/delay the claim or feature rather than fake readiness |
| **POST-LAUNCH** | Explicitly after Sprint 45 | Must not block Sprint 45 |

**Non-waivable P0 examples:** security launch blocker; privacy/legal publication; truthful real research in at least one certified market; production deployment; session/owner protection; supported-market honesty; monitoring/paging; launch rehearsal.

**Scope-reducible examples:** an individual market not certified; optional source/provider; optional product category; optional advanced feature.

**Post-launch examples:** Sprint 47 advanced buying-action intelligence.

This distinction protects the September target without sacrificing integrity.

### Evidence maturity legend

| Level | Meaning |
|-------|---------|
| Implemented | Code or config exists on the launch candidate |
| CI tested | Automated tests/gates green on that candidate |
| Immutable image built | GHCR digest published for the candidate |
| Staging proven | Live staging deploy + required smoke/evidence for that capability |
| Production rehearsed | Production (or production-equivalent) dry-run evidence filed |
| Production proven | Live production evidence under controlled rollout |
| Launch approved | Legal + security + ops go/no-go recorded |

---

## 1. Executive roadmap decision

| Decision | Value |
|----------|-------|
| Previous endpoint | **Sprint 40** (hard endpoint in Architecture Lock); Sprint 30 named as public launch target in Sprint 25 infra contract |
| Gap analysis result | Sprint 40 endpoint and Sprint 30 launch target are **insufficient / unmet** for an honest Global Public Beta |
| Public launch gate | **Sprint 45** — Controlled Global Public Beta Launch |
| Owner target date | **No later than September 30, 2026** |
| Immediate post-launch close | **Sprint 46** — Post-Launch Stabilization |
| Numbered roadmap stop | **Sprint 47** — Offer Timing, Promotions & Buying Action Intelligence (post-beta; not a launch prerequisite) |
| Newly scoped historical slots | Sprints **26–29** and **31–40** (were undefined or underspecified); Sprint **30** reclassified and remains closed |
| Added sprints beyond 40 | **7** (Sprints 41–47) |
| Smallest realistic extension | Justified by five market certifications, legal/privacy, consumer decision experience, production ops evidence, capacity, launch control, and a visible post-beta intelligence stop |

**Default execution order after this lock:**
`26 → 27 → 28 → 29 → 31 → (32∥33∥34∥35∥36) → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 LAUNCH → 46 STABILIZATION → 47 POST-BETA INTELLIGENCE`

**Reliability sequencing (non-negotiable):**
- Sprint **31** delivers shared minimum connector reliability contracts **and** the shared merchant contractual capability/policy model with fail-closed enforcement hooks (strict predecessor of 32–36).
- Market certifications **32–36** may run in parallel after Sprint 31 and must validate those minima on real paths, including evidence-backed capability-policy certification per provider/market.
- Sprint **38** hardens and consolidates cross-connector production reliability; it is **not** the first appearance of basic timeout/retry/failure handling, and it must respect certified merchant TTL/freshness policy constraints without owning legal-policy interpretation.

**Merchant connector capability-policy principles (roadmap-locked; implementation in Sprint 31 / certification in 32–36):**
- Affiliate permission ≠ product-data permission; reduced certified modes remain possible.
- Technical `ConnectorCapability` (adapter operations) ≠ contractual/policy authorization.
- Provider approval ≠ blanket capability approval; unknown permissions fail closed.
- Affiliate monetization remains outside DealScore / PiqScore / objective ranking.
- Upstream payload presence is not permission to expose or use data.
- No merchant connector may be production-certified or used to support a named shopping-market claim unless relevant permissions are explicitly declared, evidence-backed, and fail-closed enforced.

(Sprint 30 is a closed audit identity; do not re-open it as an implementation sprint.)

---

## 2. Global Public Beta definition

Global Public Beta means **all** of the following:

1. Public web access is available internationally.
2. Users can register, authenticate, recover accounts, manage privacy choices, and delete their accounts.
3. PiqSavi clearly distinguishes: globally reachable service; supported shopping markets; supported merchants; delivery destinations; display currencies.
4. Initial *planned* named live-shopping markets are **Philippines, United States, Singapore, United Kingdom, Canada** — each named only when its market gate passes.
5. Sprint 45 does **not** require all five planned markets. The actual supported-market list is documented at Sprint 44/45 from certification evidence.
6. Each **named** supported market has at least one real, legally usable, operationally validated merchant-data path.
7. At least one genuinely useful certified market must exist for public shopping launch.
8. Unsupported markets receive explicit coverage disclosure and are never presented with fixture data as live prices.
9. A real shopper request in a supported market can create an owner-bound canonical decision from live certified evidence — fixture-created UUIDs are not sufficient.
10. After Recommendation, Ask PiqSavi remains available on Results, Compare, and Why This Is the Best Piq for You.
11. The service has production deployment, rollback, monitoring, backup, incident-response, and capacity evidence.
12. Public claims are limited to proven capabilities.
13. Personalized decision URLs remain private/non-indexable.

Global Public Beta does **not** mean: every retailer worldwide; complete merchant coverage in every country; worldwide shipping from every merchant; always-current prices; guaranteed lowest price; automatic scam detection unless separately proven; Sprint 47 buying-action intelligence; ranking-position promises.

---

## 3. Historical sprint identities (1–40) — preserved

| Sprint | Historical identity | Global Beta posture |
|--------|---------------------|---------------------|
| 1–3 | Product identity / registry / matching | Preserve |
| 4 | Marketplace search / intelligence | Preserve; unify via 31; real data via 32–36 |
| 5 | DealScore / PiqScore | Preserve; certify |
| 6 | Recommendation decisions | Preserve; certify |
| 7–16 | Price history, collection, watchlists, reviews, assistant, community, KG, personal AI | Preserve |
| 17 | Consumer users / auth / sessions / profiles | Preserve; complete via 27–28 |
| 18 | Current marketplace offers / sync / freshness | Preserve; unify via 31; harden via 38 |
| 19–21 | Alerts, affiliate, merchant orgs | Preserve neutrality |
| 22 | Launch infrastructure / readiness | Preserve probes |
| 23 | Production persistence adapters | Preserve |
| 24 | API contracts | Preserve |
| 25 (+b.*) | Production infrastructure / staging deploy / rollback | Preserve architecture; complete remaining evidence via 26 / 41 / 42 |
| 26 | Staging Current-Main Proof & Roadmap Bootstrap | Open — technical proof packaged; EXT bootstrap pending |
| 27–28 | Identity/email; privacy/legal | Planned |
| 29 | Production Consumer Decision Experience & Conversational Continuity | In progress — see §5.1 |
| 30 | **Reclassified:** Public Beta Readiness Audit (2026-08-06) — **not** a launched public shopping beta | Closed audit |
| 31–40 | Previously underspecified deferred bucket — now scoped | Planned |
| 41–46 | Beyond superseded Sprint 40 hard endpoint | Planned |
| 47 | Post-beta offer timing / buying-action intelligence | Planned; not a launch prerequisite |

### Sprint 30 reclassification (mandatory)

| Field | Prior claim | Accurate classification |
|-------|-------------|-------------------------|
| Name | Public launch (M30 target) | **Public Beta Readiness Audit** |
| Outcome | Implied launch readiness | **NOT READY** (3/10) |
| Completion | Not achieved as launch | Audit complete; launch incomplete |
| Effect on roadmap | Hard gate for “public launch” | Findings mapped to Sprints 26–47; does not authorize market naming |

Obsolete statements such as “hard launch target: Sprint 30 public launch” and “hard endpoint: Sprint 40” are **superseded for launch sequencing** but retained in historical docs with pointers here.

Do **not** reopen Sprint 30.

---

## 4. Phase structure (evidence-based)

| Phase | Sprints | Focus |
|-------|---------|-------|
| 1 Roadmap reconciliation & staging-current proof | 26 | Close P0-6; bootstrap external apps |
| 2 Consumer identity, email, privacy, legal | 27–28 | Close P0-4, P0-5 |
| 3 Production consumer decision experience & Conversational Continuity | 29 | Close P1-6; implement CC-01; SEO technical foundation |
| 4 Merchant platform unification + min reliability contracts | 31 | Close P1-1A; reliability contract for 32–36 |
| 5 Real merchant integrations & market certification | 32–36 | Close P0-1 per market (may parallelize after 31) |
| 6 MarketContext, currency, shipping, localization, destination re-evaluation | 37 | Close P1-1B + P1-2; multinational honesty |
| 7 Cross-connector reliability & truthful live research | 38 | Harden certified connectors; live-mode gate |
| 8 Analytics, feedback, support, SEO measurement | 39 | Beta learning + Search Console |
| 9 Security & abuse hardening | 40 | HIGH/MEDIUM closures |
| 10 Production infrastructure & operations | 41–42 | Close P0-2, P0-3 |
| 11 Performance, scaling, spike validation | 43 | Capacity evidence |
| 12 Launch claims, approvals, rehearsal | 44 | Go/no-go package + SEO rehearsal |
| 13 Controlled Global Public Beta launch | 45 | Public cutover — target no later than 2026-09-30 |
| 14 Post-launch stabilization | 46 | Immediate program close after launch |
| 15 Post-beta offer timing & buying-action intelligence | 47 | Not a launch prerequisite |

---

## 5. Master sprint matrix

| Sprint | Name | Primary outcome | Main blockers addressed | External dependencies | Exit gate |
|--------|------|-----------------|-------------------------|-----------------------|-----------|
| 26 | Staging Current-Main Proof & Roadmap Bootstrap | Historical launch-candidate staging-proven (`79bd03f`); EXT apps bootstrap pending | P0-6 | EXT-01…05,08,10,17,18 bootstrap | Technical: Staging `/ready` + smoke on evidenced digest ([evidence](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); close still requires register updates. Later SHA `ab23d29` is **not** a Sprint 26 close. |
| 27 | Transactional Identity & Email | Real email; reset/verify/email-change; token lifecycle; enumeration-safe errors; session rotation | P0-5; HIGH demo-auth | EXT-08, EXT-09 | Staging E2E reset+verify via real provider; production cutover readiness recorded |
| 28 | Privacy, Legal, Consent & Deletion | ToS/Privacy/consent/deletion/export + search-index privacy | P0-4; MEDIUM GDPR | EXT-17…22 | Legal draft published internally; deletion E2E staging; counsel review started; private decision URLs non-indexable by policy |
| 29 | Production Consumer Decision Experience & Conversational Continuity | Public decision surfaces + a11y + Ask PiqSavi + SEO technical foundation | P1-6; CC-01 | None critical | Staging UI journey and CC-01 green; FastAPI HTML/CSS/vanilla-JS validation; no fixture-as-live in UUID mode |
| 30 | Public Beta Readiness Audit *(historical)* | Audit record only | — | — | Closed — NOT READY |
| 31 | Merchant Platform Unification | One connector/registry/router + min reliability contracts + capability/policy model + research execution contracts | P1-1A | None | Certification suite exists; 4/18 dual-path retired or dual-run documented; reliability + capability/policy + provenance/trace contracts exported (fail-closed) |
| 32 | Philippines Merchant Certification | ≥1 real PH path | P0-1 (PH) | EXT-01,06,07 | Real legally usable current-data response + capability-policy evidence; staging+limited proof. Fixtures cannot certify. |
| 33 | United States Merchant Certification | ≥1 real US path | P0-1 (US) | EXT-02,06,07 | Same for US |
| 34 | Singapore Merchant Certification | ≥1 real SG path | P0-1 (SG) | EXT-03,06,07 | Same for SG |
| 35 | United Kingdom Merchant Certification | ≥1 real UK path | P0-1 (UK) | EXT-04,06,07 | Same for UK |
| 36 | Canada Merchant Certification | ≥1 real CA path | P0-1 (CA) | EXT-05,06,07 | Same for CA |
| 37 | MarketContext, Currency & Localization | Coherent market/FX/locale + shipping honesty + destination re-evaluation | P1-1B; P1-2 | EXT-23 | Fail-closed FX; unsupported-market behavior; shipping honesty; server-side re-evaluation when destination materially changes cost; FR-CA decision recorded |
| 38 | Connector Reliability & Honest Degradation | Production live-research execution + truthful degradation | Live-HTTP risk | EXT-25 | Multi-connector chaos + probes + aggregated health + execution-trace evidence; `SHOPPING_RESEARCH_EXECUTION_MODE=live` fail-closed unless certified connector + truthful partial-failure exist |
| 39 | Analytics, Feedback & Support | Consent-gated product analytics + support + SEO measurement | P1-4 | EXT-15,16,17,22,29 | Events + dashboards + feedback/report-incorrect path + Search Console setup in staging/prod-prep |
| 40 | Security & Abuse Hardening | HIGH/launch-blocking MEDIUM closed | P1-3, P1-5; sec findings | — | Security go/no-go package ready; owner-bound decision isolation proven |
| 41 | Production Environment & Deploy Path | Isolated prod AWS + deploy/rollback + DNS/TLS | P0-2; HIGH prod path | EXT-10…14 | Prod dry-run `/ready`; rollback path exists; IaC alone is not proof |
| 42 | Production Operations & DR Evidence | Monitoring, paging, backup restore, runbooks | P0-3 | EXT-16,24 | Restore drill + page ack evidence filed |
| 43 | Performance & Capacity Validation | Load/spike evidence for announced size | Capacity unknown | EXT-25 | Evidence for 1k/10k gates or reduced announcement; Ask/search/crawler bursts included |
| 44 | Claims, Approvals & Launch Rehearsal | Approved claims + go/no-go + SEO/indexing rehearsal | Claim honesty | EXT-19…21 | Signed legal/security/ops approvals; rehearsal OK; supported-market list frozen from evidence |
| 45 | Controlled Global Public Beta Launch | Public beta live under controlled rollout no later than 2026-09-30 | All exit criteria §9 | Remaining EXT as applicable | Exit criteria all true or market/feature removed; no-go if any non-waivable blocker remains |
| 46 | Post-Launch Stabilization | Stabilize; absorb Sev0/1/2; SEO/ops learning | Post-cutover risk | — | Stability window complete; backlog groomed; no deferred 45 blockers absorbed |
| 47 | Offer Timing, Promotions & Buying Action Intelligence | Post-beta Layer 3 buying action | P2-OT-01 | Later EXT as required | Not a Sprint 45 gate |

Detailed definitions: [`sprints/`](sprints/).

### 5.1 Sprint 29 — status and sub-phase record

**Purpose (updated):** Production Consumer Decision Experience & Conversational Continuity, while preserving frontend/accessibility responsibility.

Sprint 29 is **no longer adequately described** as only “Production Consumer Web UI & Accessibility.”

| Sub-phase | Status | Evidence / notes |
|-----------|--------|------------------|
| 29.0 CC-01 contract freeze | **merged** | PR #83 |
| 29.1 Conversation domain | **merged** | PR #84 |
| 29.2 Conversation persistence | **merged** | PR #85 |
| 29.3 Canonical decision snapshots | **merged** | PR #86 |
| Product Foundation Results / Compare / Why / Ask / delivery UX | **merged** | PR #87 |
| 29.4A `answer_from_evidence` | **merged** | PR #88 |
| Canonical offer economics (schema 1.1) | **merged** | PR #89 |
| Canonical UUID consumer presentation | **merged** | PR #90 |
| Canonical decision presentation contract (schema 1.2) | **merged** | PR #91 on baseline `ab23d29` |
| 29.4B `refine_session_recommendation` | **merged** | Session overlay only; PiqScore and canonical snapshot stay immutable |
| 29.4C `propose_research` | **merged** | Proposal + confirmation only; research execution remains unimplemented and owned by Sprints 31–38 |
| Research Authorization / Execution Handoff Contract | **merged** | Server-authoritative confirmation artifact; Sprint 31 planning is separate; live research execution remains unimplemented and owned by Sprints 31–38 |
| Live research execution | **not owned here** | Sprints 31–38 |
| Full CC-01 staging proof on frozen launch candidate | **pending** | Required for EC-02 / EC-22 |

**Do not** mark Sprint 29 closed. Product Foundation and canonical presentation work do not certify live merchant research.

**Frontend architecture lock (reconcile stale wording):** production consumer frontend remains FastAPI-served semantic HTML, shared CSS, and native vanilla-JavaScript ES modules. Mandatory React, Next.js, Vite, TypeScript production build, SPA architecture, or Node production build is **not** required unless independently approved later.

---

## 6. Gap-coverage matrix (audit requirements → owners)

| Audit requirement | Existing coverage | New owning sprint | Acceptance evidence | Launch blocker? |
|-------------------|-------------------|-------------------|---------------------|-----------------|
| Current-main staging proof | Older SHA staging proven; **`79bd03f` staging_ok packaged**; later SHAs including `d62a6fb` are not Sprint 26 close evidence | 26 | Evidence JSON + `/ready` on evidenced digest — see [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md); EXT bootstrap still open; later SHAs need their own staging proof before launch | Yes |
| Real email + password recovery | NullEmailSender / demo tokens | 27 | Inbox delivery + confirm routes | Yes — NON-WAIVABLE |
| Email verification | Partial request-only | 27 | Verify confirm E2E | Yes — NON-WAIVABLE |
| ToS / Privacy / consent | Missing | 28 | Published URLs + consent records | Yes — NON-WAIVABLE |
| Account deletion / export | Missing | 28 | Delete+export E2E; propagation checklist | Yes — NON-WAIVABLE |
| Consumer production decision UI | Product Foundation merged; not launch-verified | 29 | Staging UI e2e on FastAPI HTML/CSS/vanilla-JS surfaces | Yes (public UX) |
| Conversational Continuity | Partial: 29.0–29.4C merged; live research later | 29, supported by 31/37/38/39/40/43/44/45 | CC-01 staging E2E on the immutable candidate | Yes — NON-WAIVABLE |
| Live owner-bound decision creation | Fixture/UUID presentation exists; live pipeline missing | 29 / 31 / 38 | Real shopper request → live evidence → snapshot → UUID Results | Yes — NON-WAIVABLE |
| Sprint 4/18 unification (P1-1A) | Dual-run documented; research router merged; ADR recorded; Sprint 31 owner-closed | 31 | Shared contracts + fail-closed capability/policy; 4/18 means Sprint 4 search vs Sprint 18 sync; disposition deadline 2026-09-15 | Yes (P1) |
| Unsupported-market behavior (P1-1B) | Missing | 37 | Selector + disclosure + no unsupported invoke | Yes (P1) |
| Shipping-cost honesty (P1-2) | Enrichment default risk | 37 | Shipping-known/unknown modeled + tests; 44 verifies wording | Yes (P1) |
| Destination re-evaluation | Canonical pages show decision-time destination only | 37 | Server-side re-evaluation when destination could materially change shipping/effective cost | Yes when destination is user-changeable |
| PH real merchant path | Fixtures only | 32 | Live provider response certified | Yes to **name PH** — SCOPE-REDUCIBLE |
| US real merchant path | Stubs | 33 | Same | Yes to **name US** — SCOPE-REDUCIBLE |
| SG real merchant path | Stubs | 34 | Same | Yes to **name SG** — SCOPE-REDUCIBLE |
| UK real merchant path | Allow-list only | 35 | Same | Yes to **name UK** — SCOPE-REDUCIBLE |
| CA real merchant path | None | 36 | Same | Yes to **name CA** — SCOPE-REDUCIBLE |
| At least one certified useful market | None certified | 32–36 + 44/45 | ≥1 named market with real current-data path | Yes — NON-WAIVABLE for shopping launch |
| MarketContext / FX / localization | Missing | 37 | Fail-closed FX tests + selector | Yes for multi-market honesty |
| Cross-connector reliability + live research | Missing / partial | 38 | Multi-connector chaos + probes + disclosures + live-mode gate | Yes with live HTTP — NON-WAIVABLE |
| Product analytics + feedback | Logs/demo only | 39 | Consent-gated events + support/report-incorrect path | Soft Yes (learning); report-incorrect is launch-useful |
| SEO technical foundation / private-route noindex | Partial brand metadata only | 29 / 39 / 44 / 45 / 46 | robots/sitemap/canonical/noindex + Search Console; UUID routes private | Yes for indexability honesty — NON-WAIVABLE for private routes |
| Security HIGH / blocking MEDIUM | Open | 40 | Closure evidence | Yes — NON-WAIVABLE |
| Production deploy path | Missing | 41 | Prod dry-run evidence | Yes — NON-WAIVABLE |
| Monitoring / paging / restore | Incomplete | 42 | Drill + page proofs | Yes — NON-WAIVABLE |
| Capacity 1k/10k/spike | Unproven | 43 | Load reports | Yes for announced size — SCOPE-REDUCIBLE announcement |
| Public claims approval | Missing | 44 | Signed claim matrix | Yes — NON-WAIVABLE |
| Controlled public launch | Missing | 45 | Checklist sign-off | Yes — NON-WAIVABLE |
| Post-launch stabilization | Missing | 46 | Stability report | Program close |
| Offer timing / buying action | Spec only (P2-OT-01) | 47 | Post-beta | POST-LAUNCH |
| Staging promotion discipline (P1-7) | `79bd03f` staging_ok + smoke packaged | 26 | Current-candidate staging_ok + smoke; 45 final verify on **frozen** candidate | Yes (P1) |
| DealScore / organic neutrality | Verified | 5/6 + 44 certify | CI + monitoring | Integrity gate — NON-WAIVABLE |
| Fixture never shown as live | Verified | 18 + 38/45 | Freshness gates + release check | Yes — NON-WAIVABLE |

Full itemization: [`GAP_INVENTORY.md`](GAP_INVENTORY.md).

---

## 7. Market rollout matrix

| Market | Required merchant paths | Currency / localization | Certification sprint | Launch gate |
|--------|-------------------------|-------------------------|----------------------|-------------|
| Philippines | ≥1 real legally usable connector/feed/affiliate path | PHP + EN; MarketContext | 32 | EXT-01 provisioned; staging+prod validation; coverage row published |
| United States | ≥1 real path | USD + EN | 33 | EXT-02 + same |
| Singapore | ≥1 real path | SGD + EN | 34 | EXT-03 + same |
| United Kingdom | ≥1 real path | GBP + EN | 35 | EXT-04 + same |
| Canada | ≥1 real path | CAD + EN; FR-CA decision disclosed | 36 (+37 decision) | EXT-05 + same |
| Other countries | None required | Unsupported disclosure only | 37 / 38 | Must not show fixture as live |

**Launch-date protection — market scope (locked):**

- Sprint 45 does **not** require all five planned markets if some provider approvals remain unavailable.
- Supported-market claims are dynamic and evidence-based.
- If a market fails certification: remove/delay that market; do not fake coverage; do not necessarily delay the entire launch.
- At least one genuinely useful certified market must exist for public shopping launch.
- Document the actual supported-market list at Sprint 44/45.
- Fixtures and mock providers cannot certify a market.
- Empty named-market list is allowed only with non-shopping positioning (not Global Public Beta as defined here).

---

## 8. External dependency matrix (summary)

Statuses below are copied from the register as of this lock. Do not invent later progress.

| Dependency | Owner | Target sprint | Current status | Sept 30 risk | Fallback | Launch impact |
|------------|-------|---------------|----------------|--------------|----------|---------------|
| Merchant approvals PH/US/SG/UK/CA | Marketplace + legal | 32–36 | `not_started` | **RED** for naming each market; **RED** for shopping launch until ≥1 market is certified | Remove uncertified markets | Market-specific; ≥1 market NON-WAIVABLE |
| Transactional email + DNS auth | Identity + ops | 27 | EXT-08/09 `applied` (not provisioned) | **AMBER** | Invite-only / disable self-serve reset (demotes beta) | Launch / auth — NON-WAIVABLE for self-serve |
| Domain ownership | Ops | 41 | EXT-10 `approved` | **GREEN** for ownership | — | Prerequisite only |
| Public DNS / TLS | Ops | 41 | EXT-11/12 `not_started` | **AMBER** | Delay public hostname | Launch — NON-WAIVABLE |
| AWS production + secrets | Ops | 41 | Partial TF; EXT-14 `not_started` | **AMBER** | Delay production | Launch — NON-WAIVABLE |
| Legal review + published policies | Legal | 28 / 44 / 45 | EXT-19 `applied`; EXT-20/21 `not_started` | **AMBER** | Delay launch | Launch — NON-WAIVABLE |
| Support / privacy contacts | Ops / privacy | 28 / 39 | EXT-17/18 `provisioned` | **GREEN** for bootstrap reachability | Delay public launch if later lost | Support/legal publication still 28/45 |
| Analytics / consent tooling | Product | 39 | `not_started` | **AMBER** (learning) | Essential-only first-party | SCOPE-REDUCIBLE |
| Search Console | Product / SEO | 39 / 45 | `not_started` (EXT-29) | **AMBER** | Launch without ranking claims; still require noindex honesty | Indexability proof — private-route noindex is NON-WAIVABLE |
| FX provider | Marketplace | 37 | `not_started` | **AMBER** | No cross-currency compare | SCOPE-REDUCIBLE |
| Paging destination | Ops | 42 | `not_started` | **AMBER** | Delay prod launch | Launch — NON-WAIVABLE |
| AI production quota | AI/ops | 38 / 43 | unknown | **AMBER** | Deterministic fallback only | SCOPE-REDUCIBLE AI claims |
| Payments / app stores | — | — | `n_a_beta` | **GREEN** (out of scope) | Out of scope | None |

Full register (includes **Scope** and September-risk columns): [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md).

---

## 9. Global Public Beta exit criteria (Sprint 45 cannot close unless true)

Sprint 45 is the **final go/no-go verification** gate for each criterion. Documentation alone cannot satisfy runtime requirements. Each criterion has exactly one **primary owning sprint** for implementation/evidence production.

| ID | Exit criterion | Primary owning sprint | Final evidence | Sprint 45 decision |
|----|----------------|----------------------|----------------|--------------------|
| EC-01 | Current launch candidate successfully deployed to staging | 26 | Staging deploy evidence JSON + `/ready` READY for launch-candidate digest | Verify candidate still staging_ok; no-go if stale/unproven. SHA `79bd03f` proof does not automatically cover `ab23d29` or later. |
| EC-02 | Full user journey, including CC-01 Conversational Continuity, passes in staging | 29 | Staging E2E report covering register→search→canonical PiqScore/Recommendation→Ask PiqSavi→contextual follow-up/refinement→optional confirmed research→updated Results→redirect, plus account/privacy paths | Re-run CC-01 smoke on the frozen candidate; no-go on any failure, stale evidence, context drift, or mock-only live-research proof |
| EC-03 | Password recovery and email verification work through a real provider | 27 | Real-inbox delivery + confirm-route E2E artifacts | Verify still green on candidate; no-go if demo tokens usable |
| EC-04 | Terms, Privacy Policy, consent, deletion, and support are live | 28 | Live policy URLs + consent/deletion/export staging→prod proof; support contact published | Verify published + operable; no-go if any missing |
| EC-05 | Production environment is provisioned and isolated | 41 | Applied prod AWS evidence + isolation proof (staging cannot read prod secrets) | Confirm isolation still holds; no-go if missing |
| EC-06 | Production deploy and rollback workflows are validated | 41 | Prod deploy dry-run + rollback workflow evidence | Confirm rehearsed path exists; no-go if unrehearsed |
| EC-07 | Backup restore has been rehearsed | 42 | Restore drill report with measured RTO | Confirm report current; no-go if absent |
| EC-08 | Monitoring, dashboards, alerts, and paging are active | 42 | Dashboard links + alert config + page/ack ≤15m evidence | Confirm active paging destination; no-go if inactive |
| EC-09 | ≥1 real validated merchant path in every **named** supported market, with declared / evidence-backed / fail-closed-enforced merchant capability policy | Per named market: 32\|33\|34\|35\|36 *(platform contract: 31)* | Per-market certification report with real current-data response **and** capability-policy evidence map | Name only certified markets/modes; remove failed markets or providers |
| EC-10 | PH, US, SG, UK, and Canada named only when market gates pass | 44 | Approved coverage matrix listing only gated markets | Reject any ungated market name |
| EC-11 | Currency comparison fails closed when unsafe | 37 | Fail-closed FX/mixed-currency test + staging proof | Verify still enforced; no-go if unsafe compare possible |
| EC-12 | Unsupported markets receive honest disclosure | 37 | Unsupported-market UX/API disclosure evidence | Verify disclosure; no-go if fixtures appear as live |
| EC-13 | Organic ranking neutrality remains verified | 44 *(certifies Sprint 5/6/20 invariants)* | Neutrality CI green + integrity monitoring on | No-go on neutrality regression |
| EC-14 | Analytics and consent operate correctly | 39 | Consent-gated event proof + consent-state checks | Verify consent gate; no-go if non-essential fires pre-consent |
| EC-15 | Security HIGH and launch-blocking MEDIUM findings closed | 40 | Security closure package / risk-acceptances with expiry | No-go if open HIGH or blocking MEDIUM |
| EC-16 | Capacity evidence supports announced rollout size | 43 | Load/spike reports for announced gates | Cap announcement to demonstrated size; no-go if exceeded |
| EC-17 | Production launch rehearsal succeeds | 44 | Rehearsal evidence (deploy/smoke/rollback authority exercise) | No-go if rehearsal failed |
| EC-18 | Legal, security, and operations go/no-go approvals recorded | 44 | Signed approval records | No-go without all three |
| EC-19 | Public claims match validated coverage matrix | 44 | Approved claim sheet ↔ coverage matrix | Strip or rewrite mismatched claims |
| EC-20 | Rollback authority and incident ownership assigned | 45 | Named on-call + rollback decision authority for launch window | Launch-control ownership; no-go if unassigned |
| EC-21 | No fixture/simulated merchant data can appear as a live offer | 38 *(with Sprint 18 freshness invariants)* | Release verification script + freshness gate evidence | No-go on any fixture-as-live path |
| EC-22 | Final launch checklist, including signed CC-01 evidence, is approved | 45 | Signed Sprint 45 checklist artifact referencing the exact CC-01 evidence and immutable candidate digest | Launch-control ownership; no-go if CC-01 is absent, stale, incomplete, or from another candidate |
| EC-23 | A real shopper request creates an owner-bound schema-current canonical decision from live certified evidence | 38 *(capture/presentation: 29; routing: 31)* | Production-rehearsed path: search/request → live evidence → evaluated offers → canonical economics → PiqScore → Recommendation → snapshot → owner/session binding → UUID Results | No-go if only fixture-created UUIDs exist |
| EC-24 | Ask PiqSavi remains available after Recommendation on Results, Compare, and Why | 29 | Staging + rehearsal proof of persistent Ask on all three surfaces | No-go if Recommendation is treated as the end of the conversation |
| EC-25 | Public/private SEO separation is enforced | 29 *(rehearse 44; cutover 45; measure 39/46)* | robots/sitemap/canonical/noindex evidence; UUID Results/Compare/Why are non-indexable | No-go if personalized decision URLs are indexable |
| EC-26 | Destination changes that could materially change shipping/effective cost trigger server-side re-evaluation | 37 | Staging proof of server-side re-evaluation; no client-side fake repricing | No-go if UI invents new prices/Best Piq without a new/re-evaluated decision |
| EC-27 | Shoppers can report incorrect price, product fact, outdated offer, misleading evidence, or source issues | 39 | Staging/prod-prep feedback path to monitored support | No-go if no public report path exists |
| EC-28 | Guest work can continue after register/login without silently losing the active decision | 27 / 29 / 40 | Guest→account transition tests + staging proof | No-go if signup drops the decision when preservation is safely possible |
| EC-29 | Search/Ask, Save, and Watch remain semantically distinct | 29 *(Watch monitoring: 10/19/47)* | Product copy + UI states do not silently turn Save into Watch or promise notifications before monitoring exists | No-go on false monitoring/notification claims |
| EC-30 | Approved public pages are technically indexable; Search Console is connected; ranking is not promised | 45 *(foundation 29; measure 39; rehearse 44)* | robots/sitemap/canonicals correct; GSC connected; structured data valid where used | No-go if intended public pages cannot be crawled or private routes are included |

**Market note for EC-09:** When multiple markets are named, each named market’s certification sprint (32/33/34/35/36) is the primary owner for that market’s path. Sprint 31 owns the shared capability/policy contract and fail-closed harness; 32–36 populate provider-specific evidence. Sprint 44/45 verify and may remove markets or providers.

**EC-09 capability-policy invariant:** No merchant connector may be certified for production, or used to support a named shopping-market claim, unless its permitted affiliate, data-use, caching, transformation, comparison, attribution, and related capabilities are explicitly declared, evidence-backed, and fail-closed enforced. Unknown permissions do not enable production features. Provider approval alone does not imply blanket capability approval. Affiliate-only destinations cannot independently satisfy EC-09 current-data market naming.

### CC-01 — Conversational Continuity

**Parent criteria:** EC-02, EC-22, EC-23, EC-24

**Primary implementation/evidence owner:** Sprint 29

**Supporting owners:** Sprint 31, Sprint 37, Sprint 38, Sprint 39, Sprint 40, Sprint 43

**Rehearsal/integrity verifier:** Sprint 44

**Final go/no-go verifier:** Sprint 45

CC-01 passes only when one immutable staging candidate proves all of the following:

1. A guest search produces Results from the canonical PiqScore and Recommendation authority.
2. Ask PiqSavi opens from Results and binds to that exact server-owned decision context.
3. A contextual question answerable from captured evidence is answered from that evidence without unnecessary search or unproven execution claims.
4. A second follow-up retains the exact evaluated product set unless the user explicitly requests or approves new research.
5. Equivalent context binding and continuation work from Compare and Why This Is the Best Piq.
6. The mobile conversation sheet preserves the same context and passes keyboard, safe-area, focus, close/reopen, and accessibility verification.
7. Optional session Recommendation refinement operates over the same evaluated set while every canonical PiqScore remains byte-for-byte unchanged.
8. Session priorities remain separate from persistent account preferences unless explicitly saved by the user.
9. A question requiring evidence outside the current decision produces a research proposal and does not begin research before explicit confirmation.
10. Affirmative confirmation starts exactly one real, idempotent research execution.
11. Queued, running, partial, stale, completed, failed, and cancelled wording matches the actual execution record and contains no fabricated merchants, offers, prices, reviews, counts, freshness, or progress.
12. Completed research creates updated canonical Results, retains the conversation, and leaves Ask PiqSavi available for another question.
13. Guest ownership, expiry, deletion, logout, shared-device isolation, restart/multi-worker continuity, and guest→authenticated transition pass access-control and privacy regressions.
14. Affiliate-neutrality, canonical-authority, claims, provenance, integrity, visual-manifest, and context-drift regressions pass.

**EC-02 rule:** EC-02 cannot pass unless CC-01 passes on the same frozen candidate used for the full staging journey.

**EC-22 rule:** The signed final launch checklist must attach the CC-01 evidence package, candidate commit, immutable image digest, execution references, test report, visual-manifest verification, and Sprint 44 rehearsal approval.

**No-go conditions:** Public launch is blocked if CC-01 is missing, incomplete, stale, produced from another candidate, satisfied only with mocks where live research is claimed, or shows context drift, unauthorized context access, canonical PiqScore mutation, fabricated execution, affiliate influence, or failure on Results, Compare, Why This Is the Best Piq, or mobile.

### 9.1 Intent sufficiency — locked product rule

> Ask only when missing information could materially change the Recommendation. Otherwise, research first.

Do not introduce long onboarding/questionnaire friction.

### 9.2 Ask PiqSavi — locked product requirement

Ask PiqSavi remains available **after Recommendation** on:

- Results
- Compare
- Why This Is the Best Piq for You

Recommendation is not the end of the shopping conversation.

Supported conceptual flow:

Search / Ask
→ research
→ Recommendation
→ Results
→ Ask follow-up
→ explain evidence
→ refine session priorities
→ optionally propose new research
→ explicit confirmation
→ future research
→ updated decision
→ conversation continues

### 9.3 Search / Save / Watch distinction

| Action | Meaning |
|--------|---------|
| **Search / Ask** | Research / decision action |
| **Save** | Preserve a buying decision/context for later |
| **Watch** | Explicitly subscribe to future monitoring **where that capability genuinely exists** |

Do not silently turn Save into Watch. Do not promise notifications before monitoring is operational. Certified background monitoring remains a later/post-beta capability unless separately proven.

### 9.4 End-to-end real research loop — launch-critical

User asks/searches
→ intent sufficient
→ research authorized
→ Sprint 31 router chooses certified/allowed providers
→ Sprints 32–36 provide market-certified sources
→ Sprint 37 applies market/destination context
→ Sprint 38 executes resilient live research
→ offers/evidence/provenance
→ canonical economics
→ PiqScore
→ Recommendation
→ canonical decision UUID
→ Results
→ Compare
→ Why
→ Ask PiqSavi remains available

This is a launch-critical end-to-end path. Sprint 29 must not pretend merchant research exists before Sprints 31–38 dependencies are satisfied.

`SHOPPING_RESEARCH_EXECUTION_MODE=live` may not be production-enabled unless:

1. at least one relevant certified real connector exists for the requested supported market, and
2. truthful partial-failure/execution-trace handling is operational.

Mock remains non-production only.

---

## 10. Evidence maturity matrix (program view)

| Capability | Implemented | CI tested | Staging proven | Production rehearsed | Launch approved |
|------------|:-----------:|:---------:|:--------------:|:--------------------:|:---------------:|
| Auth register/login/logout | Yes | Yes | Yes (`79bd03f` Sprint 26 tech evidence; Sprint 26 open for EXT) | Pending (41/45) | Pending (44) |
| Password reset / email verify | Partial | Partial | Pending (27) | Pending (41) | Pending (44) |
| Privacy/deletion/legal | No | No | Pending (28) | Pending (45) | Pending (44) |
| Consumer decision web UI (Product Foundation) | Yes (merged) | Yes (merged suite) | Pending (29 staging journey on later candidate) | Pending (45) | Pending (44) |
| Conversational Continuity / Ask PiqSavi | Partial (29.0–29.4C merged) | Partial | Pending (29; support 31/37/38/39/40/43) | Pending (44/45) | Pending (45 via CC-01) |
| Canonical snapshots / economics / presentation contract | Yes (merged through schema 1.2) | Yes | Pending on launch candidate | Pending (45) | Pending (44) |
| Live owner-bound decision creation | No | No | Pending (29/31/38) | Pending (44/45) | Pending (45) |
| DealScore / Recommendation | Yes | Yes | Yes (26 tech evidence; mocked-data disclosure observed) | Pending (45) | Certify (44) |
| Merchant platform unified | Partial (router/provider contract merged; 4/18 dual-run documented; Sprint 31 owner-closed) | Partial | Pending (32–36 real path) | Pending (45) | Pending (44) |
| PH/US/SG/UK/CA real paths | No | No | Pending (32–36) | Pending (45) | Per-market (44/45) |
| MarketContext / FX / destination re-eval | No | Partial fail-closed | Pending (37) | Pending (45) | Pending (44) |
| Connector reliability / live research | Partial | Partial | Pending (38) | Pending (45) | Pending (44) |
| Product analytics / report-incorrect | No | No | Pending (39) | Pending (45) | Pending (44) |
| SEO foundation / private noindex | Partial metadata | Partial | Pending (29/39/44) | Pending (45) | Pending (45) |
| Security hardening package | Partial | Partial | Pending (40) | Pending (44) | Pending (44) |
| Staging deploy/rollback arch | Yes | Yes | Yes (`79bd03f` staging_ok; see Sprint 26 evidence) | N/A | — |
| Production deploy/rollback | No | No | N/A | Pending (41/44) | Pending (44) |
| Backup restore / paging | No | No | Pending (42) | Pending (42/44) | Pending (44) |
| Capacity evidence | No | No | Pending (43) | Pending (43) | Pending (44) |
| Sprint 47 buying-action intelligence | No | No | N/A pre-launch | N/A pre-launch | POST-LAUNCH |

---

## 11. Public claim matrix

| Claim | Required evidence | Owning sprint | Approved wording (only after evidence) | Prohibited wording |
|-------|-------------------|---------------|----------------------------------------|--------------------|
| Globally accessible | Public DNS/TLS + prod `/ready` | 41 / 45 | “Available on the public web” | “Available worldwide” without legal review |
| Available worldwide | Legal review + geo policy | 28 / 44 | Qualified geo availability statement | Unqualified worldwide shopping |
| Searches stores worldwide | ≥1 real path in each named market | 32–36 / 44 | “Searches supported merchants in [list]” | “Searches stores worldwide” |
| Compares all major retailers | Never for beta | — | — | Any “all major retailers” |
| AI personal shopper | Assistant + fallback + disclosure | 13 / 44 | “AI-assisted shopping guidance (deterministic ranking)” | Unqualified “AI personal shopper” guaranteeing outcomes |
| Independent / unbiased recommendations | Neutrality tests + monitoring | 5/6/20/44 | “Organic ranking independent of affiliate commission” | Absolute “unbiased” without qualifier |
| Finds the best / smartest deal | Incomplete coverage | — | — | “Best” / “smartest” deal as a guarantee |
| Detects scams | No product evidence | — | — | Any scam-detection claim |
| Real-time / always up to date | Freshness SLOs unmet | 38 / 44 | “Prices as of [timestamp]; may be stale” | “Real-time” / “always up to date” |
| Supports PH, US, SG, UK, Canada | Each market gate pass | 32–36 / 44 / 45 | “Supported shopping markets: [passed only]” | Naming markets without gates |
| Globally reachable ≠ supported markets | Coverage matrix published | 44 / 45 | Explicit distinction statement | Conflating access with coverage |
| SEO / ranking | Technical indexability only | 45 / 46 | “Public pages may be discovered by search engines” | Ranking-position promises |
| Wait for a future sale / 9.9 | Sprint 47 evidence | 47 | None before 47 | Campaign-aware Wait before certified promotion evidence |
| We are watching this for you | Certified monitor | 47 / 10 / 19 | None before monitoring exists | Silent Save→Watch; notification promises |

---

## 12. Critical-path matrix

| Critical item | Predecessor | Earliest sprint | External risk | Fallback |
|---------------|-------------|-----------------|---------------|----------|
| Staging current-main | 25b.* workflows | 26 | Host/bootstrap drift | Fix host; re-run deploy |
| Real email | EXT-08/09 | 27 | Provider/DNS delay | Invite-only demotion |
| Legal package | Counsel | 28 → 44 | Review latency | Delay launch |
| Consumer decision experience + Conversational Continuity | API stable (24); approved Product Foundation manifest | 29 | Scope creep or parallel Results authority | Preserve canonical Results authority; hold launch if CC-01 is incomplete |
| Platform unify + min reliability contracts | Lock review | 31 | Dual-run complexity | Documented dual-run with hard deadline |
| First real market | EXT-01…05 + **31 contracts** | 32–36 | Provider denial | Remove failed markets; require ≥1 certified market |
| Remaining markets | EXT-02…05 + 31 | 33–36 (parallel OK) | Staggered denials | Launch with subset |
| MarketContext/FX + destination re-eval | 31 + 29 UI shell | 37 | FX vendor | Fail-closed no compare; no client-side fake prices |
| Cross-connector hardening + live mode | ≥1 certified market preferred | 38 | Incomplete chaos coverage | Hold live shopping launch |
| Prod path | Staging green | 41 | AWS/DNS/TLS | Delay public |
| Ops evidence | 41 | 42 | Paging vendor | Delay public |
| Capacity | 41 staging/prod-like | 43 | Fail load tests | Reduce announced size |
| Go/no-go | 27–43 done subset | 44 | Legal/security hold | No-go |
| Public launch | 44 approvals | 45 | Any Sev1 / non-waivable blocker | Rollback or no-go |
| Stabilization | 45 | 46 | Incident load | Extend window |
| Buying-action intelligence | 46 program close | 47 | Evidence/legal rights | Remain post-beta |

**Dependency classes:** Sprint 31 reliability contracts **and** contractual capability/policy model = **strict predecessor** of 32–36. Market certifications after 31 = **parallelizable**. Sprint 38 = **soft dependency** on having at least one live path to harden, and a **final launch gate** for live research. External approvals = **external gates** (approval ≠ blanket capability enablement).

---

## 13. Parallel workstreams

| Stream | Sprints | Can overlap with |
|--------|---------|------------------|
| External applications & legal drafting | 26→44 | All engineering after 26 bootstrap |
| Identity/email | 27 | UI design spikes |
| Privacy/deletion | 28 | UI implementation (29) after API contracts |
| Consumer decision experience | 29 | Merchant platform design (31) |
| Merchant unification + min reliability contracts | 31 | Market EXT follow-ups |
| Market certifications | 32–36 | **Parallel after 31** if staffing allows and shared platform stable |
| MarketContext/FX + destination re-eval | 37 | After 31; can parallel late market certs carefully |
| Cross-connector reliability / live research | 38 | After/during certified connectors; before production launch |
| Analytics/support/SEO measurement | 39 | Security (40) |
| Security | 40 | Prod TF prep |
| Production infra | 41 | Ops tooling prep |
| Ops/DR | 42 | Capacity harness build |
| Capacity | 43 | Claims drafting |
| Approvals/rehearsal | 44 | Freeze feature work |
| Launch | 45 | War-room only |
| Stabilize | 46 | Learning reviews |
| Post-beta intelligence | 47 | After 46; must not steal 45 capacity |

---

## 14. Commitments preserved vs superseded

### Preserved

- Architecture Lock ownership for Sprints 1–25 domains and invariants
- Staging deploy/rollback architecture and evidence model
- Immutable digest promotion authority
- DealScore / Recommendation / affiliate post-rank / sponsored separation
- Fixture-never-as-live freshness rules
- Sprint identities 1–40 (names/history)
- Sprint 30 closed-audit identity
- M30 evidence *content* (still required) — relocated to Sprints 26 / 41 / 42 / 44 / 45 as applicable
- FastAPI HTML / shared CSS / vanilla-JS consumer architecture unless later independently approved
- Ask PiqSavi after Recommendation
- Intent-sufficiency rule

### Superseded / reclassified

| Prior statement | Disposition |
|-----------------|-------------|
| Hard endpoint Sprint 40 | **Superseded** → launch Sprint 45; stabilize Sprint 46; numbered stop Sprint 47 |
| Sprint 30 public launch target | **Reclassified** → readiness audit; launch not achieved |
| “Launch by Sprint 40” change-control goal | **Superseded** → launch by Sprint 45 no later than 2026-09-30; stabilize Sprint 46 |
| Roadmap numbered stop Sprint 46 | **Superseded** → Sprint 46 remains post-launch stabilization; numbered stop is now Sprint 47 |
| Sprint 29 = UI/accessibility only | **Superseded** → Production Consumer Decision Experience & Conversational Continuity |
| Mandatory React / Next.js / Vite / TypeScript / SPA / Node production build | **Reconciled** — not required for production consumer frontend |
| Deferred bucket “Sprints 24–40” real connectors/email/UI | **Superseded** by explicit sprint ownership 27–39 |
| Simulated connectors allowed at M30 if documented | **Still true for infra rehearsal**; **not sufficient** for Global Public Beta shopping markets |
| All five planned markets required for Sprint 45 | **Superseded** → subset allowed; ≥1 certified useful market required for shopping launch |

---

## 15. Acceptance gates (cross-cutting)

### Market gate (per named market)

- Real provider response in staging and production (or production-equivalent rehearsal)
- Legal/terms approval recorded
- Provenance + freshness timestamps present
- Kill switch tested
- Coverage matrix row published
- No fixture path labeled live
- Capability policy declared, evidence-backed, fail-closed enforced

### Security gate (before 45)

- All HIGH closed
- Launch-blocking MEDIUM closed or written risk-accepted with expiry
- Scanning jobs green on launch candidate

### Claims gate (44)

- Every public sentence maps to evidence maturity ≥ Staging proven (prod claims need Production rehearsed/proven)

### Launch gate (45)

- Exit criteria §9
- Owner target: no later than September 30, 2026
- Date pressure may reduce scope-reducible items only

---

## 16. Post-launch stabilization (Sprint 46)

Sprint 46 **cannot** postpone unresolved Sprint 45 launch blockers. It owns stabilization findings that arise **after** an approved launch only.

- Launch-monitoring handoff from Sprint 45 + incident ownership handoff
- Sev 0/1/2 burn-down; production error-budget review
- Product regressions; UX blockers; Recommendation trust problems
- Connector freshness/provenance + merchant-data quality review
- Supported-market and merchant coverage review
- Rollback-readiness reaffirmation (evidence + authority still valid)
- Support-volume and support-response review
- Privacy deletion/export post-launch verification; analytics consent-state review
- Capacity re-check against actual beta traffic
- Public-claims drift review
- SEO/indexing observation: crawl errors, indexing failures, structured-data errors, unexpected private-route discovery, freshness/claim problems
- Post-beta backlog classification, including Sprint 47
- Explicit program-close report for the launch/stabilization window

---

## 17. Sprint 47 — Offer Timing, Promotions & Buying Action Intelligence

**Status:** Planned — POST-BETA  
**Gap ID:** P2-OT-01  
**Beta blocker:** No  
**Does not block Sprint 45.**

Preserve the already-approved conceptual phases:

| Phase | Name | Outcome |
|-------|------|---------|
| 47.0 | Contracts + Architecture Lock addendum | Additive contracts only; no protected-engine rewrite |
| 47.1 | Promotion and Voucher Evidence | Marketplace-observed promotion/voucher evidence with fail-closed rights |
| 47.2 | Effective Purchase Price | Verified vs conditional/potential checkout stack |
| 47.3 | Certified Historical Price Evidence | History usable as Wait evidence only when certified |
| 47.4 | Buying Action Layer | Buy Now / Wait / Watch / Consider Alternative |
| 47.5 | Watch Integration | Monitoring only where genuinely certified |

### Architecture lock (layers)

| Layer | Authority | Rule |
|-------|-----------|------|
| 1 | Canonical PiqScore | Objective strength of the evaluated opportunity |
| 2 | Canonical Recommendation | Organic Buy / Wait / Consider / Avoid from current evaluated facts |
| 3 | Buying Action | Buy Now / Wait / Watch / Consider Alternative — **does not replace** canonical Recommendation |
| 4 | Session refinement / personalization | May change session Best Piq / Buying Action; never rewrite Layer 1 |
| 5 | Affiliate economics | Downstream of all of the above |

Do not reinterpret current canonical `Wait` as guaranteed future promotion timing. Campaign-aware Wait requires evidence.

Detail: [`sprints/SPRINT_47_OFFER_TIMING_PROMOTIONS_BUYING_ACTION.md`](sprints/SPRINT_47_OFFER_TIMING_PROMOTIONS_BUYING_ACTION.md).

---

## 18. Launch P0 coverage matrix

Intended to prevent any launch-critical area from falling between sprints.

| # | Launch-critical area | Owning sprint(s) | Current status | Evidence required | Launch blocking? | Fallback / demotion |
|---|----------------------|------------------|----------------|-------------------|------------------|---------------------|
| 1 | Consumer Search/Ask | 29 (surfaces); 4/31/38 (research) | Surfaces merged; live research planned | Staging Search/Ask journey | Yes — NON-WAIVABLE | None for shopping launch |
| 2 | Intent sufficiency | 29 | Planned/partial | “Ask only when missing info could change Recommendation” proven | Yes — NON-WAIVABLE | Do not add questionnaire friction |
| 3 | Live research authorization | 29.4C / 38 | Planned | Proposal → explicit confirmation → one execution | Yes — NON-WAIVABLE | No silent research |
| 4 | Certified research | 31 + 32–36 + 38 | Planned; EXT RED | ≥1 certified real path | Yes — NON-WAIVABLE | Remove uncertified markets |
| 5 | Research trace/provenance | 31 / 38 | Planned | Attempted/succeeded/failed/timed-out sources + offer counts | Yes — NON-WAIVABLE | Honest partial failure |
| 6 | Canonical decision creation | 29 / 31 / 38 | Presentation merged; live creation missing | Live request → schema-current owner-bound UUID | Yes — NON-WAIVABLE | Fixtures insufficient |
| 7 | PiqScore | 5 / 29 / 44 | Implemented/verified | Neutrality + snapshot integrity | Yes — NON-WAIVABLE | None |
| 8 | Recommendation | 6 / 29 / 44 | Implemented/verified | Organic decision + disclosure | Yes — NON-WAIVABLE | None |
| 9 | Canonical economics | 29 (capture); 37 (market honesty) | Schema 1.1 merged | Listing/discount/voucher/shipping/tax/import/unknowns | Yes — NON-WAIVABLE for honesty | Unknowns remain unknowns |
| 10 | Results | 29 | Merged Product Foundation | Staging Results on UUID | Yes — NON-WAIVABLE | None |
| 11 | Compare | 29 | Merged | Staging Compare on UUID | Yes — NON-WAIVABLE | None |
| 12 | Why | 29 | Merged | Staging Why on UUID | Yes — NON-WAIVABLE | None |
| 13 | Persistent Ask PiqSavi | 29 | Merged surfaces; 29.4A merged | Ask on Results/Compare/Why after Recommendation | Yes — NON-WAIVABLE | None |
| 14 | Session Recommendation refinement | 29.4B | Merged | Overlay changes session Best Piq only | Soft Yes for CC-01 item 7 | Hold CC-01 if incomplete; do not fake it |
| 15 | Research proposal/confirmation | 29.4C / 38 | Merged proposal/confirmation; live execution not implemented | Proposal UI + confirmation; no auto-exec | Yes — NON-WAIVABLE | Do not imply research runs automatically |
| 16 | Location/market context | 37 | Planned | Destination re-eval + unsupported-market honesty | Yes — NON-WAIVABLE | Fail closed; no client fake prices |
| 17 | Merchant/source coverage | 32–36 / 44 | Externally blocked | Coverage matrix of certified sources only | Yes to name a market; ≥1 market NON-WAIVABLE | Remove uncertified markets/sources |
| 18 | Account/auth | 17 / 27 / 29 | Partial | Register/login/session | Yes — NON-WAIVABLE | Invite-only demotes beta |
| 19 | Transactional email | 27 | EXT applied, not provisioned | Real inbox reset/verify | Yes — NON-WAIVABLE for self-serve | Invite-only |
| 20 | Guest→account continuity | 27 / 29 / 40 | Planned/partial | Preserve decision on signup when safe | Yes — NON-WAIVABLE | Do not silently drop the decision |
| 21 | Privacy/consent | 28 / 39 | Planned | Consent persistence | Yes — NON-WAIVABLE | Delay launch |
| 22 | Deletion/export | 28 | Planned | Staging E2E | Yes — NON-WAIVABLE | Delay launch |
| 23 | Legal policies | 28 / 44 / 45 | Counsel applied; policies unpublished | Live ToS/Privacy/cookie policy | Yes — NON-WAIVABLE | Delay launch |
| 24 | Save | 29 / 10 | Planned/partial | Preserve decision/context | Soft Yes | Ship Save without Watch promises |
| 25 | Watch semantics | 10 / 19 / 47 | Primitives exist; monitoring uncertified | Honest Watch vs Save | Yes for honesty — NON-WAIVABLE | Hide/demote Watch until monitoring exists |
| 26 | Report Incorrect Information | 39 | Planned | Public report path | Yes — NON-WAIVABLE | Delay launch |
| 27 | Outbound offer handoff | 20 / 29 / 44 | Partial | Safe redirect + disclosure | Yes — NON-WAIVABLE | Omit View offer if no captured URL |
| 28 | Affiliate neutrality/disclosure | 20 / 28 / 40 / 44 | Engine verified; legal pending | Neutrality tests + public disclosure | Yes — NON-WAIVABLE | Organic links without monetization claims |
| 29 | Analytics | 39 | Planned | Consent-gated events listed in Sprint 39 | Soft Yes | Essential-only |
| 30 | Feedback/support | 39 / 28 | Inbox provisioned; product path pending | Support contact + in-product path | Yes — NON-WAIVABLE | Delay if contact unpublished |
| 31 | SEO foundation | 29 | Planned/partial | Semantic HTML, metadata, robots, sitemap, JSON-LD infra | Yes for technical honesty | No mass thin pages |
| 32 | Private-route noindex protection | 29 / 40 / 44 / 45 | Planned | UUID Results/Compare/Why non-indexable | Yes — NON-WAIVABLE | Delay launch if leaked |
| 33 | Search Console/indexing | 39 / 44 / 45 | Not started | GSC connected; intended pages crawlable | Soft Yes for GSC; noindex honesty NON-WAIVABLE | Launch without ranking claims |
| 34 | Security | 40 | Planned/partial | HIGH + blocking MEDIUM closed | Yes — NON-WAIVABLE | Delay launch |
| 35 | Production infrastructure | 41 | Partial TF | Isolated prod AWS/DB/secrets/IAM/DNS/TLS | Yes — NON-WAIVABLE | Delay launch |
| 36 | Monitoring/paging | 42 | Planned | Active paging | Yes — NON-WAIVABLE | Delay launch |
| 37 | Backup/restore/DR | 42 | Planned | Restore drill | Yes — NON-WAIVABLE | Delay launch |
| 38 | Capacity/performance | 43 | Planned | Load evidence | Yes for announced size | Reduce announced size |
| 39 | Accessibility | 29 | Planned/partial | A11y baseline | Yes — NON-WAIVABLE | Delay public UI |
| 40 | Mobile/browser QA | 29 / 44 | Planned/partial | Browser matrix + mobile journey | Yes — NON-WAIVABLE | Delay public UI |
| 41 | Production rehearsal | 44 | Planned | End-to-end prod rehearsal | Yes — NON-WAIVABLE | No-go |
| 42 | Claims approval | 44 | Planned | Signed claim matrix | Yes — NON-WAIVABLE | Strip claims |
| 43 | Launch go/no-go | 45 | Planned | EC-01…EC-30 + checklist | Yes — NON-WAIVABLE | No-go or rollback |
| 44 | Post-launch stabilization | 46 | Planned | Stability report | Program close | Extend window; not a 45 substitute |

---

## 19. SEPTEMBER 30, 2026 LAUNCH CRITICAL PATH

Shortest truthful path from current state to Sprint 45. Calendar durations are **not fabricated**; repository evidence does not support day-level estimates.

### Current state (reconciled 2026-09-02)

Historical 2026-08-25 snapshot after PR #96: Sprint 31 closure evidence implemented and pending owner close; Sprint 32 not started. That snapshot is not current operational status.

- `main` engineering baseline: `d890df24559325bb8d1289b6c2a01b590c9e50ab` (includes later Sprint 26 counsel-clearance merge). Prior approved merged-suite SHA `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0` remains ancestor evidence (**2977 passed / 0 failed / 0 skipped / 168 warnings** on that SHA).
- Sprint 29 Product Foundation + 29.0–29.4C + economics + UUID presentation + schema 1.2 + research authorization handoff **merged**
- Sprint 31 research execution router / provider contract **merged** and **formally owner-closed**. Historical gate satisfied.
- Sprint 32 **in progress** (foundation slices 32.1–32.5). Sprint 32 is **not complete**. Production certified research providers remain **zero**. Live research execution remains unimplemented. No PH merchant is production-certified.
- Sprint 26 **open** (technical proof is `79bd03f`, not the current baseline). Owner-observed Shopee dashboard / Affiliate Open API facts are not official Sprint 32 evidence until separately reconciled on `main`.
- EXT merchant applications **not started** (EXT-01 / EXT-06 / EXT-07 remain unresolved)
- No production AWS apply; no live certified market

### Strict gates (cannot be skipped)

1. **Finish remaining Sprint 29 launch proof** — CC-01 staging E2E on the frozen candidate; SEO technical foundation; persistent Ask lock. 29.4B and 29.4C contracts are merged; live research remains later.
2. **Sprint 26 external bootstrap remaining** — EXT-01…05 applications; Sprint 26 stays open until register evidence exists. Later SHAs still need their own staging proof before launch (EC-01).
3. **Sprint 27** — real transactional email, sender auth, verify/reset/email-change, token lifecycle, enumeration-safe errors, session rotation, staging E2E, production cutover readiness.
4. **Sprint 28** — ToS/Privacy/cookie/consent/deletion/export/retention/PII/vendor register/contacts/age notices; search-index privacy; counsel package. Final publication/approval in 44/45.
5. **Sprint 31 owner close** — satisfied. Router/provider contract is merged; unification ADR, dual-run disposition date (2026-09-15), and onboarding runbook are recorded. Sprint 32 has started and remains blocked on external merchant certification, not on Sprint 31.
6. **Minimum viable market certification (32–36)** — at least one legally usable real source path with current-data + capability-policy + credential approval. Others may be omitted. Sprint 32 foundation is implemented; the PH real path is still missing.
7. **Sprint 37** — market/currency/FX/locale/destination honesty + server-side destination re-evaluation.
8. **Sprint 38** — resilient live research + execution trace + live-mode gate + fixture-never-as-live.
9. **Sprint 41** — isolated production AWS/DB/secrets/IAM/deploy/rollback/DNS/TLS/hostname. IaC is not proof.
10. **Sprint 42** — logs/metrics/dashboards/alerts/paging/backup/restore/IR/runbooks/kill switches.
11. **Sprint 44** — claims vs actual capability; legal/security/ops approvals; production rehearsal including SEO/indexability.
12. **Sprint 45** — final go/no-go against EC-01…EC-30 no later than 2026-09-30.

### Parallelizable after prerequisites

| Work | May overlap |
|------|-------------|
| 29 remaining (after 27/28 API hooks) | 31 design |
| 32–36 | Parallel after 31 |
| 37 | After 31; careful overlap with late market certs |
| 39 analytics/SEO measurement | 40 security |
| 40 | 41 TF prep |
| 42 tooling | After 41 shape is known |
| 43 harness | After 41 staging/prod-like exists |

### External risk on this path

See §8 and the register. The items that can miss September 30 unless resolved or scope-reduced are currently **RED/AMBER**: merchant approvals (RED), email DNS/auth (AMBER), counsel written approval + policy publication (AMBER), production DNS/TLS/AWS/secrets (AMBER), paging (AMBER), Search Console (AMBER), FX (AMBER, reducible), AI quota (AMBER, reducible).

### Scope-reducible if the date is threatened

- Individual markets among PH/US/SG/UK/CA
- Optional providers/sources
- Optional categories
- Cross-currency compare
- Non-essential analytics
- Ranking/SEO acquisition outcomes
- Sprint 47 entirely
- Advanced Watch monitoring promises

Do not scope-reduce: truthfulness, privacy, security, legal publication, production isolation, monitoring/paging, rehearsal, private-route noindex, fixture-never-as-live, or the requirement for at least one useful certified market.

---

## 20. Document map

| Document | Role |
|----------|------|
| **This file** | Sole master roadmap authority |
| [`PIQSAVI_PUBLIC_BRAND_POLICY.md`](PIQSAVI_PUBLIC_BRAND_POLICY.md) | Locked PiqSavi public-brand authority (DealBrain internal codename) |
| [`GAP_INVENTORY.md`](GAP_INVENTORY.md) | Phase 1 complete inventory + 2026-08-24 reconciliation addendum |
| [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) | External dependency register |
| [`SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md`](SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md) | Persisted Sprint 30 audit summary |
| [`evidence/`](evidence/) | Packaged sprint evidence (Sprint 26 current-main staging proof + bootstrap checklist + completion draft) |
| [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) | Sprint 26 technical staging proof (Sprint 26 still open) |
| [`evidence/PIQSAVI_CONVERSATIONAL_CONTINUITY_PRODUCT_FOUNDATION_MANIFEST.md`](evidence/PIQSAVI_CONVERSATIONAL_CONTINUITY_PRODUCT_FOUNDATION_MANIFEST.md) | Owner-approved Product Foundation artwork authority and immutable checksum manifest |
| [`sprints/`](sprints/) | Per-sprint definitions 26–47 |
| [`../architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md) | Domain ownership lock (updated cross-link) |
| [`../architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md`](../architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md) | Infra contract; M30 matrix still evidential |
| [`../LAUNCH_READINESS.md`](../LAUNCH_READINESS.md) | Probe/readiness semantics |
| [`../LAUNCH_CHECKLIST.md`](../LAUNCH_CHECKLIST.md) | Rehearsal checklist (extended by Sprint 45) |

---

## 21. P0/P1 coverage confirmation

| Item | Owner | Covered? |
|------|-------|----------|
| P0-1 Live merchants | 32–36 (one primary market sprint per named market); ≥1 market required | Yes |
| P0-2 Production path | 41 | Yes |
| P0-3 M30 ops evidence | 42 | Yes |
| P0-4 Legal/privacy | 28 | Yes |
| P0-5 Email/reset | 27 | Yes |
| P0-6 Current-main staging | 26 (tech evidence packaged for `79bd03f`; EXT bootstrap pending; later candidates re-prove) | Yes |
| P1-1A Registry/router unify | 31 | Yes |
| P1-1B Unsupported-market behavior | 37 | Yes |
| P1-2 Shipping-cost honesty | 37 (44 verifies wording only) | Yes |
| P1-3 Scanning | 40 | Yes |
| P1-4 Analytics/feedback | 39 | Yes |
| P1-5 Lockout/distributed limits | 40 | Yes |
| P1-6 Consumer decision experience | 29 | Yes |
| P1-7 Staging promote discipline | 26 tech proven for `79bd03f` ([evidence](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); 45 final verification on frozen candidate | Yes |
| P2-OT-01 Offer timing / buying action | 47 | Yes — POST-LAUNCH |

---

**End of master roadmap.**
Documentation-only change. No implementation, infrastructure, or workflow mutation is authorized by this document alone.
