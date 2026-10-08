# Sprint 39 — Analytics, Feedback & Support

**Status:** IN PROGRESS (2026-10-07). Audit verdict: SPRINT 39 IN PROGRESS — TRUE SPRINT 39 ENGINEERING BLOCKERS REMAIN. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY. The 2026-10-02 ENGINEERING COMPLETE reading is withdrawn.
**Primary owner / domain:** Product analytics + support
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Closure-readiness audit:** [`../evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md`](../evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md)
**Staging evidence:** [`../evidence/SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md`](../evidence/SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md)

**Sprint 39.4 staging evidence:** [`../evidence/SPRINT_39_4_IDENTITY_LIFECYCLE_STAGING_2026-10-07.md`](../evidence/SPRINT_39_4_IDENTITY_LIFECYCLE_STAGING_2026-10-07.md)
**Next-slice readiness audit:** [`../evidence/SPRINT_39_NEXT_SLICE_READINESS_AUDIT_2026-10-08.md`](../evidence/SPRINT_39_NEXT_SLICE_READINESS_AUDIT_2026-10-08.md)
**Beta blocker classification:** Soft yes — learning; hard if privacy claims require it

## Current closure reading (2026-10-02)

The audit above is the closure-reading authority. Sprint 39 stays IN PROGRESS. Engineering status is not ENGINEERING COMPLETE. The pre-Sprint-39.4 Class C count was 27. The current Class C count is 21. This is not COMPLETE / CLOSED, not PRODUCTION PROVEN, and not LAUNCH READY.

The 2026-10-02 engineering-complete reading is withdrawn. The 2026-09-07 priority measurements do not remove the Included requirements section. Sprint 39.4 adds consent-gated product-analytics events for registrations, verified registrations, login success, login failure, deletion metrics, and the guest-to-account authentication transition. Deploy Staging #43 proved registrations, login success, login failure, and deletion metrics. It did not prove verified registrations or authentication transition. No staging proof is claimed for those two. DAU/MAU, search analytics, merchant and market coverage, Recommendation views, DealScore / PiqScore views, funnel abandonment, frontend, backend, merchant, and AI errors, slow pages, slow endpoints, support-contact analytics, and conversation expiry remain unimplemented. Consented-subject counts are not account DAU or MAU.

The instruments that do exist remain: the consent gate, schema, dedup, first-party store, dashboard, feedback and incorrect-information path, support mailto, Ask open serialization, and the server observers that do not invent a decision. Core funnel counts stay 0.

Deploy Staging #41 remains the historical `ask_opened` failure. Deploy Staging #42 of `374c9e2f45cb1810626c4138b3a145d3cff170a0` recorded the corrected partial proof. Core funnel counts stay 0 because the public staging root is Early Access and no production caller creates the initial canonical decision. That chain stays with Sprint 29, Sprint 31, and Sprint 38. Sprint 38 remains ENGINEERING COMPLETE and IN PROGRESS, waiting on Sprint 41. Sprint 39 does not fabricate the chain.

The documented 400-day engineering TTL satisfies "Retention policy for analytics." A purge job is not a current Sprint 39 acceptance requirement. Account export and account deletion exclusions stay documented and are not a partial identity join. EXT-15, EXT-22, and EXT-29 stay `not_started`. Search Console stays explicitly deferred with no ranking claim. Affiliate tracking stays off.

Sprint 40 may still run in parallel. This reading does not start Sprint 40 or Sprint 41.

The 2026-10-08 readiness audit does not change this closure reading and does not implement a slice. Class C count remains 21. It selects one next engineering slice: canonical Results recommendation and PiqScore view observation, covering Recommendation views and DealScore / PiqScore views. Both rows are READY-B. Staging proof waits for a canonical Results serve. The other 19 Class C rows stay blocked. That selection is a planning layer. It does not change any A/B/C classification.

The dated 39.1, 39.2, and 39.3 sections below are slice history. Sprint 39.4 is the identity-lifecycle slice. Earlier residual lists are not the current closure checklist.

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
- Event schema `piqsavi.product_analytics.v1` with the full roadmap vocabulary. As of this slice the browser could submit only `results_viewed`, `compare_opened`, `why_opened`, and `outbound_merchant_click`, each with fixed surface / action / outcome semantics. Sprint 39.2 adds `ask_opened` and `ask_closed` to that client set. Other names stay server-owned and are rejected on `/analytics/events`. Trusted server code uses a separate validator. A client-supplied decision id that does not resolve for the current owner returns `decision_not_found` and writes no row
- `product.analytics_events` and `product.feedback_reports` are documented in the engineering PII inventory. Account export excludes them. Account delete does not cascade them in this slice. That is remaining privacy-integration work, not a legal retention exception
- `ProductAnalyticsSink`, `NullProductAnalyticsSink`, and `FirstPartyProductAnalyticsRepository`
- Consent-off suppression with zero analytics rows; consent-on durable rows in `operational_entities` namespace `product.analytics_events`
- Deterministic dedup by event id; conflicting contents fail closed; no in-memory authority and no new SQL table
- Feedback reports in `product.feedback_reports`, separate from analytics
- `/support#report` form for incorrect price, product fact, outdated offer, misleading Recommendation evidence, and source issue
- Helpful / not helpful controls that work with analytics consent off
- Server-side Ask submission and insufficient-evidence emission, without question or answer text
- View offer click instrumentation as `outbound_merchant_click` without storing the destination URL and without affiliate parameters

### Still remaining

Remaining at the end of 39.1. The 39.2 section below is the current slice. Do not read this list as the status after 39.2.

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

`PRODUCT_ANALYTICS_ENGINEERING_TTL_DAYS` is 400. That is an **ENGINEERING / PRODUCT TTL**, not legal retention. Sprint 39.1 does not run a purge job. Sprint 39.2 does not add one. A cookie max-age of 400 days does not delete stored rows. See [`../../privacy/ENGINEERING_RETENTION.md`](../../privacy/ENGINEERING_RETENTION.md). The 2026-10-02 audit classifies this documented policy as satisfying the current Sprint 39 retention-policy wording. It classifies an enforceable purge as not a Sprint 39 engineering blocker. Counsel still owns legal retention. This paragraph does not add a purge job.

## Sprint 39.2 — core funnel instrumentation and beta-learning dashboard

Sprint 39 stays **IN PROGRESS**. This slice does not close it, does not deploy staging, and does not mark EXT-15, EXT-22, or EXT-29 started.

### Implemented

- Server observers for research proposal, confirmation, decline, start, completion, and failure, recorded only after those services already transition. Closed production gates do not emit start or failure. `research_partial` stays uninstrumented because no authoritative partial transition exists
- `ask_evidence_answered` for evidence status `answered` only, with no answer text
- Browser `ask_opened` / `ask_closed` with exact surface, action, and outcome
- Recommendation refinement attempted versus applied, using the refinement service flag
- `updated_results_viewed` only when the server resolves an owner snapshot with `context_version > 1`
- `ProductLearningDashboardService`, separate from the Sprint 22 launch dashboard, Sprint 21 merchant analytics, and Sprint 19 shopper dashboard
- Internal `GET /api/v1/launch/product-learning` and `GET /api/v1/launch/product-feedback`, reusing the existing demo/internal launch admin token. Not production IAM
- Feedback review queue with report id, category, time, product id, context version, surface, status, and message. No owner digest, analytics subject, or decision id
- Learning cadence and an empty staging evidence template
- Search Console left explicitly deferred
- Dashboard and feedback review scan the newest inserted operational rows (`id` descending), then filter by event `occurred_at` or report `created_at`. Immutable rows share `seq = 1`, so `seq` is not the scan order. A truncated scan stays partial and still withholds returning and repeat-decision metrics

### Decision events

`decision_started` and `decision_completed` have emitters and tests, and no production caller. No current service creates the initial canonical decision snapshot. Definitions are in [`../../analytics/CORE_FUNNEL_EVENTS.md`](../../analytics/CORE_FUNNEL_EVENTS.md). The completion rate, when events exist, is a distinct authorized decision-hash ratio.

### Support paths

- Direct support email: the existing mailto to `support@piqsavi.com` reaches the monitored EXT-17 inbox. This slice does not re-provision mail
- Structured in-product feedback: stored in `product.feedback_reports` and shown on the internal review queue. These reports are not emailed

### Still remaining after 39.2

This residual list is the state at the end of Sprint 39.2, before Deploy Staging #42 and before the 2026-10-02 audit. The audit reclassifies it. Do not read it as the current closure checklist.

- Staging validation of the core funnel. Deploy Staging #41 succeeded and is recorded in the staging evidence note, then paused on `ask_opened` `contradictory_event`. At that time, filled controlled-flow evidence was still remaining after the serializer correction was redeployed. Deploy Staging #42 later recorded the corrected partial session. Core funnel counts stayed 0
- A production path that creates the initial canonical decision, so `decision_started` / `decision_completed` can be emitted truthfully
- `research_partial`, if a real partial transition is added later
- Final monitored workflow evidence beyond the existing support inbox and the internal review queue
- Retention purge. The 400-day engineering TTL is still not a delete job
- Search Console setup, or this deferral left in place with no ranking claim
- Production project and environment separation
- Account export and account deletion still exclude `product.analytics_events` and `product.feedback_reports`. No identity join was added
- EXT-15 external provider decision, if still desired
- EXT-22 external CMP decision, if still desired

## Sprint 39.3 — staging-discovered ask analytics payload correction

Sprint 39 stays **IN PROGRESS**. This slice does not close it, does not deploy, and does not mark staging validation complete. Sprint 38 is unchanged.

Deploy Staging #41 (run `36822959068`) of `287cdf11ff61bfdb09d412d1cb88927c86e3c799` returned host evidence `staging_ok`. Before the controlled flow, `product.analytics_events` and `product.feedback_reports` each had 0 rows, and neither scan was truncated. Explicit analytics opt-in succeeded (`analytics_allowed`, `explicit = true`). The first valid `POST /api/v1/analytics/events` for `ask_opened` returned HTTP 400 `contradictory_event`.

`ProductAnalyticsEventRequest.client_payload()` used `model_dump()`, which included declared optional fields set to `None`. Those keys sit outside `EXACT_CLIENT_FIELDS` for `ask_opened` and `ask_closed`, so a valid browser open or close failed at the API boundary. The correction omits declared `None` fields and then restores `__pydantic_extra__`, including unknown extras whose value is null, so unknown, forbidden, and server-owned rejections stay in force.

`FORBIDDEN_ANALYTICS_FIELDS`, `SERVER_OWNED_FIELDS`, `EXACT_CLIENT_FIELDS`, and `CLIENT_EVENT_SEMANTICS` are unchanged. Consent semantics, dashboard formulas, and feedback behavior are unchanged. This slice adds no analytics event, calls no Shopify API, and adds no third-party analytics.

The failed staging attempt remains in [`../evidence/SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md`](../evidence/SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md). Do not delete it after a later deploy succeeds.

Deploy Staging #42 later deployed this correction at `374c9e2f45cb1810626c4138b3a145d3cff170a0` and recorded `ask_opened` as `recorded`. That success does not close Sprint 39 and does not remove the #41 failure from the evidence file.

## Sprint 39.4 — consent-gated identity lifecycle product analytics

Sprint 39 stays **IN PROGRESS**. It is not ENGINEERING COMPLETE, not COMPLETE / CLOSED, not PRODUCTION PROVEN, and not LAUNCH READY. The implementation slice did not deploy and did not change Deploy Staging #41 or #42 evidence. Post-merge Deploy Staging #43 is recorded in the 2026-10-07 evidence note. The pre-Sprint-39.4 Class C count of 27 is historical. The current Class C count is 21.

### Implemented

Server-owned product events, recorded only after the existing transition succeeds:

- `registration_completed` after `POST /api/v1/auth/register` creates the account and session
- `registration_verified` after `POST /api/v1/auth/verify-email/confirm` marks the account verified
- `login_success` after `POST /api/v1/auth/login` authenticates
- `login_failure` after that login endpoint has determined the attempt failed
- `account_deleted` after the existing Sprint 28 account-deletion operation completes
- `authentication_transition` after `POST /consumer/claim-decision` returns `claimed` true

The browser cannot submit these names. `POST /api/v1/analytics/events` returns `server_owned_event` and writes zero rows.

Consent reuses `analytics_context_for_request` and `ProductAnalyticsService.record_server_event`. Analytics off writes zero rows and does not change auth or claim behavior. These routes do not mint an analytics subject. Explicit consent without an existing opaque subject suppresses the event. `identity_kind` stays the helper's reading of the request owner. A successful login while that owner is still a guest stays `guest`.

`login_failure` stores only `auth_failed`, `validation_failed`, or `rate_limited`. Unknown email, inactive account, and a wrong password share `auth_failed`. Security audit details are unchanged and are not copied into the product row.

Event ids are random server UUIDs. Email, user id, session id, token, conversation id, and the analytics subject cookie are not id material. Definitions are in [`../../analytics/IDENTITY_LIFECYCLE_EVENTS.md`](../../analytics/IDENTITY_LIFECYCLE_EVENTS.md).

`ProductLearningDashboardService` adds `metrics.identity_lifecycle` with those six counts and `partial`. A truncated scan marks the section partial and counts only scanned rows. The section is not account DAU or MAU. `account_deleted` does not claim legal erasure beyond the Sprint 28 deletion operation.

Deploy Staging #43 of `d0f117b426010f629ec32b7d3f96f39dc6b865f7` (run `37567160567`, release `rel-20261007T024027Z-d0f117b42601`, host `staging_ok`) recorded `registration_completed`, `login_success`, `login_failure`, and `account_deleted`. Final `partial` was false. `registration_verified` and `authentication_transition` stayed 0. No staging proof is claimed for those two. The controlled address, credentials, tokens, session ids, and cookies are not stored in the evidence note.

### Still unimplemented

These current Class C blockers remain unimplemented. The pre-Sprint-39.4 count was 27. This list is the current count of 21:

- DAU / MAU
- searches, search success, search failure, search zero, search partial, and search started
- latency
- merchant coverage and market coverage
- Recommendation views and DealScore / PiqScore views
- funnel abandonment
- frontend errors, backend errors, merchant errors, and AI errors
- slow pages and slow endpoints
- support-contact analytics
- conversation expiry

### Next bounded slice (not selected)

No next engineering slice is selected by this reconciliation. Conversation expiry remains Class C. It is not currently executable: `cleanup_expired` has no production caller, and read-time expiry has no consent-bearing request. Do not implement expiry until an authoritative request-scoped caller exists. `/search` is not selected either. That route is still an Early Access fixture redirect and does not expose truthful success, failure, zero, or partial outcomes. The next action is a bounded next-slice readiness audit across the remaining 21 Class C rows. Sprint 40 may still run in parallel. This reading does not start that audit or Sprint 40.

## Next-slice readiness (2026-10-08)

The readiness audit named above is that audit. It does not implement the slice. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. Class C count remains 21. No A/B/C classification changes.

The selected next engineering slice is canonical Results recommendation and PiqScore view observation. The exact rows are Recommendation views and DealScore / PiqScore views. No row is READY-A. Those two rows are READY-B. A non-zero staging count waits until a canonical Results response is served. Fixture Results pages stay out of the measurement. Public Results stays disabled. The other 19 Class C rows stay blocked, including search, conversation expiry, DAU / MAU, coverage, abandonment, support-contact analytics, and the latency and error rows. Sprint 40 may still run in parallel. This section does not start Sprint 40 and does not deploy.

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
