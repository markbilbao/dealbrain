# Knowledge Graph Evidence & Path Confidence

**Status:** Sprint 15

## Path confidence: minimum edge confidence

`path_confidence()` in `app/intelligence/knowledge_graph/confidence.py`:

```python
def path_confidence(edges: list[KnowledgeEdge] | tuple[KnowledgeEdge, ...]) -> float:
    """Return the minimum edge confidence along the path (0.0 if empty)."""
    if not edges:
        return 0.0
    return round(min(edge.confidence for edge in edges), 4)
```

A path's confidence is the **minimum** confidence of any edge along it — a claim is only as strong as its weakest link. This is intentionally conservative:

- Avoids false precision from multiplying many high-confidence edges together
- Never lets weak evidence become "stronger" simply by chaining it with strong evidence
- Is trivially explainable: "confidence is 0.72 because the `HAS_AI_SUMMARY` edge is 0.72"

## Confidence bands

```python
def confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.80:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"
```

| Band | Range |
|------|-------|
| `high` | `score >= 0.80` |
| `medium` | `0.50 <= score < 0.80` |
| `low` | `score < 0.50` |

`GraphPath`, `GraphExplanation`, and evidence/contradiction payloads all report both the numeric `confidence` and its `confidence_band` so UIs never need to re-derive bucket boundaries.

## Path finding

`KnowledgeGraphEngine.find_paths(from_node_id, to_node_id, ...)`:

- BFS over both outgoing and incoming edges (the graph is traversed as undirected for path discovery)
- Cycle-safe: each queued path tracks its own `visited` node set, so a path never revisits a node
- Bounded by `max_depth` (edge count) and `max_paths` (results returned)
- Optionally filtered by `edge_types` and `min_confidence`
- Results are sorted by `(-confidence, edge_count, edge_ids)` — highest confidence first, then shortest, then a stable tiebreak
- `shortest_evidence_path()` is a convenience wrapper that returns the single best path (`max_paths=1`)

`GraphPath.evidence_ids` is the deduplicated union of every edge's `evidence_ids` along the path.

## Explanations

`KnowledgeGraphEngine.explain_connection(from_node_id, to_node_id, claim=...)` returns a `GraphExplanation`:

- `supported = bool(paths)` — no path means the claim is not supported (never fabricated)
- `confidence` / `confidence_band` come from the single best path (`paths[0]`)
- `contradictions` — any `CONTRADICTS` edges touching either endpoint
- `limitations` — always includes: relationships are only as reliable as their source evidence; traversal does not prove causation; most data is fixture/mock/imported

## Evidence collection

`GraphEvidenceService.evidence_for(node_id)` (in `evidence.py`) gathers:

- **Evidence edges**: `HAS_EVIDENCE`, `SUPPORTED_BY`, `HAS_REVIEW`, `HAS_COMMUNITY_EVIDENCE`, `DISCUSSED_IN` touching the node
- **Evidence nodes**: the other endpoint of each evidence edge, plus any node referenced via `evidence_ids`
- **Stale flags**: `GraphEvidenceService.is_stale(node, max_age_days=180)` — a node is stale if its metadata explicitly sets `stale: true`, or if `updated_at`/`created_at` is older than 180 days
- **Warnings**: produced by `EvidenceValidationService.validate_evidence_refs`

## AI summary cannot be its own evidence

`EvidenceValidationService.validate_evidence_refs()` enforces:

- An `ai_summary` node can never appear as evidence *for itself* (`KnowledgeGraphValidationError` raised if `evidence.node_id == subject.node_id` and both are AI summaries)
- More generally, a node is never allowed to cite itself as evidence when it is an AI summary
- Any `ai_summary` node appearing as evidence for *another* node produces a warning: "AI summary is interpretive and must not replace underlying evidence."

To keep AI summaries evidence-grounded, `KnowledgeGraphAggregator.seed_from_fixtures()` always creates a separate underlying `evidence` node and links the summary to it via `SUPPORTED_BY`, rather than letting the summary reference itself:

```python
summary = engine.create_node(node_type=NodeType.AI_SUMMARY, ...)
backing = engine.create_node(node_type=NodeType.EVIDENCE, ...)
engine.create_edge(edge_type=EdgeType.SUPPORTED_BY, from_node_id=summary.node_id, to_node_id=backing.node_id, ...)
```

## Contradictions

`ContradictionService.contradictions_for(node_id)` (in `evidence.py`) returns every `CONTRADICTS` edge touching the node, with `confidence_band`, the other endpoint's label, and evidence IDs. The fixture graph seeds one demo contradiction: community evidence claiming "battery lasts a full workday" vs. a review claiming "battery drains under gaming load" for the same product/topic.

## Limitations (always surfaced)

- Fixture/mock/imported data only — no live scraping
- Traversal ≠ causation
- Similar/alternative/recommended relationships are not purchase guarantees
- A path's confidence reflects its weakest edge, not an aggregate probability
