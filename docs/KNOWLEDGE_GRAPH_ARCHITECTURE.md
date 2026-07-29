# Knowledge Graph Architecture v1

**Status:** Sprint 15
**Date:** 2026-07-29
**Scope:** Provider-neutral, in-memory knowledge graph connecting products, sellers, reviews, community evidence, prices, and more across DealBrain intelligence modules.

## Goal

Give every DealBrain module (Shopping Assistant, Community Intelligence, Reviews, DealScore, Price History) a shared, evidence-first way to relate entities and answer "why is this connected?" without introducing an external graph database or new AI dependency.

## Architecture

```
demo.html (Knowledge Graph panel)
  → API /api/v1/graph/*
  → KnowledgeGraphService (facade)
       ├─ KnowledgeGraphAggregator     (seeds fixture graph from catalog + community)
       ├─ KnowledgeGraphEngine         (create/traverse/find_paths/explain)
       │    ├─ NodeCanonicalizationService  (deterministic keys/ids)
       │    ├─ NodeDeduplicationService / EdgeDeduplicationService
       │    ├─ RelationshipRegistry    (allowed node/edge type pairs)
       │    └─ KnowledgeGraphValidator (metadata sanitization, field checks)
       ├─ ProductKnowledgeGraphService (product-centered subgraph + summary)
       ├─ GraphQueryService            (structured queries: sellers, reviews, similar…)
       ├─ GraphEvidenceService / ContradictionService / EvidencePathService
       └─ InMemoryKnowledgeGraphRepository (nodes, edges, snapshot import/export)
```

No Neo4j, Neptune, or other external graph database is used. The graph lives entirely in process memory behind the `KnowledgeGraphRepository` port, so a persistent backend can be swapped in later without touching the engine, service, or API contracts.

## Design principles

- **In-memory repository pattern.** `InMemoryKnowledgeGraphRepository` implements `KnowledgeGraphRepository` and `GraphSnapshotRepository`. All referential integrity (edges require existing endpoints) is enforced here.
- **Deterministic, not AI-generated.** Canonicalization, deduplication, and traversal are pure functions/algorithms. No LLM calls exist anywhere in this module.
- **Bounded traversal.** Every read operation (`neighbors`, `traverse`, `find_paths`) is clamped to server-side `GraphLimits` (see `KNOWLEDGE_GRAPH_API.md`). Clients can request smaller limits but never larger ones.
- **Evidence-first.** Edges carry `evidence_ids`; paths compute confidence from evidence quality (see `KNOWLEDGE_GRAPH_EVIDENCE_PATHS.md`). Claims without a supporting path are marked unsupported, not fabricated.
- **Fixture/mock by default.** `app/intelligence/knowledge_graph/fixtures.py` builds records from the same Shopping Assistant catalog and community fixtures used elsewhere, so all three modules describe a consistent demo product (`sa-laptop-tuf-a15` — ASUS TUF Gaming A15).
- **Optional collaborator.** `ShoppingAssistantService` accepts an optional `knowledge_graph_service` collaborator; when absent, it degrades gracefully (see `KNOWLEDGE_GRAPH_EXTENSION_GUIDE.md`).

## Module layout

| Path | Responsibility |
|------|-----------------|
| `app/domain/entities/knowledge_graph.py` | Frozen dataclasses/enums: `KnowledgeNode`, `KnowledgeEdge`, `GraphPath`, `GraphLimits`, `GraphSubgraph`, `GraphExplanation`, `GraphSnapshot`, `NodeType`, `EdgeType` |
| `app/domain/interfaces/knowledge_graph_repository.py` | Abstract repository ports (`KnowledgeNodeRepository`, `KnowledgeEdgeRepository`, `KnowledgeGraphRepository`, `GraphSnapshotRepository`) |
| `app/intelligence/knowledge_graph/memory.py` | In-memory repository implementation |
| `app/intelligence/knowledge_graph/engine.py` | Node/edge creation, neighbors, bounded BFS traversal, path finding, explanation |
| `app/intelligence/knowledge_graph/canonicalization.py` | Deterministic canonical keys and IDs (no AI) |
| `app/intelligence/knowledge_graph/deduplication.py` | Idempotent node/edge upserts, `IdentityResolutionService` |
| `app/intelligence/knowledge_graph/registry.py` | `RelationshipRegistry`: allowed node types per edge type, symmetry, weights |
| `app/intelligence/knowledge_graph/validator.py` | Metadata sanitization (secret stripping, size limits), entity validation |
| `app/intelligence/knowledge_graph/confidence.py` | Path confidence (minimum edge confidence) and confidence bands |
| `app/intelligence/knowledge_graph/evidence.py` | `EvidenceValidationService`, `GraphEvidenceService`, `EvidencePathService`, `ContradictionService` |
| `app/intelligence/knowledge_graph/aggregator.py` | Builds the fixture graph from catalog + community data |
| `app/intelligence/knowledge_graph/fixtures.py` | Mock/imported product, similarity, contradiction, and community-evidence records |
| `app/intelligence/knowledge_graph/product_graph.py` | Product-centered subgraph + summary projection |
| `app/intelligence/knowledge_graph/query.py` | Structured (non-free-form) queries: sellers, reviews, similar products, topic evidence, paths |
| `app/intelligence/knowledge_graph/adapters/__init__.py` | Read-only adapters projecting catalog/community data into graph records |
| `app/services/knowledge_graph_service.py` | Application facade used by API endpoints and other services |
| `app/api/v1/endpoints/graph.py` | FastAPI routes under `/api/v1/graph` |
| `app/api/v1/mappers/knowledge_graph.py` | Domain → Pydantic schema mapping |
| `app/schemas/knowledge_graph.py` | Response schemas |

## Data flow (fixture seeding)

1. `KnowledgeGraphService.ensure_seeded()` is called lazily on first use.
2. If the repository has no nodes, `KnowledgeGraphAggregator.seed_from_fixtures()` runs.
3. The aggregator reads `build_fixture_records()` (products, similarity pairs, contradictions, community evidence) and creates nodes/edges via the engine, which canonicalizes, deduplicates, and validates every entity.
4. Optional `community_adapter` (a `CommunityEvidenceAdapter` wrapping `CommunityIntelligenceService`) adds live-shaped (but still mock/fixture-backed) community evidence nodes.

## Limitations

- All current data is fixture, mock, or imported — there is no live marketplace scraping.
- Graph traversal reflects **relationships**, not causation; a path existing between two nodes does not prove a causal or purchase-guarantee relationship.
- `SIMILAR_TO` / `ALTERNATIVE_TO` / `RECOMMENDED_WITH` edges express similarity heuristics, not guarantees.
- The graph is process-scoped and in-memory; it resets on process restart unless re-seeded or re-imported from a snapshot.

See also: `KNOWLEDGE_GRAPH_NODE_MODEL.md`, `KNOWLEDGE_GRAPH_EDGE_MODEL.md`, `KNOWLEDGE_GRAPH_EVIDENCE_PATHS.md`, `KNOWLEDGE_GRAPH_API.md`, `KNOWLEDGE_GRAPH_SNAPSHOTS.md`, `KNOWLEDGE_GRAPH_EXTENSION_GUIDE.md`.
