# Phase 29.4B — `refine_session_recommendation`

**Status:** Implemented on the conversational continuity path. Not a new Recommendation engine.

**Depends on:** Phase 29.4A `answer_from_evidence`, canonical UUID consumer adapter, schema 1.2 presentation contract.

## Purpose

After a shopper receives a canonical Recommendation, they may clarify preferences in Ask PiqSavi. Phase 29.4B lets PiqSavi reconsider **Best Piq for You** using only products and evidence already captured in that decision.

It does not:

- rewrite the historical canonical snapshot
- change PiqScore
- add products or merchants
- research, reprice, or call live integrations
- write permanent account preferences
- implement `propose_research` (Phase 29.4C)

Hard rule:

> PiqScore evaluates the offer. Best Piq for You reflects what best fits the shopper.

## Canonical decision vs session refinement

| | Canonical decision | Session refinement |
|---|---|---|
| Authority | Historical, immutable snapshot | Temporary conversational overlay |
| Storage | `DecisionSnapshotRepository` | `ConversationContext.session_refinement` |
| Version | `context_version` (snapshot only) | `refinement_version` (session only) |
| Best Piq | Original Recommendation | Current session Best Piq |
| PiqScore | Frozen | Unchanged |
| Evaluated set | Frozen | Frozen |

The two concepts are not merged. The original Recommendation remains recoverable as `original_best_piq_product_id`.

## Why canonical `context_version` does not increment

The frozen decision-context contract says `context_version` changes only when a new canonical snapshot is committed. Session clarification is not a new historical snapshot.

Ask continuity still uses `decision_id` + snapshot `context_version` to load the same evidence packet. The overlay is loaded from the owner-bound conversation. Subsequent Ask questions therefore see the latest session Best Piq without inventing snapshot v2.

## Session refinement lifecycle

1. Shopper asks a preference-change question on Results, Compare, or Why.
2. Server classifies the message as `refine_session_recommendation` (the browser never chooses the action).
3. Owner-bound snapshot retrieval verifies integrity.
4. The request is interpreted into structured `SessionPriorities`.
5. A deterministic evidence matcher selects a session Best Piq from `evaluated_products` only.
6. The overlay is stored on the conversation. Snapshot bytes are unchanged.
7. Results / Compare / Why apply the overlay at render time.
8. Later Ask questions use the same overlay.

Multiple clarifications increment `refinement_version`. Reset language (`use my original priorities`) restores the session Best Piq to the canonical Recommendation.

## Request and result

Input the browser may send:

- `decision_id`
- `context_version` (canonical snapshot version)
- `conversation_id`
- shopper `query`

The browser must not send `new_best_piq`. The server decides.

Structured preference change uses existing shopper-context keys when they appear in the snapshot or evidence (for example `comfort`, `anc`, `battery`, `price`, `multipoint`, `travel`) plus optional session budget and required-feature flags.

Result processing includes:

- `action = refine_session_recommendation`
- `answer_status`
- `session_priorities`
- `session_best_piq_product_id`
- `original_best_piq_product_id`
- `session_refinement_version`
- `recommendation_snapshot_sha256` (overlay digest, not a new canonical Recommendation)
- `canonical_piqscore_snapshot_sha256` (unchanged)

Statuses:

- `recommendation_changed`
- `recommendation_unchanged`
- `insufficient_evidence`
- `outside_evaluated_set`
- `unsupported_refinement`
- `ambiguous_request`
- `none_fit_constraint`
- `reset_to_original`

## How a refined Best Piq is selected

This is not a second PiqScore and not an LLM relevance score.

The selector is a bounded evidence matcher:

1. Hard required features: captured `true` may qualify a product; captured `false` excludes it; **unknown ≠ false**.
2. Session budget: only known captured costs are compared. Unknown cost is not treated as affordable. If none fit, the overlay says so and does not invent a Best Piq that violates the constraint.
3. Soft priorities: compare captured fit attributes, evidence topics, recommendation reasons, trade-offs, and best-for labels already on the snapshot.
4. If the changed priority has no captured evidence across the set, return insufficient evidence. Do not research.
5. If evidence does not differentiate, keep the current Best Piq and explain why.
6. Affiliate commission is never consulted. `affiliate_influence` remains `false`.

## Evidence and evaluated-set boundaries

Usable evidence is only what the trusted snapshot already contains: evaluated products, PiqScores, shopper context, fit attributes, reasons, trade-offs, qualification, and offer economics.

Missing evidence is unknown. Missing is not “does not support.” Insufficient evidence is returned honestly.

A named product outside `evaluated_products` is not a preference. 29.4B returns `outside_evaluated_set` and does not add it. Phase 29.4C will later propose research.

## Ask routing

| Example | Action |
|---|---|
| “Why is Sony best?” | `answer_from_evidence` |
| “Comfort matters more.” | `refine_session_recommendation` |
| “What sources did you use?” | `answer_from_evidence` |
| “My budget is only ₱15,000 now.” | `refine_session_recommendation` |
| “What about AirPods Max?” | not refined; outside-set / later research |
| “Find something cheaper.” | unsupported refinement; no search |

Ask PiqSavi remains on Results, Compare, and Why. Follow-up questions after a refinement use the latest overlay.

## Presentation

Results, Compare, and Why consume the same owner-bound overlay. PiqScore numbers stay the original captured values even when session Best Piq differs from the highest PiqScore.

Why distinguishes:

- original decision context
- what the shopper changed
- why the session Recommendation changed
- remaining unknowns / qualification

It does not imply the original decision was wrong.

## Owner isolation

The same no-existence-leak path as 29.4A applies. Wrong owner and unknown UUID both look like “not found.” Tampered snapshots cannot be refined. Fixture catalogs are not used to fill missing canonical evidence.

## Difference from Phase 29.4C

29.4B never proposes or executes research. It cannot add a product, refresh a price, or create a new canonical snapshot. Those remain future `propose_research` work.
