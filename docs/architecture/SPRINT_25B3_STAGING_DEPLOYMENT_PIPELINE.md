# Sprint 25b.3 — Staging Deployment Pipeline Architecture

**Status:** Architecture proposal (documentation only; no implementation by this document)
**Branch:** `sprint-25b3`
**Path:** `docs/architecture/SPRINT_25B3_STAGING_DEPLOYMENT_PIPELINE.md`
**Contracts:** Sprint 25 §2/§8/§15; Sprint 25a Compose/RDS/secrets; Sprint 25b.1 digest + manifest; Sprint 25b.2 OIDC + deploy IAM
**Predecessors:** 25b.1 merged (`c75f81f` / PR #23); 25b.2 merged (`49b73f3` / PR #24)
**Scope:** **Staging only** — no production workflow, approval, snapshot, or rollback

---

## 1. Executive summary

Sprint 25b.3 designs the **first controlled deployment** of an immutable DealBrain image into AWS staging:

```
CI-green commit
  → immutable GHCR image + release manifest (25b.1)
  → GitHub Environment `staging` (main-only)
  → GitHub OIDC → dealbrain-staging-gha-deploy (25b.2)
  → custom SSM document (bounded parameters)
  → staging EC2 (host-side secrets + GHCR login)
  → one-shot Alembic migrate
  → API in-place recreate
  → /live + /ready + ALB gates
  → append-only staging evidence
```

### Chosen launch design (locked)

| Decision | Choice |
|----------|--------|
| Trigger | **B — `workflow_dispatch`** with `build_workflow_run_id` (manual, auditable; no artifact race) |
| Automatic staging on every build | **Deferred** until first successful live path exists |
| Production workflow | **Forbidden** in this sprint |
| Host bootstrap | **A — Terraform gzip `user_data_base64`** (idempotent AL2023 package + dirs; cloud-init runs original `staging.sh`) |
| Release bundle | **C — S3 staging release-artifacts bucket** (integrity-checked; no host GitHub token) |
| SSM document | **B — custom `DealBrain-StagingDeploy`**; revoke `AWS-RunShellScript` on staging deploy role once live |
| API rollout | **In-place Compose recreate** on the single staging host |
| Evidence | **Append-only** `staging-deploy-evidence.json` (+ derived staging status fields); store in **GitHub artifact + S3** |
| Secrets | **Host-only** Secrets Manager reads; never from GitHub/SSM params |
| Image authority | `ghcr.io/<owner>/<repo>@sha256:<digest>` only |

**Ready for repository implementation: YES**
**Ready for live staging deploy: NO** until DoD C/D prerequisites below.

---

## 2. Repository evidence (Section 1 assessment)

### 2.1 Branch / git

| Item | Evidence |
|------|----------|
| Branch | `sprint-25b3` (tracks `origin/sprint-25b3`; clean working tree) |
| 25b.1 | Merged — `build-image.yml`, `scripts/release/*`, schema |
| 25b.2 | Merged — account OIDC, deploy roles, host SSM, `ghcr_pull` containers |
| Deploy workflows | **Absent** (`deploy-staging.yml` / `deploy-production.yml` / `rollback.yml`) |
| Deploy scripts | **Absent** (`scripts/**/*deploy*` = 0) |

### 2.2 Classification matrix

| Concern | Classification |
|---------|----------------|
| Compose overlays (`base` + `staging` + `production`) | **Repository-implemented** (25a) |
| `api` / `migrate` separation; profile `migrate` | **Repository-implemented** |
| `DEALBRAIN_IMAGE` required env | **Repository-implemented** |
| Required runtime env (`DATABASE_URL`, `CORS_ORIGINS`, `APP_ENV`, backends, …) | **Repository-implemented** (Compose base) |
| Container HEALTHCHECK → `/live`; ALB TG → `/ready` | **Repository-implemented** |
| Staging TF outputs (`api_instance_id`, TG ARN, RDS, secrets, `gha_deploy_role_*`) | **Repository-implemented** |
| EC2 tags `Environment`, `Role=api-compose-host`, `Project=dealbrain` | **Repository-implemented** |
| GHCR secret container `dealbrain/staging/ghcr_pull` | **Repository-implemented** (empty values) |
| RDS managed secret ARN + endpoint/port/db_name | **Repository-implemented** |
| `user_data` Docker/Compose bootstrap | **Repository-implemented** (`infra/ec2/user_data/staging.sh`; signed Compose plugin via Sprint 25b.5a). Earlier inventory revisions marked this missing before the 25b.3 bootstrap script landed. |
| Docker / Compose / AWS CLI / jq on host | **Repository-implemented** in staging `user_data` (live host still requires apply/replace to pick up bootstrap) |
| SSM Agent registered / Online | **Live prerequisite** (AL2023 expected; needs apply + NAT) |
| Staging TF applied | **Live prerequisite** — **not performed** |
| GitHub Environment `staging` (`main` only) | **Live prerequisite** — **not configured** |
| App secret values + GHCR classic PAT populated | **Live prerequisite** — **not performed** |
| Remote Terraform state active | **Live prerequisite** — backend still commented |
| `deploy-staging.yml` + host deploy scripts + custom SSM doc | **Missing Sprint 25b.3 work** |
| Production deploy / snapshot / rollback | **Deferred → 25b.4 / 25b.5** |
| CloudWatch agent / synthetics | **Deferred → 25c** |
| VPC SSM interface endpoints | **Deferred** (optional; NAT sufficient) |

### 2.3 Compose contract (exact)

**Files:** `infra/compose/docker-compose.base.yml` + `docker-compose.staging.yml`
**Project name:** `dealbrain-staging`

| Service | Image | Profile | Command | Restart |
|---------|-------|---------|---------|---------|
| `api` | `${DEALBRAIN_IMAGE}` | (default) | image CMD (uvicorn) | `unless-stopped` |
| `migrate` | same digest | `migrate` | `alembic upgrade head` | `no` |

Required at render time: `DEALBRAIN_IMAGE`, `APP_ENV`, `DATABASE_URL`, `CORS_ORIGINS` (plus optional AI keys / `APP_SECRET_KEY`).
Staging overlay forces `APP_ENV=staging`.
**API must not run Alembic.** Migrate is one-shot:
`docker compose -f …base.yml -f …staging.yml --profile migrate run --rm migrate`

### 2.4 Current blockers

**Blockers to live deploy (not blockers to coding 25b.3):**

1. Remote state not bootstrapped / backends commented
2. No evidence staging stack was applied
3. GitHub Environment `staging` not configured (`main` only)
4. Secret values (app + GHCR PAT) not populated
5. Host bootstrap (Docker/Compose) not modeled yet (this sprint owns it)
6. SSM Agent Online not verified

---

## 3. Chosen workflow topology

### Decision: **Option B — `workflow_dispatch` with build run ID**

| Option | Verdict |
|--------|---------|
| A. `workflow_run` after Build Image | Rejected for launch — automatic deploys before host/secrets are ready; artifact timing races |
| **B. `workflow_dispatch`** | **Selected** — explicit operator intent; stable artifact download by run ID |
| C. Reusable workflow from build | Rejected — couples publish to deploy; harder to gate on Environment |

**File:** `.github/workflows/deploy-staging.yml`
**Name:** `Deploy Staging`

### Triggers

```yaml
on:
  workflow_dispatch:
    inputs:
      build_workflow_run_id:
        description: GitHub Actions run ID of successful Build Image workflow
        required: true
        type: string
      release_id:
        description: Optional release_id cross-check (must match manifest if set)
        required: false
        type: string
```

- **Automatic vs manual:** Manual for 25b.3 launch.
- **No** `workflow_run`, **no** PR triggers, **no** production workflow.
- Forks: job `if: github.event.repository.fork == false`.
- Ref: must be `refs/heads/main` (Environment branch rule is the hard gate; workflow also asserts).

### Permissions / environment

```yaml
permissions:
  id-token: write
  contents: read
  actions: read
  packages: read   # digest existence check via GHCR API / imagetools if needed

environment: staging   # exact name — mandatory
```

### Concurrency

```yaml
concurrency:
  group: deploy-staging
  cancel-in-progress: false   # never cancel during migration
```

| Setting | Value |
|---------|-------|
| Job timeout | `60` minutes |
| Superseded queued runs | Queue behind active; when started, host lock + release_id freshness check may reject older releases |
| Failed/cancelled Build Image | Rejected during ingestion (conclusion must be `success`) |

### Artifact download method

Use GitHub API + `gh` / `actions/download-artifact` **against the build run**:

1. `gh run view <build_workflow_run_id> --json conclusion,headSha,event,workflowName,status`
2. Assert `workflowName` = `Build Image`, `conclusion` = `success`, `status` = `completed`
3. List artifacts; find `release-manifest-<release_id>`
4. Download via `gh run download <build_run_id> -n release-manifest-<id>`
5. Fail closed if missing / multiple ambiguous / cancelled upstream

---

## 4. Manifest ingestion

### Inputs validated

From `release-manifest.json` (25b.1 schema):

| Field | Check |
|-------|--------|
| Schema + semantic | `scripts/release/validate_release_manifest.py` |
| `manifest_sha256` | Recompute; reject mismatch |
| `final_status` | Must be `built` |
| `environment` | Must be `none` |
| `image_digest` | `^sha256:[0-9a-f]{64}$` |
| `image_repository` | Matches `ghcr.io/<lowercase github.repository>` |
| `image_tag_sha` | `sha-<git_sha>` |
| `git_sha` | Matches Build Image run `headSha` |
| `build_workflow_run_id` | Matches input / run ID |
| `test_workflow_run_id` | Successful `ci.yml` run for same SHA on `main` |
| Mutable tags | Reject `:latest`, `:ci-latest`, env tags as authority |
| Optional `release_id` input | Must equal manifest if provided |

### Additional evidence checks

1. **GHCR digest exists:** `docker buildx imagetools inspect ${repo}@${digest}` (or GHCR API) after packages login with `GITHUB_TOKEN`
2. **CI green:** `gh run view <test_workflow_run_id>` → success + same SHA
3. **Reject** manifests with `staging_deployment_run_id` already set (built-state invariant)
4. **Never** treat tag-only identity as deployable

### Permissions needed

`actions: read` (cross-run artifacts + run metadata), `packages: read` (digest inspect), `contents: read` (checkout deploy scripts at **workflow ref** = `main`).

---

## 5. OIDC authentication

### Contract (extends 25b.2)

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ vars.AWS_ROLE_ARN }}          # dealbrain-staging-gha-deploy
    aws-region: ${{ vars.AWS_REGION }}                 # us-east-1 frozen
    role-session-name: gha-${{ github.run_id }}-staging
    role-duration-seconds: 3600
    audience: sts.amazonaws.com
    allowed-account-ids: ${{ vars.AWS_ACCOUNT_ID }}
```

| Topic | Spec |
|-------|------|
| Role chaining | **Unused** |
| Retry | Action default retry on transient STS; permanent AccessDenied → fail closed |
| Post-assume | `aws sts get-caller-identity` → Account == `AWS_ACCOUNT_ID`; ARN contains `dealbrain-staging-gha-deploy` |
| Wrong role/account | Fail closed; no static key fallback |
| Production role | Workflow must **not** reference production ARN/vars |

### GitHub Environment hard gate (not operational until)

| Setting | Required |
|---------|----------|
| Name | Exactly `staging` |
| Deployment branches | **`main` only** |
| Required reviewers | Optional for staging launch |
| Vars | `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID` |

Do **not** add production Environment behavior in 25b.3.

---

## 6. Host bootstrap contract

### Required pre-deploy host state

| Item | Requirement |
|------|-------------|
| OS | Amazon Linux 2023 |
| SSM Agent | Installed + **Online** |
| Docker Engine | Installed; daemon enabled |
| Docker Compose plugin | `docker compose` v2 |
| AWS CLI v2 | Present |
| jq, curl | Present |
| Deploy root | `/opt/dealbrain` owned by `root:root` mode `0755` |
| Releases dir | `/opt/dealbrain/releases` |
| Runtime env dir | `/opt/dealbrain/runtime` mode `0700` |
| Lock dir | `/opt/dealbrain/locks` |
| Log dir | `/var/log/dealbrain` |
| Disk | Root volume ≥ **30 GiB** (current TF default); fail if free `< 4 GiB` before pull **and** after pull |
| Secrets in user_data | **Forbidden** |
| Git credentials on host | **Forbidden** |

### Decision: **Option A — Terraform `user_data` / `user_data_base64`**

| Option | Verdict |
|--------|---------|
| **A. Terraform user_data** | **Selected** — runs on every new instance; survives replacement; no secrets. Sprint 25b.5b submits staging bootstrap as gzip-compressed `user_data_base64` (`base64gzip(file(...))`) under the EC2 16 KiB raw limit; cloud-init executes the original script. |
| B. One-time SSM bootstrap | Rejected as sole path — drift on replace |
| C. Immutable AMI | Deferred — ops cost too high for launch |
| D. Other | N/A |

**Design:** Staging EC2 module receives cloud-init via gzip-compressed `user_data_base64` that decompresses to:

1. `dnf` install docker, awscli, jq, gnupg2 (and other AL2023 default-repo tools; not full `curl` — use preinstalled `curl-minimal`)
2. Enable/start `docker`
3. Install Compose via signed Docker Inc path only (`scripts/deploy/host/install-compose-plugin.sh` — Sprint 25b.5a): plugin RPM only, Amazon engine retained, no unsigned binaries, no `docker-ce` / `--allowerasing`
4. Create directory layout + marker `/opt/dealbrain/bootstrap.ok` after Docker + Compose + tooling checks
5. Never embeds tokens, PAT, or DB passwords

**Idempotence:** Re-run safe package installs + compose installer short-circuit; marker written only after `docker compose version` succeeds.
**Verification:** Deploy script aborts if `bootstrap.ok` missing or `docker`/`compose` fail.
**Compose:** Required at bootstrap (25b.5a) and again at deploy time (orchestrator defense in depth).
**Package failures:** Instance unhealthy until fixed; no `bootstrap.ok` / SSM deploy fails closed without Compose.

Bootstrap script content lives in-repo (`infra/ec2/user_data/staging.sh` or Terraform `templatefile`) — **no secrets**.

---

## 7. Release bundle delivery

### Decision: **Option C — S3 staging release-artifacts bucket**

| Option | Verdict |
|--------|---------|
| A. SSM command parameters | Rejected — size/injection risk |
| B. Host download from GitHub | Rejected — general repo token on host |
| **C. Upload bundle to S3** | **Selected** |
| D. Bake into app image | Rejected — violates image purity / 25b.1 |
| E. Static scripts only at bootstrap | Insufficient alone — Compose must track release |

### S3 ownership

| Item | Owner |
|------|--------|
| Bucket | Staging Terraform root → new thin module or inline `aws_s3_bucket` |
| Name pattern | `dealbrain-staging-release-artifacts-<account_id>` (or fixed + account suffix) |
| Encryption | SSE-S3 or SSE-KMS (account default) |
| Public access | Block all |
| Versioning | Enabled |
| Lifecycle | Expire incomplete multipart; optional 90-day object expiry |

**Object key:**
`releases/<release_id>/bundle.tar.gz`
`releases/<release_id>/bundle.sha256`
`evidence/<release_id>/<deploy_run_id>/staging-deploy-evidence.json`

### Bundle contents (exact)

```
compose/docker-compose.base.yml
compose/docker-compose.staging.yml
bin/dealbrain-staging-deploy.sh      # orchestrator invoked by SSM doc
bin/assemble-runtime-env.sh
bin/ghcr-login.sh
bin/verify-staging.sh
manifest/release-manifest.json       # copy of validated built manifest
bundle-meta.json                     # release_id, git_sha, image_digest, files sha256 map
```

**Integrity:** Workflow computes SHA-256 of tarball; host verifies before extract.
**Linkage:** `bundle-meta.json` must include same `image_digest` + `release_id` as SSM params.
**Production material:** Bucket is staging-only; production Compose overlay **must not** be included.

### IAM updates (25b.3)

| Principal | Permission |
|-----------|------------|
| `dealbrain-staging-gha-deploy` | `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on staging artifacts bucket only |
| `dealbrain-staging-api-host` | `s3:GetObject`, `s3:ListBucket` on `releases/*` (+ optional evidence put if host uploads; prefer GHA uploads evidence) |
| Both | Explicit deny on production artifact bucket / `dealbrain/production/*` |

Deploy-role Terraform state deny remains. **Do not** grant Secrets Manager Get to deploy role.

---

## 8. SSM document and command model

### Decision: **Custom document; revoke AWS-RunShellScript on staging**

| Option | Verdict |
|--------|---------|
| A. Continue AWS-RunShellScript | Acceptable interim only; higher injection risk |
| **B. Custom DealBrain document** | **Selected** — bounded parameters |

### Specification

| Field | Value |
|-------|--------|
| Terraform owner | Staging root via new `modules/ssm_deploy_document/` (or inline) |
| Document name | `DealBrain-StagingDeploy` |
| Type | `Command` |
| Working directory | `/opt/dealbrain` |
| TimeoutSeconds | `2400` (40 min) document default; workflow may set ≤ that |
| Shell | `/bin/bash` with `set -euo pipefail` inside **fixed** script |
| Allowed commands | Exactly: `/opt/dealbrain/current/bin/dealbrain-staging-deploy.sh` with positional/env from parameters |
| AWS-RunShellScript | **Remove** from staging `allowed_ssm_document_arns` once custom doc applied |

### Parameters (no secrets)

| Parameter | AllowedPattern (illustrative) |
|-----------|-------------------------------|
| `ReleaseId` | `^rel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{7,40}$` |
| `GitSha` | `^[0-9a-f]{40}$` |
| `ImageRepository` | `^ghcr\.io/[a-z0-9._/-]+$` |
| `ImageDigest` | `^sha256:[0-9a-f]{64}$` |
| `BundleChecksum` | `^[0-9a-f]{64}$` |
| `DeployRunId` | `^[0-9]+$` |

Document body **must not** interpolate parameters into free-form shell (`commands: ["{{ReleaseId}}"]` style injection). Use SSM `{{ReleaseId}}` only as env exports into fixed script argv validation.

### Output / evidence

- `CloudWatchOutputConfig` optional (25c); for 25b.3 capture via `GetCommandInvocation` Stdout/Stderr with redaction
- Non-zero script exit → workflow fails
- CloudTrail: `SendCommand` under role session `gha-<run_id>-staging`

### GHA SendCommand shape

```
aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name DealBrain-StagingDeploy \
  --parameters '...' \
  --timeout-seconds 2400
```

Target: `api_instance_id` from TF output / `ec2 describe-instances` filtered by tags `Project=dealbrain`, `Environment=staging`, `Role=api-compose-host`. Fail if ≠1 instance.

---

## 9. Runtime secret assembly

### Owner

**Staging EC2 instance role** (`dealbrain-staging-api-host`) — already allowed `GetSecretValue` on staging app secrets + RDS managed secret; denied production paths.

### DATABASE_URL assembly

| Source | API | Fields |
|--------|-----|--------|
| RDS managed secret | `secretsmanager:GetSecretValue` | JSON `username`, `password` (AWS standard) |
| Non-secret metadata | Host-local file written by deploy from TF outputs baked into bundle-meta **or** `rds:DescribeDBInstances` from host (prefer **bundle-meta / deploy-env non-secret file** from workflow→S3: endpoint, port, db_name) | endpoint, port, db_name |
| Driver | Fixed | `postgresql+asyncpg` |

**Encoding:** `urllib.parse.quote_plus` (Python) or Python one-liner in script — never raw shell concatenation of unescaped password.

```
DATABASE_URL=postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}
```

### Other env vars (from SM containers)

| Secret path | Env var(s) |
|-------------|------------|
| `dealbrain/staging/app_secret_key` | `APP_SECRET_KEY` |
| `dealbrain/staging/openai_api_key` | `OPENAI_API_KEY` |
| `dealbrain/staging/anthropic_api_key` | `ANTHROPIC_API_KEY` |
| `dealbrain/staging/gemini_api_key` | `GEMINI_API_KEY` |
| `dealbrain/staging/cors_origins` | `CORS_ORIGINS` |
| `dealbrain/staging/monitoring` | optional / reserved |

Missing **required** secrets (`app_secret_key`, `cors_origins`, RDS secret) → fail closed.
Optional AI keys may be empty if live HTTP disabled.

### Env file contract

| Item | Spec |
|------|------|
| Path | `/opt/dealbrain/runtime/staging.env` |
| Mode | **0600** |
| Owner | `root:root` |
| Write | Atomic: write temp → `chmod 0600` → `rename` |
| Cleanup | Truncate/shred on failure paths that abort before start; retain on success for Compose; rotate by rewrite on next deploy |
| History | Never `echo` secrets; use process substitution / Python; `set +x` |
| Redaction | Logs show only `***REDACTED***` / field names |

### Compose secret exposure (accepted launch risk)

Docker Compose `environment:` / `env_file` places values in **container config** visible via `docker inspect` to anyone with Docker socket (root on host).

**Accepted residual risk for staging launch:** host root / Docker group is already a secret peer (same as SM read). Mitigations: private subnet, IMDSv2, no SSH, no shared host users, 0600 env file, no secrets in SSM/GitHub logs. **Deferred hardening:** Docker secrets / tmpfs-only env injection (P30+).

---

## 10. GHCR authentication

### Host-side login

1. `GetSecretValue` → `dealbrain/staging/ghcr_pull`
2. Parse JSON `username` + `token`
3. `printf '%s' "$token" | docker login ghcr.io -u "$username" --password-stdin`
4. Never echo token; never pass via argv

| Topic | Spec |
|-------|------|
| Credential store | Docker default (`~/.docker/config.json` for root) mode 0600 |
| Retention | Retain login for staging ops; refresh on each deploy |
| Rotation | Operator PutSecretValue + redeploy; revoke old PAT at GitHub |
| Failed login | Fail closed before pull |
| Pull | `docker pull "${ImageRepository}@${ImageDigest}"` only |
| Verify | `docker image inspect --format '{{index .RepoDigests 0}}'` contains digest |

**Forbidden:** `latest`, `ci-latest`, branch tags, tag-only `sha-*` without digest pin.

### Disk-space checks (required)

Disk free space **must** be verified at two points:

1. **Before image pull** — fail closed if free space `< 4 GiB`
2. **After image pull** — fail closed if free space `< 2 GiB` (or if pull consumed unexpected capacity leaving the host below the post-pull floor)

Both checks are hard gates. Partial pulls that leave the host disk-starved must abort before migrate/API recreate.

---

## 11. Database migration sequence

Exact order on host (under flock):

1. Acquire `/opt/dealbrain/locks/staging-deploy.lock` (`flock -n` or wait with timeout)
2. Verify SSM params vs `bundle-meta.json` / manifest
3. Download + checksum S3 bundle; extract to `/opt/dealbrain/releases/<release_id>`
4. Symlink `pending` → that release (optional); **do not** advance `current` until health gates pass
5. Assemble runtime env (0600)
6. GHCR login + **disk check before pull** + **pull digest** + **disk check after pull**
7. `docker compose … config` validate
8. Record `alembic current` (one-shot helper container or `compose run` with `alembic current`) → `migration_revision_before`
9. `timeout 1200s docker compose -f base -f staging --profile migrate run --rm migrate`
10. Record `alembic current` → `migration_revision_after`; require exit 0
11. Recreate API (`up -d --force-recreate --no-deps api` or equivalent)
12. Health gates
13. Write `DEPLOY_VERSION` into the release dir; atomically update `current`; retain prior release directory
14. Write+upload evidence to S3; release lock

| Topic | Spec |
|-------|------|
| Timeout migrate | 20 minutes |
| Concurrent deploy | Blocked by flock + GHA concurrency |
| One-shot cleanup | `--rm` |
| Alembic failure | Fail closed; **do not** recreate API to new digest |
| Partial commit | No automatic downgrade; operator forward-fix (Sprint 23 ownership); staging risk accepted |
| Automatic downgrade | **Forbidden** |
| Prod backup gate | **Not in this sprint** |
| Output redaction | Strip connection strings from captured logs |

### Deploy version marker (required)

After a successful API recreate and health gates, write:

**Path:** `/opt/dealbrain/current/DEPLOY_VERSION`

**Contents (JSON):**

```json
{
  "release_id": "rel-…",
  "git_sha": "<40-char hex>",
  "image_digest": "sha256:<64 hex>",
  "deployed_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

This file is non-secret host state for operators and verification scripts. It must match the release identity used for the running API container.

### Release directory retention (required)

Under `/opt/dealbrain/releases/`:

- Keep the **current** release directory (target of the `current` symlink)
- Keep at least the **previous** release directory

Older directories beyond current + previous may be pruned after a successful deploy. Retention of current + previous supports manual staging recovery without an automated rollback workflow (deferred to 25b.5).

---

## 12. API rollout model

### Decision: **In-place recreate (single staging host)**

| Option | Verdict |
|--------|---------|
| **In-place recreate** | **Selected** |
| Blue-green on one host | Deferred — extra ports/TG complexity |
| Multi-host | Not available at launch |

| Topic | Spec |
|-------|------|
| Expected downtime | ~30–180s (ALB unhealthy threshold window) |
| Compose project | `dealbrain-staging` |
| Container naming | Compose default `dealbrain-staging-api-1` |
| Network | Default Compose network; port `8000:8000` |
| Image pull | **Before** migrate (shared digest); disk checks before and after pull |
| API recreate | **Only after** migrate exit 0 |
| Restart policy | `unless-stopped` (base) |
| Unhealthy new API | Fail deploy; leave failed container for forensics; **manual** restore of prior release dir + prior digest (no automated rollback workflow in 25b.3) |
| Prior container | Docker may keep previous image layers locally for manual recovery |
| Prior release dir | Retained under `/opt/dealbrain/releases/` (current + previous minimum) |
| Staging risk | Accepted brief outage + manual recovery |
| Production note (25b.4) | Approval + backup gate + possibly longer drain; not designed here |

---

## 13. Health and verification

### Hard gates (fail closed)

| Gate | Expectation |
|------|-------------|
| Localhost `/live` | HTTP 200; JSON liveness true (Sprint 22 `LiveResponse`) |
| Localhost `/ready` | HTTP 200; `ready: true` (not 503) |
| ALB target health | Instance `healthy` in staging TG (`DescribeTargetHealth`) |
| Running digest | Container image RepoDigest matches release digest |
| `APP_ENV` | `staging` (from `docker inspect` / env — not secret) |
| Alembic | `migration_revision_after` non-null; equals head of release |
| Compose | `api` service `running` |
| Smoke | `GET /api/v1/health` or stable OpenAPI `GET /live` already counted; prefer unauthenticated `/live`+`/ready` + one read-only public/stable path already in CI contracts |
| Production resources | Instance tags/role/TG ARN must be staging; fail if production identifiers appear |
| `DEPLOY_VERSION` | Present under `/opt/dealbrain/current/DEPLOY_VERSION` and matches release identity |

### Timing

| Param | Value |
|-------|--------|
| Local probe interval | 5s |
| Local max wait | 180s after recreate |
| ALB max wait | 300s (matches TG interval×thresholds) |
| TLS | ALB may be HTTP-only if ACM empty — verify via TG health + localhost; public HTTPS when cert set |

Do **not** weaken Sprint 22 probe semantics.

---

## 14. Release evidence

### Prefer append-only history

| Artifact | Role |
|----------|------|
| Original build `release-manifest.json` | **Immutable** — remains `final_status=built`, `environment=none` |
| `staging-deploy-evidence.json` | **Authoritative staging evidence** (new schema) |
| Optional derived `release-manifest.staging.json` | Copy of build manifest with staging fields filled + new checksum — **new file**, never overwrite build artifact |

### Evidence fields (minimum)

`release_id`, `git_sha`, `image_digest`, `source_manifest_sha256`, `deploy_workflow_run_id`, `aws_account_id`, `aws_region`, `assumed_role_arn`, `role_session_name`, `ec2_instance_id`, `ssm_command_id`, `migration_revision_before`, `migration_revision_after`, `timestamps`, `localhost_live`, `localhost_ready`, `alb_target_healthy`, `smoke_ok`, `final_status` (`staging_ok`|`failed`), `failure_reason`, `evidence_sha256`

### Deployment timing fields (required)

| Field | Meaning |
|-------|---------|
| `deployment_started_at` | UTC timestamp when host deploy orchestration begins (after lock acquire) |
| `deployment_finished_at` | UTC timestamp when deploy reaches terminal success or failure |
| `deployment_duration_seconds` | Integer seconds between start and finish |

### Docker image metadata fields (required)

Recorded from the pulled/running image after successful pull (and re-checked after API recreate):

| Field | Meaning |
|-------|---------|
| `image_id` | Local Docker image ID |
| `repo_digest` | Repo digest string containing `sha256:…` matching release authority |
| `image_created_at` | Image created timestamp from Docker/OCI metadata |

### Storage

**Both:** upload as GitHub Actions artifact (`staging-evidence-<release_id>-<run_id>`, 90 days) **and** `s3://…/evidence/…`.

No production approval identity.

### Schema

Add `schemas/staging-deploy-evidence.schema.json` + Python validator mirroring manifest checksum model.

Logical status transition (derived view):
`built`/`none` → evidence `staging_ok`/`staging` (build artifact unchanged).

---

## 15. Concurrency and locking

### Layer 1 — GitHub

`concurrency.group: deploy-staging`, `cancel-in-progress: false`.

### Layer 2 — Host flock

```
flock -w 30 /opt/dealbrain/locks/staging-deploy.lock \
  -c '/opt/dealbrain/current/bin/dealbrain-staging-deploy.sh …'
```

Lock metadata file: `/opt/dealbrain/locks/staging-deploy.lock.info` JSON with `release_id`, `deploy_run_id`, `pid`, `started_at`.

| Case | Behavior |
|------|----------|
| Overlapping SSM | Second flock fails/times out → command non-zero → workflow fail |
| Stale lock | If lock holder PID dead and age > 90 min → operator may `rm` info + break flock (runbook); not automatic in v1 |
| Superseded queue | Newer dispatch waits; when older finishes, newer proceeds. Freshness/`allow_older` comparison was deferred/removed in acceptance fix (no reliable live-state comparison without echo-only controls) |
| Operator override | Documented SSM Session Manager break-glass (SSO), not GHA |

---

## 16. Failure handling (summary table)

| # | Failure | Mode | Prior API | Operator | Evidence | Retry | Rollback work |
|---|---------|------|-----------|----------|----------|-------|---------------|
| 1 | Missing build artifact | Fail closed | Untouched | Re-run Build Image | GHA logs | Manual | No |
| 2 | Manifest checksum mismatch | Fail closed | Untouched | Investigate tamper | GHA | No auto | No |
| 3 | CI evidence mismatch | Fail closed | Untouched | Fix SHA/CI | GHA | Manual | No |
| 4 | GHCR digest absent | Fail closed | Untouched | Re-publish | GHA | Manual | No |
| 5 | OIDC assume failure | Fail closed | Untouched | Env/trust/gates | CloudTrail | Manual | No |
| 6 | Wrong account/role | Fail closed | Untouched | Fix vars | GHA | No | No |
| 7 | Staging Env misconfigured | Fail closed | Untouched | Fix UI gates | GitHub | No | No |
| 8 | SSM instance offline | Fail closed | Untouched | NAT/agent/IAM | SSM | Manual | No |
| 9 | Bootstrap missing | Fail closed | Untouched | Replace/fix user_data | SSM | Manual | No |
| 10 | Bundle checksum mismatch | Fail closed | Untouched | Re-upload | S3/SSM | Manual | No |
| 11 | Secret missing | Fail closed | Untouched | Populate SM | Host logs | Manual | No |
| 12 | GHCR token invalid | Fail closed | Untouched | Rotate PAT | Host | Manual | No |
| 13 | Docker pull failure | Fail closed | Untouched | Network/PAT/disk | Host | Manual | No |
| 13a | Disk full before/after pull | Fail closed | Untouched | Expand volume / prune images | Host | Manual | No |
| 14 | Compose validation failure | Fail closed | Untouched | Fix bundle | Host | Manual | No |
| 15 | Revision lookup failure | Fail closed | Untouched | DB/network | Host | Manual | No |
| 16 | Migration failure | Fail closed | **Old API kept** | Forward-fix | Evidence+logs | No auto | Later if schema dirty |
| 17 | Migration timeout | Fail closed | Old API kept | Inspect DB locks | SSM | No auto | Possible |
| 18 | API recreate failure | Fail closed | Possibly down | Manual prior digest from retained previous release dir | Host | Manual | **Yes (manual)** |
| 19 | `/live` failure | Fail closed | New may be up | Inspect logs | Evidence | Manual | Manual |
| 20 | `/ready` failure | Fail closed | ALB drains | Fix deps/config | Evidence | Manual | Manual |
| 21 | ALB unhealthy | Fail closed | Traffic none | SG/health/app | AWS API | Manual | Manual |
| 22 | Smoke failure | Fail closed | May be up | Investigate | Evidence | Manual | Manual |
| 23 | Evidence upload failure | **Fail closed** after success gates (or warn-then-fail) | Running | Re-upload | Partial local | Manual | No |
| 24 | Concurrent release | Fail closed | Active deploy wins | Wait/retry | Lock info | Queue | No |
| 25 | Stale host lock | Fail closed | Unknown | Break-glass runbook | Lock info | Manual | No |
| 26 | Partial deployment | Fail closed | Documented state | Complete or manual restore | Evidence | Manual | Manual |
| 27 | Host disk full | Fail closed | Untouched if precheck | Expand volume | Host | Manual | No |
| 28 | Wrong env resource | Fail closed | Untouched | Fix discovery | GHA | No | No |
| 29 | Secrets printed | Fail closed + rotate | Possibly | Rotate all staging secrets + PAT | Incident | No | No |
| 30 | SSM timeout/truncation | Fail closed | Indeterminate | Check host; use Session Manager | Command ID | Manual | Maybe |

---

## 17. Security threat model (condensed)

| Threat | Prevention | Detection | Containment | Residual | Deferred |
|--------|------------|-----------|-------------|----------|----------|
| Tampered manifest | Checksum + schema + run binding | Validator fail | Stop deploy | Compromised Actions | Sigstore later |
| Mutable-tag swap | Digest-only pull | Script asserts `@sha256` | Abort | Tag confusion ops | — |
| Malicious digest input | Pattern + GHCR inspect + manifest bind | Mismatch | Abort | Compromised build | Provenance |
| Command injection | Custom SSM doc + AllowedPattern | CloudTrail | Freeze role | Doc misconfig | — |
| Compromised workflow | `main`-only Env + CODEOWNERS | Audit log | Disable Env | Admin force | `job_workflow_ref` pin |
| Compromised deploy role | Least privilege; no SM get | CloudTrail | Disable role | Describe `*` | SCP |
| Compromised host | Private subnet; IMDSv2; env deny | CW/GuardDuty later | Isolate + rotate | Docker root | 25c |
| Cross-env access | Separate roles/tags/denies | AccessDenied | — | Shared account | P30+ accounts |
| Secret leakage | Host-only; redaction; 0600 | Secret scan | Rotate | `docker inspect` | Docker secrets |
| GHCR PAT leak | stdin login; SM only | GitHub audit | Revoke PAT | Crash dumps | GitHub App |
| Migration abuse | Single flock; staging only | Logs | Stop | Destructive migration | Expand/contract |
| Arbitrary SSM | Custom doc only | CloudTrail | Remove RunShellScript | Break-glass SSO | — |
| Bundle tamper | SHA-256 + TLS S3 | Checksum fail | Abort | Compromised role Put | Bucket Object Lock |
| Replay old release | Explicit dispatch; optional freshness | Evidence | Operator choice | Staging allow older | Prod disallow |
| Concurrent race | GHA + flock | Lock fail | — | Stale flock | — |
| Docker socket | Root-only docker group | — | — | Host = peer | Rootless later |
| Container escape | no-new-privileges; read_only api | — | — | Kernel CVE | — |
| Poisoned image | CI + digest from Build Image only | — | — | Compromised main | Signing |
| Evidence tamper | Checksum + dual store | Mismatch | Discard | Writer compromise | WORM |
| Env rule bypass | Treat roles non-ops until gates | Settings audit | Fix UI | Admin bypass | — |
| Stale creds | Session 3600; PAT rotation runbook | Auth fail | Rotate | Forgotten PAT | Short-lived tokens |

---

## 18. Testing strategy (no live AWS required)

**New:** `tests/unit/test_sprint25b3_staging_deploy.py` (+ shell/unit for URL encoding).

Assert at minimum:

1. `deploy-staging.yml` exists.
2. It uses `environment: staging`.
3. It uses OIDC and no static keys.
4. It assumes only the staging role.
5. It cannot target production.
6. It validates release manifest and checksum.
7. It verifies CI/build workflow evidence.
8. It deploys by digest only.
9. It does not rebuild.
10. It does not use mutable tags.
11. It uses SSM only.
12. No SSH.
13. No secrets passed from GitHub.
14. Runtime secret assembly is host-side.
15. GHCR login uses password-stdin.
16. `DATABASE_URL` encoding is tested.
17. Secret env file uses 0600.
18. Migration runs separately.
19. API startup does not run Alembic.
20. API rollout happens only after migration success.
21. Concurrency cancellation is false.
22. Host flock exists.
23. Staging and production resource isolation.
24. Probe semantics unchanged.
25. ALB health verification exists.
26. Evidence schema validates.
27. Evidence checksum detects tampering.
28. No production workflow exists.
29. No DB snapshot permission/execution.
30. No Terraform apply.
31. Existing 25a, 25b.1, and 25b.2 tests remain green.
32. Secret scan and Ruff baseline remain green.
33. Disk-space checks exist before and after image pull.
34. `DEPLOY_VERSION` is written with `release_id`, `git_sha`, `image_digest`, `deployed_at`.
35. Current and previous release directories are retained.
36. Evidence includes deployment timing fields.
37. Evidence includes Docker image metadata (`image_id`, `repo_digest`, `image_created_at`).

**Note:** Update 25b.1/25b.2 tests that currently assert `deploy-staging.yml` **must not exist** — flip to 25b.3 positive assertions.

| Technique | Use |
|-----------|-----|
| Python static file/HCL inspection | Primary |
| JSON Schema | Evidence + manifest |
| Workflow YAML parse | Triggers/permissions |
| `terraform validate`/`fmt` | CI |
| Mocked AWS CLI / Compose | Script unit tests with `PATH` shims |
| Optional staging integration | Live DoD only |

---

## 19. Implementation phases

**Recommendation: multiple small PRs** (6 phases).

### 25b.3.1 — Staging workflow + manifest ingestion

| | |
|--|--|
| **Objective** | `deploy-staging.yml` skeleton: dispatch, Environment, OIDC, manifest download/validate, identity asserts; **no** SendCommand yet (or dry-run flag) |
| **Allowed** | `.github/workflows/deploy-staging.yml`, `scripts/release/*` helpers, tests, docs |
| **Forbidden** | Production workflow; domain/API/schema; TF apply |
| **Deps** | 25b.1/25b.2 merged |
| **Tests** | Workflow static tests; manifest gates |
| **Repo exit** | Workflow present; fails closed without live AWS |
| **Live** | None required |
| **Rollback** | Revert PR |

### 25b.3.2 — Host bootstrap + S3 bundle

| | |
|--|--|
| **Objective** | user_data; S3 bucket; bundle pack/upload scripts; host IAM GetObject |
| **Allowed** | `infra/terraform/**` staging, `infra/ec2/**`, `scripts/deploy/**`, tests |
| **Forbidden** | Production deploy role snapshot; app domain |
| **Deps** | 25b.3.1 |
| **Tests** | TF validate; bootstrap script unit; bundle checksum |
| **Live** | Apply staging after review (operator) |
| **Rollback** | TF revert; keep bucket versioning |

### 25b.3.3 — Custom SSM document + IAM refinement

| | |
|--|--|
| **Objective** | `DealBrain-StagingDeploy`; staging role document ARN allowlist; remove RunShellScript |
| **Allowed** | TF modules + staging root; tests |
| **Forbidden** | Broadening to production RunShellScript removal until 25b.4 |
| **Deps** | 25b.3.2 |
| **Tests** | Policy inspection; document parameter patterns |
| **Live** | Apply; verify SendCommand denied for free-form script |
| **Rollback** | Re-add previous document ARN temporarily |

### 25b.3.4 — Secret assembly, migrate, API rollout scripts

| | |
|--|--|
| **Objective** | Host scripts end-to-end under flock; disk checks; `DEPLOY_VERSION`; release retention |
| **Allowed** | `scripts/deploy/**`, Compose unchanged except if needed for wire-up |
| **Forbidden** | Alembic in API; rebuild in workflow; secrets in GHA |
| **Deps** | 25b.3.3 |
| **Tests** | URL encoding; 0600; ordering; redaction fixtures; disk gates; `DEPLOY_VERSION` |
| **Live** | Secrets populated; first migrate on staging RDS |
| **Rollback** | Manual prior digest from retained previous release dir |

### 25b.3.5 — Verification + evidence

| | |
|--|--|
| **Objective** | Probe/ALB gates; evidence schema including timing + image metadata; dual upload |
| **Allowed** | schemas, scripts, workflow steps, tests |
| **Forbidden** | Prod approval fields required |
| **Deps** | 25b.3.4 |
| **Tests** | Evidence checksum/tamper; timing/image fields present |
| **Live** | One successful staging deploy evidence pack |
| **Rollback** | N/A (additive) |

### 25b.3.6 — Tests, docs, architecture lock

| | |
|--|--|
| **Objective** | Full suite green; `ARCHITECTURE_LOCK` §14.1c additive; DEPLOYMENT/PRODUCTION/25A docs |
| **Allowed** | docs + tests + Makefile targets |
| **Forbidden** | Scope creep to 25b.4 |
| **Deps** | Prior phases |
| **Repo exit** | DoD B |
| **Live** | DoD C/D/E as operator checklist |

---

## 20. Definition of Done

### A. Architecture complete

- [x] This document selects concrete designs for all 20 sections
- [x] Operational refinements recorded: `DEPLOY_VERSION`, release retention, deployment timing, pre/post-pull disk checks, Docker image metadata in evidence
- [ ] Stakeholder sign-off

### B. Repository implementation complete

- [ ] `deploy-staging.yml` exists; **no** `deploy-production.yml` / `rollback.yml`
- [ ] Digest authority; manifest validation; OIDC staging only
- [ ] Custom SSM doc modeled; RunShellScript removed from staging role allowlist
- [ ] Host bootstrap + S3 bundle + host scripts
- [ ] Host-side secrets + GHCR stdin login
- [ ] Disk checks before and after image pull
- [ ] Migrate then API; health + evidence; concurrency + flock
- [ ] `/opt/dealbrain/current/DEPLOY_VERSION` written on success
- [ ] Current and previous release directories retained
- [ ] Evidence includes timing and Docker image metadata fields
- [ ] Tests green; no secrets in fixtures; lock additive; docs accurate

### C. Live prerequisite complete

- [ ] Account + staging Terraform applied; remote state active
- [ ] GitHub `staging` Environment: exact name, `main` only
- [ ] Vars: role ARN / account / region
- [ ] Instance SSM Online; Docker + Compose present (`bootstrap.ok` implies signed plugin path succeeded — Sprint 25b.5a)
- [ ] App secrets + GHCR classic PAT populated
- [ ] RDS reachable from host; ALB TG attached

### D. Live staging deployment evidence complete

- [ ] One successful digest deploy with evidence artifact + S3 object
- [ ] Safe failure-path probes (e.g. bad checksum / wrong role) recorded

### E. Security verification complete

- [ ] No secrets in GHA/SSM logs
- [ ] Staging cannot SendCommand to production
- [ ] Deploy role cannot GetSecretValue
- [ ] Digest-only pull proven

---

## 21. Assumptions

1. Single AWS account; region `us-east-1` (25a freeze).
2. Repo identity `markbilbao/dealbrain`; staging OIDC `sub` uses immutable IDs
   (`repo:markbilbao@309556720/dealbrain@1314423275:environment:staging`, Sprint 25b.5f).
3. One staging EC2 Compose host.
4. AL2023 + NAT for SSM/GHCR/SM.
5. GHCR private; classic PAT `read:packages`.
6. Operators complete Environment hard gates before assume-in-anger.
7. ACM may be empty initially (HTTP ALB) — TG health still authoritative.
8. Staging accepts short in-place downtime.
9. No production touch in this sprint.

---

## 22. Open decisions

None launch-blocking. Non-blocking:

| Item | Disposition |
|------|-------------|
| Auto `workflow_run` after Build Image | Enable only after first live success |
| Host uploads evidence vs GHA-only | Prefer **GHA** upload from command outputs + host-written file pulled via SSM |
| KMS CMK vs SSE-S3 for artifacts | SSE-S3 acceptable for staging launch |
| `allow_older` dispatch input | **Removed** in acceptance fix (was echo-only; freshness requires live deploy state) |

---

## 23. Ready for implementation

# **YES**

Repository implementation of Sprint 25b.3 may proceed against this contract.

Live staging deployment remains **blocked** until DoD C is satisfied. This document does **not** authorize `terraform apply`, GitHub Environment configuration, SSM execution, or any production path.

---

### Explicit non-goals (reaffirmed)

No DealScore / Recommendation / Shopping Assistant / marketplace / affiliate / API / schema / Sprint 22 probe changes; no production deploy/approval/snapshot/rollback; no static AWS keys; no public SSH; no secrets in GitHub or Terraform state; no image rebuild at deploy; no mutable-tag authority; no Alembic at image build or API startup; no direct DB access from GitHub Actions.

---

### Operational refinements (approved)

The following were approved as normative for Sprint 25b.3 implementation and are woven into §§6, 10–14, 16, 18–20:

1. **`/opt/dealbrain/current/DEPLOY_VERSION`** containing `release_id`, `git_sha`, `image_digest`, `deployed_at`.
2. **Release retention:** at least current and previous directories under `/opt/dealbrain/releases/`.
3. **Evidence timing:** `deployment_started_at`, `deployment_finished_at`, `deployment_duration_seconds`.
4. **Disk checks:** required both before and after image pull.
5. **Evidence image metadata:** `image_id`, `repo_digest`, `image_created_at`.
