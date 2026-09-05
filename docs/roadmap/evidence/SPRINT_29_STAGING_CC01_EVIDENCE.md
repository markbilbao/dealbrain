# Sprint 29 — Staging CC-01 / Consumer Journey Evidence

**Document type:** Sanitized technical staging evidence  
**Sprint definition:** [`../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md`](../sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md)  
**Plan:** [`SPRINT_29_STAGING_E2E_PLAN.md`](SPRINT_29_STAGING_E2E_PLAN.md)  
**Packaging date (UTC):** 2026-09-05  
**Sprint 29 closure status:** **Open** — Deploy Staging #27 consumer/account/SEO/ownership evidence recorded. Live research execution and a full live canonical-UUID journey remain Sprint 38 (and supporting Sprint 31) work. Legal publication remains unpublished.

This package records a real staging run against the owner-approved, merged, and deployed SHA. It is **not** a live-research close, **not** a legal-policy publication, **not** a third-party accessibility certification, and **not** permission to start Sprint 38.

---

## 1. Purpose and scope

**In scope**

- Confirm live staging is the authorized Deploy Staging #27 host
- Sprint 29 HTML routes, unpublished-policy behavior, SEO/noindex, PH market shell
- Synthetic `@example.invalid` register / login / account / export / delete / sign-out
- Guest owner-cookie minting and rejection of unsigned/tampered cookies
- Account-session revocation and post-delete invalidation
- Fixture-catalog Results / Compare / Why / Ask surfaces that staging already permits
- Truthful unavailable behavior for canonical UUID routes that have no live snapshot

**Out of scope**

- Re-implementing Sprint 29
- Enabling extra fixture catalogs or seeding merchant research
- Claiming Search → live Results or research execution
- Publishing Privacy / Terms
- Owner, customer, Early Access, or developer identities
- Storing passwords, bearer tokens, raw owner cookies, session secrets, `APP_SECRET_KEY`, or database credentials

---

## 2. Repository and deployment provenance

| Field | Value |
|-------|--------|
| Evidence branch | `cursor/sprint-29-staging-e2e-evidence-2241` (documentation only) |
| `origin/main` at evidence time | `a8bd00190bb0b6baf256eb235043804f44858a70` |
| Merge | PR #111, owner-approved |
| Environment | `staging` (`GET /health`) |
| HTTP hostname used | `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com` (documented staging ALB; `staging.piqsavi.com` still does not resolve) |
| HTTPS on ALB DNS | Not used (TLS handshake to the raw ALB DNS fails; HTTP probes succeeded) |
| `/live` | `200` `{status: up, live: true, service: PiqSavi}` |
| `/ready` | `200`, `ready=true`, `persistence_level=READY` |
| `/health` | `200`, `status=up`, `environment=staging` |
| `/health` `started_at` | `2026-09-05T22:43:39.919658+00:00` |
| Deploy workflow | Deploy Staging **#27** |
| Deploy run | `33996684250` — SUCCESS — [Actions](https://github.com/markbilbao/dealbrain/actions/runs/33996684250) |
| Deployed SHA | `a8bd00190bb0b6baf256eb235043804f44858a70` |
| Build Image | **#92** / run `33978081429` — SUCCESS — same SHA |
| Deploy Staging also completed | release-manifest validation, staging OIDC identity check, staging target resolution, immutable bundle validation, SSM deployment, authoritative host evidence collection/validation, staging evidence artifact upload |
| Evidence window (UTC) | `2026-09-05T22:49:27Z` – `2026-09-05T22:51:00Z` |

SHA correlation: Deploy Staging #27 `headSha` equals current `origin/main`. Live process `started_at` matches that deploy minute. This document does **not** infer the deploy SHA from `/health` alone.

Independent S3/SSM `DEPLOY_VERSION` confirmation was **not** available (no AWS operator credentials in this agent). That limitation does not reverse the Actions + `/health` correlation above.

---

## 3. Synthetic accounts

Fresh staging-only `@example.invalid` identities. No owner, customer, Early Access subscriber, or developer mailbox was used.

| Role | Email (normalized by auth) | Non-secret `user_id` |
|------|----------------------------|----------------------|
| Target (register → login → export → logout → relogin → delete) | `sprint29-e2e-target-20260905T224927Z-d2c2b415@example.invalid` | `b912529d-2a1d-43ae-a3d7-6155de448a24` |
| Isolation witness (register only) | `sprint29-e2e-other-20260905T224927Z-d2c2b415@example.invalid` | `0d1ea615-4dd0-4183-83b4-6320d12b2ce1` |

Passwords, bearer tokens, cookies, and raw session values were generated in memory and are **not** recorded here.

Registration submitted `terms_accepted=false` and `privacy_acknowledged=false`. That must not create fake acceptance of unpublished policies.

---

## 4. Live route verification

| Path | HTTP | Notes |
|------|------|-------|
| `/live` | 200 | `status=up`, `live=true`, `service=PiqSavi` |
| `/ready` | 200 | `READY` |
| `/health` | 200 | `environment=staging` |
| `/openapi.json` | 200 | register, login, export, delete, Ask present. `POST /consumer/claim-decision` is `include_in_schema=False` (OpenAPI `has_claim=false` is expected) |
| `/` | 200 | PiqSavi brand; no DealBrain; staging noindex |
| `/login` `/register` `/reset-password` `/verify-email` `/account` `/support` | 200 | `X-Robots-Tag: noindex, nofollow`; meta noindex |
| `/robots.txt` | 200 | `User-agent: *` / `Disallow: /` + noindex |
| `/sitemap.xml` | 200 | public root only (`https://piqsavi.com/`); no `/results/` |
| `/privacy` `/terms` | **404** | unpublished |
| `/search?q=headphones` | 303 | `/results/headphones-standard` — **authorized staging fixture catalog**, not live research |
| `/results/headphones-standard` `/compare/headphones-standard` `/why-best-piq/headphones-standard` | 200 | `data-presentation-mode=fixture`, `non_live_contract_fixture`, noindex |
| `/results/{canonical-uuid}` `/compare/{canonical-uuid}` `/why-best-piq/{canonical-uuid}` | 200 | `data-presentation-mode=unavailable`; no fixture economics leaked |

Sprint 29 routes exist on this host. Search → Results on staging is the existing fixture-catalog permission, not a Search → live researched decision.

---

## 5. Account journey

| Step | Observed |
|------|----------|
| `GET /register` | No Terms/Privacy required checkboxes; `data-legal-unpublished="true"`; copy states policies are unpublished and registration will submit `terms_accepted=false` / `privacy_acknowledged=false` |
| `POST /api/v1/auth/register` with unpublished flags false | **201**; target `user_id` minted; session present (token omitted from evidence) |
| Witness register | **201**; distinct `user_id` |
| `GET /api/v1/auth/me` after register | **200**; `email_verified=false` |
| `POST /api/v1/auth/login` | **200**; session present |
| `/account` copy | Export is `piqsavi.account_owned_export.v1` and **not** a complete legal DSAR; deletion requires password + `DELETE` and does **not** claim backup/log/vendor erasure; Watch unavailable; Save ≠ Watch |
| `GET /api/v1/auth/account/export` | **200**; schema `piqsavi.account_owned_export.v1`; bounded engineering export |
| Delete with confirmation `"please"` | **400** |
| `POST /api/v1/auth/logout` | **204**; subsequent `/me` **401**; stale claim **401** |
| Relogin then `POST /api/v1/auth/account/delete` with `confirmation=DELETE` | **200**; `status=deleted`; `sessions_revoked=2`; `/me` **401**; stale claim **401** |
| `/reset-password` `/verify-email` | Request forms present; copy states identity email is sent only when the adapter is available and **does not display demo tokens** |
| Identity email delivery | Not claimed. Sprint 27 still owns real inbox reset/verify |

---

## 6. Unpublished-policy / legal evidence

| Check | Observed |
|-------|----------|
| `/privacy` | 404 |
| `/terms` | 404 |
| Registration HTML required acceptance boxes | Absent |
| Registration “I accept / I agree” | Absent |
| Registration unpublished marker | `data-legal-unpublished="true"` |
| Live `account.js` | Queries for legal checkboxes and does **not** force `true` when boxes are absent |
| Register API with both flags false | 201 |
| Account privacy copy | Consent stored only when a published policy version exists |

No unavailable policy acceptance was fabricated. Legal publication is **not** complete.

---

## 7. Guest / account ownership evidence

Observed **without** recording cookie values, HMAC material, or bearer tokens.

| Check | Observed |
|-------|----------|
| Guest owner credential minted | `Set-Cookie: piqsavi_decision_owner=v1.…` on fixture Results |
| Cookie flags | **HttpOnly**, **Secure**, **SameSite=lax**, signed `v1.` prefix; not unsigned JSON |
| Staging Secure flag | Present (correct for HTTPS staging) |
| HTTP ALB cookie jar | Browsers/httpx will **not** persist a `Secure` cookie on `http://` ALB DNS. Guest→account claim via automatic cookie jar returned `missing_guest_owner`. This is an environment/TLS gap, not authorization weakening |
| Unsigned / tampered cookie on UUID `00000000-0000-4000-8000-000000000041` | Pages remain `unavailable`; no fixture price/product leak |
| Valid guest cookie + same UUID | Still `unavailable` — **no live snapshot exists** on this host |
| `POST /account/clear-device` | 200; owner cookie deleted (`Max-Age=0`) |
| Logout revocation | Confirming bearer `/me` 401; claim with revoked session 401 even if a browser cookie is left in place |
| Deleted account | Confirming `/me` 401; stale claim 401 |
| Guest→account claim on a persisted conversation | Not proven on this host: fixture Ask returned `conversation_id=null`; explicit claim after replay reported `conversation_not_found` |

Account-owned decision authorization therefore depends on an authoritative session for account cookies, and on a signed guest cookie for guest cookies. A live account-owned canonical UUID snapshot was **not** available to replay a stale account owner cookie against a real Results page.

---

## 8. Results / Compare / Why

Fixture catalog `headphones-standard` is the existing authorized staging test architecture. It is classified `non_live_contract_fixture` and **must not** be described as live research.

| Surface | HTTP | Privacy | Mode | Ask / PiqScore |
|---------|------|---------|------|----------------|
| `/results/headphones-standard` | 200 | `X-Robots-Tag: noindex, nofollow` | fixture | PiqScore present; Ask dock + overlay |
| `/compare/headphones-standard` | 200 | noindex header + meta | fixture | same |
| `/why-best-piq/headphones-standard` | 200 | noindex header + meta | fixture | same |
| Canonical UUID Results/Compare/Why | 200 | noindex header + meta | **unavailable** | no fixture economics |

Canonical PiqScore immutability, evaluated-set stability, and foreign-owner isolation on a **live** snapshot cannot be proven until Sprint 38 (or an already-authorized live decision) creates an owner-bound UUID. On the fixture path, Ask refinement copy stated PiqScores remain unchanged and the historical Recommendation remains.

Search → live Results is **not** claimed.

---

## 9. Ask / conversational continuity

Endpoint exercised: `POST /api/v1/shopping-assistant/query` with `decision_id=headphones-standard`.

| Turn | HTTP | Action | `conversation_id` | Notes |
|------|------|--------|-------------------|-------|
| Evidence-bound “why Sony” | 200 | `answer_from_evidence` | absent | `data_status=mock`; Sony Best Piq explanation from captured fixture evidence; no “research complete” |
| Second question without a stored conversation | 200 | `answer_from_evidence` | absent | Answers again from fixture evidence; **no persisted conversation** |
| Preference refine (“quieter / travel”) | 200 | `refine_session_recommendation` | absent | `recommendation_changed=false`; copy says historical Recommendation remains and PiqScores are unchanged |
| Research-worded “research more brands / research complete” | 200 | `answer_from_evidence` | absent | No research proposal; no confirmation chip; **no** “research complete”; `execution_available` not true |

**Implemented and unit-tested (not re-opened here):** proposal → explicit confirmation → `research_confirmation_received_but_execution_unavailable`.

**Not proven on this live host:** a persisted `conversation_id`, a second follow-up bound to that conversation, owner-isolated Ask history, or an explicit research-proposal confirmation that reports execution unavailable.

Distinction required by this closeout:

- `Sprint 29 conversational contract implemented and tested`
- `full live staging research journey blocked on Sprint 38`

No fake “research complete” was observed. No live researched decision was manufactured.

---

## 10. Market / location

| Check | Observed |
|-------|----------|
| Market shell | Present on fixture Results; `<select name="country_code">` Philippines / `PH` |
| `POST /consumer/shopping-market` `country_code=PH` | 303 → `/results/headphones-standard`; `Set-Cookie: piqsavi_shopping_market` (HttpOnly, SameSite=lax; Secure not set by this cookie helper) |
| Results with explicit PH cookie | `data-selected-shopping-market=PH`, `data-shopping-market-origin=explicit`, `data-shopping-market-certified=false` |
| Unsupported market fixture fallback | No `value="US"` option; no certified-coverage claim |
| Location dialog | `/results/headphones-standard?prompt=1` opens `#location-dialog` with Skip |
| `GET`/`POST /consumer/location?action=skip` | 303 → Results; `piqsavi_delivery` cookie minted (HttpOnly, SameSite=lax) |

PH remains the intended product default, not a certified shopping market. Sprint 37 still owns certified-market policy.

---

## 11. SEO / noindex / canonical

| Surface | Evidence |
|---------|----------|
| Staging global | `/robots.txt` `Disallow: /`; landing + account/auth/support + decision pages send `X-Robots-Tag: noindex, nofollow` and meta noindex |
| Home canonical | Absent on staging (production canonical is not emitted on this host) |
| Home JSON-LD | Present |
| Sitemap | Only `https://piqsavi.com/`; no private `/results/` UUIDs or fixture catalogs |
| UUID private pages | noindex |
| Account / auth / support | noindex |

Search Console remains Sprint 39 / 45.

---

## 12. Accessibility / browser evidence

Not a third-party accessibility certification.

| Check | How proven |
|-------|------------|
| Skip link, `<main>`, labeled forms | Live HTML on register, account, Results/Compare/Why |
| Ask overlay `role="dialog"`, `aria-live` | Live Compare/Why HTML |
| Escape closes Ask / location | Live `/static/consumer/js/consumer.js` contains `initDialogEscape` |
| Focus trap | Same file traps Tab inside `.ask-panel` |
| Ask dock height | Live `/static/consumer/css/piqsavi.css` `--ask-h: 80px` desktop and `--ask-h: 72px` mobile |
| Register required fields | Display name / email / password only; legal boxes absent |

Interactive keyboard/focus/Escape in a real browser on this ALB is limited by `http://` + `Secure` owner cookies and by the lack of a live UUID snapshot. HTML/CSS/JS locks above were verified on the deployed host. The browser-matrix lab pass is still not a signed a11y audit.

---

## 13. External dependency boundary

| Dependency | Owner | Staging truth |
|------------|-------|----------------|
| Live merchant research / updated Results | Sprint 38 (Sprint 31 routing) | Not present. Fixture catalog is the authorized non-live path |
| Canonical live UUID snapshot creation | Sprint 31 / 38 | UUID routes render truthful `unavailable` |
| Persisted Ask `conversation_id` on a live decision | Sprint 29 contract + live snapshot | Fixture Ask answers without persisting a conversation |
| Real inbox reset / verify | Sprint 27 | Presentation truthful; delivery not claimed |
| Published Privacy / Terms | Sprint 28 / 44 / 45 | Remain 404 |
| Support ticket backend | Sprint 39 | Mailbox identities only |
| HTTPS hostname for Secure cookies | Staging TLS / DNS | Raw ALB is HTTP; `Secure` owner cookie attributes are still correct |

These are **not** treated as Sprint 29 implementation defects.

---

## 14. Defects found

None that require a Sprint 29 production-code stop.

Environment / later-sprint gaps recorded above (HTTP ALB vs Secure cookie; no live UUID snapshot; fixture Ask has no `conversation_id`; research proposal/confirmation not reached on the fixture path).

---

## 15. Verdict

`SPRINT 29 STAGING E2E PARTIAL — LIVE RESEARCH DEPENDENCY REMAINS`
