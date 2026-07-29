# Community Trust Score

**Status:** Sprint 14  
**Implementation:** `CommunityTrustCalculator` (deterministic)

## Output

- Score: integer **0–100**
- Band: `High` (≥75), `Medium` (≥50), `Low` (<50)
- Factors: 0–1 contributions
- Explanation: short human-readable summary

## Factors

| Factor | Intent |
|--------|--------|
| `evidence_count` | More supporting items → higher |
| `independent_threads` | Distinct threads / videos / questions |
| `independent_users` | Distinct authors when available |
| `source_diversity` | Multiple connectors represented |
| `topic_consistency` | Avoid single-topic spam and total chaos |
| `ai_agreement` | Multi-model agreement when available |
| `data_freshness` | Newer median evidence age scores higher |
| `coverage` | Breadth of topics discussed |

Weights are fixed in code (sum to 1.0). No ML training at runtime.

## Guarantees

- Pure function of evidence (+ optional AI agreement + clock)
- Never invents missing discussions
- Empty evidence → score `0` / band `Low`
