# Sprint 29 Phase 29.0 — Decision Context and Action Contracts

**Status:** Frozen contract; application behavior not yet implemented

**Architecture authority:**
[`SPRINT_29_CC01_ARCHITECTURE.md`](SPRINT_29_CC01_ARCHITECTURE.md)

## Contract registry

| Contract | Schema | Frozen fixture |
|---|---|---|
| Decision context v1 | `schemas/sprint29-decision-context.schema.json` | `tests/contracts/fixtures/sprint29-decision-context.json` |
| Conversation action v1 | `schemas/sprint29-conversation-action.schema.json` | three `sprint29-action-*.json` fixtures |
| Research execution v1 | `schemas/sprint29-research-execution.schema.json` | `sprint29-research-unavailable.json`, `sprint29-research-mock.json` |
| Context-drift case v1 | `schemas/sprint29-context-drift-fixture.schema.json` | `sprint29-context-drift.json` |
| Contract traceability v1 | `schemas/sprint29-contract-traceability.schema.json` | `sprint29-contract-traceability.json` |
| Authority lock v1 | `schemas/sprint29-authority-lock.schema.json` | `sprint29-authority-lock.json` |

The fixtures are non-live contract examples. Product facts, scores, timestamps,
and identifiers in them are deterministic test data, not marketplace claims or
outputs from the protected PiqScore/Recommendation engines.

Canonical offer economics for later decision snapshots are documented in
[`CANONICAL_OFFER_ECONOMICS.md`](CANONICAL_OFFER_ECONOMICS.md). Schema `1.0`
snapshots remain valid without economics. Schema `1.1` adds captured
decision-time offer economics without rewriting historical `1.0` digests.

## Decision context v1

A decision context is a versioned, server-owned snapshot. It captures the exact
inputs and canonical outputs needed for later contextual answers without
re-running search or deriving candidates from conversational text.

Required invariants:

- `decision_id` is stable across turns.
- `context_version` changes only when a new canonical snapshot is committed.
- `evaluated_products` is ordered and product IDs are unique.
- each product holds a canonical PiqScore value plus an opaque integrity digest.
- Recommendation refers only to products in `evaluated_products`.
- evidence refers only to products in `evaluated_products`.
- the owner is a server-validated guest session or account principal.
- affiliate-influence fields are fixed to `false`.
- fixtures identify themselves as `non_live_contract_fixture`.

JSON Schema validates structure. Later behavioral tests must validate
cross-field membership, product uniqueness by `product_id`, authorization,
snapshot atomicity, and persisted integrity.

## Conversation action v1

The action contract is a closed union. Exactly one action is permitted:

### `answer_from_evidence`

- cites at least one captured `evidence_id`
- returns an answer derived from the existing context
- does not require research confirmation
- preserves the evaluated product IDs and PiqScore snapshot digest

### `refine_session_recommendation`

- accepts session-scoped priorities
- returns an opaque Recommendation snapshot digest
- operates over the existing evaluated product IDs
- does not mutate canonical PiqScore values or persistent preferences
- does not require research confirmation

### `propose_research`

- carries a bounded research proposal
- does not begin execution
- always sets `requires_research_confirmation` to `true`
- cannot be represented as evidence-backed completion

Only the server classifies actions. The browser never selects an action class.

## Research execution v1

The schema reserves `unavailable`, `mock`, and `live` for long-term API
compatibility. Phase 29 fixtures and future Sprint 29 behavior are limited to
`unavailable` and `mock`.

Mock contracts require exactly:

`Demo research — not live marketplace data.`

Mock and unavailable contracts are not production eligible and must set every
live marketplace claim flag to `false`. A `live` payload requires Sprint 38
authority and real execution evidence; merely satisfying the schema does not
authorize or certify live behavior.

## Explicit confirmation boundary

Research proposal and research confirmation are separate state transitions.
An action with `propose_research` is not confirmation. Later implementation
must bind confirmation to the proposal ID, decision ID, context version,
principal, and an idempotency key before starting exactly one execution.

Phase 29.0 freezes this boundary in documentation and schemas only.

## Integrity digests

PiqScore and Recommendation snapshot hashes are opaque SHA-256 integrity values.
They do not define or reproduce either protected algorithm. Clients compare or
return these digests but do not generate canonical replacements.

Canonical UUID Results / Compare / Why adapt one owner-verified snapshot into
the Product Foundation view model. See
`docs/architecture/CANONICAL_UUID_CONSUMER_PRESENTATION.md`.

The Product Foundation authority is frozen separately by
`tests/contracts/fixtures/sprint29-authority-lock.json`. The validator checks:

- the manifest file SHA-256
- the recorded artifact-set aggregate
- the exact approved inventory
- the legacy README checksum
- source artwork checksums when `--artwork-root` is supplied

## Context-drift regression contract

The locked case requires the same ordered product IDs before and after the
battery follow-up unless research was explicitly requested or approved. Google
Pixel 9 128GB is recorded as a forbidden unapproved replacement. This is a
fixture-level invariant in Phase 29.0 and a mandatory behavioral regression in
a later authorized phase.

## API compatibility direction

Later additive APIs must expose these server-owned concepts without changing
existing endpoints or protected authorities. No Phase 29.0 file registers a
route or modifies OpenAPI. Any later API work remains subject to Sprint 24
compatibility gates.

## Traceability

`tests/contracts/fixtures/sprint29-contract-traceability.json` maps CC-01-01
through CC-01-24 to a stable future behavioral test ID, planned phase, and
contract artifact. Phase 29.0 tests require complete, unique coverage but do
not claim those future behaviors are implemented.
