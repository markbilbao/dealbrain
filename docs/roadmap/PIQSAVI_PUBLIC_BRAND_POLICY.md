# PiqSavi — Public Brand Policy

**Status:** LOCKED  
**Authority:** Product owner public-brand decision  
**Scope:** Documentation-only brand lock; does not authorize application, DNS, TLS, email, or infrastructure mutation  
**Internal technical codename:** DealBrain  
**Roadmap endpoint:** Sprint 46 (unchanged)

---

## 1. Status

This public-brand policy is **LOCKED**.

The PiqSavi public brand is locked and may not be replaced or renamed unless the product owner explicitly authorizes another public-brand decision.

The public/internal separation (PiqSavi vs DealBrain) is intentional and permanent unless the owner explicitly changes it later.

---

## 2. Public brand

| Field | Locked value |
|-------|--------------|
| Public product brand | **PiqSavi** |
| Preferred display | **PiqSavi** |

Spelling must remain exactly `PiqSavi` on public consumer surfaces.

---

## 3. Tagline

| Field | Locked value |
|-------|--------------|
| Public tagline | **Your AI Personal Shopper** |

Use exactly this string where a public tagline is displayed. Do not substitute alternate taglines without owner authorization.

---

## 4. Domain

| Field | Locked value |
|-------|--------------|
| Primary public domain | **piqsavi.com** |
| Canonical public URL | **https://piqsavi.com** |

Owner report (not yet repository-evidenced): `piqsavi.com` has been purchased and is under owner control through Cloudflare. Registrar/account proof remains pending. See EXT-10 in [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md).

---

## 5. Public / internal naming boundary

| Layer | Name | Rule |
|-------|------|------|
| Public consumer product | PiqSavi | Presented to consumers, legal/marketing copy, SEO, public email identity, and consumer UI |
| Internal engineering codename | DealBrain | Retained for repository, infrastructure, CI/CD, historical docs, and operational identifiers |

Do not treat a public-brand change as a mandate to rename internal technical identifiers.

Do not mechanically rename product-feature concepts merely because the master brand changed.

---

## 6. Internal identifiers that remain DealBrain

Keep existing technical identifiers including (non-exhaustive):

- repository name
- Git history
- package name
- GHCR repository
- `DEALBRAIN_IMAGE`
- Terraform resource names
- Terraform state
- AWS tags
- AWS IAM names
- AWS Secrets Manager paths
- SSM document names
- deployment paths
- `/opt/dealbrain`
- `/var/log/dealbrain`
- Compose project names
- database names/users/schemas
- migration history
- CI/CD identifiers
- internal service names
- internal monitoring identifiers
- historical sprint/evidence documents

**Do not perform cosmetic infrastructure renaming** for public-brand launch.

---

## 7. Public surfaces that must become PiqSavi

When public-brand implementation sprints execute (not this documentation task), these consumer-facing surfaces must use PiqSavi:

- Consumer web application chrome and copy
- Title tags, meta descriptions, Open Graph / social cards
- Install / PWA naming surfaces
- Transactional email From name, subjects, and bodies
- Password-reset and verification link bases on `piqsavi.com`
- Terms of Service and Privacy Policy consumer product naming
- Public legal / privacy / support contact identities (`@piqsavi.com`)
- Public marketing claims and launch communications
- Public API/human-readable values exposed to consumers (after implementation)

Primary implementation sprint: **Sprint 29**. Production hostname cutover evidence: **Sprint 41**. Final claims/brand gate: **Sprints 44–45**.

---

## 8. PiqScore / DealScore naming boundary (locked)

Owner-approved strategy through V1.0: **public PiqScore / internal DealScore**.

| Layer | Name | Rule |
|-------|------|------|
| Public consumer feature | **PiqScore** | Consumer UI, human-readable OpenAPI prose, disclosures, and public explanations |
| Internal engineering/scoring contract | **DealScore** | Engines, classes, modules, machine JSON fields, routes, digests, and persistence |

Explicit locked rules:

- **PiqScore** is the consumer-facing score feature name.
- **DealScore** remains the internal engineering/scoring contract through V1.0.
- `WeightedDealScoreEngine` remains unchanged.
- `DealRecommendationService` remains unchanged.
- Machine `deal_score` / `personal_deal_score` / `global_deal_score` fields remain unchanged.
- V1 `/api/v1/dealscore/...` paths and the OpenAPI machine tag `dealscore` remain unchanged.
- `PersonalDealScore` remains an internal technical identifier.
- Consumer-visible PersonalDealScore may be displayed as **Personalized PiqScore** (never `PersonalPiqScore` unless separately approved).
- No protected digest may be regenerated solely for naming.
- A full internal DealScore→PiqScore technical migration is **not** authorized.

Do **not** treat public PiqScore naming as a mandate to rename internal DealScore identifiers.

Any other user-visible feature name containing **DealBrain**, **Deal**, or **Brain** must still be reviewed individually.

Named public features that remain unchanged by this lock:

- Shopping Assistant
- Personal Agent
- Merchant Platform
- Community Intelligence

---

## 9. OpenAPI extension compatibility policy

Decision for existing `x-dealbrain-*` public/vendor OpenAPI extension keys:

1. Do not delete or blindly rename existing `x-dealbrain-*` keys.
2. Public canonical branding should eventually use `x-piqsavi-*` where a public branded extension is justified.
3. Existing `x-dealbrain-*` keys may remain temporarily as compatibility aliases.
4. No new public feature should depend on `x-dealbrain-*`.
5. Before removal, verify actual consumers and tests.
6. Final removal decision belongs to later API/public-contract review, no later than **Sprint 44**.
7. Human-readable values exposed to consumers should use PiqSavi after the public-brand implementation.

No application/OpenAPI code changes are authorized by this document alone.

---

## 10. Domain-host architecture

Recommended hostname policy:

| Hostname | Role |
|----------|------|
| `piqsavi.com` | Canonical consumer web application |
| `www.piqsavi.com` | Redirect to `piqsavi.com` |
| `api.piqsavi.com` | Planned public production API hostname |
| `staging.piqsavi.com` | Planned controlled staging web hostname |
| `api.staging.piqsavi.com` | Optional; do not introduce unless justified later |

Canonical public URL remains `https://piqsavi.com`.

---

## 11. DNS / TLS non-authorization statement

This document records brand and hostname **policy only**.

It does **not** authorize:

- DNS configuration
- TLS / certificate issuance or attachment
- Cloudflare proxy configuration
- production routing configuration
- email authentication configuration
- application domain cutover

Keep external dependencies separate:

| ID | Concern |
|----|---------|
| EXT-10 | Domain ownership |
| EXT-11 | DNS |
| EXT-12 | TLS / certificate |

Do not merge those dependencies. Do not mark EXT-10 `provisioned` from brand documentation alone.

---

## 12. Email-domain policy

### Planned public addresses (not claimed to exist yet)

- `hello@piqsavi.com`
- `support@piqsavi.com`
- `legal@piqsavi.com`
- `privacy@piqsavi.com`
- `partners@piqsavi.com`

### Transactional sender candidates

- `no-reply@piqsavi.com`
- or `notifications@piqsavi.com`

Do **not** select or purchase a paid email provider from this document. Do **not** claim these mailboxes exist yet.

### Sprint 27 requirements (future implementation)

Sprint 27 must establish:

- transactional email provider
- sending-domain verification
- SPF
- DKIM
- DMARC
- PiqSavi From name
- verification links using `piqsavi.com`
- password-reset links using `piqsavi.com`
- centralized public-site / link-base configuration

---

## 13. Brand-asset policy

Approved PiqSavi logo assets are being developed separately.

- Do **not** invent logo files in-repo for this lock.
- Do **not** create placeholder logos that could accidentally ship.

### Required future assets

- primary logo SVG
- dark logo SVG
- light logo SVG
- symbol-only SVG
- 1024×1024 app-icon master
- favicon SVG
- favicon ICO
- favicon 32×32 PNG
- Apple touch icon 180×180
- PWA 192×192
- PWA 512×512
- maskable PWA 512×512
- Open Graph / social image 1200×630
- email-safe logo PNG
- loading / splash mark

Final physical paths should be established when **Sprint 29** creates the production consumer frontend.

---

## 14. SEO / public-metadata policy

This is a **pre-launch brand establishment**, not a mature-site SEO migration.

Future public metadata must use **PiqSavi**.

Canonical root: `https://piqsavi.com`

Later implementation must cover:

- title tags
- meta descriptions
- canonical URLs
- Open Graph
- Twitter / social cards
- Organization schema
- WebSite schema
- WebApplication / SoftwareApplication schema where accurate
- sitemap
- robots.txt
- noindex staging policy
- social preview imagery

Do not create SEO implementation files from this documentation task alone.

---

## 15. Testing policy

Public-brand implementation must eventually prove:

- public brand boundary tests (no unintended consumer-facing DealBrain leakage)
- public score feature presents as PiqScore while internal DealScore contracts remain
- internal DealBrain identifiers remain operational
- staging pages are non-indexable
- reset / verification links resolve to PiqSavi public configuration
- production host map matches this policy (Sprint 41+)

No test-suite changes are authorized by this document alone.

---

## 16. Change-control policy

The PiqSavi public brand is locked and may not be replaced or renamed unless the product owner explicitly authorizes another public-brand decision.

Additional change-control rules:

1. Public brand authority for Global Public Beta lives in this document.
2. Architecture Lock retains domain-ownership authority for engineering domains; this policy does not redistribute DealScore, Recommendation, affiliate, or merchant-neutrality ownership.
3. Historical sprint/evidence documents are not rewritten solely to replace DealBrain with PiqSavi.
4. Feature names containing Deal / Brain / DealBrain require individual review; no blanket rename.
5. Infrastructure cosmetic renames are out of scope for public-brand launch.
6. EXT-10 / EXT-11 / EXT-12 status advances only with retained non-secret evidence matching the register legend.

---

## Related documents

- Master roadmap: [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
- External dependencies: [`EXTERNAL_DEPENDENCY_REGISTER.md`](EXTERNAL_DEPENDENCY_REGISTER.md)
- Architecture Lock: [`../architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md)
- Sprint 26 bootstrap checklist: [`evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)

---

**End of PiqSavi public brand policy.**  
Documentation-only. No application, DNS, TLS, email-provider, AWS, Cloudflare, or workflow mutation is authorized by this document alone.
