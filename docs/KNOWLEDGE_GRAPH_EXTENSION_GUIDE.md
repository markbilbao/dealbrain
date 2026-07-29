# Knowledge Graph Extension Guide

**Status:** Sprint 15

This guide covers how to extend the Knowledge Graph without breaking protected prior-sprint modules, plus how other services should integrate with it.

## Adding a new node type

1. Add the value to `NodeType` in `app/domain/entities/knowledge_graph.py`.
2. Add a canonicalization rule in `NodeCanonicalizationService.canonical_key()` (`canonicalization.py`) — pick a stable, type-specific key so repeated ingestion stays idempotent. If you skip this, the generic fallback (`{type}:{source_id or label}`) is used.
3. Update any `EdgeTypeSpec.allowed_from`/`allowed_to` sets in `registry.py` that should permit the new node type as an endpoint.
4. If the type participates in evidence/contradiction logic, extend `GraphEvidenceService`/`ContradictionService` in `evidence.py` as needed.

## Adding a new edge type

1. Add the value to `EdgeType` in `app/domain/entities/knowledge_graph.py`.
2. Register an `EdgeTypeSpec` in `_DEFAULT_SPECS` (`registry.py`): description, `symmetric` flag, `allowed_from`/`allowed_to` node-type sets, and a `weight` (informational; traversal itself uses per-edge `confidence`, not `weight`).
3. If the relationship is logically symmetric (e.g. "similar to"), add it to `SYMMETRIC_EDGE_TYPES` in the entities module too, so deduplication catches reverse duplicates even if a caller constructs a raw `RelationshipRegistry()` without the default specs.
4. No traversal code changes are required — `KnowledgeGraphEngine` and `GraphQueryService` consume edge types generically through the registry.

## Registering a new relationship without modifying core files

`RelationshipRegistry` supports runtime registration:

```python
from app.intelligence.knowledge_graph.registry import RelationshipRegistry, EdgeTypeSpec

registry = RelationshipRegistry()  # copies DEFAULT specs
registry.register(EdgeTypeSpec(edge_type=MyEdgeType.CUSTOM, description="...", allowed_from=..., allowed_to=...))
engine = KnowledgeGraphEngine(repository, registry=registry)
```

This is the preferred approach for experimental or module-local edge types that shouldn't be added to the shared default registry.

## Integrating a new evidence source

Add a **read-only adapter** in `app/intelligence/knowledge_graph/adapters/__init__.py` that returns plain dicts shaped like the aggregator's fixture records (see `CommunityEvidenceAdapter` for the pattern: `evidence_for(product_ids) -> list[dict]`). Pass it to `KnowledgeGraphAggregator(engine, community_adapter=my_adapter)`. Adapters must never mutate the modules they read from.

## Multi-source product merging

When the same physical product appears from two marketplaces (e.g. Shopee and Lazada) with the same brand + label, `NodeCanonicalizationService.canonical_key()` produces the same `product:{brand}:{label}` key for both, so `NodeDeduplicationService.upsert()` merges them into a single canonical product node instead of creating two. This is how `fixtures.py`'s `lazada-tuf-a15-mirror` record collapses onto the same node as `sa-laptop-tuf-a15`.

## Integrating with the Shopping Assistant (optional collaborator pattern)

`ShoppingAssistantService.__init__` accepts an optional `knowledge_graph_service: Any | None = None` collaborator — **it is never a hard dependency**. Integration happens purely through:

```python
def _graph_evidence_for(self, product_ids: list[str]) -> list[ShoppingEvidence]:
    if self._knowledge_graph is None or not product_ids:
        return []
    try:
        graph_items = self._knowledge_graph.shopping_assistant_evidence(product_ids)
    except Exception:
        return []
    ...
```

- If `knowledge_graph_service` is `None`, no graph evidence is added and a `graph_unavailable` warning (`AssistantWarning(code="graph_unavailable")`) is appended to the response.
- If the collaborator raises for any reason, the exception is swallowed and evidence generation degrades to an empty list — the assistant always keeps working using its pre-existing (candidate/community) evidence flow.
- `response.processing["knowledge_graph_integrated"]` reports whether the collaborator was present.

To wire the real service, use `app.core.dependencies.get_knowledge_graph_service` as a FastAPI dependency, which honors `KNOWLEDGE_GRAPH_ENABLED` and passes `None` when the flag is off.

## Protected modules — do not modify in place

Per project convention (see `tests/unit/test_community_protected_modules.py` and `tests/unit/test_knowledge_graph_protected_modules.py`), the following must not be rewritten to add Knowledge Graph coupling:

- `app/intelligence/shopping_assistant/orchestrator.py`, `deterministic.py`, `evidence.py`
- `app/intelligence/community/orchestrator.py`, `collector.py`, `fixtures.py`, `trust.py`, `deterministic.py`
- `app/api/v1/endpoints/community.py`
- `app/domain/entities/community_intelligence.py`, `app/domain/interfaces/community_intelligence_repository.py`
- `app/intelligence/dealscore/engine.py`, `app/intelligence/recommendation/engine.py`

Composition (constructor injection of an optional collaborator) is always the right approach; import-time hard dependencies on `KnowledgeGraphService` from any of the above files should never appear.

## Snapshots for demos/tests

See `KNOWLEDGE_GRAPH_SNAPSHOTS.md` for exporting/importing a deterministic graph state — useful for seeding a specific scenario in a test or demo without going through fixture generation each time.
