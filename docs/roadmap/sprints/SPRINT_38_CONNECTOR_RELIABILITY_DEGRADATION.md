# Sprint 38 — Connector Reliability & Honest Degradation

**Status:** IN PROGRESS (2026-09-30). Engineering foundation, authorization/planning handoff, repository-backed breaker state, durable authorized-execution preparation, a durable live-start claim, HALF_OPEN single-probe lease, exact authorization consumption on that claim, and a Shopify execution adapter with authoritative trace and durable outcome persistence. Not COMPLETE / CLOSED. Live execution is NOT OPERATIONAL. The adapter is proven only with fake transports. Real Shopify calls stay 0. Routing stays 0. Public PH shopping coverage stays disabled. Production composition cannot reach the transport.
**Primary owner / domain:** Marketplace reliability / ops
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes with live HTTP / multi-connector launch

## Current engineering foundation (2026-09-26)

Sprint 38 has started. It is not complete. Overall engineering status is IN PROGRESS. Live research operational status is NOT OPERATIONAL. Those are separate facts: `SPRINT_38_STATUS` is IN PROGRESS, and `SPRINT_38_LIVE_EXECUTION_STATUS` is NOT OPERATIONAL. The current public beta has one certified PH connector, `ph-shopify-global-catalog`, and that provider stays DISABLED. Routing stays 0. Public certified shopping markets stay 0. `SHOPPING_RESEARCH_EXECUTION_MODE` stays disabled. This foundation does not call Shopify and does not deploy.

The scripted circuit breaker is deterministic chaos-test state on one in-memory connector. It is not evidence of a persistent production breaker across separate shopper requests. Persistent production breaker hardening remains Sprint 38 work before closure.

Classification for the current PH-only scope:

- A. Reuse Sprint 31 timeout, retry, breaker, and kill-switch contracts, Sprint 31 planning-only execution, Sprint 32 reduced certification, and Sprint 37 fail-closed destination re-evaluation. Do not duplicate those systems.
- B. Implement now: execution identity and states, owner-bound idempotent confirmation, truthful non-live traces, the request-scoped live-mode fail-closed gate, a Shopify execution refusal that does not perform HTTP, scripted timeout / 429 / 5xx / retry / kill-switch behavior, an in-memory chaos-test breaker that is not a persistent production breaker, one-connector no-merchants-available behavior, prior-decision preservation, connector health distinct from `/ready`, and Shopify cache refusal.
- C. Owner validation after this foundation, not in this change: a real Shopify call once routing, operational eligibility, and a deployed profile exist.
- D. Sprint 41: production deploy, production UCP profile, AWS/DNS/TLS, and the deployed kill-switch drill.
- E. Sprint 42: alerts, paging, synthetic production probes, and incident-runbook proof. EXT-25 stays optional.
- F. Not a blocker for this one-connector beta: affiliate-provider failure, because affiliate monetization is out of launch scope.
- G. Preserved and not a close of this beta: multi-connector chaos, production evidence across multiple connectors and markets, and cross-merchant aggregation as a live shopper claim. Deterministic multi-provider tests may exercise the orchestration. Those tests are not live connectors and are not launch evidence.

One certified connector failing is no live merchant result. It is not a successful multi-merchant partial result. `DESTINATION_REEVALUATION_IMPLEMENTED` stays False until a validated evidence-backed executor exists.

## Authorization / planning / execution handoff (2026-09-26)

This slice connects the existing Ask PiqSavi chain to Sprint 38 preparation. It does not make live execution operational.

The server-authored `ResearchAuthorization` remains the confirmation authority. Explicit confirmation still creates that authorization. Sprint 38 does not parse a second confirmation token. Execution identity is derived from `authorization.idempotency_key`. A client confirmation token is not execution identity. The scripted `ResearchExecutionLedger.confirm` path remains chaos-test bookkeeping and is not the shopper authority.

A preparation binding pins that authorization to one current plan. The same authorization and the same plan reuse one execution. Silent plan drift is rejected as `authorization_plan_conflict` and does not replace the stored plan or create a second execution. `AuthorizedExecutionLedger` is an in-process preparation ledger, not durable live-execution storage. Explicit trusted replanning or rebinding, if later required before live execution, remains future Sprint 38 work.

Preparation accepts the trusted `ResearchExecutionPlan` built from the authorization handoff. Browser market, capability, source, and provider values cannot replace the plan step. The live-mode gate reads the plan step target and stays closed: mode disabled, provider disabled, routing absent, public market not activated.

`execute_research_plan` prepares or refuses without network I/O. A valid plan returns `prepared_but_live_unavailable` (or a blocked outcome when the plan has no eligible step). It does not mark a provider attempted, does not set `source_checked`, does not populate the authoritative trace, and does not mark execution completed. `mark_research_authorization_consumed` is not called. The authorization stays `authorized_pending_execution` because no live attempt started. Consumption remains the later single-logical-execution boundary, when a live connector attempt actually starts.

The authoritative production trace is `app.domain.entities.research_execution.ResearchExecutionTrace`. It stays empty. The scripted `ExecutionTrace` cannot be projected onto that model when it records an attempt, so the two cannot disagree.

The shopper confirmation answer still says execution is not available and that no sources were checked. No new canonical decision snapshot is created. Sprint 41 stays UNSTARTED.

## Reliability state (2026-09-27)

This slice adds production breaker state and failure control. It does not call Shopify, enable routing, or make live execution operational. The 2026-09-26 foundation note that persistent breaker hardening was still future work is superseded for this store only. The scripted connector breaker remains in-memory chaos-test state.

Production rows use the existing ``operational_entities`` table and namespace ``research.provider_reliability``. No Alembic migration was added. The identity is ``provider_id|market``. ``seq`` is the revision. A stale revision raises a conflict and does not overwrite the newer row. Absent rows are closed at revision 0. A stored row is what production research-provider health loads. The composition function receives the repository and does not open a database connection or substitute a closed snapshot. ``PRODUCTION_BREAKER_PERSISTED`` means ``OperationalResearchReliabilityRepository`` survives a new repository and a new database connection after commit. It does not mean production is deployed, that a row already exists, or that the breaker has been live-validated. ``InMemoryResearchReliabilityRepository`` and ``ScriptedConnector.circuit_breaker`` are not that evidence.

States are closed, open, and half-open. The injected clock is the only time source. Three consecutive breaker-worthy failures open the breaker. Breaker-worthy categories are timeout, unavailable, and unknown. Rate limit, quota, credential, kill switch, circuit-open, and partial results are recorded and do not increment or open it. Open blocks execution. Half-open is reached only at the configured reopen time (30 seconds). A half-open success closes the breaker and resets the failure count. A half-open breaker-worthy failure opens it again. These transitions are repository tests, not live validation.

Kill switch is stronger than the breaker. Provider ``DISABLED`` is stronger than a closed breaker. Disengaging the kill switch does not make a disabled provider live. Certification, a closed breaker, and application readiness do not make the provider available. Routing absence keeps live execution unavailable. ``/ready`` can stay true while merchant availability is false.

The research-provider health view keeps certified, operationally available, healthy, merchant availability, and live distinct. Operational availability is provider status, kill switch, and a closed breaker. Merchant availability is that serving contract. Healthy also requires a recorded successful attempt. Static ``AVAILABLE`` status is not healthy. Live stays false. The current ``ph-shopify-global-catalog`` row is certified for the reduced capability set, operationally disabled, not healthy, merchant availability false, and live false. One disabled connector aggregates to merchant availability false. A deterministic two-provider aggregate can show the formula and is not live evidence.

Before a future live connector attempt, permission must include provider operational status, the kill switch, and the persisted breaker. Routing, certification, and a passed live-mode flag do not override an open breaker. ``assess_persisted_live_permission`` exposes that contract and does not invoke a connector. ``production_live_mode_assessment`` stays fail-closed because live mode is disabled. The persisted breaker is not connected to HTTP.

``AuthorizedExecutionLedger`` stays in-process. Durable execution identity before HTTP is deferred to a later Sprint 38 slice. This slice does not store raw principal ids, browser confirmation tokens, secrets, or Shopify responses. It does not add probes, paging, or alert destinations. Sprint 42 owns those. Sprint 41 stays UNSTARTED. Sprint 38 stays IN PROGRESS. Live execution stays NOT OPERATIONAL. ``SHOPIFY_LIVE_CALL_PERMITTED`` stays false. ``SHOPPING_RESEARCH_EXECUTION_MODE`` stays disabled. ``DESTINATION_REEVALUATION_IMPLEMENTED`` stays false.

## Durable authorized-execution preparation (2026-09-27)

This slice supersedes the reliability-section deferral of authorized-execution records for preparation only. It does not complete Sprint 38, does not start live HTTP, and does not consume an authorization.

Production preparation now writes one ``prepared_unavailable`` row in the existing ``operational_entities`` store, namespace ``research.authorized_executions``. No Alembic migration was added. The lookup identity is the existing ``authorized_execution_id`` derived from the server authorization key. The raw key, raw principal id, session id, browser confirmation token, secrets, and Shopify payloads are not stored. The same authorization and the same plan reuse that row across a new repository, a new service, and a new database session. A different plan is ``authorization_plan_conflict`` and does not rewrite ``plan_id``. A stale revision does not overwrite a newer row. A persistence failure returns ``blocked_persistence`` and does not fall back to ``AuthorizedExecutionLedger``.

The in-memory ledger remains a test double. ``ShoppingAssistantService`` production composition uses ``OperationalAuthorizedExecutionRepository``. Durable existence does not consume the authorization. Status stays ``authorized_pending_execution``. The authoritative ``ResearchExecutionTrace`` stays empty. No source is checked, no connector is invoked, and live stays false. The prior canonical decision stays unchanged.

A database outage during preparation is ``PersistenceUnavailableError`` and the preparation outcome is ``blocked_persistence``. The confirmation response stays the truthful non-live authorization response. It does not become an internal server error, and it does not fall back to ``AuthorizedExecutionLedger``.

Future live start was recorded here as three unimplemented phases. The later 2026-09-30 sections are the current truth: the claim and HALF_OPEN lease, then the Shopify adapter, authoritative trace, and durable outcome. This preparation slice itself did not perform HTTP. Sprint 42 still owns alerts, paging, synthetic probes, and incident operations. Sprint 41 stays UNSTARTED. Sprint 38 stays IN PROGRESS. Live execution stays NOT OPERATIONAL.

## Safe live-start claim and HALF_OPEN single-probe lease (2026-09-30)

This slice adds the concurrency boundary that must exist before any future connector HTTP call. It does not perform that call. Sprint 38 stays IN PROGRESS. Live execution stays NOT OPERATIONAL. No migration was added. The execution claim and the probe lease are fields on the existing ``operational_entities`` rows.

``DURABLE_LIVE_START_CLAIM_IMPLEMENTED`` is true. A prepared execution can move to ``claimed_for_attempt``. That state is not running. The row records ``claimed_at``, ``claim_expires_at``, and ``claim_digest``. The raw claim capability is returned once to the claiming worker and is not stored. The lease is 30 seconds. An unexpired claim blocks every other worker with ``execution_already_claimed``. An expired claim can be reclaimed by compare-and-swap. The previous capability then fails ``validate_active_execution_claim``. A stale revision cannot overwrite the newer row. The same authorization with a different plan remains ``authorization_plan_conflict``. This is at-most-one active claimant, plus expiry and recovery. It is not exactly-once external HTTP.

``HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED`` is true. The lease is per provider and market, on ``ProviderReliabilityState``: ``half_open_probe_claim_digest``, ``half_open_probe_claimed_at``, and ``half_open_probe_expires_at``. The raw probe capability is not stored. The lease is 30 seconds. CLOSED does not take this lease, and a normal execution claim is still required before future HTTP. OPEN before ``reopen_at`` cannot take a probe. HALF_OPEN allows one unexpired lease. A second worker is ``half_open_probe_already_claimed``. An expired lease can be reclaimed. The old probe capability then fails ``validate_active_half_open_probe``. For a HALF_OPEN attempt the same worker must hold both the execution claim and the probe lease. Both writes share one SQLAlchemy transaction. If either compare-and-swap or the database fails, the transaction rolls back: no partial execution claim and no orphan probe lease. The reason is ``claim_persistence_unavailable``. There is no in-memory production fallback.

A claim does not call ``record_success`` or ``record_failure``. It does not set ``last_success_at``, ``last_failure_category``, or ``last_attempt_at``. Claiming is not health evidence. The provider is not marked healthy, live, or attempted. The authoritative trace stays empty. ``attempted``, ``source_checked``, ``connector_invoked``, ``http_invoked``, and ``live_execution_started`` stay false. The prior decision is unchanged.

The claim runs only after the existing gates: trusted authorization, pinned plan, exact plan target, certified connector, exact routing, public market, live mode, provider status, kill switch, and the persisted breaker. Current production still fails before a write. ``ph-shopify-global-catalog`` stays DISABLED. Routing stays 0. Public certified shopping markets stay 0. ``SHOPPING_RESEARCH_EXECUTION_MODE`` stays disabled. A fixture cannot take a production live-start claim. ``SHOPIFY_LIVE_CALL_PERMITTED`` stays false. ``LIVE_RESEARCH_EXECUTION_OPERATIONAL`` stays false. ``DESTINATION_REEVALUATION_IMPLEMENTED`` stays false. ``execute()`` stays unimplemented. Shopify live calls stay 0.

Authorization consumption is still not solved atomically. ``mark_research_authorization_consumed()`` only returns an in-memory replacement. ``ResearchAuthorization`` is stored inside ``shopping_assistant.conversations``. The execution claim and the probe lease share one ``operational_entities`` transaction. The conversation row uses that same table, but this slice does not update it in that transaction. Before HTTP, the next slice must either compare-and-swap the conversation inside the claim transaction, or keep the durable claim as the single-logical-execution lock and reconcile authorization status in the outcome transaction. Until then, status stays ``authorized_pending_execution``. The claim does not create a second active claimant.

Production deployment remains Sprint 41 and stays UNSTARTED. Alerts, paging, synthetic probes, and incident operations remain Sprint 42. Connector HTTP and outcome recording remain later Sprint 38 work. This slice does not start Sprint 41 or Sprint 42 and does not mark Sprint 38 COMPLETE.

## Atomic authorization consumption (2026-09-30)

This slice closes the authorization boundary that the live-start claim left open. Sprint 38 stays IN PROGRESS. Live execution stays NOT OPERATIONAL. No migration was added. The conversation row already lives in ``operational_entities`` / ``shopping_assistant.conversations``.

``AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM`` is true. A claim that passes every live-start gate compare-and-swaps three facts in one SQLAlchemy transaction: the execution claim, the HALF_OPEN probe lease when the breaker is HALF_OPEN, and the exact ``ResearchAuthorization`` inside the conversation. ``mark_research_authorization_consumed()`` moves that authorization from ``authorized_pending_execution`` to ``consumed``. ``authorization_version`` is not incremented. The conversation ``persistence_version`` increments through the existing conversation compare-and-swap. A CLOSED claim consumes the authorization and writes no probe lease. A failed gate, a lost execution race, a lost probe lease, a conversation version conflict, or a database outage rolls every write back. The authorization stays pending when no claim commits.

A consumed authorization does not authorize a new execution. ``validate_research_authorization_for_execution()`` still rejects ``consumed``. ``validate_consumed_authorization_for_execution_resume()`` accepts it only for the same execution, authorization, decision, plan, conversation, and owner, and only after the previous claim has expired. An unexpired claim stays ``execution_already_claimed``. Reclaim issues a new capability and does not consume the authorization again. The previous capability no longer validates. Cancellation and invalidation still do not reopen a consumed authorization.

The future connector timeout is the existing 5_000 ms ``TimeoutPolicy`` / Shopify candidate timeout. The Sprint 32 anonymous harness used a 30 second socket timeout, which equals the claim lease and is not the future HTTP timeout. One second of strict slack keeps timeout plus margin shorter than both the 30 second execution claim lease and the 30 second HALF_OPEN probe lease. No HTTP call is added. The validated Anonymous catalog contract is recorded for the next slice and is not executed. Current production still cannot claim: mode disabled, provider DISABLED, routing 0, public certified markets 0, production UCP profile undeployed. The authoritative trace stays empty. ``attempted``, ``source_checked``, ``connector_invoked``, ``http_invoked``, and ``live_execution_started`` stay false. Consuming the authorization does not mutate the canonical decision, PiqScore, recommendation, evaluated offer set, or economics.

## Shopify execution adapter and durable outcome (2026-09-30)

This slice adds the Shopify-specific execution adapter behind the existing gates. Sprint 38 stays IN PROGRESS. Live execution stays NOT OPERATIONAL. No migration was added. Real Shopify calls in this change are 0. Fake transport results are not live evidence and are not ``SourceMode.LIVE``.

``app.research.shopify_global_catalog_execution`` is the orchestration. ``app.research.shopify_global_catalog_transport`` is the injected transport. ``StaticResearchProvider.execute`` still raises ``NotImplementedError``. The adapter reuses the Sprint 32 anonymous request helpers and ``normalize_shopify_global_catalog_offer``. It does not add a second Shopify protocol. Supported capabilities are product discovery, offer discovery, current pricing, and availability. Shipping, taxes/import, promotion evidence, and review evidence fail closed before transport. The only tools are ``search_catalog`` and ``get_product``. ``lookup_catalog``, pagination past the first page, bulk ids, and promoted or affiliate fields stay forbidden.

The HTTP timeout is 5 seconds. Retry count is 0. Timeout plus the one-second cleanup margin stays shorter than the 30-second execution claim and the 30-second HALF_OPEN probe lease. If either lease has less than that budget left, the adapter returns ``claim_budget_insufficient`` and does not call transport. It does not extend the lease.

The adapter clock is injected. Production-capable composition defaults to UTC ``datetime.now``. Tests inject a deterministic clock. Immediately before transport the adapter reads that clock once. That reading is ``attempt_started_at``. The adapter reloads the execution and checks the active claim capability, the plan pins, the consumed authorization for that same execution, the provider/market/capability/source, the persisted breaker, the HALF_OPEN probe capability when the breaker is half-open, and the remaining lease budget, all at that start time. Only then does it commit ``running``. ``running`` is not used when the claim is first taken. The attempt-start row stores no raw claim capability, no raw probe capability, and no raw Shopify body. A caller-supplied finish time is not production authority.

HTTP runs outside the database transaction. After transport returns, the adapter reads the clock again. That reading is the finish time used for normalization ``checked_at``, post-transport claim and HALF_OPEN validation, trace ``finished_at``, and breaker timestamps. The preflight lease budget remains, and it does not replace that post-transport check. If the execution claim or the HALF_OPEN probe has expired by the finish time, the returned response is not committed and the breaker is not updated. The outcome transaction then reloads the execution, checks the claim capability again, checks the probe capability when HALF_OPEN, writes the authoritative ``ResearchExecutionTrace``, updates the breaker, releases the execution claim, and commits. A lost compare-and-swap does not overwrite a terminal row and does not invent success. A persistence failure leaves the row ``running`` and does not report a durable success. Reconciliation of an ambiguous post-HTTP crash uses the same service clock and does not replay HTTP.

Connector success is a validated JSON-RPC response whose products all normalize. HTTP 200 alone is not success. HTTP status is classified before the body is treated as JSON-RPC. HTTP 429 maps to ``RATE_LIMIT``, HTTP 401/403 maps to ``CREDENTIAL``, and HTTP 5xx maps to ``UNAVAILABLE``, including when the body is not JSON. Another non-200 status maps to ``UNKNOWN`` / ``http_error``. Only an HTTP 200 body that is not valid JSON-RPC maps to ``UNKNOWN`` / ``malformed_jsonrpc``. A non-timeout connection failure, such as DNS failure, connection refused, or network unreachable, maps to ``UNAVAILABLE``. Timeout still maps to ``TIMEOUT`` and trace status ``timed_out``. Retry count stays 0. A normalization refusal maps to ``PARTIAL``. Breaker-worthy failures are still timeout, unavailable, and unknown. Rate limit, credential, and partial are recorded and do not increment the breaker. HALF_OPEN success closes and resets the breaker and clears the probe lease. HALF_OPEN breaker-worthy failure reopens the breaker and clears the probe lease. A completed neutral failure also clears the probe lease. ``record_success`` is not called for a normalization failure.

Returned currency is the source currency. PHP is request context only. Shipping, tax, import, voucher, and checkout costs stay unknown. Unknown is not zero. No final landed cost is computed. Raw Shopify responses are not persisted. The durable row keeps a sanitized request digest, normalized-offer digests, currency, and minor-unit amount. A normalized-offer digest is a deterministic sha256 of product id, variant id, currency, minor-unit amount, and seller identity. It is not a shopper-visible evidence id, it does not contain the raw Shopify body, and it is not provenance-backed live evidence. Fake-transport success leaves ``ResearchExecutionTraceStep.evidence_ids`` empty because no evidence repository record exists. ``evaluated_offer_count`` does not require a matching evidence-id list. Evidence ids, when a later slice stores real evidence, must be resolvable references and must not be these digests. Fake successes use observation kind ``synthetic``.

Durable states now include ``running``, ``completed``, ``failed``, and ``outcome_unknown`` in addition to ``prepared_unavailable`` and ``claimed_for_attempt``. A terminal execution cannot be claimed again. The consumed authorization does not start a second execution.

Crash recovery is explicit and not exactly-once HTTP. A crash before the attempt-start commit leaves ``claimed_for_attempt``. After that claim expires, the same execution can be reclaimed. A crash after the attempt-start commit and before the outcome commit is ambiguous: HTTP may have happened. Recovery does not replay HTTP and does not fabricate success or failure. After the claim lease expires, reconciliation commits ``outcome_unknown``, releases the execution claim, and does not record breaker success or failure. It does not clear a HALF_OPEN probe lease early, so another probe is not granted until that lease expires under the existing policy.

``execute_production_shopify_catalog`` never calls a transport. Production gates stay closed: mode disabled, provider ``DISABLED``, routing 0, public certified markets 0, production UCP profile undeployed, ``SHOPIFY_LIVE_CALL_PERMITTED`` false, ``LIVE_RESEARCH_EXECUTION_OPERATIONAL`` false, ``DESTINATION_REEVALUATION_IMPLEMENTED`` false. No canonical updated Results decision is created. The prior decision is unchanged.

Later owner-controlled Shopify validation is not part of this slice and was not run. It may happen only when repository truth shows all of these gates together: an operational provider status other than the current ``DISABLED`` row, real non-fixture routing, approved PH market activation, the production UCP profile deployed under Sprint 41, the exact certified capability and source, an explicitly approved live execution switch, and this claim/trace/degradation path. Until then, real Shopify calls stay 0. Do not run the Sprint 32 harness, ``catalog.shopify.com``, or an owner live validation from this repository state.

Production deployment and the production UCP profile stay Sprint 41, which stays UNSTARTED. Alerts, paging, synthetic production probes, and incident-runbook proof stay Sprint 42. This slice does not start Sprint 41 or Sprint 42 and does not mark Sprint 38 COMPLETE. Fake transport evidence is not production live certification and does not enable public PH shopping coverage.

## Objective

Harden and consolidate certified connector behavior into production-grade cross-connector reliability and honest degradation — **not** introduce basic timeout/retry/failure handling for the first time (those minimum contracts are owned by Sprint 31 and validated per market in 32–36).

## Included requirements

- Shared production-grade circuit-breaker behavior across connectors
- Aggregated connector and market health
- Cross-merchant partial-result orchestration
- Stale-cache policy
- Stale-cache, degraded-mode, fallback, and refresh timing must **respect** merchant-specific certified TTL / freshness policy constraints from Sprint 31 model + 32–36 certification (must not override or weaken them)
- Connector synthetic probes
- Production alerting integration hooks
- Provider-status tracking
- Reliability consistency across all certified connectors
- No-merchants-available product behavior
- Incident runbook consolidation
- Production evidence across multiple connectors and markets
- Incomplete-coverage / degradation UI disclosures coordinated with Sprint 29 states
- AI-provider and affiliate-provider failure behavior
- Application readiness must not imply full merchant availability
- Fixture/simulated paths cannot be labeled live (release verification support for EC-21)
- Provide the production reliability and truthfulness contract for user-confirmed Conversational Continuity research.
- A research execution must have a real execution ID and evidence-backed queued, running, partial, completed, failed, or cancelled state.
- Connector, merchant, offer, price, review, freshness, and coverage statements must be derived from actual execution and certified provider capabilities.
- Repeated confirmations must not create duplicate research executions.
- Partial, stale, timeout, quota, connector-failure, and no-merchants-available outcomes must preserve the prior decision and degrade honestly.
- Own production live-research execution including: connector timeout behavior; retries where permitted; circuit breakers; partial failure; source health; degradation states; cache/freshness; research execution trace; attempted sources; succeeded sources; failed sources; timed-out sources; evaluated-offer count; truthful UI disclosure
- Shared ownership of live owner-bound decision creation: this sprint owns live execution; Sprint 31 owns routing; Sprint 29 owns snapshot presentation. Fixture-created UUIDs are not sufficient for Sprint 45.

### Hard live-mode rule

`SHOPPING_RESEARCH_EXECUTION_MODE=live` may not be production-enabled unless:

1. at least one relevant certified real connector exists for the requested supported market, and
2. truthful partial-failure/execution-trace handling is operational.

Mock remains non-production only.

## Explicit non-goals

- Owning the first appearance of timeout/retry/failure result types (31)
- Owning merchant contractual capability/policy interpretation or legal-terms mapping (31 model; 32–36 provider certification)
- Per-market legal certification (32–36)
- Multi-region active-active
- Guaranteeing provider SLOs

## External dependencies

- EXT-25

## Implementation deliverables

- Shared breaker/retry hardening wired across certified connectors
- Aggregated health model
- Probe jobs
- UI/API degradation fields for multi-connector failure
- Provider status process

## Documentation deliverables

- CONNECTOR_HEALTH updates
- Consolidated incident runbook RB-connector
- Provider status process

## Required tests

- Chaos across multiple connectors: timeout, 429, 5xx, credential fail
- Partial aggregation tests
- No-merchants-available path
- Fixture-as-live guard
- Cache/degradation/refresh paths do not exceed certified merchant TTL / freshness constraints

## Required staging evidence

- Probes green; multi-connector chaos drill recorded

## Required production evidence

- Alerts routed in 42

## Acceptance criteria

- Multi-connector chaos drill passes with honest user-visible degradation
- Aggregated health + kill switch disable merchants within agreed SLO
- `/ready` remains correct when merchants are down
- Consistency review across certified connectors signed
- Basic timeout/retry/failure handling is confirmed present from 31/32–36 — Sprint 38 evidence is hardening, not first introduction
- Stale-cache / degradation / fallback / refresh behavior respects certified merchant TTL/freshness policy constraints (does not invent or reinterpret merchant legal permissions)
- Confirmed Ask PiqSavi research uses the certified connector path and produces truthful, provenance-backed execution states.
- No research occurs before explicit confirmation.
- No timer, animation, fixture, or simulated count is accepted as evidence of live execution.
- Completed research returns a canonical updated-Results snapshot; failed or partial research does not silently replace the prior valid decision.
- `SHOPPING_RESEARCH_EXECUTION_MODE=live` is fail-closed unless a relevant certified real connector and truthful partial-failure/execution-trace handling exist
- Execution traces record attempted, succeeded, failed, and timed-out sources plus evaluated-offer count
- A real shopper request can create an owner-bound schema-current canonical decision from live certified evidence
- Mock remains non-production only

## Predecessor sprints

31 (contracts); ideally ≥1 market from 32–36 certified or in certification

## Parallelizable work

Remaining market certs; 39 analytics; 40 security prep

## Go / no-go gate

Go if multi-connector chaos + aggregated health + kill switch evidenced

## Rollback or contingency

Disable live connectors; fixture paths remain non-live

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
