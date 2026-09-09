# Sprint 28 — Consent audit staging evidence template

**Document type:** Sanitized technical staging evidence template  
**Execute only after** an approved published Privacy/Terms version exists.  
**Do not** publish counsel drafts to fill this template.

Sprint 28 internal engineering ships the inspection tooling. This package is
**blank until owner/operator publication + staging execution**. The agent must
not deploy staging or fabricate consent rows.

---

## 1. Prerequisites (owner/operator)

- [ ] EXT-19 written approval of the **published** consumer documents exists
- [ ] Approved HTML is in `docs/legal/published/` (not a counsel draft)
- [ ] `LEGAL_TERMS_PUBLISHED_VERSION_ID` / `LEGAL_PRIVACY_PUBLISHED_VERSION_ID` set on staging
- [ ] Staging deploy of that revision completed by operator (not this agent)

## 2. Host identity

| Field | Value |
|-------|--------|
| Environment | |
| HTTP hostname | |
| Deployed SHA | |
| `/privacy` HTTP | expect 200 after publication |
| `/terms` HTTP | expect 200 after publication |
| `GET /api/v1/legal/publication-status` | |

## 3. Synthetic account

Use `@example.invalid` only. Do not record passwords or bearer tokens.

| Role | Email | user_id |
|------|-------|---------|
| Subject | | |
| Isolation witness | | |

## 4. Consent inspection

| Check | Expected | Observed |
|-------|----------|----------|
| Subject `GET /api/v1/auth/account/consents` | 200; records for published version ids | |
| `unpublished` | false after publication | |
| Isolation witness consents | no subject email/user_id | |
| Unauthenticated consents | 401 | |
| Query `?user_id=` retarget | ignored; caller only | |
| `/account#consents` | shows the same records | |

## 5. Non-claims

This evidence does not certify legal compliance, DSAR completeness, or counsel approval.

## 6. Conclusion

Leave blank until executed.
