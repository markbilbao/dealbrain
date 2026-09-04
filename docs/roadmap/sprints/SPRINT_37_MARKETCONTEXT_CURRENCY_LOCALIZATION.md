# Sprint 37 — MarketContext, Currency & Localization

**Status:** In progress — 37.1 merged; 37.2 shopping-market selection and coverage disclosure implemented. Sprint 37 is **not complete**. P1-1B is partially progressed and **not** fully closed. P1-2 is **not** fully closed.
**Primary owner / domain:** Product platform / marketplace
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-1B, P1-2; multinational honesty
**Architecture:** [`../../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../../architecture/ADR_SPRINT_37_MARKETCONTEXT.md)

## 37.1 record (owner slice; not a repository-defined sub-sprint before this work)

| Area | Status |
|------|--------|
| Composed `MarketContext` (TrustedMarketContext + DeliveryContext) | implemented |
| Intended PH / PHP / en-PH display defaults | implemented — **not** certified PH support |
| Production certified shopping-market catalog | empty (0 markets) |
| Destination known / skipped / absent; optional postal | implemented (reuses Sprint 29) |
| Unknown shipping/tax/import ≠ 0 / FREE | implemented + hardened |
| Destination-sensitive invalidation contract | implemented |
| `DESTINATION_REEVALUATION_IMPLEMENTED` | **False** (unchanged) |
| Live destination re-evaluation | not implemented |
| FX adapter / EXT-23 | not started |
| Five-market QA / FR-CA / US-SG-UK-CA selector | not started |
| P1-1B / P1-2 closure | **not closed** — foundation only |

37.1 is an owner-authorized first slice. It does not close Sprint 37.

## 37.2 record (owner slice)

| Area | Status |
|------|--------|
| Selected shopping-market contract (ISO, server-validated) | implemented |
| Guest cookie persistence (`piqsavi_shopping_market`) | implemented |
| Intended PH default when no selection exists | implemented — **not** certification |
| Product-facing selectable markets | PH only (no US/SG/UK/CA launch picker) |
| Coverage state (`certified` / `coverage_available` / reason) | implemented |
| Consumer disclosure on Results / Compare / Why | implemented |
| Unsupported-market research / connector gate | implemented (planning-only; no execution) |
| Production certified shopping markets | **0** |
| Five-market selector / FR-CA / FX | not started |
| P1-1B closure | **not closed** — selection + disclosure foundation only |

37.2 does not close Sprint 37. Default PH is not certified PH coverage.

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
- Country/market, currency, FX, locale, destination context, shipping-market honesty, unsupported-market behavior, cross-border cost semantics, delivery-location decision context
- **Destination re-evaluation (locked):** if changing destination could materially change shipping/effective buying cost, PiqSavi must perform server-side re-evaluation using supported evidence. Do not implement client-side fake repricing. Potential result may change shipping, effective cost, qualification, and Best Piq. Canonical PiqScore changes only through a legitimate new/re-evaluated decision, not presentation manipulation.

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
- Five-market EN QA checklist signed (for markets still named; omitted markets need not be QA’d as supported)
- Destination change that could materially change shipping/effective cost triggers server-side re-evaluation
- No client-side fake repricing
- Canonical PiqScore changes only through a new/re-evaluated decision

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
