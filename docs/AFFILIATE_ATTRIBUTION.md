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

## 2026-09-07 public-beta posture (additive)

Attribution remains available for later monetization activation. September launch must not initiate a PiqSavi affiliate attribution cookie, affiliate Sub ID, or affiliate redirect/tracking layer on ordinary outbound merchant links. Affiliate conversion is not a Sprint 39 launch-acceptance metric.
