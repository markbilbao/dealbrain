# DealBrain — Global Public Beta Master Roadmap

**Status:** Authoritative master roadmap (documentation only)
**Branch:** `roadmap/global-public-beta-expansion`
**Base HEAD:** `fd25cc927236807ae1fe412fa0c4eac2429fbc50`
**Supersedes:** Sprint 40 hard endpoint; Sprint 30 “public launch” target as launch achievement
**Preserves:** Sprint identities 1–40 as historical; Architecture Lock domain ownership for Sprints 1–25
**Companion docs:** [`GAP_INVENTORY.md`](GAP_INVENTORY.md) · [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) · [`sprints/`](sprints/) · [`evidence/`](evidence/)
**Sprint 30 audit:** [`SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md`](SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md) — NOT READY (3/10)
**Sprint 26 technical evidence:** [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) — current-main staging proof verified; Sprint 26 remains open for external bootstrap

---

## 0. Authority and change control

1. This document is the **sole authoritative Global Public Beta roadmap**.
2. Sprint definitions under `docs/roadmap/sprints/` are normative detail owned by this master; they must not conflict with it.
3. `docs/architecture/ARCHITECTURE_LOCK.md` remains the domain-ownership lock; this roadmap **extends** launch sequencing and does not silently redistribute DealScore, Recommendation, affiliate, or merchant neutrality ownership.
4. Future roadmap additions require: gap ID, single owning sprint, acceptance evidence, beta-blocker classification, and an Architecture Lock review if ownership/invariants change.
5. Do not claim incomplete work complete. Do not mark connectors complete without real provider evidence. Do not mark production complete from Terraform alone.

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
| New endpoint | **Sprint 46** — Post-launch stabilization closes the Global Public Beta program |
| Added sprints beyond 40 | **6** (Sprints 41–46) |
| Newly scoped historical slots | Sprints **26–29** and **31–40** (were undefined or underspecified); Sprint **30** reclassified |
| Smallest realistic extension | Justified by five market certifications, legal/privacy, consumer UI, production ops evidence, capacity, and launch control as separate domains |

**Default execution order after this roadmap lands:**
`26 → 27 → 28 → 29 → 31 → (32∥33∥34∥35∥36) → 37 → 38 → 39 → 40 → 41 → 42 → 43 → 44 → 45 → 46`

**Reliability sequencing (non-negotiable):**
- Sprint **31** delivers shared minimum connector reliability contracts (strict predecessor of 32–36).
- Market certifications **32–36** may run in parallel after Sprint 31 and must validate those minima on real paths.
- Sprint **38** hardens and consolidates cross-connector production reliability; it is **not** the first appearance of basic timeout/retry/failure handling.

(Sprint 30 is a closed audit identity; do not re-open it as an implementation sprint.)

---

## 2. Global Public Beta definition

Global Public Beta means **all** of the following:

1. Public web access is available internationally.
2. Users can register, authenticate, recover accounts, manage privacy choices, and delete their accounts.
3. DealBrain clearly distinguishes: globally reachable service; supported shopping markets; supported merchants; delivery destinations; display currencies.
4. Initial named live-shopping markets are **Philippines, United States, Singapore, United Kingdom, Canada** — each named only when its market gate passes.
5. Each named supported market has at least one real, legally usable, operationally validated merchant-data path.
6. Unsupported markets receive explicit coverage disclosure and are never presented with fixture data as live prices.
7. The service has production deployment, rollback, monitoring, backup, incident-response, and capacity evidence.
8. Public claims are limited to proven capabilities.

Global Public Beta does **not** mean: every retailer worldwide; complete merchant coverage in every country; worldwide shipping from every merchant; always-current prices; guaranteed lowest price; automatic scam detection unless separately proven.

---

## 3. Historical sprint identities (1–40) — preserved

| Sprint | Historical identity | Global Beta posture |
|--------|---------------------|---------------------|
| 1–3 | Product identity / registry / matching | Preserve |
| 4 | Marketplace search / intelligence | Preserve; unify via 31; real data via 32–36 |
| 5 | DealScore | Preserve; certify |
| 6 | Recommendation decisions | Preserve; certify |
| 7–16 | Price history, collection, watchlists, reviews, assistant, community, KG, personal AI | Preserve |
| 17 | Consumer users / auth / sessions / profiles | Preserve; complete via 27–28 |
| 18 | Current marketplace offers / sync / freshness | Preserve; unify via 31; harden via 38 |
| 19–21 | Alerts, affiliate, merchant orgs | Preserve neutrality |
| 22 | Launch infrastructure / readiness | Preserve probes |
| 23 | Production persistence adapters | Preserve |
| 24 | API contracts | Preserve |
| 25 (+b.*) | Production infrastructure / staging deploy / rollback | Preserve architecture; complete remaining evidence via 26 / 41 / 42 |
| 26–29 | **Previously undefined** — now scoped (see §5) | Planned |
| 30 | **Reclassified:** Public Beta Readiness Audit (2026-08-06) — **not** a launched public shopping beta | Closed audit |
| 31–40 | **Previously underspecified deferred bucket** — now scoped (see §5) | Planned |
| 41–46 | **New** beyond superseded Sprint 40 hard endpoint | Planned |

### Sprint 30 reclassification (mandatory)

| Field | Prior claim | Accurate classification |
|-------|-------------|-------------------------|
| Name | Public launch (M30 target) | **Public Beta Readiness Audit** |
| Outcome | Implied launch readiness | **NOT READY** (3/10) |
| Completion | Not achieved as launch | Audit complete; launch incomplete |
| Effect on roadmap | Hard gate for “public launch” | Findings mapped to Sprints 26–46; does not authorize market naming |

Obsolete statements such as “hard launch target: Sprint 30 public launch” and “hard endpoint: Sprint 40” are **superseded for launch sequencing** but retained in historical docs with pointers here.

---

## 4. Phase structure (evidence-based)

| Phase | Sprints | Focus |
|-------|---------|-------|
| 1 Roadmap reconciliation & staging-current proof | 26 | Close P0-6; bootstrap external apps |
| 2 Consumer identity, email, privacy, legal | 27–28 | Close P0-4, P0-5 |
| 3 Production consumer UI & accessibility | 29 | Close P1-6 |
| 4 Merchant platform unification + min reliability contracts | 31 | Close P1-1A; reliability contract for 32–36 |
| 5 Real merchant integrations & market certification | 32–36 | Close P0-1 per market (may parallelize after 31) |
| 6 MarketContext, currency, shipping, localization | 37 | Close P1-1B + P1-2; multinational honesty |
| 7 Cross-connector reliability & honest degradation | 38 | Harden certified connectors before launch |
| 8 Analytics, feedback, support | 39 | Beta learning |
| 9 Security & abuse hardening | 40 | HIGH/MEDIUM closures |
| 10 Production infrastructure & operations | 41–42 | Close P0-2, P0-3 |
| 11 Performance, scaling, spike validation | 43 | Capacity evidence |
| 12 Launch claims, approvals, rehearsal | 44 | Go/no-go package |
| 13 Controlled Global Public Beta launch | 45 | Public cutover |
| 14 Post-launch stabilization | 46 | Endpoint |

---

## 5. Master sprint matrix

| Sprint | Name | Primary outcome | Main blockers addressed | External dependencies | Exit gate |
|--------|------|-----------------|-------------------------|-----------------------|-----------|
| 26 | Staging Current-Main Proof & Roadmap Bootstrap | Launch candidate staging-proven (`79bd03f`); EXT apps bootstrap pending | P0-6 | EXT-01…05,08,10,17,18 bootstrap | Technical: Staging `/ready` + smoke on current digest ([evidence](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); close still requires register updates |
| 27 | Transactional Identity & Email | Real email; reset/verify complete | P0-5; HIGH demo-auth | EXT-08, EXT-09 | Staging E2E reset+verify via real provider |
| 28 | Privacy, Legal, Consent & Deletion | ToS/Privacy/consent/deletion/export | P0-4; MEDIUM GDPR | EXT-17…22 | Legal draft published internally; deletion E2E staging; counsel review started |
| 29 | Production Consumer Web UI | Public web app + a11y + e2e baseline | P1-6 | None critical | Staging UI journey green; build validation |
| 30 | Public Beta Readiness Audit *(historical)* | Audit record only | — | — | Closed — NOT READY |
| 31 | Merchant Platform Unification | One connector/registry/router + min reliability contracts | P1-1A | None | Certification suite exists; 4/18 dual-path retired or dual-run documented; reliability contracts exported |
| 32 | Philippines Merchant Certification | ≥1 real PH path | P0-1 (PH) | EXT-01,06,07 | Real legally usable current-data response; staging+limited proof |
| 33 | United States Merchant Certification | ≥1 real US path | P0-1 (US) | EXT-02,06,07 | Same for US |
| 34 | Singapore Merchant Certification | ≥1 real SG path | P0-1 (SG) | EXT-03,06,07 | Same for SG |
| 35 | United Kingdom Merchant Certification | ≥1 real UK path | P0-1 (UK) | EXT-04,06,07 | Same for UK |
| 36 | Canada Merchant Certification | ≥1 real CA path | P0-1 (CA) | EXT-05,06,07 | Same for CA |
| 37 | MarketContext, Currency & Localization | Coherent market/FX/locale + shipping honesty | P1-1B; P1-2 | EXT-23 | Fail-closed FX; unsupported-market behavior; shipping honesty; FR-CA decision recorded |
| 38 | Connector Reliability & Honest Degradation | Cross-connector production hardening | Live-HTTP risk | EXT-25 | Multi-connector chaos + probes + aggregated health evidenced |
| 39 | Analytics, Feedback & Support | Consent-gated product analytics + support path | P1-4 | EXT-15,16,17,22 | Events + dashboards + feedback path in staging |
| 40 | Security & Abuse Hardening | HIGH/launch-blocking MEDIUM closed | P1-3, P1-5; sec findings | — | Security go/no-go package ready |
| 41 | Production Environment & Deploy Path | Prod AWS + deploy/rollback workflows | P0-2; HIGH prod path | EXT-10…14 | Prod dry-run `/ready`; rollback path exists |
| 42 | Production Operations & DR Evidence | Monitoring, paging, backup restore, runbooks | P0-3 | EXT-16,24 | Restore drill + page ack evidence filed |
| 43 | Performance & Capacity Validation | Load/spike evidence for announced size | Capacity unknown | EXT-25 | Evidence for 1k/10k gates or reduced announcement |
| 44 | Claims, Approvals & Launch Rehearsal | Approved claims + go/no-go | Claim honesty | EXT-19…21 | Signed legal/security/ops approvals; rehearsal OK |
| 45 | Controlled Global Public Beta Launch | Public beta live under controlled rollout | All exit criteria §9 | Remaining EXT as applicable | Exit criteria 1–22 all true or market removed |
| 46 | Post-Launch Stabilization | Stabilize; absorb Sev1/Sev2; learning cadence | Post-cutover risk | — | Stability window complete; backlog groomed |

Detailed definitions: [`sprints/`](sprints/).

---

## 6. Gap-coverage matrix (audit requirements → owners)

| Audit requirement | Existing coverage | New owning sprint | Acceptance evidence | Launch blocker? |
|-------------------|-------------------|-------------------|---------------------|-----------------|
| Current-main staging proof | Older SHA staging proven; **current main `79bd03f` staging_ok packaged** | 26 | Evidence JSON + `/ready` on launch candidate — see [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md); EXT bootstrap still open | Yes |
| Real email + password recovery | NullEmailSender / demo tokens | 27 | Inbox delivery + confirm routes | Yes |
| Email verification | Partial request-only | 27 | Verify confirm E2E | Yes |
| ToS / Privacy / consent | Missing | 28 | Published URLs + consent records | Yes |
| Account deletion / export | Missing | 28 | Delete+export E2E; propagation checklist | Yes |
| Consumer production UI | demo.html only | 29 | Staging UI e2e | Yes (public UX) |
| Sprint 4/18 unification (P1-1A) | Parallel stacks | 31 | Single registry/router + tests | Yes (P1) |
| Unsupported-market behavior (P1-1B) | Missing | 37 | Selector + disclosure + no unsupported invoke | Yes (P1) |
| Shipping-cost honesty (P1-2) | Enrichment default risk | 37 | Shipping-known/unknown modeled + tests; 44 verifies wording | Yes (P1) |
| PH real merchant path | Fixtures only | 32 | Live provider response certified | Yes to **name PH** |
| US real merchant path | Stubs | 33 | Same | Yes to **name US** |
| SG real merchant path | Stubs | 34 | Same | Yes to **name SG** |
| UK real merchant path | Allow-list only | 35 | Same | Yes to **name UK** |
| CA real merchant path | None | 36 | Same | Yes to **name CA** |
| MarketContext / FX / localization | Missing | 37 | Fail-closed FX tests + selector | Yes for multi-market honesty |
| Cross-connector reliability hardening | Missing / partial | 38 | Multi-connector chaos + probes + disclosures | Yes with live HTTP |
| Product analytics + feedback | Logs/demo only | 39 | Consent-gated events + support path | Soft Yes (learning) |
| Security HIGH / blocking MEDIUM | Open | 40 | Closure evidence | Yes |
| Production deploy path | Missing | 41 | Prod dry-run evidence | Yes |
| Monitoring / paging / restore | Incomplete | 42 | Drill + page proofs | Yes |
| Capacity 1k/10k/spike | Unproven | 43 | Load reports | Yes for announced size |
| Public claims approval | Missing | 44 | Signed claim matrix | Yes |
| Controlled public launch | Missing | 45 | Checklist sign-off | Yes |
| Post-launch stabilization | Missing | 46 | Stability report | Program close |
| Staging promotion discipline (P1-7) | Current-candidate staging_ok + smoke packaged | 26 | Current-candidate staging_ok + smoke ([evidence](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); 45 final verify | Yes (P1) |
| DealScore / organic neutrality | Verified | 5/6 + 44 certify | CI + monitoring | Integrity gate |
| Fixture never shown as live | Verified | 18 + 38/45 | Freshness gates + release check | Yes |

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

**Rule:** Global site access may proceed with a **subset** of named markets if others fail external gates. Empty named-market list is allowed only with non-shopping positioning (not Global Public Beta as defined here).

---

## 8. External dependency matrix (summary)

| Dependency | Owner | Target sprint | Current status | Fallback | Launch impact |
|------------|-------|---------------|----------------|----------|---------------|
| Merchant approvals PH/US/SG/UK/CA | Marketplace + legal | 32–36 | not_started | Remove market from supported list | Market-specific |
| Transactional email + DNS auth | Identity + ops | 27 | not_started | Invite-only / disable self-serve reset (demotes beta) | Launch / auth |
| Domain / DNS / TLS | Ops | 41 | not_started | Delay public hostname | Launch |
| AWS production + secrets | Ops | 41 | partial TF | Delay production | Launch |
| Legal review + published policies | Legal | 28 / 44 / 45 | not_started | Delay launch | Launch |
| Analytics / consent tooling | Product | 39 | not_started | Essential-only first-party | Learning |
| FX provider | Marketplace | 37 | not_started | No cross-currency compare | Multi-currency |
| Paging destination | Ops | 42 | not_started | Delay prod launch | Launch |
| AI production quota | AI/ops | 38 / 43 | unknown | Deterministic fallback only | AI claims |
| Payments / app stores | — | — | n_a_beta | Out of scope | None |

Full register (includes **Scope** column): [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md).

---

## 9. Global Public Beta exit criteria (Sprint 45 cannot close unless true)

Sprint 45 is the **final go/no-go verification** gate for each criterion. Documentation alone cannot satisfy runtime requirements. Each criterion has exactly one **primary owning sprint** for implementation/evidence production.

| ID | Exit criterion | Primary owning sprint | Final evidence | Sprint 45 decision |
|----|----------------|----------------------|----------------|--------------------|
| EC-01 | Current launch candidate successfully deployed to staging | 26 | Staging deploy evidence JSON + `/ready` READY for launch-candidate digest | Verify candidate still staging_ok; no-go if stale/unproven |
| EC-02 | Full user journey passes in staging | 29 | Staging E2E report (register→search→DealScore→recommend→redirect + account/privacy paths) | Re-run smoke on frozen candidate; no-go on failure |
| EC-03 | Password recovery and email verification work through a real provider | 27 | Real-inbox delivery + confirm-route E2E artifacts | Verify still green on candidate; no-go if demo tokens usable |
| EC-04 | Terms, Privacy Policy, consent, deletion, and support are live | 28 | Live policy URLs + consent/deletion/export staging→prod proof; support contact published | Verify published + operable; no-go if any missing |
| EC-05 | Production environment is provisioned and isolated | 41 | Applied prod AWS evidence + isolation proof (staging cannot read prod secrets) | Confirm isolation still holds; no-go if missing |
| EC-06 | Production deploy and rollback workflows are validated | 41 | Prod deploy dry-run + rollback workflow evidence | Confirm rehearsed path exists; no-go if unrehearsed |
| EC-07 | Backup restore has been rehearsed | 42 | Restore drill report with measured RTO | Confirm report current; no-go if absent |
| EC-08 | Monitoring, dashboards, alerts, and paging are active | 42 | Dashboard links + alert config + page/ack ≤15m evidence | Confirm active paging destination; no-go if inactive |
| EC-09 | ≥1 real validated merchant path in every **named** supported market | Per named market: 32\|33\|34\|35\|36 | Per-market certification report with real current-data response | Name only certified markets; remove failed markets |
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
| EC-22 | Final launch checklist signed off | 45 | Signed Sprint 45 checklist artifact | Launch-control ownership; required for close |

**Market note for EC-09:** When multiple markets are named, each named market’s certification sprint (32/33/34/35/36) is the primary owner for that market’s path. Sprint 45 only verifies and may remove markets.

---

## 10. Evidence maturity matrix (program view)

| Capability | Implemented | CI tested | Staging proven | Production rehearsed | Launch approved |
|------------|:-----------:|:---------:|:--------------:|:--------------------:|:---------------:|
| Auth register/login/logout | Yes | Yes | Yes (26 tech evidence; Sprint 26 open for EXT) | Pending (41/45) | Pending (44) |
| Password reset / email verify | Partial | Partial | Pending (27) | Pending (41) | Pending (44) |
| Privacy/deletion/legal | No | No | Pending (28) | Pending (45) | Pending (44) |
| Consumer web UI | No | No | Pending (29) | Pending (45) | Pending (44) |
| DealScore / Recommendation | Yes | Yes | Yes (26 tech evidence; mocked-data disclosure observed) | Pending (45) | Certify (44) |
| Merchant platform unified | No | Partial | Pending (31) | Pending (45) | Pending (44) |
| PH/US/SG/UK/CA real paths | No | No | Pending (32–36) | Pending (45) | Per-market (44/45) |
| MarketContext / FX | No | Partial fail-closed | Pending (37) | Pending (45) | Pending (44) |
| Connector reliability | Partial | Partial | Pending (38) | Pending (45) | Pending (44) |
| Product analytics | No | No | Pending (39) | Pending (45) | Pending (44) |
| Security hardening package | Partial | Partial | Pending (40) | Pending (44) | Pending (44) |
| Staging deploy/rollback arch | Yes | Yes | Yes (current main `79bd03f` staging_ok; see Sprint 26 evidence) | N/A | — |
| Production deploy/rollback | No | No | N/A | Pending (41/44) | Pending (44) |
| Backup restore / paging | No | No | Pending (42) | Pending (42/44) | Pending (44) |
| Capacity evidence | No | No | Pending (43) | Pending (43) | Pending (44) |

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
| Finds the best / smartest deal | Incomplete coverage | — | — | “Best” / “smartest” deal |
| Detects scams | No product evidence | — | — | Any scam-detection claim |
| Real-time / always up to date | Freshness SLOs unmet | 38 / 44 | “Prices as of [timestamp]; may be stale” | “Real-time” / “always up to date” |
| Supports PH, US, SG, UK, Canada | Each market gate pass | 32–36 / 44 / 45 | “Supported shopping markets: [passed only]” | Naming markets without gates |
| Globally reachable ≠ supported markets | Coverage matrix published | 44 / 45 | Explicit distinction statement | Conflating access with coverage |

---

## 12. Critical-path matrix

| Critical item | Predecessor | Earliest sprint | External risk | Fallback |
|---------------|-------------|-----------------|---------------|----------|
| Staging current-main | 25b.* workflows | 26 | Host/bootstrap drift | Fix host; re-run deploy |
| Real email | EXT-08/09 | 27 | Provider/DNS delay | Invite-only demotion |
| Legal package | Counsel | 28 → 44 | Review latency | Delay launch |
| Consumer UI | API stable (24) | 29 | Scope creep | Narrow MVP screens |
| Platform unify + min reliability contracts | Lock review | 31 | Dual-run complexity | Documented dual-run with hard deadline |
| First real market (PH) | EXT-01 + **31 contracts** | 32 | Provider denial | Remove PH; try next market |
| Remaining markets | EXT-02…05 + 31 | 33–36 (parallel OK) | Staggered denials | Launch with subset |
| MarketContext/FX + shipping honesty | 31 + 29 UI shell | 37 | FX vendor | Fail-closed no compare |
| Cross-connector hardening | ≥1 certified market preferred | 38 | Incomplete chaos coverage | Hold live multi-market launch |
| Prod path | Staging green | 41 | AWS/DNS/TLS | Delay public |
| Ops evidence | 41 | 42 | Paging vendor | Delay public |
| Capacity | 41 staging/prod-like | 43 | Fail load tests | Reduce announced size |
| Go/no-go | 27–43 done subset | 44 | Legal/security hold | No-go |
| Public launch | 44 approvals | 45 | Any Sev1 | Rollback |
| Stabilization | 45 | 46 | Incident load | Extend window |

**Dependency classes:** Sprint 31 reliability contracts = **strict predecessor** of 32–36. Market certifications after 31 = **parallelizable**. Sprint 38 = **soft dependency** on having at least one live path to harden, and a **final launch gate** for multi-connector production evidence. External approvals = **external gates**.

---

## 13. Parallel workstreams

| Stream | Sprints | Can overlap with |
|--------|---------|------------------|
| External applications & legal drafting | 26→44 | All engineering after 26 bootstrap |
| Identity/email | 27 | UI design spikes |
| Privacy/deletion | 28 | UI implementation (29) after API contracts |
| Consumer UI | 29 | Merchant platform design (31) |
| Merchant unification + min reliability contracts | 31 | Market EXT follow-ups |
| Market certifications | 32–36 | **Parallel after 31** if staffing allows and shared platform stable |
| MarketContext/FX + shipping honesty | 37 | After 31; can parallel late market certs carefully |
| Cross-connector reliability hardening | 38 | After/during certified connectors; before production launch |
| Analytics/support | 39 | Security (40) |
| Security | 40 | Prod TF prep |
| Production infra | 41 | Ops tooling prep |
| Ops/DR | 42 | Capacity harness build |
| Capacity | 43 | Claims drafting |
| Approvals/rehearsal | 44 | Freeze feature work |
| Launch | 45 | War-room only |
| Stabilize | 46 | Learning reviews |

---

## 14. Commitments preserved vs superseded

### Preserved

- Architecture Lock ownership for Sprints 1–25 domains and invariants
- Staging deploy/rollback architecture and evidence model
- Immutable digest promotion authority
- DealScore / Recommendation / affiliate post-rank / sponsored separation
- Fixture-never-as-live freshness rules
- Sprint identities 1–40 (names/history)
- M30 evidence *content* (still required) — relocated to Sprints 26 / 41 / 42 / 44 / 45 as applicable

### Superseded / reclassified

| Prior statement | Disposition |
|-----------------|-------------|
| Hard endpoint Sprint 40 | **Superseded** → endpoint Sprint 46 |
| Sprint 30 public launch target | **Reclassified** → readiness audit; launch not achieved |
| “Launch by Sprint 40” change-control goal | **Superseded** → launch by Sprint 45; stabilize Sprint 46 |
| Deferred bucket “Sprints 24–40” real connectors/email/UI | **Superseded** by explicit sprint ownership 27–39 |
| Simulated connectors allowed at M30 if documented | **Still true for infra rehearsal**; **not sufficient** for Global Public Beta shopping markets |

---

## 15. Acceptance gates (cross-cutting)

### Market gate (per named market)

- Real provider response in staging and production (or production-equivalent rehearsal)
- Legal/terms approval recorded
- Provenance + freshness timestamps present
- Kill switch tested
- Coverage matrix row published
- No fixture path labeled live

### Security gate (before 45)

- All HIGH closed
- Launch-blocking MEDIUM closed or written risk-accepted with expiry
- Scanning jobs green on launch candidate

### Claims gate (44)

- Every public sentence maps to evidence maturity ≥ Staging proven (prod claims need Production rehearsed/proven)

### Launch gate (45)

- Exit criteria §9

---

## 16. Post-launch stabilization (Sprint 46)

Sprint 46 **cannot** postpone unresolved Sprint 45 launch blockers. It owns stabilization findings that arise **after** an approved launch only.

- Launch-monitoring handoff from Sprint 45 + incident ownership handoff
- Sev1/Sev2 burn-down; production error-budget review
- Connector freshness/provenance + merchant-data quality review
- Supported-market and merchant coverage review
- Rollback-readiness reaffirmation (evidence + authority still valid)
- Support-volume and support-response review
- Privacy deletion/export post-launch verification; analytics consent-state review
- Capacity re-check against actual beta traffic
- Public-claims drift review
- Post-beta backlog classification
- Explicit program close report

---

## 17. Document map

| Document | Role |
|----------|------|
| **This file** | Sole master roadmap authority |
| [`GAP_INVENTORY.md`](GAP_INVENTORY.md) | Phase 1 complete inventory |
| [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md) | External dependency register |
| [`SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md`](SPRINT_30_PUBLIC_BETA_READINESS_AUDIT_SUMMARY.md) | Persisted Sprint 30 audit summary |
| [`evidence/`](evidence/) | Packaged sprint evidence (Sprint 26 current-main staging proof + bootstrap checklist + completion draft) |
| [`evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) | Sprint 26 technical staging proof (Sprint 26 still open) |
| [`sprints/`](sprints/) | Per-sprint definitions 26–46 |
| [`../architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md) | Domain ownership lock (updated cross-link) |
| [`../architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md`](../architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md) | Infra contract; M30 matrix still evidential |
| [`../LAUNCH_READINESS.md`](../LAUNCH_READINESS.md) | Probe/readiness semantics |
| [`../LAUNCH_CHECKLIST.md`](../LAUNCH_CHECKLIST.md) | Rehearsal checklist (extended by Sprint 45) |

---

## 18. P0/P1 coverage confirmation

| Item | Owner | Covered? |
|------|-------|----------|
| P0-1 Live merchants | 32–36 (one primary market sprint per named market) | Yes |
| P0-2 Production path | 41 | Yes |
| P0-3 M30 ops evidence | 42 | Yes |
| P0-4 Legal/privacy | 28 | Yes |
| P0-5 Email/reset | 27 | Yes |
| P0-6 Current-main staging | 26 (tech evidence packaged; EXT bootstrap pending) | Yes |
| P1-1A Registry/router unify | 31 | Yes |
| P1-1B Unsupported-market behavior | 37 | Yes |
| P1-2 Shipping-cost honesty | 37 (44 verifies wording only) | Yes |
| P1-3 Scanning | 40 | Yes |
| P1-4 Analytics/feedback | 39 | Yes |
| P1-5 Lockout/distributed limits | 40 | Yes |
| P1-6 Consumer UI | 29 | Yes |
| P1-7 Staging promote discipline | 26 tech proven ([evidence](evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)); 45 final verification only | Yes |

---

**End of master roadmap.**
Documentation-only change. No implementation, infrastructure, or workflow mutation is authorized by this document alone.
