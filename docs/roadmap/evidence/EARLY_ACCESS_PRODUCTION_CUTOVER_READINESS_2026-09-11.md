# Early Access production cutover readiness — 2026-09-11

**Resulting state:** `EARLY ACCESS PRODUCTION CUTOVER BLOCKED — SPECIFIC INFRASTRUCTURE/OPERATIONS ITEMS REMAIN`

**Scope:** PiqSavi Early Access landing, Early Access signup, published Privacy Policy, published Terms of Service. Not public shopping beta, live search, live recommendations, Shopee/Lazada/BuyWhere, merchant certification, affiliate monetization, or analytics launch.

**This audit did not:** deploy production, change DNS, merge, create secrets, apply Terraform, or activate shopping/merchant/affiliate surfaces.

Owner-controlled runbook: [`../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md`](../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md).

## Locked identities (verified this audit)

| Item | Value | How verified |
|------|-------|----------------|
| Current `origin/main` | `c4135859663a482b078da6959af746fd2d5dc098` | `git fetch origin main` then `git rev-parse origin/main` |
| Staging accepted SHA | `c4135859663a482b078da6959af746fd2d5dc098` | Matches expected SHA; Deploy Staging run head |
| CI | run `34572604676` success | `gh run list --workflow ci.yml` |
| Build Image | run `34573165486` success | `gh run view` |
| Release ID | `rel-20260911T071047Z-c4135859663a` | Build Image + Deploy Staging logs |
| Image digest (authority) | `sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa` | GHCR publish + staging deploy evidence |
| Image repository | `ghcr.io/markbilbao/dealbrain` | Build Image logs; **not ECR** |
| Immutable tag (pointer only) | `ghcr.io/markbilbao/dealbrain:sha-c4135859663a482b078da6959af746fd2d5dc098` | Not deployment authority |
| Deploy Staging | **#35**, run ID `34573790133`, `staging_ok` | Workflow success + host evidence accepted |
| Manifest SHA-256 | `ad6ed6d9fb1630d61adfe0f307b62375aad359acf206371c84acce5428ee444e` | Build/deploy logs |
| Privacy published version | `privacy-2026-09-11` | Staging `GET /privacy` 200 contains id |
| Terms published version | `terms-2026-09-11` | Staging `GET /terms` 200 contains id |

Expected `origin/main` matched. This audit used current main at that SHA.

## 1. Production infrastructure

Architecture in this repository is **EC2 Compose host + ALB + RDS**, not ECS. There is no ECS service or task definition.

| Resource | Implemented in repo | Actually provisioned | Verified live |
|----------|---------------------|----------------------|---------------|
| Isolated production AWS stack | Yes — `infra/terraform/environments/production/` | **Not evidenced.** Production backend is intentionally deferred / commented. This workstation has no AWS CLI/credentials, so AWS inventory of `dealbrain-production-*` was **not** executed. | **No.** Public DNS/HTTP do not reach a DealBrain ALB. |
| Production VPC / subnets / SG | Modeled (`10.20.0.0/16`) | Not evidenced applied | Not live |
| Production ALB | Modeled (`dealbrain-production-alb`) | Not evidenced applied | No production ALB hostname in public DNS |
| Production target group | Modeled; health path `/ready`, matcher `200` | Not evidenced applied | Not live |
| Health checks | TF ALB `/ready`; Compose `/live` | Staging only | Staging `/live` `/ready` `/health` up. Apex `/health` **404** |
| HTTPS listener / HTTP→HTTPS | TF creates HTTPS + redirect only when `alb_certificate_arn` is non-empty | Production ARN is placeholder | Staging HTTPS is ACM; staging HTTP still **200** (no redirect). Apex TLS is Cloudflare, not ALB |
| GHCR image path | `ghcr.io/markbilbao/dealbrain@sha256:…` | Staging pulls this digest | Staging serving this digest. Production example still `EXAMPLE_ORG` / `REPLACE_ME` |
| ECR | Not used | n/a | n/a |
| Production EC2 Compose host | Modeled, private subnet, no public IP | Not evidenced applied | Not live |
| Production RDS | Modeled: Postgres, encrypted, Multi-AZ, 30-day backup, deletion protection, final snapshot required | Not evidenced applied | No production DB. Early Access durability therefore **not available** |
| Production secrets containers | Modeled `dealbrain/production/*` | Values out-of-band; stack not applied | Not live |
| Production GHA OIDC role | Modeled `dealbrain-production-gha-deploy` (legacy name-only `sub` until migrated) | Not operational — GitHub Environment `production` absent | Not live |
| Production SSM deploy document | Staging has `DealBrain-StagingDeploy`. Production TF still defaults to `AWS-RunShellScript` until a production custom document exists | Not a production deploy path | Not live |
| Production release-artifacts bucket | Staging-only (`dealbrain-staging-release-artifacts-<account>`). Production module not wired | Staging bucket used by Deploy Staging #35 | No production bucket |
| CloudWatch log groups | IAM hook exists; empty `log_group_arns` until Sprint 25c | Not created | Not live |

**Do not treat Terraform as provisioned.** Live proof that production is not serving the app: `piqsavi.com` is a Cloudflare-proxied static page; `/health` `/privacy` `/terms` return **404**.

Staging **is** provisioned and live: `staging.piqsavi.com` CNAME `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com`.

## 2. Production deploy workflow

| Question | Finding |
|----------|---------|
| Production deploy workflow exists? | **No.** `.github/workflows/deploy-production.yml` is absent. Multiple tests require that absence. |
| Workflows that exist | `ci.yml`, `build-image.yml`, `deploy-staging.yml` (Deploy Staging), `rollback.yml` (Rollback Staging) |
| Staging trigger | `workflow_dispatch` from `refs/heads/main` only |
| Staging inputs | required `build_workflow_run_id`; optional `release_id` |
| Staging environment | GitHub Environment `staging` |
| Staging secrets from GitHub | Workflow contract: **none**. OIDC + AWS Secrets Manager on host |
| Staging approval gates | Branch policy **main only**. **No required reviewers.** `can_admins_bypass: true` |
| Staging deploy authority | Immutable GHCR digest from Build Image release-manifest (no rebuild at deploy) |
| Rollback relationship | Shared concurrency `staging-release-mutation` with Rollback Staging; prior `staging_ok` digest required |
| Production rollback workflow | **Absent** |

Minimum work to make an owner-controlled production deploy **possible** (not done in this task; Sprint 41):

1. Create GitHub Environment `production` (required reviewers, `main` only, admin bypass disabled or audited).
2. Apply isolated production Terraform (S3 backend + lockfile first).
3. Add production release-artifacts bucket + custom SSM deploy/rollback documents (do not keep `AWS-RunShellScript` as the production path).
4. Parameterize host `assemble-runtime-env.py` (today it **refuses** a production secrets prefix and hardcodes `APP_ENV=staging` / `PUBLIC_APP_BASE_URL=https://staging.piqsavi.com`).
5. Add `deploy-production.yml` that promotes the **already-built** digest `sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa` (or a later owner-locked digest) the same way staging does.
6. Update tests that currently forbid `deploy-production.yml`.

This PR does **not** create that workflow.

## 3. GitHub production environment

| Item | State |
|------|-------|
| Environment named `production` | **Absent** (`GET …/environments/production` → 404) |
| Repo architecture expects it | **Yes.** OIDC trust `…:environment:production`; docs require production reviewers |
| Environments that exist | `staging` only |
| `staging` protections | Custom branch policy: `main`. No wait timer. No required-reviewer rule. Admins may bypass |
| `staging` variables (required by workflow) | `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`, `STAGING_TARGET_GROUP_ARN` — names from workflow; values **not listed** (API 403 in this audit) |
| `staging` GitHub secrets | Workflow says none; list API 403 |
| Required production environment secrets | **None in GitHub** if the staging pattern is preserved (OIDC). Application secrets belong in `dealbrain/production/*` |
| Required production environment variables | `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`, production target-group ARN |
| Required production approvals | Required reviewers; `main` only; admin bypass disabled or audited |

This audit did **not** create or populate secrets.

## 4. Production secrets / config matrix (Early Access only)

Production application secrets are **not populated**. Staging assembly explicitly refuses the production prefix. Values were not read.

| Variable / secret | Required for EA production boot? | Source | Current production state | Action required |
|-------------------|----------------------------------|--------|--------------------------|-----------------|
| `APP_ENV=production` | Yes | Compose production overlay | Overlay exists; not applied | Set only on production host |
| `APP_DEBUG=false` | Yes | Overlay | Overlay exists | Keep |
| `LAUNCH_STRICT_STARTUP=true` | Yes | Overlay + validation | Overlay exists | Keep |
| `PUBLIC_APP_BASE_URL=https://piqsavi.com` | Yes (startup + any action links) | `.env.production.example` | Not applied | Set on production host |
| `TRUSTED_HOSTS` | Recommended (warning if empty) | Example still `api.dealbrain.example` | Placeholder | Set `piqsavi.com,www.piqsavi.com` |
| `CORS_ORIGINS` | Yes (must be non-empty, not `*`) | Secret container `cors_origins` | Not populated | Populate `https://piqsavi.com` (and www if used) |
| `LEGAL_PRIVACY_PUBLISHED_VERSION_ID=privacy-2026-09-11` | Yes for published `/privacy` + signup ack | Image defaults already this id | Defaults in `app/core/config.py` | Keep explicit in prod env |
| `LEGAL_TERMS_PUBLISHED_VERSION_ID=terms-2026-09-11` | Yes | Same | Same | Keep explicit |
| `PERSISTENCE_BACKEND=sqlalchemy` (and domain backends) | **Yes — durability blocker if missing** | Compose base | Production RDS absent | Provision RDS; do not use memory/JSON file |
| `DATABASE_URL` | Yes | Host assembly from RDS master secret | No production RDS | Apply RDS; assemble on host; never GitHub |
| `APP_SECRET_KEY` | Yes (≥32, non-placeholder) | `dealbrain/production/app_secret_key` | Not populated | Create out-of-band |
| `dealbrain/production/ghcr_pull` | Yes to pull GHCR on host | Secrets Manager container | Not populated | Classic PAT `read:packages` only |
| `TRANSACTIONAL_EMAIL_PROVIDER=resend` | **Yes for this image to boot in production** | Overlay + `validate_settings` | Production Resend **not attached** | Populate production leaf **or** do not boot `APP_ENV=production` |
| `RESEND_API_KEY` | **Yes for production boot** of this image | `dealbrain/production/resend_api_key` | Not populated | Separate from “email is live.” Signup persists even if send fails. Do **not** claim production transactional email is live until a production send is proven |
| `TRANSACTIONAL_EMAIL_FROM=no-reply@piqsavi.com` | Yes if Resend gate applies | Staging/prod examples | Domain verified (EXT-09); prod key absent | Set with production key |
| Support / privacy contacts | Already published in legal HTML | EXT-17 / EXT-18 `provisioned` | Inboxes exist | No new secret |
| `RATE_LIMITING_ENABLED=true` | Yes | Overlay/defaults | Code only | Keep; see rate-limit section |
| `RATE_LIMIT_REGISTRATION_PER_MINUTE` | Yes (EA POST bucket) | Default 5; prod example 3 | Not applied | Set when host env is assembled |
| `DEMO_LAUNCHER_ENABLED=false` | Yes | Overlay | Overlay exists | Keep |
| `SEED_DEMO_DATA=false` | Yes | Overlay | Overlay exists | Keep |
| `OPENAPI_PUBLIC_DOCS=false` | Yes | Overlay | Overlay exists | Keep |
| `AFFILIATE_ENABLED` / merchant / shopping AI keys | **Not required to activate** for EA | Examples still enable some platform flags | Must stay non-monetized / unlinked | Do not populate live merchant/affiliate credentials |
| OpenAI / Anthropic / Gemini | Not required for EA | Optional empty | Empty OK | Leave empty; keep live HTTP false |

Staging `/health` on 2026-09-11: `identity_email_adapter=resend`, `identity_email_ready=true`, `legal_*_published=true`, `tracking_mode=essential_only`. That is **staging**, not production.

## 5. DNS + TLS (no changes made)

| Hostname | Current DNS target | Expected for EA cutover | TLS now | HTTPS listener | HTTP→HTTPS |
|----------|--------------------|-------------------------|---------|----------------|------------|
| `piqsavi.com` | Cloudflare anycast `104.21.66.117`, `172.67.159.152` (+ IPv6 `2606:4700:…`) | Production ALB DNS name (after prod ALB exists) | Cloudflare / Google Trust Services `WE1`, CN `piqsavi.com`, SAN `piqsavi.com` + `*.piqsavi.com`, valid 2026-09-04 → 2026-12-03 | Cloudflare 443 | HTTP apex still **200** from Cloudflare (not ALB redirect) |
| `www.piqsavi.com` | Same Cloudflare IPs | Keep 301 to canonical `https://piqsavi.com/` | Same WE1 cert | Cloudflare 301 to `https://piqsavi.com/` | n/a |
| `staging.piqsavi.com` | CNAME `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com` (A `34.194.176.228`, `100.63.67.5`) | Unchanged; keep isolated | ACM Amazon RSA 2048, SAN **only** `staging.piqsavi.com`, 2026-09-07 → 2027-03-23 | ALB 443 | Staging HTTP **200** to uvicorn (no redirect) |

Apex live content is a **Cloudflare static property page** (`property-page.css`, no Early Access, no `/privacy` `/terms`). It is **not** the PiqSavi app.

NS: `elisabeth.ns.cloudflare.com` / `dilbert.ns.cloudflare.com`. Apex is **proxied** (Cloudflare IPs). Staging is **DNS to ALB** (not Cloudflare anycast).

Cutover implication (owner-only; not executed):

1. Provision production ALB + ACM certificate covering `piqsavi.com` and `www.piqsavi.com` (or terminate TLS at Cloudflare and pin origin).
2. Decide Cloudflare proxy: DNS-only to ALB (matches staging) **or** remain proxied with Full (strict) origin TLS to the ALB.
3. Point apex from the static site to the production ALB **only** after prod `/ready` is green.
4. Preserve `www` → `https://piqsavi.com/`.
5. Do not point apex at the **staging** ALB.

EXT-11 remains `not_started`. EXT-12 remains `not_started` for production ALB TLS.

## 6. Early Access data durability

| Question | Answer |
|----------|--------|
| Storage backend | SQLAlchemy operational store `operational_entities` (`EARLY_ACCESS_REGISTRATIONS`), uniqueness on normalized email. **Not** a container-local JSON file |
| Volume mount | None for signups. Compose API is `read_only` + `tmpfs /tmp`. Persistence is **RDS** |
| Survives container restart / redeploy / host replacement? | **Yes only if production RDS exists** and the API uses `PERSISTENCE_BACKEND=sqlalchemy` |
| Production RDS | **Not provisioned / not live** |
| Classification | **Production blocker.** Staging durability is not production durability |

## 7. Backup / restore

| Need | State |
|------|-------|
| What would be backed up | Production RDS (Early Access rows live in `operational_entities`) |
| Destination | AWS RDS automated backups **if** production RDS is applied (TF default 30 days, `copy_tags_to_snapshot`) |
| Schedule | RDS automated backups after apply; no extra EA job exists |
| Restore procedure | No production restore runbook. `docs/BACKUP_RESTORE.md` is Sprint 22 **config** export with demo admin token — not DB DR |
| Restore rehearsed? | **No.** Do not claim backup readiness from Terraform defaults |

Staging RDS backup retention default is 7 days / no Multi-AZ. That is not a production restore drill.

## 8. Rollback

| Path | Exists? | Notes |
|------|---------|-------|
| Rollback Staging | Yes — `rollback.yml`, SSM `DealBrain-StagingRollback`, immutable prior digest, no DB downgrade | Staging only |
| Rollback Production | **No workflow** | Cannot execute |
| First public cutover | There is **no previous production app release** | Fastest public rollback is **revert Cloudflare DNS** to the current static page |
| After a first prod digest is live | Promote a previously deployed production digest via a production rollback workflow that does not yet exist | Image target = prior GHCR digest; expected time similar to staging (~minutes; SSM timeout 40 min) |
| Persistence on rollback | RDS data remains; rollback must not drop/downgrade the DB | Signup rows would survive image rollback **once RDS exists** |
| Failure modes | App/signup/legal/health fail → stop DNS if not yet public; if public, revert DNS and/or roll image | Owner decision; not executed |

## 9. Monitoring

| Layer | Exists | Retained | Alerts | Paging tested |
|-------|--------|----------|--------|---------------|
| `/health` `/live` `/ready` | Code + staging live | n/a | None | No |
| ALB target health `/ready` | TF modeled; staging live | AWS TG | None evidenced | No |
| Application logs | Structured stdout on Compose host | Not proven off-host | No | No |
| CloudWatch | Deferred Sprint 25c | No prod log groups | EXT-16 `not_started` | No |
| Paging | EXT-24 `not_started` | n/a | None | **No** |

Product analytics remain off (`tracking_mode=essential_only` on staging). Do not enable EXT-15 for this cutover.

Minimum Early Access ops bar (not met in production): ALB `/ready` green, retained logs, owner-reachable alert if `/ready` fails.

## 10. Rate limiting / abuse

Limiter is **in-process sliding window** (`app/launch/rate_limit.py`). It does **not** share state across processes/hosts. `/health` reports `rate_limiter` detail `in-process sliding window`.

EA buckets: registration (POST `/api/v1/early-access`) default 5/min/IP; events 20/min/IP.

Production TF default is **one** Compose EC2 host — same concurrency model as accepted staging.

**Assessment:** Redis/shared store is **not** justified for a single-host Early Access launch. Keep one API replica. Optional Cloudflare WAF/rate-limit at DNS cutover is defense-in-depth, owner-configured, not implemented here. If task count > 1, in-process limits become a blocker.

## 11. Public exposure / security (same image that would be promoted)

Verified on staging 2026-09-11 against SHA `c413585`:

| Surface | Intended | Live staging |
|---------|----------|--------------|
| `GET /` Early Access | Public | 200; no `/demo` or `/search` links; ack checkbox present and not `checked` |
| `GET /privacy` | Public | 200, `privacy-2026-09-11` |
| `GET /terms` | Public | 200, `terms-2026-09-11` |
| `POST /api/v1/early-access` | Public signup | GET list **405** (no public list) |
| `/health` `/live` `/ready` | Probes | 200 JSON |
| `/demo` | Unlinked | **Unlinked from EA chrome; GET still 200 if guessed** |
| `/search` | Hidden from EA | **Unlinked; GET 303 → `/results/headphones-standard` if guessed** |
| Operator export | Private CLI | `GET /api/v1/early-access/export` 404/405; `scripts/export_early_access.py` only |
| Launch config export | Admin | `GET /api/v1/launch/config/exports` **401** without bearer |

Residual owner decision (not product rework in this PR): accept guessable `/demo` and `/search` on `piqsavi.com`, or authorize a separate disable before DNS.

Affiliate tracking/monetization: EA page has no affiliate query params; staging `non_essential_tracking_allowed=false`. Keep off.

## 12. Post-cutover smoke plan (do not run on production yet)

Use a dedicated removable address such as `qa-early-access-prod-cutover-20260911@piqsavi.com` (or another clearly synthetic mailbox). Export/delete later via private CLI.

1. `GET https://piqsavi.com/` → 200, approved desktop/mobile Early Access, not the current static page.
2. `GET /privacy` → 200 `privacy-2026-09-11`; `GET /terms` → 200 `terms-2026-09-11`; footer links work.
3. Acknowledgement checkbox unchecked by default; submit without it rejected; with it succeeds; duplicate returns already-registered copy.
4. If safe: restart/redeploy and confirm the smoke row still exists (RDS).
5. No shopping chrome; no `/demo` link; no affiliate tracking.
6. `GET /health` `/live` `/ready` 200 over HTTPS; ALB target healthy.

## 13. External dependency reconciliation

Statuses **not** advanced to provisioned/approved from this audit:

| ID | Status after this audit | Evidence |
|----|-------------------------|----------|
| EXT-10 | `approved` (ownership) | Unchanged |
| EXT-11 | `not_started` | Apex still Cloudflare static, not ALB |
| EXT-12 | `not_started` | No production ALB ACM/HTTPS redirect |
| EXT-13 | Partial TF only; not applied | Confirmed; AWS inventory not run; app not live |
| EXT-14 | `not_started` | No production secret values |
| EXT-16 / EXT-24 | `not_started` | No error-tracking / paging |
| EXT-20 / EXT-21 | `applied` | Staging live `/privacy` `/terms` 200 on Deploy Staging #35; **production live URL remains cutover** |
| EXT-07 / EXT-01 / merchants | Unchanged | No shopping/affiliate activation |

Not public-beta ready. Not merchant-complete.

## Exact remaining blockers

1. Isolated production AWS not applied / not live (VPC, ALB, TG, EC2 Compose host, RDS, IAM, secrets containers).
2. No production deploy workflow; host assembler is staging-only; tests currently forbid `deploy-production.yml`.
3. GitHub Environment `production` does not exist (no approval gate, no OIDC subject).
4. Production secrets not populated (`APP_SECRET_KEY`, `cors_origins`, `ghcr_pull`, RDS URL assembly, and Resend key required to **boot** this image).
5. `piqsavi.com` does not route to the PiqSavi app (Cloudflare static placeholder).
6. Production ALB TLS + HTTP→HTTPS not applied.
7. No durable production store for Early Access signups (no production RDS) — **data-loss blocker** if launched on ephemeral disk/memory.
8. No production backup/restore procedure and **no restore rehearsal**.
9. No production rollback workflow; first cutover rollback is DNS revert only.
10. No production log retention, alerts, or paging (EXT-24).
11. Owner has not authorized public-facing production actions.

Non-blockers if owner accepts: in-process rate limit on a **single** host; guessable `/demo` and `/search` remaining unlinked.

## Confirmations

- No production deployment occurred.
- No DNS change occurred.
- No merge occurred.
- No shopping / merchant / affiliate activation occurred.
- No production workflow was created.
