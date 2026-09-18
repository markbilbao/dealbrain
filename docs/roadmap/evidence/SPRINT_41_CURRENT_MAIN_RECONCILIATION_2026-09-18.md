# Sprint 41 — Current-main production reconciliation (2026-09-18)

**Resulting status:** `SPRINT 41 PARTIALLY COMPLETE — PRODUCTION LIVE; ROLLBACK VALIDATION, WWW CANONICALIZATION, CDN/WAF OWNER DECISION, STAGING PRESERVATION, AND LIVE IAM SIMULATION REMAIN OPEN`

Sprint 41 is **not** COMPLETE / CLOSED.

This audit does **not** close Sprints 42, 43, 44, or 45.

**Explicit statement:** no production mutation occurred during this reconciliation. No Deploy Production, Rollback Production, Deploy Staging, Terraform apply, EC2 replacement, SSM command, RDS mutation, Secrets Manager mutation, IAM mutation, DNS/Cloudflare mutation, ACM mutation, ALB mutation, or Resend mutation was performed.

## Starting identities

| Item | Value |
|------|--------|
| Verified `origin/main` at branch creation | `4a4fe65fa7438c75208a0052f52b77f929ee3903` |
| Latest `origin/main` subject | Merge pull request #142 — Sprint 29: reconcile internal closeout against current main |
| Feature branch | `cursor/sprint41-production-reconciliation-c90f` |
| Audit date (UTC) | 2026-09-18 |
| Authority | [`../sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md`](../sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md) |
| This task | Read-only inspection + documentation/tests only |

`origin/main` matched the expected SHA before any edit.

## Verdict

Major Sprint 41 production-environment work is **live** after the Early Access production launch diversion. Production is not a documentation-only Terraform stack.

Sprint 41 still has **owned acceptance gaps**. Live production is not automatic Sprint 41 closure.

| Claim | Result |
|-------|--------|
| Isolated production AWS exists | **Yes** |
| Production deploy path exists and has succeeded | **Yes** — Deploy Production #5 and #6 |
| Production `/ready` READY | **Yes** (live, 2026-09-18) |
| Production rollback workflow exists | **Yes** |
| Production rollback validated against a real prior successful release | **No** |
| Accidental Rollback Production #1 counted as validation | **No** — fail-closed missing release object |
| `www` redirects to canonical apex | **No** — HTTPS 200 on `www.piqsavi.com` |
| CDN/WAF owner decision recorded | **No** — proposal only |
| Live IAM AccessDenied simulation filed | **No** |
| Staging currently green on same digest lineage | **No** — staging ALB 503; last success Deploy Staging #35 on a different SHA |
| Sprints 42–45 closed | **No** |

## Production architecture inventory (2026-09-18)

Read-only public DNS/HTTP plus GitHub Actions evidence. This agent had **no AWS CLI** and did **not** assume the production deploy role.

| Concern | Current evidence |
|---------|------------------|
| AWS account | `941035169846` (Deploy Production #6 evidence `aws_account_id`) |
| Region | `us-east-1` |
| Public domain | `piqsavi.com` |
| Canonical URL | `https://piqsavi.com` |
| Production ALB DNS | `dealbrain-production-alb-1597181926.us-east-1.elb.amazonaws.com` |
| Apex A records | `100.52.52.125`, `3.234.68.186` |
| `www` | CNAME → same production ALB (same A records) |
| TLS | Amazon RSA 2048 M01; CN `piqsavi.com`; SAN `piqsavi.com`, `www.piqsavi.com`; notBefore 2026-09-14; notAfter 2027-03-30 |
| HTTP→HTTPS | ALB `awselb/2.0` HTTP 301 to HTTPS (apex and www separately) |
| Production host at Deploy #6 | `i-0e49ddadd4ecc772d` |
| Host still current? | Application `/health.started_at` = `2026-09-15T02:07:14.315730+00:00`, matching Deploy #6 finish. No later Deploy Production run exists. Treat `i-0e49ddadd4ecc772d` as the current production host unless later replaced. |
| Live production git SHA | `3c514943a8a0ec34d1df97d5a329d3acb4a86e07` (Deploy #6). Current `main` `4a4fe65` is newer (PR #142 docs) and is **not** the live production digest. |
| Image digest | `sha256:e55021f1e07bae5f2fc8a3bab038c71dc28ccad5cdc5abe76760f0cb8b942d90` |
| Release id | `rel-20260915T020323Z-3c514943a8a0` |
| Assumed deploy role | `arn:aws:iam::941035169846:role/dealbrain-production-gha-deploy` |
| Release/evidence bucket | `dealbrain-production-release-artifacts-941035169846` |
| GitHub Environment | `production` exists; `can_admins_bypass=false`; custom branch policy on; REST `protection_rules` observed as `branch_policy` only |
| Topology | EC2 Compose host + ALB + RDS (not ECS). Images from GHCR. Production VPC modeled as `10.20.0.0/16` vs staging `10.10.0.0/16`. |

Packaged Deploy #6 host evidence (no secret values):
[`PRODUCTION_DEPLOY_6_EVIDENCE_2026-09-15.json`](PRODUCTION_DEPLOY_6_EVIDENCE_2026-09-15.json)
source artifact `production-evidence-rel-20260915T020323Z-3c514943a8a0-34919890761`
run https://github.com/markbilbao/dealbrain/actions/runs/34919890761

## Proven production evidence (read-only, 2026-09-18)

| Check | Result |
|-------|--------|
| `GET https://piqsavi.com/` | HTTP 200, PiqSavi HTML |
| `GET https://piqsavi.com/privacy` | HTTP 200 |
| `GET https://piqsavi.com/terms` | HTTP 200 |
| `GET https://piqsavi.com/live` | HTTP 200, `live=true` |
| `GET https://piqsavi.com/ready` | HTTP 200, `ready=true`, `persistence_level=READY` |
| `GET https://piqsavi.com/health` | HTTP 200, `environment=production`, `identity_email_adapter=resend`, `identity_email_ready=true`, legal pages published |
| `GET http://piqsavi.com/` | HTTP 301 → `https://piqsavi.com:443/` (`Server: awselb/2.0`) |
| `GET https://www.piqsavi.com/` | HTTP **200** (not 301 to apex) |
| `GET http://www.piqsavi.com/` | HTTP 301 → `https://www.piqsavi.com:443/` |
| CORS `Origin: https://piqsavi.com` | `access-control-allow-origin: https://piqsavi.com` |
| CORS `Origin: https://www.piqsavi.com` | `access-control-allow-origin: https://www.piqsavi.com` |
| CSP | `default-src 'self'; … connect-src 'self'; form-action 'self'` (same-origin topology) |
| HSTS | `max-age=31536000; includeSubDomains` |
| Target group healthy | Deploy #6 evidence `alb_target_healthy=true`; live `/ready` continues to pass |
| Early Access | Landing HTML 200; production route hardening still hides shopping UI |
| Production Resend attach | Live `/health` `identity_email_ready=true`. Owner-observed Gmail/Yahoo delivery is treated as operational fact; this audit did not re-send mail. |

## Historical incidents vs current state

These remain **historical**. They are not reopened unless current code/evidence shows regression. This PR did not mutate production to re-test them.

| Incident | Fix / current reading |
|----------|------------------------|
| Production bundle verifier overlay bug | PR #136; overlay contract tests remain |
| Minimal AL2023 AMI / SSM registration | PR #137; default AMI selector + early SSM. Historical host `i-0382907b275b835ce` is not the Deploy #6 host |
| AL2023 `gnupg2-minimal` conflict | PR #138 |
| Stale SAFEEXTRACT evidence member | PR #139 |
| Invalid Docker `awslogs-stream-prefix` | PR #140; production compose uses Docker `tag` |
| Production evidence validation false-positive | Covered by later deploy-evidence validation; Deploy #6 `final_status=production_ok` |
| ALB identity/evidence corrections | `test_production_alb_target_health_identity.py` |
| Accidental Rollback Production #1 | 2026-09-14 run `34879465584` failed: missing `s3://dealbrain-production-release-artifacts-941035169846/releases/rel-20260914T175147Z-dd1f9b6e816b/bundle.tar.gz`. Fail-closed. **Not** rollback validation |

## Acceptance matrix

Contract fixture: [`../../../tests/contracts/fixtures/sprint41-acceptance-matrix.json`](../../../tests/contracts/fixtures/sprint41-acceptance-matrix.json)

Legend: **complete** = code/config + real environment + production evidence and the Sprint 41-owned bar for that row is met. Restore rehearsal / paging / deep WAF remain Sprint 42 / post-beta and do not block a row marked complete here.

| # | Item | Code/config | Real env | Prod evidence | Verdict | Exact missing evidence/work |
|---|------|-------------|----------|---------------|---------|-----------------------------|
| 1 | Production VPC/networking | Yes | Yes | Yes | **complete** | No AWS describe this audit; inferred from live ALB + Deploy #6 host resolve |
| 2 | Production database | Yes | Yes | Yes | **complete** (existence/runtime). Restore drill is Sprint 42 / **dependent** | Sprint 42 restore rehearsal |
| 3 | Production secrets | Yes | Yes | Yes (existence only; no values) | **complete** for attach | Redacted env dump not filed; values never printed |
| 4 | Production IAM/OIDC | Yes | Yes | Yes | **complete** for operational OIDC | Required-reviewer UI confirmation is row 11 |
| 5 | GHCR/container pull | Yes | Yes | Yes | **complete** | — |
| 6 | Production ALB | Yes | Yes | Yes | **complete** for TLS/HTTP→HTTPS/target health | Host-header www→apex is row 22 |
| 7 | Public DNS | Owner DNS, not Terraform | Yes | Yes | **complete** for apex+www resolution to production ALB | www canonicalization is row 22 |
| 8 | TLS | ACM modeled; live cert | Yes | Yes | **complete** | — |
| 9 | Static/consumer UI delivery | Same-origin FastAPI HTML | Yes | Yes | **complete** for initial path | CDN remains row 23 |
| 10 | Production deploy workflow | `deploy-production.yml` | Yes | Deploy #5 / #6 | **complete** | Current `main` `4a4fe65` not yet deployed (docs-only; not a blocker) |
| 11 | Approval/evidence gates | Environment `production`; host evidence required | Yes | Artifact + S3 key | **incomplete** | GitHub required-reviewer rule not observed in REST `protection_rules` (only `branch_policy`). Admin bypass is disabled. Owner UI confirmation remaining |
| 12 | Production rollback workflow | `rollback-production.yml` | Yes | Workflow exists; run #1 failed safe | **incomplete** | No successful `rollback_ok` against a prior `production_ok` release |
| 13 | DB migration strategy | Migrate-before-API; failure leaves prior API | Yes | Deploy #6 recorded `migration_revision_before=after=d4e5f6a7b8c9` | **complete** for strategy | This audit did not run a migration |
| 14 | rollback compatibility | No DB downgrade; abort if recorded revision diverges | Workflow exists | No successful rollback | **incomplete** | Needs a real rollback (or approved dry-run window) after two `production_ok` releases. Do not trigger from this task |
| 15 | environment isolation | Separate VPC CIDRs, state keys, buckets, OIDC env, SSM docs | Production identifiers live | Production bucket/role/instance evidenced | **incomplete** | Live cross-account/role AccessDenied simulation not filed; staging currently 503 |
| 16 | staging cannot read production secrets | Host IAM `DenyOtherEnvironmentSecrets`; GHA `DenyOppositeEnvironmentSecretArns`; assembler refuses opposite prefix | Policies exist in applied Terraform lineage | Static tests only | **incomplete** | No live `iam simulate-principal-policy` / AccessDenied artifact. No AWS CLI in this audit |
| 17 | production CORS | `dealbrain/production/cors_origins`; `*` rejected | Yes | Live allow-origin `https://piqsavi.com` and `https://www.piqsavi.com` | **complete** | Secret value not read |
| 18 | TRUSTED_HOSTS | Assembler `piqsavi.com,www.piqsavi.com` | Yes | Both hostnames serve the app | **complete** | Including www is why www 200 is accepted by TrustedHost |
| 19 | CSP/topology | Same-origin CSP; `connect-src 'self'` | Yes | Live CSP matches settings default | **complete** for same-origin topology | `'unsafe-inline'` remains Sprint 40 |
| 20 | public reset/verification links | `PUBLIC_APP_BASE_URL=https://piqsavi.com` | Yes | Adapter live; assembler pins PiqSavi URL | **complete** for hostname contract | This audit did not capture a new production reset/verify inbox screenshot |
| 21 | public brand hostname | Policy + assembler | Yes | `piqsavi.com` live | **complete** | Dedicated `api.piqsavi.com` is still planned in brand policy; current API is same-origin. Owner decision remaining if that host map must be provisioned for Sprint 41 close |
| 22 | www canonical behavior | **No** ALB host-header redirect | www live | HTTPS 200 on www | **incomplete / gap** | Owner ALB or Cloudflare 301 `www` → `https://piqsavi.com/`. Do not change DNS/ALB in this PR |
| 23 | CDN/WAF decision | Proposal only | No CDN/WAF | None | **incomplete / dependent** | Owner must accept or reject [`SPRINT_41_CDN_WAF_DECISION_PROPOSAL_2026-09-18.md`](SPRINT_41_CDN_WAF_DECISION_PROPOSAL_2026-09-18.md). Not recorded as an accepted decision |
| 24 | production `/ready` | Sprint 22 probes unchanged | Yes | Live READY | **complete** | Semantics not redefined |
| 25 | immutable digest deployment | Manifest digest only | Yes | Deploy #6 digest | **complete** | “Promote current staging digest” is **not** evidenced; production SHA was never the last staging deploy |
| 26 | evidence artifact | Schema + host writer | Yes | Deploy #6 `production_ok` | **complete** for deploy | Rollback evidence `rollback_ok` absent |
| 27 | staging preservation | Staging workflows/TF/runbooks retained | Staging ALB still answers | Last success #35 `c4135859` | **incomplete** | Live `https://staging.piqsavi.com/` HTTP **503** (`awselb/2.0`) on 2026-09-18. Architecture preserved; current staging is not green. Do not Deploy Staging from this task |
| 28 | operational rollback proof | Workflow + host script | Yes | Only failed run #1 | **incomplete** | Validate rollback to Deploy #5 (`10c0579b…`) or another prior `production_ok` release. **Do not trigger rollback from this task** |

## Rollback status

| Item | Finding |
|------|---------|
| Workflow | `.github/workflows/rollback-production.yml` present; Environment `production`; concurrency shared with deploy |
| Host script | `scripts/deploy/host/dealbrain-production-rollback.sh` — no RDS mutation, no Alembic downgrade |
| Eligibility | Target must be a prior `production_ok` immutable digest with a retained S3 release object |
| Rollback Production #1 | Failed 2026-09-14 because the requested release bundle did **not** exist. Safe failure. **Not** validation |
| Later rollback runs | **None** |
| Prior successful releases now available as theoretical targets | Deploy #5 (`10c0579b9b8a8653399193261d3ef9f188fed3c2`) then Deploy #6 (`3c51494…`) |
| Sprint 41 rollback acceptance | **OPEN** |

## www canonicalization status

Sprint 41 and the public brand policy require `www` → canonical apex.

| Surface | 2026-09-18 |
|---------|------------|
| Repository ALB module | HTTP→HTTPS 301 only. No host-header redirect |
| Live `https://www.piqsavi.com/` | HTTP **200** (same app as apex) |
| Live `http://www.piqsavi.com/` | HTTP 301 to `https://www.piqsavi.com:443/` |
| `TRUSTED_HOSTS` | Includes `www.piqsavi.com`, so www 200 is application-accepted |
| Gap | Sprint 41 www canonicalization **open** |

Remaining work is an owner-controlled ALB listener rule or Cloudflare redirect. **Not done in this PR.**

## CDN/WAF decision status

| Question | Answer |
|----------|--------|
| Formal recorded owner/architecture/security decision in repo before this PR? | **No** |
| GAP_INVENTORY class before this PR | `planned_underspecified` |
| Deep WAF | Already classified `post_beta_improvement` |
| This PR | Adds a **proposal only**: [`SPRINT_41_CDN_WAF_DECISION_PROPOSAL_2026-09-18.md`](SPRINT_41_CDN_WAF_DECISION_PROPOSAL_2026-09-18.md) |
| Sprint 41 acceptance | **OPEN** until the owner records a decision |

Do not treat the proposal as an accepted decision.

## Environment isolation status

| Rule | Code/config | Live evidence this audit |
|------|-------------|--------------------------|
| Staging cannot access production Secrets Manager | Host IAM deny opposite prefix; GHA deny secret value reads + opposite ARNs; assembler refuses `production` prefix on staging | **No** live AccessDenied / IAM simulate artifact (no AWS CLI) |
| Staging deploy identity cannot mutate production | OIDC `environment:staging` only; SendCommand tagged `Environment=staging`; opposite-env deny | Static tests only |
| Production identity cannot accidentally target staging | Symmetric opposite-env deny; production SSM docs only | Static tests + Deploy #6 assumed production role |
| Terraform state isolated | Distinct keys `staging/terraform.tfstate` vs `production/terraform.tfstate`; `use_lockfile = true` | Code/docs; state bucket not listed |
| Separate databases | Separate RDS modules/instances per env | Production sqlalchemy READY; staging currently 503 so staging DB was not re-probed |
| Separate release buckets | `dealbrain-production-release-artifacts-941035169846` vs staging prefix | Production bucket confirmed in Deploy #6 logs |

Isolation is **implemented in IAM/Terraform/assembler** and **not fully evidenced live**.

## Migration safety (no migration performed)

| Expectation | Repository / Deploy #6 |
|-------------|------------------------|
| Production migration path | Compose `migrate` profile; `alembic upgrade head` on the immutable digest |
| Migration before API replacement | `dealbrain-production-deploy.sh` captures revision, migrates, aborts on failure **before** API recreate |
| Failure leaves prior API | Documented; `FAILURE_REASON=migration_failed` / `migration_timeout` |
| Backward compatibility | Forward-only. Rollback does not downgrade schema |
| Rollback compatibility | Rollback allowed only when live `alembic current` matches the target release’s recorded revision |
| Deploy #6 | `migration_revision_before` = `migration_revision_after` = `d4e5f6a7b8c9` (no schema change on that deploy) |

## API hostname vs brand host map

[`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md) still lists `api.piqsavi.com` as a **planned** public production API hostname.

Live production serves consumer UI and API on `https://piqsavi.com` (same origin). `api.piqsavi.com` is **not** provisioned.

That is consistent with Early Access same-origin topology and with live CSP `connect-src 'self'`. It is **not** an automatic close of the planned host-map row. Owner may later accept same-origin as the Sprint 41 API hostname or provision `api.piqsavi.com`.

## Required production runbooks

Added (documentation only; no execution):

- [`../../runbooks/PRODUCTION_DEPLOY.md`](../../runbooks/PRODUCTION_DEPLOY.md)
- [`../../runbooks/PRODUCTION_ROLLBACK.md`](../../runbooks/PRODUCTION_ROLLBACK.md)

Historical cutover runbook remains [`../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md`](../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md) and is not rewritten.

## Exact resulting Sprint 41 status

`SPRINT 41 PARTIALLY COMPLETE — PRODUCTION LIVE; ROLLBACK VALIDATION, WWW CANONICALIZATION, CDN/WAF OWNER DECISION, STAGING PRESERVATION, AND LIVE IAM SIMULATION REMAIN OPEN`

Not A (complete/closed). Not B (implementation complete / evidence-only): www canonicalization is missing runtime config, CDN/WAF is not an accepted decision, and rollback has not been validated.

## Remaining Sprint 41-owned work (owner-controlled unless noted)

1. Validate Rollback Production against a real prior `production_ok` release (do not run from this task).
2. Implement www → `https://piqsavi.com/` 301 (ALB or Cloudflare). Do not do it in this PR.
3. Record an owner CDN/WAF decision (accept/reject the proposal).
4. File live IAM isolation proof (staging role denied `dealbrain/production/*`; production role cannot SendCommand staging instances).
5. Confirm GitHub Environment `production` required reviewers in the UI, or record an audited exception.
6. Restore staging to green **or** record an owner exception that Early Access staging downtime is accepted while architecture remains. Do not Deploy Staging from this task.
7. Optional: decide whether `api.piqsavi.com` is required for Sprint 41 close or deferred.

Sprint 42 still owns paging, synthetics, backup restore rehearsal, and IR depth. This reconciliation does not pull those into Sprint 41 closure.

## No production mutation

This reconciliation performed **read-only** GitHub, DNS, TLS, and public HTTP inspection plus in-repo documentation/tests.

It did **not**:

- dispatch Deploy Production or Rollback Production or Deploy Staging
- apply Terraform
- replace EC2
- send SSM commands against production
- mutate RDS, Secrets Manager, IAM, DNS, Cloudflare, ACM, ALB, or Resend
- print secret values
