# PiqSavi Founder Counsel Quick Reference

**Consultation:** August 19, 2026 — 10:00 AM PH · **Counsel:** Pauline Anne Sambuang (“Atty. Pau”)

**Status:** INTERNAL — FOUNDER MEETING CHEAT SHEET · **Not for publication** · **Not legal advice** · **Not evidence of legal approval**

Full agenda: `docs/legal/PIQSAVI_COUNSEL_CONSULTATION_AGENDA.md`

## 30-Second Product Explanation

PiqSavi is an AI personal shopper that helps users compare products and offers from third-party merchants. It evaluates the offers available to it, creates an objective PiqScore, then separately provides a Recommendation and AI explanation. Purchases are generally completed with the merchant, not with PiqSavi. We may earn affiliate commissions where approved, but affiliate compensation does not increase PiqScore or organic Recommendation ranking. Current merchant integrations are not production-certified.

## Top 10 Decisions I Need From Atty. Pau

1. [ ] What legal structure should operate PiqSavi at beta? (individual / sole proprietor / company) — and what legal/business identity must appear publicly?
2. [ ] Which countries should be included in the first public beta?
3. [ ] How should PiqSavi legally describe its role relative to merchants? (comparison / referral / intermediary / other counsel wording)
4. [ ] What permissions do we need from each merchant/provider before we can: search/access product data; display/compare; cache/store; use in AI-assisted evaluation; attach affiliate links?
5. [ ] Is affiliate approval alone enough to use merchant product data?
6. [ ] What Terms acceptance mechanism is required? (clickwrap / checkbox / policy version record / evidence of assent)
7. [ ] What age/minor rule should we implement?
8. [ ] What minimum deletion/export/retention setup is required before beta? (manual privacy@ vs self-service; verification; response time; retention periods)
9. [ ] Do we need a cookie/CMP banner at beta if the app currently has no app cookies/localStorage analytics/tracking pixels? Also Cloudflare/infra cookies?
10. [ ] What must be finalized before we can publish Terms/Privacy/disclosures and call the beta legally launch-ready?

## Merchant / Affiliate Questions

- Which of Shopee, Lazada, TikTok Shop, Amazon, Temu appear legally viable for the intended PiqSavi model?
- What exact rights should we confirm before applying?
- Does affiliate permission allow product data use, or are those separate rights?
- What should we do when provider terms are silent or ambiguous?
- What wording/disclosure is mandatory once a provider is approved?

**Preserve:** technical capability ≠ contractual permission · affiliate permission ≠ product-data permission · provider approval ≠ blanket capability permission · unknown capability = fail closed

## Privacy / Data Questions

- Legal bases by launch market?
- Minimum deletion/export setup for beta?
- Retention periods by data category?
- Identity verification for privacy requests?
- International transfer / provider disclosure wording?
- Is a DPO or other formal privacy role needed?

## AI / Recommendation Questions

**Preserve:** PiqScore = objective offer evaluation · Recommendation = separate action-oriented layer · Personalization may change personally recommended Piq without rewriting canonical PiqScore · AI = explanation/reasoning layer

- Are current disclosure drafts sufficient?
- Does personalization trigger profiling/ADM obligations?
- What user controls or opt-outs are required?
- What must be confirmed before live AI provider HTTP is enabled?
- What disclaimer wording is needed for AI limitations?

## Consumer / Marketplace Questions

- Price / availability limitations? · Shipping / returns / warranty wording? · Seller trust / authenticity? · Product safety / recall wording? · Mandatory consumer-rights carve-outs?

## Terms / Liability Questions

- Governing law? · Venue / arbitration? · Liability limitations? · Warranty disclaimers? · Indemnity / consumer-rights carve-outs?

## Important Facts to Tell Counsel

- Merchant integrations not production-certified · EXT-01…05 not submitted · Self-service deletion not implemented · Automated personal-data export not implemented · No final legal retention schedule · App cookie/localStorage/sessionStorage analytics inventory empty (repo evidence) · Live AI HTTP disabled by default · Affiliate neutrality architecture-locked · PiqScore only for offers actually evaluated · Unknown merchant data stays unknown (not treated as negative)

## If Counsel Says “No / Not Yet”

If blocked on: launch a market · merchant product data · affiliate links · enable AI · publish a policy · manual deletion/export · avoid a CMP · launch without age gate — record: (1) what is blocked (2) evidence/approval required (3) legal wording vs engineering (4) written follow-up needed? (5) condition to proceed safely.

## Decisions / Follow-Ups

| Topic | Decision / Guidance | Written Follow-Up Needed? | PiqSavi Action |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

## Evidence Rule

consultation held ≠ written approval · guidance received ≠ document approved · application allowed ≠ application submitted · application submitted ≠ provider approved · provider approved ≠ every capability permitted · policy approved ≠ policy published · policy published ≠ feature implemented

Do not put privileged counsel advice into Git.

Sprint 26: OPEN · Sprint 27: NOT STARTED · Sprint 28: NOT STARTED · EXT-01…05: not_started · EXT-19: applied · EXT-20/21/22: not_started · Legal approval: NOT CLAIMED · Merchant/provider approval: NOT CLAIMED
