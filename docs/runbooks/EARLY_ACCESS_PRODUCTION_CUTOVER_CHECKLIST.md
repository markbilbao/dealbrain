# Early Access production cutover checklist — document only

**HOLD:** Do not execute this checklist. Early Access remains staging-only.
Privacy/Terms approval and separate launch authorization are mandatory. This
document does not start Sprint 27 or advance Sprints 41–45.

## Authorization and release identity

- [ ] Privacy Policy / Privacy Notice approved for publication.
- [ ] Terms & Conditions approved for publication.
- [ ] Approved legal URLs or files supplied; no placeholder URLs remain.
- [ ] Founder gives an explicit Early-Access production-launch authorization.
- [ ] Production work is scheduled under its existing roadmap owners.
- [ ] Release commit, CI run, immutable image digest, and manifest are recorded.

## Production environment and persistence

- [ ] Isolated production AWS environment and account boundaries verified.
- [ ] Production database is private, encrypted, migrated, and readiness-tested.
- [ ] Signup uniqueness and persistence are verified across deploy/restart.
- [ ] Least-privilege founder/operator read-only export access is verified.
- [ ] Backup retention, restore procedure, and a successful restore rehearsal are evidenced.

## Secrets, network, DNS, and TLS

- [ ] Production secrets exist only in the approved secret store and are rotation-ready.
- [ ] Production CORS, trusted hosts, rate limits, logging, and security headers fail closed.
- [ ] Public load balancer and target health are verified without exposing staging.
- [ ] Approved `piqsavi.com` DNS records are applied only in the authorized window.
- [ ] Valid production TLS certificate, HTTPS redirect, renewal, and HTTPS health checks pass.

## Deployment, health, and rollback

- [ ] Production deployment workflow is separately reviewed and environment-gated.
- [ ] Immutable digest deployment, migration ordering, and release evidence pass.
- [ ] `/live`, `/ready`, database readiness, and public smoke checks pass over HTTPS.
- [ ] Production rollback procedure and known-good prior digest are verified.
- [ ] Rollback preserves signup data and has an authorized operator/window.

## Logging, monitoring, abuse, and privacy

- [ ] Centralized production logs and alerts capture the Early Access lifecycle without PII.
- [ ] Shared/distributed public rate limiting is verified at actual production concurrency.
- [ ] Error, latency, availability, database, and target-health alarms notify an owner.
- [ ] Privacy and Terms footer links resolve to the approved content.
- [ ] Signup disclosure/consent UI exactly matches approved legal guidance.
- [ ] Retention, access, deletion, and incident-response handling for signup PII are approved.

## Final launch verification

- [ ] Desktop and mobile visual smoke tests match approved masters.
- [ ] New signup, normalized duplicate, validation, loading, error, Try Again, Back, and Close pass.
- [ ] UTM/referrer attribution and approved device-information policy are verified.
- [ ] Analytics lifecycle events are visible in the approved production log destination.
- [ ] Founder/operator can retrieve a private export without public exposure.
- [ ] Final launch GO is recorded with approver, time, release digest, and rollback owner.
- [ ] Post-launch watch window completes before the change is considered stable.
