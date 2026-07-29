"""Marketplace Data Freshness — Sprint 18.

Status: implemented
Date: 2026-07-29

Scope
-----
Classify how trustworthy an observation is for “current price / inventory”
claims. Freshness is derived from timestamps and source mode — never inferred
solely from clock proximity for fixture data.

Statuses
--------
| Status | Meaning |
|--------|---------|
| ``fresh`` | Live observation within the fresh window |
| ``aging`` | Still usable but aging |
| ``stale`` | Too old or connector unhealthy |
| ``unknown`` | Missing timestamps and/or non-live modes |

Default thresholds (hours, configurable per connector)
------------------------------------------------------
- fresh ≤ 6
- aging ≤ 24
- stale ≤ 72 (and beyond)

Source-mode rules
-----------------
- **Fixture** — always ``unknown``; warning states it is **not** current live
  pricing; ``is_current_live_price`` is always ``False``.
- **Imported** — ``aging`` or ``stale`` based on age (never ``fresh`` live);
  warnings remind consumers it is not live.
- **Live** — age + connector health decide status. Simulated live may be
  ``fresh`` by age but ``is_current_live_price`` stays ``False`` and warnings
  include **SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION**.

Architecture
------------
```
evaluate_freshness(...)
  → DataFreshness attached on MarketplaceOffer / provenance consumers
  → Shopping Assistant / DealScore notes (optional collaborators)
```

Stale warnings
--------------
Aging/stale live data and unhealthy connectors attach human-readable warnings.
Downstream assistants must not claim a price is currently available unless
``is_current_live_price`` is true for non-simulated live data.

Limitations
-----------
- Thresholds are configuration, not marketplace SLAs
- No push invalidation or webhook-driven freshness
- Fixture data remains non-live regardless of ``observed_at``

Extension guide
---------------
1. Tune connector ``freshness_*_hours`` in ``ConnectorConfiguration``.
2. Pass ``connector_healthy`` from health tracking into normalization/sync.
3. Add tests asserting fixture never sets ``is_current_live_price``.
4. Official live connectors must supply trustworthy observation timestamps.
"""
