# Sprint 25a — Terraform foundation for DealBrain AWS single-region stack
#
# Structure:
#   modules/           reusable building blocks
#   environments/
#     staging/         isolated staging stack
#     production/      isolated production stack
#
# This phase defines infrastructure as code only. No AWS apply is performed
# by Sprint 25a unless an operator explicitly runs terraform apply.

## Prerequisites

- Terraform >= 1.5
- AWS credentials with permission to manage VPC/EC2/RDS/ALB/IAM/Secrets Manager
- Remote state bootstrap: S3 bucket + DynamoDB lock table (separate from app secrets)
- ACM certificate ARN (optional until TLS cutover; leave empty for HTTP bootstrap)

## Environment isolation

| Concern | Staging | Production |
|---------|---------|------------|
| VPC CIDR | 10.10.0.0/16 | 10.20.0.0/16 |
| Application secrets path | `dealbrain/staging/*` | `dealbrain/production/*` |
| RDS master secret | AWS-managed Secrets Manager ARN (staging instance) | Separate AWS-managed ARN (production instance) |
| State key | `staging/terraform.tfstate` | `production/terraform.tfstate` |
| RDS | private, backups ≥7d | private, backups ≥30d, deletion protection, Multi-AZ |
| IAM | read staging app secrets + staging RDS managed secret; deny production path | read production app secrets + production RDS managed secret; deny staging path |

## Initialize (staging example)

```bash
cd infra/terraform/environments/staging
cp terraform.tfvars.example terraform.tfvars
# Edit backend block in main.tf after remote-state bootstrap
# Do NOT set a database password — AWS manages the RDS master credential.
terraform init
terraform fmt -check -recursive ../..
terraform validate
terraform plan
```

Repeat for `environments/production` with a **separate** state key and VPC. Staging and
production each receive their own AWS-managed RDS master secret ARN.

## Secrets model

1. **RDS master password:** `manage_master_user_password = true`. AWS generates the
   credential and stores it in Secrets Manager. Terraform stores configuration and the
   **secret ARN only** — never the plaintext password. There is no `db_password`
   variable and operators must not put DB passwords in `.tfvars` or Git.
2. **Application secrets:** Terraform creates empty Secrets Manager containers under
   `dealbrain/<env>/` (`app_secret_key`, AI keys, `cors_origins`, `monitoring`).
   Values are injected out-of-band (CLI/console/CI in later phases).
3. **No conflicting `database_url` Terraform secret:** a manually managed
   `database_url` container is intentionally omitted so it cannot drift from the
   AWS-managed RDS credential.
4. **Runtime `DATABASE_URL` (Sprint 25b):** deploy automation assembles
   `postgresql+asyncpg://{user}:{password}@{rds_endpoint}:5432/{db}` by reading the
   AWS-managed secret JSON (`username` / `password`) plus Terraform outputs
   (`rds_endpoint`, `rds_db_name`) and injects the DSN into Compose env. The password
   never enters Terraform state; assembly happens at deploy/start time only.
5. **Rotation:** rotate via AWS RDS / Secrets Manager; restart Compose — no image rebuild.

## Cost-sensitive resources

- NAT Gateway(s) — staging uses one; production defaults to one per AZ
- RDS Multi-AZ — production on; staging off
- ALB — always-on hourly cost

## Teardown cautions

- Production RDS has deletion protection and requires a final snapshot
- Destroying staging/production secrets has a recovery window
- Never destroy production to "test" — use staging restore drills (Sprint 25d)

## Deferred

CI apply, DNS cutover, CloudWatch dashboards, synthetics, deploy workflows → Sprint 25b–25e.
