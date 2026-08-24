# Sprint 47 — Offer Timing, Promotions & Buying Action Intelligence

**Status:** Planned — POST-BETA
**Primary owner / domain:** Product intelligence / marketplace evidence
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Gap ID:** P2-OT-01
**Beta blocker classification:** No — does **not** block Sprint 45

## Objective

Add an evidence-backed Buying Action layer and verified checkout/promotion economics **after** Controlled Global Public Beta launch.

This sprint does not replace canonical PiqScore or canonical Recommendation.

## Hard rules

- Sprint 47 is **not** a prerequisite for Sprint 45.
- Date pressure on September 30, 2026 must not pull this work into pre-launch scope.
- Buying Action does **not** replace canonical Recommendation.
- Do not reinterpret current canonical `Wait` as guaranteed future promotion timing.
- Campaign-aware Wait requires evidence.
- Affiliate economics remain Layer 5 / downstream.
- Conditional or unverified discounts must not raise PiqScore.
- Do not promise Watch monitoring before a certified worker exists.

## Architecture lock (layers)

| Layer | Authority | Rule |
|-------|-----------|------|
| 1 | Canonical PiqScore | Objective strength of the evaluated opportunity |
| 2 | Canonical Recommendation | Organic Buy / Wait / Consider / Avoid from current evaluated facts |
| 3 | Buying Action | Buy Now / Wait / Watch / Consider Alternative |
| 4 | Session refinement / personalization | May change session Best Piq / Buying Action; never rewrite Layer 1 |
| 5 | Affiliate economics | Downstream of all of the above |

## Included requirements

### 47.0 — Contracts + Architecture Lock addendum

- Additive contracts only
- No protected Sprint 5 / Sprint 6 formula rewrite in the first phase
- Architecture Lock addendum recording Layer 3 as new, not a silent Sprint 6 change

### 47.1 — Promotion and Voucher Evidence

- Marketplace-observed promotion/voucher evidence
- Fail-closed contractual rights (affiliate ≠ voucher eligibility ≠ catalog API)
- Calendar membership without offer participation is insufficient for Wait

### 47.2 — Effective Purchase Price

- Verified listing / seller discount / platform discount / voucher / shipping / other checkout / potential unverified savings
- Only verified components enter the scored price
- Potential/conditional amounts remain disclosed unknowns or ineligible savings

### 47.3 — Certified Historical Price Evidence

- History usable as Wait evidence only when source-certified and retention-authorized
- Mock or incomplete history cannot prove a future promotional price

### 47.4 — Buying Action Layer

Actions:

- Buy Now
- Wait
- Watch
- Consider Alternative

Personal urgency (`need it by`) is a Layer 3/4 input, not a PiqScore input.

### 47.5 — Watch Integration

- Watch means an explicit subscribe-to-monitoring action
- `promised_monitoring=false` until a certified worker exists
- Do not silently turn Save into Watch

## Explicit non-goals

- Blocking or delaying Sprint 45
- Reopening Sprints 29–46 as implementation owners for this item
- Scraping
- Inventing 8.8 / 9.9 / 11.11 discounts
- Guaranteed lowest price or “smartest deal” claims

## External dependencies

Later per-provider promotion/voucher/checkout/historical-retention rights and counsel review of Wait-as-advice. Do not invent those EXT rows as approved.

## Acceptance criteria

- Layer 3 exists without mutating Layer 1 or silently redefining Layer 2
- Conditional vouchers cannot enter PiqScore
- 9.9 approaching with no offer evidence produces Watch wording, never Wait
- Confirmed promotional price + permitted urgency may produce Wait or Buy Now without changing canonical PiqScore/Recommendation digests
- Affiliate commission cannot create Buy Now, Wait preference, or Watch priority
- Watch CTA cannot promise monitoring until certified
- Fixture / imported / simulated-live cannot appear as live promotional prices

## Predecessor sprints

45 (approved launch) and 46 (stabilization). Supporting contracts from 5/6/7/10/18/19/31/37/38 may be reused; they do not own this sprint.

## Parallelizable work

None with Sprint 45.

## Go / no-go gate

Post-beta only. Cannot be used to satisfy EC-01…EC-30.

## Rollback or contingency

Keep current canonical Recommendation and honest unknowns. Do not ship campaign-aware Wait.

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
- New pre-launch sprints may not be inserted to absorb this work without explicit owner approval.
