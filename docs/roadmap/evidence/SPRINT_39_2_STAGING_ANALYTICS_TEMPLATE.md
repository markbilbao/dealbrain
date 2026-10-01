# Sprint 39.2 staging analytics evidence template

This file records the partial staging session from Deploy Staging #41 and keeps the checklist for the rest of the controlled flow. Do not fill the remaining checklist from unit tests, local fixtures, or invented counts.

Sprint 39 stays IN PROGRESS. Staging validation is **PAUSED**. This note does not mark Sprint 39 staging validation complete, does not deploy, and does not claim production evidence.

The failed `ask_opened` attempt below stays in the evidence trail after the serializer correction. Do not delete it when a later deploy succeeds.

## Current partial evidence — Deploy Staging #41

Deploy Staging #41 succeeded. Controlled validation then stopped on the first browser `ask_opened` request. Root cause is request serialization in `ProductAnalyticsEventRequest.client_payload()`.

| Field | Value |
| --- | --- |
| Deployed SHA | `287cdf11ff61bfdb09d412d1cb88927c86e3c799` |
| Staging deployment | Deploy Staging #41 |
| Staging deployment / run id | `36822959068` |
| Host evidence | `staging_ok` |
| Environment | staging |
| Validation state | PAUSED pending the ask analytics payload correction and a later redeploy |

### Consent and baseline row counts

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

`ProductAnalyticsEventRequest.client_payload()` called `model_dump()`, so declared optional fields were present with `null` values. `ask_opened` and `ask_closed` permit only `event_name`, `event_id`, `decision_id`, `surface`, `action_type`, and `outcome`. The unrelated null fields were rejected as `contradictory_event`. Sprint 39.3 corrects that serialization in application code. This note does not claim that correction has been redeployed.

## Deploy identity

Leave this table for the next staging pass after the correction is deployed. Do not copy the paused Deploy Staging #41 row into it as a completed validation.

| Field | Value |
| --- | --- |
| Deployed SHA | |
| Staging deployment / run id | |
| Environment | staging |
| Date (UTC) | |
| Operator | |

## Consent and row counts

| Step | Value |
| --- | --- |
| First-party analytics opt-in performed explicitly | |
| `product.analytics_events` row count before the controlled flow | |
| `product.feedback_reports` row count before the controlled flow | |
| `product.analytics_events` row count after the controlled flow | |
| `product.feedback_reports` row count after the controlled flow | |

## Controlled staging flow

Record only that each step was performed, plus the sanitized event names that appeared. Do not paste question text, answer text, feedback message text, subject hashes, owner digests, decision ids, or session ids into this file.

| Step | Performed | Sanitized result |
| --- | --- | --- |
| Decision workflow | | |
| Results viewed | | |
| Compare opened | | |
| Why opened | | |
| Ask submission | | |
| Insufficient-evidence case, if safely reproducible | | |
| View Offer / outbound action | | |
| Helpful or not helpful | | |
| Incorrect-information report | | |

If the decision workflow cannot create a canonical decision on staging, write that limitation here. Do not invent `decision_started` or `decision_completed` rows.

## Internal dashboard

Paste the aggregate `GET /api/v1/launch/product-learning` body after removing any accidental identifiers. Counts and rates only.

```
```

## Consent-off replay

| Check | Result |
| --- | --- |
| No new `product.analytics_events` rows | |
| Feedback report still stored | |
| Dashboard feedback aggregate includes that report | |
| Analytics funnel does not gain a subject from that session | |

## Boundaries

- Sanitized evidence only.
- No raw question, answer, or feedback message in the analytics proof.
- No production claim from this staging note.
- No affiliate conversion, commission, or revenue attribution.
- No third-party analytics call.
- EXT-15, EXT-22, and EXT-29 stay unchanged by this template.
- `support@piqsavi.com` is the monitored mailto path (EXT-17). Structured reports in `product.feedback_reports` are not emailed by this slice.
