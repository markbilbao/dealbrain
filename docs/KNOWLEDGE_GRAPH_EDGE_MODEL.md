# Knowledge Graph Edge Model

**Status:** Sprint 15

## `KnowledgeEdge`

Frozen dataclass defined in `app/domain/entities/knowledge_graph.py`:

| Field | Type | Notes |
|-------|------|-------|
| `edge_id` | `str` | Deterministic, derived from `edge_type` + endpoints |
| `edge_type` | `EdgeType` | One of the enum values below |
| `from_node_id` / `to_node_id` | `str` | Both endpoints must already exist |
| `confidence` | `float` | `0.0`–`1.0` |
| `source` | `str` | Defaults to `"knowledge_graph"` |
| `evidence_ids` | `tuple[str, ...]` | References to supporting evidence node IDs |
| `created_at` / `updated_at` | `datetime \| None` | UTC timestamps |
| `metadata` | `Mapping[str, Any]` | Sanitized, read-only extra attributes |

`deterministic_edge_id(edge_type, from_id, to_id)` returns `kg:edge:{sha256(type|from|to)[:16]}`.

## Edge types (`EdgeType`, `StrEnum`)

| Value | Meaning | Allowed from → to |
|-------|---------|--------------------|
| `SOLD_BY` | Product sold by a seller | `product` → `seller` |
| `OFFERED_ON` | Product offered on a marketplace | `product` → `marketplace` |
| `HAS_PRICE` | Product has a price observation | `product` → `price_observation` |
| `HAS_PRICE_HISTORY` | Product has price history | `product` → `price_history` |
| `HAS_REVIEW` | Product has a review | `product` → `review` |
| `DISCUSSED_IN` | Product discussed in community/topic | `product` → `community_evidence`, `topic` |
| `HAS_COMMUNITY_EVIDENCE` | Product has community evidence | `product` → `community_evidence` |
| `HAS_AI_SUMMARY` | Product has an AI summary | `product` → `ai_summary` (weight 0.85) |
| `MADE_BY` | Product made by a brand | `product` → `brand` |
| `BELONGS_TO_CATEGORY` | Product belongs to a category | `product` → `category` |
| `HAS_TOPIC` | Entity has a discussion/review topic | `product`, `review`, `community_evidence` → `topic` |
| `SIMILAR_TO` | Products are similar (**symmetric**) | `product` → `product` (weight 0.9) |
| `COMPARES_WITH` | Products are compared (**symmetric**) | `product` → `product` (weight 0.9) |
| `ACCESSORY_OF` | Accessory belongs to a product | `accessory`, `product` → `product` |
| `RECOMMENDED_WITH` | Product recommended with another | `product` → `product` (weight 0.85) |
| `COMPATIBLE_WITH` | Entities are compatible (**symmetric**) | `product`, `accessory`, `compatibility` → same set (weight 0.9) |
| `HAS_WARNING` | Entity has a warning evidence node | `product`, `seller` → `evidence` (weight 0.95) |
| `HAS_EVIDENCE` | Entity backed by evidence | any node type → `evidence`, `community_evidence`, `review` |
| `SUPPORTED_BY` | Claim/summary supported by evidence | `ai_summary`, `topic`, `evidence` → `evidence`, `community_evidence`, `review`, `price_observation` (weight 0.95) |
| `CONTRADICTS` | Evidence contradicts another claim | `evidence`, `community_evidence`, `review`, `ai_summary` → same set + `topic` (weight 0.9) |
| `ALTERNATIVE_TO` | Product is an alternative to another (**symmetric**) | `product` → `product` (weight 0.9) |

Endpoint constraints live in `RelationshipRegistry` (`registry.py`) as `EdgeTypeSpec(allowed_from=..., allowed_to=...)`. `create_edge()` raises `KnowledgeGraphValidationError` if either endpoint's node type is not in the allowed set, or if the edge type string does not resolve to a registered `EdgeType`.

## Symmetric edges

`SYMMETRIC_EDGE_TYPES = {SIMILAR_TO, COMPARES_WITH, COMPATIBLE_WITH, ALTERNATIVE_TO}`. For these types, `EdgeDeduplicationService` treats `A→B` and `B→A` as the same relationship — creating the reverse edge merges into the existing one rather than creating a duplicate.

## Validation rules (`KnowledgeGraphValidator.validate_edge`)

An edge is rejected if:

- `edge_id`, `from_node_id`, `to_node_id`, or `source` is blank
- `from_node_id == to_node_id` (self-loops are not allowed)
- `edge_type` is not a registered `EdgeType`
- `confidence` is not a number in `[0.0, 1.0]`
- endpoint node types violate the registry's `allowed_from`/`allowed_to` constraints

`InMemoryKnowledgeGraphRepository.add_edge()`/`update_edge()` additionally require both endpoint nodes to already exist in the repository — referential integrity is enforced at the repository layer, not just the engine.

## Deduplication and idempotent ingestion

`EdgeDeduplicationService.upsert()` (in `deduplication.py`):

1. Looks for an existing outgoing edge from `from_node_id` with the same `edge_type` and `to_node_id`.
2. If the edge type is symmetric (or registry-marked symmetric), also checks the reverse direction.
3. Falls back to an exact `edge_id` match.
4. If found, merges: keeps the original `edge_id`, takes the max confidence, unions `evidence_ids` (order-preserving, deduplicated), merges metadata, and bumps `updated_at`. Returns `created=False`.
5. Otherwise inserts a new edge (`created=True`).

Re-running `KnowledgeGraphAggregator.seed_from_fixtures()` or re-creating the same logical edge (e.g. `MADE_BY` for the same product+brand) never creates duplicate edges.

## Cascading node removal

`KnowledgeGraphRepository.remove_node()` removes all incident edges (both outgoing and incoming) before removing the node itself, preventing dangling edge references.
