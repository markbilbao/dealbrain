# Sprint 41 — CDN / WAF decision proposal (2026-09-18)

**Status:** OWNER DECISION PROPOSAL — **not recorded as accepted**

**Authority:** [`../sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md`](../sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md) requires “CDN/WAF decision recorded.”

This document is **not** a retroactive owner, architecture, or security decision. It exists so the owner can accept, reject, or replace it. Until that happens, Sprint 41 CDN/WAF acceptance remains **open**.

## Current live topology (read-only, 2026-09-18)

- Public entry: AWS ALB `dealbrain-production-alb-1597181926.us-east-1.elb.amazonaws.com`
- TLS: ACM certificate for `piqsavi.com` and `www.piqsavi.com`
- Origin: one production EC2 Compose host serving FastAPI HTML + API on the same origin
- Consumer static assets: in-process / same-origin (`'self'` CSP `connect-src`)
- Application rate limits: in-process sliding window (Sprint 22 / 40)
- No CloudFront distribution, no AWS WAF WebACL, and no documented third-party CDN/WAF attachment were found in repository Terraform

## Proposed decision (for owner review)

**Do not require CloudFront or AWS WAF for initial Early Access / initial public beta.**

Reasoning, if the owner later accepts this:

1. Sprint 41 initial delivery is same-origin HTML from the production API host. There is no separate static-asset fleet that needs a CDN for correctness.
2. TLS, HTTP→HTTPS, and public DNS to the production ALB are already live.
3. Deep bot/WAF programs are already classified in `GAP_INVENTORY.md` as `post_beta_improvement`. In-process rate limits are a known Sprint 40 residual, not a hidden Sprint 41 CDN gap.
4. Adding CloudFront/WAF now would enlarge the production attack/ops surface (cache invalidation, header forwarding, WebACL false positives) without closing a current Early Access functional gap.
5. Sprint 43 still owns capacity evidence. A later CDN remains available if load tests show origin saturation.

## What this proposal does **not** do

- It does not install CloudFront or WAF.
- It does not change ALB, DNS, or Cloudflare.
- It does not close Sprint 40 CSP `'unsafe-inline'` or in-process rate-limit findings.
- It does not count as the Sprint 41 “CDN/WAF decision recorded” acceptance criterion until the owner records acceptance (or a different decision) in writing.

## Owner actions

Choose one and record it:

- **Accept** this “not required for initial beta” decision, with the reasoning above.
- **Reject** and require CloudFront and/or WAF before Sprint 41 close.
- **Defer** CDN/WAF to Sprint 42/43/40 with an explicit written exception that Sprint 41 may close without it.

Until one of those is recorded, the criterion stays **open**.
