# Production host foundation — prevent minimal AL2023 and guarantee early SSM (2026-09-14)

**Resulting state:** `PRODUCTION HOST FOUNDATION FIX READY FOR OWNER REVIEW — NO AWS MUTATION PERFORMED`

**Scope:** Code, tests, and documentation only. This change does **not** apply Terraform, replace the live production EC2 host, mutate AWS, change DNS, or merge.

**Verified `origin/main` at branch creation:** `4d0b33a8db07c1c02bcca3c82aa3d9e4bebd2702`

## Incident (live host, not mutated by this PR)

Production instance `i-0382907b275b835ce` is running with instance-status ok and
`AmazonSSMManagedInstanceCore` attached, but `ssm describe-instance-information`
returns no record. Terraform selected AMI `ami-085b153e241f89f29`
(`al2023-ami-minimal-2023.12.20260909.0-kernel-6.18-x86_64`). Console output shows
cloud-init `scripts-user` failed. AL2023 **minimal** does not ship SSM Agent;
combined with a failed user-data run, the host never registered with Systems Manager.

## Root cause in repository

1. `infra/terraform/modules/ec2` default AMI lookup used name filter
   `al2023-ami-*-x86_64`, which matches both standard and **minimal** AMIs.
   `most_recent = true` can therefore select `al2023-ami-minimal-*`.
2. Production `user_data` did not install/enable/start `amazon-ssm-agent` before
   Docker/Compose work, so a later bootstrap failure left no SSM path to
   `/var/log/dealbrain/bootstrap.log`.

## Fixes (this PR)

| Change | Behavior |
|--------|----------|
| Default AMI | Official AWS public parameter `/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64` (standard/default AL2023 x86_64, not minimal). Empty `var.ami_id` uses it; non-empty `var.ami_id` still overrides. |
| Early SSM | `infra/ec2/user_data/production.sh` installs, enables, starts, and verifies `amazon-ssm-agent` immediately after bootstrap logging starts and **before** Docker/Compose. Idempotent. Fail-closed if the unit is not active. |
| AMI lifecycle | `lifecycle { ignore_changes = [ami] }` is **retained**. Correcting the selector does **not** replace the current production host. Owner replaces `i-0382907b275b835ce` out-of-band after merge/review. |
| Security | No SSH, no inbound management ports, no secrets in user data. Existing API SG (8000 from ALB only) and host SSM IAM attachment are unchanged. |

## Additional bootstrap defect (not the live cloud-init failure)

The embedded SAFEEXTRACT copy in `production.sh` still rejected
`compose/docker-compose.production.yml` ("production overlay must not be present")
while also listing that file as required. That contradiction is the same class of
bug fixed in `scripts/deploy/verify_production_bundle.py` (PR #136). It is **not**
executed during cloud-init (the Python is written to disk, not run), so it cannot
explain the current `scripts-user` failure. It **would** fail the first
post-replacement bundle extract. The embedded check now rejects the staging overlay
instead, matching the canonical verifier.

No other deterministic cloud-init abort was proven from source alone; runtime
`bootstrap.log` is unavailable without SSM.

## Owner follow-up (not this PR)

After merge and independent review, replace the current production EC2 host
out-of-band so the new AMI selector and early-SSM user_data actually run.
Do not treat a Terraform plan that only changes the AMI *data source* as a host
replacement: AMI drift is ignored on the existing instance.
