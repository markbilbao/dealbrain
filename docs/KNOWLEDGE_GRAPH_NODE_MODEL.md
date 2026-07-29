# Knowledge Graph Node Model

**Status:** Sprint 15

## `KnowledgeNode`

Frozen dataclass defined in `app/domain/entities/knowledge_graph.py`:

| Field | Type | Notes |
|-------|------|-------|
| `node_id` | `str` | Deterministic, derived from `node_type` + `canonical_key` (see below) |
| `node_type` | `NodeType` | One of the enum values below |
| `canonical_key` | `str` | Stable identity key used for deduplication |
| `source` | `str` | Origin system/module (e.g. `fixture`, `community`, marketplace name) |
| `source_id` | `str` | Identifier within the source system |
| `label` | `str` | Human-readable display label |
| `confidence` | `float` | `0.0`–`1.0`, clamped by `clamp_confidence` |
| `data_status` | `"mock" \| "imported" \| "live"` | Provenance of the underlying data |
| `created_at` / `updated_at` | `datetime \| None` | UTC timestamps |
| `metadata` | `Mapping[str, Any]` | Sanitized, read-only (`MappingProxyType`) extra attributes |

`KnowledgeNode.to_dict()` renders confidence rounded to 4 decimals, ISO timestamps, and a plain `dict` copy of metadata.

## Node types (`NodeType`, `StrEnum`)

| Value | Meaning |
|-------|---------|
| `product` | A DealBrain-tracked product |
| `seller` | A marketplace seller/storefront |
| `review` | A structured product review record |
| `community_evidence` | Normalized community discussion evidence (Reddit, YouTube, etc.) |
| `price_observation` | A single observed price point |
| `price_history` | A reference to a product's price-history series |
| `marketplace` | A marketplace (e.g. Shopee, Lazada) |
| `brand` | A product brand/manufacturer |
| `category` | A product category |
| `topic` | A discussion/review topic (battery, value, performance, …) |
| `evidence` | Generic evidence node (DealScore, warnings, AI-summary backing) |
| `ai_summary` | An AI-generated interpretive summary (never usable as its own evidence) |
| `video` | A video review/reference (reserved for future connectors) |
| `accessory` | An accessory product |
| `compatibility` | A compatibility statement/record |

## Canonicalization

`NodeCanonicalizationService.canonical_key()` (in `canonicalization.py`) builds a stable, type-specific key with no AI involved:

- **Product:** `product:{brand}:{label}` when brand+label are known (this is what lets the same physical product listed on Shopee and Lazada collapse to one node); otherwise falls back to `product:{source}:{source_id}` or `product:{label}`.
- **Seller:** `seller:{marketplace_or_source}:{label_or_source_id}`
- **Marketplace / Brand / Category / Topic:** `{type}:{normalized label or source_id}`
- **Evidence-like types** (`review`, `community_evidence`, `evidence`, `ai_summary`, `price_observation`, `price_history`, `video`, `accessory`, `compatibility`): `{type}:{source}:{source_id or label}`
- **Fallback:** `{type}:{source_id or label}`

All tokens pass through `normalize_token()`: lowercased, whitespace collapsed, non-alphanumeric characters replaced with `-`, and stripped of leading/trailing `-`.

`deterministic_node_id(node_type, canonical_key)` returns `kg:{type}:{sha256(type|key)[:16]}` — the same inputs always yield the same node ID, which is what makes repeated ingestion idempotent.

## Deduplication

`NodeDeduplicationService.upsert()` (in `deduplication.py`):

1. Looks up an existing node by `canonical_key` first, then by `node_id`.
2. If none exists, inserts the new node (`created=True`).
3. If one exists, merges: keeps the original `node_id`/`canonical_key`, takes the *max* of the two confidences, prefers non-empty incoming `source`/`source_id`/`label`, merges metadata (`{**existing, **incoming}`), and bumps `updated_at`. Returns `created=False`.

This means seeding the same fixture data twice (or observing the same product from two marketplaces with the same brand+label) does not create duplicate product nodes — see `KNOWLEDGE_GRAPH_EXTENSION_GUIDE.md` for the shopee+lazada mirror example.

## Validation (`KnowledgeGraphValidator.validate_node`)

A node is rejected (`KnowledgeGraphValidationError`) if:

- `node_id`, `canonical_key`, `source`, `source_id`, or `label` is blank
- `node_type` is not a `NodeType`
- `confidence` is not a number in `[0.0, 1.0]`
- `data_status` is not one of `mock`, `imported`, `live`

## Metadata sanitization

`sanitize_metadata()` (in `validator.py`) is applied to every node's metadata before persistence:

- Strips forbidden keys (`api_key`, `secret`, `password`, `token`, `authorization`, `private_key`, `prompt`, `system_prompt`, `hidden_prompt`, case/dash-insensitive)
- Caps nesting depth at 3 (deeper values become `"[truncated]"`)
- Caps dict size at 40 keys (extra keys replaced by `_truncated: true`)
- Caps lists at 50 items and strings at 2000 characters

This guarantees no credentials or hidden prompts can leak into graph responses.
