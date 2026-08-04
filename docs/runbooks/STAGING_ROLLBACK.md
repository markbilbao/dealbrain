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

### Accepted maintenance boundary (Sprint 25b.5n)

HashiCorp AWS provider **v5.100.0** documents that updates to
`user_data_base64`, with `user_data_replace_on_change=false` (the module
default), **trigger a stop/start of the EC2 instance**.

This specific staging apply is authorized to perform **one controlled EC2
stop/start** for instance:

    i-0edd57f32296aa323

Accepted reason (limited): reconcile the approved hardened staging bootstrap
`user_data` attribute on that exact instance.

This authorization does **not** extend to:

- EC2 replacement
- EC2 termination
- AMI changes
- instance-type changes
- storage changes
- networking changes
- security-group changes
- IAM instance-profile changes
- production resources
- arbitrary future `user_data` changes
- automatic acceptance of unrelated drift

Operators must treat these statements as true for this window:

- temporary staging downtime is expected
- the exact duration cannot be guaranteed
- application processes will restart with the host
- cloud-init / `user_data` scripts are **not** expected to rerun merely because
  the attribute changes (AWS first-boot semantics; stop/start ≠ new launch).
  Post-apply cloud-init verification is still **required**; do not treat
  “not expected” as “impossible” or skip the check
- instance identity must remain `i-0edd57f32296aa323` (no replacement)
- rollback tooling still requires a later **Deploy Staging** run after Terraform
  verification — this apply alone does **not** authorize Rollback Staging

Hard identity for this gate:

| Item | Required value |
|------|----------------|
| AWS account | `941035169846` |
| Region | `us-east-1` |
| Workspace | `default` |
| State key | `staging/terraform.tfstate` |
| Backend bucket | `dealbrain-terraform-state-941035169846` |
| EC2 instance | `i-0edd57f32296aa323` |
| Plan counts | create=`1`, update=`2`, replace=`0`, destroy=`0`, read=`1` |
| EC2 changed attribute | `user_data_base64` only |

Expected plan resource set (`terraform show -json` is the sole plan authority):

| Address | Action |
|---------|--------|
| `module.ssm_rollback_document.aws_ssm_document.staging_rollback` | create |
| `module.github_deploy_role.aws_iam_role_policy.deploy_allow` | update in place |
| `module.ec2.aws_instance.api` | update in place (`user_data_base64` only) |
| `module.github_deploy_role.data.aws_iam_policy_document.deploy_allow` | read during apply |

Expected output changes:

| Output | Action |
|--------|--------|
| `ssm_rollback_document_name` | create |
| `ssm_rollback_document_arn` | create |

### Exact acknowledgements (required for apply-capable mode)

Apply-capable mode requires **three distinct gates**, all exact:

1. **Maintenance acknowledgement** — byte-for-byte match of:

```text
I authorize temporary staging downtime caused by one EC2 stop/start for i-0edd57f32296aa323. I do not authorize replacement, destroy, production changes, or unrelated infrastructure changes.
```

No whitespace normalization, trimming, optional line breaks, case folding,
substring acceptance, prefix/suffix text, or alternate punctuation.

2. **Demo/test-session clearance** — `STAGING_MAINTENANCE_DEMO_CLEAR=1` only when
   staging is not in a critical demo or active test session. This does **not**
   substitute for live technical health checks.

3. **Recovery-readiness acknowledgement** — byte-for-byte match of:

```text
I confirm a backup operator and same-instance recovery procedure are available for staging instance i-0edd57f32296aa323.
```

4. **Plan checksum confirmation** — after the script generates and validates the
   saved plan, it prints the plan SHA-256. Apply requires
   `STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM` equal to that exact digest. The
   script records plan identity (path, device, inode, size, SHA-256, UID, GID,
   exact mode `0600`) and revalidates every field immediately before
   `terraform apply`, rejects symlinks and broader modes (`0604`/`0640`/`0644`
   and any group/world-readable or writable mode), and applies only that saved
   plan file. Plan JSON and human plan artifacts in the temp workspace must also
   be mode `0600`; the temp directory must remain mode `0700` and owned by the
   current user. Caller-supplied UID/GID/mode values are never accepted as
   authority.

Scripts enforce these via `scripts/deploy/staging_maintenance_gate_lib.sh` and
`scripts/deploy/staging_maintenance_assert.py`.

**Stop (fail closed) if any of the following are true:**

- account is not `941035169846`
- region is not `us-east-1`
- workspace is not `default`
- state key is not `staging/terraform.tfstate`
- backend bucket is not `dealbrain-terraform-state-941035169846`
- instance ID differs from `i-0edd57f32296aa323`
- plan differs from 1 create / 2 updates / 0 replace / 0 destroy / 1 read
- output changes differ from the two expected SSM rollback outputs
- EC2 changes anything other than `user_data_base64`, has nonempty
  `replace_paths`, or has after_unknown ambiguity on critical fields
- any RDS, ALB, networking, security-group, storage, bucket, DNS, or production
  resource changes
- staging is handling a critical demo or active test session
- live pre-apply EC2/ALB/`/live`/`/ready` checks fail
- required host-evidence JSON is missing, stale, malformed, or wrong phase
- recovery acknowledgement is missing or inexact
- plan checksum confirmation is missing or does not match

**No Terraform apply is allowed** until an independent combined infrastructure
apply-readiness audit verifies all of the following **and** the three operator
gates plus plan checksum confirmation are recorded:

- exact `user_data` / `user_data_base64` diff
- `replace = 0` and `destroy = 0` (no instance replacement)
- live EC2 running + status ok, ALB target healthy, `/live` and `/ready` 200
- host evidence (boot ID, uptime, cloud-init, release ID, digest, pointers)
- maintenance and downtime implications (stop/start accepted for this window)
- same-instance recovery procedure acknowledged
- unchanged EC2 identity (same instance id / no replacement)
- no unrelated infrastructure drift (no production, RDS, ALB, network,
  security-group, bucket, or DNS changes outside the expected set)

Until that audit passes **and** the acknowledgements are given, the EC2 update
remains unauthorized even when the SSM document create and IAM policy update
are otherwise desired.

Operator procedures (prepared; do not improvise):

- Pre-apply capture: `scripts/deploy/staging_maintenance_pre_apply_capture.sh`
- Controlled apply (gated): `scripts/deploy/staging_maintenance_controlled_apply.sh`
- Assert helper: `scripts/deploy/staging_maintenance_assert.py`
- Sprint detail: `docs/SPRINT_25B5N_STAGING_MAINTENANCE_APPLY_GATE.md`

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

### Pre-apply capture (read-only, fail-closed)

Before any apply, run the capture script and retain the artifact directory.
Mandatory identity, health, plan, and host-evidence inputs fail nonzero when
unavailable or malformed. Optional fields may be absent only where explicitly
valid (for example no public IP).

**Repository:** branch, full SHA, clean status, `origin/main` synchronization
**AWS:** caller account, configured region (must match hard identity)
**EC2:** instance ID, state=`running`, system/instance status=`ok`, AZ, private
IP, public IP only when present, launch time
**Host evidence JSON** (Session Manager; never SSM SendCommand; never free-form
paste as authority): schema_version, phase=`pre-apply`, instance/account/region,
timestamp, **internally generated run nonce** (operator cannot choose
`STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE`), boot ID, uptime, cloud-init status
(allowlist), release ID, immutable digest, current/previous pointers (previous
key required; value may be null), rollback marker=`false`. When `repository_sha`
is present it must match the approved repository SHA. Evidence phases and
freshness are enforced; pre/post must carry the same generated nonce.
**ALB:** expected TG identity, exact instance registered and `healthy`, `/live`
and `/ready` HTTP 200 on the Terraform ALB DNS only
**RDS:** instance identity and status only (no credentials or database URL)
**Terraform:** init against the staging backend (no skip), backend bucket/key,
workspace, exact fresh plan via `terraform show -json`, counts including read,
plan SHA-256

Do **not** print credentials, environment dumps, `DATABASE_URL`, passwords,
tokens, private keys, or application secrets.

```bash
# From repository root — read-only; does not apply
bash scripts/deploy/staging_maintenance_pre_apply_capture.sh
```

### Controlled apply procedure (prepared — execute only under separate approval)

Do **not** use `terraform -target`. Apply only the exact reviewed saved-plan
file after acknowledgements and checksum confirmation. Work files use
`mktemp -d` with mode `0700` and EXIT cleanup (failure retains non-secret
diagnostics; plan-only retains the workdir for collect snippets).
`STAGING_MAINTENANCE_SKIP_INIT` is forbidden. Do **not** set
`STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE` (rejected; nonce is internally
generated per run).

1. Verify clean, synced `main` at the approved SHA.
2. Verify AWS account `941035169846` and region `us-east-1`.
3. Create owned temp workdir (`0700`); **internally generate** the run nonce;
   write Session Manager collect snippets that embed that nonce.
4. `terraform init` against the expected backend; verify bucket/key/workspace.
5. Validate pre-apply host-evidence JSON against the generated nonce (and phase,
   freshness, instance/account/region); verify live EC2/ALB/`/live`/`/ready`.
6. Generate a fresh saved Terraform plan into the temporary workdir; `chmod 0600`
   plan/JSON/human artifacts.
7. Structurally validate `terraform show -json` (resources, reads, outputs,
   EC2 `user_data_base64`-only, empty `replace_paths`, after_unknown safety).
8. Record plan identity (path/dev/inode/size/sha256/uid/gid/mode=`0600`).
9. For apply mode: require exact maintenance ACK, demo clearance, recovery ACK,
   and exact plan checksum confirmation; re-check live health; re-verify every
   plan identity field; apply that saved plan only (never regenerate after confirm).
10. Fail-closed waits: EC2 running/ok/ok, ALB healthy, `/live`+`/ready` 200.
11. Validate post-apply host-evidence JSON with the **same** generated nonce;
    compare release/digest/pointers; record boot ID/uptime consistency; require
    accepted cloud-init status.
12. Structurally verify SSM document metadata **and** canonical content for the
    active default version; structurally verify IAM allow + deny policies
    (PassRole/production ARNs rejected). Verification failures stop before
    Deploy Staging.
13. Fresh post-apply plan must show no residual drift.
14. **Stop before Deploy Staging.** Rollback Staging remains unauthorized.
    Report `FAIL_PHASE=...` and nonzero exit on any failure — never print
    overall success when health/integrity/IAM/SSM verification failed.

```bash
# Plan-only (default). Does not apply. Prints HOST_EVIDENCE_RUN_NONCE and
# retains workdir collect snippets.
bash scripts/deploy/staging_maintenance_controlled_apply.sh

# Apply path — only after independent audit APPROVE + all gates.
# Collect pre/post evidence using the apply run's printed nonce + snippets
# (optional: STAGING_MAINTENANCE_EVIDENCE_WAIT_SECONDS while collecting).
# Do NOT set STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE.
# export STAGING_MAINTENANCE_ACK='I authorize temporary staging downtime caused by one EC2 stop/start for i-0edd57f32296aa323. I do not authorize replacement, destroy, production changes, or unrelated infrastructure changes.'
# export STAGING_MAINTENANCE_RECOVERY_ACK='I confirm a backup operator and same-instance recovery procedure are available for staging instance i-0edd57f32296aa323.'
# export STAGING_MAINTENANCE_DEMO_CLEAR=1
# export STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM='<sha256 from the apply run reviewed plan>'
# export STAGING_MAINTENANCE_HOST_EVIDENCE_PRE=/path/to/pre-apply-evidence.json
# export STAGING_MAINTENANCE_HOST_EVIDENCE_POST=/path/to/post-apply-evidence.json
# EXECUTE_MAINTENANCE_APPLY=1 bash scripts/deploy/staging_maintenance_controlled_apply.sh
```

### Failure and recovery (fail closed)

The normal script does **not** automatically perform recovery mutations. On
failure it exits nonzero, preserves non-secret diagnostics, identifies
`FAIL_PHASE` (preflight, plan_validation, apply, ec2_recovery_timeout,
alb_recovery_timeout, application_health, host_evidence, host_evidence_nonce,
host_evidence_phase, host_evidence_stale, release_integrity, post_plan_drift,
plan_identity_owner, plan_identity_mode, plan_identity_checksum,
iam_policy_verification, ssm_document_content_verification), and directs the
operator to the same-instance recovery procedure.

If any post-apply gate fails, prioritize in this order:

1. Preserve logs without exposing secrets.
2. Confirm the instance was not replaced (ID still `i-0edd57f32296aa323`).
3. Restore the same EC2 instance to `running` only when separately and
   explicitly authorized (console/CLI start only; not replace/recreate).
4. Inspect systemd/container status on the host (Session Manager; no secret dumps).
5. Verify current release pointers and immutable image digest.
6. Avoid running **Rollback Staging** until rollback tooling has been delivered
   and verified via a later Deploy Staging.
7. Do not change production.
8. Escalate rather than improvising state edits or targeted applies.

Documented failure modes include: Terraform apply failure; EC2 recovery
timeout; status checks fail; ALB recovery timeout; `/live` or `/ready` fails;
host-evidence missing/malformed; release/digest/pointer mismatch; cloud-init
error/ambiguous; post-plan residual drift; public IP changes unexpectedly;
application service does not start; Terraform state remains partially changed.

Do **not** recommend or perform:

- `terraform state rm`
- manual state surgery
- arbitrary EC2 recreation
- production failover
- bypassing health checks
- `terraform -target`
- `lifecycle { ignore_changes = [user_data_base64] }`
- automatic Deploy Staging or Rollback Staging from this maintenance step

### Post-apply assertions

After a future approved apply, require:

**Terraform:** apply used the exact reviewed plan; outputs contain rollback
document name and ARN; fresh plan has no unexplained residual drift.

**SSM:** `DealBrain-StagingRollback` exists; active default version content is
structurally verified against the approved canonical contract (entrypoint,
parameters/`allowedPattern`, timeout `2400`, staging-only, no free-form
command); creating/describing it did not invoke the document (no SendCommand).

**IAM:** Allow + deny inline policies are structurally verified against the
approved staging contract; Deploy and Rollback document permissions required;
no arbitrary SSM document wildcard; `iam:PassRole` / `iam:*` / action `*`
rejected on allow; no production ARN; staging deny protections remain.

**EC2:** instance ID remains `i-0edd57f32296aa323`; no replacement; no
termination; state returns to `running`; both status checks pass; boot-ID /
uptime evidence records whether stop/start occurred; cloud-init did not
unexpectedly execute bootstrap again.

**Application:** original immutable release ID remains active; original image
digest remains active; containers/services recover; `/live` and `/ready` pass;
ALB target becomes healthy.

**Infrastructure:** RDS, ALB/TG, VPC/networking, security groups, storage, and
production unchanged.

### Required future order (after approved apply)

1. Complete and verify the controlled Terraform maintenance apply.
2. Confirm staging is healthy and current release is unchanged.
3. Run **Deploy Staging** to install current rollback tooling.
4. Verify `staging-host-tooling.json` version/checksums.
5. Build and deploy a second immutable release.
6. Run rollback rehearsal-readiness audit.
7. Rehearse rollback to Build Image #15.
8. Stop before production.

Build Image #15 baseline:

- build run: `30741970067`
- release: `rel-20260802T093246Z-83bfc6c57fd9`
- Git SHA: `83bfc6c57fd99a43445b6edaddcaf863fabf3473`
- digest: `sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f`

**Deploy Staging** occurs only after Terraform verification. **Rollback Staging**
remains unauthorized at this maintenance-apply point.

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
