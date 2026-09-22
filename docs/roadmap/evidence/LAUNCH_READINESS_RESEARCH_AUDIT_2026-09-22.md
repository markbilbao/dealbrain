# Launch-readiness research audit — 2026-09-22

**Status:** Documentation and fail-closed launch patch only. Not an architectural rewrite.  
**Audited main:** `06be0411479c6c5dfba9d8cf94ca8bfc3b3e9620`  
**Scope:** Compare recent launch-readiness research against the existing PiqSavi implementation. Preserve current ranking, matching, freshness, review-validation, and evidence systems.  
**Out of scope:** Sprint 32 UCP lifecycle mutation, Sprint 38 start, Shopify calls, AWS/deployment, stale PR #155.

## Research conclusions (not overstated)

These observations motivated the audit. They are not treated as proof that PiqSavi already fails in production, and they do not justify building parallel engines.

- Agent-shopping research shows recommendations can change with source context, source order, memory, and tool-call or retrieval design. Unchanged inputs should therefore be tested for product, rank, and evidence stability.
- A recent commercial-advice audit found that recommended products and displayed sources can change across repeated requests. That is a trust risk when the underlying catalog is unchanged.
- Review-summary research shows material disagreement between AI textual summaries and aggregate ratings can reduce trust. Transparency about the disagreement matters more than forcing one signal to win.
- Variant-matching research reinforces distinguishing same-product identity from exact variant attributes such as storage and color. Listing-specific scoring should not silently merge a different matched variant.

This document does not copy paper passages and does not claim a new recommendation, review, or matching system is required.

## What already existed

PiqSavi already has the systems the research would otherwise reinvent:

| Capability | Existing location |
|---|---|
| Deterministic Recommendation / PiqScore ranking | `ShoppingRecommendationRanker`, `WeightedDealScoreEngine` |
| Deterministic tie-breaking | Ranker key + DealScore `listing_id` tie-break |
| Exact repeat-query recommendation test | `tests/integration/test_recommendation_flow.py` |
| Exact product / variant matcher | `ExactVariantProductMatcher` |
| Variant conflict handling for storage / color | Matcher `SAME_PRODUCT_DIFFERENT_VARIANT` |
| Marketplace provenance | `MarketplaceDataService.shopping_enrichment` |
| Freshness states | `evaluate_freshness` / `is_current_live_price` |
| Content-hash duplicate skipping | Marketplace normalization / sync |
| Incremental checkpoints | Marketplace sync engine |
| Price and inventory snapshots | Price-history + marketplace offers |
| Low-confidence / ambiguous match review routing | Marketplace matcher + sync `held for review` |
| Review counts and 1–5 star distributions | Review Intelligence collectors / comparison |
| Evidence-grounded review claims | `ReviewAnalysisValidator` |
| Multi-provider disagreement tracking | `ConsensusService` / `AnalysisDisagreement` |
| Unsupported-claim validation | Shopping + review + knowledge-graph validators |
| Explicit rejection / qualification of "fake reviews" | Shopping assistant unsupported-phrase list |

No duplicate systems were added.

## Real gaps found

1. **Stale live ranking authority.** `_apply_marketplace_data_provenance` gave `+0.08` and could set `data_status=live` when enrichment was live but `is_current_live_price` was false, including simulated live. That could promote a mock candidate or response to live and change ranking without current-live evidence.
2. **Review-summary rating vs written polarity.** `ReviewSummaryService` preserved both `average_rating` and provider `overall_sentiment` but did not surface a final consistency disagreement when those polarities materially conflicted.
3. **Assistant-level repeat-query metrics.** DealScore / recommendation-engine stability existed, and some shopping queries were exercised, but the assistant fixture catalog did not have an explicit 5-query × 3-run overlap / rank / evidence / identity / known-price suite.

## Launch-critical changes in this patch

1. Marketplace provenance is fail-closed:
   - fresh current live still becomes `live` with the existing `+0.15` boost;
   - live enrichment that is not current gets no live ranking boost and does not promote mock/imported candidates to live;
   - imported enrichment still applies `+0.03` when it does not downgrade a stronger trusted status;
   - `known_price` is not changed by marketplace enrichment.
2. `ReviewSummaryService` applies a deterministic final consistency guard:
   - broad polarity only (`positive`/`very_positive`, `mixed`, `negative`);
   - conflict adds `AnalysisDisagreement.field=summary_rating`, keeps both signals, warns the shopper, caps consensus confidence at `0.60`, uses `Consider Carefully`, and sets `processing.summary_rating_conflict=true`;
   - aligned summaries set the flag false and keep existing behavior.
3. Repeat-query stability coverage was extended on the existing Shopping Assistant + PH/PHP fixture catalog. Availability accuracy is recorded as **unavailable** because the fixture has no first-class availability observation.

## Product identity audit

Existing tests still prove:

- Pro vs Pro Max is a different product
- 256GB vs 512GB is same product / different variant and not a match
- color conflicts are different variants
- ambiguous / low-confidence marketplace matches are held for review
- unsupported graph claims are rejected

PiqScore currently scores listing-specific attributes (`listing_id`, price, seller, shipping, official-store, warranty, return policy). It does not merge evidence from a different matched variant. No runtime change was made in this area.

## P1 follow-ups — not this launch patch

These remain post-launch / later architectural work. Do not treat this PR as having implemented them.

1. **Per-attribute evidence envelope** before broad cross-source attribute merging:
   - exact `product_id` / variant identity
   - attribute
   - value
   - source
   - evidence reference
   - verification state
   - `checked_at`
   - verification states: `verified`, `seller_claim`, `unverified`, `conflicting`, `not_found`, `not_applicable`
2. **Review-summary enrichment:**
   - rating distribution
   - review observation recency
   - positive / negative theme coverage
   - available verification signals
   - explicit disagreement explanation beyond the launch consistency guard
3. **Catalog change classifier** before persistent catalog / index scaling:
   - price / stock / delivery / seller → metadata-only update
   - title / model / category / description / spec → renormalize / reindex
   - unchanged → skip
   - removed product → tombstone / deactivate
4. **Production-like stability monitoring:**
   - repeated queries against the real retrieval / source layer
   - measure product overlap, rank movement, and source churn
   - fixture-catalog stability is not a substitute for live-source monitoring

## Confirmations

- No Shopify call
- No AWS mutation or deployment
- Sprint 32 remains open / in progress
- Sprint 38 remains unstarted
- Stale PR #155 was not revived or modified
