# Sprint 25b.2 — AWS OIDC & Deploy IAM Architecture

**Status:** Architecture approved; **repository implementation complete**  
**Live status:** Terraform plan/apply **not performed**; live AWS resources **not created**; GitHub Environments **not configured**  
**Operational status:** Deploy roles remain **non-operational** until live security gates (§11 / §2.9 / DoD D) are completed  
**Branch:** `sprint-25b2`  
**Path:** `docs/architecture/SPRINT_25B2_AWS_OIDC_AND_DEPLOY_IAM.md`  
**Contracts:** Sprint 25 §2.0 / §5 / §7 / §8; Sprint 25a foundation; Sprint 25b.1 image publication  
**Predecessor:** Sprint 25b.1 merged (`c75f81f`)  
**Revision:** Status reconciled to repository-complete; normative security contract unchanged  
**Implementation doc:** [SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md](../SPRINT_25B2_OIDC_IAM_IMPLEMENTATION.md)

---

## 1. Executive summary

Sprint 25b.2 establishes the **authorization foundation** for later SSM-based staging (25b.3) and production (25b.4) deploys. It does **not** deploy DealBrain, run migrations, assemble `DATABASE_URL`, create DB snapshots, or create deploy workflows that execute against AWS.

**Repository vs live (current):** Terraform modules, env wiring, tests, and docs for OIDC + deploy IAM are in git. No `terraform apply` has been run, no AWS OIDC provider or deploy roles exist in a live account from this sprint, and GitHub Environments have not been configured. Modeled roles are **not operationally approved** until the hard gates below are live.

**Chosen launch design (concrete):**

| Decision | Choice |
|----------|--------|
| OIDC provider | **One** account-level Terraform root (`infra/terraform/account/`) owns `aws_iam_openid_connect_provider` for `https://token.actions.githubusercontent.com` |
| Deploy roles | Two roles: `dealbrain-staging-gha-deploy`, `dealbrain-production-gha-deploy` — **never** one shared role |
| Trust | Exact `sub` = `repo:<owner>/<repo>:environment:<env>` + `aud` = `sts.amazonaws.com` + `repository` claim |
| Live security gate | Roles are **not operationally approved** until GitHub Environments exist with **exact names**, **`main`-only deployment branches**, and production **required reviewers** with **admin bypass disabled or formally audited** |
| Secrets from GHA | **Denied** — hosts read Secrets Manager; GHA only orchestrates SSM |
| GHCR pull | **Classic PAT** with **`read:packages` only**, preferably a dedicated DealBrain machine account; Secrets Manager containers `dealbrain/staging/ghcr_pull` and `dealbrain/production/ghcr_pull`; values out-of-band only |
| SSM document | Use **`AWS-RunShellScript`** in 25b.2 permission scope; custom document deferred to **25b.3** |
| Host SSM | Attach **`AmazonSSMManagedInstanceCore`** + keep env-scoped secret allows/denies |
| Prod DB snapshot IAM | **Deferred to 25b.4** — document ARN-scoped contract only; **do not grant** in 25b.2 |
| Static AWS keys | **Forbidden** |

---

## 2. Repository evidence (Section 1 assessment)

### 2.1 Current branch / git

| Item | Evidence |
|------|----------|
| Branch | `sprint-25b2` |
| Remote | `git@github.com:markbilbao/dealbrain.git` → owner `markbilbao`, repo `dealbrain` |
| 25b.1 | Merged via PR #23; `build-image.yml` + release manifest tooling present |
| This phase | **Repository implementation complete** — Terraform + tests + docs in git; **no** live apply; **no** GitHub Environment configuration |

### 2.2 Terraform organization — **25a foundation + 25b.2 OIDC/IAM**

```
infra/terraform/
  account/                                      # 25b.2 — OIDC provider root
  modules/{networking,security_groups,alb,ec2,rds,secrets,iam}/
  modules/{github_oidc,github_deploy_role}/     # 25b.2
  environments/{staging,production}/
  README.md
```

| Pattern | Status |
|---------|--------|
| Provider | `hashicorp/aws ~> 5.0`, `required_version >= 1.5` |
| Backend | S3+DynamoDB **commented**; validate uses `-backend=false` |
| Naming | `dealbrain-<env>-*` / `name_prefix = dealbrain-${environment}` |
| Tags | `Project=dealbrain`, `Environment=staging|production`, `ManagedBy=terraform`; account/deploy-role `Sprint=25b.2`; env common tags remain `Sprint=25a` |
| Account IDs / ARNs hard-coded | **No** (placeholders like `EXAMPLE_ORG`, `REPLACE_ME`) |
| GitHub owner/repo parameterized | **Repository-implemented** (`github_repository_owner` / `github_repository_name`) |
| Remote state active | **Deferred** (bootstrap out-of-band) |

### 2.3 EC2 host IAM — **25a secrets scope + 25b.2 SSM**

Role: `${name_prefix}-api-host` (`dealbrain-staging-api-host` / `dealbrain-production-api-host`)

| Capability | Status |
|------------|--------|
| EC2 assume role + instance profile | **Repository-implemented** (25a) |
| `GetSecretValue` / `DescribeSecret` on env secret ARNs + RDS managed secret | **Repository-implemented** (25a) |
| Explicit deny opposite `dealbrain/<other>/*` | **Repository-implemented** (25a) |
| Optional CloudWatch Logs write | **Repository-implemented** (empty `log_group_arns` until 25c) |
| Explicit deny `ecr:*` | **Repository-implemented** (images from GHCR) |
| `AmazonSSMManagedInstanceCore` | **Repository-implemented** (25b.2) |
| GHCR pull secret access | **Repository-implemented** (`ghcr_pull` in env secret ARN list) |
| Custom minimum SSM policy (instead of managed) | **Not adopted** — managed policy acceptable for launch |
| Live host SSM Online | **Not claimed** (no apply) |

### 2.4 Secrets / RDS

| Item | Status |
|------|--------|
| App secret containers under `dealbrain/<env>/{app_secret_key,openai_api_key,…}` | **Repository-implemented** (empty values) |
| No conflicting `database_url` container | **Repository-implemented** |
| RDS `manage_master_user_password` | **Repository-implemented** |
| Host may read RDS managed secret ARN | **Repository-implemented** |
| GHCR credential secret container | **Repository-implemented** (`dealbrain/<env>/ghcr_pull`) |
| Secret values in Terraform | **Correctly absent** |
| Live secret values / classic PAT populated | **Not performed** (out-of-band operator) |

### 2.5 Network / SSM connectivity

| Item | Status |
|------|--------|
| EC2 in private subnet, `associate_public_ip = false` | **Repository-implemented** |
| NAT Gateway for egress (default on) | **Repository-implemented** → SSM public endpoints reachable after apply |
| VPC endpoints for `ssm` / `ssmmessages` / `ec2messages` | **Missing** (optional; not required while NAT exists) |
| API SG egress `0.0.0.0/0` | **Repository-implemented** (needed for GHCR, SM, SSM, RDS) |
| SSM agent | **Expected** on AL2023 AMI (preinstalled); not asserted in Terraform; user_data empty (Docker install deferred) |
| Public SSH | **Not present** (correct) |

### 2.6 EC2 / ALB targeting options

| Output | Status |
|--------|--------|
| `api_instance_id` | **Repository-implemented** |
| Tags `Environment`, `Role=api-compose-host`, `Name` | **Repository-implemented** |
| `alb_target_group_arn` | **Repository-implemented** |
| `rds_*` endpoints / secret ARN | **Repository-implemented** |

### 2.7 GitHub / workflows / OIDC & deploy IAM

| Item | Status |
|------|--------|
| `ci.yml` | Validate only; no AWS deploy; no OIDC assume |
| `build-image.yml` | GHCR publish; explicitly **no** `id-token`, OIDC, SSM, Environments |
| Deploy workflows | **Absent** (correct for 25b.2) |
| GitHub OIDC provider in AWS (Terraform model) | **Repository-implemented** (`infra/terraform/account` + `modules/github_oidc`) |
| Live OIDC provider in AWS account | **Not created** (no apply) |
| Deploy IAM roles (Terraform model) | **Repository-implemented** (`dealbrain-<env>-gha-deploy` via `modules/github_deploy_role`) |
| Live deploy roles in AWS | **Not created** (no apply) |
| GitHub Environment hard gates | **Documented; not configured** — **blocker for operational approval** |
| GHCR pull secret containers (Terraform) | **Repository-implemented** |
| Host GHCR pull at runtime | **Not claimed** (no apply / no values) |

### 2.8 Classification matrix

| Concern | Classification |
|---------|----------------|
| VPC/ALB/RDS/Secrets/host IAM (secrets) | Already implemented (25a) |
| Immutable image + manifest | Already implemented (25b.1) |
| Account OIDC provider | **Repository-implemented (25b.2)** — live resource not created |
| Staging/prod GHA deploy roles + trust | **Repository-implemented (25b.2)** — live roles not created; non-operational until gates |
| Host SSM managed policy | **Repository-implemented (25b.2)** |
| GHCR secret **container** + runbook | **Repository-implemented (25b.2)** — values out-of-band |
| GitHub Environments UI hard gates | **Prerequisite (operator)** — required before roles are operationally approved |
| Remote state bootstrap | **Prerequisite** for shared apply |
| Live `terraform plan` / `apply` | **Not performed** — operator prerequisite; not required for repo DoD |
| Custom SSM document | **Deferred → 25b.3** |
| Deploy workflows / SSM SendCommand execution | **Deferred → 25b.3/25b.4** |
| `DATABASE_URL` assembly | **Deferred → 25b.3** |
| `rds:CreateDBSnapshot` on prod deploy role | **Deferred → 25b.4** (contract documented now) |
| S3 release evidence bucket | **Deferred** (not adopted) |
| CloudWatch agent/log groups | **Deferred → 25c** |
| VPC SSM endpoints | **Deferred** (optional hardening) |

### 2.9 Blockers

**Blockers to live Terraform apply (not blockers to coding 25b.2):**

1. Remote state backend still commented  
2. No evidence AWS stack was ever applied  
3. ACM / DNS not cut over  
4. Account ID / GitHub owner-repo must be supplied as Terraform variables (no hard-coding)  
5. Secret **values** (app + GHCR classic PAT) must be set out-of-band after containers exist  

**Hard blocker to operational approval of deploy roles (live security boundary):**

6. GitHub Environments must be configured before any workflow may assume the roles in anger:
   - `staging`: exact name; deployment branches = **`main` only**
   - `production`: exact name; deployment branches = **`main` only**; **required reviewers**; **administrator bypass disabled or formally audited**

OIDC environment `sub` identifies the Environment name; it does **not** independently enforce which git ref ran the job. Branch restrictions in the GitHub Environment UI are therefore **mandatory** parts of the live security boundary, not optional hygiene.

---

## 3. Chosen architecture

```
GitHub Actions job (only after Environment hard gates are live)
  environment: staging | production   # exact names
  deployment branch rules: main only  # GitHub UI — part of security boundary
  production: required reviewers; admin bypass off/audited
  permissions: id-token: write
        │
        ▼  AssumeRoleWithWebIdentity (short-lived)
AWS IAM OIDC provider (account-level, once)
        │
        ├── dealbrain-staging-gha-deploy
        │     └── SSM SendCommand + describe* (staging tags/ARNs only)
        │           └── NO rds:CreateDBSnapshot
        │           └── NO secretsmanager:GetSecretValue
        │           └── target EC2 dealbrain-staging-api-host
        │                 └── AmazonSSMManagedInstanceCore
        │                 └── GetSecretValue dealbrain/staging/* + staging RDS secret
        │                 └── GetSecretValue dealbrain/staging/ghcr_pull  (classic PAT)
        │                 └── Deny dealbrain/production/*
        │
        └── dealbrain-production-gha-deploy
              └── SSM + describe* (production tags/ARNs only)
                    └── NO rds:CreateDBSnapshot in 25b.2 (deferred 25b.4)
                    └── target EC2 dealbrain-production-api-host
                          └── (mirror of staging, production secret paths)
```

**Invariants:**

1. GitHub never holds long-lived AWS keys.  
2. GitHub never needs application/DB secret values for deploy orchestration.  
3. Deploy roles are modeled in Terraform in 25b.2 but are **not operationally approved** until GitHub Environment hard gates (§11 / §2.9) are in place.  
4. 25b.2 grants only permissions with a current security-foundation purpose (OIDC assume, SSM orchestration prep, describe for targeting/health). Snapshot/backup gates wait for 25b.4.

---

## 4. OIDC provider ownership

### Decision: **Option A — account-level root**

Create:

```
infra/terraform/account/
  main.tf
  variables.tf
  outputs.tf
  versions.tf
  terraform.tfvars.example
```

**Do not** create the provider from staging or production roots (duplicate `EntityAlreadyExists` risk).

| Item | Specification |
|------|----------------|
| Resource | `aws_iam_openid_connect_provider.github` |
| URL | `https://token.actions.githubusercontent.com` |
| Client ID / audience list | `["sts.amazonaws.com"]` |
| Thumbprints | Prefer `data "tls_certificate"` for `token.actions.githubusercontent.com` → SHA-1 thumbprint(s); API still requires ≥1 thumbprint |
| Module | Optional thin `modules/github_oidc/` called only from `account/` |
| Inputs | `tags`; optional `create_provider` (bool, default true); optional `existing_provider_arn` |
| Outputs | `oidc_provider_arn`, `oidc_provider_url` |
| Duplicate prevention | Single root; `lifecycle { prevent_destroy = true }` recommended; tests assert exactly one provider resource |
| Import | If provider exists: `terraform import 'module.github_oidc.aws_iam_openid_connect_provider.github[0]' …` **or** `create_provider=false` + `existing_provider_arn` |
| Second AWS account later | Clone `account/` root per account; env roots consume that account’s provider ARN |

**Staging/production roots:** consume `oidc_provider_arn` via `terraform_remote_state.account` (preferred once backends exist) **or** temporary variable `github_oidc_provider_arn`.

**Plan order:** `account` → `staging` / `production`.

---

## 5. Deployment role model

### Roles (exact names)

| Role | Owner root |
|------|------------|
| `dealbrain-staging-gha-deploy` | `environments/staging` via `modules/github_deploy_role` |
| `dealbrain-production-gha-deploy` | `environments/production` via same module |

**Rejected alternative:** one role with env parameter — collapses blast radius, weakens CloudTrail attribution, and fights GitHub Environment binding.

| Field | Staging | Production |
|-------|---------|------------|
| Trust | OIDC → `environment:staging` | OIDC → `environment:production` |
| Max session duration | `3600` | `3600` |
| Session name (workflow) | `gha-${{ github.run_id }}-staging` | `gha-${{ github.run_id }}-production` |
| Tags | `Project`, `Environment=staging`, `Role=gha-deploy`, `ManagedBy=terraform` | same with `production` |
| Outputs | `gha_deploy_role_arn`, `gha_deploy_role_name` | same |
| Explicit deny | IAM mutate; opposite env; Secrets Manager get | same |
| CloudTrail | Role assumption + future SSM API calls under role session name | same |
| Operational approval | Only after GitHub `staging` env hard gates | Only after GitHub `production` env hard gates |

---

## 6. OIDC trust policies

### Supported IAM condition keys used

- `token.actions.githubusercontent.com:aud`
- `token.actions.githubusercontent.com:sub`
- `token.actions.githubusercontent.com:repository`

### Staging trust (exact)

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "GitHubActionsStagingEnvironment",
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:markbilbao/dealbrain:environment:staging",
        "token.actions.githubusercontent.com:repository": "markbilbao/dealbrain"
      }
    }
  }]
}
```

### Production trust

Same with `…:environment:production`.

Terraform variables (mandatory):

- `github_repository_owner` (e.g. `markbilbao`)
- `github_repository_name` (e.g. `dealbrain`)
- Construct `sub` as `repo:${owner}/${name}:environment:${environment}`

### Environment `sub` vs branch enforcement (critical)

An environment-based OIDC subject has the form:

`repo:<owner>/<repo>:environment:<environment_name>`

That claim proves the job declared GitHub Environment `staging` or `production`. It does **not** encode `refs/heads/main` and does **not** independently reject a job that somehow obtains that Environment from a non-`main` ref.

Therefore:

| Control | What it enforces |
|---------|------------------|
| IAM trust `sub` = `…:environment:staging\|production` | Correct Environment identity; blocks PR/`ref:`-only subjects |
| GitHub Environment **deployment branch rules = `main` only** | Source branch allowed to use that Environment |
| Production **required reviewers** | Human gate before prod credentials are issued |
| Production **admin bypass disabled or audited** | Prevents silent circumvention of reviewers |

**Roles are not operationally approved until both IAM trust and GitHub Environment hard gates are live.** Modeling roles in Terraform alone is insufficient for production or staging deploy authority.

### Why PRs / feature branches cannot assume (defense in depth)

| Context | Typical `sub` | Matches env trust? | Additional gate |
|---------|---------------|--------------------|-----------------|
| PR | `repo:…:pull_request` | **No** | — |
| Feature branch push without Environment | `repo:…:ref:refs/heads/feature-x` | **No** | — |
| Non-`main` job targeting Environment | Could match env `sub` if Environment allowed that branch | IAM may allow | **Blocked by Environment deployment branch = main only** |
| Fork PR | Restricted / wrong repository claim | **No** | — |

### Additional claim evaluation

| Claim | Use in 25b.2? | Reason |
|-------|---------------|--------|
| `aud` | **Required** | `sts.amazonaws.com` for `configure-aws-credentials` |
| `sub` (environment) | **Required** | Binds GitHub Environment name |
| `repository` | **Required** | Pin exact repo |
| `ref` | **Not primary in IAM** | Environment jobs’ `sub` is env-based; **branch enforcement is GitHub Environment UI** |
| `workflow` / `job_workflow_ref` | **Defer** | Reusable workflows rewrite `job_workflow_ref`; revisit when deploy paths are stable |
| `actor` / `event_name` | **No** | Too brittle |

### Immutable subject claims (GitHub 2026)

Existing repo uses **legacy** `sub` unless opted into immutable IDs. Launch design: legacy exact `StringEquals`. If org opts into immutable subjects, update Terraform `expected_sub` before deploy workflows go live.

### Repository rename / transfer

1. Update Terraform `github_repository_*` + re-apply trust  
2. Re-verify GitHub Environment hard gates  
3. Revoke old trust immediately on transfer away from controlled owner  

### GitHub Environment binding contract

| Name | Binding |
|------|---------|
| `staging` | Exact string in trust `sub`, workflow `environment:`, and GitHub UI |
| `production` | Exact string; required reviewers + `main`-only deploy branches + bypass policy |

---

## 7. Deploy permission policies

### Principle

Deploy roles are **orchestration roles**, not admin roles. Prefer host-side secret reads. **25b.2 includes only permissions with a current security-foundation purpose.**

### Implement **now** (25b.2)

| Permission | Staging scope | Production scope | Resource-level? | Why now |
|------------|---------------|------------------|-----------------|---------|
| `ssm:SendCommand` | Document `AWS-RunShellScript`; instances tagged `Environment=staging` + `Project=dealbrain` | Same with `production` | Document ARN + instance ARN pattern **with tag conditions** | Foundation for 25b.3/25b.4 deploy |
| `ssm:GetCommandInvocation` | `*` (API limitation) | same | **`*` required** | Observe command result |
| `ssm:ListCommands` / `ListCommandInvocations` | `*` | `*` | **`*` only** | Correlate commands |
| `ec2:DescribeInstances` | `*` (filter by tags in workflow) | same | **`*` only** | Verify target identity |
| `ec2:DescribeInstanceStatus` | `*` | `*` | **`*` only** | Host readiness |
| `elasticloadbalancing:DescribeTargetHealth` | Prefer staging TG ARN in requests; IAM often `*` | prod TG | Often **`*`**; deny opposite where conditions allow | Future verify path; harmless describe |
| `rds:DescribeDBInstances` | `*` | `*` | **`*` only** | Identify env DB without mutating |

### Explicitly **not** granted in 25b.2

| Permission | Status |
|------------|--------|
| `rds:CreateDBSnapshot` | **Deferred to Sprint 25b.4** |
| `rds:DescribeDBSnapshots` | **Deferred** (with backup gate) |
| `s3:GetObject` / `PutObject` evidence | **Deferred** until bucket adopted |
| `secretsmanager:GetSecretValue` on deploy role | **Never** (host retrieves) |

### Future ARN-scoped contract — `rds:CreateDBSnapshot` (25b.4 only)

When Sprint 25b.4 implements the production backup gate, grant **only** on the production deploy role:

```json
{
  "Sid": "CreateProductionDbSnapshotForBackupGate",
  "Effect": "Allow",
  "Action": "rds:CreateDBSnapshot",
  "Resource": [
    "arn:aws:rds:<region>:<account>:db:dealbrain-production-postgres",
    "arn:aws:rds:<region>:<account>:snapshot:dealbrain-production-*"
  ]
}
```

(Exact DB identifier / snapshot ARN patterns must match Terraform RDS `identifier` / naming at implementation time.)

- Staging role: **never** receives this permission.  
- 25b.2 tests must assert **absence** of `rds:CreateDBSnapshot` in both deploy role policies.

### Explicit deny **now** (both roles)

```
iam:*
organizations:*
secretsmanager:GetSecretValue
secretsmanager:PutSecretValue
secretsmanager:DeleteSecret
secretsmanager:UpdateSecret
rds:CreateDBSnapshot
rds:DeleteDBInstance
rds:ModifyDBInstance
ssm:SendCommand where ssm:resourceTag/Environment = opposite
ec2:TerminateInstances, StopInstances, ModifyInstanceAttribute
```

(Opposite-environment resource ARN denies where ARN patterns are stable.)

### Unnecessary

- `ec2:RunInstances`, VPC/SG mutate  
- `lambda:*`, `eks:*`, `ecr:*`  
- Terraform backend / S3 state write  
- `iam:PassRole`

### `sts:GetCallerIdentity`

**No IAM allow required.** Workflows use it for verification only.

---

## 8. SSM SendCommand security

| Topic | Decision |
|-------|----------|
| Document (25b.2) | Environment roots leave `allowed_ssm_document_arns` empty → only `arn:aws:ssm:<region>::document/AWS-RunShellScript`. That variable is an extension point for 25b.3 custom docs; do not widen it in 25b.2. |
| Custom DealBrain document | **Defer to 25b.3** |
| Target selection | Prefer **instance ID** from `api_instance_id`, verified against tags `Project=dealbrain`, `Environment=<env>`, `Role=api-compose-host` |
| Tag targeting | Allowed as secondary; IAM tag conditions mandatory |
| Cross-env prevention | Separate roles + tag condition + opposite-env deny |
| Timeout / output logging | Owned by 25b.3 / 25c |
| Injection | Fixed argv shapes in 25b.3; digest regex; no shell eval of free text |
| Params GHA may supply later | Image digest, release ID, environment name, compose paths — **not** secrets |

**25b.2 creates no SSM documents and sends no commands.**

---

## 9. EC2 host IAM updates

### Additions to `modules/iam` (env-owned)

1. **Attach** `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore` — **acceptable for launch**  
2. Include `ghcr_pull` container ARN in env secret allow list  
3. Keep `DenyOtherEnvironmentSecrets`  
4. CloudWatch / S3 release reads remain deferred  

### GHCR credential (host-side)

Classic PAT retrieved only on host. Docker login via `--password-stdin`; never echo the token.

---

## 10. GHCR pull authentication

### Options evaluated

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **A. Public package** | No pull token | Exposes image layers | Reject for launch |
| **B. Secrets Manager + PAT classic `read:packages`** | Matches current GitHub Packages docs for private Docker pulls; fits 25a secret model; host-only retrieval | Manual rotation | **Selected** |
| **C. Fine-grained PAT** | Narrower GitHub UX in some cases | **Not recommended** — current GitHub Packages documentation specifies **PAT (classic)** for private GHCR Docker authentication | **Rejected for launch** |
| **D. GitHub App / short-lived install tokens** | Better rotation story | More moving parts; private key custody | **Future hardening only** |

### Selected design (B) — locked

| Field | Value |
|-------|-------|
| Token type | **Personal access token (classic)** |
| Permission / scope | **`read:packages` only** (no `write:packages`, no repo contents write) |
| Owning identity | Preferably a **dedicated DealBrain machine account** (not a personal long-term human PAT) |
| Secret paths | `dealbrain/staging/ghcr_pull` and `dealbrain/production/ghcr_pull` |
| JSON shape | `{"username":"<machine_account_or_org>","token":"<classic_pat>"}` |
| Staging vs prod | **Separate Secrets Manager containers**; values populated independently out-of-band (may initially match, must rotate independently) |
| Terraform | Add leaf name `ghcr_pull` to secrets module — **container only** |
| Value injection | AWS CLI/console out-of-band only |
| Forbidden storage | **No token** in Terraform, tfvars, state, user_data, GitHub Actions artifacts, repository files, or documentation (docs may describe the *shape* and *path*, never a real value) |
| Rotation | Issue new classic PAT → `PutSecretValue` on each env container as needed → verify host pull → revoke old PAT at GitHub |
| Revocation | Revoke classic PAT at GitHub; pulls fail closed |
| Logging | Redact token; fail closed if secret missing |
| Future | GitHub App or other short-lived mechanisms remain **post-launch hardening**, not launch design |

---

## 11. Terraform module layout

```
infra/terraform/
  account/                         # NEW — OIDC provider only
  modules/
    github_oidc/                   # NEW
    github_deploy_role/            # NEW — role + trust + permissions (no CreateDBSnapshot)
    iam/                           # EXTEND — SSM managed policy + ghcr_pull ARN
    secrets/                       # EXTEND — add ghcr_pull to default secret_names
  environments/staging/
  environments/production/
```

### `modules/github_oidc`

- Resource: `aws_iam_openid_connect_provider`  
- Outputs: `arn`, `url`  
- Validation: audience contains `sts.amazonaws.com`

### `modules/github_deploy_role`

- Resources: role + permission/deny policies  
- Vars: `name`, `environment`, `oidc_provider_arn`, `github_repository_owner`, `github_repository_name`, region, optional instance/TG ARNs, allowed SSM document ARNs, tags, session duration  
- **Must not** accept or emit `rds:CreateDBSnapshot` allows in 25b.2  
- Validations: environment ∈ {staging, production}; owner/name non-empty; no AWS access-key variables  

### Account root

- State key: `account/terraform.tfstate`  
- Env roots may read account state; account never reads env state  

---

## 12. Environment isolation matrix

| Capability | Staging role | Production role |
|------------|--------------|-----------------|
| Assume from GitHub `staging` env | **Yes** (after hard gates) | **No** |
| Assume from GitHub `production` env | **No** | **Yes** (after hard gates) |
| Assume from PR / feature branch / fork | **No** | **No** |
| Assume usable from non-`main` if Environment misconfigured | **Operationally forbidden** — branch rule required | same |
| Send SSM to staging host | **Yes** | **No** |
| Send SSM to production host | **No** | **Yes** |
| Inspect staging ALB TG health | **Yes** | **No** |
| Inspect production ALB TG health | **No** | **Yes** |
| Create staging DB snapshot | **No** | **No** |
| Create production DB snapshot | **No** | **No** in 25b.2 (**Yes** only in 25b.4, ARN-scoped) |
| Read secret values from GHA | **No** | **No** |
| Modify IAM | **No** | **No** |
| Apply Terraform / write state | **No** | **No** |

---

## 13. GitHub Environment configuration

### Hard security gate (mandatory before operational approval)

**Staging**

| Setting | Required value |
|---------|----------------|
| Environment name | Exactly `staging` |
| Deployment branches | **`main` only** |
| Required reviewers | Optional for launch |
| Wait timer | None required |
| Admin bypass | Prefer disabled; if enabled, audit |

**Production**

| Setting | Required value |
|---------|----------------|
| Environment name | Exactly `production` |
| Deployment branches | **`main` only** |
| Required reviewers | **Enabled** (≥1) |
| Administrator bypass | **Disabled**, or **formally audited** with written acceptance if org constraints force it |
| Wait timer | Optional 5–10 min |

Until these settings exist and are verified, deploy roles must be treated as **non-operational** even if Terraform has created them.

### What belongs where

| Value | Location |
|-------|----------|
| `AWS_ROLE_ARN` | GitHub Environment **variable** (non-secret) after ops approval |
| `AWS_REGION` / `AWS_ACCOUNT_ID` | Environment or repo variables |
| EC2 / TG / secret ARNs | Prefer Terraform outputs / AWS discovery at deploy time |
| Application secrets / DB password / GHCR classic PAT | **AWS Secrets Manager only** — never GitHub |
| AWS access keys | **Nowhere** |

### Test constants

```
GITHUB_ENVIRONMENT_STAGING = "staging"
GITHUB_ENVIRONMENT_PRODUCTION = "production"
```

---

## 14. Future workflow authentication contract

**Not implemented in 25b.2.** Contract for 25b.3/25b.4 (only after Environment hard gates):

```yaml
permissions:
  id-token: write
  contents: read
environment: staging   # or production — exact names
# GitHub UI: deployment branch = main only; production reviewers required
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ vars.AWS_ROLE_ARN }}
      aws-region: ${{ vars.AWS_REGION }}
      role-session-name: gha-${{ github.run_id }}-${{ github.job }}
      role-duration-seconds: 3600
      audience: sts.amazonaws.com
      allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}
  - run: |
      aws sts get-caller-identity
      # assert Account + role name dealbrain-<env>-gha-deploy
```

| Topic | Spec |
|-------|------|
| Action | `aws-actions/configure-aws-credentials@v4` |
| Role chaining | Unused |
| Failure | Fail closed; no static key fallback |

### Evidence linkage (later)

Release manifest `build_workflow_run_id` / digest ↔ GitHub deploy `run_id` ↔ AWS role session name ↔ SSM command ID ↔ CloudTrail.

---

## 15. Threat model

| # | Threat | Prevention | Detection | Containment | Residual | Later |
|---|--------|------------|-----------|-------------|----------|-------|
| 1 | Malicious PR assumes role | Env `sub` + no PR subject match | CloudTrail | Deny | Wildcard trust misconfig | Policy tests |
| 2 | Compromised feature branch | No ref-based trust + **Environment `main`-only** | CloudTrail / GitHub audit | Disable Environment | Admin weakens branch rules | Periodic gate audit |
| 3 | Workflow changed in PR | Protected envs + `main`-only + CODEOWNERS | Review | Block merge | Admin force-merge | Required reviews |
| 4 | Fork PR | Fork limits + repository claim | Actions logs | N/A | Org misconfig | Keep forks restricted |
| 5 | GitHub token compromise | No AWS keys in GitHub | GitHub audit | Revoke sessions; rotate **classic** GHCR PAT | PAT abuse on GHCR | Shorter-lived App tokens (future) |
| 6 | Prod approval bypass | Required reviewers + **bypass disabled/audited** | GitHub audit | Re-enable protections; revoke sessions | Org-enforced admin bypass | Formal audit log |
| 6b | Env `sub` without branch gate | **Hard gate: deployment branches = main** | Settings review | Fix Environment rules; treat roles non-operational until fixed | UI drift | Live DoD checklist |
| 7 | Staging→prod deploy | Separate roles + tag deny | CloudTrail SSM | Disable staging role | Describe `*` breadth | SCPs / separate accounts |
| 8 | Prod role IAM escalation | Explicit `iam:*` deny | CloudTrail / Analyzer | Detach policies | Novel privilege paths | SCP |
| 9 | SSM command injection | Fixed document; digest regex | Command output | Freeze role | Operator mistake | Custom doc 25b.3 |
| 10 | Secrets in logs | No SM get on GHA; redaction | Secret scan | Rotate | Host mis-echo | Script lint 25b.3 |
| 11 | GHCR classic PAT leakage | Host-only; stdin login; never in docs/TF/artifacts | GitHub PAT audit | Revoke classic PAT; put new value in both env secrets as needed | Token in crash dumps | Future App tokens |
| 12 | TF state has credentials | Containers only; no secret versions in TF | State scan | Rotate if violated | Operator adds version resource | Module forbid |
| 13 | Repo rename/transfer | Mandatory vars; runbook | Assume failures | Update trust + re-check Environment gates | Stale name trust | Immutable `sub` IDs |
| 14 | Wrong AWS account | `allowed-account-ids` + GetCallerIdentity | Job failure | Stop | Typo in vars | Dual-check |
| 15 | OIDC already exists | Import/data path | Apply error | Import | Dual ownership | Account-only tests |
| 16 | Duplicate TF ownership | Single account root | Tests count providers | Delete duplicate | — | — |
| 17 | Broad `Resource:*` | Limit where possible; denies; tags | Analyzer | Tighten | Inherent describe/list limits | Permission boundaries |
| 18 | Compromised EC2 | Private subnet; IMDSv2; env secret scope | CW / GuardDuty later | Isolate + rotate secrets **including classic PAT** | Host = secret peer | 25c |
| 19 | Cross-env SM read | Explicit deny paths | IAM simulate | Deny | Tag typos | Separate accounts P30+ |
| 20 | Stale collaborator | Env reviewers + branch protection | Audit log | Remove from env | Admin leftovers | Access reviews |
| 21 | Premature use of modeled roles | Operational approval blocked until Environment hard gates | Checklist / live DoD | Deny workflow enablement | Someone ignores runbook | Explicit docs + DoD |

---

## 16. Failure and recovery

| Failure | Expected error | Fail closed? | Operator action | Evidence | Break-glass | Sprint |
|---------|----------------|--------------|-----------------|----------|-------------|--------|
| OIDC token rejected | STS `InvalidIdentityToken` | Yes | Check audience/`id-token` | Actions, CloudTrail | Human SSO | 25b.2 |
| `sub` mismatch | Assume `AccessDenied` | Yes | Fix trust / environment name | CloudTrail | SSO | 25b.2 |
| Wrong GitHub Environment | Assume denied / wrong role | Yes | Fix `environment:` | Actions | — | 25b.3 |
| Non-`main` deploy attempted | GitHub Environment rejects deployment | Yes | Use `main` only; verify branch rules | GitHub UI / Actions | Do **not** widen branch rules | ops gate |
| Environment protection missing | Process / live DoD fail | Soft→Hard | Configure gates before any assume-in-anger | Settings screenshots | Block 25b.3/25b.4 | **ops prerequisite** |
| Prod without required reviewers | Live DoD fail | Hard | Enable reviewers; disable/audit bypass | Settings | Block prod | ops |
| Wrong owner/repo | Assume denied | Yes | Update TF vars | CloudTrail | — | 25b.2 |
| Wrong AWS account | `allowed-account-ids` fail | Yes | Fix vars | Action | — | 25b.3 |
| SSM host offline / agent missing | InvalidInstanceId / timeout | Yes | NAT, SSM policy, agent | SSM console | SSO Session Manager | 25b.2/25b.3 |
| Missing tags / scope deny | AccessDenied SendCommand | Yes | Fix tags/policy | CloudTrail | — | 25b.2 |
| Missing GHCR secret / bad classic PAT | Docker 401 / SM deny | Yes | Populate/rotate classic PAT out-of-band | Host/SSM | — | 25b.2 + ops |
| Duplicate OIDC | `EntityAlreadyExists` | Yes | Import | IAM | — | 25b.2 |
| Staging usable as prod | Must not | N/A | Disable role / deny | CloudTrail | Disable role | 25b.2 tests |
| Attempt to snapshot via 25b.2 role | AccessDenied (`CreateDBSnapshot` absent/denied) | Yes | Wait for 25b.4 policy | CloudTrail | Manual snapshot via SSO if incident | 25b.4 |

---

## 17. Testing strategy

### Minimum reliable suite (no live AWS)

New file pattern: `tests/unit/test_sprint25b2_oidc_iam.py` (static inspection).

Assert at least:

1. Exactly one `aws_iam_openid_connect_provider` in tree  
2. Audience includes `sts.amazonaws.com`  
3. Trust pins repository owner/name  
4. Staging trust contains `environment:staging`  
5. Production trust contains `environment:production`  
6. Staging trust does not mention `environment:production`  
7. Staging permissions cannot target production host tags/ARNs  
8. Deploy policies deny IAM admin; no IAM allow mutations  
9. No static AWS key variables  
10. No `aws_secretsmanager_secret_version` for app/GHCR tokens  
11. Host attaches `AmazonSSMManagedInstanceCore`  
12. Host secrets env-scoped; includes `ghcr_pull` path naming  
13. Opposite-env secret deny remains  
14. Deploy role permissions limited to SSM/describe set above  
15. **`rds:CreateDBSnapshot` absent** from both deploy role policies in 25b.2  
16. Explicit deny or documented absence of snapshot create  
17. `terraform validate` / `fmt` via CI  
18. 25a + 25b.1 tests remain green  
19. Architecture lock additive  
20. No executable deploy workflows (or placeholders must not call AWS)  
21. No `terraform apply` in Actions  
22. No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in workflows  
23. Environment name constants `staging` / `production`  
24. Role outputs env-specific  
25. Tag conditions on SendCommand policy  
26. Policy JSON inspectable  
27. Docs/architecture state classic PAT + `read:packages` only (and do not embed token values)  
28. Docs state Environment hard gates (`main`-only; prod reviewers; bypass policy) as operational approval criteria  

### Tools

pytest static HCL/text (**primary**); `terraform validate`/`fmt`; optional Access Analyzer on plan; skip LocalStack for OIDC; live assume/deny probes only for live DoD.

---

## 18. Implementation phases

**Recommendation:** multiple small PRs.

### 25b.2.1 — Account-level GitHub OIDC provider

OIDC once; import path; tests for uniqueness. No deploy workflows. No secret values.

### 25b.2.2 — Environment deploy roles + trust

Staging/prod roles; env-bound trust; SSM/describe permissions only; **no** `rds:CreateDBSnapshot`; explicit denies including snapshot create. Tests for isolation + snapshot absence.

### 25b.2.3 — EC2 SSM + secret-access updates

Attach `AmazonSSMManagedInstanceCore`; keep opposite-env deny.

### 25b.2.4 — GHCR pull credential containers + runbooks

Add `ghcr_pull` containers under staging/production paths; document classic PAT `read:packages`, machine account preference, rotation/revocation; **forbid** token material in repo/TF/docs examples beyond placeholders like `REPLACE_ME_OUT_OF_BAND`.

### 25b.2.5 — Tests, documentation, architecture lock

Full suite; save this architecture doc; additive lock; CI includes 25b.2 tests; document that **operational approval** requires GitHub Environment hard gates (operator checklist — not Terraform).

**Still deferred:** 25b.4 adds ARN-scoped `rds:CreateDBSnapshot` to production role only when backup gate is implemented.

---

## 19. Definition of Done

### A. Repository complete (no AWS creds required) — **DONE in git**

- [x] OIDC provider modeled exactly once  
- [x] Separate staging/production deploy roles  
- [x] Trust pinned to repo + GitHub Environment name  
- [x] No static AWS credentials  
- [x] Deploy roles cannot administer IAM / apply Terraform / read SM values  
- [x] Deploy roles **do not** include `rds:CreateDBSnapshot`  
- [x] Isolation tests green (including snapshot absence)  
- [x] Host SSM capability modeled  
- [x] GHCR containers modeled (`dealbrain/<env>/ghcr_pull`); classic PAT design documented; **no token values** anywhere in repo/TF  
- [x] Architecture documents Environment hard gates as operational approval criteria  
- [x] `terraform fmt` + `validate` (CI / local; **no apply**)  
- [x] 25a/25b.1/25b.2 tests + secret scan green  
- [x] Architecture lock additive  
- [x] No deploy executed  

### B. Terraform plan complete — **not performed**

- [ ] `account` + staging + production plans succeed against a real account  
- [ ] Import path verified if provider pre-exists  

### C. Live AWS configuration complete — **not performed**

- [ ] Provider present once  
- [ ] Roles exist with correct trust  
- [ ] Hosts SSM Managed Instance Online  
- [ ] Host reads only own secrets including `ghcr_pull`  
- [ ] Staging cannot SendCommand to prod  
- [ ] Neither deploy role can `CreateDBSnapshot`  

### D. GitHub UI configuration complete (**hard gate — operational approval**) — **not configured**

- [ ] Environment name exactly `staging`; deployment branches = **`main` only**  
- [ ] Environment name exactly `production`; deployment branches = **`main` only**  
- [ ] Production **required reviewers** enabled  
- [ ] Production **administrator bypass disabled** or **formal audit record** filed  
- [ ] Non-secret vars (role ARN / region / account) set only after above gates  

**Until D is complete, deploy roles are not operationally approved** (even after a future apply creates them).

### E. Security verification complete — **not performed**

- [ ] Assume success only from correctly gated Environment jobs on `main`  
- [ ] Assume fail from wrong env / PR / feature branch  
- [ ] Non-`main` deployment rejected by Environment branch rules  
- [ ] Production blocked without reviewer approval  
- [ ] No secret values (including classic PAT) in Actions logs  
- [ ] Snapshot create denied on current deploy roles  

**Without AWS/GitHub UI:** complete **A** (repository).  
**Before any real assume/deploy:** complete **D** then **B/C/E** as applicable.

---

## 20. Assumptions

1. Staging and production share **one AWS account** for launch (VPC CIDR isolation as in 25a).  
2. Region remains the frozen Sprint 25a region (default `us-east-1`).  
3. Repository identity is currently `markbilbao/dealbrain` (legacy OIDC `sub`).  
4. AL2023 includes SSM Agent; NAT remains enabled.  
5. GHCR packages remain private.  
6. Private GHCR Docker pulls use a **classic PAT** with **`read:packages` only**, per current GitHub Packages documentation.  
7. A dedicated DealBrain machine account is preferred to own that classic PAT.  
8. Deploy orchestration will use SSM Run Command (not SSH).  
9. Operators configure GitHub Environment **hard gates** outside Terraform before operational use.  
10. Remote state bootstrap remains an operator prerequisite for collaborative apply.  
11. Production pre-migrate snapshot permission is a **25b.4** concern, not 25b.2.

---

## 21. Open decisions

No launch-blocking security decisions remain unresolved for 25b.2.

Non-blocking future items (explicitly **not** open launch choices):

| Item | Disposition |
|------|-------------|
| GitHub App / short-lived GHCR auth | Post-launch hardening only |
| Opt into GitHub immutable `sub` IDs | Optional migration runbook; not required to start 25b.2 coding |
| Custom SSM document | Decide in 25b.3 |
| Separate AWS accounts | P30+ |
| VPC SSM interface endpoints | Optional when NAT strategy changes |
| Exact production snapshot ARN spellings | Fixed when 25b.4 implements backup gate against live Terraform outputs |

---

## 22. Implementation status

# **Repository complete; live gates incomplete**

Sprint 25b.2 **repository** work (Terraform + tests + docs under the phases above) is complete in git.

**Not performed:** `terraform plan` / `apply`, live AWS OIDC provider or deploy-role creation, GitHub Environment configuration, role assumption, or SSM SendCommand.

**Operational use of the roles remains gated** on GitHub Environment hard security settings (`staging` / `production` exact names, `main`-only deployment branches, production required reviewers, admin bypass disabled or formally audited).

**Explicit non-goals:** no application rollout, no migration execution, no `DATABASE_URL` assembly, no `rds:CreateDBSnapshot` in 25b.2, no static AWS keys, no SSH, no fine-grained PAT for GHCR launch auth, no domain/API/schema changes, no Sprint 25a ownership redesign beyond additive IAM/secret-container extensions.

---

*Status reconciled after repository implementation. Normative security contract unchanged. No terraform apply, no live AWS resources, and no GitHub Environments were configured by this document revision.*
