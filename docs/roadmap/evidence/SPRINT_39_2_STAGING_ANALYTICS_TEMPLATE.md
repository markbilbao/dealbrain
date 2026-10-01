# Sprint 39.2 staging analytics evidence template

This file is a template for a later owner/operator pass after a real staging deploy. It is empty on purpose. Do not fill it from unit tests, local fixtures, or invented counts.

Sprint 39 stays IN PROGRESS. This pull request does not deploy staging and does not claim production evidence.

## Deploy identity

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
