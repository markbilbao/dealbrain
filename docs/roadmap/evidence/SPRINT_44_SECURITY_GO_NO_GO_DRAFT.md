# Sprint 44 security go/no-go

**Title:** DRAFT / NOT APPROVED

**Package date:** 2026-10-14

**Decision:** SECURITY GO: NOT DECIDED

This file is a draft template for the security evidence Sprint 44 will review. It is not a Sprint 44 approval. It is not a launch approval. It is not signed. No approver has decided it.

Sprint 40 stays Planned. It is not ENGINEERING COMPLETE, not PRODUCTION PROVEN, and not LAUNCH READY. No penetration test has been executed. IMPLEMENTED-NOT-PROVEN findings are not closed. R11 is IMPLEMENTED-NOT-PROVEN. R11 is not PROVEN.

Current roadmap links:

- [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)
- [`../sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md`](../sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md)
- [`../sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md`](../sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md)
- [`../sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md`](../sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md)
- [`../sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md`](../sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md)
- [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
- Pre-package reconciliation: [`SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md`](SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md)
- This package: [`SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md`](SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md)

Process documents this draft expects Sprint 44 to read:

- [`../../security/PENETRATION_TEST_READINESS.md`](../../security/PENETRATION_TEST_READINESS.md)
- [`../../runbooks/SECURITY_INCIDENT_RESPONSE.md`](../../runbooks/SECURITY_INCIDENT_RESPONSE.md)
- [`../../security/VULNERABILITY_RESPONSE.md`](../../security/VULNERABILITY_RESPONSE.md)

## Repository and release identity

Fill these fields for a future candidate. This draft is not bound to a launch candidate.

| Field | Value |
|-------|-------|
| Candidate commit SHA | NOT SELECTED |
| Immutable image digest | NOT SELECTED |
| Release manifest | NOT SELECTED |
| Environment | NOT SELECTED |
| Starting point for this draft | `e088cba9a87175e387038afb98a1754fe8cc885e` on `main`. That SHA is the package baseline. It is not a launch candidate. |
| CI on the package baseline | CI #493 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38500454900`). Full pytest on that run: 4477 passed, 5 skipped. pip-audit: 71 packages, 0 vulnerabilities, 0 exceptions. |
| Image publication on the package baseline | Build Image #175 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38501162419`). Publication is not a production pull and not a signed attestation. |

## Sprint 40 requirement state

Classes for R1–R10 and R12–R21 are the 2026-10-13 post-message-idempotency reconciliation. R11 moved from MISSING to IMPLEMENTED-NOT-PROVEN when this package landed. No row is PROVEN. Counts after the package: PROVEN 0, IMPLEMENTED-NOT-PROVEN 10 (R1, R3, R5, R7, R9, R11, R14, R17, R18, R20), PARTIAL 11, MISSING 0, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

| ID | Class in this draft | Current evidence | Staging proof | Production proof |
|----|---------------------|------------------|---------------|------------------|
| R1 | IMPLEMENTED-NOT-PROVEN | Owner binding in the reconciliation and Sprint 40.1 / 40.7 tests | None | None |
| R2 | PARTIAL | Session review. Guest revocation and API-logout cookie clearing remain | None on this baseline | None |
| R3 | IMPLEMENTED-NOT-PROVEN | Origin policy and strict default CSP | None | None |
| R4 | PARTIAL | Server-fetch policy implemented. Merchant-host allowlist absent | None | None |
| R5 | IMPLEMENTED-NOT-PROVEN | Request-log redaction and analytics forbid-list | None | None |
| R6 | PARTIAL | Secret scan and pip-audit present. SAST, container scanning, and IaC security scanning absent | CI secret scan and pip-audit only | None |
| R7 | IMPLEMENTED-NOT-PROVEN | Immutable tag, digest, and release manifest. Signed provenance is outside the Sprint 40 closure bar | Build Image publication only | None |
| R8 | PARTIAL | Shared SQL limiter and login lock. Bot challenge and click-fraud scoring absent. Affiliate activation stays off | None | None |
| R9 | IMPLEMENTED-NOT-PROVEN | Durable failed-login lock | None | None |
| R10 | PARTIAL | Six prompt-injection markers add a warning. Structural isolation is absent. Providers stay off | None | None |
| R11 | IMPLEMENTED-NOT-PROVEN | This readiness package. R11 is not PROVEN | Use, review, or rehearsal not recorded | None |
| R12 | PARTIAL | Closure gate. HIGH and MEDIUM rows below are not closed | None | None |
| R13 | PARTIAL | Decision contexts require an owner. Anonymous non-decision `create(owner=None)` remains the Sprint 40.1 contract | None | None |
| R14 | IMPLEMENTED-NOT-PROVEN | Body ids are not authority | None | None |
| R15 | PARTIAL | Product-definition conflict between guest rebind and canonical snapshot immutability | None | None |
| R16 | PARTIAL | Origin policy exists. Per-session rate-limit bucket is absent | None | None |
| R17 | IMPLEMENTED-NOT-PROVEN | Shopping-assistant `Idempotency-Key` ledger | None | None |
| R18 | IMPLEMENTED-NOT-PROVEN | Conversation bodies and session identifiers stay out of routine logs and analytics | None | None |
| R19 | PARTIAL | Same prompt and encoding gaps as R10 and R4, plus cost controls that are not a live-research budget | None | None |
| R20 | IMPLEMENTED-NOT-PROVEN | Coverage review in the reconciliation. Vulnerability response is now the R11 document. Sprint 44 has not accepted the review | None | None |
| R21 | PARTIAL | Same closure gate as R12, with the Sprint 45 deadline | None | None |

## HIGH and launch-blocking MEDIUM findings

No finding in this table is closed because the readiness package exists. No risk acceptance is recorded. Do not treat IMPLEMENTED-NOT-PROVEN as a final disposition.

| Finding | Severity | Status | Implementation evidence | Staging proof | Production proof | Risk acceptance | Final disposition |
|---------|----------|--------|-------------------------|---------------|------------------|-----------------|-------------------|
| In-process rate limits only | HIGH | IMPLEMENTED-NOT-PROVEN | [`SPRINT_40_3_DISTRIBUTED_RATE_LIMIT_2026-10-09.md`](SPRINT_40_3_DISTRIBUTED_RATE_LIMIT_2026-10-09.md) | None. Abuse controls have not been exercised | None | None | Open |
| CSRF not enforced | MEDIUM | IMPLEMENTED-NOT-PROVEN | Origin enforcement for covered cookie mutations. [`SPRINT_40_4_COOKIE_ORIGIN_POLICY_2026-10-10.md`](SPRINT_40_4_COOKIE_ORIGIN_POLICY_2026-10-10.md) | None | None | None | Open |
| CSP `'unsafe-inline'` | MEDIUM | IMPLEMENTED-NOT-PROVEN | Default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. [`SPRINT_40_6_CSP_HARDENING_2026-10-10.md`](SPRINT_40_6_CSP_HARDENING_2026-10-10.md) | None | None | None | Open |
| No Dependabot/CodeQL/Trivy/pip-audit | MEDIUM, historical | CLOSED BY IMPLEMENTATION for the dependency class. SAST, container scanning, and IaC security scanning remain open | [`SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md`](SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md). pip-audit 2.10.1. Empty exception list | CI #493 pip-audit only. That is not SAST, container scanning, or IaC security scanning | None | None | Dependency class implemented. Other scanner classes open |
| URL validation / SSRF hardening incomplete | MEDIUM | IMPLEMENTED-NOT-PROVEN | [`SPRINT_40_5_URL_TRUST_2026-10-10.md`](SPRINT_40_5_URL_TRUST_2026-10-10.md) | None | None | None | Open |

Sprint 41 still owns the production-isolation and production OIDC/SSM HIGHs. Sprint 42 still owns the CloudWatch and security-paging HIGH. Those findings are not Sprint 40 engineering and are not closed here.

## Required security proof

Sprint 44 fills the proof columns. This draft records the current gap.

| Proof area | Repository state on this draft | Still required before a security go |
|------------|--------------------------------|-------------------------------------|
| AuthN/AuthZ | Implemented in repository tests. R1 is IMPLEMENTED-NOT-PROVEN | Staging exercise |
| Owner binding | Sprint 40.7. R14 is IMPLEMENTED-NOT-PROVEN | Staging exercise |
| Session security | R2 is PARTIAL. Copied owner cookie works until expiry | Guest revocation decision, plus staging |
| Origin/CSP | R3 is IMPLEMENTED-NOT-PROVEN | Staging exercise of the default CSP and the origin policy |
| URL/SSRF | Server-fetch policy implemented. Merchant-host allowlist absent | Staging exercise. Allowlist remains a product host list |
| Rate limiting | Shared SQL limiter in staging and production configuration | Staging abuse exercise |
| Failed-login lock | R9 is IMPLEMENTED-NOT-PROVEN | Staging exercise |
| Message idempotency | R17 is IMPLEMENTED-NOT-PROVEN | Staging exercise of a retried submission |
| Logging/redaction | R5 and R18 are IMPLEMENTED-NOT-PROVEN | Staging log sample |
| Dependency scan | pip-audit gate present and clean on CI #493 | Repeat on the launch candidate SHA |
| Other scanner classes | SAST absent. Container vulnerability scanning absent. IaC security scanning absent | One class at a time, in later Sprint 40 work. Not installed by this draft |
| Abuse controls | Limiter and login lock exist. Bot challenge absent. Affiliate activation stays off | Staging exercise. Do not enable affiliate payout to create proof |
| Prompt/content boundary | R10 and R19 are PARTIAL. Providers stay off | Isolation work before any AI or live-research flag is enabled |
| Security-readiness docs | Checklist, incident runbook, vulnerability process, and this draft exist | Review during Sprint 44. Presence is not approval |
| Penetration-test evidence | Checklist is READY TO TEST. No penetration test has been executed | An authorized test, or an explicit later decision that the test remains outstanding |
| Unresolved findings | HIGH and MEDIUM rows above. R6, R12, R15, R16, R21, and prompt isolation | Disposition for each open row |

## Dependencies on later sprints

| Sprint | What Sprint 44 still needs from it | Current state |
|--------|-------------------------------------|---------------|
| Sprint 41 | Production environment, deploy, rollback, DNS, TLS, secrets, IAM, and image-pull evidence for the candidate | UNSTARTED. This draft does not start Sprint 41 |
| Sprint 42 | Monitoring, alerting, paging, paging acknowledgement, backup and restore rehearsal, and operational incident evidence | Planned. The Sprint 40 security runbook does not supply paging or a restore drill |
| Sprint 44 | Final rehearsal, final evidence review, and the security, legal, and operations approval package | This file is the security draft only. It is DRAFT / NOT APPROVED |
| Sprint 45 | Activation of the controlled public beta after approval | Not started by this draft. Routing stays 0. Shopify stays disabled. Real Shopify calls stay 0. Affiliate activation stays off. Live research stays off |

## Decision

SECURITY GO: NOT DECIDED

| Field | Value |
|-------|-------|
| Approver role | NOT NAMED. Sprint 44 assigns the security approver. This draft does not name a person. |
| Decision date | NOT DECIDED |
| Candidate SHA | NOT SELECTED |
| Candidate image digest | NOT SELECTED |
| Open exceptions | The open HIGH, the open MEDIUM rows, the absent scanner classes, R11 not PROVEN, no penetration-test execution, no paging evidence, and no restore drill. |
| Risk acceptances | None. This draft does not create or approve a risk acceptance. |

A future decision uses one of these words only after Sprint 44 records it: GO, CONDITIONAL GO, or NO-GO. This file does not select one of those outcomes.
