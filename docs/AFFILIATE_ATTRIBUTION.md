# Affiliate Attribution (Sprint 20)

**Status:** Sprint 20  
**Engine:** `AttributionEngine` in `app/affiliate/attribution/engine.py`  
**Service:** `AffiliateTrackingService.attribute()` in `app/services/affiliate_tracking_service.py`

## Models

| Model | Behavior |
|-------|----------|
| `last_click` | Most recent matching click wins |
| `first_click` | Earliest matching click wins |
| `direct` | No click required |
| `organic` | Prefer organic / unknown sources |
| `internal_recommendation` | Prefer Shopping Assistant / recommendation API clicks |
| `external_campaign` | Prefer campaign-tagged clicks (future hook) |

## Limitations

- Simulated only — no real conversion postbacks
- No billing or payout settlement
- Does not modify DealScore
