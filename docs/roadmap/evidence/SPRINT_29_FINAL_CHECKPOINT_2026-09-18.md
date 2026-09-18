# Sprint 29 — Final checkpoint (2026-09-18)

**Starting `origin/main`:** `4a4fe65fa7438c75208a0052f52b77f929ee3903`
(merge of PR #142, “Sprint 29: reconcile internal closeout against current main”)
**Date (UTC):** 2026-09-18
**Authority:** [`../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md`](../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md)
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Prior current-main reconciliation:** [`SPRINT_29_CURRENT_MAIN_RECONCILIATION_2026-09-15.md`](SPRINT_29_CURRENT_MAIN_RECONCILIATION_2026-09-15.md) — **not erased**; historically true of `3c51494` / PR #142
**Prior merged closeout:** [`SPRINT_29_CLOSEOUT_GAP_AUDIT.md`](SPRINT_29_CLOSEOUT_GAP_AUDIT.md) (SHA `a8bd001`, PR #111) — **not erased**
**Historical unmerged remaining-closeout:** [`SPRINT_29_REMAINING_INTERNAL_CLOSEOUT_AUDIT.md`](SPRINT_29_REMAINING_INTERNAL_CLOSEOUT_AUDIT.md) (PR #127) — retained as history, not current authority

This checkpoint re-reads the locked Sprint 29 definition and master-roadmap ownership against **current** `main` after PR #142. It does **not** redo PR #142. It does **not** merge, rebase, or close PR #127. It does **not** claim live merchant research. It does **not** replace the Phase 29.0 contract freeze. It does **not** mutate production, staging, AWS, DNS, Resend, or merchants.

## Verdict

`SPRINT 29 COMPLETE / CLOSED`

- Every Sprint-29-owned implementation requirement is present on current `main` and covered by existing tests.
- No second conversation, Recommendation, PiqScore, or Results system was found.
- Remaining live-research, MarketContext policy, support-backend, visual-sign-off, and frozen-candidate CC-01 work is **later-sprint launch acceptance**. It does **not** keep Sprint 29 open.
- Precedent: Sprint 27 is COMPLETE/CLOSED as EC-03 primary owner while production email attach remains Sprint 41 and Sprint 45 re-verifies EC-03. Sprint 29 is the same shape for EC-02 / CC-01: primary implementation owner of the consumer/conversational contract; Sprint 38 owns live execution; Sprint 45 re-runs CC-01 on the immutable launch candidate.
- Early Access being live is **not** public shopping beta. Sprint 29 close does **not** launch shopping, certify merchants, or enable affiliate monetization.

## Ownership question (A vs B)

PR #142 recorded `INTERNAL CONSUMER/CONVERSATIONAL CONTRACT COMPLETE — LIVE RESEARCH ACCEPTANCE REMAINS DEPENDENT` and refused COMPLETE/CLOSED because CC-01 items that need live execution were still listed under Sprint 29.

That hybrid is **not** the strongest truthful status.

| Later work | Owner | Sprint 29 closer? | Launch closer? |
|---|---|---|---|
| Live merchant research / connector execution / updated Results | 31–38 (execution: **38**) | **No** — Sprint 29 architecture may only exercise `unavailable` / non-production `mock`; live is fail-closed until 38 | Yes — EC-02 / CC-01 / EC-23 |
| Certified PH product-data path | **32** | **No** — Sprint 29 explicit non-goal | Yes — EC-09 |
| Live Search → owner-bound UUID | 29 presentation (**done**); 31 routing; **38** execution | **No** remaining Sprint 29 implementation | Yes — EC-23 |
| Execution traces / live failed-partial-cancelled | **38** | **No** — Sprint 29 owns the non-executing contract and truthful unavailable state | Yes — CC-01-11/13 |
| MarketContext / five-market / FX / live destination re-evaluation | **37** | **No** — Sprint 29 owns the PH UI shell only | Yes — EC-11/12/26 |
| Analytics / support ticket backends | **39** | **No** — Sprint 29 owns `/support` mailto stub | Yes — EC-14/27 |
| Search Console / SEO measurement | **39 / 45** | **No** — Sprint 29 owns technical foundation | Yes — EC-30 |
| Security program | **40** | **No** | Yes — EC-15 |
| Sprint 41/42/43 ops closure | **41–43** | **No** | Yes — EC-05…08/16 |
| Visual manifest pixel sign-off / signed a11y audit | **44** / owner | **No** — Sprint 29 owns engineering tokens, CSS/HTML contract, and the recorded baseline | Yes — CC-01-20; rehearsal |
| Immutable launch-candidate CC-01 journey / EC-02 / EC-22 | **45** verifies; 38 supplies live execution | **No** | Yes — EC-02 / EC-22 |

**Answer: B.** Later-sprint dependencies are later **launch** acceptance. They must not prevent Sprint 29 itself from being marked COMPLETE/CLOSED.

This is permitted by the normative Sprint 29 definition:

- Sprint 29 owns the conversational contract only: proposal → confirmation → authorized research request. That contract is implemented.
- Actual live research execution belongs to Sprints 31–38.
- External dependencies: none critical; UI may progress against non-live contracts.
- Validation explicitly allows end-to-end tests using non-live provider contracts.
- Explicit non-goals include certifying live merchant data (32–36), final MarketContext (37), and Sprint 39 backends.
- CC-01 as a full live pass lives under master-roadmap §9 (“Sprint 45 cannot close unless true”), with supporting owners 31/37/38/39/40/43 and final verifier 45.

Sprint 28 remains a different case: its remaining gates (unconditional counsel approval, CMP, legal DSAR certification) are **still Sprint 28-owned**. Sprint 29 does not own live research execution, so waiting for Sprint 38/45 is not a Sprint 29 closer.

## Stale PR #127

[#127](https://github.com/markbilbao/dealbrain/pull/127) remains **OPEN**, mergeable=CONFLICTING, and **superseded** by merged PR #142. This checkpoint does not merge, rebase, cherry-pick, or close it. Owner controls closure.

## Sprint-29-owned remaining implementation

**None.**

Do not weaken the Phase 29.0 freeze. Do not invent live research, fixture-as-live UUID flows, or a second scoring/Results/conversation system.

## Requirement audit (implementation, not launch)

| # | Requirement | Sprint 29-owned implementation complete? | Remaining dependency | Dependency owner | Prevents Sprint 29 closure? |
|---|---|---|---|---|---|
| 1 | Results → Compare → Why → Ask consistency | **YES** | Live UUID journey | 38 (live UUID); 29 contract done | **No** |
| 2 | Contextual answers from existing evidence | **YES** | Live UUID Ask | 29 done; 38 live UUID | **No** |
| 3 | Recommendation refinement | **YES** | None | 29 | **No** |
| 4 | Canonical PiqScore immutability | **YES** | None | 29 | **No** |
| 5 | Evaluated-set stability | **YES** | None | 29 | **No** |
| 6 | Research proposal | **YES** (proposal only) | Execution | 31–38 | **No** |
| 7 | Explicit research confirmation | **YES** | None | 29 | **No** |
| 8 | Authorization idempotency contract | **YES** | Live one-job execution | 38 executor | **No** |
| 9 | Research execution boundary | **YES** (refusal / non-executing handoff) | Live executor | 31–38 | **No** |
| 10 | Failed / partial / cancelled contract behavior | **YES** (cancel/stale/unavailable contract) | Live traces + updated Results | 38 | **No** |
| 11 | Guest continuity | **YES** | Current-main staging close/reopen (ops) | 29 code done; 45 re-proof | **No** |
| 12 | Guest → authenticated transition | **YES** | Live UUID owner remains immutable by design | 29 | **No** |
| 13 | Affiliate neutrality | **YES** | Must not be weakened when affiliates activate | 29 / 20 / 32 | **No** |
| 14 | PH market-selection shell | **YES** (shell) | Five-market / FX / destination policy | 37 | **No** |
| 15 | SEO technical foundation | **YES** | Search Console | 39 / 45 | **No** |
| 16 | Private UUID noindex | **YES** | None | 28.1 / 29 | **No** |
| 17 | Support entry point | **YES** (mailto stub) | Ticket / analytics backend | 39 | **No** |
| 18 | Account export/delete UI entry points | **YES** | Legal DSAR / vendor erasure certification | 28 / 44 | **No** |
| 19 | Ask desktop/mobile layout contract | **YES** (80 px / 72 px tokens) | Pixel QA vs artwork | 44 | **No** |
| 20 | Accessibility engineering | **YES** | Signed checklist / third-party audit | 44 / owner | **No** |
| 21 | PiqSavi public-brand boundary | **YES** for required surfaces | Dedicated favicon pack still asset-limited | 29 complete for required surfaces | **No** |
| 22 | Live-research non-claim protection | **YES** | Must not be weakened | 29 lock; 38 executor | **No** |
| 23 | CC-01 behavioral matrix | **YES** (24 rows; ≥20 CC tests) | Live rows remain later-sprint evidence | 38 / 45 | **No** |
| 24 | Snapshot / decision immutability | **YES** | Live atomic updated Results | 38 | **No** |
| 25 | No second Results / Recommendation / PiqScore / conversation system | **YES** | Must not be introduced later | 5 / 6 / 29 lock | **No** |

Machine-readable companion: [`../../../tests/contracts/fixtures/sprint29-internal-closeout-matrix.json`](../../../tests/contracts/fixtures/sprint29-internal-closeout-matrix.json)

## Explicit non-claims

- Live merchant research was not implemented or claimed.
- Merchants were not queried. No Shopee, Lazada, BuyWhere, or API Hub activation.
- Fixture products were not injected into real UUID flows.
- No production-certified PH merchant-data path exists. Sprint 32 is **not** complete.
- Affiliate monetization remains inactive. Affiliate state must not affect organic source eligibility, PiqScore, Recommendation, Best Piq, or ranking.
- Canonical PiqScore, Recommendation, and Results authority were not replaced.
- The Phase 29.0 contract freeze was not weakened.
- Early Access ≠ public shopping beta. Unfinished shopping UI stays hidden in production.
- Sprint 45 Controlled Global Public Beta is **not** launched.
- No production, staging, AWS, DNS, Terraform, SSM, RDS, Secrets Manager, IAM, Cloudflare, Resend, or merchant mutation occurred during this checkpoint.

## Architecture preservation

One canonical Results system, one Recommendation system, one PiqScore authority, one conversation/context system, existing research-authorization boundary, current guest/auth ownership, Product Foundation, normalized-offer/effective-cost architecture, merchant neutrality, and affiliate neutrality are unchanged.
