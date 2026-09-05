# Sprint 29 UI Journey Map

**Owner:** Sprint 29  
**Baseline:** closeout audit on `4da3947` plus this branch  
**Not a close:** staging E2E is still required on an immutable current-main deploy.

## Public entry

1. `/` Early Access landing (public; noindex on staging).
2. `/search?q=` redirects to a fixture catalog in development/staging, or `/results/unavailable` in production.
3. `/support` publishes mailbox identities only. Sprint 39 owns in-product tickets.

## Decision journey

Search / catalog entry  
→ `/results/{decision_id}`  
→ Compare `/compare/{decision_id}`  
→ Why `/why-best-piq/{decision_id}`  
→ Ask PiqSavi (top insert + dock + overlay/sheet)  
→ evidence-bound follow-up  
→ optional session Recommendation refinement  
→ optional research proposal  
→ explicit “Yes, research that” confirmation  
→ truthful `research_confirmation_received_but_execution_unavailable`  
→ outbound `View offer` when a captured URL exists (`rel="nofollow noopener"`)

Ask remains available on Results, Compare, and Why after Recommendation.

## Account journey

`/register` or `/login` with `?next=/results/{id}`  
→ Sprint 27 auth APIs  
→ `POST /consumer/claim-decision` (guest conversation rebind when safe)  
→ `/account`  
→ export (`GET /api/v1/auth/account/export`)  
→ delete (`POST /api/v1/auth/account/delete`)  
→ sign-out + `/account/clear-device`  
→ `/reset-password` and `/verify-email` presentation (delivery depends on Sprint 27 email adapter)

## Continuity rules

- Guest owner cookie `piqsavi_decision_owner` is minted on decision HTML if absent.
- Conversation id stays in `sessionStorage` key `piqsavi_ask_conversation`.
- UUID snapshot owners are immutable; claim will not hide a UUID decision by rotating the cookie.
- Foreign accounts cannot read another owner’s UUID snapshot.
- Save ≠ Watch. Watch is disclosed as unavailable.
- Affiliate economics stay post-selection.

## Unavailable / honest states

| State | Current truthful behavior |
|---|---|
| Production fixture catalog | `/results/unavailable`; no fixture offers |
| Unpublished legal pages | `/privacy` `/terms` 404 |
| Identity email | Request accepted; demo tokens not shown in UI |
| Live research | Confirmation does not execute |
| Watch / notifications | Not available |
| Support ticket API | Not available (Sprint 39) |
