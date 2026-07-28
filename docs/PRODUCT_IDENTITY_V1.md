"""Product Identity V1.0 — Architecture Review Report

**Status:** Frozen as Product Identity Version 1.0.0  
**Date:** 2026-07-28  
**Scope:** Product Intelligence Engine · Canonical Product Registry · Product Matching Engine

---

## Architecture principles (verified)

| Principle | Status |
|-----------|--------|
| Parser knows nothing about registry | Pass |
| Registry knows nothing about marketplaces | Pass |
| Matcher depends only on parser outputs (`CanonicalProduct`) | Pass |
| API depends only on services (+ schema mapping) | Pass |
| Services depend only on domain interfaces | Pass |
| Domain remains framework independent | Pass |
| No Product Identity business logic in API routes | Pass |
| Parser, registry, and matcher independently testable | Pass |

---

## Strengths

1. **Clean ports** — `ProductIntelligenceEngine`, `CanonicalProductRegistry` /
   `CanonicalProductStore`, and `ProductMatcher` are replaceable ABCs.
2. **Deterministic core** — rule engine, identity keys, and exact-variant matching
   require no LLMs.
3. **Explainability** — parse signals and match explanations are first-class.
4. **Layered HTTP** — routes map domain VOs via `app.api.v1.mappers.intelligence`;
   services no longer return Pydantic schemas.
5. **Immutable domain VOs** — frozen dataclasses; mapping fields sealed with
   `MappingProxyType`.
6. **Shared identity primitives** in `app.domain.identity` used by registry and
   matcher without cross-adapter imports.

---

## Weaknesses

1. **Identity thresholds differ** — registration requires brand+family+model;
   matching allows family+model or brand+model. Documented, but easy to confuse.
2. **Variant fields not in registry identity key** — `connector` / `screen_size`
   are parsed and matched but not part of `identity_key` or the parse API payload.
3. **In-memory registry is process-global** — demo default shares state across
   requests; fine for demos, not for multi-worker production.
4. **Parse confidence weights** omit connector/screen_size.

---

## Technical debt

1. Catalog coverage is Apple-heavy; other brands are brand-alias only.
2. No uniqueness/retry handling on concurrent SQL registry creates.
3. Relation graph APIs exist on the registry port but are not exposed over HTTP.
4. `AIProvider` / generic `Repository` ports remain unused stubs in domain.

---

## Suggested improvements (future only — not implemented)

1. Extend registry `identity_key` (and parse response) with connector/screen_size
   when marketplace SKU fidelity requires it.
2. Persist registry in Postgres by default in staging/production; keep memory for
   local demos only.
3. Add fuzzy / embedding-assisted matching behind a new `ProductMatcher`
   implementation without changing the port.
4. Expose relationship link/list endpoints when Knowledge Graph work begins.
5. Broaden non-Apple family/model catalogs.

---

## Version stamp

```
Product Identity = 1.0.0
```

Declared in `app/__init__.py` (`PRODUCT_IDENTITY_VERSION`) and
`app/intelligence/__init__.py`.
"""
