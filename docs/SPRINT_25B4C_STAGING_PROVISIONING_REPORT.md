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
| Apply staging stack (saved plans) | Done — after free-plan sizing (operator workaround for SG descriptions; see below) |
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
| Host `bootstrap.ok` | **FAIL (live host)** | Live instance still on pre-fix user_data; see Bootstrap |
| Secrets populated | **NOT DONE** | Containers only; values out-of-band |
| App deploy | **NOT DONE** | Explicit stop |

## Bootstrap failure and Sprint 25b.4c solution

### Confirmed root cause

Amazon Linux 2023 **cannot install `docker-compose-plugin` from its default dnf repositories**. Staging `user_data` previously treated Compose as a hard bootstrap gate:

1. Attempt `dnf -y install docker-compose-plugin` when `docker compose` was missing.
2. With `set -e`, cloud-init aborted when that package was not found.
3. `/opt/dealbrain/bin/dealbrain-staging-deploy.sh` and `/opt/dealbrain/bootstrap.ok` were never written.

An earlier abort also occurred when installing the full `curl` package against preinstalled `curl-minimal`. That package conflict was removed from `user_data` as part of this sprint. The **confirmed** failure that still blocked a complete bootstrap after curl was removed is the missing Compose plugin package.

Unsigned GitHub Compose binary downloads are **forbidden** and were not used.

### Sprint 25b.4c solution (repository)

Defer Compose **out of bootstrap**. Staging user_data (as of 25b.4c):

- Installs Docker Engine and bootstrap tools from AL2023 default repos only.
- Fail-closes if Docker / awscli / jq / curl / python3 / flock / timeout are missing.
- Soft-detects Compose if already present; otherwise logs deferral and continues.
- Still creates the fixed SSM entrypoint and `/opt/dealbrain/bootstrap.ok` after bootstrap-owned checks pass.
- Does **not** install Compose via `dnf`, Docker CE third-party repos, or unsigned binaries.

`bootstrap.ok` (25b.4c meaning): Docker engine + host layout + entrypoint are ready. It does **not** mean Compose CLI is present.

### Follow-on: Sprint 25b.5a signed Compose path

**Resolved in-repo by Sprint 25b.5a.** See [`docs/SPRINT_25B5A_DOCKER_COMPOSE_PLUGIN_DESIGN.md`](SPRINT_25B5A_DOCKER_COMPOSE_PLUGIN_DESIGN.md) and `scripts/deploy/host/install-compose-plugin.sh`. Staging bootstrap now installs only `docker-compose-plugin` from Docker Inc RHEL9 stable after GPG fingerprint verification, keeps the Amazon `docker` engine, disables the third-party repo (`enabled=0` + `includepkgs`), and writes `bootstrap.ok` only after `docker compose version` succeeds. Unsigned GitHub binaries remain forbidden.

The release orchestrator (`scripts/deploy/host/dealbrain-staging-deploy.sh`) remains fail-closed as defense in depth:

```text
docker compose version >/dev/null || die "docker compose missing"
```

### Live host status

The running instance (`i-0d09a608f9c776b8c`) still has the pre-fix user_data outcome (no `bootstrap.ok`). Applying the 25b.5a script requires a clean EC2 replacement (prefer `terraform plan -replace=...`, not `taint`) under a separate approval gate. After replace + successful cloud-init, expect `bootstrap.ok`, the entrypoint, and a working `docker compose` CLI.

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

## Repo fixes included in this branch

1. **Staging user_data (`infra/ec2/user_data/staging.sh`)** — remove full `curl` package install; defer Compose out of bootstrap; keep Docker bootstrap fail-closed; still write entrypoint + `bootstrap.ok`.
2. **Tests / operator docs** — AL2023 Compose-unavailable coverage; Terraform README bootstrap note; 25b.3 architecture bootstrap wording aligned to deferred Compose; this report.

### Security group descriptions (not in this PR)

During live apply, AWS rejected non-ASCII em dashes (`—`) in security group `GroupDescription` values. Operators worked around that for the live staging apply. **That ASCII description change is not included in this PR** (no Terraform behavior change in this branch). Track separately if a future apply should carry ASCII-only descriptions in `infra/terraform/modules/security_groups/main.tf`.

## Remaining blockers (before first Deploy Staging)

1. **Replace the staging EC2 instance** with the 25b.5a user_data so `/opt/dealbrain/bootstrap.ok`, the deploy entrypoint, and signed Compose plugin exist on the live host.
2. **Signed Compose path** — implemented in-repo (25b.5a); still requires EC2 replace (blocker #1) before the live host has `docker compose`. Do **not** use unsigned GitHub binaries.
3. **Populate Secrets Manager values** out-of-band (`app_secret_key`, `cors_origins`, AI keys as needed, `ghcr_pull` classic PAT with `read:packages` only). Never put values in Terraform or GitHub secrets.
4. **Successful image build on `main`** — note `build_workflow_run_id` for deploy dispatch.
5. **ALB target health** — will remain unhealthy until first digest deploy brings up the API on `:8000`.
6. **Optional:** upgrade AWS account off Free Plan if staging must use `db.t4g.small` / 7-day backups as originally modeled.

## Explicit stop

DealBrain application deploy (**Deploy Staging** workflow / SSM `DealBrain-StagingDeploy`) was **not** executed.
