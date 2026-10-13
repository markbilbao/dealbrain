# Sprint 40.7 — Decision-path owner binding

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `df051a2e122816928bb85edb75c5f27290c1aaaa`

This record does not rewrite the 2026-10-09 readiness audit or the 2026-10-10 post-40.6 reconciliation. Those files keep the classes they recorded. No Included requirement is PROVEN. Repository tests are not staging proof. No deploy was performed. No Shopify call was made. Routing stays 0.

## Authorization rule

For answer-from-evidence, session-recommendation refinement, and research proposal:

- The verified request owner is the only authority.
- Body `conversation_id`, `decision_id`, and `context_version` are lookup and reference values.
- A stored conversation owner is never promoted into request authority.
- When a verified request owner exists and a body `conversation_id` is present, the conversation is loaded only with `get_for_owner(conversation_id, owner)`. A miss is the existing not-found failure. After that match, the owned conversation's bound decision reference may supply or confirm `decision_id` and `context_version`.
- The canonical UUID snapshot read uses `get_for_owner` with the verified request owner. It does not use `context.owner`.
- When no verified request owner exists, these services do not call `get(conversation_id)` and do not set an owner from the stored row. UUID snapshot access fails closed with `DecisionSnapshotOwnershipError` and the existing reason `snapshot access requires a verified owner`.
- Owner-bound overlays, pending proposals, and research authorizations are not read from a body `conversation_id` unless that id belongs to the verified request owner.

The fix does not compare a stored owner after an unscoped read and then adopt it. It does not trust body `decision_id`, `user_id`, `profile_id`, or body owner or session identifiers as authority.

Foreign and missing conversations both surface as not-found. An ownerless UUID read uses the existing ownership error. Both exceptions already map to HTTP 404 `Decision not found.`

## Vulnerable reads on the starting SHA

These were the same-class decision-path reads. Each id came from the request body.

| Service | Method | Old read |
|---------|--------|----------|
| `AnswerFromEvidenceService` | `_resolve_packet` | `self._conversations.get(conversation_id)`, then `bound_owner = context.owner`, then `snapshots.get_for_owner(..., bound_owner)`. The same row could replace `decision_id` and `context_version` before that read. |
| `AnswerFromEvidenceService` | `answer` | When `owner` was `None`, the session overlay used `self._conversations.get(conversation_id)`. |
| `RefineSessionRecommendationService` | `_resolve_packet` | Same unscoped `get`, `bound_owner = context.owner`, and snapshot read as answer-from-evidence. |
| `RefineSessionRecommendationService` | `_existing_overlay` | When `owner` was `None`, `self._conversations.get(conversation_id)`. |
| `ProposeResearchService` | `_resolve_packet` | `get_for_owner` when a request owner existed, otherwise `self._conversations.get(conversation_id)`. Both branches then set `bound_owner = context.owner` before the snapshot read. |
| `ProposeResearchService` | `_bound_context` | When `owner` was `None`, `self._conversations.get(conversation_id)`. That helper feeds the existing overlay, pending proposal, and research-authorization lookups. |

No other `self._conversations.get(` call remains in those three services. Turn append, refinement persistence, and proposal persistence already used `get_for_owner` with the request owner. Those writes were left in place. Non-decision Sprint 40.1 reads were not changed. Sprint 38 execution reads were not changed.

`tests/unit/test_phase_29_4a_answer_from_evidence.py` `test_bound_conversation_answers_from_snapshot` previously answered a UUID snapshot from a body `conversation_id` with no request owner. That test is now the negative regression. `test_verified_owner_bound_conversation_answers_from_snapshot` is the positive verified-owner case.

## What still works

- Verified owner A, a conversation owned by A, and a canonical decision owned by A still answer, refine, and propose.
- Once that conversation is authorized, its bound decision reference may confirm the snapshot that is read. A body `decision_id` for a different owner is not adopted.
- Owner B with owner A's conversation id fails closed and does not read A's snapshot, overlay, or pending proposal.
- No verified owner, plus owner A's conversation id, fails closed for UUID snapshot access and does not read A's overlay or pending proposal.
- Fixture decision ids can still be answered without an owner. That path does not load an owner-bound overlay or proposal from the body conversation id.
- Canonical snapshot bytes are not mutated. Research-confirmation idempotency stays server-derived. Sprint 40.1 non-decision body-identity behavior is unchanged.

## Row status after this slice

Only R1, R13, R14, and the directly affected aspect of R18 were re-read. Other reconciliation classes stay as recorded on 2026-10-10.

| Row | Post-slice class | Why |
|-----|------------------|-----|
| R1 | IMPLEMENTED-NOT-PROVEN | The remaining object-level defect named by the reconciliation was this decision-path read. Answer, refinement, and research proposal now load owner-bound conversation context and UUID snapshots only under the verified request owner. No staging exercise exists, so the row is not PROVEN. |
| R13 | PARTIAL | The decision-path half is implemented: a body conversation id cannot select a stored owner, and UUID snapshot access still requires a verified owner. An independent gap remains. Anonymous non-decision queries still use `create(owner=None)`, which is the merged Sprint 40.1 contract and conflicts with binding every conversation. Repository `append_turn` can still materialize an ownerless row when a caller passes a missing id. This slice does not change that contract. |
| R14 | IMPLEMENTED-NOT-PROVEN | Body `conversation_id`, `user_id`, and `profile_id` do not authorize decision or non-decision reads. The decision-path residual is closed. Affiliate link decoration can still copy a body `user_id` into an affiliate `sub_id` on the non-decision path. Affiliate activation stays off, and that copy does not read or authorize another owner's conversation, profile, decision, or history. It is not an authorization path. No staging proof exists, so the row is not PROVEN. |
| R18 | IMPLEMENTED-NOT-PROVEN | Unchanged. This slice does not write conversation bodies or session identifiers to routine logs, product analytics, or recommendation history. The row was already IMPLEMENTED-NOT-PROVEN and stays there because staging log and analytics samples are absent. |

## Unchanged Sprint 40 findings

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence stays CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. R6 stays PARTIAL. R11 stays MISSING. They are not relabeled launch-blocking. No risk acceptance is recorded.

Guest-to-account rebind of a canonical UUID snapshot remains a product-definition conflict. Account lockout, message idempotency, prompt-injection redesign, merchant and review sanitation, and the pen-test, security IR, and vulnerability-response packages were not changed.

## Roadmap truths

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. Routing stays 0. Shopify stays disabled. Real Shopify calls stay 0. Affiliate activation stays off. No deploy was performed. No Shopify call was made.
