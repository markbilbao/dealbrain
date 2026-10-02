# Sprint 39 staging analytics evidence

This file is a **partial** staging evidence record. It keeps both deploys:

- Deploy Staging #41: host evidence succeeded, then `ask_opened` validation failed
- Deploy Staging #42: the corrected application SHA, with a successful consent and feedback validation

Sprint 39 stays **IN PROGRESS**. This note does not close Sprint 39. It does not mark the core funnel populated. It does not claim production evidence. It does not deploy.

The Deploy Staging #41 failure stays in the evidence trail. Do not delete it because Deploy Staging #42 succeeded.

Sanitized data only. This file does not contain feedback message text, question text, answer text, analytics subject hashes, owner digests, or session ids.

## Current partial evidence — Deploy Staging #42

Deploy Staging #42 is the corrected staging validation. It follows the Sprint 39.3 serializer correction. It does not erase Deploy Staging #41.

| Field | Value |
| --- | --- |
| Application `main` | `374c9e2f45cb1810626c4138b3a145d3cff170a0` |
| Post-merge CI | CI #435 SUCCESS |
| Post-merge image build | Build Image #154 SUCCESS |
| Deployed SHA | `374c9e2f45cb1810626c4138b3a145d3cff170a0` |
| Staging deployment | Deploy Staging #42 |
| Staging deployment / run id | `36847902925` |
| Host evidence | `staging_ok` |
| Release | `rel-20261001T083510Z-374c9e2f45cb` |
| Environment | staging |
| Date (UTC) | 2026-10-01, from the release id `20261001T083510Z` |
| Operator | not named in the sanitized evidence package |
| Validation state | PARTIAL. Consent, `ask_opened`, and feedback on/off are recorded. Core funnel counts stay 0 |

### Initial baseline

| Step | Value |
| --- | --- |
| `product.analytics_events` row count | 0 |
| `product.feedback_reports` row count | 0 |
| Truncation | `analytics_truncated = false`, `feedback_truncated = false` |

### Explicit first-party opt-in

| Field | Value |
| --- | --- |
| choice | `analytics_allowed` |
| analytics_allowed | true |
| advertising_allowed | false |
| explicit | true |

### Corrected `ask_opened` request

`POST /api/v1/analytics/events`

```json
{
  "event_name": "ask_opened",
  "surface": "ask",
  "action_type": "open",
  "outcome": "opened"
}
```

Result: `recorded`

Event id: `1578ca76-d354-4c09-ab83-bf952364dcce`

### Incorrect-price feedback with analytics on

| Field | Value |
| --- | --- |
| report id | `0e16b66d-7487-43aa-99e4-4111db6c0622` |
| status | `received` |
| category | `incorrect_price` |
| analytics_status | `recorded` |
| message text | not recorded here |

Counts after the analytics-on flow:

| Store | Value |
| --- | --- |
| analytics_total_rows | 2 |
| feedback_total_rows | 1 |
| analytics_truncated | false |
| feedback_truncated | false |

The two analytics rows are the recorded `ask_opened` event and the sanitized analytics event from the incorrect-price report. This note does not add any other event.

### Explicit opt-out

| Field | Value |
| --- | --- |
| choice | `essential_only` |
| analytics_allowed | false |
| advertising_allowed | false |
| explicit | true |

### Outdated-offer feedback with analytics off

| Field | Value |
| --- | --- |
| report id | `b3f221f6-ac56-4544-a8d3-fea3cec86590` |
| status | `received` |
| category | `outdated_offer` |
| analytics_status | `suppressed_no_consent` |
| message text | not recorded here |

Final counts:

| Store | Value |
| --- | --- |
| analytics_total_rows | 2 |
| feedback_total_rows | 2 |
| analytics_truncated | false |
| feedback_truncated | false |

What this session shows:

- Feedback continues after analytics opt-out
- Non-essential analytics stops immediately
- The consent-off report does not add an analytics row
- The dashboard reads these real staging rows
- Truncation did not affect this evidence

### Controlled flow steps

| Step | Performed | Sanitized result |
| --- | --- | --- |
| Explicit analytics opt-in | yes | `analytics_allowed`, `explicit = true`, advertising false |
| `ask_opened` | yes | `recorded`. Event id `1578ca76-d354-4c09-ab83-bf952364dcce` |
| `ask_closed` | no | not submitted. Same corrected exact-field contract as `ask_opened`. Not invented |
| Incorrect-price report, analytics on | yes | `received` / `recorded`. Report id `0e16b66d-7487-43aa-99e4-4111db6c0622` |
| Explicit analytics opt-out | yes | `essential_only`, `explicit = true` |
| Outdated-offer report, analytics off | yes | `received` / `suppressed_no_consent`. Report id `b3f221f6-ac56-4544-a8d3-fea3cec86590` |
| Decision workflow | no | not available from the public staging flow. No `decision_started` or `decision_completed` row was created |
| Results viewed | no | count stays 0. Not invented |
| Compare opened | no | count stays 0. Not invented |
| Why opened | no | count stays 0. Not invented |
| Ask question submitted | no | count stays 0. Not invented |
| Evidence answer | no | count stays 0. Not invented |
| Insufficient evidence | no | count stays 0. Not invented |
| View Offer / outbound action | no | count stays 0. Not invented |
| Helpful or not helpful | no | not submitted |

The public staging root is still the Early Access landing experience. The public Results / Compare / Why shopper journey is not available from that flow. No production caller creates the initial canonical decision. This session does not fabricate that chain.

### Sanitized internal dashboard

`GET /api/v1/launch/product-learning`, environment `staging`, window `1d`. Counts only.

| Reading | Value |
| --- | --- |
| Recorded analytics events | 2 |
| Distinct consented analytics subjects | 1 |
| Analytics partial | false |
| decision_started | 0 |
| decision_completed | 0 |
| results_viewed | 0 |
| compare_opened | 0 |
| why_opened | 0 |
| outbound_merchant_click | 0 |
| decision_completion_rate | unavailable, denominator 0 |
| results_to_outbound_ctr | unavailable, denominator 0 |
| ask_question_submitted | 0 |
| ask_evidence_answered | 0 |
| insufficient_evidence | 0 |
| Research lifecycle counts | all real lifecycle counts 0 |
| research_partial | unavailable. No authoritative partial transition |
| live_research_operational | false |
| Feedback total | 2 |
| incorrect_price | 1 |
| outdated_offer | 1 |
| All other feedback categories | 0 |
| Analytics coverage total | 2 |
| Feedback coverage total | 2 |
| truncated | false |
| scan bound | 5000 |

Return-visit and repeat-decision figures were not part of this sanitized extract. This note does not invent them.

### Consent-off replay

| Check | Result |
| --- | --- |
| No new `product.analytics_events` rows | yes. Final analytics count stayed 2 |
| Feedback report still stored | yes. Final feedback count became 2 |
| Dashboard feedback aggregate includes that report | yes. Feedback total 2, including `outdated_offer` = 1 |
| Analytics funnel does not gain a subject from that session | yes. Distinct consented analytics subjects stayed 1. Analytics rows stayed 2 |

## Historical failure — Deploy Staging #41

Deploy Staging #41 succeeded as a host deploy. Controlled validation then stopped on the first browser `ask_opened` request. Root cause is request serialization in `ProductAnalyticsEventRequest.client_payload()`.

This section is historical. Sprint 39.3 corrected the serializer in application code. Deploy Staging #42, above, is the later staging proof of that correction. The failure itself remains.

| Field | Value |
| --- | --- |
| Deployed SHA | `287cdf11ff61bfdb09d412d1cb88927c86e3c799` |
| Staging deployment | Deploy Staging #41 |
| Staging deployment / run id | `36822959068` |
| Host evidence | `staging_ok` |
| Environment | staging |
| Validation state | PAUSED on this deploy. The pause was the state after #41 and before #42 |

### Consent and baseline row counts on #41

| Step | Value |
| --- | --- |
| First-party analytics opt-in performed explicitly | yes — choice `analytics_allowed`, `explicit = true` |
| `product.analytics_events` row count before the controlled flow | 0 |
| `product.feedback_reports` row count before the controlled flow | 0 |
| Truncation before the controlled flow | `analytics_truncated = false`, `feedback_truncated = false` |
| `product.analytics_events` row count after the controlled flow | not recorded — validation paused before a successful write |
| `product.feedback_reports` row count after the controlled flow | not recorded — validation paused before feedback steps |

### Failed ask_opened attempt

`POST /api/v1/analytics/events`

```json
{
  "event_name": "ask_opened",
  "surface": "ask",
  "action_type": "open",
  "outcome": "opened"
}
```

HTTP 400

```json
{
  "error": "validation_error",
  "message": "contradictory_event",
  "detail": "contradictory_event"
}
```

`ProductAnalyticsEventRequest.client_payload()` called `model_dump()`, so declared optional fields were present with `null` values. `ask_opened` and `ask_closed` permit only `event_name`, `event_id`, `decision_id`, `surface`, `action_type`, and `outcome`. The unrelated null fields were rejected as `contradictory_event`. At the time of Deploy Staging #41, that correction was not on staging. Sprint 39.3 corrected it in application code. Deploy Staging #42 recorded the successful request. This failed attempt stays.

## Boundaries

- Sanitized evidence only.
- No raw question, answer, or feedback message in the analytics proof.
- No production claim from this staging note.
- No affiliate conversion, commission, or revenue attribution.
- No third-party analytics call.
- EXT-15, EXT-22, and EXT-29 stay `not_started`. This file does not change those register statuses.
- `support@piqsavi.com` is the monitored mailto path (EXT-17). Structured reports in `product.feedback_reports` are not emailed by this slice.
- Core funnel zeros are the staging result. They are not a claim that those shopper events occurred.
