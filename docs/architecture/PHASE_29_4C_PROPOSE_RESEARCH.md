# Phase 29.4C — `propose_research`

**Status:** Implemented on the conversational continuity path. Not a research engine.

**Depends on:** Phase 29.4A `answer_from_evidence`, Phase 29.4B `refine_session_recommendation`.

## Purpose

When a shopper asks something that cannot be answered or safely refined from already-evaluated evidence, PiqSavi may identify that new research is required and explicitly propose that research.

29.4C does **not** perform research. It creates the authorization boundary between:

- conversation using existing evidence
- future research that may expand or refresh the decision

Hard rule:

> Research requires explicit shopper confirmation. A proposal is not authorization, and confirmation in this phase is not execution.

## Routing boundary

Every decision-bound Ask turn resolves to exactly one server-selected action:

| Shopper intent | Action |
|---|---|
| Current evidence can answer | `answer_from_evidence` |
| Preference change within the evaluated set, and captured evidence is sufficient | `refine_session_recommendation` |
| Outside-set product, missing evidence, freshness, unevaluated source, destination re-evaluation, or evaluated-set expansion | `propose_research` |

The browser never chooses the action.

Examples:

| Example | Action |
|---|---|
| “Why is Bose now your pick?” | `answer_from_evidence` |
| “Comfort matters more.” | `refine_session_recommendation` |
| “What about AirPods Max?” | `propose_research` |
| “Which has the better microphone?” | `answer_from_evidence` if sufficient; otherwise `propose_research` |
| “What's the price today?” | `propose_research` |
| “Find something cheaper.” | `propose_research` |
| “Did you check Amazon?” | `answer_from_evidence` |
| “Check Amazon too.” | `propose_research` |

29.4C does not absorb every unknown question. Honest 29.4A/29.4B answers remain first.

## Proposal lifecycle

A created proposal is stored on the existing `ConversationContext` as `research_proposal`.

Statuses:

- `pending_confirmation` — proposed, not authorized, not running
- `cancelled` — shopper cleared it
- `replaced` — a newer pending proposal superseded it
- `research_confirmation_received_but_execution_unavailable` — explicit confirmation was recorded; execution is future work

Frozen conversation-action fixtures continue to use `awaiting_explicit_confirmation` as the contract spelling of a pending proposal.

One conversation has at most one active pending proposal.

## Explicit confirmation requirement

No research starts merely because:

- 29.4A could not answer
- 29.4B returned `insufficient_evidence`
- the shopper mentioned another product
- the shopper said “maybe”
- the shopper asked a factual question that needs freshness

Explicit confirmation examples: “Yes, research AirPods Max.”, “Yes, check the current prices.”, “Go ahead.” Those phrases classify confirmation; authorization still requires the exact `proposal_id` and `proposal_version`. Generic text alone does not authorize whichever proposal is currently active. See `docs/architecture/RESEARCH_AUTHORIZATION_HANDOFF_CONTRACT.md`.

Ambiguous replies such as “Maybe.”, “Interesting.”, or “What would you check?” do not authorize research. The proposal stays pending.

“Never mind.” cancels/clears the pending proposal.

A later phase owns the confirmation → certified live-research execution contract.

## Owner / session binding

Proposals are bound to the same owner, conversation, and canonical decision as 29.4A/29.4B.

Wrong owner and unknown UUID both look like “not found.” A tampered canonical decision cannot become the basis of a proposal. Client-supplied evaluated products, Recommendation, PiqScore, or research scope are ignored.

## Evidence / freshness / outside-set triggers

The server authors the scope from shopper intent and the trusted evidence packet:

- **Outside evaluated set** — preserve the shopper-supplied name; do not resolve SKU/storage/year unless already captured
- **Insufficient evidence** — 29.4A or 29.4B can hand off a missing topic such as warranty or microphone
- **Freshness required** — “today”, “now”, “still available”; historical snapshot prices are not treated as current
- **Requested source** — “Check Amazon too.” Capability-safe wording only; no certified-connector claim
- **Re-evaluation required** — destination-sensitive economics the current snapshot cannot support
- **Evaluated-set expansion** — “Find something cheaper.” may need options outside the current set

Scope stays proportional to the request. PiqSavi does not propose searching the whole internet or every marketplace.

## No-execution boundary

29.4C must not:

- perform web search
- call marketplace, merchant, Reddit, YouTube, or manufacturer connectors
- scrape or fetch current prices
- add products or offers
- update canonical evidence, PiqScore, Recommendation, or economics
- create a new canonical decision
- invent research results

## Evaluated-set and Recommendation immutability

Creating a proposal does not change:

- evaluated-set membership
- canonical Recommendation
- session Recommendation
- PiqScore values

If 29.4B already refined session Best Piq, that overlay remains. A later authorized research/re-evaluation is what may create a new canonical decision.

## Relationship to 29.4A

29.4A answers from captured evidence. If that evidence is definitive, 29.4C stays out of the way. If a material topic is missing (for example local warranty), 29.4C may propose researching that topic. 29.4A source-inventory questions such as “Did you check Amazon?” remain answers, not proposals.

## Relationship to 29.4B

29.4B may return `insufficient_evidence` when a priority change cannot be refined from captured facts. That outcome must not start research. 29.4C may transform it into a pending proposal. Supported refinements such as “Comfort matters more.” still stay on 29.4B.

## Relationship to the Research Authorization / Execution Handoff Contract

29.4C still owns proposal creation and the explicit-confirmation classifier. A later Research Authorization / Execution Handoff Contract turns explicit confirmation of the exact active proposal into a server-authoritative authorization.

Live research execution remains owned by Sprints 31–38. A proposal is not authorization, and authorization is not execution.
