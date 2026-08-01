# Staging deploy runbook (Sprint 25b.3 / 25b.4a)

**Audience:** operators performing the first (and subsequent) staging digest deploys  
**Does not cover:** production promotion (25b.4+), automated rollback (25b.5)  
**25b.4a note:** repository pre-live refinements only — **no live AWS action** occurred in 25b.4a; **25b.4b** remains separately gated for apply / Environment / secrets / first deploy.

## Preconditions

- [ ] Remote Terraform state active; staging stack applied
- [ ] GitHub Environment `staging` exists (`main` only)
- [ ] Vars set: `AWS_ROLE_ARN` (= `dealbrain-staging-gha-deploy`), `AWS_REGION=us-east-1`, `AWS_ACCOUNT_ID`, `STAGING_TARGET_GROUP_ARN` (exact Terraform `alb_target_group_arn` output)
- [ ] Secrets populated under `dealbrain/staging/*` including `ghcr_pull`
- [ ] EC2 SSM Online; `/opt/dealbrain/bootstrap.ok` present (implies Docker engine + signed Compose plugin — Sprint 25b.5a)
- [ ] Successful **Build Image** workflow run on `main` (note run ID)

## Dispatch

1. Open Actions → **Deploy Staging** → Run workflow on `main`
2. Input `build_workflow_run_id` = Build Image run database ID
3. Optional `release_id` cross-check
4. Do **not** cancel an in-progress run (concurrency `cancel-in-progress: false`)

## Success signals

- Workflow green; SSM command Status=`Success`
- Host-uploaded evidence at `s3://…/evidence/<release_id>/<run_id>/staging-deploy-evidence.json` with `final_status=staging_ok`
- GitHub artifact `staging-evidence-<release_id>-<run_id>` (copy of host evidence; never synthesized)
- Host `/opt/dealbrain/current/DEPLOY_VERSION` matches release identity
- Localhost `/live` + `/ready` content gates
- ALB: **strict** acceptance — the expected staging EC2 instance is the sole target and `TargetHealth.State` is exactly `healthy` (no substring fallback)

## S3 readiness (25b.4a)

The workflow does **not** call `s3api head-bucket`. The deploy role’s `ListBucket` permission is prefix-conditioned under `releases/*` and `evidence/*`; bucket-existence preflight would require a broader grant that we intentionally refuse.

Authoritative checks are exact object operations:

- upload/download of `releases/<release_id>/…`
- `head-object` / get of host evidence under `evidence/<release_id>/<run_id>/…`

Missing or inaccessible release/evidence objects fail closed.

## Evidence writer (25b.4a)

Host evidence writing requires the canonical bundled `evidence.py` module. If that import fails, the writer exits non-zero and does **not** write or upload success evidence. There is no inline fallback writer.

## Common failures

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Manifest validation fail | Wrong run / not built | Re-run Build Image; use that run ID |
| OIDC AccessDenied | Env name/branch/vars | Fix GitHub Environment gates |
| S3 object Put/Get/Head denied | Prefix/IAM/key mismatch | Fix role prefix grants; do not add unscoped ListBucket for head-bucket |
| Missing host evidence | Host failed before upload / IAM | Inspect SSM output; fix host role evidence PutObject |
| Evidence module unavailable | Bundle missing `bin/evidence.py` | Rebuild/upload release bundle; do not bypass |
| SSM offline | NAT/agent/IAM | Fix networking; replace instance if needed |
| Bundle checksum mismatch | Tamper / wrong key | Re-upload via workflow; investigate |
| ALB not exactly healthy | Wrong TG, wrong instance, initial/unhealthy/mixed targets | Confirm `STAGING_TARGET_GROUP_ARN` and single staging instance registration |
| Migration failed / timeout | Schema / DB / 20m bound | API untouched; `current` remains prior release |
| Disk space | Images/logs | Expand volume / prune unused images |
| Stale flock | Crashed deploy | SSO Session Manager; remove lock info if PID dead >90m |

## Break-glass

Use AWS SSO + Session Manager only (no public SSH). Do not put secrets in SSM parameters or GitHub logs.
