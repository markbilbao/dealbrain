# Engineering vendor / processor inventory (Sprint 28.1)

**Status:** Factual repository inventory — **not** a DPA register, **not** legal controller/processor determinations.
**Counsel-owned:** legal role (controller/processor/subprocessor), DPA status, international-transfer conclusions.

No DPA status is asserted here. Legal-role questions remain **TBD**.

| Vendor / service | Purpose (repo-evidenced) | Data transmitted/stored if known | Implementation state | Legal role / DPA |
|------------------|--------------------------|----------------------------------|----------------------|------------------|
| Application database (PostgreSQL / SQLAlchemy operational store) | Persist accounts, sessions, profiles, saved items, consent records, ops entities | Account and related payloads in `operational_entities` | Implemented (Sprint 23 adapters; memory default in development) | TBD — counsel-owned |
| In-memory process stores | Dev/demo persistence | Same domain shapes | Implemented for non-prod defaults | N/A |
| Resend | Transactional identity email (reset/verify) | Email address + message content **when provider is configured and sending** | Adapter implemented (Sprint 27.1); live staging inbox E2E **not** proven; EXT-08 `applied` / AMBER | TBD — counsel-owned; DPA **not** recorded here |
| Null email sender | Tests/dev no-op | None sent | Implemented | N/A |
| Google Workspace / Gmail | Receive `support@` / `privacy@` mail | Inbound message contents to provisioned aliases | EXT-17 / EXT-18 `provisioned` | TBD — counsel-owned |
| AWS (staging/prod path) | Hosting, secrets, deploy | App DB, secrets, logs if CloudWatch used | Staging path evidenced; production apply incomplete (EXT-13 partial) | TBD — counsel-owned |
| Cloudflare | Domain registrar / possible edge | Domain registration; **proxy/WAF cookies not proven in app code** | EXT-10 registrar `approved`; public DNS/TLS EXT-11/12 `not_started` | TBD — counsel-owned |
| OpenAI / Anthropic / Gemini | Optional AI explanation/review | Product/review/shopping payloads **if live HTTP enabled** | Adapters present; live HTTP off by default | TBD — counsel-owned |
| GitHub | Source / CI | Source and CI metadata, not end-user account PII by default | Engineering use | TBD — counsel-owned |
| Analytics provider | Product analytics | None currently | EXT-15 `not_started`. **Not added in 28.1** | TBD — counsel-owned |
| Error-tracking provider | Ops errors | None currently | EXT-16 `not_started` | TBD — counsel-owned |
| Cookie-consent / CMP vendor | Consent UX | None currently | EXT-22 `not_started`. **Banner not implemented in 28.1** | TBD — counsel-owned |
| FX provider | FX quotes | None currently | EXT-23 `not_started` | TBD — counsel-owned |
| Merchant / affiliate platforms (Shopee, Lazada, TikTok Shop, Amazon, Temu, Involve Asia, …) | Product data / affiliate | Not live certified | EXT-01…05 `not_started`; 28.1 does **not** modify affiliate routing | TBD — counsel-owned |
| Legal counsel (Pauline Anne Sambuang) | Consumer legal review engagement | Engagement materials | EXT-19 `applied`; written approval **not** present | N/A |

## Changes vs prior counsel fact-spec §15

- Resend is now **integrated as an adapter** (Sprint 27.1). This inventory does **not** claim production sender readiness or EXT-09 DNS verification.
- First-party consumer cookies/storage listed in [`ENGINEERING_PII_INVENTORY.md`](ENGINEERING_PII_INVENTORY.md) now exist; they are not third-party processors.
- No analytics, advertising pixels, or CMP vendor was added in Sprint 28.1.
