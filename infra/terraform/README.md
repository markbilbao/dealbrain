# DealBrain Terraform — Sprint 25a foundation + 25b.2 OIDC/IAM + 25b.3 staging deploy

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

- Terraform >= 1.5
- AWS credentials with permission to manage VPC/EC2/RDS/ALB/IAM/Secrets Manager/OIDC/SSM/S3
- Remote state bootstrap: S3 bucket + DynamoDB lock table (separate from app secrets **and**
  separate from the staging release-artifacts bucket)
- ACM certificate ARN (optional until TLS cutover; leave empty for HTTP bootstrap)
- GitHub repository owner/name for OIDC trust variables (25b.2)

## Apply order

1. Bootstrap remote state out-of-band  
2. **`account/`** — create (or import) the single GitHub OIDC provider  
3. **`environments/staging`** and **`environments/production`** — pass
   `github_oidc_provider_arn` from the account output (or remote state)

## Environment isolation

| Concern | Staging | Production |
|---------|---------|------------|
| VPC CIDR | 10.10.0.0/16 | 10.20.0.0/16 |
| Application secrets path | `dealbrain/staging/*` | `dealbrain/production/*` |
| GHCR pull secret | `dealbrain/staging/ghcr_pull` | `dealbrain/production/ghcr_pull` |
| RDS master secret | AWS-managed (staging instance) | Separate AWS-managed ARN |
| GHA deploy role | `dealbrain-staging-gha-deploy` | `dealbrain-production-gha-deploy` |
| OIDC subject | `…:environment:staging` | `…:environment:production` |
| SSM document | `DealBrain-StagingDeploy` only | Interim `AWS-RunShellScript` (until 25b.4) |
| Release artifacts bucket | `dealbrain-staging-release-artifacts-<account>` | none (25b.3) |
| State key | `staging/terraform.tfstate` | `production/terraform.tfstate` |
| Account OIDC state | `account/terraform.tfstate` | (shared account root) |

## Initialize (account then staging example)

```bash
cd infra/terraform/account
cp terraform.tfvars.example terraform.tfvars
terraform init -backend=false   # or uncomment backend after bootstrap
terraform validate
# Operator only: terraform apply

cd ../environments/staging
cp terraform.tfvars.example terraform.tfvars
# Set github_oidc_provider_arn from account output
# Do NOT set a database password or GHCR token
terraform init -backend=false
terraform validate
```

Repeat for `environments/production` with a **separate** state key and VPC.

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
- Host bootstrap: `infra/ec2/user_data/staging.sh` (Docker/Compose/AWS CLI/jq; no secrets)

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
