"""Marketplace Connector Architecture — Sprint 18.

Status: implemented (fixture / imported / simulated-live + future stubs)
Date: 2026-07-29

Sprint 31 unification ADR (search / sync / collection / research remain
separate implementations; documented 4/18 dual-run; September 15, 2026
disposition recorded 2026-09-05 — retain intentional dual implementations):
docs/architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md
Onboarding runbook: docs/runbooks/MERCHANT_PROVIDER_ONBOARDING.md

Scope
-----
Pluggable ``MarketplaceDataConnector`` adapters for marketplace data sync.
Distinct from Sprint 4 ``MarketplaceConnector`` (search/normalize listings) and
Sprint 8 ``MarketplaceCollector`` (scheduled collection into Price History).

Port
----
Implement ``MarketplaceDataConnector``
(``app/domain/interfaces/marketplace_data_repository.py``):

- ``connector_id``, ``name``, ``marketplace``
- ``capabilities`` → ``frozenset[ConnectorCapability]``
- ``validate_configuration(config)`` / ``test_connection(config)``
- Optional: ``fetch_products``, ``fetch_product``, ``fetch_offers``,
  ``fetch_prices``, ``fetch_inventory``, ``fetch_sellers``, ``fetch_reviews``,
  ``continue_from_checkpoint``, ``report_rate_limit``, ``report_health``

Implemented connectors
----------------------
| Connector | Mode | Notes |
|-----------|------|-------|
| ``FixtureMarketplaceConnector`` | fixture | Canned demo offers; never live |
| ``ImportedMarketplaceConnector`` | imported | Reads stored CSV/JSON imports; never live |
| ``MockLiveMarketplaceConnector`` | live (simulated) | **SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION** |

Future stubs (not implemented)
------------------------------
``FutureOfficialConnectorStub`` entries for Shopee, Lazada, Amazon,
TikTok Shop, and eBay. They report ``UNCONFIGURED``, refuse validation, and
perform **no** HTTP. Official partner APIs only — never scrape.

Registry
--------
```python
registry = MarketplaceConnectorRegistry(
    [
        FixtureMarketplaceConnector(),
        ImportedMarketplaceConnector(),
        MockLiveMarketplaceConnector(),
    ],
    register_stubs=True,
)
registry.register(MyOfficialConnector(...))
```

``list_infos(include_stubs=True)`` surfaces stub metadata for documentation /
demo UIs without claiming connectivity.

Configuration
-------------
``ConnectorConfiguration`` holds non-secret settings (base URL, region,
timeouts, freshness thresholds, opaque ``ConnectorCredentialReference``).
Secret values are never persisted in Sprint 18; API responses redact keys
matching secret/password/token/auth patterns.

Architecture
------------
```
MarketplaceConnectorRegistry
  → MarketplaceDataConnector implementations
  → MarketplaceSyncEngine / MarketplaceDataService
  → InMemoryMarketplaceDataRepository
```

Limitations
-----------
- Mock-live is deterministic simulation only
- Stubs are documentation placeholders
- No vendor SDKs embedded in application services
- No scraping browsers or unofficial HTML parsers

Extension guide for official connectors
---------------------------------------
1. Implement ``MarketplaceDataConnector`` with honest ``SOURCE_MODE`` / labels.
2. Normalize raw payloads via ``MarketplaceRecordNormalizer`` (preserve raw).
3. Register in ``MarketplaceConnectorRegistry`` / DI wiring.
4. Add non-secret config + opaque credential references (never log secrets).
5. Add unit tests for fixture/disabled/mock paths and rate-limit/health.
6. Document capabilities and legal requirements.
7. **Never scrape.** Prefer official partner APIs only after legal review.

Sprint 31 research execution routing
------------------------------------
Authorized-research planning uses a separate provider registry, a trusted
certification catalog, and a trusted routing-policy catalog
(``docs/architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md``).
Unification decision and recorded 4/18 architecture review:
``docs/architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md``.
It does not replace this Sprint 18 sync registry, Sprint 4 search connectors, or
Sprint 8 collectors. Technical ``ConnectorCapability`` remains distinct from
Sprint 31 contractual certification, and a provider descriptor cannot certify
itself or choose its own routing preference. Live merchant execution is still
not implemented. Sprint 31 was formally owner-closed before Sprint 32
implementation began. Sprint 32 is in progress and is **not complete**.

"""
