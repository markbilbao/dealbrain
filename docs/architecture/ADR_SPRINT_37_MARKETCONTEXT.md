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

## 37.2 addendum — selected market vs coverage

Selected shopping market is a separate guest-session contract (`SelectedShoppingMarket`, cookie `piqsavi_shopping_market`). It stores only a validated ISO country code.

- Missing selection uses the intended PH product default and must be labeled as a default, not as certified support.
- Delivery destination remains `DeliveryContext` / `piqsavi_delivery`. Changing one must not rewrite the other.
- Coverage is assessed only by `production_certified_shopping_markets()`. Account country, currency, locale, delivery, and affiliate availability cannot certify a market.
- Uncertified selected markets cannot become connector-eligible. Research planning may name the selected market; it must not execute connectors or treat fixtures as live coverage.
- Product-facing launch options remain PH-first. The typed contract accepts any valid ISO code so later markets do not require a second model.

## 37.3 addendum — currency authority vs conversion

Source offer currency is monetary truth. Preferred/display currency (PHP on PH MarketContext) is presentation context only. Selected market, locale, delivery destination, and account country are not FX rates.

- Same-currency presentation (PHP → PHP) needs no quote and must not invent an FX layer.
- Foreign source + preferred PHP with no trusted quote is an explicit `conversion_unavailable` state. No synthetic PHP amount, estimated rate, or rounded conversion may be shown.
- `conversion_available` requires an authoritative `FxQuote`. Production has zero quotes and `PRODUCTION_FX_CONVERSION_ENABLED = False`.
- Test-only quotes (`fx_quote_for_tests`) are deterministic, not live, and cannot enter the production provider catalog.
- Mixed-currency DealScore and Recommendation remain fail-closed. A test quote must not rewrite ranking.

## Out of scope

Live FX provider / EXT-23 credentials and production quotes, live destination re-evaluation, five-market QA, FR-CA, Sprint 33–36, Sprint 38 live execution, naming PH as a supported shopping market.
