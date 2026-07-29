# Profile Model

**Status:** Sprint 16 (`CustomerProfile` fixtures) + Sprint 17 (`UserProfile` accounts)

This document covers two related but distinct profile models:

1. **`CustomerProfile`** (Sprint 16) — fixture-only personas used by the
   Personal AI Shopping Agent for anonymous / demo personalization. No
   account, no login, no persistence beyond static fixtures.
2. **`UserProfile`** (Sprint 17) — account-backed shopping profile owned by a
   registered User Platform account, created and updated via the
   `/api/v1/profile` API. See [User Platform](USER_PLATFORM.md) and
   [Authentication](AUTHENTICATION.md) for the account system it belongs to.

The two models are independent: a `UserProfile.preferences.personal_profile_id`
field can *optionally* reference a `CustomerProfile` fixture id to seed
Shopping Assistant personalization, but neither model requires the other.

## `CustomerProfile` (Sprint 16)

**Entity:** `CustomerProfile` in `app/domain/entities/personal_agent.py`
**Fixtures:** `app/intelligence/personal/fixtures.py`

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `profile_id` | str | Stable fixture id |
| `display_name` | str | Demo label |
| `persona` | str | Machine persona key |
| `budget` | float \| None | Max spend |
| `currency` | str | Default `PHP` |
| `country` | str | Default `PH` |
| `preferred_marketplaces` | tuple[str] | e.g. Shopee, Lazada |
| `favorite_brands` / `disliked_brands` | tuple[str] | Brand affinity |
| `preferred_screen_sizes` / `preferred_colors` | tuple[str] | Soft preferences |
| `gaming` / `office_work` / `student` / `creator` / `traveler` | bool | Lifestyle flags |
| `battery_priority` / `performance_priority` / `camera_priority` / `storage_priority` | float 0–1 | Feature priorities |
| `price_sensitivity` | float 0–1 | Budget strictness |
| `upgrade_frequency` | str | Qualitative cadence |
| `owned_products` / `wishlist` / `accessories_owned` | tuple[str] | Product ids |
| `favorite_categories` | tuple[str] | e.g. laptop, phone |
| `description` | str | Human-readable demo blurb |
| `data_status` | mock \| imported \| live | Always `mock` in v1 |

`use_cases()` derives shopping use-case tags from lifestyle flags and high priorities.

### Demo personas

1. Budget Student  
2. Gaming Enthusiast  
3. Photographer  
4. Business Traveler  
5. Content Creator  
6. Apple Fan  
7. Android Fan  
8. Minimalist Buyer  

### Limitations (`CustomerProfile`)

Profiles are **fixtures**. There is no account system, no sync, and no inferred behavioral profile beyond these explicit fields.

## `UserProfile` (Sprint 17)

**Entity:** `UserProfile` in `app/domain/entities/user_platform.py`
**Service:** `ProfileService` in `app/profile/service.py`
**API:** `GET/PUT /api/v1/profile`, `GET/PUT /api/v1/profile/preferences`
**Schemas:** `app/schemas/user_platform.py` (`ProfileResponse`, `ProfileUpdateRequest`, `PreferencesPayload`, `PreferencesUpdateRequest`)
**Persistence:** in-memory only (`InMemoryProfileRepository` in `app/user/memory.py`)

Unlike `CustomerProfile`, a `UserProfile` is **account-backed**: it is created
automatically at registration (`AuthService._bootstrap_profile`) and belongs
to exactly one `User`. It is read and updated through authenticated
`/api/v1/profile` requests (`Authorization: Bearer <access_token>`).

### Fields

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | str | Owning account id |
| `display_name` | str | Defaults to the account's display name at registration |
| `preferences` | `UserPreference` | Composed preference dimensions (below) |
| `favorite_brands` | tuple[`FavoriteBrand`] | Brand affinity records |
| `favorite_marketplaces` | tuple[`FavoriteMarketplace`] | Preferred marketplaces (e.g. Shopee, Lazada) |
| `wishlist` | `Wishlist` \| None | Wishlisted product ids |
| `owned_products` | tuple[str] | Product ids the user owns |
| `accessories` | tuple[str] | Accessory product ids owned |
| `version` | `ProfileVersion` \| None | Incrementing version + change summary, bumped on every update |
| `data_status` | mock \| imported \| live | Always `mock` in Sprint 17 |

`UserPreference` fields (nested under `preferences`, also flattened at the
top level of `ProfileResponse` for convenience): `budget`, `currency`,
`country`, `shopping_goals`, `categories`, `battery_priority`,
`camera_priority`, `performance_priority`, `travel_frequency`,
`creator_mode`, `gaming_mode`, `student_mode`, `business_mode`,
`preferred_screen_size`, `preferred_colors`, `personal_profile_id` (optional
link to a Sprint 16 `CustomerProfile` fixture id), `updated_at`.

`UserSettings` (separate from `UserProfile`, via `GET/PUT` — not yet exposed
as its own endpoint in Sprint 17, available on the service layer) holds
`theme`, `language`, `ai_mode_preference`, `notification_settings`,
`privacy_settings`, and `community_settings`.

### Versioning

Every `update_profile` / `update_preferences` call bumps
`ProfileVersion.version` and records a `change_summary`
(`profile_updated` / `preferences_updated`). There is no history of prior
versions — only the current version marker is retained.

### Demo accounts

`app/user/fixtures.py` seeds three demo `UserProfile` records (student,
creator, traveler personas) with realistic preferences, saved products,
comparisons, history, and searches. See `GET /api/v1/auth/demo`.

### Limitations (`UserProfile`)

- **Demo users only** — Sprint 17 accounts are not production identities.
- **No email sending**, **no MFA**, **no OAuth** for the account that owns
  the profile (see [Authentication](AUTHENTICATION.md), [Security Model](SECURITY_MODEL.md)).
- **In-memory persistence only** — profiles reset on process restart.
- **No production database adapter** wired in Sprint 17.
- **No payment integration.**
- No profile version history — only the latest `ProfileVersion` is kept.

## Summary

Sprint 17 **adds** the account-backed `UserProfile` described above; it does
not replace or modify the Sprint 16 `CustomerProfile` fixtures, which remain
in place unchanged for anonymous / demo Personal AI Shopping Agent
personalization.
