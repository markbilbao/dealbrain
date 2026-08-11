# PiqSavi Account Deletion, Data Export & Retention Policy

**Status:** DRAFT — COUNSEL REVIEW REQUIRED
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**
**Not evidence that self-service deletion/export is currently implemented**
**Not evidence that a final retention schedule has been approved**

<!--
INTERNAL FACTUAL BASIS (remove or relocate before any public use):
Primary sources:
  - docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_COOKIE_TRACKING_NOTICE_COUNSEL_DRAFT.md
Supporting product / infrastructure docs inspected as needed:
  - docs/AUTHENTICATION.md / docs/SECURITY_MODEL.md / docs/SESSION_MANAGEMENT.md
  - docs/PERSISTENCE.md / docs/USER_PLATFORM.md / docs/BACKUP_RESTORE.md
  - docs/roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md
  - docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md
  - app/auth/service.py (session / reset / verification expiries)
  - app/intelligence/shopping_assistant/memory.py (conversation TTL)
  - app/api/v1/endpoints/user.py (saved-product delete)
  - infra/terraform environments (intended RDS backup / CloudWatch log retention defaults)
Authoritative main at drafting: e4c91ac88fc42c5d42779c9deca2fea698077a66
Fact-spec audit HEAD noted in fact-spec: 7e1adaf01b46ba3029778f0b2eebe70737e1ef56
Internal technical codename: DealBrain (do not use in public-facing policy body)
Internal scoring names: DealScore / PersonalDealScore (public name remains PiqScore)
This draft does not claim EXT-19 written approval, EXT-20/21 publication, Sprint 27/28 start,
self-service deletion/export, automated DSAR download, final retention schedule approval,
or legal sufficiency.
Repository re-verification at drafting (current main): no consumer account-deletion endpoint;
no personal-data export / DSAR download endpoint; UserRepository.delete NOT FOUND; consumer
deactivation API NOT FOUND; per-item saved-product DELETE exists; privacy@piqsavi.com and
support@piqsavi.com provisioned; Sprint 28 Status: Planned / NOT STARTED.
-->

---

**Effective Date:**
[COUNSEL TO CONFIRM]

**Last Updated:**
[COUNSEL TO CONFIRM]

**Operator:**
[COUNSEL TO CONFIRM: legal operator/entity name]

**Privacy contact:** privacy@piqsavi.com
**General support:** support@piqsavi.com

---

## 1. Purpose

This Account Deletion, Data Export & Retention Policy is intended to describe, in plain language:

- how users may request deletion of account-related information;
- how users may request a copy / export of their data;
- what data categories may exist in connection with PiqSavi accounts and related operations;
- how long different categories of information may be retained;
- circumstances in which limited data may need to be retained; and
- how future self-service controls may work if and when implemented.

PiqSavi (“PiqSavi,” “we,” “us,” or “our”) is marketed as **Your AI Personal Shopper**. Among other features, PiqSavi may evaluate offers using **PiqScore** and may present separate purchase recommendations.

This document is a **founder/product draft for counsel review**. It is:

- **NOT** final;
- **NOT** for publication;
- **NOT** legal advice;
- **NOT** evidence of legal approval;
- **NOT** evidence that self-service account deletion is implemented;
- **NOT** evidence that automated data export is implemented; and
- **NOT** evidence that a final retention schedule is approved.

### Capability posture used in this draft

| Posture | Meaning in this draft |
|---------|------------------------|
| **CURRENT PRODUCT CAPABILITY** | Behavior supported by repository / product evidence reviewed for this draft |
| **PLANNED / FUTURE CAPABILITY** | Roadmap or design intent (including Sprint 28 planning) that is **not** described as currently available |
| **COUNSEL-DEPENDENT LEGAL REQUIREMENTS** | Legal scope, timing, exceptions, and market rules that require counsel confirmation |

For broader privacy processing, see the **PiqSavi Privacy Policy** (counsel draft). For account/service terms, see the **PiqSavi Terms of Service** (counsel draft). For AI, affiliate, and cookie/tracking posture, see the related counsel drafts.

---

## 2. Current Account Lifecycle Posture

This section describes **CURRENT PRODUCT CAPABILITY** grounded in repository evidence. It does **not** describe a complete privacy-rights program.

### 2.1 Account creation

Users may register an account using email, password, and display name. PiqSavi stores a **password hash**, not the plaintext password. Related profile/preference/settings records may be bootstrapped at registration.

Authentication currently uses a **Bearer-token** model rather than browser cookie-based sessions.

### 2.2 Account status / active state

Consumer accounts include an active/inactive status flag. Login may reject inactive accounts. A consumer-facing **account deactivation** API/workflow was **not found**.

**Important:** Deactivation (if later implemented) is **not** the same as deletion. This draft does not equate the two.

### 2.3 Sessions

Session records may include session identifiers, hashed tokens, expiry times, remember-me behavior, last-seen time, and revocation state. Logout may revoke the current session. Expired sessions may be treated as invalid.

Session expiry values are technical/security controls (see Section 10). They are **not** a general privacy retention policy.

### 2.4 Preferences / settings

Authenticated users may store preferences and settings (for example budget, currency, country preference, theme/language, AI-mode preference flags, notification preference flags, privacy/community-related preference dictionaries, favorites, wishlist, owned products, accessories).

### 2.5 Saved products and related activity

Account-linked saved products and related activity records (for example comparisons, searches, recommendation history, recently viewed items) may exist where those features are used.

### 2.6 Auth / security records

Authentication and security audit events may be recorded (for example register, login success/failure, logout, session expired, password-reset requested, rate-limited). Some paths may include normalized email in metadata.

Password-reset and email-verification **request records** may be created with technical expiries where those service paths exist. Full live confirmation/delivery workflows are not treated here as complete product capabilities.

---

## 3. Current Deletion Capability

### CURRENT PRODUCT CAPABILITY

Based on the current product implementation reviewed for this draft:

| Capability | Current state |
|------------|---------------|
| Per-item saved-product deletion | **Exists** (delete a specific saved product by its identifier) |
| Full self-service account deletion | **Not currently implemented** |
| Soft-delete / anonymization pipeline for accounts | **Not found** |
| Hard-delete cascading across all account-linked stores | **Not found** |
| Consumer account-deactivation workflow | **Not found** (active-flag field exists; consumer deactivate API not found) |
| Session invalidation on logout / expiry | **Exists** for session lifecycle |
| Instant erasure from all logs, backups, and third parties upon any deletion action | **Not claimed / not evidenced** |

**Closest existing delete:** removing an individual saved product does **not** mean that all related server, audit, attribution, log, backup, or third-party data is deleted.

Users should **not** assume that a “Delete Account” control currently exists in the product UI or API.

[COUNSEL TO CONFIRM: legally required deletion workflow, identity verification, response timing and exceptions by launch market]

### PLANNED / FUTURE CAPABILITY

Broader account deletion, confirmation, and propagation work is **planned** (including Sprint 28 planning materials) but **Sprint 28 is NOT STARTED**. Planned work is **not** current product capability.

---

## 4. Current Data Export Capability

### CURRENT PRODUCT CAPABILITY

Based on the current product implementation reviewed for this draft:

| Capability | Current state |
|------------|---------------|
| Automated / self-service personal-data export (DSAR-style archive download) | **Not currently implemented** |
| Formal portable export package | **Not currently implemented** |
| Authenticated access to some account/profile/preference APIs | **Partial** (account-holder API access is not a complete export package) |
| Launch **configuration** export endpoints | Exist for ops/config rehearsal; **not** personal-data portability |

Users should **not** assume they can currently download a complete account archive through an in-product control.

### Manual privacy-request handling (operating posture)

Privacy-related requests may be directed to **privacy@piqsavi.com** and may be handled manually, subject to verification and applicable law. This is an operational contact path, not a self-service export product feature.

[COUNSEL TO CONFIRM: required access/export scope, format, verification and response timing by market]

### PLANNED / FUTURE CAPABILITY

Data export product work is **planned** (including Sprint 28 planning) but **not** currently available as a self-service product feature.

---

## 5. How Users May Request Deletion or Export

### CURRENT PRODUCT CAPABILITY

For the current counsel-draft posture, users may contact:

**privacy@piqsavi.com**

for privacy-related deletion, access, or export requests.

General product support may be contacted at **support@piqsavi.com**. Privacy requests should preferentially use the privacy contact.

This draft does **not** invent a dedicated public deletion portal, in-product request tracker, or founder personal contact channel.

[COUNSEL TO CONFIRM: final request channels, identity-verification steps and required response timelines]

---

## 6. Identity Verification

PiqSavi may need to verify that a requester is authorized to act on the account before fulfilling a deletion, access, or export request.

Potential approaches may include confirming control of the account email or other account-authentication steps. This draft does **not** finalize a verification standard, authorized-agent process, or anti-fraud protocol.

[COUNSEL TO CONFIRM: identity-verification standard, authorized-agent handling and anti-fraud safeguards]

---

## 7. Data Categories

The following categories are grounded in current product behavior / repository evidence. Categories not evidenced as collected are **not** invented here.

| Category | Examples (where applicable) | Notes |
|----------|-----------------------------|--------|
| Account identity data | User identifier, email, display name, account timestamps, active/verified flags | Consumer registration fields reviewed for this draft |
| Authentication / security data | Password hash; session token hashes; CSRF prep tokens where issued | Plaintext passwords are not stored |
| Session records | Session id, expiry, remember-me, last-seen, revocation | Bearer-token model |
| Preferences / settings | Budget, currency, country preference, theme/language, AI-mode flags, notification flags, privacy/community preference dictionaries | Account-linked |
| Saved products / related activity | Saved products, comparisons, searches, recommendation history, recently viewed, favorites/wishlist/owned/accessories where used | Per-item saved-product delete may exist; account purge not found |
| Recommendation-related data | Recommendation history / personalization-linked account state where used | Separate from objective PiqScore computation |
| Affiliate click / attribution data | Click ids; optional user/session ids; merchant/product/campaign fields; simulated conversion fields | Currently demo/fixture-oriented; not treated as live provider tracking |
| Support / privacy correspondence | Messages to support@ / privacy@ and response records | Outside product DB where handled by mailbox systems |
| Security / audit logs | Auth security events; possible normalized email on some paths | May persist separately from account UI state |
| Technical / request logs | Method, path, status, duration, request id, client IP where logging captures it | Operational |
| AI / conversation state | Short-lived shopping-assistant conversation memory where that path is used | Technical TTL; not a durable privacy retention guarantee |

**Not currently evidenced as consumer account collection for this draft:** phone number, date of birth, government ID, payment-card data, precise location, biometric data.

---

## 8. What “Deletion” May Mean

Deletion of account-related information may involve one or more of the following methods, depending on data type, system design, and legal requirements:

- deleting data from active systems;
- anonymizing or de-identifying data;
- dissociating data from the account; and/or
- retaining limited data where legally or operationally justified.

This draft does **not** present these methods as final legal rights, final exceptions, or a promise that every copy of every data element can be instantly erased from all systems.

[COUNSEL TO CONFIRM: permissible deletion methods and legal retention exceptions]

Deleting a visible saved item, logging out, or ceasing to use PiqSavi is **not** automatically equivalent to full account deletion.

---

## 9. Retention Principles

PiqSavi intends to retain information only for appropriate business, security, contractual, or legal purposes, subject to counsel review and applicable law.

This draft does **not**:

- invent fixed retention periods for account data, logs, affiliate records, AI provider data, or backups as approved legal commitments;
- convert technical TTLs into public privacy retention promises; or
- conclude that any particular retention period is lawful in every market.

[COUNSEL TO CONFIRM: lawful retention purposes and required retention periods by category / market]

---

## 10. Current Coded Expiry Periods (Technical TTL ≠ Legal Retention)

**Important distinction:** Technical TTL / expiry is a security or operational control. It is **not** automatically a privacy retention policy or a public legal commitment.

### INTERNAL counsel-facing inventory (technical behavior)

| Mechanism | Current technical expiry (repository-evidenced) | Privacy retention policy? |
|-----------|--------------------------------------------------|---------------------------|
| Default session | 3600 seconds (1 hour) | No — EXPIRY ONLY |
| Remember-me / extended session | 2,592,000 seconds (30 days) | No — EXPIRY ONLY |
| Password-reset request record | approximately 1 hour | No — EXPIRY ONLY; confirm/delivery flows incomplete |
| Email-verification request record | approximately 1 day | No — EXPIRY ONLY; confirm/delivery flows incomplete |
| Shopping-assistant conversation memory | default 1800 seconds (30 minutes); configurable bound exists in app config | No — EXPIRY ONLY; process-scoped / in-memory path |
| Affiliate merchant `cookie_days` metadata | fixture/registry values (e.g. 7–30 days) | No — attribution-window config, **not** a purge job |
| Intended CloudWatch log retention (infra defaults) | staging default 14 days; production default 30 days | Infra intent only — **not** a finalized privacy retention schedule |
| Intended RDS backup retention (infra defaults) | staging default 7 days; production default ≥30 days | Infra intent only — **not** a finalized privacy retention schedule |

Do **not** convert these code/infra defaults into published legal retention commitments without counsel approval.

[COUNSEL TO CONFIRM: which technical TTLs should be described as privacy retention versus security/operational expiry]

---

## 11. Account / Profile Data Retention

No final privacy retention period for account identity, preferences, saved items, inactive accounts, or deactivated accounts is established in this draft.

[COUNSEL TO CONFIRM: retention period after account closure/deletion request]

**CURRENT PRODUCT CAPABILITY notes:**

- No automatic account-purge job for inactive accounts was found.
- No consumer deactivation workflow was found.
- No coded privacy retention/deletion schedule for durable account stores was found.

Do not state automatic purge behavior unless and until implemented and approved.

---

## 12. Authentication / Security Data Retention

### CURRENT PRODUCT CAPABILITY (technical handling)

| Data | Current technical handling |
|------|----------------------------|
| Password hashes | Stored for authentication; not returned in ordinary public account views |
| Session token hashes | Stored; raw bearer tokens are not stored |
| Auth audit events | May be recorded in-process and/or in operational persistence |
| Rate-limit / security signals | In-process / operational controls |
| Password-reset / email-verification records | Created with technical expiries where service paths exist |

This draft does **not** claim that active sessions survive a future account-deletion workflow. No account-deletion workflow currently exists against which that claim could be verified.

[COUNSEL TO CONFIRM: security/audit retention periods and deletion exceptions]

---

## 13. Logs

Cross-check with the Data Processing Product Behavior Spec and Privacy Policy counsel drafts:

- structured HTTP request logs may include method, path, status, duration, request id, and client IP where enabled;
- auth/security audit events may include identifiers and, on some paths, normalized email;
- application logging is operational and may not be instantly erasable from all systems;
- infra-intended CloudWatch retention defaults (staging/production) are **not** a finalized privacy retention schedule.

[COUNSEL TO CONFIRM: access/security/application log retention and deletion schedule]

This draft does **not** imply that every log entry can necessarily be instantly erased from all systems upon request.

---

## 14. Affiliate Attribution Data

Cross-check with the Affiliate & Advertising Disclosure counsel draft.

### CURRENT PRODUCT CAPABILITY

- Affiliate link/click/attribution foundation may include demo/fixture click and attribution records.
- Click records may include optional user/session identifiers and related metadata.
- Live affiliate-provider tracking, real network IDs, live conversion postbacks, and production payout systems are **not** claimed as currently live.
- Merchant `cookie_days` values are registry/attribution-window metadata, **not** evidence of a coded purge schedule.

[COUNSEL / PROVIDER REVIEW REQUIRED: retention/deletion obligations for affiliate click/attribution data under each approved provider program]

---

## 15. AI / Conversation Data

Cross-check with the AI Recommendation Disclosure counsel draft.

### CURRENT PRODUCT CAPABILITY

- Shopping-assistant conversation memory may use a short in-memory TTL (default on the order of 30 minutes / 1800 seconds) where that path is used.
- Live external AI HTTP may be disabled by default; provider adapters exist.
- Absence of an app-side durable prompt/response store is **not** the same as a complete privacy guarantee across providers, infrastructure logs, or future product changes.

This draft does **not** claim that:

- all AI interactions are retained;
- all AI interactions are deleted immediately; or
- provider retention matches PiqSavi’s technical TTL.

[COUNSEL / PROVIDER REVIEW REQUIRED: retention/deletion treatment for AI requests, responses, provider logs and subprocessors]

---

## 16. Email / Support Records

Distinguish, where applicable:

| Record type | Current posture |
|-------------|-----------------|
| Transactional email delivery records | Live transactional delivery is **not** currently integrated in the application (`NullEmailSender` / mock paths); Sprint 27 is planned / not started |
| Verification / reset request records | Technical request records with expiries may exist; confirm/delivery incomplete |
| Support correspondence | May exist in mailbox systems for support@piqsavi.com |
| Privacy request correspondence | May exist in mailbox systems for privacy@piqsavi.com |

No final retention periods are invented here.

[COUNSEL TO CONFIRM: retention periods for support/privacy correspondence and request records]

---

## 17. Backups

This section is intentionally cautious.

### What repository / infrastructure evidence supports

- Application docs describe configuration backup/restore rehearsal and optional demo `pg_dump` usage; they do **not** establish enterprise disaster-recovery claims.
- Terraform defaults express **intended** RDS backup retention (staging default 7 days; production default ≥30 days) and related production snapshot safeguards.
- These infra defaults are **not** a finalized legal retention schedule and do **not** prove instantaneous deletion of user data from all backup copies.

### What this draft does **not** claim

- exact approved legal backup duration as a public privacy commitment;
- instant deletion from all backups upon request;
- immutable backup deletion guarantees; or
- automatic privacy-driven backup purge jobs for account PII.

Conceptually, deletion from active systems may not necessarily mean immediate physical erasure from all backup copies, if counsel approves that formulation. That concept is **not** finalized legal language in this draft.

[COUNSEL / INFRASTRUCTURE REVIEW REQUIRED: production backup architecture, retention, restore lifecycle and treatment of deletion requests]

---

## 18. Third-Party Providers

Potential relevant providers may include, where implemented or operationally used:

| Provider / category | Relevance to deletion / export / retention |
|---------------------|--------------------------------------------|
| Hosting / cloud (e.g. AWS) | Application data, logs, backups, secrets pathways |
| Email (e.g. Resend — selected/planned; not integrated for live send) | Future transactional email content/addresses |
| Mailbox (Google Workspace / Gmail for support/privacy aliases) | Support/privacy correspondence |
| AI providers (optional adapters; live HTTP off by default) | Possible request/response handling if enabled |
| Merchant / affiliate services | Future / subject to approvals; demo/fixture today |
| Domain (Cloudflare registrar/control) | Domain/ops; not treated as consumer account store |

This draft does **not** imply that every listed provider currently processes personal data for every user, or that each can delete/export on demand today.

[COUNSEL / PROVIDER REVIEW REQUIRED: deletion/export/retention obligations, subprocessors and deletion-verification capabilities for each production third-party provider]

See also the Privacy Policy counsel draft third-party section for related posture.

---

## 19. Legal / Security Exceptions

Potential topics for counsel (not finalized here as a public exception list):

- fraud prevention;
- security and abuse prevention;
- disputes;
- contractual obligations;
- legal claims;
- regulatory requirements;
- accounting / tax obligations (if applicable); and
- law enforcement / legal process.

This draft does **not** state that PiqSavi may retain data indefinitely, and does **not** independently finalize broad exceptions.

[COUNSEL TO CONFIRM: permissible and required deletion/retention exceptions]

---

## 20. Anonymized / Aggregated Data

As part of deletion or retention design, some information may potentially be de-identified or aggregated.

This draft does **not** make a blanket claim that anonymized or aggregated data is outside all privacy laws.

[COUNSEL TO CONFIRM: de-identification/anonymization standards, reversibility, permitted continued use and jurisdiction differences]

---

## 21. Data Export Content (Planning)

### INTERNAL / COUNSEL PLANNING — NOT A CURRENT PRODUCT PROMISE

An eventual export package **may** include categories such as:

- account / profile fields;
- preferences / settings;
- saved items and related account activity;
- recommendation-related account data where applicable; and
- privacy-request history where tracked.

This draft does **not** promise that all categories will be included, or that any export package exists today.

Secrets and sensitive internals should generally **not** be included unless counsel/engineering determines disclosure is appropriate, including for example:

- password hashes;
- session-token hashes;
- internal security signals; and
- proprietary scoring internals.

[COUNSEL TO CONFIRM: required scope of portable/access data]

---

## 22. Export Format

No current self-service export format is implemented.

Future possibilities may include machine-readable formats. This draft does **not** claim that JSON, CSV, ZIP, or any other download format is currently available.

[COUNSEL TO CONFIRM: required export format / portability standard]

---

## 23. Request Timelines

This draft does **not** invent a single global legal deadline.

[COUNSEL TO CONFIRM: Philippines response timeline]

[COUNSEL TO CONFIRM: United States response timeline(s)]

[COUNSEL TO CONFIRM: Singapore response timeline]

[COUNSEL TO CONFIRM: United Kingdom response timeline]

[COUNSEL TO CONFIRM: Canada response timeline]

---

## 24. Request Fees / Excessive Requests

This draft does not invent fees, refusals, extensions, or limits.

[COUNSEL TO CONFIRM: whether fees, refusal, extension or limits may apply to manifestly unfounded/excessive/repetitive requests in each market]

---

## 25. Authorized Agents / Representatives

This draft does not invent an authorized-agent process.

[COUNSEL TO CONFIRM: authorized-agent / parent / guardian / representative request requirements]

---

## 26. Minors

Based on current product implementation reviewed for this draft, PiqSavi does **not** currently publish or enforce a coded minimum-age policy, age gate, date-of-birth collection, or parental-consent flow. Keep consistency with sibling legal drafts.

[COUNSEL TO CONFIRM: deletion/access rights and guardian procedures for minors]

[COUNSEL TO CONFIRM: minimum age, parental-consent rules and child-data restrictions for intended markets]

---

## 27. Future Self-Service Controls (Planning Only)

### PLANNED / FUTURE CAPABILITY — Sprint 28 is Planned / NOT STARTED

Self-service account deletion and automated data export are **not** currently implemented.

Possible future controls **may** include (planning language only; not a UX commitment):

- Delete Account;
- Request Data Export / Download Data;
- privacy request status visibility;
- confirmation / re-authentication steps; and
- a cooling-off / recovery period if legally and operationally appropriate.

This draft does **not** promise these exact UX features, does **not** state that Sprint 28 has started, and does **not** treat roadmap intent as current capability.

[COUNSEL TO CONFIRM: required UX and confirmation safeguards]

---

## 28. INTERNAL Data Retention Schedule

### INTERNAL / COUNSEL REVIEW / NOT PUBLIC RETENTION COMMITMENT

The following table is for counsel and engineering planning. It is **not** a public retention commitment and does **not** approve legal retention periods.

| Data Category | Example Data | System / Location | Current Technical Behavior | Current Technical Expiry | Proposed Legal Retention | Deletion Method | Backup Treatment | Third-Party Dependency | Evidence | Counsel Status |
|---------------|--------------|-------------------|----------------------------|--------------------------|--------------------------|-----------------|------------------|------------------------|----------|----------------|
| Account identity | email, display name, user id, flags | `user_platform.users` / operational persistence | Persisted after register | None as privacy retention | TBD — COUNSEL TO CONFIRM | Account purge NOT FOUND | TBD — COUNSEL / INFRA | Hosting/DB | Fact-spec §3; User entity | OPEN |
| Preferences / settings | budget, currency, country, theme, notification flags | `user_platform.*` | Persisted / updatable | None as privacy retention | TBD — COUNSEL TO CONFIRM | Account-level NOT FOUND | TBD — COUNSEL / INFRA | Hosting/DB | Fact-spec §3.4 | OPEN |
| Saved products / activity | saved products, comparisons, searches, history | `user_platform.*` | Per-item saved-product DELETE exists | None as privacy retention | TBD — COUNSEL TO CONFIRM | Per-item only today | TBD — COUNSEL / INFRA | Hosting/DB | `DELETE .../saved-products/{id}` | OPEN |
| Sessions | session id, token hash, expiry | `user_platform.sessions` | Logout revoke; expiry invalidation | 1h default / 30d remember-me | TBD — COUNSEL TO CONFIRM | Revoke/expiry | TBD — COUNSEL / INFRA | Hosting/DB | AuthService TTLs | OPEN |
| Password-reset records | token hash, expires_at | password-reset store | Create + expiry | ~1 hour | TBD — COUNSEL TO CONFIRM | Expiry / consume paths | TBD — COUNSEL / INFRA | Future email provider | AuthService | OPEN |
| Email-verification records | token hash, expires_at | verification store | Create + expiry | ~1 day | TBD — COUNSEL TO CONFIRM | Expiry / consume paths | TBD — COUNSEL / INFRA | Future email provider | AuthService | OPEN |
| Auth audit / security events | login/logout/rate-limit events | audit buffer / `user_platform.audit_events` | Recorded; no privacy purge job found | None as privacy retention | TBD — COUNSEL TO CONFIRM | NOT FOUND | TBD — COUNSEL / INFRA | Hosting/DB | AuditLogger | OPEN |
| Technical / request logs | IP, path, status, request id | app stdout / intended CloudWatch | Operational logging | Infra intent: staging 14d / prod 30d CW default | TBD — COUNSEL TO CONFIRM | Not instantly erasable from all systems | TBD — COUNSEL / INFRA | AWS / ops | request_logging; TF vars | OPEN |
| Affiliate clicks / attributions | click id, optional user/session ids | affiliate stores | Demo/fixture-oriented persistence | `cookie_days` ≠ purge | TBD — COUNSEL TO CONFIRM | NOT FOUND | TBD — COUNSEL / INFRA | Future affiliate providers | Affiliate entities; Affiliate Disclosure draft | OPEN |
| AI / conversation state | conversation turns (in-memory path) | process memory | TTL cleanup | default 1800s | TBD — COUNSEL TO CONFIRM | TTL / process end | N/A (non-durable path) | AI providers if live HTTP enabled | memory.py; AI Disclosure draft | OPEN |
| Support / privacy correspondence | email content | mailbox systems | Ops receiving at aliases | Unknown / not coded in app | TBD — COUNSEL TO CONFIRM | Mailbox/ops process | Provider/mailbox backups unknown | Google Workspace / Gmail | EXT-17/18 | OPEN |
| Backups | DB snapshots / config export rehearsal | RDS intended backups; config export docs | Infra defaults / rehearsal docs | Staging 7d / prod ≥30d intended RDS default | TBD — COUNSEL TO CONFIRM | Instant backup purge NOT claimed | See §17 | AWS / ops | BACKUP_RESTORE.md; TF vars | OPEN |

---

## 29. INTERNAL Deletion / Export Implementation Gap Table

### INTERNAL / COUNSEL REVIEW / NOT PUBLIC COMMITMENT

| Capability | Current State | Evidence | Required for Launch? | Legal Requirement? | Engineering Dependency | Counsel Decision | Owner | Status |
|------------|---------------|----------|----------------------|--------------------|------------------------|------------------|-------|--------|
| Self-service account deletion | Not implemented | No consumer delete-account endpoint; UserRepository.delete NOT FOUND; Sprint 28 Planned | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Sprint 28 APIs + propagation | OPEN | Legal + privacy eng | OPEN |
| Account deactivation | Field exists; consumer workflow not found | `is_active` checked on login; no deactivate API found | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Product design + API | OPEN | Product + eng | OPEN |
| Data export | Not implemented | No DSAR export endpoint; launch config export is unrelated | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Sprint 28 export API | OPEN | Legal + privacy eng | OPEN |
| Request verification | Not finalized | Manual contact path only | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Ops + product | OPEN | Legal + ops | OPEN |
| Request tracking | Not found as product feature | No privacy-request status system found | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Sprint 28 / ops tooling | OPEN | Ops + eng | OPEN |
| Backup handling for deletion | Not finalized | BACKUP_RESTORE rehearsal; TF intended RDS retention | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Infra + runbooks | OPEN | Infra + counsel | OPEN |
| Provider deletion | Unknown / not claimed | Provider capabilities outside repo | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | DPAs / provider APIs | OPEN | Counsel + ops | OPEN |
| Provider export | Unknown / not claimed | Provider capabilities outside repo | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Provider tooling | OPEN | Counsel + ops | OPEN |
| Retention scheduler | Not found | No privacy retention cron/purge jobs found | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Sprint 28 retention design | OPEN | Eng | OPEN |
| Purge jobs | Not found | No account PII purge jobs found | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Engineering | OPEN | Eng | OPEN |
| Audit evidence of deletion/export | Not found as complete privacy audit package | Auth audit exists; deletion/export audit package not found | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Sprint 28 evidence | OPEN | Eng + counsel | OPEN |
| Privacy request SLA | Not finalized | Mailbox provisioned; no coded SLA | UNKNOWN / COUNSEL TO CONFIRM | UNKNOWN / COUNSEL TO CONFIRM | Ops process | OPEN | Legal + ops | OPEN |

---

## 30. Contact

**Privacy:** privacy@piqsavi.com

**Support:** support@piqsavi.com

**Operator:**
[COUNSEL TO CONFIRM: legal operator/entity name]

**Operator / legal address:**
[COUNSEL TO CONFIRM: legal operator name and address disclosure]

This draft does **not** include a founder home address.

---

## 31. Relationship to Other Documents

| Document | Relationship |
|----------|--------------|
| Privacy Policy (counsel draft) | Broader personal-data processing; deletion/export limitations aligned |
| Terms of Service (counsel draft) | Account terms; deletion/export current limitations aligned |
| Data Processing Product Behavior Spec (counsel draft) | Factual technical basis |
| Affiliate & Advertising Disclosure (counsel draft) | Affiliate/attribution posture |
| AI Recommendation Disclosure (counsel draft) | AI / conversation retention posture |
| Cookie & Tracking Notice (counsel draft) | Cookies/storage/tracking; Bearer auth; no invented cookies |
| Sprint 28 planning | Planned privacy/legal/consent/deletion work — **NOT STARTED** |

---

## 32. Explicit Non-Claims

This counsel draft does **NOT** claim:

- self-service account deletion currently exists;
- automated export currently exists;
- a final retention schedule exists or is approved;
- all data can be deleted instantly;
- all backups are instantly purged;
- all third parties delete on demand today;
- all user data is portable today;
- a global request deadline;
- a fixed deletion timeline as a legal commitment;
- a fixed export timeline as a legal commitment;
- a fixed log-retention period as an approved privacy policy;
- a fixed affiliate retention period as an approved privacy policy;
- a fixed AI-provider retention period;
- a final legal exception list;
- Sprint 28 has started;
- Sprint 26 is closed;
- Sprint 27 has started;
- EXT status advancement (including EXT-01…05, EXT-20/21, EXT-22);
- EXT-19 written legal approval; or
- that this document is published or legally sufficient.

---

# INTERNAL COUNSEL REVIEW NOTES — REMOVE BEFORE PUBLICATION

This appendix is **internal only**. It must not appear in any future public policy.

## Unresolved issues (questions / placeholders only — no privileged advice)

1. **Operator / entity** — exact legal operator/entity name and public disclosure form.
   Placeholder: `[COUNSEL TO CONFIRM: legal operator/entity name]`

2. **Effective date** — publication timing after counsel approval.
   Placeholder: `[COUNSEL TO CONFIRM]`

3. **Deletion right scope** — what must be deleted vs dissociated vs retained.
   Placeholder: `[COUNSEL TO CONFIRM: legally required deletion workflow, identity verification, response timing and exceptions by launch market]`

4. **Export / access right scope** — required portable/access content.
   Placeholder: `[COUNSEL TO CONFIRM: required scope of portable/access data]`

5. **Identity verification** — standard for requesters.
   Placeholder: `[COUNSEL TO CONFIRM: identity-verification standard, authorized-agent handling and anti-fraud safeguards]`

6. **Authorized agents** — agent / representative handling.
   Placeholder: `[COUNSEL TO CONFIRM: authorized-agent / parent / guardian / representative request requirements]`

7. **Response timelines** — by market.
   Placeholders: PH / US / SG / UK / CA response timeline confirmations above.

8. **Request fees / extensions / refusals** — whether permitted and when.
   Placeholder: `[COUNSEL TO CONFIRM: whether fees, refusal, extension or limits may apply to manifestly unfounded/excessive/repetitive requests in each market]`

9. **Account closure vs deletion** — legal and product semantics.
   Placeholder: `[COUNSEL TO CONFIRM]`

10. **Deactivation semantics** — whether deactivation is required, optional, or insufficient.
    Placeholder: `[COUNSEL TO CONFIRM]`

11. **Saved-item deletion** — whether per-item delete is adequate for any interim compliance posture.
    Placeholder: `[COUNSEL TO CONFIRM]`

12. **Account data retention** — period after closure/deletion request.
    Placeholder: `[COUNSEL TO CONFIRM: retention period after account closure/deletion request]`

13. **Inactive-account retention** — whether automatic purge is required.
    Placeholder: `[COUNSEL TO CONFIRM]`

14. **Auth / security retention** — audit, hashes, security signals.
    Placeholder: `[COUNSEL TO CONFIRM: security/audit retention periods and deletion exceptions]`

15. **Log retention** — access/security/application logs.
    Placeholder: `[COUNSEL TO CONFIRM: access/security/application log retention and deletion schedule]`

16. **Affiliate attribution retention** — under each approved provider program.
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: retention/deletion obligations for affiliate click/attribution data under each approved provider program]`

17. **AI / conversation retention** — app TTL vs provider logs.
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: retention/deletion treatment for AI requests, responses, provider logs and subprocessors]`

18. **Support / privacy request retention** — correspondence and tickets.
    Placeholder: `[COUNSEL TO CONFIRM: retention periods for support/privacy correspondence and request records]`

19. **Email records** — transactional / verification / reset once Sprint 27 integrates delivery.
    Placeholder: `[COUNSEL TO CONFIRM]`

20. **Provider deletion obligations** — AWS, email, AI, affiliate, mailbox.
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: deletion/export/retention obligations, subprocessors and deletion-verification capabilities for each production third-party provider]`

21. **Backup retention** — production architecture and legal description.
    Placeholder: `[COUNSEL / INFRASTRUCTURE REVIEW REQUIRED: production backup architecture, retention, restore lifecycle and treatment of deletion requests]`

22. **Backup deletion treatment** — whether delayed erasure from backups is permissible and how to describe it.
    Placeholder: `[COUNSEL / INFRASTRUCTURE REVIEW REQUIRED: production backup architecture, retention, restore lifecycle and treatment of deletion requests]`

23. **Fraud / security exceptions** — permissible retention.
    Placeholder: `[COUNSEL TO CONFIRM: permissible and required deletion/retention exceptions]`

24. **Legal / regulatory exceptions** — claims, process, regulatory holds.
    Placeholder: `[COUNSEL TO CONFIRM: permissible and required deletion/retention exceptions]`

25. **Tax / accounting obligations** — if any apply to affiliate/revenue records later.
    Placeholder: `[COUNSEL TO CONFIRM]`

26. **Anonymization / de-identification** — standards, reversibility, continued use and jurisdiction differences.
    Placeholder: `[COUNSEL TO CONFIRM: de-identification/anonymization standards, reversibility, permitted continued use and jurisdiction differences]`

27. **Export content** — required scope; exclusion of secrets/security internals.
    Placeholder: `[COUNSEL TO CONFIRM: required scope of portable/access data]`

28. **Export format** — portability standard.
    Placeholder: `[COUNSEL TO CONFIRM: required export format / portability standard]`

29. **Minors / guardians** — age floor and guardian procedures.
    Placeholders: `[COUNSEL TO CONFIRM: deletion/access rights and guardian procedures for minors]`; `[COUNSEL TO CONFIRM: minimum age, parental-consent rules and child-data restrictions for intended markets]`

30. **Philippines requirements** — deletion/export/retention/response rules.
    Placeholder: `[COUNSEL TO CONFIRM: Philippines response timeline]` (+ substantive PH rules)

31. **United States requirements** — federal/state applicability as relevant.
    Placeholder: `[COUNSEL TO CONFIRM: United States response timeline(s)]`

32. **Singapore requirements**.
    Placeholder: `[COUNSEL TO CONFIRM: Singapore response timeline]`

33. **United Kingdom requirements**.
    Placeholder: `[COUNSEL TO CONFIRM: United Kingdom response timeline]`

34. **Canada requirements**.
    Placeholder: `[COUNSEL TO CONFIRM: Canada response timeline]`

35. **Sprint 28 implementation requirements** — minimum product controls before launch claims.
    Placeholder: `[COUNSEL TO CONFIRM: required UX and confirmation safeguards]`

36. **Audit / evidence requirements** — what proof of deletion/export completion must be retained.
    Placeholder: `[COUNSEL TO CONFIRM]`

37. **Deletion completion confirmation** — user-facing confirmation standards.
    Placeholder: `[COUNSEL TO CONFIRM]`

38. **Provider deletion verification** — how to confirm third-party erasure.
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: deletion/export/retention obligations, subprocessors and deletion-verification capabilities for each production third-party provider]`

39. **Retention schedule approval** — formal approval of the INTERNAL schedule above.
    Placeholder: `[COUNSEL TO CONFIRM: lawful retention purposes and required retention periods by category / market]`

40. **Final public wording** — what may be published after EXT-20/21 and counsel approval.
    Placeholder: `[COUNSEL TO CONFIRM]`

## Explicit non-claims for this drafting exercise

- Not legal advice
- Not legally approved
- Not published
- Not evidence of EXT-19 written approval
- Not evidence of EXT-20/21 publication
- Not evidence of Sprint 28 start/completion
- Does not close Sprint 26
- Does not start Sprint 27
- Does not start Sprint 28
- Does not modify EXT statuses
- Does not invent self-service deletion/export product capabilities
- Does not invent a final retention schedule
- Does not invent global deadlines, fixed fees, or blanket “keep forever” exceptions

## Drafting provenance

| Item | Value |
|------|-------|
| Public brand | PiqSavi |
| Public tagline | Your AI Personal Shopper |
| Public feature | PiqScore |
| Primary fact sources | Sibling counsel drafts under `docs/legal/` + repository implementation evidence |
| Drafting branch | `docs/piqsavi-deletion-export-retention-policy-counsel-draft` |
| Authoritative main at drafting | `e4c91ac88fc42c5d42779c9deca2fea698077a66` |
| Sprint 26 | OPEN (unchanged) |
| Sprint 27 | NOT STARTED (unchanged) |
| Sprint 28 | Planned / NOT STARTED (unchanged) |
| EXT-01…05 | `not_started` (unchanged) |
| EXT-19 | `applied` (engagement; written approval not claimed) |
| EXT-20/21/22 | `not_started` (unchanged) |
| Counsel consultation (schedule evidence) | 2026-08-19 10:00 AM Philippines local time |

**End of PiqSavi Account Deletion, Data Export & Retention Policy — Counsel Draft.**
