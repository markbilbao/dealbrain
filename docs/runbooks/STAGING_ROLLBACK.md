# Staging Rollback Runbook (Sprint 25b.5)

**Audience:** operators performing a staging rollback rehearsal after a second
immutable release is deployed  
**Scope:** staging only — no production promotion, snapshot, or production rollback  
**This document is the rehearsal plan.** Do not execute rehearsal until the
implementation has passed an independent acceptance audit and prerequisites below
are green.

## Authority model

Rollback target authority comes **only** from:

1. A successful **Build Image** release-manifest (immutable digest + release_id +
   git_sha + manifest_sha256)
2. A previously uploaded staging release bundle under
   `s3://dealbrain-staging-release-artifacts-<account>/releases/<release_id>/`
3. Prior host-authored `staging_ok` deploy evidence for that exact release +
   digest, loaded only with its SHA-256 sidecar and bound to the exact staging
   account, region, and EC2 instance

Mutable tags (`latest`, `staging`, branch tags) are never authority.

## Host tooling delivery model

Rollback host binaries are **not** installed by EC2 `user_data` / cloud-init.

1. **Terraform / EC2 `user_data`** provides the hardened baseline bootstrap only
   (approved SAFEEXTRACT protections + deploy/evidence/ALB helper members). It
   does **not** embed rollback-specific tooling in `REQUIRED_MEMBERS`.
2. **Deploy Staging** builds/uploads a schema-2 release bundle (SAFEEXTRACT-
   protected), extracts it on the host, installs rollback binaries/schemas under
   `/opt/dealbrain/bin/` (and refreshes `verify_staging_bundle.py` from the
   bundle), and writes `/opt/dealbrain/bin/staging-host-tooling.json` only after
   verified installation (`tooling_version=25b.5` + checksum inventory).
3. **Rollback Staging** preflight verifies that capability/version/checksums
   before any mutation. Missing or outdated tooling fails closed.

**Prerequisite order:** after an approved Terraform apply, run **Deploy Staging**
to install current host rollback tooling before any rollback rehearsal.

## Combined infrastructure apply gate

The rollback SSM/IAM Terraform changes and staging bootstrap `user_data`
reconciliation may appear together in the same plan. This plan is **not**
SSM/IAM-only.

The EC2 `user_data_base64` update is intentional: the declarative staging
bootstrap contains approved Sprint 25b.5h SAFEEXTRACT protections that are not
reflected in the older live instance attribute. Do **not** pin live EC2 bytes,
add `lifecycle { ignore_changes = [user_data_base64] }`, or use
`terraform -target` to hide that drift.

**No Terraform apply is allowed** until an independent combined infrastructure
apply-readiness audit verifies all of the following:

- exact `user_data` / `user_data_base64` diff
- `replace = 0` and `destroy = 0` (no instance replacement)
- expected instance behavior after cloud-init / attribute update
- maintenance and downtime implications
- rollback and recovery plan
- unchanged EC2 identity (same instance id / no replacement)
- no unrelated infrastructure drift (no production, RDS, ALB, network,
  security-group, bucket, or DNS changes outside the expected set)

Until that audit passes, the EC2 update remains unauthorized even when the
SSM document create and IAM policy update are otherwise desired.

### Historical Build Image #15 contract

**HISTORICAL BUILD IMAGE #15 RECONSTRUCTION IS SAFE** under this audited model:

- Bundle schema version `1` = historical application-runtime release (predates
  rollback binaries)
- Bundle schema version `2` = current application runtime + host deploy/rollback
  tooling
- Historical reconstruction verifies the declared schema/version and **every**
  original `file_checksums` entry (path-safe, no symlink escape)
- Historical targets are **not** required to contain
  `dealbrain-staging-rollback.sh`, rollback evidence writers, or the rollback
  schema — those are host tooling
- Current host-installed rollback tooling (refreshed by a successful
  Deploy Staging after merge) operates the reconstructed target
- Immutable image digest authority and SAFEEXTRACT path/checksum rules remain
  enforced
- Unsupported schema versions fail closed

If a historical release directory is already retained locally, rollback verifies
it with the same complete `file_checksums` contract before use.

## Prerequisites (abort if any fail)

- [ ] Rollback PR merged to `main`
- [ ] Staging Terraform/SSM/IAM applied (includes `DealBrain-StagingRollback`
      document and GHA role allowlist for deploy + rollback) — **apply is a
      separate approved change**
- [ ] Host tooling refreshed through a successful **Deploy Staging** after merge
      (installs rollback binaries and writes
      `/opt/dealbrain/bin/staging-host-tooling.json`)
- [ ] Exact rollback tooling capability verified (`tooling_version=25b.5` and
      binary checksum inventory)
- [ ] Baseline eligibility evidence checksum verified (JSON + `.sha256` sidecar)
- [ ] Build Image #15 local retention **or** historical S3 reconstruction
      available under the schema-1 contract above
- [ ] Second immutable release deployed successfully
- [ ] Baseline and second-release `staging_ok` evidence retained (with sidecars)
- [ ] Independent rollback audit approved
- [ ] Deploy Staging #11 evidence preserved (`staging_ok` for
      `rel-20260802T093246Z-83bfc6c57fd9` /
      `sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f`)
- [ ] GitHub Environment `staging` vars unchanged: `AWS_ROLE_ARN`, `AWS_REGION`,
      `AWS_ACCOUNT_ID`, `STAGING_TARGET_GROUP_ARN`
- [ ] No in-flight Deploy Staging / Rollback Staging run
      (concurrency group `staging-release-mutation`)

## Release retention contract

The staging host must retain:

| Pointer / directory | Purpose |
|---------------------|---------|
| `/opt/dealbrain/current` | Active release |
| `/opt/dealbrain/previous` | Immediately previous approved release (forward recovery) |
| Release dirs for both | Reconstructible API + compose + DEPLOY_VERSION |

### Pointer pair model (compensating transaction)

`current` and `previous` are **two** symlinks, not one filesystem transaction.
Commit captures exact original states, validates release paths under
`/opt/dealbrain/releases`, replaces each link atomically, and on any failure
**restores both** to their exact originals (including restoring `previous` to
absent when it was originally absent). Restoration failure is an explicit
non-zero failure and never emits `rollback_ok`.

Pointer mutations occur **only after** localhost `/live`, `/ready`, and strict
ALB healthy checks succeed.

### Pointer matrix

| Scenario | `current` | `previous` |
|----------|-----------|------------|
| First deployment (no prior) | new release | unset / unchanged |
| Second deployment | new (B) | displaced (A) |
| Successful rollback A←B | A | B (forward recovery) |
| Failed rollback before API replacement | B (unchanged) | prior state |
| Failed rollback after API replacement | restored to B | restored prior state |
| Health OK but evidence finalization fails | A (committed) | B; workflow fails; no `rollback_ok` |

## Database compatibility policy

- Rollback **never** runs Alembic downgrade.
- Before API replacement, host compares live `alembic current` to the
  authoritative target recorded revision:
  1. `DEPLOY_VERSION.migration_revision` when canonical/valid
  2. else `migration_revision_after` from the **exact** fully validated prior
     `staging_ok` evidence (sidecar + account/region/instance/release/digest)
- Unbound evidence scans and first-match JSON field reads are forbidden.
- Mismatch → fail closed (`database_incompatible`) with API + pointers untouched.
- Rollback evidence records
  `target_migration_revision_authority` =
  `deploy_version` | `validated_prior_staging_evidence`.

---

## Rehearsal phases (document only — do not execute in the implementation pass)

### Phase 1 — Preserve baseline

**Actions**

1. Archive Deploy Staging #11 GitHub artifact and S3 evidence key + sidecar.
2. Record baseline identity:

   - Build run ID: `30741970067`
   - Release ID: `rel-20260802T093246Z-83bfc6c57fd9`
   - Image-source Git SHA: `83bfc6c57fd99a43445b6edaddcaf863fabf3473`
   - Digest: `sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f`

**Evidence to capture**

- `staging-deploy-evidence.json` with `final_status=staging_ok` **and**
  `.sha256` sidecar
- Host `current` → baseline release dir
- Running digest equals baseline digest

**Abort if:** baseline evidence missing, sidecar missing/mismatch, digest
mismatch, or production env referenced.

### Phase 2 — Second immutable release deploy

**Actions**

1. Build Image on `main` → new digest (≠ baseline).
2. Deploy Staging with the new build run ID (also refreshes host rollback tooling
   capability).
3. Confirm host retention kept baseline as `previous` (do **not** delete
   Build Image #15 / baseline release directory unless reconstructing from the
   verified historical bundle).

**Evidence to capture**

- `staging_ok` for the second release (+ sidecar)
- Exact running digest = second digest
- Localhost `/live` + `/ready`
- Strict ALB target healthy
- `current` → second release; `previous` → baseline
- `/opt/dealbrain/bin/staging-host-tooling.json` present at `25b.5`

**Abort if:** deploy fails, ALB not exactly healthy, baseline pruned without
reconstructible historical bundle, or `previous` not pointing at baseline.

### Phase 3 — Rollback to Build Image #15

**Actions**

1. Actions → **Rollback Staging** → Run workflow on `main`
2. Inputs:
   - `build_workflow_run_id` = `30741970067`
   - optional `release_id` = `rel-20260802T093246Z-83bfc6c57fd9`
3. Do not cancel an in-progress run.

**Evidence to capture**

- Host tooling preflight success before mutation
- SSM document `DealBrain-StagingRollback` command Success
- Host evidence key
  `evidence/<release_id>/<rollback_run_id>/staging-rollback-evidence.json`

**Abort if:** eligibility gates fail, tooling capability missing/outdated, SSM
document missing (Terraform not applied), database incompatible, or
fork/non-main dispatch attempted.

### Phase 4 — Verify rollback success

**Verify**

- [ ] Evidence `final_status=rollback_ok`
- [ ] `target_migration_revision_authority` recorded
- [ ] Running digest equals Build Image #15 digest
- [ ] Localhost `/live` and `/ready` true
- [ ] Strict ALB target healthy
- [ ] `current` → baseline release
- [ ] `previous` → second release (forward recovery preserved)
- [ ] GitHub artifact uploaded only after validation
- [ ] Workflow run ID + SSM command ID bind in evidence

**Abort if:** any gate false, `rollback_ok` fabricated by GitHub, or second
release directory removed.

### Phase 5 — Stop

- Stop. No production promotion. No further AWS mutation beyond the staging
  rehearsal scope already approved.

---

## Common failures

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Target bundle missing | Never deployed / pruned | Redeploy target via Deploy Staging first |
| No prior `staging_ok` / sidecar | Target never approved or sidecar missing | Abort; redeploy with evidence+sidecar |
| Prior binding mismatch | Wrong account/region/instance | Abort; fix staging identity |
| Host tooling preflight failed | Deploy Staging not refreshed after merge | Run Deploy Staging once; retry |
| `database_incompatible` | Schema advanced past target | Abort; do not force API rollback |
| Pointer pair restore failed | Dual-symlink compensation failed | Operator inspect pointers; do not claim success |
| SSM AccessDenied on Rollback doc | Terraform allowlist not applied | Apply staging SSM rollback module (separate change) |
| Concurrent run blocked | Shared concurrency group | Wait for deploy/rollback to finish |
| Evidence missing | Host failed before upload | Inspect SSM; do not fabricate `rollback_ok` |

## Security / isolation checklist

- [ ] Workflow `environment: staging` only
- [ ] Role `dealbrain-staging-gha-deploy` only (OIDC)
- [ ] No production workflow/env/role/host/TG/bucket
- [ ] No static AWS keys
- [ ] Logs contain no secrets, DB URLs, or env dumps
