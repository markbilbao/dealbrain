# EXT-09 — Resend sender-domain DNS (operator runbook)

**Status:** Instruction plus 2026-09-08 public-DNS check **and** owner-observed Resend domain **Verified**. Sprint 27 sender-domain evidence is **PASS**. Production `RESEND_API_KEY` attach remains Sprint 41.  
**Sprint:** 27 — EXT-09 complete; Sprint 27 / P0-5 **COMPLETE / CLOSED** after PR #121 / Deploy Staging #32 live `/health` `identity_email_ready=true` on 2026-09-08. Production `RESEND_API_KEY` attach remains Sprint 41.

**Domain:** `piqsavi.com`  
**Provider:** Resend  
**DNS host:** Cloudflare (registrar/control evidenced for EXT-10; this runbook does not claim production public hostname, TLS, or proxy readiness)

Owner-observed Resend dashboard (2026-09-08, sanitized): domain status **Verified**; message `Domain verified: Your domain is ready to send emails.`; provider Cloudflare; region Tokyo (`ap-northeast-1`). Recorded in [`../roadmap/evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](../roadmap/evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md).

Do **not** invent, guess, or reuse abbreviated record values from screenshots. Copy the exact records displayed by the current Resend domain-verification screen at execution time.

Sanitized Sprint 26 plan evidence (not a substitute for live values):
[`../roadmap/evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](../roadmap/evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png)

## Preconditions

- Resend account exists (EXT-08 `applied` — account establishment only)
- Operator can open Resend → Domains → `piqsavi.com` (add the domain in Resend first if it is not already listed)
- Operator can edit Cloudflare DNS for `piqsavi.com`
- Staging secret `dealbrain/staging/resend_api_key` is ready to attach (or already attached) via Secrets Manager — this runbook does not create the key

## What to copy from Resend

Open the Resend domain-verification / “Fill in your DNS Records” screen for `piqsavi.com`. Copy each displayed row exactly:

1. **DKIM** — typically a TXT name such as `resend._domainkey` (confirm the live name). Copy the full Content value from Resend. Do not truncate. Do not invent a public key.
2. **Return-Path / Enable Sending** — copy the live MX and/or TXT rows Resend shows (Sprint 26 plan showed a `send` subdomain intended as `send.piqsavi.com`). Confirm names, priority, and Content against the live screen.
3. **SPF** — copy only the SPF TXT Resend displays for the Return-Path / sending hostname. Do not invent an SPF string.
4. **DMARC** — apply **only** according to the existing approved plan / current domain policy. The Sprint 26 plan displayed `v=DMARC1; p=none;` as optional. Do **not** upgrade to `p=quarantine` or `p=reject` from this runbook. If a DMARC record already exists for `piqsavi.com`, do not overwrite it without an explicit owner decision. If Resend still shows optional `_dmarc` with `p=none` and no DMARC exists, that is the only DMARC this runbook authorizes.

Never hard-code a DNS value into git from this execution unless it is already evidenced from the live provider and sanitized.

## Cloudflare apply

For each copied record:

1. Cloudflare → DNS → Records for `piqsavi.com`
2. Create or update the matching type / name / content / TTL
3. **Proxy status**
   - TXT (DKIM, SPF, DMARC): DNS only — do **not** orange-cloud / proxy
   - MX (Return-Path): DNS only — MX is not proxied
   - If Resend later shows a CNAME Return-Path, follow the live Resend instruction. Do not proxy a mail CNAME unless Resend and current Cloudflare mail guidance both require it. Default for this runbook: DNS only
4. Save. Do not use “Auto configure” unless the owner explicitly accepts Cloudflare’s Resend integration for this domain at execution time. Manual copy is the default because it keeps values operator-visible.

## Verify in Resend

1. Wait for DNS propagation (often minutes; can be longer)
2. Return to the Resend domain screen and run **Verify**
3. Record the date/time and whether Resend reports the domain verified
4. Do **not** mark EXT-09 `approved` in the register until sanitized verification evidence is retained
5. Public DNS or Gmail delivery alone is not verification. Combined with Resend **Verified** (recorded 2026-09-08), Sprint 27 sender-domain evidence is complete. Staging inbox E2E (verify/reset/email-change) also passed 2026-09-08 ([`../roadmap/evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](../roadmap/evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md)). Sprint 27 / P0-5 later closed after PR #121 / Deploy Staging #32 when live staging `/health` reported `identity_email_ready=true`. Production email attach remains Sprint 41.

## Evidence rules

Retain only sanitized screenshots/logs:

- Domain name `piqsavi.com` and record **types/names** may appear
- Redact full DKIM public-key material if the evidence will be committed, or keep the full value only in operator-private notes
- Never store API keys, session cookies, raw identity tokens, or passwords
- This runbook is not evidence that DNS was applied

## Explicit non-claims

- EXT-09 sender-domain evidence is **Verified** / register `approved` as of 2026-09-08
- This is not production email live and not production secret attach (Sprint 41)
- Public DNS resolvability alone was never sufficient; it is now paired with Resend **Verified**
- EXT-11 public hostname DNS and EXT-12 TLS are separate
- Google Workspace receiving / support / privacy inboxes are separate
- Production `RESEND_API_KEY` attach remains Sprint 41
- This runbook does not flip `/health` `identity_email_ready`
