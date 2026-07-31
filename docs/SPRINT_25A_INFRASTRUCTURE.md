# Sprint 25a — Production Infrastructure Foundation

**Status:** Implemented as code (no AWS apply performed by this sprint)  
**Branch:** `sprint-25`  
**Contract:** [SPRINT_25_PRODUCTION_INFRASTRUCTURE.md](architecture/SPRINT_25_PRODUCTION_INFRASTRUCTURE.md)

## Objective

Establish the AWS + Compose + CI foundation required by later Sprint 25 phases. This phase does **not** deploy to AWS, cut over DNS, or run production traffic.

## Directory layout

```
infra/
  terraform/
    modules/           # networking, security_groups, alb, ec2, rds, secrets, iam
    environments/
      staging/
      production/
    README.md
  compose/
    docker-compose.base.yml
    docker-compose.staging.yml
    docker-compose.production.yml
    README.md
.github/workflows/ci.yml
scripts/validate_infra_25a.sh
scripts/secret_scan_25a.py
```

Root `Dockerfile` and `docker-compose.yml` remain the local/dev baseline.

## Prerequisites

- Terraform >= 1.11.0 (see Sprint 25b.4b; CI pins `1.15.8`)
- AWS account (or separate staging/prod accounts) with IAM least privilege
- Docker / Docker Compose for overlay config checks
- Remote state bootstrap: encrypted S3 bucket with **S3 native lockfiles**
  (`use_lockfile = true`). DynamoDB lock tables are obsolete (superseded by 25b.4b).
- ACM certificate ARN placeholder until TLS cutover (Sprint 25b+)

## AWS account requirements

| Item | Expectation |
|------|-------------|
| Region | Default recommendation `us-east-1` (freeze at kickoff) |
| Networking | Ability to create VPC, subnets, IGW, NAT, security groups |
| Compute | EC2 + instance profiles |
| Data | RDS PostgreSQL 16 (private); AWS-managed master password |
| Edge | ALB (+ ACM when ready) |
| Secrets | App secret containers under `dealbrain/<env>/*` + per-env RDS managed secret ARN |

## Terraform initialization

Account and staging use a **partial** S3 backend (`use_lockfile = true`). Supply
bucket/key/region at init (see [`infra/terraform/README.md`](../infra/terraform/README.md)):

```bash
cd infra/terraform/environments/staging
cp terraform.tfvars.example terraform.tfvars
# Do NOT export or set a database password — AWS manages the RDS master credential.
terraform init \
  -backend-config="bucket=dealbrain-terraform-state-<ACCOUNT_OR_SUFFIX>" \
  -backend-config="key=staging/terraform.tfstate" \
  -backend-config="region=us-east-1"
terraform validate
# Operator only: terraform plan / apply
```

Production backend modernization is **intentionally deferred** until the production
rollout sprint. For CI/schema checks only:

```bash
terraform init -backend=false && terraform validate
```

### Remote-state bootstrap assumptions

- One encrypted S3 bucket for Terraform state
- Separate state keys: `account/terraform.tfstate`, `staging/terraform.tfstate`,
  `production/terraform.tfstate` (production key when that root is modernized)
- Locking: S3 native lockfiles (`use_lockfile = true`) — **not** DynamoDB
- `terraform init -backend=false` is for validation / CI only

## Staging vs production isolation

| Dimension | Staging | Production |
|-----------|---------|------------|
| VPC CIDR | `10.10.0.0/16` | `10.20.0.0/16` |
| App secrets path | `dealbrain/staging/*` | `dealbrain/production/*` |
| RDS master secret | Distinct AWS-managed Secrets Manager ARN | Distinct AWS-managed Secrets Manager ARN |
| IAM | Read staging app + staging RDS secret; **deny** production path | Read production app + production RDS secret; **deny** staging path |
| RDS backups | ≥7 days | ≥30 days, deletion protection, Multi-AZ |
| State | Separate key / backend | Separate key / backend |

Production credentials must never be granted to staging roles or hosts.

## Variable configuration

Safe examples: `terraform.tfvars.example` in each environment. Do **not** put secrets in
`.tfvars` files that are committed. There is **no** `db_password` variable — operators
must never place RDS master passwords in Git, tfvars, or Terraform inputs.

## Secret injection model

1. RDS enables `manage_master_user_password`. AWS generates the master password and
   stores it in Secrets Manager. Terraform outputs the **secret ARN only**.
2. Terraform creates empty application Secrets Manager containers under
   `dealbrain/<env>/` (not a conflicting manually managed `database_url`).
3. Deploy host IAM may `GetSecretValue` only for its environment’s application
   secrets and that environment’s RDS managed secret ARN.
4. Compose receives env vars at start — no secrets in Git or images.
5. **Sprint 25b** assembles runtime `DATABASE_URL` from the AWS-managed secret
   (`username`/`password`) plus RDS endpoint/db name outputs, then injects it into
   Compose. The password never enters Terraform state.
6. Rotation: rotate via AWS → restart Compose; no image rebuild.

Categories: AWS-managed RDS master secret (ARN), `app_secret_key`, AI keys,
`cors_origins`, `monitoring`.

## Compose usage

```bash
export DEALBRAIN_IMAGE=ghcr.io/ORG/dealbrain@sha256:…
export DATABASE_URL=…   # assembled at deploy time (Sprint 25b); never commit
export CORS_ORIGINS=…
export APP_SECRET_KEY=…

# Migrate first (one-shot)
docker compose -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.production.yml \
  --profile migrate run --rm migrate

# Then API
docker compose -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.production.yml up -d
```

- `api` and `migrate` share the same image digest
- `api` does **not** run Alembic at startup
- No in-container Postgres — RDS only
- Container HEALTHCHECK → `/live`; ALB → `/ready`

## Security group model

- ALB SG: 80/443 from `allowed_ingress_cidrs`
- API SG: port 8000 **only** from ALB SG
- RDS SG: port 5432 **only** from API SG; **explicit empty egress** (no outbound)
- RDS `publicly_accessible = false`

## ALB `/ready` behavior

Target group health check path is fixed to `/ready` (Sprint 22 readiness). Unready targets are removed from rotation. Liveness remains Docker `/live`.

## TLS assumptions

- Public TLS terminates at the ALB (ACM certificate ARN variable)
- Empty `alb_certificate_arn` → HTTP listener only (bootstrap); HTTPS listener created when ARN is set
- App may speak HTTP to the ALB on the private path; `X-Forwarded-*` trust is an edge concern

## Production configuration gate

`run_startup_validation()` in `app/core/validation.py` is fail-closed for production:
invalid mandatory production configuration raises even if a caller forgets a separate
`is_production` check or sets `LAUNCH_STRICT_STARTUP=false`. The flag strengthens
non-production environments but cannot weaken production. Local/development remain
usable without cloud secrets. Error messages name field categories and never include
secret values. `/live` and `/ready` semantics are unchanged.

## CI (Phase 25a)

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pull requests and
pushes to `main` / `sprint-25`:

- Python deps via `uv`, Ruff lint/format via **baseline gate**
  (`scripts/check_ruff_baseline.py` + `tests/lint/baselines/ruff.baseline.json`):
  pre-existing debt is grandfathered; CI fails only on **new** lint/format regressions
- Deterministic secret scan (`scripts/secret_scan_25a.py`)
- API/OpenAPI contract tests, protected-module/architecture tests, Sprint 25a tests
- Full pytest suite
- Terraform fmt + validate (staging and production, `-backend=false`)
- Docker Compose config validation
- Docker image build validation (no deploy; **no GHCR publish** — releasable
  publication moved to `build-image.yml` in Sprint 25b.1)

CI does **not** run `terraform apply`, staging/production deploy, approval gates, or
digest promotion. See [SPRINT_25B_IMAGE_PUBLICATION.md](SPRINT_25B_IMAGE_PUBLICATION.md).

## Validation commands

```bash
chmod +x scripts/validate_infra_25a.sh
./scripts/validate_infra_25a.sh

# Or manually:
python scripts/secret_scan_25a.py
uv run python scripts/check_ruff_baseline.py
terraform fmt -check -recursive infra/terraform
(cd infra/terraform/environments/staging && terraform init -backend=false && terraform validate)
(cd infra/terraform/environments/production && terraform init -backend=false && terraform validate)
# Compose (requires Docker):
DEALBRAIN_IMAGE=ghcr.io/EXAMPLE_ORG/dealbrain:test \
DATABASE_URL=postgresql+asyncpg://u:StrongPassword12@host:5432/db \
CORS_ORIGINS=https://example.com \
docker compose -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.production.yml config

uv run pytest tests/unit/test_sprint25a_infrastructure.py -q
uv run pytest   # full suite
```

If Terraform or Docker are unavailable locally, treat CI as the required validation
evidence before merge — do not claim local validate/build passed.

## Known limitations (Sprint 25a)

- No AWS resources were applied by this change set
- Remote state backend must be bootstrapped before shared `apply`
- ACM/DNS cutover not performed
- Ruff CI uses a committed baseline (`tests/lint/baselines/ruff.baseline.json`);
  ~95 lint findings and ~90 unformatted files are grandfathered until intentionally
  ratcheted with `uv run python scripts/check_ruff_baseline.py --update`
- CloudWatch dashboards, synthetics, paging deferred
- Deploy / promote workflows deferred to Sprint 25b+
- EC2 user-data does not yet install Docker (deploy phase)
- Runtime `DATABASE_URL` assembly from the AWS-managed RDS secret is Sprint 25b

## Deferred — Sprint 25b–25e

| Phase | Focus |
|-------|-------|
| **25b** | Immutable GHCR publish via `build-image.yml` (25b.1); OIDC/IAM (25b.2); staging apply, secret population, `DATABASE_URL` assembly, Compose deploy by digest (25b.3+) |
| **25c** | CloudWatch logs/metrics/synthetics/alarms |
| **25d** | Backup restore drill, runbooks RB-01…RB-10 |
| **25e** | Production dry-run, rollback rehearsal, config-failure evidence |

## Teardown cautions

- Production RDS has deletion protection and requires a final snapshot
- Secrets have recovery windows — do not destroy casually
- Never copy unsanitized production data to staging

## Cost-sensitive resources

- NAT Gateway(s) (staging: 1; production: per-AZ by default)
- ALB hourly charge
- RDS Multi-AZ (production default)
- EC2 + EBS

## Architecture locks

Sprint 25a does not modify DealScore, Recommendation, Marketplace ranking, Shopping Assistant ranking, Personal AI, affiliate/merchant neutrality, Sprint 22 probe semantics, Sprint 23 adapters, or Sprint 24 API contracts. No `/api/v2`.
