# Launch Checklist (Sprint 22)

**Status:** Sprint 22

**Also available via API:** `GET /api/v1/launch/checklist`

**Global Public Beta:** Final sign-off checklist is owned by **Sprint 45** per [`roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md). This Sprint 22 list remains the **rehearsal / demo** checklist.

Use this checklist before a public beta rehearsal. Items can be toggled in the
demo UI or via `PATCH /api/v1/launch/checklist/{item_id}` (admin token).

## Configuration

- [ ] `APP_ENV` set appropriately (`development` / `staging` / `production`)
- [ ] Staging and production env example files reviewed
- [ ] Feature flags reviewed (`GET /api/v1/launch/feature-flags`)
- [ ] `APP_DEBUG=false` for staging/production rehearsals
- [ ] No production secrets committed to the repo
- [ ] `LAUNCH_STRICT_STARTUP` considered for production (fails on config errors)

## Security

- [ ] Rate limiting enabled (`RATE_LIMITING_ENABLED=true`)
- [ ] Security headers enabled (`SECURITY_HEADERS_ENABLED=true`)
- [ ] CORS origins are explicit (no `*` in production)
- [ ] Structured logging redacts tokens/passwords/API keys
- [ ] Merchant isolation still enforced
- [ ] Affiliate links remain post-rank only

## Reliability

- [ ] `GET /live` returns up
- [ ] `GET /ready` returns ready when dependencies are healthy
- [ ] `GET /health` reports database + cache + version + uptime
- [ ] Docker HEALTHCHECK points at a probe endpoint
- [ ] Startup validation warnings reviewed in logs

## Product surfaces

- [ ] User auth login/register rate-limited
- [ ] Search / recommendations rate-limited
- [ ] Affiliate + merchant routes rate-limited
- [ ] Demo launcher personas switch (anonymous / registered / merchant / admin)
- [ ] Launch dashboard loads with admin token

## Documentation & ops

- [ ] DEPLOYMENT.md / PRODUCTION.md / SECURITY.md reviewed
- [ ] OPERATIONS.md / MONITORING.md / BACKUP_RESTORE.md reviewed
- [ ] OpenAPI (`/docs`) descriptions reviewed in staging
- [ ] Prior sprint tests still pass
- [ ] DealScore / recommendation ranking unchanged

## Explicit non-goals (do not block beta rehearsal)

- Real cloud deployment
- Production database cutover
- Payment processing
- Real email / SMS / push providers
- Subscription billing
- Production secret vault integration

> These non-goals apply to the **Sprint 22 rehearsal checklist only**.
> They **do block Global Public Beta** and are owned by Sprints 27 / 41 / 42 / 45 in the master roadmap.
