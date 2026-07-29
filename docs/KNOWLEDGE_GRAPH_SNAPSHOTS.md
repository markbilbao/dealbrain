# Knowledge Graph Snapshots

**Status:** Sprint 15

Snapshots give a deterministic, serializable view of the entire in-memory graph — useful for tests, demos, and (eventually) migrating to a persistent backend.

## `GraphSnapshot`

Frozen dataclass in `app/domain/entities/knowledge_graph.py`:

| Field | Type |
|---|---|
| `schema_version` | `int` |
| `nodes` | `tuple[KnowledgeNode, ...]` |
| `edges` | `tuple[KnowledgeEdge, ...]` |
| `created_at` | `datetime` |
| `data_status` | `"mock" \| "imported" \| "live"` |
| `source_summary` | `Mapping[str, Any]` — node/edge counts by type |

`schema_version` defaults to `1` (`KNOWLEDGE_GRAPH_SNAPSHOT_SCHEMA_VERSION`, configurable via env var).

## Export

```python
snapshot = repository.export_snapshot(data_status="mock")
# or via the service facade:
snapshot = knowledge_graph_service.export_snapshot()
```

`InMemoryKnowledgeGraphRepository.export_snapshot()`:

- Sorts nodes and edges by ID for deterministic ordering (stable diffs, reproducible test fixtures)
- Falls back to `"mock"` if an invalid `data_status` is passed
- Computes `source_summary` with `node_count`, `edge_count`, `node_types` (counts per `NodeType`), `edge_types` (counts per `EdgeType`)

## Import

```python
imported = repository.import_snapshot(snapshot)          # accepts GraphSnapshot or dict
# or:
imported = knowledge_graph_service.import_snapshot(payload)
```

`import_snapshot()` **replaces** the current graph contents (`self.clear()` is called before re-adding). It validates before mutating anything:

- `schema_version` must exactly match the repository's configured version, else `KnowledgeGraphValidationError: Unknown snapshot schema version`
- `nodes` and `edges` must both be lists
- `data_status` must be one of `mock`, `imported`, `live`
- Each node must be a dict with a non-blank `node_id`; duplicate `node_id`s within the snapshot are rejected
- Each node's `node_type` must resolve to a valid `NodeType` (case-insensitive)
- Each edge must be a dict with a non-blank `edge_id`; duplicate `edge_id`s are rejected
- Each edge's `from_node_id`/`to_node_id` must reference a node present in the *same* snapshot's node list
- Each edge's `edge_type` must resolve to a valid `EdgeType` (case-insensitive, matched against the enum's uppercase values)
- `evidence_ids` (if present) must be a list

Any malformed snapshot raises `KnowledgeGraphValidationError` and the previous graph state is left untouched (validation happens before `clear()`/re-insert). Every parsed node/edge is then re-inserted through `add_node()`/`add_edge()`, so ordinary node/edge validation (blank fields, endpoint constraints, confidence range) applies again on import.

## Round-tripping

`snapshot.to_dict()` produces a plain-JSON-serializable payload (ISO datetime strings, plain lists/dicts) suitable for writing to disk or sending over HTTP. `import_snapshot()` accepts either a `GraphSnapshot` instance or an equivalent `dict` (e.g. loaded from JSON), so:

```python
payload = json.loads(json.dumps(snapshot.to_dict()))
repository.import_snapshot(payload)
```

round-trips losslessly for all fields that matter to graph identity and traversal (node/edge IDs, types, endpoints, confidence, evidence references). Metadata is re-sanitized on import, so any metadata that would have been stripped on creation is stripped again — snapshots cannot be used to smuggle secrets back in.

## Why this matters instead of a real graph database

Because the repository is in-memory, snapshots are the only way to (a) persist graph state across process restarts, (b) seed a specific test scenario without re-running the fixture aggregator, and (c) eventually migrate to a persistent store — a future `GraphSnapshotRepository` implementation backed by a real database only needs to support the same `export_snapshot`/`import_snapshot` contract.
