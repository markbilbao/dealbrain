# Sprint 37 — MarketContext, Currency & Localization

**Status:** Planned
**Primary owner / domain:** Product platform / marketplace
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-1B, P1-2; multinational honesty

## Objective

Ship a coherent MarketContext with honest currency, localization, unsupported-market behavior, and shipping-cost honesty for PH/US/SG/UK/CA.

## Included requirements

### P1-1B — Unsupported-market product behavior

- Supported-market decision and configuration
- Unsupported-market state
- Market selector behavior (integrates Sprint 29 UI shell)
- Coverage disclosure
- No unsupported connector invocation
- Market-selection persistence

### P1-2 — Shipping-cost and unknown-shipping honesty

- Unknown shipping cannot silently become free shipping
- Shipping-known / shipping-unknown state is modeled
- Comparison behavior is documented and tested
- UI discloses exclusions and uncertainty
- Final claims review (Sprint 44) verifies — does **not** implement — this behavior

### MarketContext / FX / localization

- MarketContext fields: account country, detected country, selected shopping market, delivery destination, display currency, original merchant currency, locale, language, timezone, tax context, shipping destination
- Selector + persistence + safe defaults
- Formatting: currency/number/date-time; original currency preservation
- FX provider; source timestamp; staleness threshold; missing-rate fail-closed; rounding; comparison-currency policy
- Taxes/duties/delivery cost/shipping availability disclosures; landed-cost limitations
- Regional variant disclosures (model, voltage/plug, warranty-region, seller-region)
- Localization QA for five markets; English baseline
- French-Canadian scope decision + disclosure

## Explicit non-goals

- Full multilingual product
- Guaranteed landed-cost calculator
- Canonical registry/router ownership (P1-1A → 31)
- Live merchant certification (32–36)

## External dependencies

- EXT-23

## Implementation deliverables

- MarketContext service
- FX adapter
- Shipping-known/unknown model + comparison rules
- API + UI wiring to Sprint 29 shells

## Documentation deliverables

- MarketContext ADR
- FX policy
- Shipping honesty policy
- FR-CA decision record

## Required tests

- Fail-closed mixed currency
- Stale FX rejected
- Unsupported market UX; no unsupported connector invoke
- Unknown shipping never presented as free
- Market-selection persistence

## Required staging evidence

- Selector + FX + unsupported-market paths proven
- Shipping honesty cases demonstrated
- QA checklist for 5 markets

## Required production evidence

- FX credentials in secrets

## Acceptance criteria

- P1-1B closed: unsupported markets disclosed; no unsupported connector invocation; selection persists
- P1-2 closed: shipping-known/unknown modeled; unknown ≠ free; UI discloses uncertainty
- Unsafe FX comparisons fail closed
- Unsupported markets never show fixture-as-live
- FR-CA decision published
- Five-market EN QA checklist signed

## Predecessor sprints

31, 29 (UI shell)

## Parallelizable work

Late 35–36

## Go / no-go gate

Go if fail-closed FX + unsupported-market + shipping honesty pass

## Rollback or contingency

Disable cross-currency compare; PH-default disclosure; hide uncertain shipping rather than invent free shipping

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
