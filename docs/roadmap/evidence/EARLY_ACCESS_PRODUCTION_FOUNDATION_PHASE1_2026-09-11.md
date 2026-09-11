# Early Access production foundation — Phase 1 (2026-09-11)

**Resulting state:** `EARLY ACCESS PRODUCTION FOUNDATION PHASE 1 COMPLETE — OWNER INFRASTRUCTURE PROVISIONING REQUIRED`

**Scope:** Close foundational production blockers in **code/config only**. No public cutover.

**This PR did not:** apply production Terraform, create live RDS, deploy production, change Cloudflare/DNS/`piqsavi.com`, merge, activate merchants/affiliates, or enable analytics.

Owner-controlled next steps: GitHub Environment UI
([`../../runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md`](../../runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md)),
then owner Terraform apply, secrets population, restore rehearsal, and only later the
cutover runbook
([`../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md`](../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md)).

## Starting identities

| Item | Value |
|------|--------|
| Verified `origin/main` at branch creation | `d886409d1282b31670b09dd04dd664d0dd2edb37` |
| Feature branch | `cursor/early-access-production-foundation-phase1-24ac` |
| Locked staging SHA (unchanged; not redeployed) | `c4135859663a482b078da6959af746fd2d5dc098` |
| Locked staging digest (image pointer in TF example) | `sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa` |
| Locked staging Deploy | #35 / run `34573790133` / `rel-20260911T071047Z-c4135859663a` |
| Architecture | **EC2 Compose host + ALB + RDS** (not ECS). Images from GHCR (not ECR). Isolated production VPC `10.20.0.0/16` vs staging `10.10.0.0/16`. |

## 1. Production Terraform

`infra/terraform/environments/production/` is now a deployable root (syntax/validate), still **unapplied**.

| Resource | In-repo | Applied |
|----------|---------|---------|
| S3 backend + `use_lockfile = true` | Yes (partial backend; bucket/key at `terraform init`) | No |
| Dedicated VPC `10.20.0.0/16`, public/private subnets, NAT | Yes | No |
| Production EC2 Compose host (private, `user_data` from `infra/ec2/user_data/production.sh`) | Yes | No |
| Production ALB + target group `/ready` + optional ACM | Yes | No |
| Production RDS (see §2) | Yes | No |
| Security groups, IAM host role, OIDC `dealbrain-production-gha-deploy` | Yes | No |
| Immutable OIDC IDs `309556720` / `1314423275` | Required (no name-only `sub`) | No |
| Custom SSM `DealBrain-ProductionDeploy` / `DealBrain-ProductionRollback` | Yes — **not** `AWS-RunShellScript`, **not** staging documents | No |
| Release-artifacts bucket `dealbrain-production-release-artifacts-<account>` | Yes | No |
| Logging module (CW groups + ALB access-log bucket) | Yes | No |

Staging resources are not reused. No ECS. `alb_certificate_arn` may be empty for HTTP bootstrap; DNS remains owner-only.

## 2. Production RDS durability

Modeled (not live): encrypted storage, Multi-AZ, deletion protection, 30-day automated backups, `skip_final_snapshot=false`, `publicly_accessible=false`, private subnets.

Runtime `DATABASE_URL` is assembled on the host from the AWS-managed RDS master secret ARN + non-secret endpoint metadata. Credentials are never in Terraform variables, GitHub secrets, or workflow logs.

Application startup rejects sqlite/localhost/compose aliases in `APP_ENV=production`.

Backup/restore procedure (no rehearsal claimed):
[`../../runbooks/PRODUCTION_RDS_BACKUP_RESTORE.md`](../../runbooks/PRODUCTION_RDS_BACKUP_RESTORE.md).

## 3. Production runtime config contract

`scripts/deploy/host/assemble-runtime-env.py --environment staging|production`.

| | Staging (preserved) | Production (fail closed) |
|--|---------------------|--------------------------|
| Secrets prefix | `dealbrain/staging` only | `dealbrain/production` only |
| `APP_ENV` | `staging` | `production` |
| `PUBLIC_APP_BASE_URL` | `https://staging.piqsavi.com` | `https://piqsavi.com` |
| `TRUSTED_HOSTS` | (unchanged) | `piqsavi.com,www.piqsavi.com` |
| Legal versions | image defaults | `privacy-2026-09-11` / `terms-2026-09-11` |
| Support/privacy contacts | published HTML | written into env (`support@piqsavi.com`, `privacy@piqsavi.com`) |
| Resend | optional (`null` if missing) | required usable key |
| DB host | staging RDS | durable RDS; localhost/`postgres`/`db`/sqlite rejected |
| Secret printing | never | never |

Compose production overlay sets public URL, trusted hosts, legal version ids, and `awslogs` to `/dealbrain/production/{api,migrate}`.

## 4. Production deploy workflow

`.github/workflows/deploy-production.yml`

- `workflow_dispatch` only; GitHub Environment `production`; concurrency `production-release-mutation`
- Immutable GHCR digest from a successful **Build Image** run (no rebuild, no `docker build`)
- Exact SHA/digest/manifest relationship (same ingest contract as staging)
- OIDC only; no long-lived AWS keys; role must be `dealbrain-production-gha-deploy`
- Fail closed if instance/TG/RDS/bucket identifiers contain `staging`
- SSM `DealBrain-ProductionDeploy`; health checks before success
- Does **not** create the GitHub Environment or secrets
- Does **not** `terraform apply` or change DNS

## 5. Production rollback workflow

`.github/workflows/rollback-production.yml`

- Manual only; Environment `production`; same concurrency group as deploy
- Target is a previously `production_ok` immutable digest
- Must not modify/delete RDS; host script uses `alembic current` only
- Health verification after rollback
- Evidence schema `schemas/production-rollback-evidence.schema.json`

## 6. Logging baseline

[`../../runbooks/PRODUCTION_LOGGING.md`](../../runbooks/PRODUCTION_LOGGING.md)

CloudWatch 30-day groups + ALB S3 access logs. No product analytics. No paging (EXT-16 / EXT-24 later).

## 7. Production route hardening (`APP_ENV=production`)

| Surface | Production Early Access |
|---------|-------------------------|
| `/` `/privacy` `/terms` | Remain available |
| `POST /api/v1/early-access` | Remains available |
| `/live` `/ready` `/health` | Remain available |
| `/demo` | 303 → `/` |
| `/search` | 303 → `/` (no fixture shopping) |
| `/results/*` `/compare/*` `/why-best-piq/*` | 303 → `/` |
| Development/staging demo and fixture search | Unchanged |

## 8. GitHub Environment owner actions

[`../../runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md`](../../runbooks/GITHUB_PRODUCTION_ENVIRONMENT.md)

Create Environment `production`, restrict to `main`, required reviewer, disable admin bypass if possible, variables `AWS_ROLE_ARN` / `AWS_REGION` / `AWS_ACCOUNT_ID` / `PRODUCTION_TARGET_GROUP_ARN`. No GitHub secrets.

## Remaining blockers after this phase

1. **Owner GitHub UI:** create Environment `production` with hard gates (not done).
2. **Owner Terraform apply:** production VPC/ALB/EC2/RDS/IAM/SSM/logging/artifacts (not done).
3. **Owner secrets:** populate `dealbrain/production/*` values out-of-band (not done).
4. **ACM / TLS** for `piqsavi.com` when public traffic is intended (`alb_certificate_arn` still empty).
5. **RDS restore rehearsal** on a throwaway instance (procedure exists; not executed).
6. **Production deploy of an immutable digest** after infra is live (not done).
7. **DNS/TLS cutover** of `piqsavi.com` (EXT-11 / EXT-12) — owner only; not this phase.
8. **Alerts/paging** (EXT-16 / EXT-24) — later; logging baseline is present.
9. **Founder GO** on the cutover runbook. Cutover remains **BLOCKED** until the items above plus owner authorization.

Shopping, merchants, affiliates, and analytics stay inactive.

## Confirmations

- No Terraform apply
- No production deploy
- No DNS change
- No shopping / merchant / affiliate activation
- PR remains unmerged (owner controls merges)
