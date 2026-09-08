# Sprint 27 — 2026-09-08 staging evidence reconciliation

**Document type:** Dated reconciliation / evidence record (not a new feature design)  
**Sprint definition:** [`../sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](../sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md)  
**Prior harness (not rewritten):** [`SPRINT_27_3_STAGING_EMAIL_E2E_TEMPLATE.md`](SPRINT_27_3_STAGING_EMAIL_E2E_TEMPLATE.md)  
**DNS runbook:** [`../../runbooks/EXT_09_RESEND_DNS.md`](../../runbooks/EXT_09_RESEND_DNS.md)  
**Reconciliation date:** 2026-09-08  
**Baseline `origin/main` SHA:** `55b4e6880875b87bb99bd3331fbe4040fe2483d0`  
**Contains:** PR #118 (`f0e115cfd7cb426065ce96db8168f46aff092a08`) and PR #119 (this merge commit)  
**Sprint 27 / P0-5 status after this record:** **OPEN** — EXT-09 is **PASS / VERIFIED**. Remaining closure action is the designed production-code `identity_email_ready` gate update, then staging deploy and `/health` verification.  
**Production code changed by this record:** No  
**Merge performed:** No

This record does **not** rewrite the 2026-08-08 EXT-08/EXT-09 screenshots, the Sprint 26 bootstrap packages, or the 27.3 E2E template as if those documents had always contained this evidence.

No API keys, passwords, raw identity tokens, or full DKIM public-key material are stored here. No screenshots are invented. The 2026-09-08 inbox session has no repository screenshot. Owner/operator Resend **Verified** evidence is recorded below as sanitized dashboard observations (no image file was supplied).

---

## 1. Verdict

| Question | Verdict |
|----------|---------|
| Close Sprint 27 / P0-5 now? | **No** |
| Outcome | **B** — Sprint-27-owned sender-domain and inbox evidence now pass; Sprint 27 still cannot close while staging `/health` truthfully reports `identity_email_ready=false` |
| EXT-09 | **PASS / VERIFIED** — public DKIM/SPF/MX/DMARC DNS plus owner-observed Resend domain status **Verified** |
| Remaining Sprint-27-owned closure action | Designed production-code update of `identity_email_status().ready` / `external_evidence` in a **separate PR** (not this docs PR), then staging deploy, then confirm `/health` `identity_email_ready=true` |
| Sprint 41 | Production `RESEND_API_KEY` attach / production email live remains **Sprint 41**. Not a Sprint 27 blocker. Do not claim production email is live. |

---

## 2. Independent baseline and deployment checks

| Check | Result | Source |
|-------|--------|--------|
| `origin/main` SHA | `55b4e6880875b87bb99bd3331fbe4040fe2483d0` | `git fetch` + `git rev-parse HEAD` on 2026-09-08 |
| PR #119 merge | Yes — this SHA | `Merge pull request #119 from markbilbao/cursor/sprint-27-4-auth-aware-header-d434` |
| PR #118 ancestor | Yes — `f0e115cfd7cb426065ce96db8168f46aff092a08` | `git merge-base --is-ancestor` |
| HTTPS staging | `https://staging.piqsavi.com/` → HTTP 200, TLS verify OK | `curl` 2026-09-08 |
| TLS certificate | `CN=staging.piqsavi.com`, issuer Amazon RSA 2048 M04, notBefore 2026-09-07 | `openssl s_client` 2026-09-08 |
| Deploy Staging #31 | `success`, `headSha=55b4e6880875b87bb99bd3331fbe4040fe2483d0`, completed 2026-09-08T10:11:32Z | GitHub Actions run `34213996307` |
| Live `/health` | `status=up`, `environment=staging`, `identity_email_adapter=resend`, `identity_email_ready=false` | `GET https://staging.piqsavi.com/health` 2026-09-08 |
| Live `/health` `started_at` | `2026-09-08T10:11:08.152755+00:00` | Matches Deploy Staging #31 window |
| Live `/ready` | `ready=true`, `persistence_level=READY` | `GET https://staging.piqsavi.com/ready` 2026-09-08 |

Owner/operator observation that Deploy Staging #31 succeeded on this SHA is **independently corroborated** by GitHub Actions and by the live health `started_at`.

Staging TLS for `staging.piqsavi.com` is **not** EXT-09 evidence. It is not confused with DKIM/SPF/DMARC/return-path records.

---

## 3. Owner/operator-observed real-inbox E2E (2026-09-08)

The following are **owner/operator observations** from live staging. They are not repository screenshots and are not invented.

### 3.1 Sender / branding

| Observation | Result |
|-------------|--------|
| Sender | `PiqSavi <no-reply@piqsavi.com>` |
| Demo / inline token used | **No** for the live verify / reset / email-change flows below |
| Inbox | Real Gmail delivery |

### 3.2 Email verification — PASSED

- A real PiqSavi verification email was delivered.
- The user followed the real email link.
- Verification completed successfully.
- Account subsequently displayed `Email status: Verified`.

### 3.3 Password reset — PASSED

- A real password-reset email was delivered.
- Subject observed: `PiqSavi password reset`.
- The reset link opened the staging password-reset flow.
- A new password was submitted successfully.
- Final consumer state: `Password reset` / `Your password has been updated.` / `You can now sign in using your new password.`
- Sign-in using the updated credentials succeeded.

### 3.4 Email change — PASSED (observed UX)

Starting account email: `mark@piqsavi.com`  
Requested new email: `markbilbao@gmail.com`

- Account Change Email required new email + current password.
- Real confirmation email received at the proposed new address.
- Sender: `PiqSavi <no-reply@piqsavi.com>`
- Subject: `Confirm your new PiqSavi email`
- The real confirmation link was used.
- Email change succeeded.
- Account subsequently displayed `Email: markbilbao@gmail.com` and `Email status: Verified`.
- Lifecycle preserved confirmation-before-mutation.

**Not inferred from this UX:** session revoke-all after email-change confirm. That behavior is evidenced by implementation + tests (`tests/unit/test_sprint27_2_email_change.py`), not by the owner session.

**Not operator-observed:** old-email token-free security notice; live token-reuse rejection; live newest-request-wins. Those remain implementation + unit-test evidence.

### 3.5 Auth-aware header / logout — PASSED

After PR #119 deployment:

| State | Observation |
|-------|-------------|
| Signed in | Header displayed How it works / Account / Support / Sign out |
| After refresh | Validated authenticated state remained signed in |
| After Sign out | Redirected to `/` (Early Access page) |
| Direct `/account` after logout | Sign in / Sign up; `You are signed out on this device.`; did **not** expose display name, account email, account id, Change Email form, or other authenticated account information |

---

## 4. EXT-09 public DNS plus provider Verified

Repository standard (`docs/runbooks/EXT_09_RESEND_DNS.md`):

1. Copy live Resend DNS rows for `piqsavi.com`.
2. Apply them in Cloudflare (DNS only for mail TXT/MX).
3. Return to Resend and run **Verify**.
4. Record whether Resend reports the domain verified.
5. Retain sanitized verification evidence before marking EXT-09 `approved`.

Public DNS alone is **not** a substitute for step 3–5. Gmail delivery alone is **not** a substitute for Resend **Verified**. Together, the 2026-09-08 public DNS check **and** the owner-observed Resend **Verified** dashboard state satisfy the Sprint 27 sender-domain evidence requirement.

### 4.1 Public records checked 2026-09-08 (`dig` / `nslookup`)

Compared against the sanitized 2026-08-08 Resend plan
[`external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png)
(DKIM name `resend._domainkey`; Enable Sending host `send`; optional DMARC `v=DMARC1; p=none;`).

| Record | Public result | Matches plan type/name? |
|--------|---------------|-------------------------|
| TXT `resend._domainkey.piqsavi.com` | Present; RSA `p=` DKIM material (full key **not** committed) | Yes — Domain Verification / DKIM |
| MX `send.piqsavi.com` | `10 feedback-smtp.ap-northeast-1.amazonses.com.` | Yes — Return-Path / Enable Sending MX |
| TXT `send.piqsavi.com` | `v=spf1 include:amazonses.com ~all` | Yes — Return-Path SPF |
| TXT `_dmarc.piqsavi.com` | `v=DMARC1; p=none;` | Yes — optional DMARC, monitor-only |
| TXT `piqsavi.com` SPF | `v=spf1 include:_spf.google.com ~all` | **Not** the Resend sending SPF. This is apex Google Workspace receiving SPF. Resend SPF is on `send.piqsavi.com`. |
| Nameservers | `dilbert.ns.cloudflare.com.` / `elisabeth.ns.cloudflare.com.` | Cloudflare-hosted DNS (EXT-10 ownership context; not EXT-09 verify) |
| `staging.piqsavi.com` | CNAME to staging ALB; HTTPS works | **Not** a transactional-email DKIM/SPF record |

### 4.2 Owner/operator Resend dashboard evidence (2026-09-08)

Owner/operator observation of the live Resend domain screen for `piqsavi.com` on 2026-09-08. Sanitized. No API key, token, password, or DKIM public-key material. No screenshot file was supplied; none is invented or claimed to exist in this repository.

| Field | Owner-observed value |
|-------|----------------------|
| Domain | `piqsavi.com` |
| Domain status | **Verified** |
| Event / status message | `Domain verified: Your domain is ready to send emails.` |
| DNS provider shown | Cloudflare |
| Region | Tokyo (`ap-northeast-1`) |
| Observer | Owner/operator |
| Date | 2026-09-08 |

The reported region matches the independently resolved return-path MX `feedback-smtp.ap-northeast-1.amazonses.com.` That is corroboration of the sending region, not a substitute for the dashboard status.

### 4.3 What this still does **not** prove

- Production sender authentication or production email live
- Production `RESEND_API_KEY` attached (Sprint 41)
- DKIM/SPF alignment headers from the 2026-09-08 Gmail messages (not supplied)
- `/health` `identity_email_ready=true`
- Sprint 27 / P0-5 closure

**EXT-09 verdict:** **PASS / VERIFIED.** Public DNS for the plan’s DKIM / return-path SPF / return-path MX / optional DMARC rows is resolvable, and Resend reports domain status **Verified**. Register status: **`approved`**. This is not production email cutover.

---

## 5. `identity_email_ready` / health

Live staging 2026-09-08:

```text
identity_email_adapter=resend
identity_email_ready=false
```

Code (`app/auth/email_factory.py`):

- `configured` — Resend settings are constructible (non-placeholder key, From, public base URL).
- `adapter` — `resend` when `TRANSACTIONAL_EMAIL_PROVIDER=resend`.
- `external_evidence` — hardcoded `pending`.
- `ready` — hardcoded `False`.

This is **not** a stale health bug and **not** a missing operator config flag. It is the designed external-evidence gate: configuration ≠ Sprint 27 ready. Tests assert that a configured Resend adapter still reports `ready=false` (`tests/unit/test_sprint27_3_email_cutover.py`).

**Classification:** designed external-evidence gate, still hardcoded `pending` / `False`.

EXT-09 is now **Verified**. Inbox E2E has passed. `ready=false` is therefore **no longer** explained by missing sender-domain evidence. It remains the designed code gate. Closing Sprint 27 while staging `/health` still reports `identity_email_ready=false` would contradict health truthfulness.

**Remaining closure action (not this PR):** update `identity_email_status().ready` / `external_evidence` in a **separate production-code PR**, deploy that digest to staging, and verify `/health` reports `identity_email_ready=true`. This reconciliation does not implement that change.

---

## 6. Production cutover vs Sprint 41

Sprint 27 acceptance requires the **recorded** production-ready secret/config path, not live production attach.

| Item | Evidence | Sprint 27? |
|------|----------|------------|
| Staging secret path | `dealbrain/staging/resend_api_key` via `assemble-runtime-env.py` | Yes — recorded and in use (`adapter=resend` on staging) |
| Staging From / base URL | `no-reply@piqsavi.com` / `https://staging.piqsavi.com` | Yes |
| Production provider contract | `.env.production.example`: `TRANSACTIONAL_EMAIL_PROVIDER=resend`, From PiqSavi, `PUBLIC_APP_BASE_URL=https://piqsavi.com`, `ALLOW_DEMO_RESET_TOKENS=false` | Yes — path recorded |
| Production secret attach | Comment: `RESEND_API_KEY` attached from Secrets Manager in Sprint 41; isolation path `dealbrain/production/*` | **NOT Sprint 27** |
| Production email live | Not claimed | **NOT Sprint 27** |

---

## 7. Acceptance matrix (2026-09-08)

Status values: **PASS** (implementation + required evidence), **PARTIAL** (implementation exists; required evidence incomplete), **BLOCKED** (external/operator dependency remains), **NOT SPRINT 27**.

| Criterion | Status | Evidence |
|-----------|--------|----------|
| EmailSender / Resend adapter | PASS | Code + tests; staging `/health` `identity_email_adapter=resend`; real inbox delivery |
| Password-reset request | PASS | Implementation + tests; owner requested live reset without demo tokens |
| Password-reset real delivery | PASS | Owner: Gmail received `PiqSavi password reset` from `PiqSavi <no-reply@piqsavi.com>` |
| Password-reset confirm | PASS | Owner: staging reset form, success copy, subsequent sign-in |
| Reset expiry / single use | PASS | Implementation + unit tests (`test_sprint27_1_transactional_email.py`, `test_sprint27_3_email_cutover.py`). Live reuse was not operator-observed. |
| Session revoke-all after reset | PASS | Implementation + unit tests. Live prior-session death was not operator-observed. |
| Email verification request | PASS | Implementation + tests + owner live request |
| Verification real delivery | PASS | Owner: real verification email delivered |
| Verification confirm | PASS | Owner: real link; Account `Email status: Verified` |
| Verification expiry / single use | PASS | Implementation + unit tests. Live reuse was not operator-observed. |
| Authenticated email-change request | PASS | Implementation + owner: Account Change Email used while signed in |
| Current-password re-auth | PASS | Implementation + owner: new email + current password required |
| Email-change real delivery | PASS | Owner: confirmation received at proposed new address |
| Email-change confirmation | PASS | Owner: real link; Account email became `markbilbao@gmail.com`, `Verified` |
| Email unchanged before confirmation | PASS | Implementation + owner: confirmation-before-mutation preserved |
| New email verified only after mailbox control | PASS | Owner: new address Verified only after confirming the new-inbox link |
| Session revoke-all after email change | PASS | Implementation + unit tests (`test_sessions_revoked_and_login_identity_updates`). **Not** inferred from owner UX. |
| Purpose-bound tokens | PASS | Implementation + unit tests (`test_purpose_separation`, wrong-purpose cases) |
| Newest-request-wins | PASS | Implementation + unit tests. Live operator re-request race was not observed. |
| Enumeration safety | PASS | Implementation + unit/HTTP tests. Owner flows used real accounts; no demo-token leakage. |
| Demo-token disabled in staging/prod | PASS | Config contract + tests; owner: no demo/inline token used; staging health uses Resend |
| PiqSavi email branding | PASS | Templates + owner sender/subjects (`PiqSavi`, `PiqSavi password reset`, `Confirm your new PiqSavi email`) |
| Approved staging public base URL | PASS | Contract `https://staging.piqsavi.com`; owner reset/verify/change links opened staging flows; HTTPS independently confirmed |
| HTTPS staging link behavior | PASS | Owner links opened staging; independent HTTPS 200 + valid cert for `staging.piqsavi.com` |
| SPF/DKIM/DMARC / EXT-09 | PASS | Public DNS resolvable for plan rows **and** owner-observed Resend domain status **Verified** (2026-09-08 sanitized dashboard evidence) |
| Staging real-inbox E2E | PASS | Verify + reset + email-change real Gmail delivery and confirm on 2026-09-08 |
| Production cutover readiness path | PASS | Path recorded; attach remains Sprint 41 |
| Production secret attached / prod email live | NOT SPRINT 27 | Sprint 41 |
| Auth-aware signed-in/signed-out header | PASS | PR #119 on deployed SHA; owner signed-in / refresh / signed-out header E2E |
| Logout privacy / no stale PII exposure | PASS | Owner: `/account` after logout showed signed-out controls only |
| P0-5 closure | BLOCKED | Designed `identity_email_ready` production-code gate still reports `false`; not flipped in this docs PR |

---

## 8. Explicit non-claims

- Sprint 27 is **not** complete.
- P0-5 is **not** closed.
- EXT-09 **is** verified for Sprint 27 sender-domain evidence (public DNS + Resend **Verified**).
- Production transactional email is **not** live.
- Production secrets are **not** attached.
- `identity_email_ready=true` is **not** claimed.
- Inbox delivery is **not** production cutover.
- No later sprint (28, 29, 37–41) work is pulled into Sprint 27 by this record.
