# Core funnel event definitions

Sprint 39.2. These definitions are the analytics contract. They are not a claim that every named event already has a production caller.

## decision_started

Emit only from `record_decision_started` after a shopper decision request has passed validation and the server has begun canonical decision generation.

The caller must already hold the server-owned decision hash on `AnalyticsServerContext`, including `context_version`. The function does not allocate a decision id.

Do not emit from a page load, `GET /shopping-assistant/demo`, a client event, or a request that fails validation.

Current production has no such caller. `ShoppingAssistantService.query` does not persist a `CanonicalDecisionSnapshot`. `GET /search` redirects to a fixture catalog or `/results/unavailable`.

## decision_completed

Emit only from `record_decision_completed` after the canonical snapshot required for Results has been persisted and owner binding for that snapshot has succeeded.

Pass `canonical_persisted=False` when the attempt fails, is abandoned, or never creates that snapshot. Those calls write nothing.

`CanonicalResearchResultsService` writes `context_version + 1` onto a snapshot that already exists. That transition is research completion, not `decision_completed`.

## Decision completion rate

The beta-learning read model uses distinct authorized decision hashes:

`decision_completion_rate = distinct decision_started hashes that also have decision_completed / distinct decision_started hashes`

in the same UTC window. It is not a unique-user funnel and not a raw event ratio. Completed hashes with no start are counted separately as `decision_completed_without_start` and do not increase the rate above 1. If there are no started hashes, the rate is unavailable (`null`), not 0%.

## results_to_outbound_ctr

`outbound_merchant_click` event count / `results_viewed` event count in the same window.

This is an event ratio. It is not affiliate conversion, purchase conversion, or unique-shopper conversion. If Results views are 0, the rate is unavailable. Values above 1.0 are returned with the raw numerator and denominator.

## Ask

`ask_question_submitted` and `insufficient_evidence` stay server-owned and still carry no question text.

`ask_evidence_answered` is emitted only when the evidence answer status is `answered`. It carries no answer text. `evidence_count` may be included. `partially_answered` does not emit this event.

Ask submission does not have a stable non-PII idempotency key, because the question text must not be hashed into the event id. A retried Ask request can therefore create another row. That limitation is intentional.

`ask_opened` and `ask_closed` are browser panel transitions:

- `ask_opened`: surface `ask`, action `open`, outcome `opened`
- `ask_closed`: surface `ask`, action `close`, outcome `closed`

Any other property on those two client events is rejected.

## Research

Events are recorded only after `ProposeResearchService` or `ConfirmedResearchExecutionService` has already finished the transition. Telemetry does not change research state, consume authorization, open routing, or call Shopify.

| Event | Transition |
| --- | --- |
| `research_proposed` | lifecycle `propose` or `replace`, status `pending_confirmation` |
| `research_confirmed` | lifecycle `confirm` or `reconfirm` and `authorization_created` |
| `research_declined` | lifecycle `cancel`, status `cancelled` |
| `research_started` | execution `attempted` or `research_executed`, with an execution id |
| `research_completed` | `live_research_completed` |
| `research_failed` | execution started and live research did not complete |

A closed production gate returns before a claim. That stop is not `research_started` and not `research_failed`. Live research is not operational, so these counts may stay zero.

`research_partial` is not emitted. No authoritative partial-completion transition exists. The dashboard reports that metric as unavailable.

Stable ids use the server proposal id, authorization id, or execution id. Those raw ids are not stored as event properties.

## Recommendation refinement

`recommendation_refinement_attempted` is recorded when the refinement service returns after validation.

`recommendation_refinement_applied` is recorded only when that service sets `recommendation_applied`. A shopper click is not treated as applied.

## updated_results_viewed

The Results route emits this only after `resolve_canonical_snapshot` returns an owner-authorized snapshot with `context_version > 1`. The browser `data-context-version` attribute is not an authority. Each serve is a view; a repeated GET can add another row.

## recommendation_viewed and piqscore_viewed

Sprint 39.5. These names are server-owned. They are not aliases of `results_viewed` or `updated_results_viewed`.

| Event | Meaning |
| --- | --- |
| `results_viewed` | Browser Results document view, including unavailable Results |
| `updated_results_viewed` | Authorized canonical snapshot with `context_version > 1` was served |
| `recommendation_viewed` | Canonical Results response contained the Best Piq recommendation hero |
| `piqscore_viewed` | Canonical Results response contained the hero PiqScore control |

The visible score control is the PiqScore gauge. Results does not render a second DealScore control. `piqscore_viewed` is the observation for the DealScore / PiqScore row. `dealscore_viewed` is not an event.

The Results route emits these only for `presentation_mode = canonical` and `data_unavailable = false`, and only after an authorized snapshot resolves. `context_version` 1 is allowed. The completed HTML is checked independently:

- Best Piq hero: `data-product-analytics-recommendation-view="true"`
- Hero PiqScore control: `data-product-analytics-piqscore-view="true"`

A response can contain one marker without the other. The missing element is not recorded. `presentation_mode = canonical` alone does not record either event.

A successful server serve is a view. This does not claim viewport visibility, scroll depth, eye tracking, or time on screen. A repeated GET can add another row. Event ids are random. They are not derived from the decision id, product id, score, query, account id, or subject cookie.

Stored properties are the existing decision hash and context version, plus surface `results`, action `view`, and outcome `viewed`. The numeric PiqScore, DealScore, product name, product id, recommendation text, query, price, merchant, raw decision id, and HTML are not stored.

Analytics off writes zero rows. Serving Results does not mint an analytics subject. Consent without an existing opaque subject writes zero rows. Fixture catalogs, `/results/unavailable`, unavailable Results, the production Early Access redirect, Compare, and Why write zero rows even when they contain similar PiqScore markup.

Analytics failure does not change the Results response.

`ProductLearningDashboardService` exposes `metrics.recommendation_visibility` with `recommendation_viewed`, `piqscore_viewed`, and `partial`. Those are event counts, not unique shoppers and not scores. A truncated newest-row scan sets `partial` true.

No non-zero staging count is claimed. Public canonical Results is not enabled. Unit tests that build canonical snapshots are engineering verification, not staging evidence.

## return_visit and repeat_decision

These names stay in the vocabulary. The dashboard derives them and does not require stored copies.

- Returning consented analytics subject: at least two distinct UTC dates in the selected window.
- Repeat-decision consented subject: at least two distinct `decision_completed` decision hashes in the selected window.

If the scan is truncated, both figures are unavailable. The bounded scan reads the newest inserted rows, then keeps events whose `occurred_at` falls in the window. Database row time is not the window clock.

## Analytics failure

Persistence errors are swallowed. Decision generation, Ask answers, research state, and View Offer navigation do not roll back because analytics failed.

Feedback submission is different. If feedback persistence fails, the report response may say the report is unavailable.
