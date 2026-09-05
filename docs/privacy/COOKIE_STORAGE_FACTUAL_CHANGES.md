# Cookie / storage factual changes for counsel review (Sprint 28.1)

**Status:** Engineering factual addendum only.
**Does not** approve, publish, or rewrite the counsel Cookie & Tracking Notice.
**Does not** implement a CMP/banner (EXT-22 remains `not_started`).

The counsel draft [`docs/legal/PIQSAVI_COOKIE_TRACKING_NOTICE_COUNSEL_DRAFT.md`](../legal/PIQSAVI_COOKIE_TRACKING_NOTICE_COUNSEL_DRAFT.md) was factually stale relative to current `origin/main` because it predates current consumer cookies/storage.

Counsel should re-review the following **facts** before any public cookie notice:

## Factual delta counsel must review

| Prior counsel-draft posture | Current repository fact |
|-----------------------------|-------------------------|
| Named first-party application cookies **NOT FOUND** in reviewed consumer UI | Three first-party HTTP cookies exist: `piqsavi_decision_owner`, `piqsavi_delivery`, `piqsavi_shopping_market` |
| `localStorage` / `sessionStorage` **NOT FOUND** | `sessionStorage` key `piqsavi_ask_conversation` stores a `conversation_id` |
| Auth described as Bearer (not cookie sessions) | **Unchanged** — still Bearer `Authorization`; these cookies are not session-auth cookies |
| No GA/GTM/Meta/TikTok pixels | **Unchanged** — none added in 28.1 |
| No CMP/banner | **Unchanged** — none added in 28.1 |
| Affiliate `cookie_days` is registry metadata, not a browser cookie | **Unchanged** |

## Current first-party stores (engineering)

See [`ENGINEERING_PII_INVENTORY.md`](ENGINEERING_PII_INVENTORY.md) for fields, flags, and TTL. All three HTTP cookies are `httponly`, `samesite=lax`, `secure=False`, `path=/`, and are **session cookies** (no `max_age` in setters).

Product-architecture labels (functional / owner-binding) are **not** legal category conclusions.

## What this file is not

- Not a published cookie notice
- Not EXT-22 completion
- Not a claim that a banner is or is not legally required
- Not a rewrite of counsel `[COUNSEL TO CONFIRM]` answers
