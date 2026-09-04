# ADR — Sprint 37.1 MarketContext composition

**Status:** Accepted for Sprint 37.1 only. Sprint 37 is **not complete**.
**Date:** 2026-09-03
**Baseline recorded:** `ba05aa7e205eab69a2f727e28b6b97d0d3b130ff`
**Related:** [`../roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](../roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md)

## Context

Sprint 29 already shipped session `DeliveryContext` and truthful price-state labels. Sprint 31 already shipped server-trusted `TrustedMarketContext` (country only) and blocked destination-sensitive planning with `DESTINATION_REEVALUATION_IMPLEMENTED = False`. Canonical snapshots already store `CanonicalDeliveryContext`.

Sprint 37 needs a coherent MarketContext without creating a second destination store and without claiming the Philippines is a certified shopping market.

## Decision

Add `app/market/` as a composition layer:

- `MarketContext` holds `TrustedMarketContext | None` plus the existing `DeliveryContext`.
- Country stays on the trusted-market object. `DeliveryContext` is not given a competing country field.
- Intended first-market defaults are PH / PHP / `en-PH` via an **explicit** constructor. Missing trusted market is **not** replaced with PH.
- Certified / supported shopping markets are a separate empty production catalog. Default PH context ≠ certified PH market.
- Destination-key changes produce `DestinationInvalidation` (stale shipping/tax/import, `reevaluation_required`). They do not rewrite canonical PiqScore, Recommendation, or snapshot economics, and they do not execute live merchant re-evaluation.
- `DESTINATION_REEVALUATION_IMPLEMENTED` remains `False`.

## Shipping / currency honesty in 37.1

- Unknown shipping/tax/import stay unknown. Verified `0` may be FREE; unknown or estimated `0` may not.
- Display formatting uses the offer’s source currency. No FX. Mixed currencies remain fail-closed.
- Mock DealScore enrichment `shipping_cost=0.0` values remain fixture-only and are not live PH evidence. Unknown mock SKUs no longer default shipping to `0.0`.

## Out of scope

FX adapter (EXT-23), live destination re-evaluation, five-market QA, FR-CA, Sprint 33–36, Sprint 38 live execution, naming PH as a supported shopping market.
