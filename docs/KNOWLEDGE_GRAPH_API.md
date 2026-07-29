# Knowledge Graph API

**Status:** Sprint 15
**Base path:** `/api/v1/graph`

All endpoints are read-only GETs backed by `KnowledgeGraphService` (`app/services/knowledge_graph_service.py`) via `app/api/v1/endpoints/graph.py`. The graph is seeded lazily from fixtures on first request (`ensure_seeded()`).

## Error mapping

| Domain exception | HTTP status |
|---|---|
| `KnowledgeGraphValidationError` | 400 |
| `KnowledgeGraphNotFoundError` | 404 |
| Any other exception | 500 (generic message, no internals leaked) |

## Endpoints

### `GET /demo`

Returns the demo product's subgraph (`GraphSubgraphResponse`). Demo product: `sa-laptop-tuf-a15` (ASUS TUF Gaming A15).

### `GET /meta`

Returns `GraphMetaResponse`: `enabled`, `demo_product_id`, `demo_product_name`, `data_status`, `external_graph_database` (always `false`), `limits`, `node_types`, `edge_types`, `confidence_method` (`"minimum_edge_confidence"`).

### `GET /product/{product_id}`

Product-centered subgraph (`GraphSubgraphResponse`) with summary (brands, categories, sellers, marketplaces, reviews, community evidence, similar products, warnings), contradictions, and evidence paths.

Query params: `max_depth` (1–10), `max_nodes` (1–1000), `max_edges` (1–2000) — all optional, clamped to server ceilings.

`product_id` may be the source product ID (e.g. `sa-laptop-tuf-a15`), the deterministic node ID, or a case-insensitive label match. Unknown product IDs return 404.

### `GET /node/{node_id}`

Fetch a single node (`KnowledgeNodePayload`). 404 if missing.

### `GET /node/{node_id}/neighbors`

Direct neighbors of a node (`GraphSubgraphResponse`).

Query params:
- `direction` — `"outgoing"`, `"incoming"`, or `"both"` (default)
- `edge_types` — comma-separated `EdgeType` values
- `minimum_confidence` — `0.0`–`1.0`
- `max_nodes` — 1–1000

### `GET /node/{node_id}/relationships`

All outgoing and incoming edges for a node (`GraphRelationshipsResponse`), unfiltered and unbounded by traversal limits (only capped by however many edges the node actually has).

### `GET /path`

Find evidence paths between two nodes (`GraphPathResponse`).

Query params: `from_node_id`, `to_node_id` (required); `max_depth` (1–10), `edge_types` (comma-separated), `minimum_confidence` (0.0–1.0).

Response includes `paths` (each with `node_ids`, `edge_ids`, `confidence`, `confidence_band`, `evidence_ids`), `truncated`, and `limits`.

### `GET /evidence/{node_id}`

Evidence linked to a node (`GraphEvidenceResponse`): `evidence_nodes`, `evidence_edges`, `stale` (evidence flagged stale), `contradictions`, `warnings` (e.g. AI-summary-is-interpretive notices). 404 if the node doesn't exist.

### `GET /explain`

Evidence-grounded explanation of a connection (`GraphExplanationResponse`).

Query params: either (`from_node_id` + `to_node_id`) or (`from_product_id` + `to_product_id`); optional `claim` (free text label only, not evaluated), `max_depth`.

Response: `claim`, `supported`, `confidence`, `confidence_band`, `paths`, `contradictions`, `limitations`.

## Server-enforced limits (`GraphLimits`)

Configured via environment variables (`app/core/config.py`), applied in `KnowledgeGraphEngine.effective_limits()`:

| Setting | Env var | Default |
|---|---|---|
| `max_depth` | `KNOWLEDGE_GRAPH_MAX_DEPTH` | `3` |
| `max_nodes` | `KNOWLEDGE_GRAPH_MAX_NODES` | `100` |
| `max_edges` | `KNOWLEDGE_GRAPH_MAX_EDGES` | `200` |
| `max_paths` | `KNOWLEDGE_GRAPH_MAX_PATHS` | `20` |
| `min_confidence` | `KNOWLEDGE_GRAPH_MIN_CONFIDENCE` | `0.0` |

Client-supplied values are always clamped **down** to these ceilings (`min(requested, server_ceiling)` for max\*, `max(requested, server_floor)` for `min_confidence`) — a client can never widen limits beyond what the server allows. When a traversal or neighbor listing is truncated, the response sets `truncated: true` and appends a warning string; it never silently drops data without saying so.

## Feature flag

| Env var | Default | Meaning |
|---|---|---|
| `KNOWLEDGE_GRAPH_ENABLED` | `true` | When `false`, `KnowledgeGraphService` raises `KnowledgeGraphValidationError` ("Knowledge Graph is disabled.") from every read/write method, and the Shopping Assistant DI wiring passes `knowledge_graph_service=None`. |
| `KNOWLEDGE_GRAPH_SNAPSHOT_SCHEMA_VERSION` | `1` | Snapshot schema compatibility gate (see `KNOWLEDGE_GRAPH_SNAPSHOTS.md`) |

## Security

- No external graph database, no client-supplied query language (only structured, whitelisted query kinds via `GraphQueryService`)
- Metadata is sanitized on every node/edge (`sanitize_metadata`) — API responses never contain API keys, secrets, tokens, or prompts
- `demo_product_id`/`demo_product_name` and all `data_status` fields are `"mock"` unless a snapshot explicitly imports `"imported"`/`"live"` data
