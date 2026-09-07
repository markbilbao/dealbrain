# EXT-09 — Resend sender-domain DNS (operator runbook)

**Status:** Instruction only. DNS is **not** applied and **not** verified by this document.  
**Sprint:** 27.3 cutover readiness — owner/operator executes after this PR.  
**Domain:** `piqsavi.com`  
**Provider:** Resend  
**DNS host:** Cloudflare (registrar/control evidenced for EXT-10; this runbook does not claim public hostname, TLS, or proxy readiness)

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
4. Do **not** mark EXT-09 `approved` / `provisioned` in the register until sanitized verification evidence is retained
5. Do **not** treat verification as Sprint 27 complete — real inbox E2E is still required ([`../roadmap/evidence/SPRINT_27_3_STAGING_EMAIL_E2E_TEMPLATE.md`](../roadmap/evidence/SPRINT_27_3_STAGING_EMAIL_E2E_TEMPLATE.md))

## Evidence rules

Retain only sanitized screenshots/logs:

- Domain name `piqsavi.com` and record **types/names** may appear
- Redact full DKIM public-key material if the evidence will be committed, or keep the full value only in operator-private notes
- Never store API keys, session cookies, raw identity tokens, or passwords
- This runbook is not evidence that DNS was applied

## Explicit non-claims

- EXT-09 remains `applied` (plan) until live verify evidence exists
- EXT-11 public hostname DNS and EXT-12 TLS are separate
- Google Workspace receiving / support / privacy inboxes are separate
- Production `RESEND_API_KEY` attach remains Sprint 41
