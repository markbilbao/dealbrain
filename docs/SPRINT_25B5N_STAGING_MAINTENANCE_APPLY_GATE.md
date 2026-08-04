# Sprint 25b.5n — Staging EC2 Maintenance Apply Gate

**Status:** Fail-closed operator procedures, structural plan authority, behavioral tests
**Branch:** `sprint-25b5n-staging-maintenance-gate`
**Scope:** Authorize one controlled staging EC2 stop/start during the combined
Terraform apply that reconciles hardened bootstrap `user_data_base64` together
with SSM rollback document create and IAM allowlist update.
**Out of scope for this documentation/code pass:** live Terraform apply execution,
Deploy Staging, Rollback Staging, production, AWS mutation during validation.

## Confirmed provider stop/start behavior

Installed staging AWS provider: **hashicorp/aws v5.100.0**.

Provider documentation for `aws_instance`:

> Updates to [`user_data_base64`] will trigger a stop/start of the EC2 instance
> by default. If the `user_data_replace_on_change` is set then updates to this
> field will trigger a destroy and recreate of the EC2 instance.

`user_data_replace_on_change` defaults to `false` and is unset in
`infra/terraform/modules/ec2` — therefore an in-place `user_data_base64` update
may stop and start instance `i-0edd57f32296aa323`, temporarily making staging
unavailable and restarting processes on the host.

Cloud-init / user_data scripts are **not** expected to rerun merely because the
attribute changes (first-boot semantics). Stop/start ≠ instance replacement.
Post-apply cloud-init verification is still **required**; documentation must not
claim rerun is impossible.

## Accepted maintenance boundary

Authorized for this specific staging apply only:

| Item | Value |
|------|-------|
| Account | `941035169846` |
| Region | `us-east-1` |
| Workspace | `default` |
| State key | `staging/terraform.tfstate` |
| Backend bucket | `dealbrain-terraform-state-941035169846` |
| Instance | `i-0edd57f32296aa323` |
| Reason | Reconcile approved hardened staging bootstrap `user_data` |
| Allowed host effect | One controlled EC2 stop/start |
| Plan counts | create=`1`, update=`2`, replace=`0`, destroy=`0`, read=`1` |

Not authorized: replacement, termination, AMI/type/storage/network/SG/IAM-profile
changes, production, arbitrary future user_data changes, unrelated drift
acceptance, Rollback Staging, Deploy Staging from this script.

## Exact acknowledgements

Apply-capable mode requires all of:

```text
I authorize temporary staging downtime caused by one EC2 stop/start for i-0edd57f32296aa323. I do not authorize replacement, destroy, production changes, or unrelated infrastructure changes.
```

```text
I confirm a backup operator and same-instance recovery procedure are available for staging instance i-0edd57f32296aa323.
```

```bash
STAGING_MAINTENANCE_DEMO_CLEAR=1
STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR=<exact independently audited plan-only workdir>
STAGING_MAINTENANCE_PLAN_CHECKSUM_CONFIRM=<sha256 of that audited plan binary>
EXECUTE_MAINTENANCE_APPLY=1
```

Maintenance ACK and recovery ACK are compared **byte-for-byte** (no whitespace
normalization, trimming, optional line breaks, case folding, or substrings).
Demo clearance is separate from recovery readiness and does not replace live
EC2/ALB/`/live`/`/ready` checks.

### Exact independently audited plan reuse (Sprint 25b.5q)

Contract:

1. **Plan-only** creates the immutable candidate plan workdir (saved plan binary,
   plan JSON/text, plan identity, plan-only nonce, collect snippets, retained
   pre-evidence pair, `plan-only.complete` / `plan-only.authority.log`,
   `repository.sha`).
2. **Independent audit** approves that exact plan binary (checksum + identity).
3. **Controlled apply** consumes that same exact plan via
   `STAGING_MAINTENANCE_APPROVED_PLAN_WORKDIR` (exact path; no latest-dir search,
   no globs).
4. Apply mode **does not generate a replacement maintenance plan**. It may use
   read-only `terraform show` against the retained binary and still runs a
   post-apply residual drift plan after apply.
5. Apply generates a **fresh** run nonce and requires **fresh** pre/post host
   evidence bound to that apply-run nonce (retained in the apply-run private
   workdir). Plan-only evidence/nonce are not reused.

## Expected plan resource set

| Address | Action |
|---------|--------|
| `module.ssm_rollback_document.aws_ssm_document.staging_rollback` | create |
| `module.github_deploy_role.aws_iam_role_policy.deploy_allow` | update in place |
| `module.ec2.aws_instance.api` | update in place (`user_data_base64` only) |
| `module.github_deploy_role.data.aws_iam_policy_document.deploy_allow` | read during apply |

Expected output changes: `ssm_rollback_document_name` create,
`ssm_rollback_document_arn` create.

`terraform show -json` is the sole plan authority. EC2 must have
`actions=["update"]`, null/empty `replace_paths`, unchanged instance id
`i-0edd57f32296aa323`, `user_data_replace_on_change=false`, structural
before/after equality except `user_data_base64`, and no critical
`after_unknown` ambiguity.

## Operator artefacts

| Artefact | Path |
|----------|------|
| Runbook gate | `docs/runbooks/STAGING_ROLLBACK.md` — Combined infrastructure apply gate |
| Canonical ack + helpers | `scripts/deploy/staging_maintenance_gate_lib.sh` |
| Plan/host/IAM/SSM assert helper | `scripts/deploy/staging_maintenance_assert.py` |
| Pre-apply capture | `scripts/deploy/staging_maintenance_pre_apply_capture.sh` |
| Controlled apply (gated) | `scripts/deploy/staging_maintenance_controlled_apply.sh` |
| Behavioral tests | `tests/unit/test_sprint25b5n_staging_maintenance_gate.py` |
| Exact plan reuse tests | `tests/unit/test_sprint25b5q_exact_audited_plan_reuse.py` |

## Temporary workspace model

Apply/capture work directories are created with `mktemp -d`, mode `0700`, owned by
the current user, and are never repository `.tmp/` paths. Apply installs an EXIT
cleanup trap that retains non-secret diagnostics on failure. Successful plan-only
and successful apply-capable runs retain the work directory (including validated
host evidence). Caller-supplied arbitrary paths are never deleted.

Plan binary, JSON plan evidence, and human-readable plan output in the temporary
workspace must be regular files with exact mode `0600` (no symlink; no
group/world read or write; no setuid/setgid/sticky). Parent temp directory remains
mode `0700`.

### Retained validated host evidence (Sprint 25b.5p)

After external operator-supplied host evidence passes the existing validator, the
controlled maintenance run atomically retains a byte-for-byte identical copy
inside the authoritative work directory:

| Mode | Retained evidence |
|------|-------------------|
| Plan-only success | `${WORK_DIR}/host-evidence-pre.json` (+ `${WORK_DIR}/host-evidence-pre.json.sha256`) |
| Apply success | pre as above **and** `${WORK_DIR}/host-evidence-post.json` (+ `.sha256` binding) |

A successful retained **plan-only** workdir therefore contains:

- saved Terraform plan (`staging-combined.tfplan`)
- plan JSON/text (`staging-combined.plan.json`, `staging-combined.plan.txt`)
- plan identity (`plan.identity.json`)
- host-evidence nonce (`host-evidence.nonce`)
- pre/post collect snippets
- completed validated `host-evidence-pre.json` (and SHA-256 binding)
- plan-only authority marker/log (`plan-only.complete`, `plan-only.authority.log`)
- repository SHA binding (`repository.sha`)

Plan-only does **not** invent or require post-apply evidence. Apply mode retains
fresh validated apply-run `host-evidence-pre.json` / `host-evidence-post.json`
in the **apply-run private workdir** only after validation (never injected into
the audited plan-only workdir).

Retention rules (fail closed):

- destination is a regular file, non-symlink, owned by current euid/egid, mode `0600`
- published via a private temporary file in `$WORK_DIR` then atomic exclusive publish
- never partially visible under the final name; never overwritten if the destination exists
- evidence JSON and its `.sha256` sidecar are one logical publication unit; success
  requires the complete pair
- if this invocation publishes a final path and a later retention step fails, only
  invocation-owned finals are removed (device/inode + ownership checked via `lstat`);
  pre-existing destinations/sidecars are never deleted
- retained destination is re-parsed and revalidated (schema/phase/nonce/account/region/
  instance/repository SHA/freshness/release/digest/boot/uptime/cloud-init/pointers/
  rollback marker false)
- SHA-256 binding proves retained bytes match the validated source
- retention failure → clear `FAIL_PHASE=host_evidence_retention`, nonzero exit, no
  plan-only success message, no apply authorization, no Terraform apply

**Operators must not manually inject evidence into an already completed workdir.**
Post-hoc injection is rejected (existing destination fails closed). The external
operator-supplied path remains the source of authority until validation succeeds;
the retained copy is not authoritative before that point.

## Backend / state verification

`terraform init` against the expected staging backend is mandatory on every
apply-capable and capture path. `STAGING_MAINTENANCE_SKIP_INIT` is rejected.
Backend bucket, state key, region, and workspace `default` are verified from
`.terraform/terraform.tfstate` after init.

## Host evidence and automatic nonce binding

Each controlled maintenance run **internally generates** a cryptographically
strong nonce (`secrets.token_hex(16)` → 32 lowercase hex chars) before host
evidence validation. The nonce is stored only as `host-evidence.nonce` inside the
run’s mode-`0700` temporary workspace (file mode `0600`).

Operators **cannot** choose the authoritative nonce:

- `STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE` is rejected
- the script does not silently create a second nonce for post evidence
- pre and post evidence must embed exactly the same generated run nonce

The run writes Session Manager collect snippets that embed the nonce explicitly:

- `${WORK_DIR}/host-evidence-collect-pre.sh`
- `${WORK_DIR}/host-evidence-collect-post.sh`

Session Manager evidence collection may require passwordless sudo solely for the
read-only rollback-marker existence check (`sudo -n test -e` on
`/opt/dealbrain/runtime/rollback-execution.marker`). Failure to obtain an
unambiguous marker result fails closed (nonzero; no valid evidence JSON). The
collector never creates, removes, or alters the marker.

Optional `STAGING_MAINTENANCE_EVIDENCE_WAIT_SECONDS` may wait for evidence files
to become valid after the nonce is printed (default `0` = fail immediately).

Accepted evidence JSON requirements:

- schema_version `1`
- phase `pre-apply` or `post-apply` (not interchangeable; swap rejected)
- bound account `941035169846`, region `us-east-1`, instance `i-0edd57f32296aa323`
- exact run nonce; malformed/missing/stale/mismatched nonce → fail closed
- timestamp freshness (default 1h for single-phase checks)
- validated boot ID, numeric uptime, allowlisted cloud-init status
- validated release ID + `sha256:` digest
- current pointer and previous pointer present (previous may be JSON `null`)
- rollback marker must be `false`
- when `repository_sha` is present in the schema, it must match the approved repo SHA
- regular file, mode not broader than `0600`, not a symlink

Release ID and immutable digest must be byte-for-byte identical before and after.
Current and previous pointers must be unchanged. Boot ID and uptime are recorded
for stop/start consistency without treating either signal alone as proof.

## Plan identity / TOCTOU binding

After plan-only `terraform plan -out`, the script forces plan mode `0600`, then
records:

- canonical path, regular-file / non-symlink status
- device ID, inode, size, SHA-256
- UID, GID (must equal current effective user/group)
- exact mode `0600`

Apply mode revalidates every recorded field against that **same** immutable
path before `terraform apply`. It does not copy the plan into another unbound
file, rewrite identity, or update modification time. Modes such as `0604`,
`0640`, `0644`, group/world-writable, or setuid/setgid/sticky are rejected.
Caller-supplied UID/GID/mode values are never accepted as authority.

Terraform’s native saved-plan / state lineage and serial safeguards remain in
force: a stale saved plan against newer state fails closed at `terraform apply`
with no repository bypass.

## Post-apply IAM structural verification

After apply, the script fetches inline policies:

- `dealbrain-staging-gha-deploy-allow`
- `dealbrain-staging-gha-deploy-deny`

and structurally parses JSON (not grep/substring). Normalized comparison requires
the approved staging contract: Deploy + Rollback document SendCommand allowlist,
staging-tagged EC2 target conditions, staging release-artifacts S3 prefixes,
describe/observe statements, and deny protections including `iam:*` (PassRole
mutation deny). Explicitly rejected in the allow policy regardless of statement
order: `iam:PassRole`, `iam:*`, action `*`, production ARNs, foreign accounts,
unexpected regions/documents/instances/buckets, and unexpected statements.

Failure sets `FAIL_PHASE=iam_policy_verification`, exits nonzero, and does not
report overall success or run Deploy Staging / Rollback Staging.

## Post-apply SSM document content verification

Verification is not limited to name/status/version. The active default document
version content is fetched and compared to the canonical contract derived from
`infra/terraform/modules/ssm_rollback_document` after JSON canonicalization:

- name `DealBrain-StagingRollback`, type `Command`, status `Active`
- owner/account `941035169846`
- environment fixed to staging
- entrypoint `/opt/dealbrain/bin/dealbrain-staging-rollback.sh`
- approved parameter definitions and `allowedPattern` constraints
- timeout exactly `2400` seconds (bounded; missing/excessive rejected)
- no free-form command parameter, no extra steps, no production identifiers,
  no env/secret dumps, no alternate executable path

Document create/describe/get must not invoke the document (no SendCommand).
Failure sets `FAIL_PHASE=ssm_document_content_verification`.

## Fail-closed monitoring and failure phases

All waits are bounded. Timeouts and health/integrity failures exit nonzero and
never print overall success. Distinguished phases include:

- preflight, plan_validation, apply
- ec2_recovery_timeout, alb_recovery_timeout, application_health
- host_evidence, host_evidence_nonce, host_evidence_phase, host_evidence_stale
- host_evidence_retention
- release_integrity, post_plan_drift
- plan_identity_owner, plan_identity_mode, plan_identity_checksum
- iam_policy_verification, ssm_document_content_verification

The script does not automatically mutate recovery (no instance recreate, state
surgery, `-target`, `ignore_changes`, Deploy Staging, Rollback Staging, or
production). Verification failures stop before Deploy Staging. Rollback Staging
remains unauthorized. No production promotion is authorized.

## Required future order

1. Complete and verify the controlled Terraform maintenance apply.
2. Confirm staging is healthy and current release/digest/pointers are unchanged.
3. Run Deploy Staging to install current rollback tooling.
4. Verify `staging-host-tooling.json` version/checksums.
5. Build and deploy a second immutable release.
6. Run rollback rehearsal-readiness audit.
7. Rehearse rollback to Build Image #15.
8. Stop before production.

Build Image #15 baseline: run `30741970067`, release
`rel-20260802T093246Z-83bfc6c57fd9`, SHA
`83bfc6c57fd99a43445b6edaddcaf863fabf3473`, digest
`sha256:338b03ad39cbb2d5733c8da5912e3ef1c38111e3f3b42d43eaf3b87bd9d1b91f`.

## Forbidden techniques

- `terraform -target`
- `lifecycle { ignore_changes = [user_data_base64] }`
- `terraform state rm` / manual state surgery
- arbitrary EC2 recreation
- production failover
- bypassing health checks / HEALTH_CLEAR attestation
- `STAGING_MAINTENANCE_SKIP_INIT`
- caller-selected `STAGING_MAINTENANCE_HOST_EVIDENCE_NONCE`
- authorizing Rollback Staging before Deploy Staging tooling delivery
- no production authorization

## Production isolation

Production Terraform, workflows, roles, hosts, and state keys are out of scope
and must not appear in the changing plan set. This gate authorizes staging only.
