# Identity lifecycle product analytics

Sprint 39.4. These six events are server-owned product analytics. They are not security-audit rows, and the browser cannot submit them on `POST /api/v1/analytics/events`.

Analytics off writes zero rows. Explicit analytics consent uses the existing opaque subject only. These routes do not mint a subject and do not create an account-linked analytics identity. If consent is on and no valid subject is already present, the event is suppressed.

`identity_kind` comes from `analytics_context_for_request`. This slice does not rewrite a guest subject to authenticated because login or claim succeeded.

Event ids are random server UUIDs from `record_server_event`. `deterministic_event_id` is not used. Email, user id, principal id, session id, access token, verification token, reset token, conversation id, IP address, and the analytics subject cookie are not event-id material and are not stored properties.

| Event | Emit only after | Not emitted for |
| --- | --- | --- |
| `registration_completed` | `POST /api/v1/auth/register` has created the account and its session. Surface `account`, action `complete`, outcome `completed`. | Validation failure, duplicate account, rate limit, failed persistence |
| `registration_verified` | `POST /api/v1/auth/verify-email/confirm` has marked that account verified. Surface `account`, action `complete`, outcome `completed`. | Verification email request, invalid token, expired token |
| `login_success` | `POST /api/v1/auth/login` has authenticated. Surface `account`, action `submit`, outcome `completed`. | Any failed login |
| `login_failure` | That login endpoint has determined the attempt failed. Surface `account`, action `submit`, outcome `failed`. | Success. Other endpoints that write a security `login_failure` audit row |
| `account_deleted` | The existing account-deletion operation has completed. Surface `account`, action `complete`, outcome `completed`. | Rejected deletion. This does not claim legal erasure of audit logs, backups, analytics, or feedback |
| `authentication_transition` | `POST /consumer/claim-decision` returns `claimed` true for the guest conversation claim. Surface `account`, action `complete`, outcome `completed`. | `missing_guest_owner`, `not_a_guest_owner`, `conversation_not_found`, `missing_conversation`, `immutable_snapshot_owner`, `owner_mismatch`, and any other unsuccessful claim |

`login_failure.error_code` is only `auth_failed`, `validation_failed`, or `rate_limited`. Unknown email, an inactive account, and a wrong password all store `auth_failed`. The product row does not say which one happened. The security audit log still records its existing detail and is not copied here.

A login attempt is a distinct action, so a random id is the truthful id. Registration, verification, deletion, and claim also lack a safe non-PII stable id. Retries that fail do not emit a second success row.

The dashboard section is `metrics.identity_lifecycle`. It exposes the six counts and `partial`. Windows stay `1d`, `7d`, and `30d`. A truncated scan sets `partial` and counts only the scanned rows, in the same way as `core_funnel`. These counts are not account DAU or MAU.

Analytics persistence or schema failure does not change the auth or claim HTTP result.
