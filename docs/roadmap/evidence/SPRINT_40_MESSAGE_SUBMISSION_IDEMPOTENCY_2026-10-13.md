# Message submission idempotency — 2026-10-13

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `591bcf751aae5e8f7cc14c1ffac17b81211b395a`

This record does not assign a sprint slice number. It does not rewrite the 2026-10-09 readiness audit, the post-40.6 reconciliation, the post-40.7 reconciliation, the failed-login lock record, or the post-failed-login-lock reconciliation. Those files keep the classes they recorded. R17 is IMPLEMENTED-NOT-PROVEN and is not PROVEN. No Included requirement is PROVEN. Repository tests are not staging proof. No deploy was performed. No Shopify call was made. Live research stays off. Routing stays 0. Real Shopify calls stay 0. Affiliate activation stays off.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. This record does not select a later engineering slice.

## Mutation boundary

`POST /api/v1/shopping-assistant/query` is the public Ask submission. Conversation compare-and-swap does not cover the whole POST. The effects reachable from the handler are:

1. Before response construction, inside `ShoppingAssistantService.query`:
   - Non-decision path: optional conversation `create` (verified owner, or `owner=None` for anonymous Ask), recommendation-history write for an authorized account, then `append_turn`.
   - Decision path: `ProposeResearchService.handle` may return early after creating or replacing a research proposal, incrementing `proposal_version`, requesting confirmation, or passing a confirmation through the existing research-authorization path. Otherwise a refinement request persists a session overlay and appends a turn. Otherwise `AnswerFromEvidenceService.answer` appends a bound turn when a conversation and owner exist. Snapshot integrity checks can raise after some of those writes.
2. After the assistant result exists, still inside `query`: affiliate-link attachment and response validation. Affiliate activation stays off. This slice does not change that attachment.
3. Inside conversation-repository transactions: `create`, `save`, `append_turn`, and research-authorization consumption use the operational store compare-and-swap. Recommendation history is a separate user-platform write and is not in that transaction.
4. Outside the conversation repository: recommendation history, affiliate-link generation, `emit_ask_product_events` in the endpoint after `query` returns, and this submission ledger.

`emit_ask_product_events` runs only when this request is the atomic winner (`applied.fresh`). A replay does not emit `ask_question_submitted`, `ask_evidence_answered`, `insufficient_evidence`, refinement observations, or research observations again. Analytics success is not the idempotency authority.

Research confirmation keeps `derive_authorization_idempotency_key` and the `research-auth:` prefix. The client confirmation token is not the execution identity. A new submission key that repeats a confirmation still reuses that authorization. A retry of the same submission key returns the stored response and does not enter `service.query`.

## Client submission identity

The public POST requires the `Idempotency-Key` header. The body schema has no submission field. A missing or malformed key is HTTP 400 (`Idempotency-Key is required.` or `Idempotency-Key is invalid.`) and does not claim a row. The server does not invent a key.

A valid key is 16 to 128 characters from `A-Za-z0-9_-`. A UUID with hyphens matches. Comma-separated multi-values are rejected. The raw key is not logged and is not stored. The ledger stores SHA-256 of the key.

The PiqSavi browser generates one key with `crypto.randomUUID()` before the first fetch, or `crypto.getRandomValues` when `randomUUID` is absent. The same key is reused for a transient network failure, HTTP 503, HTTP 429, or HTTP 409 `Request already in progress.` A new intentional submit, including identical question text, gets a new key. The key is not derived from the question, `decision_id`, `conversation_id`, `proposal_id`, a timestamp, or `user_id`. The submit control is disabled while one request is active. That is UX hardening and is not the idempotency control. A terminal success, a payload conflict, an indeterminate outcome, or another terminal HTTP error discards the key.

## Server replay scope

The scope is the strongest verified subject:

- Authenticated account: `opaque_subject_key("ask-acct", principal_id)`.
- Verified guest: `opaque_subject_key("ask-guest", principal_id + session_id)`.
- Anonymous Ask, which remains supported: `opaque_subject_key("ask-anon", trusted client host)`.

`opaque_subject_key` is the existing HMAC helper (`dealbrain-rate-limit-v1`). The raw principal, owner cookie, session token, bearer token, email, password, and client address are not stored. Body `user_id`, `profile_id`, `conversation_id`, and `decision_id` are not the replay authority. An HMAC failure is HTTP 503 and does not execute the query. Different verified owners do not share a scope, so the same client key does not collide across them.

## Request fingerprint

The fingerprint is SHA-256 of canonical JSON (`sort_keys`, compact separators) over the mutation-relevant input: normalized query, `decision_id`, `context_version`, `conversation_id`, `proposal_id`, `proposal_version`, `confirmation_token`, mode, budget, category, currency, products, use cases, surface, the selected market country code, a digest of delivery context, normalized body `profile_id`, normalized body `user_id`, and the server authority scope. Whole floats are canonicalized to integers. Blank `profile_id` and `user_id` are stored as null, using the same `_blank_none` rule as the other optional strings. Those two fields are part of the submitted payload because a matching `profile_id` can change the effective profile, response, and history metadata, and `user_id` is passed into affiliate decoration. They are not authorization authority and they are not read by `submission_authority_scope`. The same scoped key with a changed `profile_id` or `user_id` is an HTTP 409 fingerprint conflict. Unstable transport metadata is omitted.

Same scoped key and same fingerprint: replay. Same scoped key and a different fingerprint: HTTP 409 `Idempotency-Key does not match the original request.` The key is never reused as a new request.

## Persistence

Table `shopping_assistant_submissions`, Alembic revision `a7b8c9d0e1f2` (revises `f6a7b8c9d0e1`). Primary key `(scope, key_hash)`.

| Column | Meaning |
|--------|---------|
| `scope` | Opaque HMAC subject. No email, cookie, token, or address. |
| `key_hash` | SHA-256 of `Idempotency-Key`. The raw key is not stored. |
| `fingerprint` | SHA-256 of the canonical mutation input. |
| `state` | `processing`, `completed`, or `indeterminate`. |
| `http_status` | 200 when a response was stored. Otherwise null. |
| `response_body` | Public response JSON needed to replay. Null while processing or indeterminate. Capped at 262144 characters. |
| `created_at_ms` / `updated_at_ms` / `expires_at_ms` | Bounded timestamps. |

Index `ix_shopping_assistant_submissions_state_expires` is `(state, expires_at_ms)`.

Development and unit tests use `InMemoryShoppingSubmissionStore`. Staging and production resolve the same backend rule as the rate limiter: unset means PostgreSQL, and `RATE_LIMIT_BACKEND=memory` raises `RateLimitConfigurationError`. The SQL store does not fall back to memory. Store errors are HTTP 503 `Shopping assistant submission store is unavailable.` and do not execute `service.query` when the claim cannot be evaluated. The ledger singleton is built at process start, so a later test that changes `APP_ENV` does not switch a running development process onto PostgreSQL.

The stored response is the public assistant JSON. It includes the question and answer because an exact replay cannot be rebuilt without calling `service.query`. No owner credential or authorization token is stored.

## Retention

`docs/privacy/ENGINEERING_RETENTION.md` had no approved shopping-submission period. The beta default is explicit and bounded:

- `SUBMISSION_RETENTION_SECONDS` = 86400 (24 hours) for completed and indeterminate rows.
- `PROCESSING_HORIZON_SECONDS` = 900 (15 minutes). This is a fail-closed seal horizon, not a re-execution lease.

Cleanup deletes only expired completed and indeterminate rows. It does not delete a `processing` row. After the horizon, a stale `processing` row is sealed `indeterminate` and kept for 24 hours. It is not executed again. After that retention, a very late retry of the same key can execute, because the record is gone. The browser discards the key on a terminal response, so that path is a late reuse outside the beta window. Records are not indefinite. The 24 hours are an engineering TTL, not legal retention.

## Concurrent claim

`claim` inserts the processing row. The primary key is the atomic winner. A conflicting insert loads the committed row and does not execute. There is no check-then-insert. Two workers with the same scoped key produce one `service.query`, one conversation turn, one history write, one analytics emit, one proposal-version increment, and one refinement persist. The loser receives HTTP 409 `Request already in progress.` while the winner is still processing, or the stored response if the winner has already completed. The browser retries that in-progress result with the same key.

## Completed replay

A completed retry returns the stored JSON. It does not call `service.query` and does not call `emit_ask_product_events`. If the stored JSON no longer validates, the response is HTTP 409 `Request outcome is indeterminate.` and the query is not run again. If the response exceeds the size cap, the winner still returns it once, the row is sealed indeterminate, and a retry does not re-execute.

## Crash and indeterminate state

`apply_shopping_submission` treats `execute` as the mutation boundary. Any exception from `service.query` is sealed `indeterminate` and re-raised. The processing claim is not released, because the query may already have written a turn, a history row, a proposal, or a refinement before raising. `release_unentered` exists only for a claim that has not entered `execute`. The public handler does not call it after `query` starts.

A crash between the claim commit and `execute` leaves `processing` until the 15-minute horizon, then seal moves it to `indeterminate` without a second apply. A crash after an unknown partial apply stays indeterminate for 24 hours. The horizon does not authorize another execution. If completion persistence fails after a successful execute, the row is sealed indeterminate so a retry cannot apply again, and the winner still returns the response and emits analytics once.

## Error contract

| Condition | Status | Detail |
|-----------|--------|--------|
| Missing key | 400 | `Idempotency-Key is required.` |
| Malformed key | 400 | `Idempotency-Key is invalid.` |
| Same key, different payload | 409 | `Idempotency-Key does not match the original request.` |
| Duplicate while processing | 409 | `Request already in progress.` |
| Indeterminate or unusable stored response | 409 | `Request outcome is indeterminate.` |
| Ledger unavailable | 503 | `Shopping assistant submission store is unavailable.` |

These details do not say whether another subject's key exists.

## Directly affected requirements

| ID | Class | Why |
|----|-------|-----|
| R17 | IMPLEMENTED-NOT-PROVEN | Ordinary message submission and decision-bound Ask now share one client submission identity. Research confirmation keeps its server authorization key. Staging has not exercised the ledger. Not PROVEN. |

R8, R10, R11, R15, R16, and R19 are unchanged. R1, R9, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 5 (R1, R9, R14, R17, R18), PARTIAL 15, MISSING 1 (R11), BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The Sprint 40 HIGH "In-process rate limits only" stays IMPLEMENTED-NOT-PROVEN. SAST, container vulnerability scanning, and IaC security scanning stay open. This slice does not implement them.
