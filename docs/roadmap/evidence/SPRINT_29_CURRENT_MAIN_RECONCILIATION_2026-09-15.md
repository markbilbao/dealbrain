# Sprint 29 — Current-main reconciliation (2026-09-15)

**Starting `origin/main`:** `3c514943a8a0ec34d1df97d5a329d3acb4a86e07`
(merge of PR #141, “Early Access: send and persist signup confirmation email”)
**Date (UTC):** 2026-09-15
**Authority:** [`../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md`](../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md)
**Prior merged closeout:** [`SPRINT_29_CLOSEOUT_GAP_AUDIT.md`](SPRINT_29_CLOSEOUT_GAP_AUDIT.md) (SHA `a8bd001`, PR #111) — **not erased**
**Historical unmerged remaining-closeout:** [`SPRINT_29_REMAINING_INTERNAL_CLOSEOUT_AUDIT.md`](SPRINT_29_REMAINING_INTERNAL_CLOSEOUT_AUDIT.md) (PR #127, baseline `6666bb26`) — retained as history, not current authority
**Prior staging package:** [`SPRINT_29_STAGING_CC01_EVIDENCE.md`](SPRINT_29_STAGING_CC01_EVIDENCE.md) (Deploy Staging #27 on `a8bd001`)

This audit re-reads the locked Sprint 29 definition against **current** `main`. It does **not** close Sprint 29. It does **not** merge, rebase, or close PR #127. It does **not** claim live merchant research. It does **not** replace the Phase 29.0 contract freeze. It does **not** mutate production, staging, AWS, DNS, Resend, or merchants.

## Verdict

`SPRINT 29 INTERNAL CONSUMER/CONVERSATIONAL CONTRACT COMPLETE — LIVE RESEARCH ACCEPTANCE REMAINS DEPENDENT`

Sprint 29 is **not** COMPLETE/CLOSED.

- Internally controllable Sprint 29 consumer, conversational-contract, guest/auth, SEO, a11y-engineering, and brand work is present on current `main` and covered by existing tests.
- No second conversation, Recommendation, PiqScore, or Results system was found.
- No internally controllable Sprint 29 feature implementation remains after this reconciliation. Remaining acceptance is owned by later sprints or by owner/lab sign-off.
- Live research execution, live owner-bound UUID creation, and the complete CC-01 launch-candidate journey remain owned by later sprints.
- Last packaged Sprint 29 staging E2E is still **partial** on SHA `a8bd001`. Current `main` is newer. This PR does not deploy.

## Old PR #127 identity

| Field | Value |
|-------|-------|
| PR | [#127](https://github.com/markbilbao/dealbrain/pull/127) — OPEN, mergeable=CONFLICTING / DIRTY |
| Title | Sprint 29: complete remaining internal consumer continuity readiness |
| Branch | `cursor/sprint-29-remaining-internal-closeout-d1c7` |
| HEAD | `37eae8f1eff5a4f8e91d302faaa33fbb556173a0` |
| Base (then `main`) | `6666bb26f40255b9fece39e94bc5ca2b6e3ff2dd` |
| This PR | Does **not** merge, rebase, or close #127. Owner controls closure. |

PR #127 is **stale and superseded** by this current-main reconciliation.

## Classification of old PR #127 changes

Legend: **A** already independently present on current main; **B** still valid and ported; **C** stale because later work superseded it; **D** conflicts with current architecture/roadmap and must not be ported; **E** wording updated but underlying lock remains valid.

| Old #127 change | Class | Disposition |
|-----------------|-------|-------------|
| Remaining-closeout audit markdown | **E** | Retained as historical artifact with supersession banner. Current authority is this 2026-09-15 document. |
| Current CC-01 matrix JSON | **E** | Ported with baseline SHA `3c51494`, extra honesty flags, and updated legal/email/production notes. |
| `test_sprint29_internal_closeout_matrix.py` | **E** | Ported; points at this document; locks non-claims (no shopping beta, no merchant cert, no unconditional counsel approval). |
| Cross-action affiliate-neutrality lock in `test_sprint29_closeout_locks.py` | **B** | Ported unchanged in substance. 29.4A/B/C still emit `affiliate_influence: false`. |
| Sprint 29 status → internal-contract-complete / live-research-dependent | **E** | Ported. Fresh audit still supports that verdict. |
| GAP_INVENTORY 2026-09-10 remaining-closeout addendum | **C / E** | Not copied with SHA `6666bb26`. New 2026-09-15 addendum records current truth. |
| Master roadmap §5.1 remaining-internal-contract row | **E** | Ported with current SHA and later-work caveats. |
| Master roadmap evidence-matrix consumer/Ask rows | **E** | Ported; still partial on `a8bd001`. |
| Master roadmap strict gate 1 | **E** | Ported: Sprint 29-owned contract complete; remaining launch proof is frozen-candidate CC-01 after live research exists. |
| `sprints/README.md` Sprint 29 status | **E** | Ported with current verdict. |
| `SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md` status rewrite | **E** | Ported; engineering baseline pointer updated to `3c51494`. Historical `ab23d29` suite count retained as history. |
| Closeout-gap-audit 2026-09-10 pointer | **E** | Pointer updated to this document. 2026-09-05 audit left intact. |
| Staging E2E plan: Sprint 27 now closed | **B / E** | Keep. Inbox proof is not a Sprint 29 implementation gap. |
| Staging E2E plan: “`/privacy` `/terms` remain 404 while unpublished” as a current blocker | **C** | Historically true of Deploy Staging #27. **Not** current: owner-authorized `privacy-2026-09-11` / `terms-2026-09-11` are published. Pointer added; historical 404 row kept for that package. |
| Staging E2E plan: “Published Privacy/Terms = Sprint 28 / 44 / 45” as a Sprint 29 remaining blocker | **C / E** | Early Access legal pages are published as owner-authorized content. Sprint 28 is still not COMPLETE/CLOSED. Unconditional counsel approval, CMP, DSAR certification, and Sprint 44/45 publication gates remain — **not** Sprint 29-owned. |
| “Legal publication / counsel DSAR” as a Sprint 29 remaining dependency for export/delete UI | **C / E** | Sprint 29 export/delete **UI** is complete. Remaining legal program work is Sprint 28/44/45. Early Access Privacy/Terms publication removes the unpublished-page blocker for registration links. |
| Production described as unimplemented Sprint 29 blocker | **C** | Production AWS/ALB/HTTPS/RDS/deploy path now exist as operational reality after #127. This reconciliation does **not** close Sprint 41. Production is not a Sprint 29 implementation gap. |
| Identity email treated as staging-only in Sprint 29 remaining work | **C / E** | Sprint 27 is COMPLETE/CLOSED on staging. PR #141 adds Early Access confirmation send+persist on current `main`. Production transactional email is operational per owner context and #141. Sprint 29 account UI does not own inbox delivery. |
| Affiliate-neutrality as a missing closeout lock | **B** | Still missing on `main` before this PR; ported. |
| Phase 29.0 freeze left `planned_not_implemented` | **B** | Keep. Must not be read as current implementation status. |
| Wholesale cherry-pick of #127 commits | **D** | Not done. Conflicts on `GAP_INVENTORY.md`; stale legal/email/production sentences would land incorrectly. |

No old #127 change was rejected for architecture conflict (**D** except wholesale cherry-pick). No second PiqScore, Results, Recommendation, research, or conversation system was ported.

## Items resolved since PR #127 (not Sprint 29 features)

These landed on `main` after `6666bb26` and change Sprint 29 **dependency wording**, not Sprint 29 contract code:

| Item | Evidence on current `main` | Effect on Sprint 29 |
|------|----------------------------|---------------------|
| Early Access landing + registration live | Early Access routes/tests; production foundation disables `/demo` `/search` shopping in production | Sprint 29 unfinished shopping UI stays hidden. Early Access ≠ public shopping beta. |
| Owner-authorized Privacy/Terms published | `privacy-2026-09-11` / `terms-2026-09-11`; `test_early_access_owner_authorized_legal_activation.py`; Sprint 28 catalog | `/privacy` `/terms` 200 when published. Registration UI already links published catalog (`test_sprint29_legal_registration_ui.py`). |
| Early Access policy acknowledgement | `terms_version_id`, `privacy_version_id`, `policies_acknowledged_at` | Not a Sprint 29 remaining implementation. |
| Production AWS / ALB / HTTPS / RDS / Deploy Production / SSM | Production Terraform, `deploy-production.yml`, host-foundation evidence citing live instance `i-0382907b275b835ce`, Deploy Production run regressions | Not a Sprint 29 blocker. Sprint 41 sprint doc remains **Planned**; this PR does not close 41–43. |
| Early Access confirmation email send+persist | PR #141 / `app/early_access/confirmation_email.py` / `email_confirmation_status` | Sprint 29 recovery/verify **UI** remains complete. Inbox is not a Sprint 29 code gap. |
| EXT-20 / EXT-21 | Register: `applied` as owner-authorized content layer | Unpublished-page Sprint 29 dependency is gone. EXT-19 remains `applied` (conditional), not `approved`. |

## Items still blocked / dependent

| Item | Owner |
|------|--------|
| Live merchant research / connector execution / updated Results | Sprints 31–38 |
| Live owner-bound Search → UUID snapshot | 31 routing + 38 execution |
| Certified PH product-data path | Sprint 32 (externally blocked) |
| MarketContext / five-market / FX / live destination re-evaluation | Sprint 37 |
| Support ticket + analytics backends | Sprint 39 |
| Search Console / SEO measurement | Sprint 39 / 45 |
| Security program | Sprint 40 |
| Sprint 41/42/43 closure as launch evidence | 41–43 (ops evidence; not pulled into Sprint 29) |
| Visual manifest pixel sign-off / signed a11y audit | Sprint 44 / owner |
| Immutable launch-candidate CC-01 journey / EC-02 / EC-22 | Sprint 45 |
| Unconditional counsel approval of published legal scope; CMP; legal DSAR certification | Sprint 28 / 44 / 45 |

## Exact Sprint 29-owned remaining work

**None after this PR**, other than preserving the contract:

- Do not weaken the Phase 29.0 freeze.
- Do not invent live research, fixture-as-live UUID flows, or a second scoring/Results/conversation system.
- Do not mark Sprint 29 COMPLETE/CLOSED until later-sprint acceptance that the normative CC-01 list still requires is actually satisfied — and that remaining acceptance is **not** Sprint 29-owned implementation.

Honesty/status/matrix/affiliate-lock gaps from #127 are the work of this reconciliation.

## Current acceptance matrix

| # | Acceptance requirement | Current evidence | Current status | Missing work | Owning sprint | Internal vs dependent | Sprint 29 still owns implementation? |
|---|---|---|---|---|---|---|---|
| 1 | Registration / login / recovery / verification | `/login` `/register` `/reset-password` `/verify-email`; `test_sprint29_account_pages.py`; Sprint 27 staging inbox E2E closed; PR #141 Early Access confirmation | **complete** (Sprint 29 UI) | Current-main staging/production re-proof of User-account inbox is ops, not new UI | 29 UI; 27 / 41 email | Internal UI complete | **No** |
| 2 | Results → Compare → Why → Ask equivalence | `test_results_compare_why_ask_same_decision`; `test_results_compare_why_share_canonical_decision` | **complete** (fixture decision) | Live UUID journey | 29 contract; 38 live UUID | Internal contract | **No** |
| 3 | Contextual answers from existing evidence | 29.4A `answer_from_evidence` | **complete** | Live UUID Ask | 29 | Internal | **No** |
| 4 | Session recommendation refinement | 29.4B; PiqScore bytes unchanged | **complete** | None | 29 | Internal | **No** |
| 5 | Canonical PiqScore immutability | Snapshot freeze + 29.4A/B/handoff tests | **complete** | None | 29 | Internal | **No** |
| 6 | Evaluated-set stability / iPhone–Samsung battery regression | `sprint29-context-drift.json`; `test_follow_up_cannot_introduce_the_forbidden_pixel` | **complete** | None | 29 | Internal | **No** |
| 7 | Research proposal | 29.4C `propose_research` | **complete** (proposal only) | Execution | 29 proposal; 31–38 execution | Internal proposal | **No** |
| 8 | Explicit confirmation | 29.4C + authorization handoff | **complete** | None | 29 | Internal | **No** |
| 9 | Authorization idempotency | `test_repeat_confirmation_reuses_same_authorization` | **complete** | Live one-job execution | 29 contract; 38 executor | Internal contract | **No** |
| 10 | Research execution boundary | Handoff non-executing; fixtures `mock`/`unavailable` only; `production_eligible: false` | **complete** (refusal) | Live executor | 31–38 | Dependent | **No** |
| 11 | Failed / partial / cancelled behavior | Cancel/stale/unavailable contract | **partial** | Live failed/partial/cancelled traces + updated Results | 29 contract; 38 live | Dependent for live states | **No** |
| 12 | Guest continuity | Cookie + persistence restart/CAS/TTL + session-binding | **complete** (code) | Current-main staging close/reopen | 29 | Internal complete | **No** |
| 13 | Guest → authenticated claim | `POST /consumer/claim-decision`; UUID snapshot owners stay immutable | **complete** | Live UUID claim remains immutable-owner by design | 29 | Internal | **No** |
| 14 | Affiliate neutrality | `affiliate_influence: false` on 29.4A/B/C; ranking engines have no affiliate tokens; closeout lock | **complete** | Must not be weakened; affiliate activation later must not feed scoring | 29 / 20 / 32 | Internal | **No** |
| 15 | Market-selection UI shell | `.market-shell` → `POST /consumer/shopping-market`; PH only | **complete** (shell) | Five-market / FX / destination policy | 29 shell; 37 domain | Dependent | **No** |
| 16 | SEO technical foundation | `robots.txt`, `sitemap.xml`, canonical/JSON-LD, staging noindex | **complete** (foundation) | Search Console | 29 foundation; 39/45 measurement | Dependent | **No** |
| 17 | Private UUID noindex | `test_sprint28_1_index_privacy.py` | **complete** | None | 28.1 / 29 | Internal | **No** |
| 18 | Support / feedback entry points | `/support` mailto `support@piqsavi.com` / `privacy@piqsavi.com`; no ticket form | **complete** (stub) | Ticket / analytics backend | 29 stub; 39 backend | Dependent | **No** |
| 19 | Account export / delete entry points | `/account` wired to Sprint 28 APIs; “complete legal DSAR” not claimed in UI | **complete** (UI) | Legal DSAR / vendor erasure certification | 29 UI; 28/44 legal | Dependent | **No** |
| 20 | Ask 80 px / 72 px | CSS tokens + `test_ask_insertion_heights_match_manifest` | **complete** (tokens) | Pixel QA vs artwork | 29 tokens; 44 visual | Dependent for sign-off | **No** |
| 21 | Accessibility engineering | `test_sprint29_accessibility.py` | **complete** (engineering) | Signed checklist / third-party audit | 29 engineering; owner/44 | Dependent for sign-off | **No** |
| 22 | Public-brand boundary | PiqSavi / tagline / PiqScore; no DealBrain in consumer JS/CSS | **complete** for required surfaces | Dedicated favicon pack still asset-limited | 29 | Internal complete | **No** |
| 23 | NON-NEGOTIABLE live-research boundary | Closeout locks; consumer pages must not say research executed | **complete** | Must not be weakened | 29 lock; 38 executor | Internal lock | **No** |
| 24 | CC-01 Search → snapshot | Fixture `/search` → `/results/headphones-standard`; production UUID unavailable | **dependent** | Live owner-bound snapshot | 31/38 | Dependent | **No** |
| 25 | CC-01 full journey | Contract pieces exist; staging package partial on `a8bd001` | **dependent** | Frozen launch-candidate live journey | 45 via 38 | Dependent | **No** |
| 26 | Historical 29.0 `planned_not_implemented` fixture | `validate_traceability()` freeze | **complete** as freeze | Do not flip freeze | 29.0 | Internal (do not weaken) | **No** (freeze owner only) |

Machine-readable CC-01 companion: [`../../../tests/contracts/fixtures/sprint29-internal-closeout-matrix.json`](../../../tests/contracts/fixtures/sprint29-internal-closeout-matrix.json)

## Legal dependency re-evaluation

PR #127 listed “Legal publication / counsel DSAR” as a Sprint 29 remaining dependency and told staging to expect `/privacy` `/terms` 404.

**Current truth:**

- Owner-authorized Early Access Privacy and Terms are published: `privacy-2026-09-11`, `terms-2026-09-11`.
- Early Access requires: “I agree to the Terms of Service and acknowledge the Privacy Policy.”
- Acknowledgement persists `terms_version_id`, `privacy_version_id`, `policies_acknowledged_at`.
- This is **owner-authorized publication / factual-currentness correction**, not new unconditional counsel approval.
- EXT-19 remains `applied` (written **conditional** 2026-08-19 review). `approved` is reserved for written approval of the published consumer-legal scope.
- Sprint 28 remains **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN**. Not COMPLETE/CLOSED.
- CMP / EXT-22 still `not_started`. Legal DSAR certification is still not claimed by the account export/delete **engineering** APIs.

**Sprint 29 remainder:** none. Registration UI already follows the Sprint 28 catalog. Unpublished 404 is no longer a Sprint 29 blocker.

## Production / email / support re-evaluation

| Topic | PR #127 claim | Current-main treatment |
|-------|---------------|------------------------|
| Production infra | Predated production deploy | Not a Sprint 29 unimplemented blocker. In-repo production stack + Deploy Production path exist. Host-foundation evidence refers to a live production instance. This PR does **not** close Sprint 41 or rewrite EXT-11…14 register rows. |
| Transactional email | Staging-era Sprint 27; production attach Sprint 41 | Sprint 27 COMPLETE/CLOSED on staging. PR #141 Early Access confirmation send+persist is on current `main`. Owner context: production sender live and delivery observed. Sprint 29 UI does not own Resend attach. |
| Support | `/support` mailto stub | **Unchanged.** `render_support_page()` is static mailto only. Sprint 39 owns ticket/analytics backend. Status is **not** upgraded. |

## Explicit merchant / live-research non-claims

- Live merchant research was not implemented or claimed.
- Merchants were **not** queried. No Shopee, Lazada, BuyWhere, or API Hub activation.
- Fixture products were **not** injected into real UUID flows.
- No production-certified PH merchant-data path exists. Sprint 32 is **not** complete.
- Affiliate monetization remains inactive. Affiliate state must not affect organic source eligibility, PiqScore, Recommendation, Best Piq, or ranking.
- Canonical PiqScore, Recommendation, and Results authority were not replaced.
- The Phase 29.0 contract freeze was not weakened.
- Sprint 29 is not closed.

## Explicit Early Access vs shopping-beta distinction

- `https://piqsavi.com` Early Access is the public surface. This is **still Early Access**, **not** public shopping beta.
- Unfinished shopping UI remains hidden in production (`test_production_disables_demo_search_and_shopping`).
- Sprint 45 Controlled Global Public Beta is **not** launched.
- Do not describe Early Access registration, legal-page 200s, or confirmation email as shopping-beta launch.

## Architecture preservation

One canonical Results system, one Recommendation system, one PiqScore authority, one conversation/context system, existing research-authorization boundary, current guest/auth ownership, Product Foundation, normalized-offer/effective-cost architecture, merchant neutrality, and affiliate neutrality are unchanged.

## Non-claims for this reconciliation PR

- No production, staging, AWS, DNS, Terraform, SSM, RDS, Secrets Manager, IAM, Cloudflare, or Resend mutation.
- No Deploy Production / Deploy Staging / Rollback.
- No live merchant research was fabricated.
- PR #127 was not merged, rebased, or closed.
- Owner controls merge of this replacement PR and closure of #127.

---

## 2026-09-18 final-checkpoint pointer

This 2026-09-15 reconciliation remains historically true of baseline `3c51494` / PR #142. It is **not** erased.

Successor checkpoint: [`SPRINT_29_FINAL_CHECKPOINT_2026-09-18.md`](SPRINT_29_FINAL_CHECKPOINT_2026-09-18.md) against `4a4fe65`. That checkpoint **reconfirms** the same verdict. It does **not** mark Sprint 29 COMPLETE/CLOSED. CC-01-10/11/12/24 remain unmet.
