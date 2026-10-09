# Sprint 40.1 — Non-decision assistant body-identity authorization

**Slice status:** Implemented. Not PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `09757717971ad01077cefbaf806caddf10b8624d`

This record does not rewrite [`SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md`](SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md). That audit selected this slice and did not implement it. The audit matrix classes stay as recorded there. No Included requirement is PROVEN. Code and regression tests are not staging or production proof.

## What this slice changes

On `POST /api/v1/shopping-assistant/query` when there is no `decision_id`, request-body `conversation_id`, `user_id`, and `profile_id` are lookup hints. They do not establish authority.

The verified principal is the `ConversationOwner` already supplied by `authorized_owner_from_request`. The decision-bound branch is unchanged and still uses that owner with `get_for_owner`.

Non-decision behavior after this slice:

- A stored conversation is continued only when `get_for_owner` matches the verified guest or account owner.
- A missing, ownerless, or foreign client conversation id is not read and is not passed to `append_turn`. The repository `create(owner=...)` opens a new context. An anonymous caller gets an ownerless new context, which is the existing create contract. That new context does not reuse the client id.
- Account profile, display name, settings, preferences, and overrides load only for `owner.principal_id` when `principal_type` is `account`.
- Shopping recommendation history is written only for that same account id.
- A body `profile_id` personalizes only when it is the personal profile already bound to that verified account. Guests and anonymous callers do not activate a body profile id.

Affiliate link generation is unchanged. This slice does not enable affiliate tracking and does not change affiliate click behavior.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE.
- The open Sprint 40 HIGH remains in-process rate limits only.
- CSRF not enforced, CSP `'unsafe-inline'`, no Dependabot/CodeQL/Trivy/pip-audit, and incomplete URL validation / SSRF hardening remain the existing MEDIUMs. They are not relabeled launch-blocking. No risk acceptance is recorded.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0.

Out of scope and not implemented here: distributed rate limiting, account lockout, CSP changes, CSRF middleware, SSRF / URL-validation changes, Dependabot / CodeQL / Trivy / pip-audit, pen-test documents, Sprint 41 production work, Sprint 42 paging, Sprint 38 changes, and Sprint 39 changes.

## Tests

Focused regression coverage is `tests/unit/test_sprint40_assistant_body_identity.py`. `test_follow_up_conversation_context` now continues a conversation only for the verified owner. These tests do not make the slice PROVEN.
