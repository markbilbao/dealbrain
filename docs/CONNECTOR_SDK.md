# Community Connector SDK

**Status:** Sprint 14  
**Purpose:** Pluggable, provider-neutral community source adapters

## Port

Implement `CommunityProvider` (`app/domain/interfaces/community_intelligence_repository.py`):

- `source_name`
- `is_enabled()` / `is_available()` / `health_check()`
- `search_product(...)`
- `search_threads(...)`
- `extract_comments(...)`
- `collect(...)` → `list[CommunityEvidence]`

## Transport

Use `CommunityTransport`:

- `DisabledCommunityTransport` — refuse live fetches
- `MockCommunityTransport` — deterministic payloads
- `ScriptedCommunityTransport` — test sequences

Never scrape. Never embed vendor SDKs in application services.

## Base helper

`BaseCommunityProvider` provides fixture/mock wiring, normalization, and validation.

## Register

```python
registry = CommunityRegistry()
registry.register(MyFutureProvider(...))
```

`CommunityCollector` will include the new source automatically.

## Normalization contract

Adapters should preferably return raw dicts and let `EvidenceNormalizer` produce:

```json
{
  "source": "...",
  "product": "...",
  "evidence_id": "...",
  "url": "...",
  "title": "...",
  "body": "...",
  "topic": "...",
  "sentiment": {"label": "...", "score": 0.0},
  "confidence": 0.0,
  "engagement": {},
  "timestamp": "..."
}
```

## Checklist for a new connector

1. Add fixture map (optional) under `app/intelligence/community/fixtures.py`
2. Implement provider under `app/infrastructure/community/`
3. Register in `get_community_registry()` with **disabled-by-default** flag
4. Add config env key
5. Add unit tests for mock / disabled / fixture paths
6. Document in platform docs
