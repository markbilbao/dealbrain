# Sprint 39 — Analytics, Feedback & Support

**Status:** Planned
**Primary owner / domain:** Product analytics + support
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Soft yes — learning; hard if privacy claims require it

## Objective

Instrument consent-gated product analytics and a real feedback/bug/support path for beta learning.

## Included requirements

- Analytics provider decision; consent-gated initialization
- Event schema; anonymous/authenticated identity; deduplication
- Events: registrations, verified registrations, login success/failure, DAU/MAU, searches, success/failure/zero/partial, latency, merchant/market coverage, recommendation/DealScore/explanation views, CTR, affiliate attribution, funnel abandonment, retention, frontend/backend/merchant/AI errors, slow pages/endpoints, feedback, bugs, support, deletion metrics, consent state
- Retention policy for analytics
- Dashboards; beta-learning review cadence
- In-product feedback + bug report + support contact
- Add consent-gated Conversational Continuity events for Ask open/close, question submission, evidence answer, insufficient evidence, Recommendation refinement, research proposal/confirmation/decline/start/partial/completion/failure, updated Results, reopen, expiry, and authentication transition.
- Do not send raw questions, answers, emails, product free text, full conversations, or session tokens to analytics.
- Separate essential operational/security telemetry from non-essential product analytics.

## Explicit non-goals

- Counting logs as analytics done
- Growth experimentation platform

## External dependencies

- EXT-15
- EXT-16
- EXT-17
- EXT-22

## Implementation deliverables

- Analytics SDK/server events
- Feedback endpoints/UI
- Dashboards

## Documentation deliverables

- Event schema
- Retention
- Learning cadence

## Required tests

- Consent off ⇒ no non-essential events
- Schema validation
- Dedup tests

## Required staging evidence

- Dashboards populated from staging traffic

## Required production evidence

- Prod project separated

## Acceptance criteria

- Consent gate proven
- Core funnel events visible
- Support/feedback path reaches monitored inbox
- Logging-only paths are not labeled analytics-complete
- Consent-off behavior emits no non-essential Conversational Continuity analytics.
- Conversational events are schema-validated and deduplicated.
- Event properties use anonymous decision/session hashes, action type, surface, turn number, evidence count, latency/freshness bands, error code, and context version only.

## Predecessor sprints

28, 29

## Parallelizable work

40

## Go / no-go gate

Go if consent + core events + support path work

## Rollback or contingency

Disable non-essential analytics

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
