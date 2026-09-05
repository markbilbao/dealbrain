# Account deletion propagation checklist (Sprint 28.1)

**Status:** Engineering runbook — **not** a legal SLA, **not** a statutory completion window, **not** a backup-erasure claim.
**Endpoint:** `POST /api/v1/auth/account/delete`
**Confirmation:** Authenticated bearer session plus JSON `{"confirmation":"DELETE","password":"<current password>"}`.

## Immediate engineering behavior

On a valid authenticated request:

1. Reject unauthenticated requests (401).
2. Re-authenticate with the current password. Wrong password returns 401 and does not delete.
3. Reject unless `confirmation` is exactly `DELETE`.
4. Ignore any client-supplied `user_id`; ownership is the bearer session only.
5. Revoke all active sessions, then physically delete session rows.
6. Delete profile, preferences, settings, wishlist, favorites.
7. Delete saved products, comparisons, recommendation history, saved searches, recently viewed.
8. Delete password-reset and email-verification records for the user (consumed tokens become invalid).
9. Delete policy-acceptance records for the user (they are account-owned; remaining audit events may still exist).
10. Delete watchlists whose `owner_id` matches the user, when the watchlist store is wired.
11. Remove Notification Center preferences for the user, when that store is wired.
12. Delete the `User` row (email / display name / password hash gone from the live account store).
13. Append `account_deletion_requested` and `account_deleted` to the security audit log (retained).

Repeat delete with the same bearer token returns **401** (session and account are gone).

## Early Access waitlist (unresolved / separate)

Early Access registrations are a **separate data relationship**, not consumer User accounts. There is **no** `user_id` foreign key. Sprint 28.1 **does not** delete Early Access rows when an account is deleted, including when the waitlist email matches the account email. Whether that email match should later imply erasure is **counsel-owned** and not implemented. Operators continue to use the existing Early Access export runbook, which is not a consumer DSAR API.

## Not claimed deleted

| Store / process | Engineering truth |
|-----------------|-------------------|
| `user_platform.audit_events` | Retained (including `account_deleted`) |
| HTTP / application logs | Not purged |
| Database backups / snapshots | Not claimed erased |
| Transactional email provider copies | Not claimed erased |
| Guest browser cookies / `sessionStorage` | Client-side; this API does not clear another device |
| Shopping-assistant conversations | TTL-bound; no list-by-`user_id` purge on this path |
| Alert-rule rows in the alerts bounded context | Not cascaded by this endpoint |
| Legal hold / statutory retention exceptions | Counsel-owned; not encoded |

## Export

`GET /api/v1/auth/account/export` returns JSON schema `piqsavi.account_owned_export.v1` (`export_kind`: `account_owned_engineering_export`) for the authenticated user only. Completeness is checked against the engineering category list in [`ENGINEERING_PII_INVENTORY.md`](ENGINEERING_PII_INVENTORY.md) / `app/privacy/inventory.py`. This is an engineering account-data export of the current account-owned schema. It is **not** a complete legal DSAR and does **not** claim all PiqSavi or personal data.

## Persistence

`PolicyAcceptanceRecord` uses the existing Sprint 23 `operational_entities` table (`user_platform.consent_records` store). No new Alembic revision is required. Uniqueness is `uq_operational_store_secondary` on `{user_id}:{policy_type}:{version_id}`. `accepted_at` is stored in the JSON payload. Rows are owner-scoped and deleted with the account. Production/staging already migrate `operational_entities` via `d4e5f6a7b8c9`.

## Legal questions left open

Exact response deadlines, statutory retention exceptions, whether `privacy@piqsavi.com` alone satisfies law, and age-related delete/export rules remain counsel-owned.
