# Sprint 37 — MarketContext, Currency & Localization

**Status:** COMPLETE / CLOSED (2026-09-26) for the PH-only public beta scope. Live destination re-evaluation remains unavailable and is Sprint 38. Production FX remains unavailable. Public PH shopping coverage is not enabled.
**Primary owner / domain:** Product platform / marketplace
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-1B, P1-2; multinational honesty
**Architecture:** [`../../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../../architecture/ADR_SPRINT_37_MARKETCONTEXT.md)
**Close record:** [`../evidence/SPRINT_37_COMPLETION.md`](../evidence/SPRINT_37_COMPLETION.md)

## Current closure (2026-09-26)

Sprint 37 is COMPLETE / CLOSED for the PH-only public beta. Historical slices below recorded that they did not close the sprint. Those sentences stay as history.

P1-1B and P1-2 are closed for this scope: unsupported markets stay disclosed and connector-ineligible, and unknown shipping is not free. US, SG, UK, and CA stay omitted. FR-CA is not applicable because Canada is omitted. EXT-23 stays `not_started`; the selected FX behavior is fail-closed conversion-unavailable. `DESTINATION_REEVALUATION_IMPLEMENTED` stays False. Live evidence-backed re-evaluation is Sprint 38. Production FX secrets, if a provider is later chosen, stay Sprint 41. Claims review stays Sprint 44. The certified shopping-market catalog stays empty.

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
| FX adapter / EXT-23 | domain + fail-closed conversion state in 37.3; live provider **not started** |
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

## 37.3 record (owner slice)

| Area | Status |
|------|--------|
| Source offer currency retained (PHP stays PHP; USD stays USD) | implemented |
| Preferred/display currency distinguished from source currency | implemented |
| Same-currency PHP → PHP (no FX quote) | implemented |
| Conversion-unavailable when preferred ≠ source and no trusted quote | implemented |
| Production FX provider / live quotes | **none** (count = 0) |
| Test-only FX fixture | implemented — not live, not production-eligible |
| Mixed-currency compare / DealScore / Recommendation | remain fail-closed without trusted FX |
| Results / Compare / Why source-currency presentation + disclosure | implemented (no redesign) |
| EXT-23 live FX provider, credentials, production quotes | **OPEN** (`not_started`) |
| Five-market selector / FR-CA / live destination re-evaluation | not started |
| P1-1B / P1-2 closure | **not closed** |

37.3 satisfies domain currency authority, conversion-unavailable presentation, and fail-closed comparison. It does **not** complete EXT-23. Production currency conversion remains unavailable.

## 37.4 record (owner slice)

| Area | Status |
|------|--------|
| Destination comparison / invalidation (normalized key + declared transitions) | implemented |
| Server-authoritative re-evaluation-required state | implemented |
| Fail-closed unavailable re-evaluation (`required_unavailable`) | implemented |
| Canonical decision immutability | enforced / tested |
| Shipping / effective-cost truthfulness | hardened |
| Destination-insensitive economics remain usable when proven `not_applicable` | implemented |
| Live merchant-backed destination re-evaluation | **not implemented** |
| `DESTINATION_REEVALUATION_IMPLEMENTED` | **False** (unchanged — live evidence path) |
| Sprint 38 live execution / fake live executor | **not started** |
| Production certified shopping markets | **0** |
| Production FX provider / live quotes | **none** (count = 0) |
| P1-1B / P1-2 closure | **not closed** |

37.4 implements destination-change fail-closed / re-evaluation readiness. Live evidence-backed re-evaluation remains unavailable. It does **not** close Sprint 37. It does **not** start Sprint 38.

## Objective

Current closure scope (2026-09-26): ship a coherent MarketContext for the PH-only public beta, with honest currency behavior, unsupported-market fail-closed behavior, and shipping-cost honesty.

Historical / future scope: the original objective also named PH/US/SG/UK/CA. US, SG, UK, and CA are omitted from this beta. They are not part of this closure and were not QA'd as supported markets.

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
- FX for this closure: a production FX provider is optional and deferred. EXT-23 remains `not_started`. Current behavior is fail-closed `conversion_unavailable` when the preferred currency differs from the source currency and no trusted quote exists. Same-currency PHP presentation does not invent a rate. Source timestamp, staleness, rounding, and a comparison-currency policy apply only if production conversion is later enabled.
- Taxes/duties/delivery cost/shipping availability disclosures; landed-cost limitations. Unknown shipping, tax, and import stay unknown.
- Regional variant disclosures (model, voltage/plug, warranty-region, seller-region) remain future scope where a market is later named. They are not a PH-only closure claim.
- Historical / future scope, not this closure: localization QA for five markets. US, SG, UK, and CA are omitted from this PH-only beta and were not QA'd as supported.
- French-Canadian scope is not applicable because Canada is omitted. No FR-CA localization is implemented.
- Country/market, currency, locale, destination context, shipping-market honesty, and unsupported-market behavior for the PH-only beta.
- **Destination re-evaluation (current contract):** a destination change that could materially change shipping or effective cost triggers the server-authoritative re-evaluation requirement. While no live evidence-backed executor exists, the state is `required_unavailable`. The prior canonical decision, PiqScore, and Recommendation remain unchanged. Do not implement client-side fake repricing. Live evidence-backed re-evaluation is Sprint 38. `DESTINATION_REEVALUATION_IMPLEMENTED` remains False.

### 2026-09-06 owner lock — shipping and effective-cost honesty

Historical lock. On that date it did not close Sprint 37. Current closure scope is the 2026-09-26 PH-only record above. The lock still strengthens P1-2. It does not start a second price model or pull Sprint 47 into pre-launch.

- Unknown shipping must never become ₱0, FREE, included, or assumed negligible unless evidence supports that state.
- If destination-specific shipping is known, it participates in Sprint 29 canonical effective purchase cost.
- If shipping materially depends on shopper destination and the shopper supplies or changes destination, use this sprint's server-side re-evaluation contract. No client-side fake repricing.
- Ranking/comparison must not give an incomplete offer an artificial advantage by treating unknown shipping or other unknown costs as zero.
- September beta uses currently verified purchase-cost information from canonical offer economics. Historical campaign prediction, promotion timing, Buy Now / Wait / Watch, and price-drop monitoring remain Sprint 47 / post-beta.

## Explicit non-goals

- Full multilingual product
- Guaranteed landed-cost calculator
- Canonical registry/router ownership (P1-1A → 31)
- Live merchant certification (32–36)

## External dependencies

- EXT-23 remains `not_started`. It is optional. Under the selected PH-only fail-closed fallback it is not a Sprint 37 closure requirement. Production secret attachment, if production FX conversion is later enabled, belongs to Sprint 41.

## Implementation deliverables

- MarketContext service
- FX adapter
- Shipping-known/unknown model + comparison rules
- API + UI wiring to Sprint 29 shells

## Documentation deliverables

- MarketContext ADR
- FX policy
- Shipping honesty policy
- FR-CA decision for this closure: not applicable, because Canada is omitted. Recorded in [`../evidence/SPRINT_37_COMPLETION.md`](../evidence/SPRINT_37_COMPLETION.md). No FR-CA localization is implemented.

## Required tests

- Fail-closed mixed currency
- Stale FX rejected
- Unsupported market UX; no unsupported connector invoke
- Unknown shipping never presented as free
- Market-selection persistence

## Required staging evidence

Current PH-only closure evidence:

- PH selector and PH default behavior
- Unsupported-market fail-closed behavior
- FX-unavailable / fail-closed behavior, with no live FX provider
- Shipping honesty

Do not read this list as proof of a live FX provider. Omitted markets were not QA'd as supported.

## Required production evidence

FX credentials in production secrets are required only if production FX conversion is later enabled. They are not a Sprint 37 closure requirement under the selected PH-only fail-closed fallback. Production secret attachment, if later needed, belongs to Sprint 41. EXT-23 remains `not_started`. Production FX conversion remains disabled.

## Acceptance criteria

- P1-1B closed for this scope: unsupported markets disclosed; no unsupported connector invocation; selection persists
- P1-2 closed for this scope: shipping-known/unknown modeled; unknown ≠ free; UI discloses uncertainty
- Unsafe FX comparisons fail closed. Production FX remains disabled. EXT-23 remains `not_started`.
- Unsupported markets never show fixture-as-live
- FR-CA is not applicable because Canada is omitted. No FR-CA localization is implemented.
- Five-market supported QA is not applicable. US, SG, UK, and CA are omitted and were not QA'd as supported.
- A destination change that could materially change shipping or effective cost triggers the server-authoritative re-evaluation requirement. While no live evidence-backed executor exists, the state is `required_unavailable`. The prior canonical decision, PiqScore, and Recommendation remain unchanged. Live evidence-backed re-evaluation is Sprint 38. `DESTINATION_REEVALUATION_IMPLEMENTED` remains False.
- No client-side fake repricing
- Canonical PiqScore changes only through a new or re-evaluated decision, which this closure does not execute

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
