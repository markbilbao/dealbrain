# DealBrain API Standards (Sprint 24)

Short implementer-facing standard. Authoritative architecture contract:
[`docs/architecture/SPRINT_24_API_STABILITY.md`](architecture/SPRINT_24_API_STABILITY.md).

## Versioning

| Rule | Detail |
|------|--------|
| Active version | `/api/v1` only |
| `/api/v2` | **Forbidden** in Sprint 24 |
| Unversioned probes | `/live`, `/ready`, `/health` (intentional) |
| Breaking changes | Out of scope — additive only |

## Success responses

- **Resource:** direct object (unchanged).
- **Collection:** keep existing named keys (`watchlists`, `notifications`, `events`, …).
  Optional additive `items` (duplicate of the named array) and `pagination`.
- **Bare lists:** `GET /products` and several `/user/*` lists remain JSON arrays.
- **Search (Kind S):** keep `{query, results, …}` — do not force `items`+`pagination`.
- **No** global `{data, meta}` envelope.

## Errors

Sprint 22 `ErrorBody` envelope (always includes legacy `detail`):

```json
{
  "error": "validation_error",
  "message": "…",
  "status_code": 422,
  "detail": "…",
  "details": [],
  "request_id": "req-…"
}
```

## Pagination

| Param | Notes |
|-------|-------|
| `limit` | Endpoint default; keep existing defaults |
| `offset` | Canonical; default `0` where introduced |
| `skip` | Deprecated alias of `offset` on **products** and **watchlists**; still accepted |

**Alias precedence:** only `skip` → use it; only `offset` → use it; both equal → OK;
both differ → **422**.

**Watchlists compatibility:** `GET /api/v1/watchlists` returns the **complete** list when
no `limit` / `offset` / `skip` are supplied. Pagination applies only when at least one
of those params is present.

Response `pagination` (additive when present):

```json
{ "limit": 50, "offset": 0, "total": 123, "has_more": true }
```

`total` may be omitted when expensive; `has_more` is preferred.

## Filtering

Query params, snake_case, domain-owned semantics. Preserve existing filter names.
Do not suddenly reject previously ignored unknown query params unless an endpoint
adopts an explicit filter model.

## Sorting

| Rule | Detail |
|------|--------|
| Param | `sort=field,-other` (comma-separated; `-` = desc) |
| Allowlists | Endpoint-specific; unknown field → 422 |
| Products | `created_at`, `brand`, `category` (no `name`) |
| Default | Service default when `sort` omitted |

**Hard ban — no caller sort influencing:**

- DealScore search
- Recommendation search
- Marketplace search
- Shopping Assistant organic ranking
- Affiliate / merchant organic visibility

## Deprecation

Mark OpenAPI `deprecated: true`; **do not remove** paths.
Sprint 10 legacy `/api/v1/alerts`, `/alerts/{id}`, acknowledge, dismiss remain available.

## OpenAPI drift

1. Phase 0 freeze: `tests/contracts/baselines/openapi_sprint23.json`
2. Active contract: `tests/contracts/baselines/openapi.baseline.json`
3. Drift test fails if live `create_app().openapi()` differs from the baseline
4. Update baseline **explicitly** (never auto-rewrite in tests):

```bash
.venv/bin/python scripts/update_openapi_baseline.py
```

## Frontend / client compatibility

**No frontend package exists in this repository.** Compatibility proxy:

- Existing API regression suite
- Frozen OpenAPI snapshots
- Representative response fixtures / contract tests

Sprint 24 must not require mandatory client changes.
