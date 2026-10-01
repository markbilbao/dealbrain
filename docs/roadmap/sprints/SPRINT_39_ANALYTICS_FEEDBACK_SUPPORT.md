# Sprint 39 — Analytics, Feedback & Support

**Status:** IN PROGRESS
**Primary owner / domain:** Product analytics + support
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Soft yes — learning; hard if privacy claims require it

## Sprint 39.1 — consent-gated analytics foundation

This is the first implementation slice. Sprint 39 stays **IN PROGRESS**. It is not COMPLETE and not CLOSED.

### Provider decision for this slice

Initial analytics backend: **FIRST-PARTY MINIMAL EVENT STORE**.

EXT-15 remains `not_started`. The external register allows a privacy-safe first-party minimal-event fallback while no provider is provisioned. This slice is not Google Analytics, Meta Pixel, PostHog, Mixpanel, Amplitude, or advertising tracking. `ANALYTICS_PROVIDER` stays `None`. `CMP_VENDOR` stays `None`. EXT-22 remains `not_started`. EXT-29 remains `not_started`; this slice does not call Google, add a verification token, or claim Search Console property verification. Private UUID routes stay noindex.

### Implemented

- Explicit first-party analytics preference (`essential_only` or `analytics_allowed`), default essential-only, reversible, versioned, and server-validated
- Preference cookie `piqsavi_tracking_preference` (choice, schema, selected time only)
- Opaque analytics subject cookie created only after opt-in and deleted on opt-out
- Advertising remains unavailable
- Event schema `piqsavi.product_analytics.v1` with the roadmap event vocabulary and a closed property set
- `ProductAnalyticsSink`, `NullProductAnalyticsSink`, and `FirstPartyProductAnalyticsRepository`
- Consent-off suppression with zero analytics rows; consent-on durable rows in `operational_entities` namespace `product.analytics_events`
- Deterministic dedup by event id; conflicting contents fail closed; no in-memory authority and no new SQL table
- Feedback reports in `product.feedback_reports`, separate from analytics
- `/support#report` form for incorrect price, product fact, outdated offer, misleading Recommendation evidence, and source issue
- Helpful / not helpful controls that work with analytics consent off
- Server-side Ask submission and insufficient-evidence emission, without question or answer text
- View offer click instrumentation as `outbound_merchant_click` without storing the destination URL and without affiliate parameters

### Still remaining

- Broader funnel instrumentation, including decision started/completed coverage beyond this slice
- Beta-learning dashboards and staging populated-event evidence
- Monitored feedback/support workflow evidence beyond the existing `support@piqsavi.com` inbox
- EXT-15 external provider decision if still desired
- EXT-22 external CMP decision if still desired
- EXT-29 Search Console setup and verification
- Final retention/learning cadence evidence
- Production project separation

Search Console setup remains an owner action. Do not treat this slice as verification.

### Engineering retention

`PRODUCT_ANALYTICS_ENGINEERING_TTL_DAYS` is 400. That is an **ENGINEERING / PRODUCT TTL**, not legal retention. Sprint 39.1 does not run a purge job. See [`../../privacy/ENGINEERING_RETENTION.md`](../../privacy/ENGINEERING_RETENTION.md).

## Objective

Instrument consent-gated product analytics and a real feedback/bug/support path for **September public-beta product validation**.

### 2026-09-07 beta learning objective (owner lock)

The September beta exists to prove product usefulness, recommendation quality, shopper trust, completed buying decisions, merchant click-through, repeat usage, and product-market demand. Affiliate revenue is not a launch requirement and **no affiliate conversion/revenue metric is required for initial launch acceptance**. Affiliate conversion/revenue becomes a later monetization metric after affiliate activation.

**Priority measurements** (consent-gated; preserve privacy/consent requirements):

- decision started
- decision completed
- Results viewed
- merchant outbound click
- decision completion rate
- outbound CTR
- repeat decisions
- return visits
- Recommendation helpful / not helpful
- incorrect price / product / source report
- insufficient-evidence outcome

## Included requirements

- Analytics provider decision; consent-gated initialization
- Event schema; anonymous/authenticated identity; deduplication
- Events: registrations, verified registrations, login success/failure, DAU/MAU, searches, success/failure/zero/partial, latency, merchant/market coverage, recommendation/DealScore/explanation views, CTR, funnel abandonment, retention, frontend/backend/merchant/AI errors, slow pages/endpoints, feedback, bugs, support, deletion metrics, consent state
- Consent-aware measurement for: search started; research started/completed; **decision started**; decision completed; Results viewed; Compare opened; Why opened; Ask PiqSavi used; Recommendation refinement attempted/applied; research proposed; research confirmed; Save; Watch; View offer/outbound action / merchant outbound click; return visits; repeat decisions; insufficient-evidence outcome; connector/research failure; incorrect-information report; Recommendation helpful/not helpful; support contact
- Affiliate attribution / conversion / revenue events may exist in the later schema for post-activation monetization learning. They are **not** Sprint 39 launch-acceptance metrics.
- Preserve privacy/consent requirements. Do not weaken consent gates to learn faster.
- Retention policy for analytics
- Dashboards; beta-learning review cadence
- In-product feedback + bug report + support contact
- Public launch path to report incorrect price, incorrect product fact, outdated offer, misleading Recommendation evidence, or source issue
- Add consent-gated Conversational Continuity events for Ask open/close, question submission, evidence answer, insufficient evidence, Recommendation refinement, research proposal/confirmation/decline/start/partial/completion/failure, updated Results, reopen, expiry, and authentication transition.
- Do not send raw questions, answers, emails, product free text, full conversations, or session tokens to analytics.
- Do not collect unnecessary PII.
- Separate essential operational/security telemetry from non-essential product analytics.

### SEO measurement (Sprint 39)

- Google Search Console setup/verification (EXT-29)
- indexing/crawl monitoring
- organic landing traffic
- search landing → Ask PiqSavi
- landing → Results/decision
- landing → outbound merchant action
- organic returning-user measurement

Respect consent/privacy rules. Ranking position is not an acceptance guarantee.

## Explicit non-goals

- Counting logs as analytics done
- Growth experimentation platform
- Requiring affiliate conversion or affiliate revenue as a September launch-acceptance metric
- Starting Sprint 38 or enabling affiliate tracking under an analytics label

## External dependencies

- EXT-15
- EXT-16
- EXT-17
- EXT-22
- EXT-29

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
- Core funnel events visible, including the 2026-09-07 priority product-validation measurements
- Affiliate conversion/revenue is not required to close Sprint 39 launch-acceptance for September
- Support/feedback path reaches monitored inbox
- Report Incorrect Information path exists for price, product fact, outdated offer, misleading evidence, and source issues
- Logging-only paths are not labeled analytics-complete
- Search Console setup/verification recorded or explicitly deferred with no ranking claims
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
