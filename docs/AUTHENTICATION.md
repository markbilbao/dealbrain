# Authentication

**Status:** Sprint 17 + Sprint 27.1 (reset/verify confirm; Resend adapter) + Sprint 27.2 (verified email change) + Sprint 28.1 (consent hooks, delete/export)
**Service:** `AuthService` in `app/auth/service.py`
**Password hashing:** `app/auth/password.py` (`PasswordHasher`)
**Security hooks:** `app/auth/security.py` (rate limiting, CSRF, audit, MFA/OAuth extension points)
**Email port:** `app/auth/email.py` (`EmailSender`); Resend adapter `app/auth/email_resend.py`; factory `app/auth/email_factory.py`

## Overview

`AuthService` implements register, login, logout, and session validation for
demo/in-memory DealBrain accounts. It composes password hashing, rate
limiting, audit logging, and no-op extension points for MFA and OAuth so the
architecture is ready for those features without implementing them in
Sprint 17.

## Registration

`POST /api/v1/auth/register` → `AuthService.register(email, password, display_name, remember_me=False)`

Validation:

- `email` must match a basic `user@domain.tld` shape (normalized to lowercase, trimmed).
- `password` must be at least 8 characters, include mixed case, and include at least one digit.
- `display_name` must not be blank.
- Registration is rate-limited per normalized email (`RateLimiterHook`, 20 attempts / 60s window by default).
- Duplicate emails raise `UserPlatformConflictError` (HTTP 409).
- Optional `terms_accepted` / `privacy_acknowledged` are ignored unless a
  **published** policy version exists and requires acceptance. Unpublished
  catalogs never write fake Terms/Privacy acceptance rows.

On success, a `User` is created, a starter `UserProfile` + `UserSettings` are
bootstrapped (`AuthService._bootstrap_profile`), a `SecurityEvent` is recorded,
and a session is issued — see [Session Management](SESSION_MANAGEMENT.md).

Sprint 28.1 also adds authenticated `POST /api/v1/auth/account/delete`
(password re-auth + `confirmation=DELETE`) and `GET /api/v1/auth/account/export`.
These cover defined account-owned engineering data only; Early Access is a
separate relationship and this is not a complete legal DSAR.
See [`privacy/ACCOUNT_DELETION_PROPAGATION.md`](privacy/ACCOUNT_DELETION_PROPAGATION.md).

## Login

`POST /api/v1/auth/login` → `AuthService.login(email, password, remember_me=False)`

- Rate-limited per normalized email.
- Unknown email, inactive account, or bad password all raise the same
  generic `UserPlatformAuthError("Invalid email or password.")` (HTTP 401) to
  avoid account enumeration.
- If `MfaExtensionPoint.is_enabled(user_id)` ever returns `True` (it does not
  in Sprint 17), login raises `UserPlatformAuthError("MFA required but not
  implemented in Sprint 17.")` rather than silently bypassing MFA.
- On success, the rate limiter is reset for that email and a new session is issued.

## Logout

`POST /api/v1/auth/logout` → `AuthService.logout(access_token)`

Revokes the session backing the provided bearer token. Missing/invalid
tokens are a no-op (idempotent logout); no error is raised.

## Password hashing

`PasswordHasher` (`app/auth/password.py`) uses PBKDF2-HMAC-SHA256 from the
Python standard library — no third-party crypto dependency, no hardcoded
secrets. Hashes are stored as `pbkdf2_sha256$<iterations>$<salt-hex>$<digest-hex>`
so the algorithm can be migrated (e.g. to argon2 or bcrypt) later without
breaking existing hashes. Verification uses `hmac.compare_digest` for
constant-time comparison.

## Password reset & email verification (Sprint 27.1)

HTTP:

- `POST /api/v1/auth/password-reset` — enumeration-safe request
- `POST /api/v1/auth/password-reset/confirm` — token + new password
- `POST /api/v1/auth/verify-email` — enumeration-safe request by email
- `POST /api/v1/auth/verify-email/confirm` — token

Tokens are generated with `secrets.token_urlsafe`, stored as SHA-256 hashes
only, bound to a user and to a purpose-specific repository, expire
(reset: 1 hour; verification: 24 hours), and are marked consumed on first
successful use. Expired, reused, unknown, and wrong-purpose tokens fail with
the same generic auth error.

Password-reset confirm changes the password and revokes all existing
sessions via the existing `SessionRepository.revoke_all_for_user` path.
Registration still issues a session and also queues a verification email
when the verification repository is wired.

Request responses never vary HTTP status or `email_delivery` by account
membership. Provider failure on a request path is audited
(`email_delivery_failed`) and still returns the generic accepted body.

Inline `*_token_demo_only` values are allowed only in **development** when
`ALLOW_DEMO_RESET_TOKENS=true`. Staging, production, and unknown
environments never expose tokens in API responses.

Action links are built only from `PUBLIC_APP_BASE_URL`. The request `Host`
header is not used. Staging/production startup requires
`TRANSACTIONAL_EMAIL_PROVIDER=resend` plus a non-placeholder
`RESEND_API_KEY`, `TRANSACTIONAL_EMAIL_FROM`, and `https` public base URL.
`NullEmailSender` is not permitted in those environments.

EXT-09 sender-domain DNS verification is still a plan only. 27.1/27.2 do not
claim production email readiness.

## Email change (Sprint 27.2)

HTTP:

- `POST /api/v1/auth/email-change` — authenticated request
- `POST /api/v1/auth/email-change/confirm` — token

Ownership: the authenticated principal/session is the only account
authority. Request bodies and query strings may contain `user_id`,
`profile_id`, or other identity selectors; those fields are ignored and
cannot retarget another account.

Re-auth: the request requires the current account password, using the same
`Invalid credentials.` failure as Sprint 28.1 account deletion. A missing
or invalid bearer session is rejected before password checks.

The current account email does not change until a valid confirmation. The
confirmation token is generated with `secrets.token_urlsafe`, persisted as
a SHA-256 hash only in `user_platform.email_changes`, bound to the user,
the intended new email, and `purpose=email_change`, expires in 24 hours,
and is single-use. Newest request wins: a later request invalidates prior
unconsumed tokens for that user.

Validation:

- Invalid addresses are rejected with the existing email normalizer.
- The same effective email as the current account is rejected.
- An occupied destination returns the same accepted body as a free
  destination and does not create a token (no extra occupancy signal).
- Confirmation of an occupied, expired, consumed, wrong-purpose, stale, or
  unbound token fails with `Invalid or expired email-change token.`
- Provider failure leaves the account email unchanged and never returns
  the provider body or a staging/production raw token.

On valid confirm the bound account email is updated, `email_verified` is
set `True` (mailbox control was proven), the token is consumed, all
sessions for that user are revoked, and a token-free notice is sent to the
old address: “Your PiqSavi account email was changed.” Notice-delivery
failure does not roll back the change.

Confirmation ordering is fail-closed and does not introduce a new
transaction framework (each repository call still commits independently):

1. Validate token / purpose / expiry / newest-request / account — no mutation.
2. Recheck destination uniqueness — occupied destinations fail without
   consume or email mutation.
3. Determine whether the identity is already applied from a previous retry.
4. Revoke every session for that user, including the confirming session.
   Revoke failure leaves the old email, verified state, and token unchanged
   and does not send the old-email notice.
5. After successful revocation, persist the new email and
   `email_verified=True`. A save failure leaves identity unchanged and the
   token unconsumed (sessions may already be revoked).
6. Old-email notice is a secondary notification after a first-time identity
   mutation. It is not authorization. Failure is audited and never rolls back.
   Retry after consume failure does not send a duplicate notice.
7. Consume the winning token and invalidate sibling tokens. Consume failure
   does not return success; prior sessions are already revoked.
8. Success is returned only after revoke, persist (or already-applied), and
   consume succeed.

Password-reset and ordinary verification tokens cannot confirm email
change. Email-change tokens cannot reset a password or satisfy ordinary
verify-email confirmation.

## MFA and OAuth extension points

`MfaExtensionPoint` and `OAuthExtensionPoint` (`app/auth/security.py`) define
the shape of future multi-factor and external-identity-provider support.
Both are inert in Sprint 17: `MfaExtensionPoint.is_enabled()` always returns
`False`, and `OAuthExtensionPoint.begin_link()` always returns
`status: "not_implemented"`.

## Bearer tokens

Sessions are opaque, high-entropy random tokens (`secrets.token_urlsafe`),
returned once at register/login time. Only a SHA-256 hash of the token
(`AuthService.hash_token`) is ever persisted server-side — the raw token
cannot be recovered from storage. Clients must send it as:

```
Authorization: Bearer <access_token>
```

The API layer's `extract_bearer_token()` helper
(`app/api/v1/endpoints/auth.py`) parses this header; a missing or malformed
header is treated as an unauthenticated request.

## Error mapping

| Domain exception | HTTP status | Example |
|--------------------|-------------|---------|
| `UserPlatformValidationError` | 400 | Weak password, malformed email |
| `UserPlatformAuthError` | 401 | Bad credentials, expired/revoked session, invalid reset/verify/email-change token |
| `UserPlatformConflictError` | 409 | Email already registered |
| `UserPlatformRateLimitError` | 429 | Too many register/login attempts |

## Limitations

- **No MFA** implemented — extension point only.
- **No OAuth / external identity providers** — extension point only.
- **Email-change confirmation** is implemented in 27.2 (code path only;
  staging inbox E2E and EXT-09 remain open).
- **EXT-09** sender-domain SPF/DKIM/DMARC is not verified. Do not claim
  production sender authentication from 27.1 code alone.
- **Staging inbox E2E** is still required to close Sprint 27.
- **No payment integration.**
