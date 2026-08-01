# Sprint 25b.4c — Staging Infrastructure Provisioning Report

**Status:** Staging AWS infrastructure provisioned; **application deploy not performed**  
**Branch:** `sprint-25b4c`  
**Account:** `941035169846`  
**Region:** `us-east-1`  
**Operator date:** 2026-08-01

## Scope completed

| Step | Result |
|------|--------|
| Terraform init (remote S3 backend + `use_lockfile`) | Done — account + staging |
| Apply account stack (saved plan) | Done — GitHub OIDC provider |
| Apply staging stack (saved plans) | Done — after free-plan sizing + SG ASCII fix |
| GitHub Environment `staging` | Done — `main` only + required vars |
| Verify SSM / RDS / ALB / outputs | Done (see Validation) |
| Deploy DealBrain application | **Stopped** (out of scope) |

Production was not touched. No production VPC/RDS/ALB resources exist in this account.

## Backend

| Root | Bucket | Key | Locking |
|------|--------|-----|---------|
| `infra/terraform/account` | `dealbrain-terraform-state-941035169846` | `account/terraform.tfstate` | S3 native lockfile |
| `infra/terraform/environments/staging` | `dealbrain-terraform-state-941035169846` | `staging/terraform.tfstate` | S3 native lockfile |

State bucket: SSE-S3 encrypted, versioning enabled (bootstrapped out-of-band prior to this sprint).

## Resources created

### Account stack (1)

- `aws_iam_openid_connect_provider` — `arn:aws:iam::941035169846:oidc-provider/token.actions.githubusercontent.com`

### Staging stack (selected)

| Component | Identifier |
|-----------|------------|
| VPC | `vpc-07605e3f3e54ba417` (`10.10.0.0/16`) |
| Public subnets | `subnet-0211155ee10dfac79`, `subnet-01b40578d6886ebec` |
| Private subnets | `subnet-033f9e687f216a76f`, `subnet-023e6fe823bb44940` |
| NAT Gateway | `nat-0bbb85ad5eaa6f0e9` (single) |
| ALB | `dealbrain-staging-alb` — active |
| Target group | `dealbrain-staging-api` |
| EC2 API host | `i-0d09a608f9c776b8c` (`t3.small`, private IP `10.10.10.221`) |
| RDS PostgreSQL | `dealbrain-staging-postgres` — **available** |
| Release artifacts bucket | `dealbrain-staging-release-artifacts-941035169846` |
| SSM document | `DealBrain-StagingDeploy` |
| GHA deploy role | `dealbrain-staging-gha-deploy` |
| API host role / profile | `dealbrain-staging-api-host` |
| Secrets Manager containers | `dealbrain/staging/*` (empty values; GHCR pull included) |

Terraform staging state: **no drift** after final apply (`terraform plan` clean).

## Validation results

| Check | Result | Evidence |
|-------|--------|----------|
| EC2 running | **PASS** | `i-0d09a608f9c776b8c` state `running` |
| SSM Online | **PASS** | `PingStatus=Online`, Agent `3.3.4624.0` |
| RDS available | **PASS** | `DBInstanceStatus=available`, endpoint live |
| ALB active | **PASS** | Load balancer `State=active` |
| ALB target healthy | **EXPECTED FAIL** | Target `unhealthy` / HTTP `502` — no app container yet |
| Required TF outputs | **PASS** | All staging outputs present (see below) |
| Host `bootstrap.ok` | **FAIL** | `/opt/dealbrain/bootstrap.ok` missing (user_data aborted) |
| Secrets populated | **NOT DONE** | Containers only; values out-of-band |
| App deploy | **NOT DONE** | Explicit stop |

### Bootstrap failure detail

Initial `user_data` aborted on AL2023 package conflict:

`curl` (requested) vs preinstalled `curl-minimal`.

Directories under `/opt/dealbrain` were created; Docker/AWS CLI are present via partial install, but entrypoint scripts and `bootstrap.ok` were never written. Deploy entrypoint refuses to run without `bootstrap.ok`.

**Repo fix applied (not yet on the live instance):** remove `curl` from `infra/ec2/user_data/staging.sh` package list. EC2 recreate / re-bootstrap was not applied (operator skipped instance replace).

## Outputs (non-secret)

### Account

| Output | Value |
|--------|-------|
| `oidc_provider_arn` | `arn:aws:iam::941035169846:oidc-provider/token.actions.githubusercontent.com` |
| `oidc_provider_url` | `https://token.actions.githubusercontent.com` |

### Staging

| Output | Value |
|--------|-------|
| `environment` | `staging` |
| `aws_region` | `us-east-1` |
| `vpc_id` | `vpc-07605e3f3e54ba417` |
| `alb_dns_name` | `dealbrain-staging-alb-1595747404.us-east-1.elb.amazonaws.com` |
| `alb_target_group_arn` | `arn:aws:elasticloadbalancing:us-east-1:941035169846:targetgroup/dealbrain-staging-api/abcb960a806a8f3d` |
| `api_instance_id` | `i-0d09a608f9c776b8c` |
| `api_private_ip` | `10.10.10.221` |
| `rds_endpoint` | `dealbrain-staging-postgres.c4fm2y4uucmx.us-east-1.rds.amazonaws.com` |
| `rds_port` | `5432` |
| `rds_db_name` | `dealbrain` |
| `gha_deploy_role_arn` | `arn:aws:iam::941035169846:role/dealbrain-staging-gha-deploy` |
| `gha_deploy_role_name` | `dealbrain-staging-gha-deploy` |
| `release_artifacts_bucket_name` | `dealbrain-staging-release-artifacts-941035169846` |
| `ssm_deploy_document_name` | `DealBrain-StagingDeploy` |
| `secrets_path_prefix` | `dealbrain/staging/*` |

Sensitive outputs present in state (not printed): `rds_master_user_secret_arn`, `secret_arns`.

## GitHub Environment `staging`

| Setting | Value |
|---------|-------|
| Name | `staging` |
| Deployment branches | `main` only (custom branch policy) |
| `AWS_ROLE_ARN` | `arn:aws:iam::941035169846:role/dealbrain-staging-gha-deploy` |
| `AWS_REGION` | `us-east-1` |
| `AWS_ACCOUNT_ID` | `941035169846` |
| `STAGING_TARGET_GROUP_ARN` | `arn:aws:elasticloadbalancing:us-east-1:941035169846:targetgroup/dealbrain-staging-api/abcb960a806a8f3d` |

## Operator deviations (local `terraform.tfvars` only)

AWS Free Plan blocked the example sizing. Local staging tfvars (gitignored) were adjusted:

| Setting | Example / default | Live staging |
|---------|-------------------|--------------|
| `rds_instance_class` | `db.t4g.small` | `db.t4g.micro` |
| `rds_allocated_storage` | `30` | `20` |
| `rds_max_allocated_storage` | `100` | `20` |
| `backup_retention_days` | `7` | `1` |

## Repo fixes required during provisioning

1. **Security group descriptions** — replaced Unicode em dashes with ASCII `-` in `infra/terraform/modules/security_groups/main.tf` (AWS rejects non-ASCII `GroupDescription`).
2. **Staging user_data** — removed conflicting `curl` package install in `infra/ec2/user_data/staging.sh` (not yet applied to running instance).

## Remaining blockers (before first Deploy Staging)

1. **Complete host bootstrap** — recreate EC2 (preferred, picks up fixed user_data) or finish bootstrap on-instance so `/opt/dealbrain/bootstrap.ok` and `/opt/dealbrain/bin/dealbrain-staging-deploy.sh` exist.
2. **Populate Secrets Manager values** out-of-band (`app_secret_key`, `cors_origins`, AI keys as needed, `ghcr_pull` classic PAT with `read:packages` only). Never put values in Terraform or GitHub secrets.
3. **Successful image build on `main`** — note `build_workflow_run_id` for deploy dispatch.
4. **ALB target health** — will remain unhealthy until first digest deploy brings up the API on `:8000`.
5. **Optional:** upgrade AWS account off Free Plan if staging must use `db.t4g.small` / 7-day backups as originally modeled.

## Explicit stop

DealBrain application deploy (**Deploy Staging** workflow / SSM `DealBrain-StagingDeploy`) was **not** executed.
