# Sprint 39 next-slice readiness audit — 2026-10-08

**Audit verdict:** One bounded next engineering slice is selected. It is not implemented in this audit.

**Sprint closure status:** IN PROGRESS. Not COMPLETE / CLOSED.

**Engineering status:** Not ENGINEERING COMPLETE. Class C count remains 21. The pre-Sprint-39.4 Class C count was 27. This audit does not implement any Class C row and does not change any Included-requirements A/B/C classification.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `b45ec8972ba6d38c1007850aa58919b44d89ac5c`

**Closure-reading authority:** [`SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md`](SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md)

**Sprint definition:** [`../sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md`](../sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md)

This audit is a planning layer. Readiness classes (`READY-A`, `READY-B`, `BLOCKED-DOMAIN`, `BLOCKED-DEFINITION`, `BLOCKED-PRIVACY`, `BLOCKED-OPERATIONS`) do not replace closure classes A/B/C. No row below moves from C to A or B.

No deploy was performed. No Shopify call was made. Sprint 40 was not started. Sprint 41 was not started. Affiliate tracking was not enabled. No third-party analytics provider was activated. Runtime code is unchanged.

Sprint 38 stays IN PROGRESS. Its engineering status stays ENGINEERING COMPLETE. Its closure validation stays blocked on Sprint 41. Sprint 40 may still run in parallel with Sprint 39. This audit does not start Sprint 40.

The six rows already reconciled by Sprint 39.4 stay outside this audit: registrations, login success, login failure, and deletion metrics remain Class A; verified registrations and authentication transition remain Class B. No repository fact contradicted that reconciliation.

## What this audit asked

For each of the 21 remaining Class C rows:

- Is there an authoritative domain or request transition today?
- Does that transition have a real production-capable caller?
- Can Sprint 39 observe it without fabricating shopper behavior, treating fixture-only behavior as production truth, changing another sprint's domain semantics, inventing a scheduler, duplicating operational telemetry, weakening consent, or waiting on a Sprint 41 production deployment?
- Can the measurement be a small bounded Sprint 39 slice now?
- If not, what exact dependency blocks it?

Product analytics stays separate from security audit logs, infrastructure metrics, connector health, application logs, load-test output, and raw access logs. Counting those logs as analytics remains a non-goal.

## Selected slice

**Selected next engineering slice:** canonical Results recommendation and PiqScore view observation.

**Rows in that slice:**

- Recommendation views
- DealScore / PiqScore views

**READY-A rows:** none.

**READY-B rows:** Recommendation views; DealScore / PiqScore views.

**Reason:** These two rows share one existing render, `_hero_card` on a canonical Results page. That render includes the Best Piq recommendation and the PiqScore gauge together. The unavailable Results page includes neither. `results_viewed` fires for every Results document, including unavailable, so it does not distinguish the two elements. The observer can be added on the canonical branch the Results route already uses for `updated_results_viewed`, consent-gated, with fixture and unavailable responses excluded. Writing that observer does not enable public Results, does not create a canonical snapshot, does not require Sprint 41, and does not duplicate Sprint 42 monitoring. A non-zero staging count still waits until a real canonical Results response is served. That is READY-B, not READY-A.

**Proposed server-owned event names for the future slice, not added here:** `recommendation_viewed` and `piqscore_viewed`. Both stay out of `CLIENT_EVENT_NAMES`. The visible score control is the PiqScore gauge. Results does not render a second DealScore control. `piqscore_viewed` is the observation for the combined DealScore / PiqScore row. DealScore remains the Sprint 5 scoring engine.

**Slice bounds:**

- Emit only from the Results response when `presentation_mode` is `canonical`, `data_unavailable` is false, the recommendation hero is in the HTML, and the hero PiqScore gauge is in the HTML.
- Check the hero and the gauge separately. Today `_hero_card` includes both. A later template that drops one must not record the other.
- Use the existing consent context. Analytics off writes zero rows. Do not mint an analytics subject on this GET.
- Store the existing decision hash and context version. Do not store the numeric score, the query, or a raw decision id.
- Do not emit for fixture catalogs, the unavailable page, compare, why, or alternate-card gauges.
- Do not alias `results_viewed` or `updated_results_viewed`.
- Do not turn unfinished HTML surfaces on. Do not treat a fixture staging visit as proof.

**Staging proof now:** No. Production redirects `/results/{decision_id}` home. The public staging root is Early Access. No production caller creates the initial canonical decision. That chain stays Sprint 29 / 31 / 38, and Sprint 38 closure still waits on Sprint 41. The slice can land before that proof.

**Rows explicitly not in the slice:** DAU / MAU; searches; search success; search failure; search zero; search partial; search started; latency; merchant coverage; market coverage; funnel abandonment; frontend errors; backend errors; merchant errors; AI errors; slow pages; slow endpoints; support-contact analytics; conversation expiry.

## Family findings

### Search

`GET /search` in `app/api/consumer.py` is presentation. Production (`unfinished_html_surfaces_enabled()` false) returns 303 to `/`. Development and staging, where fixture catalogs are permitted, return 303 to `/results/{catalog}`. Any other environment returns 303 to `/results/unavailable`. The handler logs `consumer_search` and writes no product-analytics row. It has no success, failure, zero, or partial outcome.

The Sprint 4 engine is `MarketplaceIntelligenceService.search`. `get_marketplace_connectors()` registers mocked `ShopeeConnector` and `LazadaConnector`. Those adapters filter canned listings by title and seller. A miss returns an empty tuple. The connectors do not fail and do not return a partial set. There is no separate started signal.

Production callers of that engine are:

- `GET /api/v1/marketplace/search`
- `GET /api/v1/dealscore/search` through `DealRecommendationService.recommend`
- `GET /api/v1/recommendations/search` through `ShoppingRecommendationService.recommend`

`DealRecommendationService` labels the listing source as a mock connector. `app/static/demo.html` calls those APIs. `app/static/consumer/js/account.js` may send the browser to `/search?` after sign-in. That hits the presentation redirect.

`GET /api/v1/price-history/search` and `GET /api/v1/user/searches` are other domains. `ShoppingAssistantService.query` is Ask, research, and evidence. Those paths already have their own Sprint 39 observers. They are not the six search rows.

No non-fixture authoritative search result transition exists. All six search rows stay `BLOCKED-DOMAIN`.

### Latency, slow requests, and errors

`RequestLoggingMiddleware` records `duration_ms` and sets `X-Response-Time-Ms`. That log is Sprint 22 operational telemetry. It is not consent-gated. Sprint 25 states API latency SLOs from load-balancer or log duration. Sprint 42 owns error tracking, metrics, dashboards, connector monitoring, and AI-provider monitoring, and has not started. Sprint 43 owns load-test and capacity evidence, including search bursts. None of those define the Sprint 39 product rows, and copying them into `product.analytics_events` would count logs as analytics.

`latency_band` is an optional property on the product schema (`under_100ms`, `under_300ms`, `under_1s`, `under_3s`, `over_3s`). No caller passes it. `emit_research_observations` does not. The bands are a vocabulary, not a defined population. "Slow" has no page set and no endpoint set.

Frontend JavaScript has no error listener. A first-party listener could be added later without a third-party tracker. There is no classified frontend error transition to observe now, and a generic `window.onerror` sink would risk raw exception text.

Backend handlers exist. Several map failures with `str(exc)`. Request status in the access log is operational. There is no sanitized product classification of backend errors.

`research_failed` already records a bounded `block_reason` after confirmed research starts and does not complete. That event is the separate connector / research failure row, which is Class B. Connector health in `docs/CONNECTOR_HEALTH.md` is Sprint 18 state for a disabled provider. It is not a shopper merchant-error event.

AI transports expose bounded provider codes (`timeout`, `rate_limited`, `malformed`, `unavailable`). Sprint 42 owns AI-provider monitoring. The shopping assistant's `fallback_reason` is an operational string, not a product event. Ask already records `insufficient_evidence` and `ask_evidence_answered` for those answer statuses only. No separate product AI-error transition exists.

This family does not form a slice now. Consent can stay on product events while operational metrics stay independent. That separation is a reason to leave the middleware alone, not a reason to wrap it.

### Coverage

Merchant coverage and market coverage are listed with product events. No formula says whether they count shoppers who saw covered merchants, or a server-side certified catalog.

What exists today is derived registry state:

- `production_certified_shopping_markets()` returns an empty catalog. Public certified shopping markets stay 0. Sprint 37 owns that honesty.
- `ph-shopify-global-catalog` is registered with `operational_status` DISABLED. Routing policies in the production catalog stay empty. `_CONFIGURED_BUCKET` is 0. Sprint 32 / 38 own that provider state.
- The product-learning `coverage` object counts consented analytics subjects. It is not merchant or market coverage.

Publishing DISABLED, routing 0, and certified markets 0 on the learning dashboard would be a true registry snapshot and a false analytics event. The Included requirements do not define a derived coverage metric those constants would satisfy. Shopper-observed coverage has no live evaluated-set transition while routing stays 0. Both rows stay `BLOCKED-DEFINITION`. This audit does not change Sprint 37 or Sprint 38 truth.

### Recommendation and score views

`app/static/consumer/js/product_analytics.js` emits `results_viewed` whenever `data-page` is `results`. The unavailable Results page still has that attribute and renders neither a recommendation nor a score. Fixture Results pages render both inside a labeled demo catalog. Canonical Results (`page_view_from_snapshot`) sets `presentation_mode` to `canonical` and `data_unavailable` to false, then `_results_main` calls `_hero_card`. That hero includes the Best Piq recommendation and `#piqscore` with `piqscore_gauge`. Compare and why can also show gauges. Those pages are not this pair of rows. Explanation views remain the existing `why_opened` row, which is Class B.

The server already knows the mode. `results_page` already calls `emit_updated_results_viewed` only for a canonical snapshot with `context_version > 1`. A sibling observer can use the same request and the same consent gate. Production does not serve the page: `unfinished_html_surfaces_enabled()` is false when `app_env` is production, and the route redirects home. The observer is implementable now. Staging proof of a non-fixture view is not.

### Funnel abandonment

`docs/analytics/CORE_FUNNEL_EVENTS.md` defines decision completion rate and Results-to-outbound CTR. It does not define abandonment. It names no denominator, terminal state, timeout, or stage boundary. The word "abandoned" in the `decision_completed` rule means the caller passes `canonical_persisted=False` and the writer stores nothing. That is the absence of a completion event, not an abandonment metric. No inactivity window is authorized. The row stays `BLOCKED-DEFINITION`.

### DAU / MAU

Consented analytics subjects in `ProductLearningDashboardService._coverage` and `_retention`, and the `identity_lifecycle` counts, are explicit non-DAU readings. `docs/analytics/BETA_LEARNING_CADENCE.md` says so. `user_id` is forbidden on product events. Account export still has no trusted account-wide mapping, and Sprint 39 must not add a partial identity join.

`UserSession.last_seen_at` is updated when an auth session is validated. It is stored with `user_id` on the session. It is not a privacy-safe account activity digest. Sprint 43 lists evidence gates for 1k DAU and 10k DAU. Those gates consume a capacity number. They do not define the product metric, the activity that counts, or the window. The 400-day engineering TTL is a storage horizon, not a DAU definition.

The row needs both an activity definition and a privacy-safe account digest that does not store raw account ids. The readiness class is `BLOCKED-PRIVACY` because the current subject model is the wrong population and no allowed identity model can hold account DAU. The missing definition is part of the same block.

### Support contact

The support path that reaches `support@piqsavi.com` is already Class A. This row is the analytics event `support_contact`.

The support page renders `mailto:support@piqsavi.com`. A click can be seen in the browser. It does not prove an email was sent. `support_contact` is server-owned, so the browser cannot submit it. No server route sends support mail, and no delivery webhook exists.

The report form writes `product.feedback_reports`. Categories map to `incorrect_information_report` or `bug_report`. They do not map to `support_contact`. No `record_server_event` caller uses `support_contact`. `app/privacy/contacts.py` uses the same field name for the public email address. That is contact copy, not an analytics emission.

The Included requirements say "support contact." They do not choose among link clicked, form submitted, and email delivered. The form-submitted reading is already a different event. A click reading would claim less than delivery and more than the product can prove. No request-scoped action can truthfully emit `support_contact`. The row stays `BLOCKED-DOMAIN`.

### Conversation expiry

Re-checked on this `main`. `cleanup_expired` exists on the conversation repository port, the in-memory repository, and the database repository. Application code does not call it. The only callers are `tests/unit/test_shopping_assistant_service.py` and `tests/unit/persistence/test_sprint29_phase_29_2_conversation_persistence.py`. There is no scheduler, cron, or request-scoped cleanup job.

`get()` on both repositories deletes an expired conversation and returns `None`. The caller cannot tell expiry from a missing id, and the repository call has no analytics consent. Sprint 29 owns conversation TTL. Sprint 39 still must not add a scheduler, a synthetic request, or a fake consent context. The row stays `BLOCKED-DOMAIN`.

## Readiness table

| Class C row | Current implementation | Authoritative transition | Current caller | Readiness classification | Dependency | Can implement now? | Can staging-prove now? | Recommended slice membership | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DAU / MAU | Consented-subject counts and identity-lifecycle counts exist. Both documents say they are not account DAU or MAU. Session `last_seen_at` stores `user_id` | No privacy-safe account activity transition | Auth session validation updates `last_seen_at` inside the account store | BLOCKED-PRIVACY | A privacy-safe account activity digest, plus an activity and window definition. Sprint 43 only consumes DAU | No | No | no | Consented subjects cannot be relabeled. `user_id` is forbidden on product events. No trusted account-wide mapping exists |
| searches | No search event name and no search observer | No non-fixture search result transition. `GET /search` redirects | Production redirects home. Staging redirects to a fixture catalog. Sprint 4 mock connectors serve the three search APIs | BLOCKED-DOMAIN | A non-fixture search result transition with a production-capable caller | No | No | no | Instrumenting the redirect or the mock connectors would record fixture behavior as production truth |
| search success | No search-success event | Mock title matches return canned listings. That is not a production success transition | Same mock search APIs | BLOCKED-DOMAIN | The same missing search result transition | No | No | no | A canned match is not a shopper search success |
| search failure | No search-failure event | Mock connectors do not fail | Same mock search APIs | BLOCKED-DOMAIN | A real search failure distinct from an HTTP 400. Mock connectors do not fail | No | No | no | There is no failure outcome to observe |
| search zero | No zero-result search event | A mock title miss returns an empty tuple | Same mock search APIs | BLOCKED-DOMAIN | A production zero-result transition. A mock title miss is not a production zero-result transition | No | No | no | Empty mock output is fixture filtering |
| search partial | No search-partial event. `research_partial` is a different name and stays unemitted | No partial search transition. Every registered mock connector is always queried | Same mock search APIs | BLOCKED-DOMAIN | An authoritative partial search transition. No partial search transition exists | No | No | no | Partial research is not partial search |
| search started | No search-started event. The name is in the consent-aware list only | The mock call and the redirect have no separate started outcome | Same presentation route and mock APIs | BLOCKED-DOMAIN | A search-started transition that is not the fixture redirect. No search-started transition exists | No | No | no | Logging `consumer_search` is an application log |
| latency | `latency_band` is unused. Middleware stores `duration_ms` | No product latency population. Operational duration exists on every HTTP request | `RequestLoggingMiddleware`; Sprint 25 SLO text; Sprint 42 and Sprint 43 own operational use | BLOCKED-DEFINITION | A product latency population and event that is not the request log. No product latency population is defined | No | No | no | Copying middleware duration would duplicate Sprint 22 / 25 / 42 / 43 telemetry and would ignore consent |
| merchant coverage | Learning `coverage` counts consented subjects. Connector health is a separate document | No merchant-coverage formula. Provider status is Sprint 32 / 38 state | Disabled `ph-shopify-global-catalog`. Routing catalog empty | BLOCKED-DEFINITION | A merchant-coverage formula. No merchant-coverage formula is defined. DISABLED and routing 0 are not analytics events | No | No | no | Registry zeros are true and are not this metric |
| market coverage | `production_certified_shopping_markets()` is empty | No market-coverage formula. Sprint 37 market honesty is a different fact | Certified shopping markets stay 0 | BLOCKED-DEFINITION | A market-coverage formula. No market-coverage formula is defined. Certified-market 0 is not an analytics event | No | No | no | Publishing the empty catalog would not create a product-learning measurement |
| Recommendation views | No recommendation-view event. `results_viewed` is a different Class B row | Canonical Results `_hero_card` renders the Best Piq recommendation. Unavailable Results omits it | `GET /results/{decision_id}` redirects home in production. The canonical renderer exists. No production caller creates the initial snapshot | READY-B | A served canonical Results document. Staging proof waits on Sprint 29 / 31 / 38 | Yes | No | yes | The render is real and consent can gate a server observer. Fixture HTML must stay out. Public Results stays off |
| DealScore / PiqScore views | No score-view event. The Results hero gauge is labeled PiqScore | The same canonical `_hero_card` renders `piqscore_gauge` in `#piqscore` | Same Results route | READY-B | The same canonical Results serve | Yes | No | yes | One visible PiqScore gauge covers this combined row. A separate DealScore display is not on the page |
| funnel abandonment | No abandonment event and no dashboard formula | Completion rate and CTR are defined. Abandonment is not | None | BLOCKED-DEFINITION | An abandonment denominator, terminal state, window, and stage list. No abandonment denominator is defined | No | No | no | `canonical_persisted=False` writes nothing. It is not an abandonment metric |
| frontend errors | No frontend error event and no browser error listener | No frontend error transition | None in product JavaScript | BLOCKED-DOMAIN | A bounded frontend error transition that stores a code rather than raw exception text. No frontend error transition exists | No | No | no | A first-party listener is possible later. A generic error sink is not an existing transition. Sprint 42 operational tracking does not close this row |
| backend errors | No product backend-error event. Handlers and request logs exist | No sanitized backend-error transition | Per-route HTTP handlers and `RequestLoggingMiddleware` | BLOCKED-DOMAIN | A bounded backend error code on a product transition. No sanitized backend-error transition exists | No | No | no | Status codes in access logs are operational telemetry |
| merchant errors | No general merchant-error event. `research_failed` is the separate connector / research row | Connector health and research block reasons are other domains | Research observer after a started execution; Sprint 18 health | BLOCKED-DOMAIN | A shopper-facing merchant-error transition. `research_failed` is a different row | No | No | no | Health and research failure must stay on their own records |
| AI errors | No product AI-error event. Provider transports have operational codes | No product AI-error transition. Ask already records answered and insufficient evidence | AI transports; assistant `fallback_reason`; Sprint 42 owns provider monitoring | BLOCKED-DOMAIN | A consent-bearing product AI-error classification with a bounded code. No product AI-error transition exists | No | No | no | Provider codes and fallback strings are operational. They must not be copied into product analytics |
| slow pages | No slow-page event and no browser timing event | No page-latency population. Slow is undefined for pages | None | BLOCKED-DEFINITION | A page set and a slow threshold that is not a Sprint 25 SLO. Slow is undefined for pages | No | No | no | Client page timing would be new operational RUM unless a product definition exists first |
| slow endpoints | No slow-endpoint event. Middleware duration exists | No endpoint population. Slow is undefined for endpoints | `RequestLoggingMiddleware` | BLOCKED-DEFINITION | An endpoint set and a slow threshold held apart from Sprint 42 metrics. Slow is undefined for endpoints | No | No | no | Endpoint duration is already an operational measurement |
| support-contact analytics | `support_contact` is a server-owned name with no emitter. Mailto and the feedback form exist | No request-scoped support contact. Mailto does not prove delivery. The form emits other event names | Support page mailto. Feedback submit writes `product.feedback_reports` | BLOCKED-DOMAIN | A request-scoped action that proves a support contact. No request-scoped support contact exists | No | No | no | The source wording does not authorize a click, a feedback report, or an undelivered mailto as this event |
| conversation expiry | `cleanup_expired` deletes expired rows and returns a count. `get()` deletes and returns `None` | No consent-bearing expiry transition | Tests only. No scheduler and no application caller | BLOCKED-DOMAIN | An authoritative request-scoped expiry caller. `cleanup_expired` has no production caller | No | No | no | A scheduler or a synthetic request would invent the transition |

## Blocked rows by category

| Category | Rows |
| --- | --- |
| BLOCKED-PRIVACY | DAU / MAU |
| BLOCKED-DOMAIN | searches; search success; search failure; search zero; search partial; search started; frontend errors; backend errors; merchant errors; AI errors; support-contact analytics; conversation expiry |
| BLOCKED-DEFINITION | latency; merchant coverage; market coverage; funnel abandonment; slow pages; slow endpoints |
| BLOCKED-OPERATIONS | none. Sprint 42 and Sprint 43 own operational monitoring and capacity. That ownership does not delete the product rows above, and it does not make those rows implementable by wrapping logs |

## Status that stays put

Sprint 39 stays IN PROGRESS. It is not ENGINEERING COMPLETE, not COMPLETE / CLOSED, not PRODUCTION PROVEN, and not LAUNCH READY. Class C count remains 21.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, waiting on Sprint 41. Sprint 40 may still run in parallel and is not started by this audit. Sprint 41 stays UNSTARTED.
