# DealBrain Sprint 24 — Architecture Contract

**Theme:** API Stability & Integration Foundation  
**Status:** Implemented (Sprint 24) — additive, backward compatible  
**Depends on:** Sprints 1–23 (merged), Architecture Lock through Sprint 40  
**Audience:** Implementation agents and reviewers executing Sprint 24

---

## 0. Non-negotiable constraints

These constraints override any conflicting tactic elsewhere in this document.

### 0.1 Backward compatibility is mandatory

- Sprint 24 **must not require frontend changes**.
- Existing API consumers **must continue working** without mandatory client updates.
- Existing response bodies and HTTP status codes **must remain valid** unless a change is explicitly documented as **additive and backward compatible**.
- Existing paths **must not be removed**.
- Deprecated paths **may remain available** and must be marked `deprecated: true` in OpenAPI.
- New metadata, aliases, dual keys, and documentation **must be additive**.
- Removing fields, renaming paths, changing status codes, or requiring clients to adopt `items`/`pagination` is **forbidden** in Sprint 24.

### 0.2 OpenAPI is the implementation contract

- OpenAPI **must be updated before or alongside** endpoint standardization (never after as an afterthought).
- Implementation and tests **must conform** to the documented OpenAPI contract.
- OpenAPI must accurately describe: request models, response models, errors, pagination, filtering, sorting, authentication, and deprecated routes.
- Sprint 24 must include a **contract test / CI validation plan** that detects OpenAPI drift (schema snapshot or equivalent).
- **Do not introduce `/api/v2`** in Sprint 24.

### 0.3 Compatibility gate (release blocker)

> **Sprint 24 passes only if the existing frontend and current API test suite work without mandatory client changes.**

This gate is part of Definition of Done (§14) and Phase 7 (§17).

### 0.4 Success response strategy (locked)

- Preserve **direct resource response bodies**.
- **Do not** apply a global `{ "data": ..., "meta": ... }` wrapper.
- Collection endpoints may standardize toward `{ "items": [...], "pagination": {...} }` **only** where this can be introduced **without breaking** current consumers (typically via dual-run: keep named keys, add optional fields).
- Existing named collection keys **remain** during a documented compatibility period (through at least Sprint 24; removal is a later sprint).

### 0.5 Sorting restrictions (locked)

Sorting must **never** override or influence:

- DealScore
- Recommendation
- Shopping Assistant organic ranking
- Affiliate neutrality
- Merchant neutrality

Sorting is allowed **only** for endpoint-owned presentation fields using **explicit allowlists**.

---

## 1. Sprint 24 Overview

Sprint 24 standardizes DealBrain’s **public HTTP API surface** so every endpoint behaves consistently for web, mobile, and future external integrations — **without forcing client changes**.

Production persistence (Sprint 23) and all domain engines (Sprints 1–22) are **frozen owners**. Sprint 24 does **not** redesign domains, ranking, recommendations, or persistence. It improves **contract consistency**: response shapes, errors, validation, pagination/filtering/sorting, versioning, OpenAPI completeness, integration tests, and API documentation.

**OpenAPI is the source of truth for the HTTP contract.** Code follows OpenAPI; tests assert both.

**Current baseline (as of Sprint 23):**

| Concern | Current state |
|---------|---------------|
| Path versioning | `/api/v1/...` (~232 routes) + unversioned probes |
| Success bodies | Direct Pydantic schemas; **no** shared success envelope |
| Errors | Sprint 22 `ErrorBody` envelope (+ legacy `detail`) |
| Pagination | Inconsistent: `skip`/`limit`, `offset`/`limit`, `limit`-only, or none |
| Filtering | Ad hoc query params per domain |
| Sorting | **None** exposed as query params |
| OpenAPI | Enabled when docs flag on; tag metadata incomplete; no drift CI gate |
| Tests | Strong unit API coverage; integration flows exist; no shared API-contract suite |
| Frontend | Assumed to consume current `/api/v1` shapes; Sprint 24 must not force updates |

Sprint 24 turns this baseline into an **executable, non-breaking standardization plan**.

---

## 2. Goals

1. **Unified response conventions** for single-resource and collection endpoints without breaking existing clients or requiring frontend changes.
2. **Canonical error contract** (formalize Sprint 22; close gaps; document codes in OpenAPI).
3. **Shared request validation** patterns (Query/Body/Path) via reusable dependencies/schemas.
4. **One pagination standard** (`limit` + `offset` + response `pagination` metadata) introduced **additively**.
5. **One filtering standard** (documented query grammar; domain-owned filter fields).
6. **One sorting standard** (`sort` query param; allowlisted presentation fields only; neutrality-safe).
7. **Explicit versioning strategy** (keep `/api/v1` only; no `/api/v2`).
8. **Endpoint naming conventions** for all current and future routes (document; do not mass-rename).
9. **OpenAPI as implementation contract** (complete, accurate, drift-detected).
10. **Integration test coverage matrix** across all major domains (§13.6).
11. **API documentation** that matches runtime OpenAPI and this contract.
12. Preserve every Architectural Lock invariant from Sprints 1–23.
13. Pass the **compatibility gate**: existing frontend + current API test suite work without mandatory client changes.

---

## 3. Non-goals

Sprint 24 **must not**:

- Require frontend or other client changes
- Add product features, new domains, or new ranking/recommendation behavior
- Change DealScore formulas, Recommendation decisions, or Shopping Assistant ordering
- Redesign persistence, repositories, migrations, or adapter selection (Sprint 23 ownership)
- Move ownership of any Sprint 5–23 domain
- Silently break existing response field names, status codes, or paths
- Introduce a global success envelope `{data, meta}` wrapping all payloads
- Replace named collection keys with `items`-only responses in this sprint
- Remove Sprint 10 legacy `/alerts` paths (Architecture Lock: keep until proven migration)
- Introduce `/api/v2`
- Build Redis, real marketplace connectors, billing, WAF/CDN, or UI redesign
- Merge consumer and merchant identity systems
- Change affiliate/merchant neutrality rules or attachment order
- Allow `sort` (or any API param) to influence DealScore, Recommendation, Shopping Assistant organic ranking, affiliate attachment order, or merchant organic visibility

---

## 4. Architecture Diagram

```text
┌──────────────────────────────────────────────────────────────────────────┐
│              Clients (Web / Mobile / External) — NO MANDATORY CHANGES    │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │  HTTPS  /api/v1  (no /api/v2)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Transport & Ops (Sprint 22 — unchanged ownership)                       │
│  probes · rate limit · logging · security headers · request_id           │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────┐
│  API Contract Layer (Sprint 24 — THIS SPRINT)                            │
│                                                                          │
│  OpenAPI = implementation contract (updated before/alongside code)       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │
│  │ Naming &   │  │ Shared DTOs│  │ Pagination │  │ Error Contract     │  │
│  │ Versioning │  │ Validation │  │ Filter/Sort│  │ (Sprint 22 formal) │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Contract tests · OpenAPI drift CI · Compatibility gate             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │  mappers only (additive shape translation)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Domain Services (Sprints 1–21 — LOCKED owners)                          │
│  Identity · Search · DealScore · Reco · Price · Collections · Watchlists │
│  Reviews · AI · Community · Graph · Users · Sync · Alerts · Affiliate    │
│  Merchant · …                                                            │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    │  ports / repositories
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Persistence Adapters (Sprint 23 — LOCKED)                               │
│  SQLAlchemy · transactions · migrations · readiness                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Rule:** Sprint 24 may change **HTTP shapes (additively), shared schemas, OpenAPI, and tests**. It may **not** change domain decision logic, persistence semantics, or force client migration. Mappers remain the only place that translates domain objects ↔ HTTP DTOs.

---

## 5. Ownership Matrix

| Concern | Owner sprint | Sprint 24 may… | Sprint 24 may not… |
|---------|--------------|----------------|--------------------|
| API contracts, DTOs, OpenAPI, versioning docs | **24** | Standardize additively; dual-run; OpenAPI-first | Change business meaning of fields; break clients |
| Error envelope handlers | 22 (infra) + **24** (contract formalization) | Complete codes/docs/tests in OpenAPI | Remove `detail` compatibility |
| DealScore | 5 | Document Kind S search shape | Change scores/weights; add ranking `sort` |
| Recommendations | 6 | Same | Change Buy/Wait/Consider/Avoid; add ranking `sort` |
| Price history | 7 | Additive paginate/filter/sort wrappers | Change stats/trends semantics |
| Marketplace search | 4 | Contract wrappers / docs | Change organic ordering; ranking `sort` |
| Collections / collection-ops | 8 / 9 | Additive list pagination | Change job semantics |
| Watchlists / legacy alerts | 10 | Contract consistency | Delete legacy `/alerts` |
| Alert rules / notifications | 19 | Contract consistency | Change evaluation rules |
| Affiliate | 20 | Contract consistency | Affect ranking / attach earlier |
| Merchant | 21 | Contract consistency | Affect organic visibility |
| Users / auth / profile | 17 | Contract consistency | Merge with merchant identity |
| Marketplace sync / offers | 18 | Contract consistency | Change sync semantics |
| Launch / probes / rate limit | 22 | Document probe exception to versioning | Redesign launch infra |
| Persistence | 23 | Prove persistence-backed API behavior in tests | Redesign adapters/migrations |
| AI / community / graph / personal | 11–16 | Contract consistency | Change ranking ownership |

**Sprint 24 sole ownership:** API contracts, endpoint consistency, DTO standardization, OpenAPI generation quality, API versioning strategy, shared response models, error response consistency, pagination/filtering/sorting standards, API integration tests, API documentation, OpenAPI drift detection, compatibility gate.

---

## 6. Endpoint Inventory

**Base:** `/api/v1`  
**Unversioned probes (intentional):** `/live`, `/ready`, `/health`  
**Excluded from public contract:** `/demo` (HTML, `include_in_schema=False`)  
**Forbidden in Sprint 24:** `/api/v2` or any second public version path

### 6.1 Compliance legend

| Status | Meaning |
|--------|---------|
| **Compliant** | Matches Sprint 24 target conventions closely enough that work is docs/OpenAPI/tests only |
| **Needs standardization** | Correct domain behavior; HTTP shape, pagination, naming, or OpenAPI needs additive Sprint 24 work |
| **Deprecated** | Kept available; marked deprecated in OpenAPI; **not removed** |

### 6.2 Inventory by domain

#### Probes / health — mostly compliant (special case)

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/live`, `/ready`, `/health` | Compliant | Unversioned by design (k8s) |
| GET | `/api/v1/live`, `/ready`, `/health` | Compliant | Versioned mirrors |
| GET | `/demo` | N/A | Not public API |

#### Launch (`/api/v1/launch`) — needs standardization (OpenAPI/docs)

| Endpoints | Status | Notes |
|-----------|--------|-------|
| `GET /meta`, `/dashboard`, `/feature-flags`, `/system-status` | Needs standardization | Response shapes OK; OpenAPI tags/examples |
| Demo launcher, checklist, config export/import, performance | Needs standardization | Internal/ops; keep paths; document as launch-ops |

#### Auth / profile / user (`/auth`, `/profile`, `/user`) — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| Auth register/login/logout/me | Needs standardization | Error codes already mapped; list endpoints N/A |
| Profile GET/PUT + preferences | Needs standardization | Naming OK |
| Saved products, history, comparisons, searches, recently-viewed | Needs standardization | Several bare lists; additive pagination only if non-breaking |

#### Products — needs standardization

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/products` | Needs standardization | Uses `skip`/`limit` → add `offset` as alias dual-run; keep `skip`; additive `pagination` only if response wrap stays compatible |
| GET/POST/PUT/DELETE | `/products/{id}` | Needs standardization | CRUD naming OK; OpenAPI completeness |

#### Intelligence / marketplace search / DealScore / recommendations

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/intelligence/parse`, `/match` | Needs standardization | Request/response docs |
| GET | `/marketplace/search` | Needs standardization | Search aggregate shape kept; **no ranking `sort`** |
| GET | `/dealscore/search` | Needs standardization | Same; **no ranking changes / no `sort`** |
| GET | `/recommendations/search` | Needs standardization | Same; **no decision changes / no `sort`** |

#### Marketplace data (`/marketplaces`, history under `/products`) — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| Sources, connectors, imports, sync, offers, demo/seed | Needs standardization | Some `count`; additive `pagination` where lists grow and consumers stay compatible |
| Product/inventory history | Needs standardization | Align docs with price-history conventions |

#### Price history — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| Snapshots POST; product/listing/search/range GETs | Needs standardization | Filter (`start`/`end`) keep; presentation sort allowlist only where applicable |

#### Collections / collection-operations — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| Runs/jobs list endpoints | Needs standardization | `limit`-only → add `offset` default 0; additive `pagination` if safe |
| Pause/resume/run/health/readiness | Compliant (ops verbs) | Document action naming |

#### Watchlists — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| CRUD + items/offers/history/pause/resume/archive | Needs standardization | Named wrappers (`watchlists`) **must remain**; optional dual-run `items`+`pagination` |
| Preferred merchants/categories; check-alerts | Needs standardization | Keep paths |

#### Alerts — mixed

| Area | Status | Notes |
|------|--------|-------|
| Sprint 19 `/alerts/rules`, `/alerts/evaluate`, `/alerts/events` | Needs standardization | Canonical engine; additive pagination on events |
| Sprint 10 `GET /alerts`, `/alerts/{id}`, acknowledge/dismiss | **Deprecated** | Remain available; OpenAPI `deprecated: true`; **do not remove** |

#### Notifications / dashboard — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| Notifications list | Needs standardization | Already `limit`/`offset`; keep `notifications` key; optional additive `items`+`pagination` |
| Preferences, unread-count, read-all | Needs standardization | Docs/OpenAPI |
| Dashboard GET | Compliant (single resource) | Document limitations field |

#### Affiliate — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| link / click / report / merchant / disclosure routers | Needs standardization | List wrappers; OpenAPI; **no ranking coupling**; **no neutrality-breaking sort** |

#### Merchant (`/merchants`, `/admin`) — needs standardization

| Area | Status | Notes |
|------|--------|-------|
| Orgs, members, invitations, catalog, offers, promotions, campaigns, analytics, audit | Needs standardization | Often already uses `items`; additive pagination where missing |
| Admin approve/reject/suspend/activate/verification | Needs standardization | Action verbs OK |

#### Reviews / review-summary / shopping-assistant / community / graph / personal

| Area | Status | Notes |
|------|--------|-------|
| Reviews collect/get/history/compare | Needs standardization | `limit`-only lists; additive offset/pagination if safe |
| Review-summary, shopping-assistant, community, graph, personal | Needs standardization | Meta/demo keep shapes; **Shopping Assistant: no organic ranking `sort`** |

### 6.3 Summary counts (planning estimate)

| Category | Approx. share |
|----------|---------------|
| Already compliant (probes + a few single-resource/ops) | ~5–10% |
| Needs standardization | ~85–90% |
| Deprecated (Sprint 10 legacy alerts) | ~4 endpoints |

Exact route count is ~232 including mirrors; Phase 0 freezes baseline via OpenAPI export and marks each route (see §17).

---

## 7. Response Contract

### 7.1 Design decision (compatibility-first — locked)

**Preserve direct resource response bodies.**

**Do not apply a global `{ "data": ..., "meta": ... }` wrapper.**

A mandatory success envelope would break frontend and all Sprint 1–23 clients and violate §0.1 / Architecture Lock.

**Unified success contract = three response kinds:**

| Kind | When | Shape |
|------|------|-------|
| **Resource** | Single entity or action result | Direct object (existing pattern) — **unchanged** |
| **Collection** | Homogeneous lists | May move toward §7.3 **only if non-breaking** (usually dual-run §7.4) |
| **Search aggregate** | Ranked/search results | Keep `{ query, results, ... }` domain shape; document as Kind S |

Errors always use the Error Contract (§8), never the success shapes.

**Status codes:** Existing success and error status codes remain valid. Do not change status code mappings as part of “standardization.”

### 7.2 Resource response

```json
{
  "watchlist_id": "wl_123",
  "name": "Phones",
  "status": "active"
}
```

Rules:

- Return the domain `*Response` / `*Payload` object directly.
- Include `response_model` on every route (OpenAPI accuracy).
- Optional additive fields allowed if documented, optional for old clients, and reflected in OpenAPI **before or alongside** code.
- `204 No Content` remains valid for deletes with empty body.

### 7.3 Collection response (target — non-breaking introduction only)

Target shape for **new or safely dual-run** collection endpoints:

```json
{
  "items": [ { "...": "..." } ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 123,
    "has_more": true
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `items` | array | only when dual-run or already present | Must not replace named keys in Sprint 24 |
| `pagination` | object | optional additive when paging applies | See §9 |
| Named domain key | array | **keep if already present** | e.g. `watchlists`, `notifications` |
| `disclaimer` / `limitations` | array/string | optional | Preserve where already used |

**Eligibility rule:** Introduce `items` / `pagination` **only where this can be introduced without breaking current consumers**. If adding `items` would break a strict schema client that rejects unknown fields, prefer documenting the target without changing the live body until a later negotiated migration — **default assumption for DealBrain JSON clients is unknown fields are tolerated; Phase 0 must verify frontend tolerance**. If frontend rejects unknown fields, Sprint 24 limits collection work to OpenAPI docs + query-param aliases only.

### 7.4 Dual-run compatibility for named list keys

Many endpoints today return `{ "watchlists": [...] }`, `{ "notifications": [...] }`, etc.

**Migration rule (additive):**

1. Keep the existing named key (mandatory).
2. Optionally add `items` as a **duplicate** of the same array (same order, same objects) when safe.
3. Optionally add `pagination` when paging applies and safe.
4. Document named keys as the **current primary** consumer fields; describe `items` as additive alias in OpenAPI.
5. Removal of named keys is **out of Sprint 24**.

Example (notifications after safe dual-run):

```json
{
  "notifications": [ { "notification_id": "..." } ],
  "items": [ { "notification_id": "..." } ],
  "pagination": { "limit": 50, "offset": 0, "total": 10, "has_more": false }
}
```

### 7.5 Search aggregate response (Kind S)

Do **not** force DealScore / marketplace / recommendation / Shopping Assistant search into `items`+`pagination` if results are ranked with domain-specific fields.

Keep:

```json
{
  "query": "iphone",
  "results": [ { "...": "..." } ]
}
```

**No `sort` parameter** on these endpoints in Sprint 24. Ranking ownership stays with Sprints 4/5/6/13/16.

### 7.6 Shared schema modules (implementation blueprint)

Create (when implementing — after OpenAPI update in Phase 2):

- `app/schemas/api_common.py` — `PaginationMeta`, collection helpers, shared literals
- Re-export from domain schemas as needed
- Mappers may attach additive fields without touching domain decision logic

---

## 8. Error Contract

### 8.1 Canonical envelope (Sprint 22 — formalized)

```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "status_code": 422,
  "detail": "Request validation failed",
  "details": [ { "loc": ["body", "email"], "msg": "field required" } ],
  "request_id": "req-abc123"
}
```

| Field | Required | Purpose |
|-------|----------|---------|
| `error` | yes | Machine-readable code (stable string) |
| `message` | yes | Human-readable, redacted-safe |
| `status_code` | yes | HTTP status mirrored in body |
| `detail` | yes | FastAPI legacy compatibility (same as `message` unless override) |
| `details` | no | Structured validation / field errors |
| `request_id` | no | Correlation (prefer always set when middleware present) |

### 8.2 Standard error codes

| HTTP | `error` code | Usage |
|------|--------------|-------|
| 400 | `validation_error` / domain validation codes already mapped | Bad input |
| 401 | `authentication_error` | Missing/invalid auth |
| 403 | `authorization_error` | Authenticated but forbidden |
| 404 | `not_found` | Missing resource |
| 409 | `conflict` | Uniqueness / state conflict |
| 422 | `validation_error` | Pydantic/request validation |
| 429 | `rate_limited` | Rate limit |
| 500 | `internal_error` | Unexpected |
| 503 | `service_unavailable` | Readiness/dependency down |

Domain-specific codes already mapped in `app/core/errors.py` remain valid. Status codes currently returned by endpoints **must not change** as part of Sprint 24 unless a bug is explicitly documented.

### 8.3 Sprint 24 error work

1. Treat `ErrorBody` as the **only** public error shape.
2. Ensure OpenAPI documents error responses for 4xx/5xx on all tagged routes (**OpenAPI-first**).
3. Reduce duplicated per-router `_map_error` only if behavior-identical (optional).
4. Never return raw FastAPI `{"detail": ...}` alone for handled errors.
5. Do not remove `detail` in Sprint 24.

---

## 9. Pagination Contract

### 9.1 Query parameters (canonical)

| Param | Type | Default | Constraints | Notes |
|-------|------|---------|-------------|-------|
| `limit` | int | endpoint default (document) | `ge=1`, `le=max` | Keep existing defaults where present |
| `offset` | int | `0` | `ge=0` | Canonical offset; additive where missing |

**Deprecated alias:** `skip` (products) — **keep accepting** as alias of `offset`; OpenAPI mark deprecated. Do not remove `skip` in Sprint 24.

**Not used in Sprint 24:** `page` / `page_size`, cursor tokens, `/api/v2`.

### 9.2 Response metadata (additive)

```json
{
  "limit": 50,
  "offset": 0,
  "total": 123,
  "has_more": true
}
```

Add `pagination` to response bodies **only** when safe for consumers (§7.3 eligibility). Query-param standardization (`offset`) may proceed even when response `pagination` is deferred, as long as existing params keep working.

| Field | Rule |
|-------|------|
| `limit` | Echo effective limit |
| `offset` | Echo effective offset |
| `total` | Prefer when cheap; omit only if documented |
| `has_more` | Prefer when `total` known |

### 9.3 Defaults (recommended families)

| Family | Default `limit` | Max |
|--------|-----------------|-----|
| Notifications, alerts, events | 50 | 200 |
| Products, offers, audit | 100 | 500 |
| Collections runs | 20 | 100 |
| Personal deals | 5 | 20 |
| Reviews | 50 | 200 |

Preserve existing defaults when already established. Endpoints that are `limit`-only may add `offset` with default `0` (additive).

### 9.4 Non-paginated endpoints

Single resources, auth actions, evaluate/run actions, meta/demo, Kind S search, and small bounded enums may omit pagination. Document in OpenAPI: “Not paginated.”

---

## 10. Filtering Contract

### 10.1 Principles

1. Filters are **query parameters** on GET (and safe list) endpoints.
2. Filter field names are **snake_case**, matching resource fields when possible.
3. Unknown filter params → **422** only after an explicit `FilterParams` model is adopted for that endpoint; until then, do not suddenly start rejecting previously ignored extras if that would break clients — Phase 0 documents current FastAPI behavior per route.
4. Domain services own filter **semantics**; API owns **parameter names and validation** as described in OpenAPI.
5. Filters must not become a backdoor to change organic ranking owned by other sprints.

### 10.2 Shared patterns

| Pattern | Convention | Examples |
|---------|------------|----------|
| Exact match | `field=value` | `status=active` |
| Boolean | `enabled=true` | alert rules, watchlist items |
| Free text | `q=` | search endpoints only |
| Time range | `start`, `end` (ISO-8601) | price history |
| Ownership scope | derived from auth, not spoofable query | prefer session user over `user_id` in production |
| Nested scope | path params preferred | `/watchlists/{id}/items` |

### 10.3 Implementation pattern

Per list endpoint (or family), define a Pydantic model documented in OpenAPI first, then wired via `Depends()`.

### 10.4 Existing filters to preserve

`q`, `status`, `enabled`, `type`, `priority`, `unread`, `watchlist_id`, `alert_type`, `item_id`, `rule_id`, `marketplace`, `source_mode`, `product_id`, `include_stubs`, `failed_only`, `mode`, `start`/`end`, `currency`, `profile_id`, graph traversal clamps, `enrich`, demo `user_id` (document as demo-only).

Rename only with dual-run aliases. Never remove existing filter params in Sprint 24.

---

## 11. Sorting Contract

### 11.1 Query parameter

| Param | Format | Example |
|-------|--------|---------|
| `sort` | `field` or `-field` | `sort=-created_at` |

- Prefix `-` = descending; no prefix = ascending.
- Multiple fields: comma-separated, left-to-right: `sort=-priority,created_at`.
- Default sort remains **service default** when `sort` omitted (preserves current behavior).
- `sort` is **optional and additive**; omitting it must yield today’s ordering.

### 11.2 Allowlists

Each eligible endpoint declares an allowlist in OpenAPI. Unknown fields → 422.

Suggested initial allowlists (presentation fields only):

| Endpoint family | Allowlist (runtime) |
|-----------------|---------------------|
| Notifications | `created_at`, `priority` |
| Alert events | `created_at` |
| Products | `created_at`, `brand`, `category` |
| Watchlists | `created_at`, `name`, `status` |
| Watchlist history | `created_at` |
| Legacy alerts | `created_at` |
| Merchant audit log | `created_at` |
| Collection runs (ops) | `started_at`, `created_at` |
| Affiliate links | `created_at` |

### 11.3 Hard restrictions (non-negotiable)

Sorting must **never** override or influence:

1. **DealScore** computation or DealScore search result ordering  
2. **Recommendation** decisions or recommendation search ordering  
3. **Shopping Assistant** organic ranking  
4. **Affiliate neutrality** (commission, partner priority, conversion value)  
5. **Merchant neutrality** (sponsored/merchant data must not reorder organic results)

Therefore:

- **No `sort`** on `/dealscore/search`, `/recommendations/search`, `/marketplace/search`, or Shopping Assistant query/result ordering endpoints in Sprint 24.
- Sorting is allowed **only** for endpoint-owned presentation fields on non-ranking list endpoints, using explicit allowlists.
- Affiliate and merchant list endpoints may sort their **own** operational lists (e.g. audit log by `created_at`) but must not expose sorts that feed into organic ranking pipelines.

---

## 12. Versioning Strategy

### 12.1 Current and target

| Mechanism | Sprint 24 decision |
|-----------|-------------------|
| URL path | **Keep** `/api/v1` as the only public versioned API |
| Headers | No required `Accept-Version` in Sprint 24 |
| Unversioned probes | Remain at `/live`, `/ready`, `/health` |
| `/api/v2` | **Not created** in Sprint 24 — non-negotiable |

### 12.2 Compatibility policy

1. Additive changes only in Sprint 24 (new optional fields, dual keys, aliases).
2. Breaking changes are **out of scope**; if discovered necessary, stop and architecture-review — do not ship.
3. Deprecation annotations in OpenAPI (`deprecated: true`) + docs entry; paths remain available.
4. Removal of deprecated fields/paths is **not** Sprint 24 scope.

### 12.3 What constitutes a break (forbidden)

- Removing/renaming a response field
- Changing field type or enum meaning
- Changing default ordering of ranked search results
- Removing a path
- Changing status codes clients rely on
- Requiring stricter auth without documented dual-run (and still no mandatory frontend change in Sprint 24)
- Changing error `error` code strings clients rely on
- Requiring clients to read `items` instead of named keys
- Introducing `/api/v2`

### 12.4 Endpoint naming conventions

| Rule | Example |
|------|---------|
| Plural nouns for collections | `/watchlists`, `/products` |
| kebab-case path segments | `/price-history`, `/shopping-assistant` |
| snake_case JSON fields | `watchlist_id` |
| Path params: `{resource_id}` | `/alerts/{alert_id}` |
| Actions as subresources or POST verbs | `/alerts/{id}/acknowledge` |
| Admin under `/admin` | existing merchant admin |
| Auth under `/auth` | existing |

Sprint 24 **documents** conventions; it does **not** mass-rename paths.

---

## 13. Integration Test Strategy

### 13.1 Goals

Prove that Sprint 24 changes are:

1. **Behavior-preserving** for domain outputs  
2. **Contract-correct** vs OpenAPI  
3. **Backward compatible** with existing frontend and current API tests  
4. **Neutrality-safe** for ranking / affiliate / merchant  

### 13.2 Test layers

| Layer | Location (planned) | Focus |
|-------|--------------------|-------|
| OpenAPI drift CI | `tests/unit/api_contract/test_openapi_drift.py` (or equiv.) | Fail if live schema diverges from committed baseline / required components |
| Contract unit | `tests/unit/api_contract/` | Pagination params, error envelope, dual-key presence, sort allowlists |
| Existing unit API | `tests/unit/test_*_api.py` | **Must stay green without weakening assertions of old fields** |
| Integration flows | `tests/integration/test_*_flow.py` | Keep green; no domain expectation changes |
| Compatibility gate | Phase 7 script/checklist | Frontend smoke (or recorded client fixtures) + full current API suite |
| Neutrality regression | reuse Sprint 20/21/23 patterns | Affiliate/merchant do not alter organic ordering via API |
| Persistence-backed API | extend/reuse Sprint 23 persistence tests at HTTP where applicable | Durable stores still serve correct API shapes |

### 13.3 OpenAPI drift detection plan

1. Phase 0: export and freeze baseline OpenAPI JSON/YAML artifact (committed).  
2. Phase 2+: update OpenAPI **before or alongside** code; regenerate expected artifact in the same PR.  
3. CI job: boot app (or import `create_app().openapi()`), diff against committed contract for:
   - path existence (no removals)
   - required response properties still present
   - status codes still documented
   - deprecated flags only additive
4. Fail CI on silent drift (path deleted, required property removed, status code changed).

### 13.4 Mandatory cases per standardized list endpoint

1. Default `limit`/`offset` behavior (and `skip` alias where applicable)  
2. Existing named collection keys still present and correct  
3. Additive `items`/`pagination` only if introduced — assert equality with named key  
4. Invalid `limit`/`offset` → 422 envelope (where validation already applies)  
5. Filter/sort allowlist behavior where introduced  
6. Authz errors use Error Contract  
7. OpenAPI documents the route accurately  

### 13.5 Search / ranking endpoints

Assert **field-stable ordering** for identical inputs before vs after Sprint 24. Any ordering change is a **release blocker**. Confirm **no `sort`** query on DealScore / Recommendation / Marketplace search / Shopping Assistant organic endpoints.

### 13.6 Integration Test Coverage Matrix

Required API coverage by domain. “R” = required for Sprint 24 Done. “N/A” = not applicable to that surface.

| Domain | Representative route group | Auth | Success path | Validation / error | Authz / ownership | Pagination / filter / sort | OpenAPI contract | Backward compatibility |
|--------|----------------------------|------|--------------|--------------------|-------------------|----------------------------|------------------|------------------------|
| **Authentication** | `POST /api/v1/auth/register\|login\|logout`, `GET /auth/me` | Public + session | R: login/register/me | R: 401/422 envelope | R: logout/me session | N/A | R | R: token/session fields unchanged |
| **Users and sessions** | `/api/v1/profile`, `/api/v1/user/*`, session via auth | Authenticated | R: profile get/update; saved items | R: 401/404/422 | R: user cannot access another user’s resources | R where lists exist (additive only) | R | R: existing profile/user fields |
| **Marketplace** | `GET /api/v1/marketplace/search`, `/api/v1/marketplaces/*` | Mixed (search often public; data ops as today) | R: search + one offers/list path | R: 422 on bad params | R where auth exists today | Search: **no sort**; lists: additive page/filter only | R | R: `{query,results}` and offer shapes |
| **Price history** | `/api/v1/price-history/*` | As today | R: product history + range | R: 404/422 | As today | R: `start`/`end` preserved; additive page/sort if eligible | R | R: snapshot/history fields |
| **Collections** | `/api/v1/collections/*`, `/api/v1/collection-operations/*` | As today | R: list runs/jobs + one action | R: 404/422 | As today | R: limit/offset additive | R | R: run/job payloads |
| **Watchlists** | `/api/v1/watchlists/*` | Authenticated / ownership | R: CRUD + items list | R: 401/403/404/422 | R: ownership isolation | R: named keys kept; additive page/filter/sort if eligible | R | R: `watchlists` key & fields |
| **Reviews** | `/api/v1/reviews/*`, `/api/v1/review-summary/*` | As today | R: get/history or summary | R: 404/422 | As today | R: limit preserved; additive offset if safe | R | R: review payloads |
| **Shopping Assistant** | `/api/v1/shopping-assistant/*` | As today | R: meta + query | R: 422 | As today | **No organic ranking sort** | R | R: response ordering stable |
| **Community** | `/api/v1/community/*` | As today | R: meta + product/topics path | R: 404/422 | As today | As applicable; no ranking hijack | R | R: community payloads |
| **Knowledge Graph** | `/api/v1/graph/*` | As today | R: meta + product/node path | R: 422 on clamp violations | As today | Traversal params preserved | R | R: graph payloads/limits |
| **Personal AI** | `/api/v1/personal/*` | As today | R: meta + recommendation/deals | R: 404/422 | As today | limit preserved; **no ranking ownership change** | R | R: personal payloads |
| **Alerts** | Sprint 19 `/alerts/rules\|evaluate\|events` + Sprint 10 `/alerts` | Authenticated | R: rules CRUD + events; legacy list still works | R: 401/404/422 | R: user-scoped rules/events | R: events pagination additive | R: mark legacy deprecated | R: **legacy paths remain** |
| **Affiliate** | `/api/v1/affiliate/*` | As today | R: link + one report/merchant path | R: 404/422 | As today | Operational list sort only; **no organic influence** | R | R: affiliate payloads; neutrality |
| **Merchant** | `/api/v1/merchants/*`, `/api/v1/admin/*` | Merchant/admin auth | R: org list + one admin action | R: 401/403/404/422 | R: cross-merchant denied | R: `items` preserved; additive page/sort | R | R: merchant payloads; neutrality |
| **Launch / readiness** | `/live`, `/ready`, `/health`, `/api/v1/launch/*` | Probes public; launch as today | R: ready/health + launch meta/dashboard | R: 503 paths as today | Launch authz as today | N/A for probes | R | R: probe JSON; launch fields |
| **Persistence-backed API behavior** | Auth/users, alerts, notifications, affiliate, merchant (Sprint 23 stores) | As today | R: create→read survives app restart in test harness where Sprint 23 covers | R: conflict/not_found envelopes | R: ownership after persist | As applicable | R: same schemas memory vs SQL | R: identical field values for same inputs |

**Matrix notes:**

- Every “R” cell must have at least one automated test or an explicit Phase 7 checklist item with owner.
- Backward-compatibility coverage means asserting **pre-Sprint-24 field names and status codes** still succeed.
- Persistence-backed row does not redesign Sprint 23; it proves HTTP contracts still hold on durable adapters.

### 13.7 Definition of “integration” for Sprint 24

HTTP-level tests through `TestClient`/`httpx` ASGI against `create_app()` with DI overrides are sufficient. Full multi-service docker compose is **not** required unless already used. Frontend compatibility may be proven by: existing frontend test suite, recorded response fixtures the frontend depends on, or a documented smoke checklist against running UI — **whichever already exists in-repo; do not invent a new frontend app**.

---

## 14. Definition of Done

Sprint 24 is done when **all** are true:

1. **Architecture docs published:** this contract + API standards doc linked from README/ops docs.
2. **Shared schemas exist** (as needed): pagination helpers, filter/sort param models used only where eligibility allows.
3. **Error contract documented** in OpenAPI and asserted in contract tests for representative 401/403/404/409/422/429/500.
4. **Pagination/filter/sort** applied **additively** only where non-breaking; dual-run for `skip` and named list keys; **no path removals**.
5. **OpenAPI is the implementation contract:** accurate for requests, responses, errors, pagination, filtering, sorting, authentication, deprecated routes; updated before or alongside code.
6. **OpenAPI drift CI** (or equivalent contract test) fails on silent schema regressions.
7. **No `/api/v2`.**
8. **Coverage matrix (§13.6)** complete for all R cells.
9. **Versioning/deprecation policy** documented; Sprint 10 legacy alerts marked deprecated **but still available**.
10. **Integration/contract tests green** in CI; **existing Sprint 1–23 API tests green** without removing old-field assertions.
11. **No domain/persistence/ranking diffs** beyond optional passthrough of additive query params on eligible endpoints.
12. **Migration notes** published (additive only; clients need not change).
13. **Architecture Lock respected.**
14. **Compatibility gate (non-negotiable):**  
    **Sprint 24 passes only if the existing frontend and current API test suite work without mandatory client changes.**

---

## 15. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Frontend rejects unknown JSON fields | Dual-run `items`/`pagination` breaks clients | Phase 0 verify tolerance; if strict, skip response dual-keys — docs/query aliases only |
| Dual-key payload size | Minor bandwidth | Accept if used; optional |
| `total` count expensive | Latency | Omit only if documented; prefer indexed COUNT |
| Accidental ranking change via sort | Neutrality violation | §0.5 / §11.3 bans; fixture order tests |
| OpenAPI updated after code | Drift / wrong contract | Phase order: OpenAPI in Phase 2 before Tier-1 code |
| OpenAPI snapshot churn | CI noise | Baseline in Phase 0; review diffs deliberately |
| Treating success envelope as mandatory | Client break | Forbidden (§0.4, §7.1) |
| Scope creep into features | Schedule slip | Non-goals |
| Incomplete inventory | Missed routes | Phase 0 freeze |
| Compatibility gate fails late | Rework | Run subset of gate after each Tier phase |

---

## 16. Migration Plan

### 16.1 Compatibility modes

| Mode | Behavior |
|------|----------|
| **Additive** | New optional fields (`items`, `pagination`), new optional query params |
| **Alias** | `skip` ↔ `offset`; keep both |
| **Dual-key** | Named list key **plus** optional `items` (named key remains primary for existing clients) |
| **Deprecate-in-place** | OpenAPI `deprecated: true`; path **remains available** |
| **Remove** | **Forbidden** in Sprint 24 |
| **`/api/v2`** | **Forbidden** in Sprint 24 |

### 16.2 Client guidance (to publish)

1. **No mandatory changes** for Sprint 24.
2. Existing named keys and fields continue to work.
3. Optional: new clients may read `items` + `pagination` where present.
4. Optional: prefer `offset` but `skip` still works on products.
5. Continue handling Error Contract `error` + `message` (+ `detail`).

### 16.3 Server sequencing

Follow §17 Phases 0–7 strictly. OpenAPI before or alongside endpoint code. Compatibility gate last.

### 16.4 Rollback

Additive-only → rollback = revert deploy. No data migration. No persistence schema changes in Sprint 24.

---

## 17. Implementation Phases

### Phase 0 — Freeze baseline and inventory routes

- Export OpenAPI; commit baseline artifact for drift detection  
- Inventory every route: Compliant / Needs standardization / Deprecated  
- Verify frontend (or client fixture) JSON tolerance for unknown fields  
- Record current status codes and named collection keys  
- **No production behavior changes**

### Phase 1 — Define shared API primitives

- Design `PaginationParams`, `PaginationMeta`, sort parser, filter param patterns  
- Document primitives in this contract / `docs/API_STANDARDS.md`  
- Skeleton contract test package (may be empty failing placeholders only if needed — prefer docs-first until Phase 6)  
- **Still no breaking endpoint changes**

### Phase 2 — Update OpenAPI contracts

- Expand `OPENAPI_TAGS`, error components, auth schemes, pagination/filter/sort parameters  
- Mark Sprint 10 legacy alerts and `skip` as deprecated **without removal**  
- Describe additive fields as optional  
- Regenerate/update committed OpenAPI baseline in the same change set as schema declarations  
- **OpenAPI must lead or land with code — never lag**

### Phase 3 — Implement additive compatibility changes

- Wire shared query aliases (`offset` alongside `skip`)  
- Ensure error envelope consistency without changing status codes  
- Dual-run response fields only where Phase 0 confirmed safe  
- Keep all existing paths and required response properties  

### Phase 4 — Standardize Tier-1 collection APIs

- Notifications, products, watchlists lists, alert events, legacy alerts list  
- Additive pagination/filter/sort per eligibility  
- Named keys remain  
- Existing unit API tests must remain green  

### Phase 5 — Standardize remaining eligible APIs

- Merchant, affiliate, marketplace-data, collections, collection-ops, reviews, user lists  
- Kind S search / AI surfaces: OpenAPI + docs only for ranking endpoints; **no sort / no order changes**  
- Persistence-backed domains: confirm HTTP parity on SQL adapters  

### Phase 6 — Add integration and contract tests

- Implement §13.6 coverage matrix R cells  
- OpenAPI drift CI gate  
- Neutrality / ordering fixtures for DealScore, Recommendation, Marketplace search, Shopping Assistant  
- Persistence-backed API behavior tests as specified  

### Phase 7 — Run full regression and compatibility gate

- Full current API test suite (unit + integration) green  
- Contract / OpenAPI drift tests green  
- **Compatibility gate:** existing frontend and current API test suite work **without mandatory client changes**  
- Architecture Lock checklist sign-off  
- Sprint 24 Done only if §14 item 14 passes  

---

## 18. OpenAPI Completeness Requirements

OpenAPI is the **implementation contract** (§0.2).

Every public route must have:

1. Tag belonging to the ownership domain  
2. `summary` and (where non-obvious) `description`  
3. `response_model` / documented success schema (except 204)  
4. Documented error responses (401/403/404/422/429 as applicable + 500)  
5. Query/path/body schemas with constraints (pagination, filtering, sorting where applicable)  
6. Authentication / security scheme documentation  
7. Examples for Tier-1 routes  
8. `deprecated: true` where applicable (**path still present**)  

Custom OpenAPI in `app/main.py` should continue to advertise:

- Error envelope description  
- Hard ranking / affiliate / merchant neutrality notes  
- Explicit statement: no `/api/v2` in Sprint 24  
- Link to this Architecture Contract and API Standards  

**Drift:** CI must detect OpenAPI drift (§13.3). Implementation that disagrees with OpenAPI is a defect.

---

## 19. API Documentation Improvements

| Deliverable | Purpose |
|-------------|---------|
| `docs/architecture/SPRINT_24_API_STABILITY.md` | This contract (source of truth for Sprint 24) |
| `docs/API_STANDARDS.md` | Implementer-facing short standard (Phase 1) |
| OpenAPI `/docs` + `/redoc` | Runtime implementation contract |
| Committed OpenAPI baseline artifact | Drift detection |
| Per-domain doc patches | Dual-run fields; deprecated-but-available legacy alerts |
| Client note | **No mandatory changes**; optional additive fields |

Documentation must not claim removals or `/api/v2` that did not / must not happen.

---

## 20. Explicit Invariants Carried Forward

Sprint 24 implementation **must preserve**:

1. Sprint 5 sole DealScore ownership  
2. Sprint 6 sole organic recommendation decisions  
3. Affiliate metadata post-selection only; no commission-driven ordering  
4. Merchant data cannot alter organic visibility / DealScore / recommendations / historical prices  
5. Sponsored content separate and labeled  
6. Sprint 19 canonical alert engine; Sprint 10 legacy paths retained and available  
7. AI downstream of identity / DealScore / recommendation  
8. Repositories without domain decision logic  
9. Sprint 23 persistence behavior for identical inputs  
10. Existing APIs compatible; no mandatory frontend changes  
11. Direct resource success bodies (no global `{data, meta}` wrapper)  
12. Sorting never overrides DealScore, Recommendation, Shopping Assistant organic ranking, affiliate neutrality, or merchant neutrality  

---

## 21. Success Criteria (planning)

This Architecture Contract succeeds if an implementation agent can:

1. Know exactly which layers they may touch (API schemas, mappers, routers, OpenAPI, docs, contract tests).  
2. Know OpenAPI is updated before or alongside code and enforced by drift CI.  
3. Know the target JSON for resources, collections, errors, pagination, filters, and sort — and when dual-run is required.  
4. Apply additive changes only; never remove paths or require client changes.  
5. Execute Phases 0–7 in order and pass the compatibility gate.  
6. Avoid domain, ranking, and persistence redesign.  
7. Mark Done only when §14 checklist passes — especially item 14.

**Sprint 24 produces consistency, not features — and never at the cost of client breakage.**

---

## Appendix A — Suggested file touch list (implementation only; do not create in planning)

| Area | Likely paths |
|------|----------------|
| Shared schemas | `app/schemas/api_common.py` |
| Error/OpenAPI | `app/core/errors.py`, `app/main.py` |
| OpenAPI baseline | e.g. `docs/openapi/openapi.v1.baseline.json` (name chosen in Phase 0) |
| Endpoints | `app/api/v1/endpoints/*.py` (additive shape only) |
| Mappers | `app/api/v1/mappers/*.py` |
| Docs | `docs/API_STANDARDS.md`, domain doc patches, README links |
| Tests | `tests/unit/api_contract/*`, updates to existing `test_*_api.py` (additive assertions only) |

**Forbidden touch without architecture exception:** domain scoring/recommendation modules, persistence adapters/migrations, affiliate attachment order, merchant organic visibility, frontend mandatory rewrites, `/api/v2`.

## Appendix B — Relationship to Architecture Lock

This document is subordinate to `docs/architecture/ARCHITECTURE_LOCK.md`. If any Sprint 24 tactic conflicts with the Lock or with §0 Non-negotiable constraints, the Lock and §0 win — revise the tactic (usually by choosing additive dual-run or docs-only).

## Appendix C — Change log (documentation)

| Date | Change |
|------|--------|
| 2026-07-30 | Initial Sprint 24 Architecture Contract |
| 2026-07-30 | Added non-negotiable constraints: mandatory backward compatibility, OpenAPI-as-contract + drift plan, coverage matrix, compatibility gate DoD, clarified success/sorting rules, Phases 0–7 resequence |
| 2026-07-30 | Implementation complete: shared primitives, additive pagination/sort, OpenAPI drift gate, dual-run collections, compatibility baseline docs |
| 2026-07-30 | Sprint 24.1 acceptance fixes: watchlists opt-in pagination, products sort allowlist docs aligned to runtime (`created_at`, `brand`, `category`), Tier-1 ErrorBody OpenAPI docs, coverage matrix behavioral tests |

## Appendix D — Implementation notes (Sprint 24 delivered)

### Compatibility proxy (no in-repo frontend)

See `docs/architecture/SPRINT_24_COMPATIBILITY_BASELINE.md`. Gate proven via:
API regression suite + `openapi_sprint23.json` freeze + `openapi.baseline.json` drift gate +
`tests/unit/api_contract/*` + representative fixtures.

### Dual-run collections introduced

`notifications`, `watchlists`, `alerts` (legacy), `events`, collection `runs` (v1 + ops),
merchant audit `items`+`pagination`.

### Bare lists retained

`GET /products`, `/user/saved-products`, `/user/history`, `/user/comparisons`, `/user/searches`.

### Deferred / known limitations

1. **`offset` on `GET /reviews/history/{product_id}`** — deferred. The reviews endpoint
   file is SHA-locked by architecture-protected digests; changing it fails Sprint 11–22
   lock tests. Documented only; `limit` preserved.
2. **User bare-list endpoints** — not wrapped; optional `offset`/`limit` not yet added
   (would remain bare lists if added later).
3. **`total` on some pages** — may be omitted when a cheap COUNT is unavailable;
   `has_more` preferred via limit+1 fetch.
4. **Removal of named keys / `skip` / legacy `/alerts`** — out of Sprint 24.
5. **Product presentation sort** — when `sort` is supplied, sorts a bounded in-memory
   window (≤10k) before paging; default (no `sort`) keeps repository order unchanged.
