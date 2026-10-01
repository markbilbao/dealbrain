# Beta learning cadence

This is a review cadence for the internal product-learning dashboard. It is not a growth KPI promise and it does not set success targets.

The dashboard is `GET /api/v1/launch/product-learning`. Access reuses the existing Sprint 22 internal launch admin gate. That gate is demo/internal only. It is not production IAM.

Windows are UTC calendar days: `1d` is the current UTC day, `7d` is that day plus the previous six, and `30d` is that day plus the previous 29. See `docs/analytics/CORE_FUNNEL_EVENTS.md` for metric definitions.

## Daily during beta

Review the current UTC day:

- decision starts and decision completions
- Results views
- Results-to-outbound event CTR
- insufficient-evidence rate
- feedback problem reports
- bug reports

Decision start and completion stay at zero until a production path creates the initial canonical decision. Do not treat that zero as a failed shopping session.

Research counts may stay zero while live research is not operational.

## Weekly

Review `7d` and `30d`:

- active consented analytics subjects
- returning consented analytics subjects
- repeat-decision consented subjects
- helpful share of feedback ratings
- highest feedback categories
- funnel changes against the prior week

These subject counts are consented analytics subjects. They are not account DAU or MAU. Non-consenting shoppers are absent from the analytics series. Feedback totals can include those shoppers and are labeled separately.

## What this review does not decide

- Search Console indexing or ranking
- affiliate conversion or revenue
- Sprint 39 closure
- production deployment
