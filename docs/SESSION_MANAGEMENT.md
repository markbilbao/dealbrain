# Session Management

**Status:** Sprint 17
**Service:** `SessionService` in `app/session/service.py`
**Entity:** `UserSession` in `app/domain/entities/user_platform.py`
**Repository port:** `SessionRepository` in `app/domain/interfaces/user_platform_repository.py`
**In-memory adapter:** `InMemorySessionRepository` in `app/user/memory.py`

## Overview

`SessionService` is a thin facade over `SessionRepository` and
`AuthService.validate_session`, used for session lookups, revocation, and
expiry checks outside the login/logout request path (e.g. "list my active
sessions" or admin/session-hygiene tooling).

## Session lifecycle

1. **Issued** — `AuthService._issue_session` creates a `UserSession` on
   successful register/login with:
   - `session_id` — internal identifier.
   - `token_hash` — SHA-256 hash of the raw bearer token (the raw token is
     never persisted).
   - `expires_at` — `created_at + session_ttl_seconds` (default 3600s), or
     `+ remember_me_ttl_seconds` (default 2,592,000s / 30 days) when
     `remember_me=True`.
   - `csrf_token` — issued alongside the session (see [Security Model](SECURITY_MODEL.md)).
2. **Validated** — `AuthService.validate_session(access_token)` hashes the
   incoming token, looks it up, and rejects it if missing, revoked, or past
   `expires_at` (auto-revoking expired sessions and recording a
   `session_expired` audit event). Valid sessions have `last_seen_at`
   refreshed on every use.
3. **Revoked** — `AuthService.logout` or `SessionService.revoke` /
   `revoke_all` mark a session `revoked=True`. Revoked sessions fail
   validation immediately regardless of `expires_at`.

## `SessionService` API

| Method | Purpose |
|--------|---------|
| `validate(access_token)` | Returns the active `UserSession` or raises `UserPlatformAuthError` |
| `revoke(session_id)` | Revoke a single session by id |
| `revoke_all(user_id)` | Revoke every active session for a user (e.g. "log out everywhere") |
| `list_active(user_id)` | List sessions that are neither revoked nor expired |
| `is_expired(session)` | Check expiry/revocation without raising |

## Remember-me sessions

Passing `remember_me: true` on register or login extends the session TTL from
1 hour to 30 days. This only affects `expires_at` — the same opaque bearer
token and revocation semantics apply.

## Token hashing rationale

Only `token_hash` (SHA-256 of the raw token) is stored; the raw token is
returned exactly once, in the register/login response body. This limits
blast radius if the in-memory store were ever inspected or leaked, since
raw tokens cannot be reconstructed from stored hashes.

## Limitations

- **In-memory persistence only** — all sessions are lost on process restart;
  there is no shared session store across multiple processes/instances.
- **No production database adapter** — `SessionRepository` is a storage-neutral
  port; only `InMemorySessionRepository` ships in Sprint 17.
- **No sliding-window renewal endpoint** — sessions extend `last_seen_at` on
  use but do not currently expose a "refresh token" endpoint.
- **No device/session metadata UI** — `user_agent` / `ip_hint` are captured
  but there is no endpoint to list or manage them by device yet beyond
  `SessionService.list_active`.
- **No MFA or OAuth** tie-ins to session issuance.
- **No payment integration.**
