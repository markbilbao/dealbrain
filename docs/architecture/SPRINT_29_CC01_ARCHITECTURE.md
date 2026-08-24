# Sprint 29 Phase 29.0 — CC-01 Architecture Contract

**Status:** Frozen for Phase 29.0 implementation

**Implementation baseline:** `f80f0ef81874e51f42c27aed014d368091c75741`

**Launch gate:** CC-01 Conversational Continuity under EC-02 / EC-22

**Visual authority:**
[`../roadmap/evidence/PIQSAVI_CONVERSATIONAL_CONTINUITY_PRODUCT_FOUNDATION_MANIFEST.md`](../roadmap/evidence/PIQSAVI_CONVERSATIONAL_CONTINUITY_PRODUCT_FOUNDATION_MANIFEST.md)

## Purpose

This contract freezes the additive architecture for Sprint 29 before behavior is
implemented. Phase 29.0 adds contracts, fixtures, schemas, traceability, and
integrity validation only. It does not add conversation behavior, persistence,
decision APIs, consumer pages, or research execution.

## Existing architecture to extend

Conversational Continuity must extend, rather than replace:

- `app.domain.entities.shopping_assistant.ConversationContext`
- `app.domain.interfaces.shopping_assistant_repository.ConversationRepository`
- the existing Shopping Assistant service and dependency graph
- the canonical Results, Recommendation, and PiqScore/DealScore authorities

No second conversation subsystem, Results authority, scoring engine, or
Recommendation engine is permitted.

## Consumer architecture lock

The approved consumer architecture is:

- FastAPI document routes
- FastAPI-served semantic HTML
- shared CSS
- native vanilla-JavaScript ES modules
- one reusable conversation controller on Results, Compare, and Why Best Piq
- server-owned decision context, PiqScore, and Recommendation state

The planned additive document routes are:

- `/search`
- `/results/{decision_id}`
- `/compare/{decision_id}`
- `/why-best-piq/{decision_id}`

The planned static application root is `app/static/consumer/`. Phase 29.0 does
not create that directory or any consumer runtime files.

React, Vite, TypeScript, SPA routing, a Node production build, and client-side
scoring or Recommendation authority are prohibited.

## Server-owned decision boundary

Search will eventually create an immutable-versioned decision snapshot. A
conversation refers to the decision by `decision_id` and `context_version`; it
does not reconstruct the evaluated set from a follow-up prompt.

The decision context carries:

- the exact evaluated product set
- canonical PiqScore snapshots and integrity digests
- the canonical Recommendation, Best Piq, and alternatives
- captured evidence, provenance, freshness, and unknowns
- guest or authenticated ownership
- context version and timestamps
- affiliate-neutrality invariants

The normative data shape is
[`SPRINT_29_DECISION_CONTEXT_CONTRACT.md`](SPRINT_29_DECISION_CONTEXT_CONTRACT.md)
and `schemas/sprint29-decision-context.schema.json`.

## One closed action classification

Every follow-up resolves to exactly one server-selected action:

1. `answer_from_evidence`
2. `refine_session_recommendation` — implemented in Phase 29.4B as a
   session-level overlay. Canonical snapshots stay immutable. See
   [`PHASE_29_4B_SESSION_RECOMMENDATION_REFINEMENT.md`](PHASE_29_4B_SESSION_RECOMMENDATION_REFINEMENT.md).
3. `propose_research` — implemented in Phase 29.4C as a pending confirmation
   boundary only. Research is not executed. See
   [`PHASE_29_4C_PROPOSE_RESEARCH.md`](PHASE_29_4C_PROPOSE_RESEARCH.md).

The client may render the returned action but must not choose it, calculate a
score, or alter the evaluated set. Research proposals require a separate,
explicit confirmation contract before execution.

## Stable evaluated-set invariant

Follow-up questions operate on the current decision snapshot. The evaluated
product set remains byte-for-byte stable unless the user explicitly requests
or approves new research and that research completes into a new canonical
decision version.

The frozen regression case is:

- iPhone 17 Pro Max
- Samsung Galaxy S25 Ultra 512GB
- follow-up: `Which one has better battery?`
- forbidden unapproved replacement: Google Pixel 9 128GB

This case is encoded in
`tests/contracts/fixtures/sprint29-context-drift.json`. Phase 29.0 validates the
fixture and invariant contract; behavioral enforcement starts only after a
later phase receives owner authorization.

## Ownership and persistence boundary

Decision and conversation access will be bound to either a verified guest
session or an authenticated principal. Ownership validation is server-side.
Guest-to-account transfer must validate both principals and rotate ownership
credentials. Durable persistence and repository changes are explicitly outside
Phase 29.0.

Session Recommendation refinements remain scoped to the active decision.
They do not write persistent account preferences unless the user explicitly
chooses to save them.

## Research truth boundary

The execution-mode contract reserves three values:

- `unavailable`
- `mock`
- `live`

Sprint 29 may exercise only `unavailable` and non-production `mock` behavior.
Mock output must display exactly:

> Demo research — not live marketplace data.

No consumer surface may claim live merchants, live prices, live availability,
refreshed research, or live marketplace coverage while execution is mock.
The `live` enum value is reserved for compatibility but is fail-closed until
Sprint 38 provides and certifies the executor.

## Protected authorities

Sprint 29 must not change:

- canonical PiqScore/DealScore calculations or semantics
- canonical Recommendation calculations or semantics
- affiliate-neutral candidate inclusion or ordering
- Early Access behavior
- existing demo behavior
- Product Foundation artwork or its recorded checksums

Affiliate commission, partner priority, and conversion value remain downstream
of organic selection and cannot influence any conversational action.

## Phase sequencing

- **29.0:** contracts, schemas, fixtures, traceability, integrity validation
- **29.1:** extend the existing conversation domain and repository ports
- **29.2+:** later owner-approved persistence, snapshots, actions, research
  boundary, APIs, documents, and interaction integration

Each implementation phase uses RED evidence on its working branch, followed by
the minimum implementation and a fully GREEN commit/PR. Knowingly failing tests
are never merged.

## Phase 29.0 exit conditions

Phase 29.0 is complete only when:

- all Phase 29.0 schemas are valid Draft 2020-12 JSON Schemas
- every frozen fixture validates against its schema
- all 24 CC-01 acceptance criteria have unique forward traceability
- the visual manifest document, artifact inventory aggregate, and optional
  source artwork checksums validate
- the context-drift fixture contains the exact frozen products and follow-up
- targeted and complete test suites are green
- the diff contains no protected-authority or runtime behavior changes
