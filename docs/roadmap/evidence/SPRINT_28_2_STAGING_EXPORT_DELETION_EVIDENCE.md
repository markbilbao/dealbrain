# Sprint 28.2 — Staging Account Export / Deletion Evidence

**Document type:** Sanitized technical staging evidence  
**Sprint definition:** [`../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md)  
**Propagation checklist:** [`../../privacy/ACCOUNT_DELETION_PROPAGATION.md`](../../privacy/ACCOUNT_DELETION_PROPAGATION.md)  
**Packaging date (UTC):** 2026-09-05  
**Sprint 28 closure status:** **Open** — 28.2 staging export/delete HTTP evidence recorded. Counsel publication and EXT-20/21/22 remain open.

This package records a real staging run against the deployed Sprint 28.1 export/delete endpoints. It is **not** a complete legal DSAR, **not** a complete erasure certification, and **not** permission to publish legal policies.

---

## 1. Purpose and scope

**In scope**

- Confirm live staging is running the post-28.1 deploy
- Synthetic-account `GET /api/v1/auth/account/export` (`piqsavi.account_owned_export.v1`)
- Synthetic-account `POST /api/v1/auth/account/delete` with password re-auth and `confirmation=DELETE`
- Session invalidation of confirming and secondary sessions
- Other-user isolation
- Early Access separation via the supported waitlist API
- Bounded failure cases

**Out of scope**

- Publishing Privacy Policy, Terms, or cookie notice
- Changing EXT-19 / EXT-20 / EXT-21 / EXT-22
- Claiming backup, log, vendor, or statutory erasure
- Direct RDS / SSM row inspection (this Cloud Agent has no AWS operator credentials)

---

## 2. Staging identity and deployed SHA

| Field | Value |
|-------|--------|
| Environment | `staging` (`GET /health`) |
| HTTP hostname used | `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com` (documented staging ALB; `staging.piqsavi.com` still does not resolve) |
| HTTPS on ALB DNS | Not used (TLS handshake to the raw ALB DNS fails; HTTP probes succeeded) |
| `/health` status | `up`, `database=up`, `persistence_level=READY`, user-platform SQLAlchemy adapter |
| `/health` `started_at` | `2026-09-05T13:25:36.315986+00:00` |
| `/ready` | `200`, `ready=true`, `persistence_level=READY` |
| `/privacy` | `404` — no published policy |
| `/terms` | `404` — no published policy |
| Live OpenAPI | Contains `GET /api/v1/auth/account/export` and `POST /api/v1/auth/account/delete` |
| Deploy workflow | Deploy Staging **#26** |
| Deploy run | `33968814488` |
| Deploy branch | `main` |
| Deployed SHA | `ec7dd1dc3ecf788c191f3fa4d406962f1d7aa977` |
| Build Image run | `33968569122` (same SHA, success) |
| Host evidence artifact | `staging-evidence-rel-20260905T132006Z-ec7dd1dc3ecf-33968814488` |
| Evidence window (UTC) | `2026-09-05T13:35:00Z` – `2026-09-05T13:35:09Z` |

SHA correlation: Deploy Staging #26 `headSha` equals current `origin/main`. Live process `started_at` matches that deploy minute. Live OpenAPI now exposes the Sprint 28.1 routes that were absent on the previous 2026-08-18 host. `/health` does not itself print a git SHA.

Independent S3/SSM `DEPLOY_VERSION` confirmation was **not** available (no AWS CLI / credentials in this agent). That limitation does not reverse the HTTP + Actions correlation above.

---

## 3. Synthetic accounts

Fresh staging-only `@example.invalid` identities. No customer, owner, Early Access subscriber, or developer mailbox was used.

| Role | Email (normalized by auth) | Non-secret `user_id` |
|------|----------------------------|----------------------|
| Target (export + delete) | `sprint28-2-target-20260905t133500z-8992e2fa@example.invalid` | `3a2352e6-9c33-418f-84d4-f228297f76c5` |
| Isolation witness | `sprint28-2-other-20260905t133500z-8992e2fa@example.invalid` | `fa69f3c5-ed1c-410d-bc20-3789d651528c` |
| Body-retarget throwaway | `sprint28-2-attacker-20260905T133500Z-8992e2fa@example.invalid` | `1f09887f-32e8-4574-ae63-996680327592` |
| Query-retarget throwaway | `sprint28-2-qattack-20260905T133500Z-8992e2fa@example.invalid` | `f09a288c-9629-4c25-9c10-d82132147bee` |

Passwords and bearer tokens were generated in memory and are **not** recorded here.

Auth lowercases emails (documented). Marker string used for ownership checks: `sprint28-2-target-only-8992e2fa` vs `sprint28-2-other-only-8992e2fa`.

Consent was **not** seeded: `/privacy` and `/terms` are unpublished `404`. Registration `terms_accepted` / `privacy_acknowledged` flags were sent and must not create fake acceptance rows.

---

## 4. Seeded account-owned data (supported APIs)

| Operation | HTTP | Result |
|-----------|------|--------|
| `PUT /api/v1/profile` | 200 | Target profile/country/budget seeded |
| `PUT /api/v1/profile/preferences` | 200 | Preferences seeded |
| `POST /api/v1/user/saved-products` | 201 | Target-only product marker |
| `POST /api/v1/user/comparisons` | 201 | Target comparison |
| `POST /api/v1/user/searches` | 201 | Target search marker |
| `POST /api/v1/user/recently-viewed` | 200 | Target product viewed |
| `POST /api/v1/watchlists` | 200 | Target-owned watchlist |
| `PUT /api/v1/notification-preferences` | 200 | Notification-center prefs set |
| Other-user saved product | 201 | Isolation marker |
| `POST /api/v1/auth/password-reset` | 200 | Generic accepted body; `email_delivery=false`; no demo token |
| `POST /api/v1/auth/verify-email` | 200 | Same; no demo token |
| `POST /api/v1/auth/email-change` | 200 | Generic accepted body; no demo token |
| `POST /api/v1/early-access` (same email) | 200 | `outcome=success` |

`/health` reports `identity_email_adapter=null` and `identity_email_ready=false`. Reset / verify / email-change requests are enumeration-safe and do not return tokens in staging.

---

## 5. Export evidence

**Endpoint:** `GET /api/v1/auth/account/export`  
**Sanitized request:** `Authorization: Bearer <redacted>` only. No body.

| Check | Observed |
|-------|----------|
| HTTP | 200 |
| `export_schema` | `piqsavi.account_owned_export.v1` |
| `export_kind` | `account_owned_engineering_export` |
| Inventory categories present | account, profile, settings, wishlist, saved_products, saved_comparisons, recommendation_history, saved_searches, recently_viewed, consent_records, sessions, notification_preferences |
| Account identity | Target `user_id` + normalized target email + display name `Sprint282 Target Synthetic` |
| Target marker | Present in saved products and saved searches |
| Other-user email / marker | Absent |
| Early Access waitlist fields | Absent |
| `consent_records` | `[]` (no published policy) |
| Session metadata | 2 sessions; `session_id` / expiry / `remember_me` / `revoked` only |
| `password_hash` | Absent (no `pbkdf2_` material) |
| `token_hash` / `csrf_token` / `access_token` | Absent as keys; raw bearer tokens absent |
| Reset / verify / email-change tokens | Absent |
| Overclaim phrases | Absent (`all personal data`, `complete legal dsar`, `all piqsavi information/data`) |
| Other-user export | 200; other marker present; target email/marker absent |

This is an engineering account-owned export of the current schema. It is **not** a complete legal DSAR and does **not** claim all PiqSavi or personal data.

---

## 6. Deletion evidence

**Endpoint:** `POST /api/v1/auth/account/delete`  
**Sanitized request shape:** authenticated bearer + `{"confirmation":"DELETE","password":"<redacted>"}`. No trusted client `user_id`.

| Field | Observed |
|-------|----------|
| HTTP | 200 |
| `status` | `deleted` |
| Returned `user_id` | `3a2352e6-9c33-418f-84d4-f228297f76c5` (server-derived target; not the isolation witness) |
| `sessions_revoked` | 2 |
| `sessions_deleted` | 2 |
| `watchlists_deleted` | 1 |
| `notification_preferences_removed` | true |
| `consent_records_deleted` | 0 (none existed) |
| Overclaim phrases | Absent |
| Retained-limitation text | Present (audit, logs, backups, vendor copies, Early Access, guest storage, shopping-assistant, alert-rules, counsel-owned holds) |

### HTTP state verification (no RDS session)

| Check | Method | Result |
|-------|--------|--------|
| User row removed | Login with deleted email → 401; re-register same email → 201 with new `user_id` `ea462fa0-c917-4923-8c0c-a61cde17d557` | Pass |
| Profile / settings / saved items | Pre-delete export contained them; post-delete export with old bearer → 401; isolation export has no target marker | Pass (HTTP-inferred) |
| Sessions revoked/deleted | Confirming `/me` 401; secondary `/me` 401; delete counts 2/2 | Pass |
| Watchlist | Create 200; delete reports `watchlists_deleted=1` | Pass (count + ownership API) |
| Notification-center prefs | Seeded 200; delete reports `notification_preferences_removed=true` | Pass (API-reported) |
| Consent rows | Empty export; `consent_records_deleted=0` | Consistent; no published policy |
| Reset / verify / email-change rows | Requests accepted without tokens; no consumer read API; no RDS | **Not independently row-proven** |
| Isolation witness | Other `/me` 200; other export still has other marker only | Pass |
| Repeat delete | 401 | Pass |
| Re-registered residue | Immediately deleted (`cleanup` 200) | Cleaned |

---

## 7. Session evidence

| Session | Before delete | After delete |
|---------|---------------|--------------|
| Confirming (register token) | `/me` 200 | `/me` 401; export 401 |
| Secondary (login token) | `/me` 200 | `/me` 401 |
| Isolation witness | `/me` 200 | `/me` 200; export 200 |

HTTP 200 from delete alone was not treated as sufficient.

---

## 8. Early Access separation

Supported `POST /api/v1/early-access` with the target synthetic email:

| When | HTTP | `outcome` |
|------|------|-----------|
| Before account delete | 200 | `success` |
| After account delete | 200 | `already_registered` |

The waitlist row using the same email was **not** treated as the User account and was **not** silently deleted. Early Access residue remains by design.

---

## 9. Failure cases

| Case | HTTP | Side effect |
|------|------|-------------|
| Unauthenticated export | 401 `Missing session token.` | None |
| Unauthenticated delete | 401 `Missing session token.` | None |
| Wrong password | 401 `Invalid credentials.` | Target `/me` still 200 |
| Wrong confirmation | 400 `confirmation='DELETE'` | Target `/me` still 200 |
| Body `user_id` retarget | 200 deletes **caller** `1f09887f-…`, not target | Target `/me` 200 |
| Query `?user_id=` retarget | 200 deletes **caller** `f09a288c-…`, not target | Target and isolation witness `/me` 200 |

---

## 10. Retained / unresolved (unchanged)

Do **not** treat these as deleted:

- `user_platform.audit_events` (including `account_deleted`)
- HTTP / application logs
- Database backups / snapshots
- Third-party transactional email copies
- Guest cookies / `sessionStorage`
- Shopping-assistant conversations
- Alert-rule rows in the alerts bounded context
- Statutory / legal holds (counsel-owned)
- Early Access waitlist (proven retained for this email)

Reset / verify / email-change **row** deletion is implemented in 28.1 but was not independently inspected in staging RDS.

---

## 11. External dependency truth

Unchanged by this evidence:

| ID | Status |
|----|--------|
| EXT-19 | `applied` — written approval still absent |
| EXT-20 | `not_started` |
| EXT-21 | `not_started` |
| EXT-22 | `not_started` |

---

## 12. Residue

| Item | Status |
|------|--------|
| Target User account | Deleted; re-registered twin also deleted |
| Body/query retarget throwaways | Deleted by the retarget tests |
| Isolation witness User | Still present (`fa69f3c5-…` / `sprint28-2-other-…@example.invalid`) |
| Early Access row for target email | Intentionally retained |
| Passwords / tokens | Not retained in this package |

---

## 13. Limitations

1. No AWS/SSM/S3 operator access from this Cloud Agent; deployed SHA is correlated from Actions + live `started_at` + OpenAPI, not a host `DEPLOY_VERSION` file.
2. No direct SQL verification of user/profile/session/token/consent tables.
3. Identity email adapter is `null` on this host; token-row lifecycle cannot be confirmed via delivered mail or demo tokens.
4. `/api/v1/auth/meta` still reports `persistence=memory` while `/ready` reports SQLAlchemy. Known honesty gap; `/ready` remains the persistence authority used here.
5. This does not close Sprint 28.

---

## 14. Conclusion

**SPRINT 28.2 STAGING EVIDENCE COMPLETE — READY FOR OWNER REVIEW**

Verified against deployed SHA `ec7dd1dc3ecf788c191f3fa4d406962f1d7aa977` (Deploy Staging #26). Sprint 28 remains open.
