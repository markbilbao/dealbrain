# Research Authorization / Execution Handoff Contract

**Status:** Implemented on the conversational continuity path. Not live research.

**Depends on:** Phase 29.4C `propose_research`.

**Does not implement:** certified live research execution (Sprints 31–38).

## Purpose

Phase 29.4C can propose research and record that a shopper said yes. That is not enough.

This phase creates the secure bridge between:

- a 29.4C research proposal
- future certified live research execution in Sprints 31–38

After explicit confirmation of the exact active proposal, the server authors a bounded **research authorization**. The authorization is the artifact future execution may consume.

A generic “Yes.” never itself becomes enough to execute research later. Authorization is bound to the exact approved request.

Authorization-producing confirmation must be correlated to the exact proposal ID and proposal version. The server must never interpret a delayed generic confirmation as approval of whichever proposal is currently active.

Hard rule:

> Execution is still unavailable. This phase ends at a valid authorized handoff. It does not perform merchant, network, or connector research.

## Proposal vs authorization vs execution

| Stage | Meaning | Implemented here |
|---|---|---|
| 29.4A `answer_from_evidence` | Existing evidence can answer | Yes, unchanged |
| 29.4B `refine_session_recommendation` | Preference change inside the current evaluated set | Yes, unchanged |
| 29.4C `propose_research` | New evidence is required; pending confirmation | Yes, unchanged |
| **Research authorization** | Shopper explicitly confirmed the exact active proposal; server froze that scope | **Yes** |
| Certified live research execution | Connectors, merchants, search, rerank, new canonical decision | **No** — Sprints 31–38 |

Routing order is unchanged. Authorization logic attaches only to explicit confirmation of an active proposal. Ordinary “yes” replies outside that context do not create an authorization.

## Confirmation correlation

A confirmation may authorize only the exact proposal it was created for. It must never authorize whichever proposal happens to be current when the request arrives.

Authorization-producing confirmation must carry the exact server-authored:

- `proposal_id`
- `proposal_version`

Those fields identify the proposal only. They do not give the client authority over scope, products, sources, evidence topics, destination, evaluated set, Recommendation, or PiqScore. The server still loads the trusted proposal and freezes that server-authored scope.

The rendered **Yes, research that** action must bind to the proposal identity from that rendered response. It must not read a global “latest proposal” that can change before the click arrives.

If a later turn replaces proposal A with proposal B, a still-visible chip for A must still submit A’s ID and version. The server rejects that as `stale_research_proposal`. B is not authorized. A is not resurrected.

Missing trustworthy correlation fails closed:

- typed generic text such as “Go ahead.”, “Yes.”, or “Sure.” with no bound proposal ID/version does not authorize the current proposal
- named text such as “Yes, research AirPods Max.” without ID/version is not a security boundary and does not authorize
- a client `confirmation_token` is never enough by itself; it is not cryptographically bound to a proposal and cannot select the current proposal

Ordinary Ask messages do not require proposal ID or version. Only an authorization-producing confirmation does.

## Exact authorization binding

A `ResearchAuthorization` is frozen and bound to:

- owner identity digest (`principal_type` + `principal_id` + `session_id`, never exposed)
- `conversation_id`
- canonical decision UUID
- canonical context version
- proposal ID
- proposal version
- frozen approved research scope
- server-derived idempotency key
- authorization ID and authorization version (`1`)
- created timestamp
- status

The frozen scope includes:

- proposal reason
- evaluated product IDs at authorization time
- shopper-supplied outside-set product names, unexpanded
- requested evidence topics
- requested sources
- destination label if applicable
- expansion / freshness / canonical-update flags

A deterministic `scope_digest` covers those stable server-authoritative values plus decision ID, context version, and proposal ID/version. Presentation prose is omitted.

## Idempotency

Explicit confirmation is idempotent.

Repeated confirmation of the same owner, conversation, decision, context version, proposal ID, proposal version, and frozen scope returns the same logical authorization. Distinct proposal versions produce distinct authorizations.

**Idempotency key authority is the server.** The key is derived from owner binding, conversation, decision, context version, proposal ID/version, and scope digest.

If the client supplies a `confirmation_token`, it is accepted only after that exact proposal is already bound and is **not** used as execution identity. A generic reusable token cannot select the current proposal. Proposal ID/version validation remains mandatory. The browser cannot mint an unrelated research run by sending a different token.

Near-simultaneous confirmations use conversation compare-and-swap. A lost race reloads session state and reuses the authorization already stored under the same server key.

## Frozen scope

Once created, approved scope is immutable. Future execution cannot silently widen it.

Authorization for “Research AirPods Max against the current evaluated headphones” cannot later become a search of every premium headphone and every merchant.

Authorization for “Check Amazon too.” cannot later become Amazon + Shopee + Lazada + Reddit + YouTube.

Client-supplied scope fields are ignored. If more scope is needed later, execution must fail closed or request a new proposal.

Shopper-supplied outside names stay as typed. Authorization does not invent USB-C, year, or merchant SKU variants.

## Stale / replaced / cancelled behavior

Fail closed. Do not resurrect. Do not silently upgrade.

| Event | Result |
|---|---|
| No pending proposal, shopper says “Go ahead.” | Safe conversational refusal. No authorization. |
| Pending proposal, generic “Go ahead.” with no proposal ID/version | Unbound. No authorization. Current proposal stays pending. |
| Ambiguous reply (“Maybe.”, “Interesting.”) | Proposal stays pending. No authorization. |
| Rendered chip for A arrives after B replaced A | `stale_research_proposal`. Does not authorize B. Does not resurrect A. B stays pending. |
| Confirmation names a replaced proposal (v1 AirPods after v2 Beats) | Stale. Does not authorize v2. Does not resurrect v1. |
| Client `proposal_id` / `proposal_version` does not match the active proposal | Stale. No authorization. |
| Matching proposal ID with a stale version | Stale. No authorization. |
| Pending proposal cancelled before confirmation | No authorization. A late confirmation for that ID/version fails closed. |
| Authorized but unconsumed, then “Never mind.” | Authorization becomes `cancelled`. Cannot validate for execution. |
| Authorized but unconsumed, then a material new research request (Beats instead of AirPods, new destination, and similar) | Previous authorization is `invalidated`. New request needs its own proposal and confirmation. |

A cancelled or replaced proposal cannot be authorized.

## Context-version behavior

Authorization is bound to the canonical context version captured on the trusted proposal.

If a later canonical decision replaces that context, the previous authorization is stale. The validator fails closed. The authorization is not upgraded to the newer decision.

A new decision requires a new proposal/authorization path where appropriate.

Destination-sensitive confirmation is the same rule: an Amazon-price authorization does not silently cover a later Cebu re-evaluation.

## Owner / conversation isolation

Authorization is owner- and conversation-bound.

Wrong-owner authorize, inspect, cancel, consume, or validate-for-execution attempts follow existing non-existence-leak behavior: they look like “not found.” The server does not reveal whether another user’s authorization exists.

## Authorization lifecycle

Statuses:

- `authorized_pending_execution`
- `consumed`
- `cancelled`
- `invalidated`

There is no `researching`, `completed`, or `failed` state. Execution does not exist yet.

Creating authorization does **not** mark it consumed. Consumption belongs to future execution.

## Single logical execution

One authorization is valid for one logical research execution.

Repeated worker retries of that same run must reuse the same server idempotency key. The same authorization must not generate multiple unrelated research runs.

`mark_research_authorization_consumed(...)` exists for Sprints 31–38. The Ask confirmation path does not call it.

## Validation interface

Future execution must call:

`validate_research_authorization_for_execution(...)`

before doing anything. It fails closed when:

- owner binding mismatches (not-found, no existence leak)
- conversation, decision, or context version mismatches
- proposal ID/version mismatches
- scope digest mismatches
- authorization is cancelled, invalidated, or consumed

Connectors must not reconstruct this security model themselves.

## Future execution handoff

`get_authorized_research_handoff(...)` returns a bounded packet only when validation succeeds:

- authorization ID/version
- decision ID and canonical context version
- proposal ID/version
- frozen scope and scope digest
- conversation binding
- server idempotency key
- `execution_available = false`

The packet does not include merchant credentials, connector implementations, live data, or results.

In this phase the packet is a validated handoff contract, not permission to start research.

## Recommendation integrity

Creating or reusing authorization does not mutate:

- PiqScore or PiqScore digest
- canonical Recommendation or its digest
- session Best Piq
- evaluated-set membership
- canonical economics
- canonical snapshot content hash
- canonical context version

The current decision remains exactly as it was.

## Persistence and session loss

Authorization is stored on the existing `ConversationContext` as `research_authorizations`, next to the research proposal.

That is the same session-scoped conversation persistence already used by 29.4A–C. No new database migration is added.

Implications for future execution:

- If the session is lost or expired, authorization is gone.
- Fail closed. Do not reconstruct an executable authorization from browser text.
- Future research then requires a new proposal and a new explicit confirmation.

This phase does not silently make authorization durable across sessions.

## No-live-research boundary

Authorization and handoff modules must not import or call HTTP clients, marketplace connectors, web search, merchant APIs, Reddit, YouTube, manufacturer fetch, repricing, new products, new offers, new canonical decisions, Recommendation reranking, or PiqScore calculation.

Affiliate commission cannot influence source selection, product expansion, scope, or execution priority. Scope comes only from the shopper-approved proposal.

## Proposal state after authorization

- The proposal remains historically identifiable.
- It is no longer `pending_confirmation`.
- Status becomes `research_confirmation_received_but_execution_unavailable`.
- The proposal records the corresponding `authorization_id`.
- The conversation stores the authorization.
- Repeated confirmation returns that same authorization.

`pending_confirmation` and an active executable authorization are never both current.

## Relationship to 29.4C

29.4C still owns proposal creation, replacement, cancellation of a pending proposal, and the explicit-confirmation classifier.

This phase consumes that confirmation and turns it into a server-authoritative authorization. It does not bypass 29.4A/29.4B/29.4C routing.

## Relationship to Sprints 31–38

Sprints 31–38 own certified research orchestration, router/provider execution contracts, loading/partial/failure evidence, and any new canonical decision that research may produce.

The next true implementation step is:

> Connect validated authorizations to the certified research orchestration path owned by Sprints 31–38, beginning with router/provider execution contracts rather than bypassing roadmap ownership.

Until that work exists, live research execution remains **not implemented**.
