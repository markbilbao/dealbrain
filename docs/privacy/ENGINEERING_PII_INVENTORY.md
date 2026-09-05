# Engineering PII inventory (Sprint 28.1)

**Status:** Engineering inventory — **not** a published Privacy Policy, **not** legal advice, **not** a completeness certification.
**Baseline:** `origin/main` `68664c44d615fb28bb03b5a72868a977b2c5cb8f` plus Sprint 28.1 code on this branch.
**Counsel-owned:** statutory categories, retention exceptions, DPA roles, age rules, public legal wording.

This inventory records **repository-evidenced** personal and related data. Classifications such as “essential/functional” are product-architecture labels, not legal opinions. Consumer export uses schema `piqsavi.account_owned_export.v1` and is an engineering account-owned export, not a complete legal DSAR.

## Account-attributable stores (export/delete in scope)

| Category | Fields (engineering) | Location | Retention / TTL | Deletion (28.1) | Export (28.1) | Architecture note |
|----------|----------------------|----------|-----------------|-----------------|---------------|-------------------|
| Account | `user_id`, `email`, `display_name`, `is_active`, `email_verified`, timestamps, `data_status`. Password stored as `password_hash` only | `user_platform.users` | No privacy retention policy | User row deleted | Included **without** `password_hash` | |
| Sessions | `session_id`, `user_id`, expiry, `remember_me`, `user_agent`, `ip_hint`, `revoked`. Raw token never stored | `user_platform.sessions` | TTL 1h default / 30d remember-me | Revoked then physically deleted | Metadata only; no `token_hash` / `csrf_token` | Bearer auth, not cookie sessions |
| Profile / prefs | budget, currency, country, goals, modes, favorites, owned products, accessories | `user_platform.profiles` / preferences / favorites | No privacy retention policy | Deleted | Included | |
| Settings | theme, language, `privacy_settings`, `community_settings`, nested `NotificationPreference` including `newsletter` | `user_platform.settings` | No privacy retention policy | Deleted | Included | `newsletter` is **not** legal consent |
| Wishlist | `product_ids` | `user_platform.wishlists` | No privacy retention policy | Deleted | Included | Distinct from Watchlists |
| Saved products / comparisons / searches / history / recently viewed | query and product identifiers, notes | `user_platform.saved_*` | No privacy retention policy | Deleted | Included | Per-item saved-product delete already existed |
| Consent records | `user_id`, `policy_type` (`terms`/`privacy`), server-owned `version_id`, `accepted_at`, `source`, `actor` | `user_platform.consent_records` in existing `operational_entities` (no new table). Unique `{user_id}:{policy_type}:{version_id}` via `uq_operational_store_secondary` | No privacy retention policy | Deleted with account | Included | Empty until a published policy version exists |
| Password reset / email verify / email change | hashed tokens, expiry, consumed; email-change also stores intended `new_email` + `purpose` | `user_platform.password_resets` / `email_verifications` / `email_changes` | TTL 1h / 1d / 1d | Deleted | **Excluded** (security tokens) | Email-change uses the existing `operational_entities` store |
| Notification Center prefs | in-app/email/digest/marketing flags | `notifications.preferences` | No privacy retention policy | Removed when that store is wired | Merged under `notification_preferences` when present | Separate from legal consent |
| Watchlists | name, owner_id, items | watchlist store | No privacy retention policy | Owner-scoped watchlists deleted | Not a dedicated export category; account-owned lists are deleted | Distinct from profile wishlist |

## First-party cookies

| Name | Type | Purpose | Data fields | Storage | TTL | Deletion | Essential/functional (product) |
|------|------|---------|-------------|---------|-----|----------|--------------------------------|
| `piqsavi_decision_owner` | HTTP cookie | Authorize canonical UUID decision pages | `principal_type`, `principal_id`, `session_id`, `expires_at` | First-party cookie `httponly`, `samesite=lax` | Session cookie (no `max_age`); payload has `expires_at` | Browser clear / cookie expiry. Setter exists; issuance not currently wired in app routes | Functional / owner-binding |
| `piqsavi_delivery` | HTTP cookie | Guest delivery city/postal for offer presentation | `city`, `postal_code`, `skipped`, `source`. No street/GPS | First-party cookie `httponly`, `samesite=lax` | Session cookie (no `max_age`) | Browser clear; `clear_delivery_cookie` | Functional |
| `piqsavi_shopping_market` | HTTP cookie | Guest shopping-market country code | `{country_code}` only | First-party cookie `httponly`, `samesite=lax` | Session cookie (no `max_age`) | Browser clear; `clear_shopping_market_cookie` | Functional |

## sessionStorage

| Name | Type | Purpose | Data fields | Storage | TTL | Deletion | Essential/functional (product) |
|------|------|---------|-------------|---------|-----|----------|--------------------------------|
| `piqsavi_ask_conversation` | `sessionStorage` | Ask PiqSavi conversation continuity in the tab | `conversation_id` string | Browser `sessionStorage` | Tab/session | Tab close / user clears site data | Functional |

Auth uses `Authorization: Bearer`, not an auth cookie.

## Early Access data (unresolved / separate)

Early Access waitlist rows (`early_access.registrations`: full name, email, country, shopping interest, UTM/referrer) are a **separate data relationship**, not a consumer User account. There is no trusted `user_id` link. They are **not** deleted or exported by the account APIs, including when the waitlist email matches a deleted or exporting account. Whether email match should later imply erasure/export is **counsel-owned**. Operator CSV export remains a separate runbook.

## Intentionally excluded from consumer export

- `password_hash`
- session `token_hash`, `csrf_token`, raw access tokens
- password-reset / email-verification / email-change token hashes
- other users’ data
- Early Access waitlist rows (not a User account; no trusted `user_id` link)
- internal credentials / secrets
- proprietary scoring internals beyond the account’s stored recommendation-history summary

## Audit / logs / backups (not claimed erased)

| Store | Behavior |
|-------|----------|
| `user_platform.audit_events` | `account_deleted` / `policy_accepted` / export events may remain. Not physically purged by delete |
| HTTP request logs | May include client IP / path. No purge job |
| Database backups | Not claimed erased |
| Third-party email provider copies | Not claimed erased |

## Vendor / legal-role status

Controller / processor / subprocessor roles are **TBD — counsel-owned**. See [`ENGINEERING_VENDOR_INVENTORY.md`](ENGINEERING_VENDOR_INVENTORY.md). This inventory does not assign legal roles.

## Unresolved policy fields (not activated)

- Minimum age / parental consent — counsel-owned; not coded
- Marketing consent as a legal basis — not added; `newsletter` / `marketing_enabled` remain preference flags
- Analytics / cookie CMP consent — EXT-22 `not_started`; no banner implemented
