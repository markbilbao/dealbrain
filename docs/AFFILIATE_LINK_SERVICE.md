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
