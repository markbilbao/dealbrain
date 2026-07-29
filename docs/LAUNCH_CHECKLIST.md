# Launch Checklist (Sprint 22)

**Status:** Sprint 22  
**Also available via API:** `GET /api/v1/launch/checklist`

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
