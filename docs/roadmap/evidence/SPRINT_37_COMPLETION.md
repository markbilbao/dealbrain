# SPRINT 37 COMPLETE / CLOSED

**Label:** SPRINT 37 COMPLETE / CLOSED
**Authority:** Authoritative Sprint 37 final completion record for the current PH-only public beta scope.
**Close date:** 2026-09-26
**Starting `main`:** `58a6d81a5447ced30fce6294f852e43ecdb46ef9`
**Sprint definition:** [`../sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](../sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md)
**Architecture:** [`../../architecture/ADR_SPRINT_37_MARKETCONTEXT.md`](../../architecture/ADR_SPRINT_37_MARKETCONTEXT.md)

**2026-09-26 close verdict:**

**SPRINT 37 COMPLETE / CLOSED**

PH-ONLY PUBLIC BETA SCOPE

NOT LIVE DESTINATION RE-EVALUATION

NOT PRODUCTION FX

NOT PUBLIC PH SHOPPING COVERAGE

This closure does not start Sprint 38 or Sprint 41. It does not reopen Sprint 32. It does not enable a certified shopping market. It does not invent an FX rate. It does not treat unknown shipping as zero or free.

---

## Scope

September supported-market target remains Philippines-first. US, SG, UK, and CA stay omitted (`n_a_beta`). PH remains the intended default display context. PH is not a public certified shopping market. `production_certified_shopping_markets` stays empty.

---

## Ownership reconciliation

| Item | Class | Disposition |
|------|-------|-------------|
| MarketContext composition (trusted market + delivery) | A. Already satisfied | PASS |
| Intended PH / PHP / en-PH defaults, labeled as defaults | A | PASS. Not certified PH support |
| Selected shopping-market persistence and PH-only product picker | A | PASS |
| Unsupported-market disclosure and no connector invocation (P1-1B) | A | PASS |
| Unknown shipping / tax / import never become zero or free (P1-2) | A | PASS |
| Source currency retained; same-currency PHP needs no quote | A | PASS |
| Mixed currency and missing FX fail closed | A | PASS |
| Destination-change contract; prior decision stays immutable | A | PASS |
| No client-side repricing | A | PASS |
| Empty production certified shopping-market catalog | A | PASS. Must stay empty |
| FR-CA decision for this beta | E. Not applicable | NOT APPLICABLE TO PH-ONLY BETA. Canada is omitted. No FR-CA localization is implemented |
| US / SG / UK / CA selector and five-market supported QA | E | NOT APPLICABLE TO PH-ONLY BETA. Omitted markets are not QA'd as supported |
| Shopify SHIPPING / TAXES_IMPORT certification | E | NOT APPLICABLE. Sprint 32 left those capabilities uncertified. Sprint 37 keeps unknown costs unknown |
| Live evidence-backed destination re-evaluation | C. Sprint 38 | DEFERRED TO SPRINT 38. `DESTINATION_REEVALUATION_IMPLEMENTED` stays False |
| Production FX provider, live quotes, and EXT-23 provisioning | D. Later / optional | DEFERRED. EXT-23 stays `not_started`. Selected behavior is the register fallback: no cross-currency compare; disclose conversion unavailable |
| FX credentials in production secrets | D | DEFERRED TO SPRINT 41. Not required while production conversion stays disabled |
| Final public claims review of shipping wording | D | DEFERRED TO SPRINT 44 |
| Frozen supported-market list at launch | D | DEFERRED TO SPRINT 44 / 45 |

No Sprint 37-owned item remains open.

---

## FX and EXT-23

`PRODUCTION_FX_CONVERSION_ENABLED` is False. Production FX quotes = 0. A preferred currency that differs from the source currency is `conversion_unavailable`. No synthetic rate is shown. Test-only quotes stay out of the production catalog.

EXT-23 remains `not_started`. It is an optional dependency. The September fallback in the external register is the selected path. Multi-currency compare is not a PH-only beta claim.

---

## Destination re-evaluation

A shopper destination change that can affect shipping or effective cost is assessed on the server. The result is `required_unavailable` while no live evidence path exists. The prior canonical decision, PiqScore, and Recommendation stay unchanged. Disclosure says updated pricing is not available yet. Previous destination shipping is not reused as the new destination's cost.

`DESTINATION_REEVALUATION_IMPLEMENTED` remains False. Live merchant re-evaluation is Sprint 38 live execution. This closure does not add an executor.

---

## Shipping honesty

Unknown shipping, tax, and import stay unknown. Unknown or estimated zero is not FREE. Verified zero may be FREE. Shopify's uncertified shipping, tax, and promotion capabilities are not treated as known costs.

---

## Supported markets

Product-facing selectable market remains PH only. The certified shopping-market catalog remains empty. Public PH copy remains: “PiqSavi is preparing shopping-source coverage for the Philippines.” Account country, locale, currency, and affiliate state cannot certify PH.

---

## Acceptance matrix

| Criterion | Result | Evidence |
|-----------|--------|----------|
| P1-1B unsupported markets disclosed; no unsupported connector invocation; selection persists | PASS | 37.2 selection, coverage gate, empty certified catalog |
| P1-2 shipping known/unknown modeled; unknown is not free; UI discloses uncertainty | PASS | 37.1 shipping display tests; destination disclosures |
| Unsafe FX comparisons fail closed | PASS | 37.3 currency authority; production quotes empty |
| Unsupported markets never show fixture-as-live | PASS | Coverage fail-closed; fixtures are not certified markets |
| FR-CA decision published | NOT APPLICABLE TO PH-ONLY BETA | Canada omitted. No FR-CA product surface |
| Five-market EN QA for markets still named | NOT APPLICABLE TO PH-ONLY BETA | US/SG/UK/CA omitted. PH is not publicly named as certified coverage |
| Server-side destination-change contract without client repricing | PASS | 37.4 `required_unavailable`; canonical decision immutable |
| Live evidence-backed destination re-evaluation | DEFERRED TO SPRINT 38 | Flag remains False. No executor added |
| Production FX provider and EXT-23 live quotes | DEFERRED | EXT-23 `not_started`; fail-closed fallback selected |
| FX credentials in production secrets | DEFERRED TO SPRINT 41 | Conversion disabled |
| Shipping wording final claims review | DEFERRED TO SPRINT 44 | Sprint 37 implements the behavior; Sprint 44 verifies claims |
| Public PH shopping coverage enabled | NOT APPLICABLE TO THIS CLOSE | Catalog stays empty |

---

## Explicit non-claims

- Closing Sprint 37 does not make PH a certified shopping market.
- Closing Sprint 37 does not enable live destination re-evaluation.
- Closing Sprint 37 does not enable production FX.
- Closing Sprint 37 does not start Sprint 38.
- Closing Sprint 37 does not start Sprint 41.
- Closing Sprint 37 does not certify shipping, tax, or import on the Shopify path.
- Closing Sprint 37 does not add US, SG, UK, or CA support.
