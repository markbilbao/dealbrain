# User Platform

**Status:** Sprint 17
**Facade:** `UserPlatformService` in `app/services/user_platform_service.py`
**Domain entities:** `app/domain/entities/user_platform.py`
**Repository ports:** `app/domain/interfaces/user_platform_repository.py`
**In-memory adapters:** `app/user/memory.py` (`InMemoryUserPlatformStore`)
**Demo fixtures:** `app/user/fixtures.py`

## Overview

The User Platform introduces multi-user, account-backed shopping profiles on
top of DealBrain's fixture-based Sprint 16 `CustomerProfile` model. It
provides registration, login, per-account preferences, and saved-item
collections (products, comparisons, searches, recommendation history, and
recently-viewed products) so authenticated users can persist their own
shopping context across sessions — as a demo-scale account system, not a
production identity provider.

See also: [Authentication](AUTHENTICATION.md), [Session Management](SESSION_MANAGEMENT.md),
[Security Model](SECURITY_MODEL.md), and [Profile Model](PROFILE_MODEL.md)
(covers both the Sprint 16 `CustomerProfile` fixtures and the Sprint 17
account-backed `UserProfile`).

## Architecture

```
API (/api/v1/auth, /api/v1/profile, /api/v1/user)
  → UserPlatformService (facade)
      → AuthService        (app/auth/service.py)      — register / login / logout / session validation
      → ProfileService     (app/profile/service.py)   — UserProfile / UserPreference / UserSettings
      → SessionService     (app/session/service.py)   — session lookups, revocation, expiry
      → SavedItemsRepository (app/user/memory.py)     — saved products, comparisons, history, searches
  → AuditLogger / RateLimiterHook / CsrfTokenService   (app/auth/security.py)
  → PasswordHasher                                     (app/auth/password.py)
  → EmailSender (NullEmailSender)                       (app/auth/email.py)
```

All persistence in Sprint 17 is process-scoped and in-memory
(`InMemoryUserPlatformStore`). Repository ports are storage-neutral so a
SQL/NoSQL adapter can implement the same interfaces without changing the
service or API layers.

### Domain entities

| Entity | Purpose |
|--------|---------|
| `User` | Registered account; `password_hash` only, never returned over the API |
| `UserSession` | Opaque bearer session; only `token_hash` persisted, raw token returned once |
| `UserPreference` | Shopping preference dimensions tied to an account |
| `UserProfile` | Composed profile: preferences + favorite brands/marketplaces + wishlist + owned/accessory products |
| `UserSettings` | Theme, language, AI mode preference, notification/privacy/community settings |
| `SavedProduct` / `SavedComparison` / `SavedSearch` / `RecommendationHistory` / `RecentlyViewed` | Per-account saved-item collections |
| `SecurityEvent` | Audit hook payload (register, login, logout, rate-limited, etc.) |
| `PasswordResetRequest` / `EmailVerificationRequest` | Architecture-only records — no email is ever sent |

## API surface

| Method | Path | Auth required |
|--------|------|----------------|
| `POST` | `/api/v1/auth/register` | No |
| `POST` | `/api/v1/auth/login` | No |
| `POST` | `/api/v1/auth/logout` | No (no-op if no token) |
| `GET` | `/api/v1/auth/me` | Yes |
| `GET` | `/api/v1/auth/demo` | No |
| `GET` | `/api/v1/auth/meta` | No |
| `GET` | `/api/v1/profile` | Yes |
| `PUT` | `/api/v1/profile` | Yes |
| `GET` | `/api/v1/profile/preferences` | Yes |
| `PUT` | `/api/v1/profile/preferences` | Yes |
| `GET` | `/api/v1/user/saved-products` | Yes |
| `POST` | `/api/v1/user/saved-products` | Yes |
| `DELETE` | `/api/v1/user/saved-products/{saved_id}` | Yes |
| `GET` | `/api/v1/user/history` | Yes |
| `GET` | `/api/v1/user/comparisons` | Yes |
| `GET` | `/api/v1/user/searches` | Yes |
| `GET` | `/api/v1/user/recently-viewed` | Yes |

Authenticated routes require `Authorization: Bearer <access_token>` using the
token returned from `/auth/register` or `/auth/login`.

## Sample flow

Register (returns an `AuthResponse` with a bearer token):

```
POST /api/v1/auth/register
{
  "email": "demo@example.com",
  "password": "DemoPass123!",
  "display_name": "Demo User"
}
```

```json
{
  "user": { "user_id": "...", "email": "demo@example.com", "display_name": "Demo User", "is_active": true, "email_verified": false, "data_status": "mock" },
  "access_token": "opaque-random-token",
  "csrf_token": "opaque-random-token",
  "token_type": "Bearer",
  "expires_at": "2026-07-29T13:00:00+00:00",
  "session": { "session_id": "...", "user_id": "...", "created_at": "...", "expires_at": "...", "remember_me": false, "revoked": false }
}
```

Use the token for subsequent calls:

```
GET /api/v1/profile
Authorization: Bearer opaque-random-token
```

## Demo accounts

`GET /api/v1/auth/demo` lists ready-made demo accounts (see
`app/user/fixtures.py`) seeded with sample preferences, saved products,
comparisons, history, and searches. All demo accounts share the password
`DemoPass123!`.

## Error mapping

| Domain exception | HTTP status |
|-------------------|-------------|
| `UserPlatformValidationError` | 400 |
| `UserPlatformAuthError` | 401 |
| `UserPlatformConflictError` | 409 |
| `UserPlatformRateLimitError` | 429 |
| `UserPlatformNotFoundError` | 404 |

## Limitations

- **Demo users only** — Sprint 17 accounts are not production identities.
- **No email sending** — password reset and email verification create
  architecture-only records (`PasswordResetRequest`, `EmailVerificationRequest`);
  `NullEmailSender` records intent without delivering anything.
- **No MFA** — `MfaExtensionPoint` always reports disabled.
- **No OAuth / external identity providers** — `OAuthExtensionPoint` always
  returns `not_implemented`.
- **In-memory persistence only** — all data resets on process restart; there
  is no cross-process or cross-instance sharing.
- **No production database adapter is wired in Sprint 17** — repository
  interfaces are storage-neutral and designed for a future SQL/NoSQL adapter.
- **No payment integration** of any kind.
- Sprint 16 `CustomerProfile` fixtures (`app/intelligence/personal/fixtures.py`)
  remain unchanged and are used for anonymous / demo personalization; the
  Sprint 17 `UserProfile` is additive and account-backed (see
  [Profile Model](PROFILE_MODEL.md)).
