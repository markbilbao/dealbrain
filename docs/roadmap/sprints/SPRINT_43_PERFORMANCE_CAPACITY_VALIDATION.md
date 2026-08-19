# Sprint 43 — Performance & Capacity Validation

**Status:** Planned
**Primary owner / domain:** Performance eng / ops
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes for announced size

## Objective

Produce capacity evidence for announced rollout sizes; forbid unproven capacity claims.

## Included requirements

- Load-test tooling; representative staging dataset
- API concurrency; search burst; merchant slowdown/outage; AI slowdown tests
- DB pool/limit/index/slow-query review
- Cache design; distributed cache decision
- Queue/worker/retry/DLQ/idempotency review as in scope
- Horizontal scaling readiness; autoscaling decision; single-instance risk removal decision
- Static asset/bundle/image/CDN optimization checks
- Rate-limit capacity; AI/merchant quotas; graceful overload
- Celebrity/creator spike simulation
- Evidence gates for 1k registered, 1k DAU, 10k registered, 10k DAU, short spike
- Validate shared ConversationRepository capacity across restarts and multiple application workers.
- Load-test decision-context reads/writes, bounded conversation history, session cleanup, AI-answer concurrency, and confirmed-research job concurrency.
- Measure database payload size, cleanup/index behavior, connection-pool pressure, idempotency storage, queue requirements, provider quotas, and graceful overload.
- Decide from evidence whether the operational JSON store is sufficient for beta or whether a dedicated indexed table or Redis adapter is required behind the same repository port.

## Explicit non-goals

- Claiming 10k DAU without evidence
- Full multi-region scale

## External dependencies

- EXT-25

## Implementation deliverables

- Load test suites
- Reports
- Tuning PRs as needed

## Documentation deliverables

- Capacity report
- Announced size recommendation

## Required tests

- Automated load scenarios where feasible

## Required staging evidence

- Load tests on staging or prod-like

## Required production evidence

- Optional prod canaries

## Acceptance criteria

- Written capacity evidence for the size Sprint 45 will announce
- If 10k gates fail, announcement reduced accordingly
- Spike test report filed
- Capacity evidence covers the announced concurrent conversational sessions, AI-answer rate, and research-execution rate.
- Restart and multi-worker tests preserve authorized active sessions without cross-session leakage.
- Overload fails honestly without duplicate research, corrupted context, fabricated progress, or canonical Results mutation.

## Predecessor sprints

41, 38

## Parallelizable work

44 drafting

## Go / no-go gate

Go if evidence matches intended announcement

## Rollback or contingency

Reduce rollout percentage / announcement

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
