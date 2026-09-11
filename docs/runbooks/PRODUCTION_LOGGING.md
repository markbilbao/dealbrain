# Production logging baseline (Early Access Phase 1)

Durable logs must exist **outside container stdout**. This phase does **not**
add product analytics, ad tracking, affiliate pixels, or on-call paging.

Alerts/paging remain a later phase (register **EXT-16** error tracking,
**EXT-24** monitoring/paging). CloudWatch log groups and ALB access logs can
accept metric filters later without redesigning the stack.

## Application logs

| Stream | Destination | Retention |
|--------|-------------|-----------|
| Compose `api` | CloudWatch Logs `/dealbrain/production/api` via Docker `awslogs` | 30 days |
| Compose `migrate` | CloudWatch Logs `/dealbrain/production/migrate` via Docker `awslogs` | 30 days |
| Host bootstrap / SSM | Instance disk `/var/log/dealbrain/` (EBS). CloudWatch group `/dealbrain/production/host` is provisioned for a future agent; this phase does not install a CloudWatch agent | 30 days (CW group); disk until volume lifecycle |

Terraform module: `infra/terraform/modules/logging/`.
Compose overlay: `infra/compose/docker-compose.production.yml` (`awslogs-create-group=false`; groups are Terraform-owned).

IAM: production API host role may `CreateLogStream` / `PutLogEvents` on those
groups only. Staging host is unchanged (no production log groups wired there).

Never print `DATABASE_URL`, `APP_SECRET_KEY`, Resend keys, or GHCR tokens in
logs. Host scripts and evidence modules redact secret-like fields.

## ALB / access logs

Production ALB writes access logs to:

`s3://dealbrain-production-alb-logs-<account>/alb/AWSLogs/<account>/`

Bucket: encrypted, versioned, public access blocked, lifecycle expiration **30
days**. Bucket policy allows the regional ELB log-delivery account
(`127311923021` in `us-east-1`) and `logdelivery.elasticloadbalancing.amazonaws.com`.

Staging ALB is unchanged unless an operator later opts in (`access_logs_bucket`
empty keeps current staging behavior).

## Deployment / health evidence location

Authoritative deploy and rollback evidence is **not** CloudWatch. Host-written
JSON + SHA-256 sidecar:

`s3://dealbrain-production-release-artifacts-<account>/evidence/<release_id>/<run_id>/production-deploy-evidence.json`

Rollback:

`s3://dealbrain-production-release-artifacts-<account>/evidence/<release_id>/<run_id>/production-rollback-evidence.json`

GitHub Actions also uploads a copy as a workflow artifact
(`production-evidence-*` / production rollback artifact) after validating the
host object. The workflow must not fabricate `production_ok` / `rollback_ok`.

Health probes used as evidence: `/live`, `/ready`, ALB target health. Record
those in the evidence JSON, not in a product analytics system.

## What this phase does not add

- No CloudWatch alarms, SNS topics, PagerDuty, or Opsgenie.
- No Datadog / Sentry / product analytics.
- No ad or affiliate tracking pixels.
- No log shipping to a third-party SIEM.

Those can attach later to the same log groups and ALB bucket.
