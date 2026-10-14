# Sprint 40 security-readiness package — 2026-10-14

**Slice:** The Sprint 40 security-readiness package: a penetration-test readiness checklist, a security incident-response runbook, a vulnerability-response process, and a Sprint 44 security go/no-go draft.

This record does not name the slice Sprint 40.8. It implements the slice selected by [`SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md`](SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md). It does not select the next engineering slice.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `e088cba9a87175e387038afb98a1754fe8cc885e`

**Post-merge evidence on that SHA:** CI #493 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38500454900`). Full pytest on that run: 4477 passed, 5 skipped. The pip-audit gate on that run reported 71 packages, 0 vulnerabilities, 0 exceptions. Build Image #175 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38501162419`). Those runs are publication and test evidence for the merged tree this package started from. They are not a penetration test, a staging abuse exercise, a signed provenance attestation, or a security go/no-go.

No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Affiliate activation stays off. Live research stays off. No provider or public-market activation was changed. Runtime application code is unchanged.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED.

## Files created

| File | Why this location |
|------|-------------------|
| [`../../security/PENETRATION_TEST_READINESS.md`](../../security/PENETRATION_TEST_READINESS.md) | The repository had no penetration-test checklist. `docs/security/` keeps the checklist beside the vulnerability process and leaves historical `docs/SECURITY.md` intact. |
| [`../../runbooks/SECURITY_INCIDENT_RESPONSE.md`](../../runbooks/SECURITY_INCIDENT_RESPONSE.md) | Security response sits with the other operator runbooks. It is not the Sprint 42 paging runbook. |
| [`../../security/VULNERABILITY_RESPONSE.md`](../../security/VULNERABILITY_RESPONSE.md) | The vulnerability lifecycle is process evidence, not a scanner workflow. |
| [`SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md`](SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md) | Sprint 44 consumes roadmap evidence. The file is a draft template. The Sprint 44 sprint definition is unchanged. |

## Files updated

Additive notes only:

- [`../../SECURITY.md`](../../SECURITY.md)
- [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)
- [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
- [`../GAP_INVENTORY.md`](../GAP_INVENTORY.md)
- [`../sprints/README.md`](../sprints/README.md)

Historical audit sections were not rewritten. The 2026-10-13 reconciliation still records R11 as MISSING, because that was the class before this package.

## Existing docs reviewed

- `docs/SECURITY.md`
- `docs/SECURITY_MODEL.md`
- `docs/MERCHANT_SECURITY.md`
- `docs/OPERATIONS.md`
- `docs/runbooks/PRODUCTION_LOGGING.md`
- `docs/runbooks/EMAIL_OUTAGE.md`
- `docs/runbooks/STAGING_ROLLBACK.md`
- `docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`
- `docs/roadmap/sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md`
- `docs/roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md`
- `docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`
- `docs/roadmap/GAP_INVENTORY.md`
- `docs/roadmap/evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md`

`docs/SECURITY_MODEL.md` remains the Sprint 17 model. Where its in-memory and demo-token caveats differ from later merged controls, this package follows the 2026-10-13 reconciliation and the current route behavior. The Sprint 17 document was not rewritten.

## R11

| | Class |
|--|-------|
| Before this package | MISSING |
| After this package | IMPLEMENTED-NOT-PROVEN |

R11 is not PROVEN. The four documents exist and link to each other. Proof still depends on use, review, or rehearsal where a later gate requires it. No penetration test has been executed. The incident runbook has not been rehearsed. The vulnerability process has not closed a finding. The Sprint 44 draft is DRAFT / NOT APPROVED. SECURITY GO: NOT DECIDED.

Other Included rows keep the classes from the 2026-10-13 reconciliation. R20 stays IMPLEMENTED-NOT-PROVEN. The vulnerability-response topic now has a document, and Sprint 44 has not accepted the coverage review. This package does not reclassify R20.

Counts after this package: PROVEN 0, IMPLEMENTED-NOT-PROVEN 10 (R1, R3, R5, R7, R9, R11, R14, R17, R18, R20), PARTIAL 11, MISSING 0, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0. No Included requirement is PROVEN.

## Boundaries

Sprint 42 still owns production monitoring, alerts, paging, paging acknowledgement evidence, production incident operations, restore rehearsal, and disaster-recovery operational evidence. This runbook does not configure paging and does not claim a restore drill exists.

Sprint 44 still owns final rehearsal, final evidence review, the final security, legal, and operations approval package, and launch go/no-go approval. The draft aggregates the evidence that review will need. It does not grant approval.

Sprint 41 still owns production environment and deploy evidence and stays UNSTARTED.

Sprint 45 activation is not started.

## What remains unproven

- R11 use, review, and rehearsal.
- Staging proof for the implemented authorization, origin, CSP, URL-trust, rate-limit, login-lock, idempotency, and redaction controls.
- The Sprint 40 HIGH "In-process rate limits only" stays IMPLEMENTED-NOT-PROVEN.
- The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs stay IMPLEMENTED-NOT-PROVEN.
- R6 still lacks SAST, container vulnerability scanning, and IaC security scanning.
- R10 and R19 still lack structural prompt and content isolation. Providers stay off.
- R16 still lacks a per-session rate-limit bucket.
- R15 remains a product-definition conflict between guest rebind and canonical snapshot immutability.
- R12 and R21 remain closure gates.
- No risk acceptance is recorded.
- No launch approval exists.

A later reconciliation chooses the next blocker. This record does not select one.

## What this package did not do

- No deploy.
- No Shopify call.
- No provider, routing, or public-market activation.
- No runtime security control.
- No scanner installation.
- No claim that a penetration test was executed, that vulnerabilities were independently tested, that production incident response is operational, that paging exists, or that a restore drill exists.
