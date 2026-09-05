# Sprint 29 vs Sprint 37 — Market Selection Ownership

**Sprint 29 owns:** the accessible market-selection UI shell on Results / Compare / Why.

**Sprint 37 owns:** MarketContext domain rules, certified-market data, persistence semantics beyond the existing cookie, currency/FX policy, unsupported-market connector policy, and destination re-evaluation.

## What the Sprint 29 shell does

- Renders the current selected/default market and coverage disclosure.
- Offers a Philippines `<select>` and posts `country_code` to `/consumer/shopping-market`.
- Persists the existing `piqsavi_shopping_market` cookie.
- States that selection does not certify live shopping coverage.

## What it does not do

- Add US / SG / UK / CA as launch-ready choices
- Invoke connectors
- Reprice offers client-side
- Claim certified PH coverage
- Implement FX conversion

Default PH remains an intended product default, not a certified shopping market.
