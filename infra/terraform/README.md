# DealBrain Terraform — Sprint 25a foundation + 25b.2 OIDC/IAM + 25b.3 staging deploy + 25b.4b backend

## Structure

```
infra/terraform/
  account/                 # Sprint 25b.2 — GitHub Actions OIDC provider (once)
  modules/
    networking/
    security_groups/
    alb/
    ec2/
    rds/
    secrets/               # + ghcr_pull container (25b.2)
    iam/                   # + SSM core (25b.2) + staging S3 GetObject (25b.3)
    github_oidc/           # Sprint 25b.2
    github_deploy_role/    # Sprint 25b.2 (+ staging S3/SSM wiring in 25b.3)
    release_artifacts/     # Sprint 25b.3 — staging-only release/evidence bucket
    ssm_deploy_document/   # Sprint 25b.3 — DealBrain-StagingDeploy
  environments/
    staging/               # isolated staging stack + gha deploy role + 25b.3
    production/            # isolated production stack + gha deploy role
  README.md
```

This repository defines infrastructure as code only. These sprints do **not**
perform `terraform apply` unless an operator explicitly runs it.

## Prerequisites

- Terraform >= 1.11.0 (CI pins `1.15.8`)
- AWS credentials with permission to manage VPC/EC2/RDS/ALB/IAM/Secrets Manager/OIDC/SSM/S3
- Remote state bootstrap: encrypted S3 bucket for Terraform state (separate from app secrets
  **and** separate from the staging release-artifacts bucket). Locking uses **S3 native
  lockfiles** (`use_lockfile = true`). DynamoDB lock tables are obsolete and must not be
  created for new backends.
- ACM certificate ARN (optional until TLS cutover; leave empty for HTTP bootstrap)
- GitHub repository owner/name for OIDC trust variables (25b.2); staging also
  requires numeric `github_repository_owner_id` / `github_repository_id` for the
  immutable OIDC `sub` (25b.5f; see `environments/staging/terraform.tfvars.example`)

## Remote state locking (Sprint 25b.4b)

| Concern | Current | Obsolete |
|---------|---------|----------|
| Locking | S3 native lockfiles (`use_lockfile = true`) | S3 + DynamoDB lock table |
| Roots modernized | `account/`, `environments/staging` | — |
| Production | Intentionally deferred (see below) | Commented DynamoDB-era backend remains until production rollout |

## Backend initialization

`account/` and `environments/staging` declare a **partial** S3 backend:

```hcl
backend "s3" {
  use_lockfile = true
}
```

`bucket`, `key`, and `region` are supplied at `terraform init` time via `-backend-config`.
Do **not** commit real bucket names or account-specific values into the repository.

### Account backend

```bash
cd infra/terraform/account
cp terraform.tfvars.example terraform.tfvars   # if needed
terraform init \
  -backend-config="bucket=dealbrain-terraform-state-<ACCOUNT_OR_SUFFIX>" \
  -backend-config="key=account/terraform.tfstate" \
  -backend-config="region=us-east-1"
terraform validate
# Operator only: terraform apply
```

### Staging backend

```bash
cd infra/terraform/environments/staging
cp terraform.tfvars.example terraform.tfvars
# Set github_oidc_provider_arn from account output
# Do NOT set a database password or GHCR token
terraform init \
  -backend-config="bucket=dealbrain-terraform-state-<ACCOUNT_OR_SUFFIX>" \
  -backend-config="key=staging/terraform.tfstate" \
  -backend-config="region=us-east-1"
terraform validate
# Operator only: terraform apply
```

Use the same state bucket for account and staging with **distinct keys**. Encrypt the bucket
(SSE-S3 or SSE-KMS) out-of-band before first apply.

### Validation / CI only — `terraform init -backend=false`

```bash
terraform init -backend=false -input=false
terraform validate
```

`-backend=false` skips remote-state configuration. It is intended **only** for:

- Local schema validation
- GitHub Actions `terraform` job (fmt + validate)

It is **not** a substitute for a real backend when applying shared infrastructure.

## Production status (intentionally deferred)

Production backend modernization is **deferred** until the production rollout sprint.

| Item | Status |
|------|--------|
| `environments/production` `required_version` | Still `>= 1.5.0` |
| Production S3 backend block | Still commented (legacy DynamoDB-era comments) |
| Action this sprint | **None** — do not migrate production state or enable `use_lockfile` here |

When production is rolled out, migrate it to the same partial S3 backend pattern as staging
(`use_lockfile = true` + `-backend-config` for bucket/key/region). Until then, operators
must not assume production shares the modernized locking model.

## Apply order

1. Bootstrap the encrypted S3 state bucket out-of-band (versioning + encryption recommended)
2. **`account/`** — init with backend config, then create (or import) the single GitHub OIDC provider
3. **`environments/staging`** — init with backend config; pass `github_oidc_provider_arn` from
   the account output (or remote state)
4. **`environments/production`** — deferred backend migration; follow production rollout sprint

## Environment isolation

| Concern | Staging | Production |
|---------|---------|------------|
| VPC CIDR | 10.10.0.0/16 | 10.20.0.0/16 |
| Application secrets path | `dealbrain/staging/*` | `dealbrain/production/*` |
| GHCR pull secret | `dealbrain/staging/ghcr_pull` | `dealbrain/production/ghcr_pull` |
| RDS master secret | AWS-managed (staging instance) | Separate AWS-managed ARN |
| GHA deploy role | `dealbrain-staging-gha-deploy` | `dealbrain-production-gha-deploy` |
| OIDC subject | immutable `repo:…@owner_id/…@repo_id:environment:staging` (25b.5f) | legacy name-only `…:environment:production` until migrated |
| SSM document | `DealBrain-StagingDeploy` only | Interim `AWS-RunShellScript` (until 25b.4) |
| Release artifacts bucket | `dealbrain-staging-release-artifacts-<account>` | none (25b.3) |
| State key | `staging/terraform.tfstate` | `production/terraform.tfstate` |
| Account OIDC state | `account/terraform.tfstate` | (shared account root) |
| State locking | S3 native lockfile | Deferred (see Production status) |

## Secrets model

1. **RDS master password:** `manage_master_user_password = true`. Terraform stores
   the **secret ARN only**.
2. **Application secrets:** empty containers under `dealbrain/<env>/`.
3. **GHCR pull (25b.2):** container `ghcr_pull` only. Expected shape
   `{"username":"REPLACE_ME_OUT_OF_BAND","token":"REPLACE_ME_OUT_OF_BAND"}`.
   Classic PAT with `read:packages` only; populate out-of-band. **No**
   `aws_secretsmanager_secret_version` in Terraform.
4. **No conflicting `database_url` Terraform secret.**
5. **Runtime `DATABASE_URL`:** assembled on the staging host during deploy (25b.3).
6. **Deploy roles never read secret values** — hosts do.

## OIDC / deploy IAM (Sprint 25b.2 + 25b.3 staging refinement)

- Exactly one `aws_iam_openid_connect_provider` (account root)
- Trust pins exact repository + exact GitHub Environment name
- Staging SendCommand allowlist: custom `DealBrain-StagingDeploy` ARN only
  (`AWS-RunShellScript` removed for staging once 25b.3 is applied)
- Staging deploy role: S3 Put/Get on release + evidence prefixes
- Staging host: S3 Get on `releases/*` only
- Explicitly denied: IAM admin, PassRole, Secrets Manager values, `rds:CreateDBSnapshot`,
  opposite-environment SSM targets, Terraform state writes
- Host roles attach `AmazonSSMManagedInstanceCore`
- Host bootstrap: `infra/ec2/user_data/staging.sh` (Amazon Docker + AWS CLI/jq; Compose via signed Docker Inc plugin only — Sprint 25b.5a; no secrets). Staging submits this script as gzip-compressed `user_data_base64` (`base64gzip(file(...))`) so the EC2 raw payload stays within the 16,384-byte limit; cloud-init executes the original decompressed script (Sprint 25b.5b).

### GitHub Environment hard gates (live; not Terraform)

Roles are **not operationally approved** until:

| Environment | Deployment branches | Reviewers | Admin bypass |
|-------------|---------------------|-----------|--------------|
| `staging` | `main` only | optional | disabled or audited |
| `production` | `main` only | required | disabled or audited |

Staging Environment vars required for `deploy-staging.yml`:
`AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`.

See [docs/SPRINT_25B3_STAGING_DEPLOYMENT_IMPLEMENTATION.md](../../docs/SPRINT_25B3_STAGING_DEPLOYMENT_IMPLEMENTATION.md).

## Cost-sensitive resources

- NAT Gateway(s) — staging uses one; production defaults to one per AZ
- RDS Multi-AZ — production on; staging off
- ALB — always-on hourly cost

## Teardown cautions

- Production RDS has deletion protection and requires a final snapshot
- OIDC provider has `prevent_destroy` — import/adopt carefully
- Destroying staging/production secrets has a recovery window
- Never destroy production to "test" — use staging restore drills (Sprint 25d)
- Staging release-artifacts bucket is versioned; emptying it is operator-owned

## Deferred

- Production backend modernization (`use_lockfile` + partial S3 backend) → production rollout sprint
- Production deploy workflow / approval / snapshot gate → 25b.4
- Automated rollback → 25b.5
- CloudWatch dashboards / synthetics → 25c
- Production custom SSM document (remove RunShellScript) → with production deploy

## Validation (no apply)

```bash
terraform fmt -check -recursive infra/terraform
# for each of account, staging, production:
terraform init -backend=false && terraform validate
make validate-staging-deploy
```
