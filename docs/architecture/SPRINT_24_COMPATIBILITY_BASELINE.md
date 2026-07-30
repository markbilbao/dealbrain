# Sprint 24 — Compatibility Baseline (Phase 0)

**Frozen at:** Sprint 23 merge baseline (pre–Sprint 24 behavior changes)  
**OpenAPI snapshot:** [`tests/contracts/baselines/openapi_sprint23.json`](../../tests/contracts/baselines/openapi_sprint23.json)  
**Route inventory:** [`SPRINT_24_ROUTE_INVENTORY.json`](SPRINT_24_ROUTE_INVENTORY.json)

## Frontend status

**No frontend / UI package exists in this repository.**

There is no `frontend/`, `web/`, `ui/`, `packages/*`, or `package.json` React/Next app.
The only HTML surface is `app/static/demo.html` via `/demo` (excluded from public API schema).

### Compatibility proxy

Because there is no in-repo frontend:

1. The existing API unit + integration regression suite
2. The frozen OpenAPI Sprint 23 snapshot
3. Representative response fixtures / Sprint 24 contract tests

serve as the **client-compatibility proxy**. Sprint 24 must keep those green without
removing assertions of pre-Sprint-24 field names or status codes.

## Inventory summary (Phase 0 freeze)

| Metric | Value |
|--------|-------|
| OpenAPI paths | 193 |
| Operations | 231 |
| Bare-list success responses | `GET /api/v1/products`, `GET /api/v1/user/saved-products`, `GET /api/v1/user/history`, `GET /api/v1/user/comparisons`, `GET /api/v1/user/searches` |
| Pagination styles | `skip`/`limit` (products), `offset`/`limit` (notifications), `limit`-only (many), none |
| Sorting query params | None at freeze |
| Error envelope | Sprint 22 `ErrorBody` + legacy `detail` + `request_id` |
| `/api/v2` | Absent (must remain absent) |

## Named collection keys (must remain)

Examples (non-exhaustive): `watchlists`, `notifications`, `events`, `rules`, `alerts`,
`runs`, `jobs`, `links`, `merchants`, `history`, plus merchant `items` lists.

## Ranking / neutrality (must not gain caller sort)

- `GET /api/v1/dealscore/search`
- `GET /api/v1/recommendations/search`
- `GET /api/v1/marketplace/search`
- Shopping Assistant query/demo organic ordering

## Deprecated (keep available)

Sprint 10 legacy alert routes under `/api/v1/alerts` (list/get/acknowledge/dismiss).

## Phase 0 constraints

- No production response-body changes in Phase 0
- Baseline OpenAPI is deterministic JSON (`sort_keys=True`)
- Subsequent Sprint 24 work updates `openapi.baseline.json` explicitly alongside code
