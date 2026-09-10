# Sprint 29 — Remaining Internal Closeout Audit

**Audit baseline:** `6666bb26f40255b9fece39e94bc5ca2b6e3ff2dd` (`origin/main` at start of this work)  
**Date (UTC):** 2026-09-10  
**Authority:** [`../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md`](../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md)  
**Prior closeout:** [`SPRINT_29_CLOSEOUT_GAP_AUDIT.md`](SPRINT_29_CLOSEOUT_GAP_AUDIT.md) (merged SHA `a8bd001`)  
**Prior staging package:** [`SPRINT_29_STAGING_CC01_EVIDENCE.md`](SPRINT_29_STAGING_CC01_EVIDENCE.md) (Deploy Staging #27 on `a8bd001`)

This audit re-reads the locked Sprint 29 definition against current `main`. It does **not** close Sprint 29. It does **not** claim live merchant research. It does **not** replace the Phase 29.0 contract freeze.

## Verdict

`SPRINT 29 INTERNAL CONSUMER/CONVERSATIONAL CONTRACT COMPLETE — LIVE RESEARCH ACCEPTANCE REMAINS DEPENDENT`

- Internally controllable Sprint 29 consumer, conversational-contract, guest/auth, SEO, a11y-engineering, and brand work is present on current `main` and covered by existing tests.
- No second conversation, Recommendation, PiqScore, or Results system was found.
- Live research execution, live owner-bound UUID creation, and the complete CC-01 launch-candidate journey remain owned by later sprints.
- Last recorded Sprint 29 staging E2E is **partial** on SHA `a8bd001`. Current `main` is newer. Non-live journeys can be re-proven after a later Deploy Staging of the merged SHA. This PR does not deploy.

Sprint 29 is **not** COMPLETE/CLOSED.

## Classification legend

| Class | Meaning |
|-------|---------|
| `already_complete` | Code + tests on current `main` satisfy the Sprint 29-owned slice |
| `internal_missing` | Sprint 29 still owns an internally controllable gap |
| `staging_verifiable_now` | Can be re-proven on current staging without live research |
| `blocked_31_38` | Requires live research / certified execution |
| `blocked_later` | Owned by Sprint 37, 39, 44, or 45 (or owner sign-off) |
| `stale_wording` | Historical text that must not be read as current implementation truth |

## Acceptance matrix

| Acceptance requirement | Existing evidence | Missing work | Owner sprint | Internal vs dependent | Action in this PR |
|---|---|---|---|---|---|
| Registration / login / recovery / verification-state journey | `/login` `/register` `/reset-password` `/verify-email`; `app/consumer/account_pages.py`; `tests/unit/test_sprint29_account_pages.py`; Sprint 27 inbox E2E now closed | Current-main staging re-proof | 29 UI; 27 email | Internal UI complete; staging re-proof after merge | Document only |
| Results → Compare → Why → Ask equivalence | Product Foundation pages; `test_results_compare_why_ask_same_decision`; `test_cross_surface_overlay_is_consistent` | None for Sprint 29 contract | 29 | Internal | None |
| Contextual answers from existing evidence | 29.4A `answer_from_evidence`; 25 tests | None | 29 | Internal | None |
| Session recommendation refinement | 29.4B; `test_piqscore_bytes_unchanged_after_service_refine` | None | 29 | Internal | None |
| Canonical PiqScore immutability | Snapshot repo + 29.4B locks | None | 29 | Internal | None |
| Evaluated-set stability | `test_battery_follow_up_preserves_the_exact_evaluated_set` | None | 29 | Internal | None |
| Research proposal | 29.4C `propose_research`; 22 tests | None | 29 | Internal | None |
| Explicit confirmation | Confirmation chips in `consumer.js`; authorization handoff | None | 29 | Internal | None |
| Authorization idempotency | `test_repeat_confirmation_reuses_same_authorization` | None | 29 | Internal | None |
| Research execution boundary | `research_confirmation_received_but_execution_unavailable`; no merchant calls | Live executor | 29 contract; 31–38 execution | Dependent | Preserve non-claim |
| Failed / partial / cancelled state behavior | Cancel/invalidate/fail-closed authorization; truthful unavailable after confirm | Live failed/partial/cancelled execution traces | 29 contract; 38 live states | Dependent for live states | None |
| Guest continuity (nav / close-reopen / restart / multi-worker / expiry / deletion / logout / shared-device) | Persistence + owner-cookie + session-binding suites | Current-main staging close/reopen | 29 | Internal complete; staging re-proof | Document only |
| Guest→authenticated transition | `POST /consumer/claim-decision`; `account.js` `afterAuth`; principal validation + rotation tests | Fixture conversations only on older staging | 29 | Internal | None |
| Affiliate-neutrality | Engine + refine + authorization asserts; services hardcode `affiliate_influence: false` | Explicit 29.4A / 29.4C processing lock was thinner than 29.4B | 29 | Internal | Add cross-action lock |
| Market-selection UI shell | `.market-shell` → `POST /consumer/shopping-market` | Five-market policy / FX / destination re-eval | 29 shell; 37 domain | Dependent | None |
| SEO technical foundation | `robots.txt`, `sitemap.xml`, canonical/JSON-LD, staging noindex | Search Console / measurement | 29 foundation; 39/45 measurement | Dependent | None |
| Private UUID noindex | UUID Results/Compare/Why `X-Robots-Tag` + meta | None | 29 / 28.1 | Internal | None |
| Support / feedback entry points | `/support` mailto `support@piqsavi.com` / `privacy@piqsavi.com` | Ticket / analytics backend | 29 stub; 39 backend | Dependent | None |
| Account export / delete entry points | `/account` wired to Sprint 28 APIs | Legal DSAR / counsel publication | 29 UI; 28/44 legal | Dependent | None |
| Desktop / mobile Ask insertion sizing | CSS `--ask-h: 80px` / `72px`; height lock test | Pixel QA vs artwork | 29 tokens; 44 visual | Internal tokens complete | None |
| Accessibility | Escape, focus trap/restore, `aria-live`, safe-area, keyboard dock | Signed checklist / third-party audit | 29 engineering; owner/44 sign-off | Dependent for sign-off | None |
| Public-brand boundary | PiqSavi / tagline / PiqScore; `test_piqsavi_public_brand.py` | Dedicated favicon pack still asset-limited | 29 | Internal complete for required surfaces | None |
| NON-NEGOTIABLE live-research boundary | Closeout locks; research fixtures `unavailable`/`mock` only | Must not be weakened | 29 | Internal | Preserve |
| CC-01-01 existing ConversationRepository / ConversationContext | `test_existing_conversation_architecture_is_extended` | None | 29 | Internal | None |
| CC-01-02 sole Results / Recommendation / PiqScore authority | Snapshot + authority lock | None | 29 | Internal | None |
| CC-01-03 search creates server-owned decision context | Snapshot contract + fixture catalog on staging | Live owner-bound search | 29 presentation; 31/38 live creation | Dependent | None |
| CC-01-04 full guest journey including truthful research + updated Results | Unit/service path through propose/confirm/unavailable | Live research + updated Results | 29 contract; 31–38 | Dependent | None |
| CC-01-05 Results / Compare / Why / mobile sheet equivalence | Cross-surface tests + Ask on all three pages | Mobile lab pass | 29 code; 44 lab | Internal code complete | None |
| CC-01-06 evidence answers do not research | 29.4A outside-set / no-research tests | None | 29 | Internal | None |
| CC-01-07 refinement leaves PiqScore bytes unchanged | `test_piqscore_bytes_unchanged_after_service_refine` | None | 29 | Internal | None |
| CC-01-08 session priorities are not account preferences | `test_session_priorities_do_not_write_account_preferences` | None | 29 | Internal | None |
| CC-01-09 research proposed only when evidence insufficient | 29.4C proposal tests | None | 29 | Internal | None |
| CC-01-10 confirmation idempotent; starts exactly one real execution | Idempotent authorization; execution unavailable | One real live execution | 29 contract; 38 execution | Dependent | None |
| CC-01-11 execution-backed loading/partial/stale/completed/failed/cancelled/merchant/offer/price/review/freshness | Truthful unavailable only | Live execution evidence | 38 | Dependent | None |
| CC-01-12 completed research atomically returns new Results | Not implemented (correct) | Live atomic snapshot update | 38 | Dependent | None |
| CC-01-13 failed/partial/cancelled preserve last valid decision | Authorization cancel/invalidate; no fabricated execution | Live failed/partial traces | 29 contract; 38 live | Dependent | None |
| CC-01-14 evaluated set stable unless research approved | Context-drift fixture + snapshot tests | None | 29 | Internal | None |
| CC-01-15 iPhone 17 Pro Max / Samsung Galaxy S25 Ultra 512GB battery regression | `test_follow_up_cannot_introduce_the_forbidden_pixel` | None | 29 | Internal | None |
| CC-01-16 bounded turn history | `test_active_session_retains_bounded_turn_history` | None | 29 | Internal | None |
| CC-01-17 guest continuity durable and isolated | Persistence restart/CAS/TTL + cookie/session suites | Current-main staging close/reopen | 29 | Internal | None |
| CC-01-18 guest→auth validates both principals, rotates credentials, isolates accounts | Guest-claim + account-session-binding tests | Live UUID claim remains immutable-owner | 29 | Internal | None |
| CC-01-19 affiliate economics never influence actions | Refine + authorization asserts | Cross-action lock for 29.4A/C | 29 | Internal | Add lock |
| CC-01-20 visual states match approved Product Foundation artwork | Artwork hashes frozen; CSS/HTML reproduce insertion | Pixel QA | 44 | Dependent | None |
| CC-01-21 Ask insertion 80 px / 72 px | `test_ask_insertion_heights_match_manifest` | None | 29 | Internal | None |
| CC-01-22 accessibility contract | `test_conversation_surfaces_meet_accessibility_contract` | Signed audit | 29 engineering; owner/44 | Dependent for sign-off | None |
| CC-01-23 ≥20 Conversational Continuity behavior tests | Current `main` already has far more than 20 named Sprint 29 CC tests | Named matrix test `test_cc01_behavioral_matrix_is_complete` was missing; 29.0 freeze still says `planned_not_implemented` | 29 | Internal | Add matrix lock; do **not** mutate 29.0 freeze |
| CC-01-24 complete CC-01 staging journey on immutable launch-candidate digest | Partial package on `a8bd001` | Frozen launch-candidate live journey | 45 via 38 | Dependent | Do not claim complete |
| Save vs Watch | Copy and account sections honest; Save ≠ Watch; Watch unavailable | Functional decision-Save wiring would invent a second save path | 29 copy; later product Save | Internal copy complete | Do not invent Save wiring |
| Fixture-as-live prevention | Production UUID unavailable; fixtures staging/dev only | Live creation | 29 / 38 / 45 | Dependent | None |
| Phase 29.0 CC-01 traceability fixture all `planned_not_implemented` | Frozen by `validate_traceability()` | Historical freeze, not current status | 29.0 freeze | `stale_wording` if read as current | Keep freeze; add current matrix |
| GAP_INVENTORY §A “only demo.html” | 2026-08-24 addendum already called it stale | Body never rewritten | docs | `stale_wording` | Add 2026-09-10 addendum |

## Already complete on current main

- 29.0–29.4C, Product Foundation, economics, UUID presentation, schema 1.2, research authorization handoff
- Account / auth / export / delete / support document routes
- Market-selection UI shell (PH)
- SEO technical foundation and private UUID / staging noindex
- Consumer a11y engineering slice and Ask 80/72 insertion tokens
- Guest owner cookie, claim, session binding, restart/TTL/CAS persistence
- Public brand boundary (PiqSavi / Your AI Personal Shopper / PiqScore)
- ≥20 Conversational Continuity behavior tests (existing suites; not duplicated here)

## Remaining internally controllable gaps found

1. **Honesty / traceability:** the Phase 29.0 freeze still records every CC-01 row as `planned_not_implemented`. That freeze must stay. Current status was not machine-locked.
2. **Affiliate-neutrality lock breadth:** 29.4A and 29.4C already emit `affiliate_influence: false`, but the dedicated closeout lock did not cover all three conversational actions.
3. **Status wording:** Sprint 29 docs still said only “In progress” even though remaining work is dependency-owned, not missing consumer/conversational contract code.
4. **Stale inventory:** GAP_INVENTORY §A still describes `demo.html` as the only consumer UI.

No legitimate remaining consumer-feature code gap was found that Sprint 29 can close without pulling Sprint 31–38 live research, Sprint 37 market policy, Sprint 39 support backend, or Sprint 44/45 visual/launch proof.

## Implementation performed here

- Current-status closeout matrix + `test_cc01_behavioral_matrix_is_complete`
- Cross-action affiliate-neutrality lock
- Status reconciliation to the verdict above
- GAP_INVENTORY / roadmap / staging-plan wording reconciliation

## Dependency-owned acceptance (do not pull into Sprint 29)

| Item | Owner |
|------|--------|
| Live merchant research / connector execution / updated Results | Sprints 31–38 |
| Live owner-bound Search → UUID snapshot | 31 routing + 38 execution |
| MarketContext / five-market / FX / live destination re-evaluation | 37 |
| Support ticket + analytics backends | 39 |
| Visual manifest pixel sign-off | 44 |
| Immutable launch-candidate CC-01 journey / EC-02 / EC-22 | 45 |
| Legal publication / counsel DSAR completeness | 28 / 44 / 45 |

## Staging requirement

Do **not** deploy from this PR.

Non-live-research checks that can run now against current staging, and should be re-run after a later Deploy Staging of the merged SHA:

1. `/login` `/register` `/reset-password` `/verify-email` `/account` `/support` 200 + noindex
2. Synthetic register → login → export → delete → `/me` 401
3. Guest owner cookie mint + unsigned/tampered rejection
4. Fixture-catalog Results / Compare / Why / Ask (authorized staging fixture only)
5. Ask evidence answer + optional refine on fixture decision
6. Propose/confirm only if a persisted conversation exists; expect execution-unavailable wording, never completed research
7. PH market shell + uncertified disclosure
8. `/robots.txt` staging `Disallow: /`; `/sitemap.xml` has no `/results/`
9. Canonical UUID routes stay `unavailable` with no fixture economics leak
10. `/privacy` `/terms` remain 404 while unpublished

Cannot be claimed on current staging: live Search → owner-bound UUID → confirmed live research → updated Results.

## Non-claims

- Live merchant research was not implemented or claimed.
- Merchants were not queried.
- Fixture products were not injected into real UUID flows.
- Canonical PiqScore, Recommendation, and Results authority were not replaced.
- The Phase 29.0 contract freeze was not weakened.
- Sprint 29 is not closed.

Machine-readable companion: [`../../../tests/contracts/fixtures/sprint29-internal-closeout-matrix.json`](../../../tests/contracts/fixtures/sprint29-internal-closeout-matrix.json)
