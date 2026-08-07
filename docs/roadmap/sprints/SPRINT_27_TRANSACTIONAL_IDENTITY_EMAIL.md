# Sprint 27 — Transactional Identity & Email

**Status:** Planned
**Primary owner / domain:** Identity / user platform (Sprint 17 domain; adapter hardening)
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-5

## Objective

Make self-serve authentication production-safe with real transactional email, complete password recovery, and email verification.

## Included requirements

- Select and integrate transactional email provider
- Sender-domain SPF/DKIM/DMARC verification
- Password-reset email + confirm route; token expiry and invalidation
- Email verification send + confirm
- Email-change verification
- Session rotation / revoke-all sessions
- Disable demo inline reset tokens in staging/production paths
- Failed-login messaging without account enumeration regressions

## Explicit non-goals

- OAuth/MFA
- Full privacy policy publication (28)
- Consumer UI polish (29)

## External dependencies

- EXT-08
- EXT-09

## Implementation deliverables

- Email sender adapter replacing NullEmailSender for staging/prod
- Confirm endpoints
- Config/secrets wiring

## Documentation deliverables

- AUTHENTICATION.md updates
- EMAIL_PROVIDER_ARCHITECTURE.md provider decision
- Runbook for email outages

## Required tests

- Unit/API tests for reset/verify confirm
- Enumeration-safe responses
- Token reuse rejected

## Required staging evidence

- Real inbox delivery of reset and verify emails
- E2E reset completes login

## Required production evidence

- Provider credentials in Secrets Manager (prep OK; full prod cutover in 41)

## Acceptance criteria

- Staging user can reset password via email without demo tokens
- Verification flow completes
- Tokens expire and invalidate after use
- Production config cannot enable demo token leakage

### Additive PiqSavi brand criteria (not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- Consumer-visible email subjects/bodies use PiqSavi
- No unintended DealBrain branding in transactional emails
- Public email-link base uses approved `piqsavi.com` URL
- Password-reset URLs use PiqSavi public configuration
- Verification URLs use PiqSavi public configuration
- Sender identity is PiqSavi
- Sender-domain authentication is verified before public use
- Internal DealBrain technical identifiers remain unchanged

## Predecessor sprints

26

## Parallelizable work

28 drafting can start after identity API shapes freeze

## Go / no-go gate

Go if staging E2E email flows pass; else public self-serve auth blocked

## Rollback or contingency

Feature-flag email flows off; revert to invite-only

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
