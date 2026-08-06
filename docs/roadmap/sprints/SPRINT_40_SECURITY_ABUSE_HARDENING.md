# Sprint 40 — Security & Abuse Hardening

**Status:** Planned
**Primary owner / domain:** Security engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes

## Objective

Close launch-blocking security findings and establish abuse protections appropriate for public traffic.

## Included requirements

- AuthN/AuthZ/object-level review
- Session security review
- Headers/CSP/CORS/CSRF policy completion
- Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection
- Log redaction; body logging policy; PII handling
- Secret/dependency/SAST/container/Terraform scanning in CI
- Supply-chain provenance checks; immutable image authority verification
- Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta
- Account lockout or equivalent
- AI prompt-injection + merchant-content sanitation review
- Pen-test readiness package; security IR runbook; vulnerability-response process
- Close all HIGH and launch-blocking MEDIUM findings

## Explicit non-goals

- Full WAF/CDN depth program (post-beta OK)
- Formal SOC2 certification

## External dependencies

- None

## Implementation deliverables

- Scanning workflows
- Rate-limit/lockout hardening
- CSP/SSRF fixes
- IR templates

## Documentation deliverables

- SECURITY.md updates
- Vuln response
- Pen-test readiness checklist

## Required tests

- Security regression tests
- Scanner gates in CI

## Required staging evidence

- Scanners clean on candidate
- Abuse controls exercised

## Required production evidence

- Prod IAM review continues in 41

## Acceptance criteria

- No open HIGH
- Launch-blocking MEDIUM closed or time-boxed risk-accepted in writing
- CI scanning required on main
- Security package ready for 44 approval

## Predecessor sprints

27, 28, 29

## Parallelizable work

39, 41 prep

## Go / no-go gate

Security go/no-go draft ready

## Rollback or contingency

Keep registration invite-only if abuse controls fail

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
