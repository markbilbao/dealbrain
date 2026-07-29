# Personal DealScore

**Status:** Sprint 16  
**Module:** `app/intelligence/personal/scoring_engine.py`

## Purpose

Produce a **PersonalDealScore** (0–100) that blends the catalog’s global DealScore with profile-specific fit.

## Formula (v1)

```
PersonalDealScore = 100 * (
  0.30 * global_deal_score_norm
+ 0.22 * preference_fit
+ 0.18 * budget_fit
+ 0.12 * brand_affinity
+ 0.10 * ownership_compatibility
+ 0.08 * community_trust
)
```

Where:

- `global_deal_score_norm` = catalog `deal_score / 100` (or 0.5 if missing)
- `preference_fit` = PreferenceEngine `total_score`
- `budget_fit` / `brand_affinity` = preference dimensions
- `ownership_compatibility` = wishlist / owned / ecosystem heuristics from explicit profile fields
- `community_trust` = optional collaborator signal or preference community dimension

## Output fields

`PersonalDealScore` includes the blended score plus factor breakdown and evidence IDs for explanations.

## Rules

- Does **not** rewrite the protected DealScore engine; it composes catalog DealScore values.
- Does not invent purchase history; ownership uses fixture `owned_products` / `accessories_owned` / `wishlist` only.
- Factors are listed explicitly so Buying Advisor and demos can cite them.
