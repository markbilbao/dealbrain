# Sprint 29 Staging E2E Plan

**Do not run this plan against an unmerged branch.**  
**Do not claim current-main staging until a new Deploy Staging run proves the merged SHA.**

## Current staging truth

| Field | Value |
|---|---|
| Last proven staging SHA | `ec7dd1dc3ecf788c191f3fa4d406962f1d7aa977` (Deploy Staging #26) |
| Closeout audit start SHA | `4da3947d63f2c325996e2974070d57db8175dc6d` |
| Sprint 28.2 export/delete HTTP | recorded; APIs present on that host |
| This closeout UI | **not** on `ec7dd1dc` |
| Identity email adapter on that host | `null` / not ready |
| `/privacy` `/terms` | 404 |

## Preconditions

1. Owner merges this PR (or a successor) to `main`.
2. Build Image + Deploy Staging succeed on that exact `main` SHA.
3. Record workflow run id, image digest, `/ready`, and `/health`.
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
