# EARLY ACCESS — PRE-PRODUCTION READINESS REPORT

**Date:** 2026-08-18

**Audited release:** `a1879a2c699d9c00b23a75091391af494fd43e0d`

**Environment:** staging only

**Production status:** HOLD — no production resources, secrets, DNS, TLS,
workflow, or deployment were created or changed.

## A. Visual readiness

- PASS on the audited staging release against the locked 1440 desktop and 390
  mobile masters, modal/state masters, approved logo/hero asset hashes, and
  responsive interpolation specification.
- Measured at 1440, 1280, 1024, 768, 414, 390, and 375 CSS px. Page frame,
  header, integrated hero, image focal point, How It Works, Trust, footer,
  modal geometry, mobile full-page signup, and hamburger remain within the
  locked system with no redesign.
- The branch changes one proven accessibility detail only: loading-button blue
  is darkened without changing geometry, copy, or layout.

## B. Functional readiness

- PASS on staging: required full name/email/country validation; optional blank
  shopping interest; loading state; successful synthetic signup; normalized
  duplicate response; Back to PiqSavi; Close; signup logo home navigation; and
  mobile form scrolling/focus under a reduced viewport.
- Synthetic staging records used: `QA.Readiness.A1879A2+Normalized@Example.com`
  and `qa-rate-limit@example.com`. These are reserved-domain QA records, not
  real users.
- Duplicate response is distinct and exact: “You’re already on the Early
  Access list.”
- Double-submit protection is synchronous (`disabled` + `aria-busy=true`) and
  regression-covered. Loading was observed live before the response resolved.
- Generic technical-error and Try Again behavior are source/test verified. A
  destructive database/network failure was not injected into staging.

## C. Responsive readiness

- PASS: 1440/1280 use desktop navigation and three columns.
- PASS: 1024 uses desktop navigation and two columns.
- PASS: 768 and below use hamburger and stacked How/Trust layouts, as required
  by the final correction sheet.
- PASS: no horizontal overflow at any requested width; no clipped copy or
  breakpoint layout jump observed.
- PASS: mobile site and signup logos measure 108 × 72 CSS px; close and
  hamburger targets measure 44 × 44 CSS px.

## D. Accessibility readiness

- PASS: labels and `aria-describedby` error associations; polite live errors;
  status live regions for success/duplicate/error; keyboard navigation;
  visible focus; desktop modal focus trap; Escape close; and focus restoration.
- PASS: mobile form remains scrollable with the focused input visible in a
  390 × 500 reduced viewport; prior real-iPhone staging QA was also accepted by
  the founder.
- FIXED ON THIS BRANCH: loading text contrast was 2.53:1. The color-only change
  raises it to 4.84:1. Primary button text remains 5.12:1; muted text 5.41:1;
  eyebrow text 4.51:1. Status icons exceed the 3:1 non-text threshold and are
  accompanied by text.

## E. Security readiness

- PASS for staging: server validation and length bounds, lower/trim email
  normalization, database uniqueness, generic error envelopes, no stack trace,
  request-body/PII omission from logs, CSP, frame denial, content sniffing
  protection, restrictive referrer/permissions policies, and private encrypted
  RDS.
- PASS: registration bucket is 5/min/IP; first-party event bucket is 20/min/IP;
  direct bounded probes received 429 with `Retry-After`.
- PASS: hostile-origin preflight was rejected and did not receive an
  `Access-Control-Allow-Origin` grant. The JSON endpoint has no cookie-backed
  authentication state; conventional CSRF tokens are therefore not applicable.
  Cross-origin HTML form encoding is rejected by the JSON schema.
- Production blocker by design: the current limiter explicitly documents
  itself as in-process and not a production WAF/CDN. Public launch needs a
  shared/edge abuse control proven at production concurrency.
- Staging is HTTP-only; its HSTS response is ineffective over HTTP. This is
  accepted only while staging remains staging. Production must be HTTPS-only.

## F. Analytics readiness

- WORKING: page view (`early_access_page_view`); CTA click; form started; form
  submitted; How It Works viewed; signup success; duplicate; and signup error.
  All four browser event endpoint names returned 204 on staging; lifecycle
  outcomes are emitted server-side.
- PRESERVED WITH REGISTRATION: `utm_source`, `utm_medium`, `utm_campaign`,
  `utm_content`, `utm_term`, referrer, coarse source, and timestamps.
- GAP: device information is not stored. Adding it requires a privacy-minimized
  definition and legal/data-retention decision before changing the event model.
- GAP: registration source is currently `early_access_landing`; header-vs-hero
  CTA source exists in the event log but is not joined to the registration row.
- GAP: no `/dealbrain/staging` CloudWatch log group was present. Event evidence
  is application/container logging, not a durable analytics store. A direct
  host log inspection was not performed because the audit workstation lacks
  the Session Manager plugin. Centralized privacy-safe logs are a production
  cutover requirement.

## G. Staging deployment readiness

- PASS: CI run `32137389273` and Build Image run `32137961972` succeeded for
  exact commit `a1879a2`.
- PASS: immutable release `rel-20260818T123929Z-a1879a2c699d` and digest
  `sha256:52fcf98a6570e40a71d4bbac803da9dfbed37875df354d2bd952700e94ecd6c5`.
- PASS: Deploy Staging run `32138435094`; `final_status=staging_ok`; exact
  commit/digest match; ALB target, localhost live/ready, smoke, schema, and
  SQLAlchemy persistence all healthy; migration remained `d4e5f6a7b8c9`.
- PASS: current `/health` and `/ready` report database/cache up and persistence
  `READY`.
- PASS by existing evidence: Rollback Staging run `31059080611` ended
  `rollback_ok` with healthy ALB/local probes and unchanged migration. It was
  not repeated.

## H. Data retrieval readiness

- An existing non-public CLI and repository list method cover the requested
  fields. No dashboard or public endpoint exists.
- FIXED ON THIS BRANCH: export now requires a new path outside the repository,
  never writes PII to stdout, creates mode `0600`, refuses overwrite/symlinks,
  neutralizes spreadsheet formulas, and removes partial output on failure.
- The staging RDS instance is private and encrypted. The documented operator
  path uses Session Manager port forwarding and a short-lived local database
  environment.
- Remaining operational gate: install the Session Manager plugin on the
  approved operator workstation and rehearse a private export. No real-user PII
  was exported during this audit.

## I. Privacy/Terms integration readiness

Current footer locations are `app/static/early_access/index.html` Privacy and
Terms anchors. They intentionally point to `/privacy` and `/terms`, are marked
`aria-disabled`, and are click-gated by `app/static/early_access/early-access.js`.
Both routes currently return 404.

### LEGAL-INTEGRATION CHECKLIST

- [ ] Supply approved Privacy and Terms files or exact approved URLs.
- [ ] Update the two footer anchors in `app/static/early_access/index.html`.
- [ ] Remove `aria-disabled` / `data-legal-gated` only when both destinations
  resolve; remove the corresponding click gate from `early-access.js`.
- [ ] If files are supplied, add the minimal static routes/files in
  `app/api/early_access_page.py` and the Early Access static directory.
- [ ] Obtain counsel/product wording for the signup disclosure near
  `.signup-note`; decide whether links are sufficient or affirmative consent is
  required. Do not infer this in engineering.
- [ ] Update `tests/unit/test_early_access_static.py` to require enabled,
  resolvable legal destinations and the approved disclosure behavior.
- [ ] Re-run accessibility, mobile, full test, secret, and staging smoke gates.

No legal content or URL was invented or implemented.

## J. Remaining blockers

1. Approved Privacy Policy / Privacy Notice and Terms & Conditions, exact
   publication destinations, and approved signup disclosure/consent behavior.
2. Explicit founder authorization to leave the production hold.
3. Separately authorized production environment, persistence, secrets, DNS,
   TLS, deployment/rollback, backup/restore, monitoring, and public smoke gates.
4. Shared/edge production abuse control and durable privacy-safe event logs.
5. A policy decision for device information and CTA-to-registration attribution.
6. Merge, rebuild, and staging deployment of this readiness branch, followed by
   a private operator export rehearsal.

## K. Remaining non-blocking issues

- Third-party GitHub actions currently emit a Node.js 20 deprecation warning;
  workflow execution remains successful.
- Existing Starlette/FastAPI deprecation warnings remain unrelated to Early
  Access behavior.
- Technical-error/Try Again was not induced with a destructive staging
  dependency failure; implementation and generic 500 behavior are covered by
  focused tests.

## L. Exact work completed while waiting

- Reconciled current main, locked masters, breakpoints, deployed release,
  health/persistence, and prior rollback evidence.
- Performed seven-width visual/responsive QA and desktop/mobile interaction QA.
- Performed one success plus normalized duplicate signup using synthetic data.
- Verified validation, loading, navigation, focus, live regions, event endpoint,
  headers, hostile-origin behavior, and bounded rate limiting.
- Corrected the proven loading-state contrast defect.
- Hardened the existing private CSV export and added regression tests.
- Added the private export runbook and document-only production cutover checklist.

## M. Exact files changed

- `app/static/early_access/early-access.css`
- `scripts/export_early_access.py`
- `tests/unit/test_early_access_export.py`
- `tests/unit/test_early_access_static.py`
- `docs/runbooks/EARLY_ACCESS_DATA_EXPORT.md`
- `docs/runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_CHECKLIST.md`
- `docs/roadmap/evidence/EARLY_ACCESS_PRE_PRODUCTION_READINESS_REPORT.md`

## N. Test results

- Early Access focused suite: 72 passed.
- OpenAPI/API contract suite: 49 passed.
- Protected-module/architecture suite: 123 passed.
- Full pytest: 2,608 passed with 168 known deprecation warnings in 400.66s.
- Ruff baseline: PASS; no new lint/format regression.
- Direct changed-file Ruff/format: PASS.
- Deterministic secret scan: PASS.
- `git diff --check`: PASS.
- Live staging event endpoints: 4/4 returned 204.

## O. GO / NO-GO status once Privacy + Terms are approved

- **Staging application:** conditional GO after this branch is reviewed,
  merged, rebuilt, deployed to staging, and the private export is rehearsed.
- **Public production launch:** NO-GO today. Legal approval removes the main
  content gate but does not itself authorize or complete production. Public GO
  requires every blocker in section J and the document-only production cutover
  checklist to pass under separate authorization.
