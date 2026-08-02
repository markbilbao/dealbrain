# Sprint 25b.2 — AWS OIDC & Deploy IAM Implementation

**Status:** Repository implementation complete (no live AWS apply, no GitHub Environment configuration, no role assumption claimed)  
**Branch:** `sprint-25b2`  
**Architecture contract:** [SPRINT_25B2_AWS_OIDC_AND_DEPLOY_IAM.md](architecture/SPRINT_25B2_AWS_OIDC_AND_DEPLOY_IAM.md)

## Objective

Establish the **authorization foundation** for later SSM-based staging (25b.3) and production (25b.4) deploys:

- One account-level GitHub Actions OIDC provider
- Separate staging and production deploy IAM roles with exact environment-bound trust
- Least-privilege SSM orchestration permissions
- EC2 host `AmazonSSMManagedInstanceCore`
- Environment-specific GHCR pull secret **containers** (values out-of-band)

This sprint does **not** deploy DealBrain, run migrations, assemble `DATABASE_URL`, create DB snapshots, send SSM commands, or create executable deploy workflows.

## Repository vs live completeness

| Layer | Status in this sprint |
|-------|------------------------|
| Terraform + tests + docs in git | **Repository-complete** |
| `terraform apply` / live AWS resources | **Not performed** |
| GitHub Environments UI hard gates | **Documented; not configured here** |
| Role assumption / SSM SendCommand | **Not performed** |
| Hosts online in SSM | **Not claimed** |

**Terraform role creation alone does not make the roles operationally approved.**

Environment subject claims (`…:environment:staging|production`) do **not** independently encode the source branch. GitHub Environment **deployment-branch rules** are part of the live security boundary. **No workflow should use these roles until the hard gates below are verified.**

## Terraform ownership

```
infra/terraform/
  account/                      # OIDC provider only
  modules/
    github_oidc/                # aws_iam_openid_connect_provider
    github_deploy_role/         # role + trust + allow/deny
    iam/                        # + AmazonSSMManagedInstanceCore
    secrets/                    # + ghcr_pull container
  environments/staging/         # dealbrain-staging-gha-deploy
  environments/production/      # dealbrain-production-gha-deploy
```

### Apply order (operator; not run by this sprint)

1. Bootstrap remote state (encrypted S3 + native lockfiles; **not** DynamoDB) if not already done  
2. Apply `infra/terraform/account/` (partial S3 backend + `-backend-config`)  
3. Apply staging with `github_oidc_provider_arn` from account output  
4. Production backend modernization remains deferred (Sprint 25b.4b) — see [`infra/terraform/README.md`](../infra/terraform/README.md)

### OIDC import path

If the provider already exists in the account:

```bash
cd infra/terraform/account
terraform import 'module.github_oidc.aws_iam_openid_connect_provider.github[0]' \
  arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com
```

Or set `create_provider = false` and pass `existing_provider_arn`.

Staging and production roots **must not** create a second provider.

## Exact environment names

| Constant | Value |
|----------|-------|
| Staging GitHub Environment | `staging` |
| Production GitHub Environment | `production` |
| Staging deploy role | `dealbrain-staging-gha-deploy` |
| Production deploy role | `dealbrain-production-gha-deploy` |

Mandatory Terraform variables (no wildcards, no hard-coded account IDs in modules):

- `github_repository_owner`
- `github_repository_name`
- `github_oidc_provider_arn`
- Staging also: `github_repository_owner_id`, `github_repository_id` (Sprint 25b.5f)

## Trust-policy contract

Each deploy role allows only `sts:AssumeRoleWithWebIdentity` from the account OIDC provider when **all** of the following match:

| Claim | Staging (25b.5f) | Production (current) |
|-------|------------------|----------------------|
| `aud` | `sts.amazonaws.com` | `sts.amazonaws.com` |
| `sub` | `repo:markbilbao@309556720/dealbrain@1314423275:environment:staging` | `repo:<owner>/<repo>:environment:production` |
| `repository` | `<owner>/<repo>` (name-based) | `<owner>/<repo>` |

- Matching uses `StringEquals` only (no `StringLike` / wildcards on `sub`)
- Max session duration: `3600`
- No IAM user / AWS principal trust
- Staging trust cannot assume production; production trust cannot assume staging
- This repo’s GitHub OIDC `use_default: true` emits immutable `sub` IDs; staging trust must match that exact form

## Permissions granted (orchestration)

| Permission | Notes |
|------------|--------|
| `ssm:SendCommand` | Document `AWS-RunShellScript` only; instances tagged `Environment=<env>` + `Project=dealbrain` |
| `ssm:GetCommandInvocation` / `ListCommands` / `ListCommandInvocations` | Resource `*` (API limitation) |
| `ec2:DescribeInstances` / `DescribeInstanceStatus` | Resource `*` (API limitation) |
| `elasticloadbalancing:DescribeTargetHealth` | Resource `*` (API limitation) |
| `rds:DescribeDBInstances` | Resource `*` (API limitation) |

## Permissions intentionally withheld

- `secretsmanager:GetSecretValue` (and other SM value mutations) on deploy roles — hosts read secrets  
- `iam:*` / `iam:PassRole`  
- `organizations:*`  
- `rds:CreateDBSnapshot` (**deferred to Sprint 25b.4**; denied in 25b.2)  
- RDS mutate / delete; dangerous EC2 mutate  
- Terraform state S3 writes  
- Static AWS access keys anywhere  

## Host IAM (Sprint 25b.2 addition)

API host roles (`dealbrain-<env>-api-host`) attach:

`arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`

Preserved from 25a:

- Read own environment secret ARNs + RDS managed secret  
- Explicit deny of opposite `dealbrain/<other>/*`  
- Explicit deny `ecr:*`  

No SSH, no user_data deploy logic, no Docker install in Terraform.

## GHCR pull secret containers

| Path | Owner |
|------|--------|
| `dealbrain/staging/ghcr_pull` | Secrets module / staging root |
| `dealbrain/production/ghcr_pull` | Secrets module / production root |

Terraform owns **containers only**. There is **no** `aws_secretsmanager_secret_version` for GHCR credentials.

### Launch authentication contract

- Token type: **personal access token (classic)**  
- Scope: **`read:packages` only**  
- Preferably a dedicated DealBrain machine account  
- Values populated **out-of-band** (AWS CLI/console)  
- Separate environment containers; independently rotatable  
- Later Docker login uses `--password-stdin` (Sprint 25b.3+)  

Expected JSON shape (placeholders only — never real values in git/TF):

```json
{
  "username": "REPLACE_ME_OUT_OF_BAND",
  "token": "REPLACE_ME_OUT_OF_BAND"
}
```

### Out-of-band population (operator)

```bash
# Example shape only — do not commit real values
aws secretsmanager put-secret-value \
  --secret-id dealbrain/staging/ghcr_pull \
  --secret-string '{"username":"REPLACE_ME_OUT_OF_BAND","token":"REPLACE_ME_OUT_OF_BAND"}'
```

Repeat for `dealbrain/production/ghcr_pull`. Rotate by issuing a new classic PAT, updating each container, verifying host pull, then revoking the old PAT at GitHub.

## GitHub Environment hard gates (mandatory live security boundary)

**Documented here; not configured by this sprint.**

### Staging

| Setting | Required value |
|---------|----------------|
| Environment name | Exactly `staging` |
| Deployment branches | **`main` only** |
| Required reviewers | Optional for launch |
| Admin bypass | Prefer disabled; if enabled, audit |

### Production

| Setting | Required value |
|---------|----------------|
| Environment name | Exactly `production` |
| Deployment branches | **`main` only** |
| Required reviewers | **Enabled** (≥1) |
| Administrator bypass | **Disabled**, or **formally audited** with written acceptance |

Until these settings exist and are verified:

- Deploy roles must be treated as **non-operational**  
- No workflow should assume the roles  

OIDC `sub` proves the job used Environment `staging` / `production`; it does **not** prove the git ref was `main`. Branch rules in the GitHub UI are therefore mandatory.

## Validate (repository)

```bash
# Format
terraform fmt -check -recursive infra/terraform

# Account
cd infra/terraform/account && terraform init -backend=false && terraform validate

# Environments
cd infra/terraform/environments/staging && terraform init -backend=false && terraform validate
cd infra/terraform/environments/production && terraform init -backend=false && terraform validate
```

Do **not** run `terraform plan` / `apply` / `destroy` / `import` as part of this sprint’s CI.

## Deferred work

| Item | Sprint |
|------|--------|
| Custom SSM document + SendCommand execution | 25b.3 |
| Staging deploy workflow | 25b.3 |
| `DATABASE_URL` assembly | 25b.3 |
| Production deploy + approval workflow | 25b.4 |
| `rds:CreateDBSnapshot` ARN-scoped on production role | 25b.4 |
| Rollback workflow | 25b.5 |
| CloudWatch agent / log groups | 25c |
| VPC SSM interface endpoints | optional hardening |

## Tests

`tests/unit/test_sprint25b2_oidc_iam.py` — static inspection of OIDC uniqueness, trust isolation, permission denies, host SSM, GHCR containers, workflow absence, and documentation gates.
