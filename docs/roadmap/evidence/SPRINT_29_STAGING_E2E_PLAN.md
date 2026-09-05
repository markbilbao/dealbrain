# Sprint 29 Staging E2E Plan

**Do not run this plan against an unmerged branch.**  
**Do not claim current-main staging until a new Deploy Staging run proves the merged SHA.**

## Current staging truth

| Field | Value |
|---|---|
| Last proven staging SHA | `a8bd00190bb0b6baf256eb235043804f44858a70` (Deploy Staging #27, run `33996684250`) |
| Build Image | #92 / run `33978081429` (same SHA, SUCCESS) |
| Closeout audit start SHA | `4da3947d63f2c325996e2974070d57db8175dc6d` |
| Sprint 29 merged closeout | PR #111 merged to `main` at `a8bd001` |
| Sprint 29 staging E2E package | [`SPRINT_29_STAGING_CC01_EVIDENCE.md`](SPRINT_29_STAGING_CC01_EVIDENCE.md) — **partial**; live research still Sprint 38 |
| Sprint 28.2 export/delete HTTP | re-proven on Deploy #27 with synthetic `@example.invalid` accounts |
| Identity email adapter on that host | not claimed ready; reset/verify pages do not display demo tokens |
| `/privacy` `/terms` | 404 |

## Preconditions

1. Owner merges this PR (or a successor) to `main`. **Done — PR #111 → `a8bd001`.**
2. Build Image + Deploy Staging succeed on that exact `main` SHA. **Done — Build Image #92, Deploy Staging #27.**
3. Record workflow run id, image digest, `/ready`, and `/health`. **Recorded in the CC-01 evidence package.**
4. Use only synthetic `@example.invalid` accounts.

## Synthetic journey

1. Guest `/search` → Results (fixture catalog is allowed on staging; production unavailable mode is separate).
2. Compare → Why → Ask PiqSavi.
3. Evidence-bound follow-up, then a second follow-up.
4. Optional refinement; confirm canonical PiqScore bytes unchanged if a snapshot exists.
5. Optional research proposal → explicit confirmation → execution-unavailable wording. Do not manufacture completed research.
6. Register or login with `next=` back to the active decision.
7. Confirm conversation/decision continuity for fixture conversations; UUID snapshot owners stay immutable.
8. `/account` → export UI/API → delete UI/API → post-delete `/me` 401.
9. Isolation: second synthetic account cannot read the first decision UUID.
10. Logout + `/account/clear-device` does not leave the previous owner cookie.
11. Unsupported/uncertified market disclosure never presents fixture economics as live.
12. UUID Results/Compare/Why keep `X-Robots-Tag: noindex, nofollow`.
13. Keyboard / Escape / Ask dock smoke on one mobile-width viewport.

## Blocked even after UI deploy

| Item | Owner |
|---|---|
| Live research execution / updated Results | Sprint 38 |
| Real inbox reset/verify | Sprint 27 |
| Published Privacy/Terms | Sprint 28 / 44 / 45 |
| Support ticket backend | Sprint 39 |
| Search Console | Sprint 39 / 45 |

## Evidence package to file after the deploy

Create `docs/roadmap/evidence/SPRINT_29_STAGING_CC01_EVIDENCE.md` with sanitized synthetic ids, HTTP codes, and the proven SHA. Do not store passwords or bearer tokens.
