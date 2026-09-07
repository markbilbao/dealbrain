# Affiliate Disclosure (Sprint 20)

**Status:** Sprint 20  
**Service:** `AffiliateDisclosureService` in `app/services/affiliate_disclosure_service.py`  
**Helpers:** `app/affiliate/disclosure/texts.py`

## Supported hooks

- General affiliate disclosure
- Merchant-specific disclosure
- Regional disclosure
- FTC disclosure **placeholder**

## Limitations

- Demo copy only — **not legal advice**
- No compliance workflow or counsel review pipeline
- No real FTC filing / merchant portal integration

## 2026-09-07 launch-UI rule (additive)

Keep this disclosure architecture. Do not delete it. The published Affiliate & Advertising Disclosure may remain future-capable with conditional wording (“may”, “where active”).

Launch UI must **not** show active-affiliate disclosure such as “Affiliate link” or “PiqSavi may earn a commission” next to ordinary outbound merchant links. Canonical UUID pages omit inactive affiliate-disclosure copy. Future affiliate activation must explicitly attach the appropriate disclosure together with the affiliate action; that path is not enabled by this launch lock. This note does not publish legal documents and does not claim counsel approval.
