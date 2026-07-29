# Preference Engine

**Status:** Sprint 16  
**Module:** `app/intelligence/personal/preference_engine.py`

## Purpose

Compute **normalized weighted preference scores** for a catalog product against a customer profile.

## Dimensions

| Dimension | Default weight | Signal |
|-----------|----------------|--------|
| `budget_fit` | 0.18 | Known price vs profile budget + price sensitivity |
| `brand_affinity` | 0.14 | Favorite / disliked brands |
| `feature_match` | 0.14 | Use cases, priorities, favorite categories |
| `marketplace_preference` | 0.08 | Preferred marketplaces |
| `community_sentiment` | 0.08 | Optional community collaborator (else neutral 0.5) |
| `review_quality` | 0.10 | Rating + review volume |
| `knowledge_graph_proximity` | 0.06 | Optional KG collaborator (else neutral 0.5) |
| `availability` | 0.06 | Near-low / listing availability cues |
| `deal_score` | 0.16 | Catalog global DealScore / 100 |

Weights are normalized to sum to 1.0.

## Output

`PreferenceScoreResult`:

- `total_score` ∈ [0, 1] — sum of weighted dimension scores
- per-dimension `score`, `weight`, `weighted_score`, `evidence`
- `confidence` / `confidence_band` derived from total score
- `evidence_ids` for auditability

## Rules

- Missing attributes produce **neutral 0.5**, not invented affinity.
- Disliked brands score near-zero brand affinity.
- Never invent community or graph signals when collaborators are absent.
