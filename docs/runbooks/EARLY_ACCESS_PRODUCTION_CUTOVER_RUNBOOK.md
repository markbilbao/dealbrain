# Early Access production cutover runbook

**HOLD until the owner explicitly authorizes each public-facing step.**

This runbook does not deploy production, change DNS, or merge. It is the owner-controlled sequence after staging acceptance of SHA `c4135859663a482b078da6959af746fd2d5dc098`.

Authoritative audit: [`../roadmap/evidence/EARLY_ACCESS_PRODUCTION_CUTOVER_READINESS_2026-09-11.md`](../roadmap/evidence/EARLY_ACCESS_PRODUCTION_CUTOVER_READINESS_2026-09-11.md).

**Current resulting state:** `EARLY ACCESS PRODUCTION CUTOVER BLOCKED — SPECIFIC INFRASTRUCTURE/OPERATIONS ITEMS REMAIN`

Do not start steps marked IRREVERSIBLE OR PUBLIC-FACING until blockers 1–10 in the audit are closed and the owner records GO.

## Locked release (do not drift)

| Field | Value |
|-------|-------|
| Git SHA | `c4135859663a482b078da6959af746fd2d5dc098` |
| Release ID | `rel-20260911T071047Z-c4135859663a` |
| Image digest | `sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa` |
| Image | `ghcr.io/markbilbao/dealbrain@sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa` |
| Build Image run | `34573165486` |
| Deploy Staging | #35 / `34573790133` / `staging_ok` |
| Privacy | `privacy-2026-09-11` |
| Terms | `terms-2026-09-11` |

If `main` moves, re-lock SHA + digest before any production action. Deploy the immutable digest; do not rebuild at cutover.

Legend: **SAFE / READ-ONLY** · **OWNER ACTION REQUIRED** · **IRREVERSIBLE OR PUBLIC-FACING**

---

### 0. Preconditions (SAFE / READ-ONLY)

- Confirm `origin/main` still equals the locked SHA, or record a new lock.
- Confirm staging `/health` `/ready` `/privacy` `/terms` still 200 on that digest.
- Confirm GitHub Environment `production` exists (today: **absent until owner UI** — stop). See [`GITHUB_PRODUCTION_ENVIRONMENT.md`](GITHUB_PRODUCTION_ENVIRONMENT.md).
- Confirm `.github/workflows/deploy-production.yml` exists and deploys by digest (in-repo as of Phase 1; dispatch still owner-only after Environment + apply).
- Confirm production AWS inventory shows isolated `dealbrain-production-*` VPC/ALB/TG/EC2/RDS (today: **not live** — stop).
- Confirm this is Early Access only. Do not enable shopping, `/demo` links, merchants, or affiliate tracking.

### 1. Final SHA / digest lock (OWNER ACTION REQUIRED)

Owner records in writing: SHA, release ID, digest, Build Image run, staging run. No production action with a different digest.

### 2. Production infra verification (SAFE / READ-ONLY, then OWNER apply)

Today this step fails closed. Owner/ops (not this agent) must apply isolated production Terraform when authorized:

- Backend: encrypted S3 state key `production/terraform.tfstate` with `use_lockfile = true`.
- VPC `10.20.0.0/16`, private API host, public ALB, private RDS, secrets containers, OIDC deploy role.
- Do **not** use the staging ALB as production.
- ACM (or Cloudflare origin TLS) covering `piqsavi.com` and `www.piqsavi.com`.
- ALB target group health `/ready`.
- HTTPS listener + HTTP→HTTPS redirect (`certificate_arn` non-empty).

Re-verify live: production ALB `/ready` 200 **before** DNS.

### 3. Secrets confirmation (OWNER ACTION REQUIRED)

Do not put values in GitHub. Populate AWS Secrets Manager `dealbrain/production/*` out-of-band. Confirm presence, never print values:

- `app_secret_key` (strong, ≥32)
- `cors_origins` (`https://piqsavi.com`)
- `ghcr_pull` (`read:packages` PAT)
- RDS master secret (AWS-managed) → host-assembled `DATABASE_URL`
- `resend_api_key` — **required to boot this image** with `APP_ENV=production`. Does **not** by itself prove production email is live.
- Host env: `PUBLIC_APP_BASE_URL=https://piqsavi.com`, `TRUSTED_HOSTS=piqsavi.com,www.piqsavi.com`, legal version ids `privacy-2026-09-11` / `terms-2026-09-11`, sqlalchemy persistence, demo/seed/launcher off.

GitHub Environment `production` variables only: `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`, production target-group ARN. Required reviewers on `main`.

### 4. Backup snapshot (OWNER ACTION REQUIRED)

Before first public traffic:

- Confirm production RDS automated backups ≥30 days, deletion protection, Multi-AZ, final snapshot enabled.
- Take a manual snapshot and record the snapshot id.
- Restore rehearsal: restore snapshot to a throwaway instance, `SELECT` operational store, destroy throwaway. If unrehearsed, **do not claim backup ready**.

### 5. Deployment (OWNER ACTION REQUIRED; not public until DNS)

When a production workflow exists:

1. Owner approves the GitHub `production` environment job.
2. Dispatch production deploy from `main` with Build Image run `34573165486` (or the re-locked build run) and release id `rel-20260911T071047Z-c4135859663a`.
3. Wait for host evidence `production_ok` (or equivalent). Do not fabricate evidence.
4. Expected wait: staging analogue was ~2 minutes; SSM timeout 40 minutes.

If the workflow still does not exist, **stop**. Do not SSM by hand from a laptop unless a separately authorized break-glass procedure exists.

### 6. Health wait (SAFE / READ-ONLY)

Against the **production ALB** (not apex DNS yet):

- `GET /live` 200
- `GET /ready` 200 `ready: true` `persistence_level: READY`
- `GET /health` 200, `environment: production`, legal flags true, sqlalchemy persistence
- ALB target healthy
- `GET /` `/privacy` `/terms` 200 on the ALB hostname

If any fail: do not touch DNS; use rollback section.

### 7. DNS (IRREVERSIBLE OR PUBLIC-FACING)

Owner-only in Cloudflare. Do not point apex at staging.

Current apex: Cloudflare-proxied static page (`104.21.66.117` / `172.67.159.152`). Staging remains CNAME to `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com`.

Owner steps:

1. Record current apex/www records (screenshot + export) for revert.
2. Choose proxy mode: DNS-only to production ALB (like staging) **or** proxied Full (strict) to ALB origin.
3. Replace apex static target with production ALB. Keep `www` → `https://piqsavi.com/`.
4. Do not change Resend/Google MX/TXT/SPF/DKIM as part of this cutover unless a named email task says so.

### 8. TLS (SAFE / READ-ONLY after DNS)

- Browser/openssl: cert covers `piqsavi.com` (and www as designed).
- HTTPS 200 on `/` `/privacy` `/terms` `/ready`.
- HTTP→HTTPS 301 if ALB redirect (and/or Cloudflare Always HTTPS) is enabled.
- Staging cert must remain `staging.piqsavi.com` only.

### 9. Public smoke (IRREVERSIBLE OR PUBLIC-FACING)

Use `qa-early-access-prod-cutover-20260911@piqsavi.com` (or another clearly synthetic, later-exportable address):

1. Homepage 200, approved desktop/mobile, PiqSavi lockup — not the pre-cutover static page.
2. `/privacy` `/terms` 200; footer links; versions `privacy-2026-09-11` / `terms-2026-09-11`.
3. Acknowledgement unchecked; reject without it; success with it; duplicate path.
4. Persistence: confirm row survives a controlled restart **only if** ops has already proven RDS.
5. No shopping chrome; no `/demo` link; no affiliate tracking.

Do not run these against production until DNS is owner-authorized.

### 10. Rollback decision point (OWNER ACTION REQUIRED)

Decide within the watch window if:

- App, signup, legal pages, or `/ready` fail
- TLS/DNS is wrong
- Shopping/demo/affiliate accidentally public

**If DNS has not changed:** leave Cloudflare static page in place; roll/fix production privately.

**If DNS has changed:**

1. Immediate public rollback: restore Cloudflare apex/www to the captured static-page records.
2. Application rollback (only after a production rollback workflow exists): dispatch prior production digest. None exists before the first successful prod deploy.
3. Do not drop RDS. Signups must survive image rollback.

Expected DNS revert time: minutes (Cloudflare TTL/proxy). Expected image rollback time: on the order of the staging rollback (minutes; 40 min SSM cap).

### 11. Watch window (SAFE / READ-ONLY)

Owner monitors `/ready`, signup success/errors (no PII in logs), ALB 5xx, certificate, and support/privacy inboxes. Product analytics stay off.

---

## Explicit prohibitions

- Do not deploy production from this document alone.
- Do not change DNS without owner GO after health wait.
- Do not merge this (or any) PR as a substitute for owner cutover authorization.
- Do not attach public DNS to staging.
- Do not activate Shopee, Lazada, BuyWhere, live search, recommendations, merchant certification, affiliate monetization, or analytics.
