# Security incident-response runbook

**Status:** Process prepared. Production incident response is not operational.

**Package date:** 2026-10-14

**Owner:** Sprint 40 security-readiness package

This runbook is the security-response process. This runbook does not configure paging. Sprint 42 owns production monitoring, alerts, paging, paging acknowledgement, production incident operations, restore rehearsal, and disaster-recovery operational evidence. Sprint 44 owns final rehearsal, final evidence review, the final security, legal, and operations approval package, and launch go/no-go approval.

No PagerDuty service, Slack channel, phone number, or security mailbox is named here. Actual paging and contact destinations are Sprint 42 and Sprint 44 configuration evidence. Until those destinations exist, the Incident Commander records who was told, by which role, and when, in the incident notes.

Related documents:

- Penetration-test readiness: [`../security/PENETRATION_TEST_READINESS.md`](../security/PENETRATION_TEST_READINESS.md)
- Vulnerability response: [`../security/VULNERABILITY_RESPONSE.md`](../security/VULNERABILITY_RESPONSE.md)
- Sprint 44 draft: [`../roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md`](../roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md)
- Request logging: [`PRODUCTION_LOGGING.md`](PRODUCTION_LOGGING.md)
- Identity email: [`EMAIL_OUTAGE.md`](EMAIL_OUTAGE.md)
- Staging rollback: [`STAGING_ROLLBACK.md`](STAGING_ROLLBACK.md)
- Day-2 cues: [`../OPERATIONS.md`](../OPERATIONS.md)

Current roadmap links:

- [`../roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)
- [`../roadmap/sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md`](../roadmap/sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md)
- [`../roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md`](../roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md)
- [`../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)

Sprint 40 stays Planned. It is not ENGINEERING COMPLETE, not PRODUCTION PROVEN, and not LAUNCH READY. Closing an incident note does not close Sprint 40.

## Incident categories

Use the category that best matches the first credible report. One incident can carry more than one category.

| Category | Examples that belong here |
|----------|---------------------------|
| Account compromise or credential stuffing | Repeated failed logins, a lock that is not containing guesses, or a report that an account password is in another person's hands. |
| Session or cookie compromise | A bearer token or `piqsavi_decision_owner` cookie used from an unexpected client. A copied owner cookie remains valid until its seven-day expiry because there is no server-side guest revocation list. |
| Authorization isolation failure | One owner can read, continue, or mutate another owner's conversation, decision, or snapshot. |
| Possible data disclosure | A response, log, export, or analytics row contains another person's data or a conversation body that the surface must not return. |
| Secret or key exposure | `APP_SECRET_KEY`, `DATABASE_URL`, `RESEND_API_KEY`, a GHCR pull token, or a provider key appears in a log, ticket, repository, or client response. |
| Malicious dependency or supply-chain concern | A pip-audit advisory, a suspicious package release, or an image that does not match the published digest. Container vulnerability scanning and signed provenance are not current gates. |
| SSRF or unexpected outbound traffic | The application fetches a loopback, link-local, metadata, or other unapproved host. Shopify and live research are required to stay disabled. |
| Injection or code execution concern | SQL, command, template, or browser-script execution from untrusted input. |
| Abuse or automated traffic | Volume that exhausts a limiter, registration spam, or Ask traffic that retries past the idempotency ledger. |
| Ranking-integrity or merchant manipulation | A merchant, affiliate, or client parameter changes organic DealScore or recommendation ranking. Affiliate activation stays off. |
| Compromised admin or operator credentials | A demo launcher token, merchant demo token, GitHub credential, AWS role, or Secrets Manager access used outside its intended operator. Production merchant identity is not implemented. |

Do not relabel existing Sprint 40 findings with these severities. The historical HIGH "in-process rate limits only" and the historical MEDIUM findings keep the classes in the latest Sprint 40 reconciliation.

## Severity model

Assign severity from the current impact. Reassess when containment changes the impact.

| Severity | Impact |
|----------|--------|
| SEV-1 Critical | Confirmed disclosure of secrets, session credentials, or another person's account or decision data. Confirmed code execution. An operator credential is in active unauthorized use. A live provider key can be used now. |
| SEV-2 High | A reachable authorization isolation failure without a confirmed disclosure yet. Credential stuffing that the durable lock is not containing. A secret committed where it can be read. Unexpected outbound traffic to a private or metadata address. |
| SEV-3 Medium | A control weakness without confirmed data access. Examples: a missing security header on one enabled surface, an error that reveals whether an account exists on a flow that is supposed to be uniform, or automated traffic that the shared limiter is still containing. |
| SEV-4 Low | A report with no reachable path on the current disabled-provider posture, a documentation gap, or scanner noise that does not identify a vulnerable package in the locked closure. |

These labels are for incidents opened under this runbook. They are not a new score for Sprint 40 R1–R21.

## Roles

| Role | Responsibility in this process |
|------|--------------------------------|
| Incident Commander | Owns the timeline, stop conditions, and the decision to hold a deploy or launch. |
| Security Owner | Owns technical triage, containment choice, and the vulnerability handoff. |
| Engineering Owner | Owns the code, configuration, or secret change. |
| Product/Founder Owner | Owns shopper-facing and partner-facing communication decisions. |
| Privacy/Legal Owner | Owns whether any notification is required. Counsel owns legal deadlines. |
| Operations Owner | Owns environment access, log collection, and the existing deploy or rollback workflow. |

Named people, on-call rotations, and paging routes are Sprint 42 and Sprint 44 evidence. This document has no roster.

## Response phases

### 1. Identify

Record the reporter, the time, the environment (`development`, `staging`, or `production`), the URL or job, and the category. Capture the `X-Request-ID` response header when the reporter has it. The request log stores that id with method, path, status, duration, and client host.

### 2. Triage

Assign a severity from the impact table. Decide whether the report is a security incident, a vulnerability to track under [`../security/VULNERABILITY_RESPONSE.md`](../security/VULNERABILITY_RESPONSE.md), or an operational email or availability issue already covered by [`EMAIL_OUTAGE.md`](EMAIL_OUTAGE.md) or [`../OPERATIONS.md`](../OPERATIONS.md). An incident can follow both this runbook and the vulnerability process.

### 3. Contain

Apply the smallest containment option that stops further exposure. Use the options in the next section. Do not enable Shopify, live research, or affiliate payout while containing an incident.

### 4. Preserve evidence

Follow the evidence section. Do this before rotating a secret when the current logs are the only copy of the request ids, and again after rotation so the timeline shows both states.

### 5. Eradicate and remediate

Remove the exposed credential from use, fix the isolation or injection defect, or disable the flag that gates the affected surface. A code change follows the vulnerability-response lifecycle. This runbook does not deploy by itself.

### 6. Recover

Restore ordinary service only after the containment still holds. Recovery may be a configuration flag returned to its previous value, a new immutable image deployed through the existing workflow, or a rollback through the staging or production workflow that is actually authorized for that environment. Production deploy and rollback evidence remains Sprint 41 work. Sprint 41 is UNSTARTED. A workflow file is not proof that production rollback has been rehearsed.

### 7. Validate

Repeat the smallest check that shows the original path no longer succeeds. For an authorization failure, use two test owners. For a secret exposure, confirm the old secret is rejected and the new secret is not present in the incident notes. For abuse, confirm the limiter or lock still fails closed. Record the commit SHA that was validated.

### 8. Communicate

Use the communications section. Record a decision, including a decision not to notify.

### 9. Post-incident review

The Incident Commander schedules a review with the Security Owner and Engineering Owner. The review states the timeline, the containment, the evidence locations, the residual risk, and whether a vulnerability remains open. It does not mark Sprint 40 ENGINEERING COMPLETE. It does not approve launch.

## Immediate containment options

Use a control that exists today or that a named sprint owns. Do not invent a production kill switch, a paging bridge, or a restore drill.

| Option | What exists now |
|--------|-----------------|
| Disable a feature flag | Settings flags include `ai_shopping_enabled`, `ai_review_enabled`, `community_enabled`, `affiliate_enabled`, `merchant_platform_enabled`, `demo_launcher_enabled`, `rate_limiting_enabled`, and `security_headers_enabled`. Changing one is a configuration change plus a restart or redeploy. It is not an evidenced production console. |
| Disable providers | AI live HTTP defaults off. Leave `AI_SHOPPING_LIVE_HTTP` and the other live-HTTP switches off. `SHOPIFY_LIVE_CALL_PERMITTED` is false in code. Real Shopify calls stay 0. Routing stays 0. |
| Keep Shopify and live research disabled | This is the current fail-closed posture. Do not turn either on to investigate. |
| Disable an affected endpoint | There is no general per-route kill switch. Hold the release, or turn off the Settings flag that already gates that surface. A code change that removes a route ships through the normal review and deploy gates. |
| Rotate application or provider credentials | Hosts read secrets from AWS Secrets Manager. GitHub Actions deploy roles do not read secret values. Rotate through that secret process. Never print `APP_SECRET_KEY`, `DATABASE_URL`, `RESEND_API_KEY`, or a GHCR token. Production secret attach remains Sprint 41. |
| Revoke bearer sessions | `POST /api/v1/auth/logout` revokes the presented bearer. Password reset confirmation and email-change confirmation call `revoke_all_for_user` for that account. There is no operator API in this runbook that revokes every bearer in the database. |
| Clear a compromised device credential | `POST /account/clear-device` deletes the owner cookie on the browser that calls it and requires a trusted `Origin`. A copied cookie cannot be revoked server-side and works until the seven-day expiry. Record that residual when the incident is a copied cookie. |
| Hold deployment or launch | The Incident Commander can stop a staging deploy, a production promotion, and any Sprint 44 or Sprint 45 decision. Launch approval does not exist. |
| Rollback | Staging rollback follows [`STAGING_ROLLBACK.md`](STAGING_ROLLBACK.md) and uses immutable digest authority. Production rollback is the existing `rollback-production.yml` workflow only when an authorized operator runs it. Sprint 41 owns production deploy evidence and is UNSTARTED. This runbook does not execute either workflow. A restore rehearsal does not exist. Sprint 42 owns that drill. |

## Evidence preservation

Record:

- Start time, containment time, and recovery time, with timezone.
- Commit SHA and, when a release exists, the release id and immutable image digest.
- Affected account ids or other opaque ids. Prefer hashes already stored by the product. Do not add a raw email to a new document when an opaque id will do. Security-audit rows may already contain an account email. Leave those rows in the audit store.
- Redacted application logs and, when production logging is in scope, the CloudWatch group named in [`PRODUCTION_LOGGING.md`](PRODUCTION_LOGGING.md). That document does not add alarms or paging.
- `X-Request-ID` values and the matching request-log lines.
- Deploy or rollback evidence JSON when a deployment is part of the incident. Do not fabricate `production_ok` or `rollback_ok`.
- Screenshots of the shopper-visible symptom, cropped so they omit cookies, tokens, and passwords.

Do not copy passwords, bearer tokens, reset tokens, owner cookies, or provider secrets into incident documents, pull requests, or chat. If a secret was already pasted, rotate it and remove the copy from the working notes.

## Communications

Consider each audience. The Privacy/Legal Owner decides external notification. This runbook does not state a legal notification deadline. Legal requirements remain counsel-owned.

| Audience | Consider notification when |
|----------|----------------------------|
| Users | A confirmed disclosure or account compromise affects identifiable accounts. |
| Merchants or partners | Merchant organization data or a merchant credential is involved. Demo merchant tokens are not production merchant identity. |
| Providers | A Resend key, a future Shopify credential, or a future model-provider key may have left the secret store. Do not contact a provider merely to exercise this runbook. |
| Privacy and legal | Any possible personal-data disclosure, before an external notice is sent. |
| Public status | The Product/Founder Owner and the Privacy/Legal Owner both decide that a public statement is warranted. Sprint 42 lists public status-page polish as a non-goal. This runbook does not operate a status page. |

Also tell the Engineering Owner and the Operations Owner for every SEV-1 and SEV-2 incident, using the contact path those roles already have. If no paging destination is configured, write that fact in the timeline. Absence of paging is a Sprint 42 gap. It is not fixed by this runbook.

## Exit criteria

Close the incident only when all of the following are true:

- The category, severity, environment, and commit SHA are recorded.
- Containment is in place, or the report was shown to be unfounded.
- Evidence is stored without secrets.
- The Engineering Owner has a fix in the normal gates, or the Security Owner has written residual risk with an owner and a review date. This runbook does not approve that residual risk. Risk acceptance follows [`../security/VULNERABILITY_RESPONSE.md`](../security/VULNERABILITY_RESPONSE.md) and is not created here.
- Validation was repeated on the contained path.
- Communications decisions are recorded, including decisions not to notify.
- A post-incident review is scheduled or complete.
- The incident record does not mark a Sprint 40 HIGH or MEDIUM finding closed, does not mark R11 PROVEN, and does not mark Sprint 40 ENGINEERING COMPLETE.

An incident stays open while a SEV-1 or SEV-2 containment is still unvalidated.
