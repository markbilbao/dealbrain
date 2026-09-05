# Sprint 29 Closeout Gap Audit

**Audit baseline:** `4da3947d63f2c325996e2974070d57db8175dc6d` (`origin/main` at start)  
**Working branch:** `cursor/sprint-29-closeout-staging-e2e-2241`  
**Date (UTC):** 2026-09-05  
**Sprint status after this work:** implementation gaps that Sprint 29 owns are closed in code; staging E2E on an immutable current-main deploy remains pending. Sprint 29 is **not closed**.

This audit was produced by reading the locked sprint definition against the live tree. Older reports were not treated as proof.

## Verdict

`SPRINT 29 IMPLEMENTATION READY — STAGING EVIDENCE PENDING`

- Sprint 29 conversational contract is complete in code (proposal → confirmation → authorized request).
- Live research execution remains owned by Sprints 31–38 and is not faked here.
- Staging E2E cannot be claimed against current-main until a new deploy proves SHA `4da3947` or a later merged SHA. Deploy Staging #26 proved `ec7dd1dc`, which is an ancestor, not this closeout revision.

## Acceptance matrix

| Sprint 29 acceptance criterion | Evidence on main before this branch | Status after this branch | Exact file / test / route | Smallest required action |
|---|---|---|---|---|
| Registration / login / recovery / verification presentation | Auth APIs only; email templates linked to missing HTML | complete | `/login` `/register` `/reset-password` `/verify-email`; `app/consumer/account_pages.py`; `tests/unit/test_sprint29_account_pages.py` | Staging synthetic journey after deploy |
| Account settings, sign-out, email/status | No consumer HTML | complete | `/account`; `app/static/consumer/js/account.js` | Staging session proof |
| Deletion / export UI wired to Sprint 28 APIs | APIs + 28.2 HTTP evidence; no UI | complete | `/account#export` `/account#delete` → `GET/POST /api/v1/auth/account/export\|delete` | Staging UI+API after current-main deploy |
| Feedback / support entry points | Missing | complete (stub) | `/support`; mailto `support@piqsavi.com` | Sprint 39 owns ticket/analytics backend |
| Search → Results → PiqScore → Recommendation → explanation → merchant redirect | Product Foundation merged; `/search` still fixture-or-unavailable | complete for presentation; live creation externally blocked | `/search`, `/results/{id}`, `/compare/{id}`, `/why-best-piq/{id}` | Live owner-bound creation is Sprint 31/38 |
| Loading / empty / error / timeout / partial / stale / unsupported | Partial Product Foundation states | partial | `app/consumer/pages.py`, `consumer.js` | Remaining research execution states owned by Sprint 38 |
| Market-selection UI shell | Coverage banner only | complete | `.market-shell` → `POST /consumer/shopping-market`; `tests/unit/test_sprint29_market_selection_shell.py` | Sprint 37 owns five-market policy |
| Save vs Watch distinction | Header both pointed at `/`; copy promised price updates | complete | `/account#saved` `/account#watch`; save-prompt copy | Watch monitoring remains later sprints |
| CC-01 1–2 architecture / sole authority | merged | complete | Conversation + snapshot repos; 29.0–29.3 tests | None |
| CC-01 3 search creates server-owned snapshot | Fixture redirect / production unavailable | externally blocked | `app/api/consumer.py` | Sprint 31 routing + 38 execution |
| CC-01 4–9 evidence / refine / propose / no silent research | merged unit/service tests | complete (code) | 29.4A/B/C tests | Staging guest journey pending |
| CC-01 10 confirmation idempotent; starts one execution | Authorization idempotent; execution unavailable | complete for Sprint 29 contract; execution externally blocked | `test_research_authorization_handoff.py` | Sprint 38 live executor |
| CC-01 11–13 execution-backed status / updated Results | Truthful unavailable state only | externally blocked | `research_confirmation_received_but_execution_unavailable` | Sprint 38 |
| CC-01 14–16 evaluated-set / iPhone-Samsung / turn history | merged | complete | `sprint29-context-drift.json`; persistence tests | None |
| CC-01 17 guest continuity | Persistence/TTL/CAS; no HTML cookie mint | complete for cookie + persistence | `ensure_guest_owner_cookie`; `test_sprint29_guest_claim.py` | Staging close/reopen |
| CC-01 18 guest→auth | Repo `rebind_owner` only | complete for fixture conversations; UUID snapshots immutable | `POST /consumer/claim-decision` | Do not mutate snapshot owners |
| CC-01 19 affiliate neutrality | Engine + refine/auth tests | complete (no weakening) | Product Foundation disclosure + closeout lock test | None |
| CC-01 20 visual manifest match | CSS/HTML present; no pixel QA | partial | Product Foundation pages; Sprint 44 verifies artwork | Sprint 44 visual sign-off |
| CC-01 21 Ask 80px / 72px | CSS tokens; test did not lock px | complete | `test_ask_insertion_heights_match_manifest` | None |
| CC-01 22 a11y | Partial HTML | complete for required slice | `test_sprint29_accessibility.py` | Signed checklist still owner review |
| CC-01 23 ≥20 CC tests | 158 functions; traceability still planned | complete on count; matrix not flipped | existing 29.0–29.4C suites | Do not weaken traceability freeze |
| CC-01 24 staging journey on launch digest | missing | incomplete / blocked | this plan | Owner merge + current-main staging deploy |
| SEO: semantic HTML, metadata, robots, sitemap, canonical, noindex | UUID noindex only | complete for Sprint 29 foundation | `/robots.txt` `/sitemap.xml`; `app/consumer/seo.py` | GSC is Sprint 39/45 |
| UUID Results/Compare/Why noindex | merged Sprint 28.1 | complete | `test_sprint28_1_index_privacy.py` | None |
| Staging pages non-indexable | landing always indexable | complete | staging `Disallow: /` + landing noindex | None |
| PiqSavi brand / tagline / no DealBrain in consumer UI | mostly complete | complete | public brand tests + new account pages | PWA icons reuse approved logo; dedicated favicon pack still asset-limited |
| Live merchant research not claimed | locked | complete | closeout lock test | Do not start Sprint 38 here |

## Gaps found (before implementation)

1. No consumer HTML for register/login/recovery/verify/settings/export/delete/sign-out.
2. No market-selection UI shell.
3. No robots/sitemap/canonical/staging-noindex infrastructure.
4. Ask overlay missing Escape, focus trap, live region, safe-area, keyboard inset.
5. Save/Watch copy promised notifications.
6. No support/feedback entry.
7. Guest owner cookie never minted; guest→auth HTTP claim missing.
8. Missing journey map, a11y checklist, browser matrix, 29-vs-37 ownership note, staging plan.

## Explicitly not implemented here

- Live merchant research or Sprint 38 execution
- Merchant certification / Sprint 32–36
- Live FX / destination re-evaluation (Sprint 37)
- Legal policy publication (Sprint 28/44/45)
- Support ticket backend (Sprint 39)
- Security program (Sprint 40)
- New frontend framework
