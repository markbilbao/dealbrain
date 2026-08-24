# Canonical decision presentation contract

**Status:** Schema 1.2 capture + read-only consumer/Ask adapter

A PiqSavi decision snapshot may now remember the decision-time facts needed to
explain the same Recommendation across Results, Compare, Why, and Ask PiqSavi.

This is not Phase 29.4B or 29.4C. Ask remains read-only. The original snapshot
is immutable. Later conversational preference changes must not rewrite it.

## Schema versions

| Version | When |
|---|---|
| **1.0** | No economics and no presentation contract |
| **1.1** | Economics present, presentation contract absent |
| **1.2** | Any presentation-contract field is present |

1.0 and 1.1 `to_dict()` payloads and `content_sha256` values stay byte-identical
when the new fields are absent. Missing 1.2 keys are not backfilled.

PiqScore descriptor labels such as **Excellent** remain presentation formatting
of the captured score. They are not canonical ranking evidence. Percentile
claims such as Top 5% are not invented.

## Qualification

`qualification.state` is `unqualified` or `qualified` when captured.

`qualification=None` means qualification was not captured. It is not an
explicit unqualified Recommendation. Ask returns insufficient evidence for
legacy snapshots instead of claiming they were evaluated as unqualified.

A qualified Recommendation stores:

- reason(s)
- material unknown(s)
- whether those unknowns could change the Recommendation

The adapter does not infer qualification. PiqScore is not rewritten.

## Shopper decision context

Captured only when used at decision time:

- budget label
- top priority / priorities
- use case
- urgency
- required features
- preferences
- constraints

This is historical decision context, not a user profile and not future session
refinement state.

## Product presentation

Optional per evaluated product:

- brand
- model
- category
- outbound offer URL (`http`/`https` only)
- category-flexible fit attributes (key, label, value, unit, status, evidence IDs)

Brand and model are used only when captured. Canonical presentation does not
parse `display_name` to invent them. `display_name` may still render as the
product identity. Images are not part of this contract.

Fit rows come only from captured `fit_attributes`. Canonical UUID Compare does
not fall back to headphone fixture rows such as Comfort or Sound quality.

## Recommendation reasoning

Optional:

- `recommendation_reasons`
- `best_for`
- `alternative_tradeoffs`

These copy reasons actually used. They do not generate marketing personas.

## Economics and evidence

Existing canonical economics and evidence IDs remain the authority. The
presentation contract does not duplicate prices or create a second source
system.

Affiliate wrapping stays downstream. Commission cannot influence PiqScore,
Recommendation, Best Piq, qualification, or ranking.

## Capture path

`attach_presentation_contract` copies caller-supplied facts onto a new
snapshot. There is still no live search → research → snapshot production
pipeline. If upstream evaluation does not produce a field, it stays absent.

## Consumer and Ask

`page_view_from_snapshot` and `packet_from_snapshot` consume 1.2 fields when
present and degrade truthfully when they are not. Ask PiqSavi remains on
Results, Compare, and Why. It may explain captured context. It must not change
Best Piq, rerank, research, or reprice.
