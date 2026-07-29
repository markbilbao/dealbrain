# Buying Advisor

**Status:** Sprint 16  
**Module:** `app/intelligence/personal/buying_advisor.py`

## Purpose

Generate **structured, evidence-backed buying advice** for a product and profile.

## Verdicts

| Verdict | Label |
|---------|-------|
| `excellent_choice` | Excellent choice |
| `good_value` | Good value |
| `worth_waiting` | Worth waiting |
| `price_likely_to_drop` | Price likely to drop |
| `not_recommended` | Not recommended |
| `alternative_available` | Alternative available |
| `upgrade_not_worthwhile` | Upgrade not worthwhile |
| `too_expensive` | Too expensive |
| `poor_community_trust` | Poor community trust |

## Decision order (summary)

1. Already owned → `upgrade_not_worthwhile`
2. Disliked brand → `not_recommended`
3. Weak community trust (< 0.35) → `poor_community_trust`
4. Price > budget × 1.15 → `too_expensive`
5. Price falling / not near low → `price_likely_to_drop` or `worth_waiting`
6. Weak fit with better alternative → `alternative_available`
7. High PersonalDealScore + budget/preference thresholds → `excellent_choice` / `good_value`
8. Otherwise evidence-backed `good_value` or `not_recommended`

Every verdict includes `summary`, `explanation`, and evidence references. Advice never fabricates positive community sentiment or future price guarantees.
