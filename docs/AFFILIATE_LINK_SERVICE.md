# Affiliate Link Service (Sprint 20)

**Status:** Sprint 20  
**Service:** `AffiliateLinkService` in `app/services/affiliate_link_service.py`  
**Builder:** `AffiliateLinkBuilder` in `app/affiliate/linking/builder.py`

## Responsibilities

- Generate affiliate links from merchant tracking templates
- Attach tracking parameters (`campaign_id`, `sub_id`, `click_id`)
- Support deep links
- Validate http(s) URLs
- Estimate commission for reporting only

## Post-rank only

```
generate_for_recommendation(selected_product)  → AffiliateLink | None
```

Called by Shopping Assistant **after** DealScore / match ranking. Returns
`None` when no active merchant matches — never raises into the ranking path.

## Limitations

- No real affiliate network APIs or credentials
- Templates use `DEMO_*` placeholders
- Estimated commission is never a ranking input

## 2026-09-07 public-beta posture (additive)

September public beta launches **without affiliate monetization**. This service remains available for later downstream activation (organic decision → winning merchant → optional affiliate attachment). Do not delete it.

At launch:

- merchant links are ordinary outbound merchant links
- no affiliate parameters, Sub IDs, redirect/tracking layer, commission claim, or PiqSavi-initiated affiliate attribution cookie
- a legitimate merchant remains fully eligible for research, PiqScore, Best Piq, Recommendation, and an outbound link even if PiqSavi earns ₱0

`generate_for_recommendation` returning `None` / ordinary destination URLs is valid launch behavior. Affiliate activation must never modify source eligibility, evaluated set, PiqScore, Recommendation, Best Piq, or organic ordering.
