# Early Access production — Phase 2 provisioning & private origin validation (2026-09-11)

**Resulting state:** `EARLY ACCESS PRODUCTION PROVISIONING BLOCKED — SPECIFIC ITEMS REMAIN`

**Scope:** Close live infrastructure blockers while keeping public DNS unchanged.
Private production origin validation, RDS restore rehearsal, and Deploy Production
were in scope **only after** GitHub Environment `production`, a clean production
Terraform plan/apply, secrets, and TLS prerequisites existed.

**This agent did not:** apply production Terraform, create live RDS, populate secret
values, request/issue ACM, change Cloudflare DNS for `piqsavi.com` / `www.piqsavi.com`,
dispatch Deploy Production, invite real users, merge any PR, activate merchants /
affiliates / shopping / analytics, or enable public Early Access traffic.

Owner-controlled next actions are listed in §15. Public DNS cutover still requires a
**separate owner GO** after private origin is verified.

## Starting identities

| Item | Value | How verified |
|------|-------|----------------|
| Expected `origin/main` | `37418968e23320129020015d7e70f2a883672a0b` | Task prompt |
| Verified `origin/main` after fetch | `37418968e23320129020015d7e70f2a883672a0b` | `git fetch origin main` then `git rev-parse origin/main` |
| Tip commit | `Merge pull request #134 from markbilbao/cursor/early-access-production-foundation-phase1-24ac` | `git log -1 --oneline origin/main` |
| Phase 1 evidence | [`EARLY_ACCESS_PRODUCTION_FOUNDATION_PHASE1_2026-09-11.md`](EARLY_ACCESS_PRODUCTION_FOUNDATION_PHASE1_2026-09-11.md) | Merged in PR #134 |
| Architecture | Isolated EC2 Compose host + ALB + RDS (not ECS). Images from GHCR (not ECR). Production VPC CIDR `10.20.0.0/16` vs staging `10.10.0.0/16` | In-repo Terraform + compose |
| Known AWS account (from staging apply; **not re-verified this run**) | `941035169846` / `us-east-1` | [`docs/SPRINT_25B4C_STAGING_PROVISIONING_REPORT.md`](../../../SPRINT_25B4C_STAGING_PROVISIONING_REPORT.md) |
| State bucket (documented; **not accessed this run**) | `dealbrain-terraform-state-941035169846` | Same report; production key would be `production/terraform.tfstate` |
| OIDC provider ARN (documented; **not accessed this run**) | `arn:aws:iam::941035169846:oidc-provider/token.actions.githubusercontent.com` | Same report |
| This workstation AWS | **No AWS CLI, no credentials, no IMDS role** | `aws` not installed; `env` has no `AWS_*`; IMDS `169.254.169.254` timed out |
| This workstation Terraform | **Not installed** | `terraform` not on PATH |
| CI pin Terraform version | `1.15.8` | `.github/workflows/ci.yml` `TERRAFORM_VERSION` |
| CI (this SHA) | run `34580625340` **success** | `gh run view` |
| Build Image (this SHA) | run `34581089637` **success** | `gh run view` |
| Release ID | `rel-20260911T084953Z-37418968e233` | Build Image manifest |
| Production image digest | `sha256:b8fd76d2e4ff69f94568097790a1dae5dd9de6ea598c6ae81d0ed001fb9f19e4` | Build Image GHCR publish; **not deployed** |

CI and Build Image for this SHA completed successfully during this phase (see §9).
That image was **not** deployed to production.

## 1. GitHub Environment `production`

Inspected with `gh api` (read-only). **Environment does not exist.**

| Check | Result |
|-------|--------|
| `GET /repos/markbilbao/dealbrain/environments` | `total_count: 1`; only `staging` |
| `GET /repos/markbilbao/dealbrain/environments/production` | **404 Not Found** |
| `staging` branch policy | Custom policy **`main` only** |
| `staging` required reviewers | **None** (`protection_rules` is branch_policy only) |
| `staging` `can_admins_bypass` | `true` |
| Staging environment variables / secrets list | **403** `Resource not accessible by integration` (values not read) |
| This token environment write | **Cannot create or configure.** `gh` is read-only for this agent. Repo `permissions.admin` reported `false`. Creating an Environment requires repository Administration. |
| Long-lived AWS keys on GitHub | **Not created.** Do not add `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`. |
| Required production variables | Names known; **values not invented.** `AWS_ROLE_ARN` and `PRODUCTION_TARGET_GROUP_ARN` do not exist until production Terraform apply. `AWS_REGION` is the frozen `us-east-1`. `AWS_ACCOUNT_ID` is the documented account `941035169846` only after the owner confirms that is still the production account. |
| Required reviewers | Repository owner type is **User** (`markbilbao`); repo is **public**. GitHub environment required reviewers are available on public repositories. This agent cannot enable them. |
| Admin bypass | Must be disabled in the GitHub UI when the control is offered. |

**Stop for this item.** Owner must create and gate the Environment in the GitHub UI.
Workflows and Terraform do not create it.

### Exact owner GitHub UI steps

Repository: `markbilbao/dealbrain`.
Runbook: [`../../runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md`](../../runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md).

1. Open [Settings → Environments → New environment](https://github.com/markbilbao/dealbrain/settings/environments/new).
2. Name it exactly `production` (lowercase). Save.
3. **Deployment branches and tags:** Selected branches / custom policy → **`main` only**. Do not allow all branches.
4. **Required reviewers:** enable. Add at least one human owner (not an unattended bot). Enable **prevent self-review** if shown.
5. **Allow administrators to bypass configured protection rules:** **disable**. If org/user policy forces bypass on, record a written audit exception — do not treat that as equivalent to required reviewers.
6. Wait timer: optional. Not required for this phase.
7. **Do not add Environment secrets.** No `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, Resend keys, GHCR tokens, or `APP_SECRET_KEY`.
8. Environment **variables** (non-secret). Fill `AWS_REGION` / `AWS_ACCOUNT_ID` only when the owner confirms the account. Fill the two ARNs **only after** production Terraform apply outputs exist — do not paste staging ARNs:

   | Name | Source after owner apply | Do not use |
   |------|--------------------------|------------|
   | `AWS_ROLE_ARN` | Terraform output `gha_deploy_role_arn` (`dealbrain-production-gha-deploy`) | `dealbrain-staging-gha-deploy` |
   | `AWS_REGION` | `us-east-1` | other regions |
   | `AWS_ACCOUNT_ID` | Twelve-digit production account (documented staging account `941035169846` if still correct) | invented ids |
   | `PRODUCTION_TARGET_GROUP_ARN` | Terraform output `alb_target_group_arn` | `STAGING_TARGET_GROUP_ARN` / `dealbrain-staging-api` |

9. Confirm the Environment is not named `prod`, `Production`, or `live`. OIDC trust is `repo:markbilbao@309556720/dealbrain@1314423275:environment:production`.
10. Confirm **Deploy Production** and **Rollback Production** remain `workflow_dispatch` on `refs/heads/main` only.

Until this Environment exists with those gates and (after apply) the four variables, Deploy Production / Rollback Production cannot assume `dealbrain-production-gha-deploy`.

## 2. Terraform plan

**Live `terraform plan` against AWS was not executed.**

| Gate | Result |
|------|--------|
| Initialize production backend `dealbrain-terraform-state-941035169846` / `production/terraform.tfstate` | **Blocked** — no AWS credentials; AWS CLI absent |
| `terraform plan` | **Not run** |
| Plan ID | **None** |
| Destructive / cross-environment inspection | **Not performed** (no plan output) |
| Only `dealbrain-production-*` targeted | In-repo root uses `name_prefix = dealbrain-production` and VPC `10.20.0.0/16`. **Not proven against live state.** |
| Staging resources unmodified | Cannot prove without a live plan. Staging state key is `staging/terraform.tfstate` (separate). |
| Unexpected deletion/replacement | **STOP** — no plan to inspect; apply forbidden |

CI job **Terraform fmt and validate** on this SHA **succeeded** (`terraform init -backend=false` + `validate` for account, staging, and production). That is **schema validation only**. It is not a remote-state plan and must not be treated as apply authorization evidence.

In-repo production root (`infra/terraform/environments/production/`): S3 backend with `use_lockfile = true`; `bucket`/`key`/`region` supplied at init. HTTPS listener is created only when `alb_certificate_arn` is non-empty (currently empty in `terraform.tfvars.example`).

### Owner plan command (not run by this agent)

```bash
cd infra/terraform/environments/production
cp terraform.tfvars.example terraform.tfvars
# Set github_oidc_provider_arn from account output. Do NOT set a database password.
terraform init \
  -backend-config="bucket=dealbrain-terraform-state-941035169846" \
  -backend-config="key=production/terraform.tfstate" \
  -backend-config="region=us-east-1"
terraform plan -out=production.tfplan
```

Inspect the saved plan before apply. **STOP** if the plan destroys or replaces staging resources, unrelated account resources, or unexpected production resources. Apply only `dealbrain-production-*` creates/updates.

## 3. Terraform apply

This prompt authorizes **non-public** infrastructure provisioning **after a clean plan**. Public DNS remains forbidden.

**Apply was not executed** because there was no clean live plan (no AWS access).

| Record | Value |
|--------|-------|
| Terraform version (workstation) | Not installed |
| Terraform version (CI pin / intended apply) | `1.15.8` |
| Plan ID / output | None |
| Apply result | **Not run** |
| Created resource identifiers | **None this run** |

Expected identifiers **after** a future clean apply (names only; not live):

| Resource | Expected name / pattern |
|----------|-------------------------|
| VPC | `dealbrain-production` / CIDR `10.20.0.0/16` |
| ALB | `dealbrain-production-alb` |
| Target group | `dealbrain-production-api` (health `/ready`) |
| EC2 | `dealbrain-production` Compose host in a private subnet, no public IP |
| RDS | `dealbrain-production-postgres` |
| GHA role | `dealbrain-production-gha-deploy` |
| SSM documents | `DealBrain-ProductionDeploy` / `DealBrain-ProductionRollback` |
| Release artifacts | `dealbrain-production-release-artifacts-<account>` |
| ALB logs bucket | `dealbrain-production-alb-logs-<account>` |
| CW groups | `/dealbrain/production/{api,migrate,host}` |

## 4. Production RDS

**Not live.** No `describe-db-instances` was possible.

| Control | Modeled in Terraform | Verified live |
|---------|----------------------|---------------|
| Identifier | `dealbrain-production-postgres` | No |
| Encrypted storage | Yes (RDS module) | No |
| Multi-AZ | `true` (default) | No |
| Deletion protection | `true` | No |
| Automated backup retention | `30` (variable rejects `< 30`) | No |
| Publicly accessible | `false` | No |
| Production subnet group | `dealbrain-production-db` (module naming) | No |
| Production security group only | RDS SG from `dealbrain-production` module | No |
| AWS-managed master credentials | `manage_master_user_password = true`; ARN only | No |
| `DATABASE_URL` via runtime assembler | Host assembler reads RDS non-secret metadata + managed secret; rejects localhost / sqlite / compose aliases in `APP_ENV=production` | Not exercised |

Credentials were never printed.

## 5. Required production secret / config inventory

Terraform creates **empty containers** under `dealbrain/production/*` (values out-of-band; no `aws_secretsmanager_secret_version` in Terraform). Containers are not live until apply.

| Secret / config | Path or source | Required for Early Access production boot / pull? | This run |
|-----------------|----------------|--------------------------------------------------|----------|
| Application secret key | `dealbrain/production/app_secret_key` | **Yes** (≥32, non-placeholder) | Not populated (containers not created) |
| CORS / origin | `dealbrain/production/cors_origins` | **Yes** — intended value `https://piqsavi.com` (non-empty, not `*`) | Not populated |
| GHCR pull | `dealbrain/production/ghcr_pull` | **Yes to pull the image** — JSON `{"username","token"}` classic PAT `read:packages` only | Not populated |
| Resend API key | `dealbrain/production/resend_api_key` | **Yes to boot** this image (`APP_ENV=production` fail-closed) | Not populated. Does **not** by itself prove production email is live |
| RDS master | AWS-managed secret ARN on the RDS instance | **Yes** — host assembles `DATABASE_URL`; never GitHub / TF variables | Not created |
| Public base URL | Assembler hardcodes `https://piqsavi.com` | Yes | Code only |
| Trusted hosts | Assembler hardcodes `piqsavi.com,www.piqsavi.com` | Yes | Code only |
| Legal versions | Assembler `privacy-2026-09-11` / `terms-2026-09-11` | Yes | Code only |
| Support / privacy contacts | Assembler `support@piqsavi.com` / `privacy@piqsavi.com` (EXT-17 / EXT-18 inboxes already provisioned) | Written into env; not Secrets Manager | Code only |
| `TRANSACTIONAL_EMAIL_FROM` | Assembler `no-reply@piqsavi.com` | Yes with Resend gate | Code only |
| `openai_api_key` / `anthropic_api_key` / `gemini_api_key` | Optional leaves | **No** unless live AI HTTP flags are on (defaults off) | **Not populated; not required** |
| `monitoring` | Optional leaf | **No** for Early Access boot | Not populated |
| Merchant / affiliate / analytics credentials | Not in required assembler set | **No.** Startup does not require them. **Do not activate.** | Not populated |

**Architectural note (not activated):** `Settings.affiliate_enabled` and `merchant_platform_enabled` default **true** in `app/core/config.py`. Production compose overlay and the host assembler do **not** currently set them false. Production HTML shopping surfaces (`/demo`, `/search`, `/results/*`, `/compare/*`, `/why-best-piq/*`) fail closed via `unfinished_html_surfaces_enabled()`. Startup validation does **not** require merchant/affiliate/analytics credentials. Do **not** add those credentials to “make boot work.” Prefer a later explicit `AFFILIATE_ENABLED=false` / `MERCHANT_PLATFORM_ENABLED=false` in the production assembler if the owner wants belt-and-suspenders API disablement.

Populate secrets only through AWS Secrets Manager (CLI/console), never GitHub, never Terraform state on purpose. Do not print values.

## 6. ACM / TLS without public cutover

| Check | Result |
|-------|--------|
| Production ACM certificate | **Not requested** (no AWS) |
| Coverage required | `piqsavi.com` and `www.piqsavi.com` (`TRUSTED_HOSTS`) |
| DNS validation records | **Unknown until** `acm request-certificate`. Adding those CNAMEs is **not** traffic cutover, but DNS mutation is owner-controlled |
| Apex / www traffic records | **Unchanged** (see §14) |
| Production ALB HTTPS listener | Terraform creates it only when `alb_certificate_arn != ""`. Example tfvars still empty → HTTP-only bootstrap if applied as-is |
| HTTP→HTTPS redirect | Same gate (`enable_http_redirect` + non-empty certificate) |
| Staging certificate reuse | Must not set production `alb_certificate_arn` to the staging `staging.piqsavi.com` cert |

### Exact owner ACM steps (stop for DNS mutation)

1. In `us-east-1` (ALB region): request a certificate for `piqsavi.com` with SAN `www.piqsavi.com`, validation method **DNS**.
2. Copy the two ACM-provided CNAME name/value pairs. **Do not invent them.**
3. In Cloudflare, add **only** those ACM validation CNAMEs. Do **not** change apex A/AAAA, `www`, or `staging` traffic records.
4. Wait until ACM status is **Issued**.
5. Set production `alb_certificate_arn` to that ARN and apply (or a follow-up apply if the first apply was HTTP bootstrap).
6. Verify HTTPS listener + HTTP→HTTPS redirect on the **production ALB hostname**, not `piqsavi.com`.

## 7. Logging

| Stream | Modeled | Verified live |
|--------|---------|---------------|
| `/dealbrain/production/api` | CW group, 30-day retention | No |
| `/dealbrain/production/migrate` | CW group, 30-day retention | No |
| `/dealbrain/production/host` | CW group provisioned; host agent **not** installed this phase (disk `/var/log/dealbrain/` on EBS) | No |
| ALB access logs | `s3://dealbrain-production-alb-logs-<account>/alb/AWSLogs/<account>/`, 30-day lifecycle | No |
| Release/deploy evidence | `s3://dealbrain-production-release-artifacts-<account>/evidence/<release_id>/<run_id>/` | No |
| Alerts / paging (EXT-16 / EXT-24) | **Not configured.** Do not claim paging. | n/a |

## 8. Backup / restore rehearsal

Procedure: [`../../runbooks/PRODUCTION_RDS_BACKUP_RESTORE.md`](../../runbooks/PRODUCTION_RDS_BACKUP_RESTORE.md).

| Item | Status |
|------|--------|
| Manual snapshot of `dealbrain-production-postgres` | **Not possible** — instance does not exist / no AWS |
| Restore to `dealbrain-production-restore-rehearsal` | Not run |
| Connectivity / Early Access schema check | Not run |
| Destroy throwaway restore instance | n/a |
| Snapshot / restored-instance identifiers | **None** |
| Remaining blocker | **Yes** — cost is not the issue; **AWS credentials and a live production RDS** are |

Primary production DB was not touched (it does not exist).

## 9. Build / image selection

Do **not** reuse the pre-Phase-1 staging digest as production authority. Current `main` is the Phase 1 merge SHA, which is **not** `c4135859663a482b078da6959af746fd2d5dc098`.

Locked **staging** digest (still valid for staging only; **not** this production SHA):

| Staging lock (unchanged; not redeployed this phase) | Value |
|-----------------------------------------------------|-------|
| SHA | `c4135859663a482b078da6959af746fd2d5dc098` |
| Digest | `sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa` |
| Build Image | `34573165486` |
| Deploy Staging | #35 / `34573790133` |

### Current main (`37418968e23320129020015d7e70f2a883672a0b`)

| Workflow | Identity | Status |
|----------|----------|--------|
| CI | run `34580625340` | **success** (push on `main`). URL: https://github.com/markbilbao/dealbrain/actions/runs/34580625340 |
| Build Image | run `34581089637` | **success** (`workflow_run` after CI). URL: https://github.com/markbilbao/dealbrain/actions/runs/34581089637 |
| Release ID | `rel-20260911T084953Z-37418968e233` | Manifest artifact `release-manifest-rel-20260911T084953Z-37418968e233` |
| Image repository | `ghcr.io/markbilbao/dealbrain` | Not ECR |
| Image digest (deploy authority) | `sha256:b8fd76d2e4ff69f94568097790a1dae5dd9de6ea598c6ae81d0ed001fb9f19e4` | GHCR publish + digest verify in Build Image logs |
| Immutable tag (pointer only) | `ghcr.io/markbilbao/dealbrain:sha-37418968e23320129020015d7e70f2a883672a0b` | Not deployment authority |
| Manifest SHA-256 | `a20250ed9d9f88659b56ca22ee4fda4a26a9cf499402d3a8f8688da905303a00` | Build Image “Create release manifest” step |

Production must deploy **this** digest, not the older staging digest `sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa`. Image selection is ready. Private Deploy Production is still blocked on Environment + AWS infra + secrets (§10).

## 10. Private production deploy

**Not executed.**

Prerequisites missing: GitHub Environment `production`, production AWS stack, secrets, (recommended) issued ACM. CI + Build Image for this SHA **are ready** (§9). Dispatch input would be `build_workflow_run_id=34581089637` (optional `release_id=rel-20260911T084953Z-37418968e233`). **Not dispatched.**

| Check | Result |
|-------|--------|
| Deploy Production workflow | Exists: `.github/workflows/deploy-production.yml` (`workflow_dispatch`, `environment: production`, concurrency `production-release-mutation`) |
| Dispatch | **Not dispatched** |
| Targets production only | Workflow fail-closes if identifiers contain `staging`; role must be `dealbrain-production-gha-deploy` |
| Migrations / host assembly / ALB health / `/live` `/ready` `/health` | Not exercised |

## 11. Private origin testing

**Not executed** — no production ALB origin.

Public apex was probed **read-only** to confirm it is still the static placeholder (not the app). That is **not** private origin validation.

## 12. Data durability / restart test

**Not executed** — no production RDS and no production app container.

## 13. Rollback rehearsal

**Not executed.** There is **no prior production release** to roll back to. Workflow `.github/workflows/rollback-production.yml` exists (manual, Environment `production`, same concurrency group, must not modify RDS). Mechanics were not dispatched. Do not fabricate `rollback_ok`.

Limitation: first production deploy has no previous `production_ok` digest. A true rollback rehearsal requires two successful production deploys (or an owner-approved substitute). Documented only.

## 14. Public DNS — not cut over

Read-only DNS/HTTP at 2026-09-11 (this run). **No Cloudflare changes were made.**

| Name | Observed | Meaning |
|------|----------|---------|
| `piqsavi.com` A | `104.21.66.117`, `172.67.159.152` | Cloudflare-proxied static/placeholder (unchanged vs cutover-readiness audit) |
| `piqsavi.com` NS | `elisabeth.ns.cloudflare.com`, `dilbert.ns.cloudflare.com` | Cloudflare |
| `www.piqsavi.com` A | same Cloudflare anycast | Unchanged |
| `staging.piqsavi.com` CNAME | `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com` | Staging only; not production |
| `https://piqsavi.com/` | 200 HTML static “PiqSavi — Your AI Personal Shopper” | Not the production ALB app |
| `https://piqsavi.com/privacy` | **404** | App legal pages not public |
| `https://piqsavi.com/terms` | **404** | Same |
| `https://piqsavi.com/health` | **404** | Same |

`piqsavi.com` must remain on this static/placeholder target until a **separate owner GO**. Production origin may later be privately healthy without being public.

## 15. Remaining blockers

1. **Owner GitHub UI:** create Environment `production` with `main`-only deployments, required reviewer, admin bypass disabled, no long-lived AWS keys. Add the four variables after Terraform outputs exist.
2. **AWS credentials / operator access** for this (or a follow-on) apply path. This Cloud Agent workstation cannot talk to AWS.
3. **Live `terraform plan`** of `infra/terraform/environments/production` against `production/terraform.tfstate`. STOP if unexpected destroys/replacements.
4. **Owner `terraform apply`** of that clean plan (non-public infra only).
5. **Populate** required `dealbrain/production/*` values (app secret, CORS, GHCR pull, Resend) plus confirm RDS managed secret exists. Never print values. Do not add merchant/affiliate/AI/analytics keys for boot.
6. **ACM DNS validation** (owner adds Cloudflare CNAMEs only) and production ALB HTTPS listener + HTTP→HTTPS redirect. Do not repoint apex/www.
7. **Live logging proof:** CW groups + ALB log bucket + release-artifacts bucket.
8. **RDS backup/restore rehearsal** on a throwaway instance; destroy the throwaway; never delete `dealbrain-production-postgres`.
9. **Private Deploy Production** of digest `sha256:b8fd76d2e4ff69f94568097790a1dae5dd9de6ea598c6ae81d0ed001fb9f19e4` (Build Image `34581089637`, release `rel-20260911T084953Z-37418968e233`). Do **not** deploy the older staging digest. Dispatch only after Environment + infra + secrets exist. ALB healthy; `/live` `/ready` `/health` (`environment=production`).
10. **Private origin functional tests** (Host/SNI to ALB): `/` `/privacy` `/terms`, registration reject/success/duplicate, no shopping chrome, `/demo` `/search` fail closed.
11. **Durability:** registration survives app/container restart without replacing RDS; duplicate detection still recognizes it.
12. **Rollback rehearsal** after a second production digest exists (or document remaining limitation).
13. **Separate owner GO** for public DNS cutover (EXT-11 / EXT-12). Not this phase.
14. Alerts/paging (EXT-16 / EXT-24) remain later; not claimed.

## Confirmations

- Public DNS for `piqsavi.com` / `www.piqsavi.com` was **not** changed
- No merchant / affiliate / shopping / analytics activation
- No public Early Access traffic was intentionally enabled
- No production Terraform apply
- No production deploy
- No PR merged by this agent
- STOP before any public DNS cutover. **OWNER MUST GIVE A SEPARATE GO.**
