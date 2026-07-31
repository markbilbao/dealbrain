# Staging deploy runbook (Sprint 25b.3)

**Audience:** operators performing the first (and subsequent) staging digest deploys  
**Does not cover:** production promotion (25b.4+), automated rollback (25b.5)

## Preconditions

- [ ] Remote Terraform state active; staging stack applied
- [ ] GitHub Environment `staging` exists (`main` only)
- [ ] Vars set: `AWS_ROLE_ARN` (= `dealbrain-staging-gha-deploy`), `AWS_REGION=us-east-1`, `AWS_ACCOUNT_ID`, `STAGING_TARGET_GROUP_ARN` (exact Terraform `alb_target_group_arn` output)
- [ ] Secrets populated under `dealbrain/staging/*` including `ghcr_pull`
- [ ] EC2 SSM Online; `/opt/dealbrain/bootstrap.ok` present
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
- Localhost `/live` + `/ready` content gates; ALB target healthy

## Common failures

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| Manifest validation fail | Wrong run / not built | Re-run Build Image; use that run ID |
| OIDC AccessDenied | Env name/branch/vars | Fix GitHub Environment gates |
| Missing host evidence | Host failed before upload / IAM | Inspect SSM output; fix host role evidence PutObject |
| SSM offline | NAT/agent/IAM | Fix networking; replace instance if needed |
| Bundle checksum mismatch | Tamper / wrong key | Re-upload via workflow; investigate |
| Migration failed / timeout | Schema / DB / 20m bound | API untouched; `current` remains prior release |
| Disk space | Images/logs | Expand volume / prune unused images |
| Stale flock | Crashed deploy | SSO Session Manager; remove lock info if PID dead >90m |

## Break-glass

Use AWS SSO + Session Manager only (no public SSH). Do not put secrets in SSM parameters or GitHub logs.
