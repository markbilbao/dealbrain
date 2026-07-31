# Sprint 25 — Production Infrastructure Architecture

**Status:** Implementation-ready architecture contract (documentation only; no infra implemented by this document)  
**Branch:** `sprint-25`  
**Hard launch target:** Sprint 30 public launch  
**Predecessor:** Sprint 24 (API stability) merged to `main`  
**Owner:** Production infrastructure and operations (not domain logic, not API contracts, not persistence adapters)  
**Contract revision:** Finalization (concrete platform, IaC, isolation, release, migration, rollback, SLOs, observability, backup evidence, config gate, M30 evidence matrix, phased DoD)

---

## 0. Scope and non-negotiables

### 0.1 What Sprint 25 owns

Sprint 25 owns the **runtime platform and operational practices** required to run DealBrain safely before Sprint 30:

- Environments, deployment topology, CI/CD
- Configuration and secrets handling (ops layer)
- Logging, metrics, alerting, and probe integration
- Backup / recovery / disaster recovery / rollback
- Migration and release workflow
- Incident response and operational runbooks
- Security hardening at the infrastructure boundary

### 0.2 What Sprint 25 does **not** own

| Locked owner | Must remain untouched |
|--------------|------------------------|
| Sprint 5 | DealScore |
| Sprint 6 | Recommendation Engine |
| Sprint 13 | Shopping Assistant ranking |
| Sprint 16 | Personal AI |
| Sprint 4 / 18 / 21 | Marketplace domain semantics |
| Sprint 23 | Production persistence adapters, Alembic schema ownership |
| Sprint 24 | API contracts / OpenAPI / pagination / error envelope |
| Sprint 22 | Readiness **semantics** (`/live`, `/ready`, `/health`, persistence levels) |

**Forbidden:** business logic changes; API redesign; database schema redesign; ranking/affiliate/merchant neutrality changes; redistributing Architecture Lock ownership from Sprints 1–24.

Sprint 25 **consumes** Sprint 22 probes and Sprint 23 readiness depth as black-box contracts. It must not redefine them.

### 0.3 Design principles

1. Prefer portable containers, standard probes, env/secret injection — but **implement against one concrete platform** (§2.0).
2. Single-region first; multi-region deferred.
3. Reliability over premature optimization.
4. Minimize operational complexity for Sprint 30.
5. Allow future horizontal scaling without requiring it at day one.
6. Preserve app contracts — wrap existing `Dockerfile`, Compose migrate pattern, Alembic, and probes.

### 0.4 Priority legend

| Tag | Meaning |
|-----|---------|
| **M30** | Mandatory for Sprint 30 public launch |
| **P30+** | Recommended soon after launch |
| **FUT** | Future scalability / multi-region / advanced ops |

---

## 1. Current production readiness assessment

### 1.1 Repository evidence (platform selection inputs)

| Evidence | Finding |
|----------|---------|
| `Dockerfile` | Multi-stage Python 3.12 image; non-root user; `HEALTHCHECK` → `GET /live`; uvicorn `:8000` |
| `docker-compose.yml` | `api` + Postgres 16 + one-shot `migrate` profile (`alembic upgrade head`) |
| `Makefile` | `docker-up`, `docker-migrate`, `test`, `lint`, `migrate` |
| Env examples | `.env.example`, `.env.staging.example`, `.env.production.example` |
| CI | **No** `.github/workflows` (or other CI configs) present *(baseline before Sprint 25a; Phase 25a adds `.github/workflows/ci.yml`)* |
| IaC / K8s / cloud | **None** (no Terraform, Pulumi, Helm, ECS task defs, etc.) *(baseline before Sprint 25a; Phase 25a adds `infra/terraform/**` + Compose overlays)* |
| Cloud vendor lock-in | **None** selected in code or docs; Sprint 22 explicitly deferred real cloud deploy |
| DB | PostgreSQL 16 via Compose; Alembic async migrations; Sprint 23 fail-closed SQLAlchemy backends |
| Observability in-app | Structured JSON logs; `X-Request-ID` / `request_id`; `/live` `/ready` `/health` |

### 1.2 Application readiness vs ops readiness

DealBrain is **application-ready for a production-shaped rehearsal**, not yet **operations-ready for public traffic**.

Gaps: no cloud topology, no managed DB backups, no secret vault, no CI/CD promotion, no log shipping, no paging alerts, no restore/rollback evidence.

### 1.3 Explicit non-goals (unchanged)

Real marketplace connector fleets, distributed workers as launch blockers, billing, multi-region active-active, formal compliance certifications, Redis rate limiting as hard M30 requirement.

---

## 2. Infrastructure architecture

### 2.0 Concrete deployment target (implementation contract)

**No cloud platform was previously selected in this repository.** Sprint 25 therefore selects **one** implementation target.

#### Selected target

**AWS single-region launch stack:**

| Concern | Concrete choice |
|---------|-----------------|
| Region | One AWS region (default recommendation: `us-east-1`; final region chosen at 25a kickoff and frozen) |
| API runtime | **EC2** instance(s) running **Docker Compose** (extends existing `docker-compose.yml` patterns) |
| Database | **Amazon RDS PostgreSQL 16** (separate instances for staging and production) |
| Secrets | **AWS Secrets Manager** → injected as container env at deploy/start |
| TLS / public entry | **Application Load Balancer (ALB)** terminating TLS; target group health check = `GET /ready` |
| Liveness | Compose/Docker restart policy + container `HEALTHCHECK` = `GET /live` |
| Logs | Container stdout → **CloudWatch Logs** |
| Metrics / alarms | **CloudWatch** metrics + alarms (ALB 5xx, target health, RDS CPU/storage, synthetics) |
| Synthetics | CloudWatch Synthetics (or equivalent scheduled HTTPS checks) against `/live` and `/ready` |
| Images | **GitHub Container Registry (GHCR)** — immutable digests |
| CI/CD | **GitHub Actions** (build/test/push/deploy); production promote is approval-gated |
| Migrate | One-shot Compose `migrate` service / host job: `alembic upgrade head` (same image digest) |

#### Why this target (Sprint 30 appropriateness)

1. Matches repository evidence: Dockerfile + Compose `api`/`db`/`migrate` are the only deploy artifacts.
2. Avoids introducing Kubernetes or ECS task-definition complexity before the team has any cloud ops history.
3. RDS provides automated backups, encryption at rest, and private networking needed for M30 without building backup tooling.
4. GitHub Actions + GHCR fill the empty CI gap with minimal new vendors.
5. ALB gives TLS and `/ready`-based traffic control without redesigning the app.
6. Single-region EC2+Compose keeps operator surface small for first public launch.

#### Assumptions

- Team can operate one AWS account (or staging/prod accounts) with IAM least privilege.
- Public DNS and ACM certificate are available for the ALB.
- Production traffic volume for Sprint 30 fits 1–2 small API hosts and a modest RDS instance.
- Bearer-token API auth remains (no cookie-session redesign); “secure cookies” gate is N/A unless cookie transport is later introduced.
- In-process rate limiting / launch cache remain per-process (acceptable at 1–2 replicas).

#### What remains portable

| Portable | Notes |
|----------|-------|
| OCI image from root `Dockerfile` | Rebuildable on any registry |
| Compose service shape (`api`, `migrate`) | Runnable on any Docker host |
| Probe URLs and readiness semantics | Sprint 22 contract |
| Alembic migration commands | DB-URL driven |
| Env-var Settings model | pydantic-settings unchanged |
| Structured JSON logs + `request_id` | Shipable to any log store |

#### What is provider-specific (AWS)

| Provider-specific | Notes |
|-------------------|-------|
| VPC / security groups / IAM | AWS networking and identity |
| RDS instance classes, subnet groups, backup API | AWS managed Postgres |
| Secrets Manager ARNs + IAM retrieve | AWS secret injection |
| ALB listener rules, target groups, ACM | AWS edge |
| CloudWatch log groups, alarms, synthetics | AWS observability |
| GitHub Actions OIDC → AWS IAM role | Deploy auth pattern |

**Do not treat ECS/Fargate, EKS, Cloud Run, or Compose-on-non-AWS as equal M30 targets.** A future migration off AWS is allowed architecturally because the app artifact remains an OCI image + env config, but it is **out of Sprint 25/30 scope**.

### 2.1 Target topology (AWS single region)

```
                         Internet
                             │
                             ▼
                   ┌───────────────────┐
                   │ ALB (TLS / ACM)   │  health: GET /ready
                   └─────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     ┌─────────────────┐           ┌─────────────────┐
     │ EC2 + Compose   │           │ EC2 + Compose   │  M30: ≥1; prefer 2
     │ api:8000        │           │ api:8000        │  same image digest
     └────────┬────────┘           └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             ▼
                   ┌───────────────────┐
                   │ RDS PostgreSQL 16 │  private subnets
                   │ (env-isolated)    │
                   └───────────────────┘

Side planes: Secrets Manager · GHCR · GitHub Actions · CloudWatch Logs/Alarms/Synthetics
Migrate: one-shot job on deploy host (Compose profile) — never at API startup
```

### 2.2 Component responsibilities

| Component | Responsibility |
|-----------|----------------|
| API container | Existing DealBrain image; uvicorn `:8000` |
| RDS | System of record (Sprint 23 + prior SQL tables) |
| Migrate job | `alembic upgrade head` once per release per env |
| Secrets Manager | `DATABASE_URL`, AI keys, admin material |
| ALB | TLS + `/ready` membership |
| CloudWatch | Logs, host/RDS/ALB metrics, alarms, synthetics |
| GHCR | Immutable image digests |
| GitHub Actions | CI gates + deploy orchestration |

### 2.3 Scaling posture

| Phase | Topology |
|-------|----------|
| **M30** | 1–2 EC2 API hosts; 1 primary RDS per env; no Redis |
| **P30+** | More hosts; connection pooling; optional Redis; Multi-AZ RDS if not already on |
| **FUT** | Autoscaling / ECS or K8s migration / read replicas / multi-region |

---

## 3. Environment strategy and isolation contract

### 3.1 Environments

Four environments are recognized. `APP_ENV` for running API processes remains `development` | `staging` | `production` (existing Settings). **test** is a CI/ephemeral environment, not a long-lived cloud stack.

### 3.2 Environment isolation contract (**M30**)

| Dimension | local | test | staging | production |
|-----------|-------|------|---------|------------|
| **Purpose** | Developer workstation | CI / ephemeral verification | Pre-prod rehearsal | Public traffic |
| **Database** | Local Compose Postgres **or** memory backends per Settings | Ephemeral Postgres in CI (or SQLite only where existing tests already allow); destroyed after job | **Dedicated RDS PostgreSQL 16 instance** (or dedicated DB + role on a staging-only server). Credentials unique to staging | **Separate RDS PostgreSQL 16 instance**. Credentials unique to production. **Never** shared with staging |
| **Secrets** | `.env` (gitignored); example files only in git | CI secrets / OIDC; no prod secrets | AWS Secrets Manager path `dealbrain/staging/*` | AWS Secrets Manager path `dealbrain/production/*`. **Production secret IAM denied to staging roles** |
| **Service credentials** | Dev/demo tokens allowed | Synthetic tokens in tests | Staging-only admin tokens; `DEMO_LAUNCHER` off or tightly gated | No demo tokens; `ALLOW_DEMO_RESET_TOKENS=false` |
| **External integrations** | Simulated / disabled live HTTP by default | Mocked | Optional live AI with staging keys only | Live integrations only behind explicit flags + prod keys |
| **Logging destination** | Local stdout | CI job logs | CloudWatch log group `/dealbrain/staging/api` | CloudWatch log group `/dealbrain/production/api` |
| **Monitoring destination** | Optional local | CI summaries | CloudWatch dashboards/alarms labeled `env=staging` (no page by default) | CloudWatch dashboards/alarms labeled `env=production` (P1 pages) |
| **Deployment authority** | Developer | GitHub Actions on PR/`main` | GitHub Actions deploy-staging (protected env optional) | GitHub Actions deploy-production **requires human approval**; no direct laptop deploys for normal releases |
| **Data policy** | Disposable | Synthetic fixtures only | Synthetic or explicitly sanitized data only. **No unsanitized production copies** | Real customer/operational data. Export/scrub process required before any copy to lower envs |
| **Backup policy** | None required | None | Automated RDS backups (≥7 days retention); restore drills target staging | Automated RDS backups (**M30** daily); retention ≥30 days; pre-migrate snapshot; restore drill evidence required before launch |

### 3.3 Mandatory isolation rules

1. Staging and production use **separate RDS instances** (preferred) or, if cost-constrained, **isolated databases with separate credentials on separate logical boundaries** — never shared credentials.
2. Production credentials are **never** available to staging roles, staging hosts, or staging CI environments.
3. Production data is **not** copied to staging without an explicit sanitization process and recorded approval.
4. Staging failure (deploy, migrate, load test, data corruption) must **not** affect production control planes, secrets, or data paths.
5. Every alert, log stream, dashboard, and synthetic check **must** include an `environment` label/dimension (`local` | `test` | `staging` | `production`).

### 3.4 Promotion model

```
PR + CI (test) → merge → build immutable image → deploy staging
      → staging verify → manual prod approval → promote SAME digest to production
```

Production **must not rebuild** the image (§8).

---

## 4. Configuration management

### 4.1 Sources of truth

| Layer | Source | Mutable at runtime? |
|-------|--------|---------------------|
| Build | Image labels / git SHA | No |
| Deploy config | Non-secret env in Compose overlays / params | Restart to apply |
| Secrets | Secrets Manager → env | Restart to apply |
| Feature flags | Existing Settings / launch flags | Restart (existing launch APIs unchanged) |

No new dynamic config service for M30.

### 4.2 Production required posture (app Settings)

Enforce existing `.env.production.example` / Sprint 23 rules via deploy-time + startup gate (§11):

- `APP_ENV=production`, `APP_DEBUG=false`
- Operational backends `sqlalchemy`
- `ALLOW_DEMO_RESET_TOKENS=false`, `DEMO_LAUNCHER_ENABLED=false`, `SEED_DEMO_DATA=false`
- `LAUNCH_STRICT_STARTUP=true`
- Explicit `CORS_ORIGINS` (no `*`)
- `OPENAPI_PUBLIC_DOCS=false` unless approved
- Rate limiting, security headers, structured logging enabled

---

## 5. Secrets management

### 5.1 Principles

1. No secrets in git, images, or OpenAPI examples (**M30**).
2. Inject at runtime as env vars (compatible with current Settings).
3. Rotate without image rebuild.
4. Staging and production secret paths and IAM are isolated (§3.2).
5. Application redaction (logs, launch export) remains authoritative for app output.

### 5.2 Secret inventory

| Secret | staging | production |
|--------|---------|------------|
| `DATABASE_URL` | staging RDS | production RDS |
| AI provider keys (if live) | staging keys | production keys |
| Admin / internal tokens | staging-only | prod-only; no demo tokens |
| Deploy role credentials | Actions OIDC → staging role | Actions OIDC → prod role |

### 5.3 Exclusions from IaC state and git

Terraform state and git must **never** store raw secret values. Secrets Manager holds values; Terraform may reference ARNs only. Compose files reference secret names/ARNs via deploy scripts, not plaintext.

---

## 6. Deployment topology

Covered in §2.0–§2.2. M30 sizing start: API 0.5–1 vCPU / 1–2 GiB per host; RDS 2 vCPU / 4–8 GiB SSD with automated backups; DB not publicly reachable.

---

## 7. Infrastructure-as-code decision

### 7.1 Chosen approach

**Split representation (intentionally thin):**

1. **Terraform** — AWS foundation only (VPC, subnets, security groups, EC2, RDS, IAM, Secrets Manager stubs/ARNs, ALB, ACM data sources, CloudWatch log groups/alarms).
2. **Docker Compose overlays** — application runtime (`api`, `migrate`) consuming the root `Dockerfile` image.
3. **GitHub Actions workflows** — `ci.yml` validation gates, `build-image.yml` releasable publish, staging deploy, production promote.

This avoids Kubernetes/ECS abstraction for a single-region Compose-native app while still keeping cloud resources reviewable as code.

### 7.2 Repository locations (created during implementation — not by this doc)

| Path | Contents |
|------|----------|
| `infra/terraform/` | Root module + `environments/staging` + `environments/production` (or workspaces) |
| `infra/compose/` | `docker-compose.staging.yml`, `docker-compose.production.yml` overlays |
| `.github/workflows/` | `ci.yml`, `build-image.yml`, `deploy-staging.yml`, `deploy-production.yml` |
| `docs/runbooks/` | RB-01…RB-10 procedures (implementation) |

Root `Dockerfile` and root `docker-compose.yml` remain the local/dev baseline; production does not replace them without overlays.

### 7.3 State management

| Concern | Expectation |
|---------|-------------|
| Terraform state | Remote backend (S3 + DynamoDB lock) **per environment** or clearly separated state keys |
| State secrets | No plaintext DB passwords in state; use Secrets Manager / ARN references |
| Locking | State lock required; concurrent `terraform apply` forbidden |
| Compose | Not stateful; hosts pull immutable digests |
| Drift | `terraform plan` in CI for staging/prod on infra PRs (**M30**) |

### 7.4 Environment separation in IaC

- Separate Terraform vars/backends for staging vs production.
- Separate AWS tags: `Project=dealbrain`, `Environment=staging|production`.
- Separate Secrets Manager prefixes.
- Separate RDS identifiers.
- Separate ALB / DNS names.

### 7.5 Secrets exclusions

- No `.tfvars` with live secrets committed.
- No secret values in Compose committed files.
- CI uses OIDC to assume deploy roles; long-lived AWS access keys avoided when possible (**M30** goal; documented temporary exception requires expiry date).

### 7.6 Validation strategy

| Gate | How |
|------|-----|
| `terraform fmt` / `validate` | CI on infra changes |
| `terraform plan` | CI; apply only via controlled workflow |
| Compose config sanity | `docker compose -f … config` in CI |
| Image + app tests | Existing pytest + OpenAPI drift |
| Deploy verify | `/live`, `/ready`, smoke HTTP after deploy |
| Destroy protection | Production RDS deletion protection enabled |

---

## 8. CI/CD and release / image promotion contract

### 8.1 Image build ownership

| Step | Owner |
|------|-------|
| Define `Dockerfile` | Application repo (already exists) |
| Validation CI | `.github/workflows/ci.yml` — lint, tests, contracts, Terraform/Compose checks, Docker **build without push** |
| Releasable image publication | `.github/workflows/build-image.yml` only — after CI succeeds on `main` (`workflow_run` / gated `workflow_dispatch`) |
| Authoritative tagging | Immutable: `ghcr.io/<org>/<repo>:sha-<full_git_sha>` (40-char SHA) |
| Deployment authority | Image digest `sha256:…` (and the release manifest that records it) — **never** a mutable tag |
| Mutable / convenience tags | `latest`, `ci-latest`, branch names, `staging` / `production` pointers are **informational only**; they confer **no** deployment authority and must resolve to a previously built digest if used at all |

Sprint 25b.1 implements the validation/publication split above. Staging and production deploy workflows remain later phases (25b.3–25b.4).

### 8.2 Promotion contract (**M30**)

| Stage | Rule |
|-------|------|
| **Validation** | `ci.yml` gates merge/main quality; it does **not** publish releasable GHCR images |
| **Image build** | `build-image.yml` builds once from git SHA after CI is green; pushes to GHCR; records digest + checksummed release manifest artifact |
| **Immutable tagging** | `sha-<full_git_sha>` is the only publish tag in 25b.1; digest is canonical identity |
| **Digest recording** | Store `GIT_SHA`, `IMAGE_REF`, `IMAGE_DIGEST`, workflow run URL in deploy evidence / release manifest |
| **Staging deployment** | Pull **that digest** on staging hosts; run migrate job; start/reload API |
| **Staging verification** | `/live` OK; `/ready` with `persistence_level` compatible with READY; smoke critical paths; CI contract suite already green |
| **Production approval** | GitHub Environment protection rule — human approver; checklist includes staging evidence link |
| **Production deployment** | Pull **the identical digest** already verified on staging; **do not rebuild**; migrate then API rollout |
| **Release evidence** | Digest, alembic revision post-migrate, probe JSON, smoke results, approver identity, timestamps |
| **Rollback evidence** | Prior digest, time of rollback, post-rollback probe JSON, operator identity |

### 8.3 Pipeline sketch

```
PR / branch: ci.yml → lint → unit/contract/OpenAPI drift → compose/terraform → docker build (push: false)
main (CI green): build-image.yml → build once → push sha-<full_git_sha> + digest
                 → release-manifest artifact
later phases:    deploy staging (same digest) → migrate → verify
                 → manual approval → deploy production (same digest) → migrate → verify → hold window
```

### 8.4 Forbidden

- Publishing releasable images from `ci.yml` (validation-only).
- Treating `latest`, `ci-latest`, or other mutable tags as deployment authority.
- Rebuilding for production from the same commit “to pick up secrets” (secrets are runtime).
- Tagging `production` to an image that never ran on staging (except documented P1 hotfix with incident record).
- Skipping OpenAPI drift / contract tests.

---

## 9. Observability contract

### 9.1 Request ID propagation (existing — preserve)

Already implemented in Sprint 22 middleware (`app/core/middleware/request_logging.py`):

- Inbound `X-Request-ID` reused, else generate `req-<12 hex>`.
- Stored on `request.state.request_id`.
- Echoed on response as `X-Request-ID`.
- Included in structured logs and error envelope `request_id`.

Platform log shipping must preserve this field. Operators correlate ALB access logs ↔ app logs via `request_id` when present.

### 9.2 Logs contract

| Item | Requirement |
|------|-------------|
| **Required fields** | `timestamp`, `level`, `message`/`event`, `environment`, `service=dealbrain-api`, `request_id` (when request-scoped), `http.method`, `http.path`, `http.status`, `duration_ms` for request logs |
| **Retention** | staging ≥14 days; production ≥30 days (**M30**); 90 days (**P30+**) |
| **Environment labels** | CloudWatch dimension / log field `environment=staging|production` |
| **Redaction** | No secrets, access tokens, passwords, `Authorization` headers, API keys, or sensitive PII in logs (app redaction + platform ban on body logging) |
| **Destination** | CloudWatch Logs per §3.2 |

### 9.3 Metrics contract

| Item | Requirement |
|------|-------------|
| **Required metrics** | ALB `HTTPCode_Target_5XX`, target healthy host count, API host CPU/mem, RDS CPU/free storage/connections, synthetic success |
| **Environment labels** | All metrics dimensions include `Environment` |
| **Retention** | **M30** minimum 30 days actionable |
| **Dashboard ownership** | Ops lead owns CloudWatch dashboards; app `/api/v1/launch/dashboard` is **not** the infra dashboard |

### 9.4 Synthetic probes contract

| Item | Requirement |
|------|-------------|
| **Checks** | `GET /live`, `GET /ready` over public HTTPS (prod + staging) |
| **Interval** | ≤ 1 minute (**M30**) |
| **Required fields in results** | `environment`, `endpoint`, `http_status`, `success`, `latency_ms`, `timestamp` |
| **Success criteria** | `/live` 200; `/ready` 200 with readiness compatible with traffic (prod must not stay DEGRADED/NOT_READY unnoticed) |

### 9.5 Alerts contract

| Item | Requirement |
|------|-------------|
| **Severity levels** | P1 page; P2 urgent; P3 ticket; P4 backlog (§10) |
| **Routing** | P1 → on-call pager; P2 → ops chat (+ page if sustained); P3 → ticket; staging defaults to P3 |
| **Paging threshold** | Prod `/ready` fail ≥2 min; prod `/live` fail ≥2 min; prod 5xx rate above §12 threshold for 5 min |
| **Deduplication** | Related alarms for same env+service fold into one incident for 15 min unless severity escalates |
| **Runbook links** | Every alarm action description includes RB-id URL |
| **Environment** | Alarm name/description must include `staging` or `production` |

---

## 10. Alerting strategy (severity detail)

| Severity | Examples | Response |
|----------|----------|----------|
| **P1** | Prod `/ready` or `/live` down >2 min; DB unreachable; security breach | Page on-call |
| **P2** | Elevated 5xx; latency SLO burn; disk <20% | Urgent; page if sustained |
| **P3** | Staging failures; cert expiry <14 days; backup job failed | Ticket |
| **P4** | Capacity forecasts | Backlog |

Minimum M30 alerts: prod synthetics `/live`+`/ready`, prod 5xx, RDS storage/CPU critical, deploy/migrate failure, TLS expiry if operator-managed.

---

## 11. Health/readiness integration and production configuration gate

### 11.1 Probe wiring (**M30**)

```
Docker HEALTHCHECK / host restart  →  /live
ALB target health                  →  /ready
Humans / incident triage           →  /health
```

Persistence levels remain Sprint 22/23 semantics.

### 11.2 Production configuration gate (fail-closed)

**Rule:** Invalid mandatory production configuration must prevent the process from becoming eligible for public traffic. Prefer fail at **startup** with `LAUNCH_STRICT_STARTUP=true`; additionally fail **deploy verification** if `/ready` is not READY.

| Gate item | Mandatory production expectation | Fail mode |
|-----------|----------------------------------|-----------|
| Environment identity | `APP_ENV=production` | Startup fatal / deploy abort |
| Debug | `APP_DEBUG=false` | Startup fatal (existing validation) |
| Demo seed | `SEED_DEMO_DATA=false`; `PRICE_HISTORY_SEED_DEMO_MOCK=false` | Startup fatal / warning→fatal in gate |
| Demo launcher / reset tokens | both false | Startup fatal |
| Persistence backends | sqlalchemy for required domains | Startup fatal |
| Production database URL | Present, well-formed, points at **production RDS** (host allowlist / secret ARN binding) | Startup fatal if malformed; deploy gate verifies secret binding |
| Secret strength/presence | `DATABASE_URL` password not placeholder (`CHANGE_ME`/empty); AI keys present **if** live HTTP enabled | Deploy precheck abort |
| Allowed origins | `CORS_ORIGINS` explicit; no `*` | Startup fatal |
| Trusted hosts | ALB/Host allowlist at edge; app documents expected public hostnames in deploy config | Deploy abort if DNS/ALB host mismatch |
| Secure cookies | **N/A for M30** (bearer header auth; no cookie session transport). If cookies introduced later, `Secure; HttpOnly; SameSite` required | Track as future gate |
| TLS / proxy assumptions | Public clients terminate TLS at ALB; app may speak HTTP to ALB in private subnets; `X-Forwarded-*` trusted only from ALB | Misconfig = deploy abort |
| Logging configuration | `STRUCTURED_LOGGING_ENABLED=true`; level not DEBUG | Deploy gate warning→abort for DEBUG |
| Monitoring configuration | Synthetics + alarms enabled for `environment=production` | Launch checklist abort |
| Migration state | `alembic current == head` after migrate job; `/ready` persistence components OK | Release blocked |
| Strict startup | `LAUNCH_STRICT_STARTUP=true` | Required so validation errors abort boot |

ALB must not register targets that fail `/ready`. A boot-looping bad config is preferable to serving public traffic with open CORS or memory backends.

---

## 12. Initial service objectives (Sprint 30 launch)

These are **initial launch objectives**, not permanent contractual guarantees. Revisit after 30 days of production data.

| Objective | Initial launch threshold | Measurement |
|-----------|--------------------------|-------------|
| Service availability | ≥ **99.5%** monthly | Synthetic `/ready` success ratio |
| Readiness probe success rate | ≥ **99.5%** monthly | Synthetic `GET /ready` |
| Synthetic `/live` success | ≥ **99.9%** monthly | Synthetic `GET /live` |
| API 5xx error rate | < **1%** of requests over 5-minute windows sustained <15 min | ALB target 5xx / request count |
| API latency | p50 < **300 ms**; p95 < **1.5 s**; p99 < **3 s** for core read APIs under expected launch load | ALB target response time and/or log `duration_ms` |
| Deployment success | ≥ **95%** of production promotes succeed without emergency rollback | Release evidence log |
| Backup success | **100%** of scheduled daily backups succeed over rolling 7 days before launch; alert on failure | RDS backup events |
| Restore-point age | Latest automated restore point ≤ **24 hours** (**M30**); ≤ **1 hour** target (**P30+** PITR) | RDS backup timestamp |
| RPO | ≤ **24 hours** (**M30**) | Backup/PITR capability |
| RTO | ≤ **4 hours** (**M30**) for in-region restore + API bring-up | Timed restore drill |
| P1 alert acknowledgement | ≤ **15 minutes** | On-call metrics / incident log |
| Staging soak before launch | ≥ **24 hours** continuous healthy synthetics | Staging dashboard |

---

## 13. Backup, restore evidence, and disaster recovery

### 13.1 Backup contract (**M30**)

| Item | Requirement |
|------|-------------|
| Frequency | Automated RDS backups **daily**; continuous/PITR enabled if available on instance class |
| Retention | Production ≥ **30 days**; staging ≥ **7 days** |
| Encryption | Encryption at rest enabled (RDS default KMS) |
| Pre-migrate | On-demand snapshot (or verified current restore point <15 min old) **before** production migrate |
| Failure alerting | Backup failure → P3 (staging) / P2 (production) with RB-06 |

### 13.2 Restore drill contract (**M30**)

A configured backup **without** a successful restore drill is **not complete**.

| Item | Requirement |
|------|-------------|
| Restore test environment | Staging account/VPC or isolated restore subnet; **never** overwrite production in-place for drills |
| Procedure | (1) select snapshot (2) restore to new RDS instance (3) point staging API at restored endpoint with staging secrets pattern (4) run migrate if needed (5) verify probes (6) destroy restored instance |
| Verification criteria | `/live` 200; `/ready` READY; `alembic current` readable; sample read API 200; row-count smoke vs pre-drill note |
| Evidence to retain | Date, operator, snapshot ID, restored instance ID, elapsed time (RTO sample), probe JSON, pass/fail, follow-ups |
| Acceptable RPO/RTO at launch | RPO ≤24h; RTO ≤4h (§12) |

### 13.3 DR scope

Single-region. Multi-region = **FUT**. Prefer restore-to-known-good over heroic repair. Domain “fixes” must not rewrite ranking rules.

---

## 14. Rollback categories

**Database rollback is not equivalent to application rollback.**

### 14.A Application rollback

| Item | Rule |
|------|------|
| Mechanism | Redeploy **previous known-good image digest** from GHCR |
| Rebuild | **Forbidden** — pull prior digest only |
| Steps | (1) declare rollback (2) set Compose/image to prior digest (3) restart API (4) leave DB schema as-is if compatible (5) validate |
| Validation | `/live`, `/ready`, smoke critical paths, 5xx rate normalized, evidence logged |

### 14.B Database-compatible rollback

Application rollback is **allowed only when** the prior application version is compatible with the **current** database schema (expand/contract: additive migrations preferred).

Compatibility check (architecture-level):

- Migration since prior digest was **additive only** (new tables/columns nullable/unused), **or**
- Explicit compatibility note in release evidence states old app works with new schema.

If incompatible → do **not** only roll back the app; use 14.C or 14.D.

### 14.C Forward-fix migration

**Preferred** response for irreversible or data-bearing schema problems:

- Ship a new Alembic revision that corrects data/schema
- Build new image → staging → prod promote
- Keep system forward

### 14.D Restore from backup

**Reserved** for destructive migration failure or data corruption.

| Item | Expectation |
|------|-------------|
| Data loss window | Up to configured RPO (≤24h M30) unless PITR narrows it |
| Recovery time | Target ≤ RTO 4h |
| Steps | Snapshot/PITR restore → verify → point API → validate → incident review |
| Approval | Incident commander + ops lead |

---

## 15. Database migration ownership

### 15.1 Ownership boundary

- **Alembic revision content / schema design:** Sprint 23 (persistence owners)  
- **Execution in environments:** Sprint 25 release job  

### 15.2 Hard rules (**M30**)

1. Alembic migrations run as a **dedicated release job** (Compose `migrate` profile / one-shot container) using the **release image digest**.
2. **Application replicas do not run migrations at startup.**
3. **Only one migration job may execute per environment at a time.**
4. Migration execution is **auditable** (CI job URL, operator, digest, `alembic current` before/after, exit code).
5. Production migrate requires a **backup or verified recovery point** first (§13).
6. **API rollout proceeds only after migration success.**
7. **Migration failure blocks the release** (no partial “start API anyway” in production).

### 15.3 Concurrency / locking strategy (architecture level)

| Control | Mechanism |
|---------|-----------|
| CI/CD mutex | Per-environment GitHub Environment concurrency group `migrate-staging` / `migrate-production` — queue length 1 |
| Database lock | Rely on Alembic’s transaction + `alembic_version` table; do not run parallel Alembic processes against the same DB |
| Host lock | Deploy script takes a simple exclusive lock file/slot on the bastion/deploy host before migrate (e.g., `flock`) so two operators cannot double-run |
| API overlap | Old API may continue serving during additive migrate; new API starts only after migrate exit 0 |
| Failure | Non-zero migrate exit → pipeline fails → alert → no API image switch |

### 15.4 Expand / contract

Prefer additive migrations so 14.B application rollback remains possible. Destructive changes require explicit release note + restore plan (14.D).

### 15.5 Forbidden

- Manual `psql` DDL as normal production process  
- `alembic downgrade` in production without incident approval  
- Starting API when required migrations are pending (should surface NOT_READY)

---

## 16. Release process

Aligned with §8. Standard path: CI green → digest recorded → staging migrate+deploy+verify → approval → production backup gate → migrate → deploy same digest → verify → hold window 30–60 min.

Hotfix: branch from last good prod source SHA; prefer staging; document exceptions.

Sprint 24 compatibility: OpenAPI drift must stay green; no `/api/v2`.

---

## 17. Incident response

Roles: incident commander, ops lead, app lead, comms. Capture digest, alembic revision, probe JSON, `request_id`s, recent changes. Security: rotate secrets; revoke sessions via existing capabilities; preserve logs.

---

## 18. Security hardening

TLS at ALB; private RDS; non-root container; Secrets Manager; Sprint 22 headers/CORS/rate limits on; image CVE policy for high/critical before promote; no demo tokens in prod. WAF/CDN/Redis/mesh = P30+/FUT.

---

## 19. Operational runbooks

Mandatory **M30** runbooks RB-01…RB-10 (deploy staging/prod, app rollback, migrate, probe triage, backup verify, restore, secret rotation, cert renewal, P1 incident). Each alert links a runbook. Implementation creates `docs/runbooks/` during phases 25d–25e.

---

## 20. Risks, phases, and M30 acceptance evidence

### 20.1 Key risks

| Risk | Mitigation |
|------|------------|
| Treating local Compose DB as production | RDS mandatory for staging/prod |
| Parallel migrates | Concurrency locks (§15.3) |
| Prod rebuild drift | Digest promotion only (§8) |
| Backup without restore proof | Restore drill gate (§13.2) |
| Scope creep to EKS/multi-region | Hard M30 cut; 25f–h deferred |
| Architecture lock violations | Evidence matrix + review |

### 20.2 Phase refinement (25a–25e implementation sequence)

#### Phase 25a — Foundation & registry

| | |
|--|--|
| **Objective** | Establish AWS foundation + GHCR + Terraform skeleton for staging |
| **Allowed repo changes** | `infra/terraform/**`, `infra/compose/**` stubs, `.github/workflows/ci.yml` + image build workflow, docs/runbook stubs; **no** domain/API/schema changes |
| **Dependencies** | Architecture contract approved; AWS account; GitHub package permissions |
| **Deliverables** | Remote Terraform state; staging VPC/network plan applied or plan-only with approval; GHCR repo; CI lint/test on PR |
| **Tests** | `terraform validate`; existing pytest on PR |
| **Operational evidence** | Links to Terraform state backend; sample CI run URL |
| **Exit criteria** | CI green on `main`; Terraform validates; GHCR push of a test digest succeeds |

#### Phase 25b — Staging data plane & deploy

| | |
|--|--|
| **Objective** | Staging RDS + Secrets Manager + EC2 Compose deploy by immutable digest (after `build-image.yml`) |
| **Allowed repo changes** | Staging Terraform apply configs; staging Compose overlay; `deploy-staging` workflow; secret name docs |
| **Dependencies** | 25a complete |
| **Deliverables** | Staging API reachable via ALB TLS; Secrets injected; migrate job works |
| **Tests** | Staging smoke: `/live`, `/ready`, OpenAPI drift still in CI |
| **Operational evidence** | Staging URL; screenshot/JSON of `/ready`; workflow run deploying a digest |
| **Exit criteria** | Staging `/ready` READY with sqlalchemy backends; staging≠prod credentials proven |

#### Phase 25c — Observability & paging path

| | |
|--|--|
| **Objective** | Logs, metrics, synthetics, alert routing |
| **Allowed repo changes** | Terraform alarms/synthetics; dashboard JSON/docs; alert runbook links |
| **Dependencies** | 25b |
| **Deliverables** | CloudWatch log ingestion; synthetics on staging (and prod wiring ready); alarm → chat/pager test |
| **Tests** | Controlled failure test (stop staging API) proves alert fires and includes `environment=staging` |
| **Operational evidence** | Alert screenshot; log query showing `request_id`; synthetic history |
| **Exit criteria** | Alert test recorded; logs retained per contract; no secret leakage in sampled logs |

#### Phase 25d — Backup, restore drill, runbooks

| | |
|--|--|
| **Objective** | Prove data recovery and publish RB-01…RB-10 |
| **Allowed repo changes** | Runbook markdown; backup alarm config; drill checklist templates |
| **Dependencies** | 25b (RDS), 25c (alerts for backup failure) |
| **Deliverables** | Automated backups on; restore drill completed; runbooks reviewed |
| **Tests** | Restore drill verification criteria (§13.2) |
| **Operational evidence** | Drill report with RTO sample; backup retention settings screenshot/API output |
| **Exit criteria** | Drill **passed**; backup failure alarm exists; runbooks linked from alarms |

#### Phase 25e — Production dry-run, rollback, config gate

| | |
|--|--|
| **Objective** | Production-equivalent stack + promotion/rollback/config-failure evidence |
| **Allowed repo changes** | Production Terraform/Compose/workflows; protection rules; evidence templates |
| **Dependencies** | 25a–25d |
| **Deliverables** | Prod ALB+EC2+RDS+secrets; digest promote path; rollback rehearsal; fail-closed config test |
| **Tests** | Prod dry-run migrate+deploy; rollback to prior digest; boot with bad config must not pass `/ready` / must fail strict startup |
| **Operational evidence** | Release evidence bundle; rollback evidence; config-failure logs; isolation proof (prod secrets inaccessible from staging role) |
| **Exit criteria** | All §20.3 evidence rows for M30 marked complete or waived with written risk acceptance |

#### Phases 25f–25h — Deferred (not required to unblock launch)

| Phase | Focus | Priority |
|-------|-------|----------|
| **25f** | Deeper image scanning cadence, egress lock-down, public status page | **P30+** |
| **25g** | Redis shared limits/cache, CDN/WAF depth, Multi-AZ tuning | **P30+** |
| **25h** | Multi-region DR, autoscaling policies, possible ECS/K8s migration | **FUT** |

### 20.3 M30 acceptance evidence matrix

| Capability | Implementation artifact | Automated verification | Manual verification | Required evidence | Owner | Blocking severity |
|------------|-------------------------|------------------------|---------------------|-------------------|-------|-------------------|
| Staging deployment | `deploy-staging` workflow + Compose overlay + Terraform staging | Workflow success; curl `/ready` in job | Browse staging URL; review logs | Workflow URL + `/ready` JSON | Ops | **Block launch** |
| Production deployment | `deploy-production` + approval env | Workflow success after approval | Approver checklist signed | Release evidence bundle | Ops + eng lead | **Block launch** |
| Isolated PostgreSQL | Separate RDS instances/creds | Terraform plan shows distinct identifiers | IAM/secret path review | Diagram + RDS IDs (non-secret) | Ops | **Block launch** |
| Secrets injection | Secrets Manager + deploy hook | Deploy fails if secret missing | Confirm no plaintext in git/state | Secret ARNs list + redacted env dump | Ops | **Block launch** |
| Image promotion | GHCR digest promote | Prod workflow uses staging digest input; rebuild step absent | Compare digests staging vs prod | Digest equality record | Ops | **Block launch** |
| CI gates | `.github/workflows/ci.yml` | lint, pytest, OpenAPI drift required | Spot-check failed PR cannot merge | Sample green/red CI runs | Eng | **Block launch** |
| Migration job | Compose migrate one-shot | Job exit code gate in workflow | `alembic current` before/after | Migrate logs + revisions | Ops | **Block launch** |
| Readiness/liveness routing | ALB `/ready`; Docker `/live` | Synthetics + target health checks | Pull instance from ALB when `/ready` fails | ALB health check config screenshot | Ops | **Block launch** |
| Logging | CloudWatch log groups | Agent/driver shipping check | Query by `request_id`; confirm redaction | Log query screenshots | Ops | **Block launch** |
| Monitoring | CloudWatch dashboards | Alarms in Terraform/CI | Dashboard review | Dashboard URL | Ops | **Block launch** |
| Synthetic probes | CloudWatch Synthetics | Success metrics | Force fail test | Synthetic history + fail test record | Ops | **Block launch** |
| Paging | Pager integration on P1 | Alert test hooks | Ack within 15m objective | Page + ack timestamps | On-call | **Block launch** |
| Backups | RDS automated backups | AWS backup event / describe | Confirm retention settings | Backup window + retention proof | Ops | **Block launch** |
| Restore drill | RB-07 execution | N/A (manual drill) | Full §13.2 procedure | Drill report with RTO | Ops | **Block launch** |
| Rollback rehearsal | Prior digest redeploy | Workflow/docs path | Execute on staging or prod dry-run window | Rollback evidence pack | Ops | **Block launch** |
| Runbooks | `docs/runbooks/RB-*.md` | Link presence in alarms | Tabletop walkthrough RB-01,03,04,05,07,10 | Sign-off checklist | Ops | **Block launch** |
| TLS | ALB + ACM | HTTPS synthetics | Certificate details review | Cert ARN + HTTPS proof | Ops | **Block launch** |
| Private database | SG: no public RDS | Terraform assert / AWS config rule | Port-scan attempt from public internet fails | SG rules export | Ops | **Block launch** |
| Fail-closed configuration | `LAUNCH_STRICT_STARTUP` + deploy precheck | CI/staging negative test with bad CORS/debug | Prod-like negative test recorded | Failure logs showing boot/deploy abort | Eng + ops | **Block launch** |
| Environment isolation | Separate accounts/roles/secrets | IAM policy tests where feasible | Confirm staging role denied prod secrets | IAM simulation / access denial proof | Ops | **Block launch** |
| Architecture locks preserved | Diff review vs lock | Contract tests still green | Architecture review sign-off | Sign-off + “no domain/API/schema change” statement | Arch eng | **Block launch** |

---

## 21. Definition of Done

### 21.1 Architecture contract (this document)

- [x] Concrete deployment target selected (AWS EC2+Compose+RDS+ALB+SM+CW; GHCR; GitHub Actions)
- [x] IaC decision recorded (Terraform + Compose overlays + Actions)
- [x] Environment isolation contract finalized
- [x] Release/image promotion contract finalized
- [x] Migration ownership and locking finalized
- [x] Rollback categories A–D finalized
- [x] Initial launch objectives defined
- [x] Observability contract defined
- [x] Backup/restore evidence requirements defined
- [x] Production configuration gate defined
- [x] M30 evidence matrix defined
- [x] Phases 25a–25e refined; 25f–h deferred
- [ ] Stakeholder sign-off that this contract is implementation-ready

### 21.2 Sprint 25 implementation DoD (observable evidence required)

Sprint 25 is **not** complete merely because infrastructure configuration files exist.

| Evidence requirement | Required |
|----------------------|----------|
| Staging deployment **demonstrated** (live URL + `/ready` JSON) | Yes |
| Production-equivalent **dry run** demonstrated | Yes |
| CI and release gates **passing** on the promoted digest | Yes |
| Migration process **demonstrated** (auditable job, one-at-a-time) | Yes |
| Backup **completed** (automated + verified settings) | Yes |
| Restore drill **completed** with retained report | Yes |
| Rollback rehearsal **completed** with retained evidence | Yes |
| Alerts **tested** (including environment label + paging path) | Yes |
| Runbooks **validated** (tabletop or live use) | Yes |
| Environment isolation **verified** (prod secrets denied to staging) | Yes |
| Production configuration failure **tested** (fail-closed) | Yes |
| Architecture locks **preserved** (no domain/API/schema redesign) | Yes |

Until the evidence matrix rows marked **Block launch** are complete (or explicitly risk-accepted in writing), Sprint 25 implementation is **incomplete** and Sprint 30 launch is **blocked**.

### 21.3 Explicit launch limitations (allowed if documented)

Single region; per-process rate limit/cache; simulated connectors / non-live notifications where already documented; intentionally memory-backed subsystems per Sprint 23 deferrals — must not be hidden by weakening `/ready`.

---

## Appendix A — Document map

| Existing doc | Relationship |
|--------------|--------------|
| `docs/LAUNCH_READINESS.md` | Probe/flag semantics — consume |
| `docs/DEPLOYMENT.md` | Local/compose — cloud extends via `infra/` |
| `docs/PRODUCTION.md` | App config — enforced by §11 gate |
| `docs/OPERATIONS.md` | Day-2 app ops — linked from runbooks |
| `docs/MONITORING.md` | Baseline — platform contract in §9 |
| `docs/BACKUP_RESTORE.md` | Config rehearsal only — DB DR is §13 |
| `docs/DATABASE_MIGRATIONS.md` | Alembic how-to — execution owned by §15 |
| `docs/SECURITY.md` | App controls — complement §18 |
| `docs/architecture/ARCHITECTURE_LOCK.md` | Ownership lock — Sprint 25 additive ops only |
| `docs/architecture/SPRINT_24_API_STABILITY.md` | CI must keep green |

## Appendix B — Architecture Lock additive note (apply during implementation kickoff)

| Sprint | Canonical ownership |
|--------|---------------------|
| 25 | Production infrastructure and operations on the selected AWS single-region Compose+RDS stack: Terraform/Compose/Actions, secrets injection, promotion by digest, migrate jobs, observability, backup/DR/rollback, runbooks — **does not** own domain engines, API contracts, persistence adapters, or readiness semantics |

## Appendix C — M30 one-page checklist

```
[ ] Staging live + /ready READY
[ ] Prod dry-run live + /ready READY
[ ] Separate RDS + secret paths
[ ] Digest staging == digest prod promote
[ ] CI lint/test/contract green
[ ] Migrate job audited; API does not migrate on boot
[ ] ALB /ready ; Docker /live
[ ] Logs in CloudWatch with request_id; no secrets
[ ] Synthetics + P1 page tested
[ ] Backup on; restore drill report filed
[ ] Rollback rehearsal filed
[ ] Runbooks RB-01..10 validated
[ ] Fail-closed bad-config test filed
[ ] Isolation proof filed
[ ] Architecture lock sign-off
```

---

**End of Sprint 25 implementation-ready architecture contract.**  
No infrastructure was implemented by this documentation change.
