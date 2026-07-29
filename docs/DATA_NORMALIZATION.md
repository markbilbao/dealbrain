"""Marketplace Data Normalization — Sprint 18.

Status: implemented
Date: 2026-07-29

Scope
-----
Convert marketplace-specific raw payloads into canonical ``MarketplaceOffer``
models with provenance, freshness, sellers, and stable content hashes — without
inventing prices or silently promoting fixture/imported data to live.

Architecture
------------
```
Raw payload (dict)
  → MarketplaceRecordNormalizer.normalize(...)
      → parse prices, availability, timestamps, URLs
      → enforce source-mode rules
      → DataProvenance + DataFreshness
      → MarketplaceOffer
  → RawMarketplaceRecord preserved separately (payload + content_hash)
```

Canonical fields
----------------
Product identity: ``marketplace_product_id``, ``title``, brand/model/category,
SKU/UPC/EAN/GTIN, URLs, condition, warranty.

Commercial: currency, ``regular_price`` / ``sale_price``, ``shipping_cost``,
``total_price = unit + shipping``, availability, inventory quantity, seller.

Traceability: ``source_mode``, ``provenance``, ``freshness``, ``raw_record_id``,
``simulated``, human-readable ``label``.

Source mode rules
-----------------
- Caller supplies the authoritative ``source_mode`` for the connector/import.
- Payload ``source_mode=live`` is **ignored** when the connector/import mode is
  fixture or imported.
- Fixture mode always forces ``SourceMode.FIXTURE`` and ``simulated=False``.
- Imported mode always forces ``SourceMode.IMPORTED`` and ``simulated=False``.
- Mock-live may declare ``live`` **only** with ``simulated=True`` and the
  SIMULATED LIVE label.

Raw preservation
----------------
``RawMarketplaceRecord`` stores the original mapped payload plus a SHA-256
``content_hash`` used for duplicate detection and idempotent sync writes.

Limitations
-----------
- No FX conversion; currency is preserved as observed
- Invalid URLs (non-http(s)) raise validation errors
- Matching is separate (``MarketplaceProductMatcher``) and never silently merges
  ambiguous products

Extension guide for official connectors
---------------------------------------
1. Prefer returning raw dicts from the connector; let the normalizer canonicalize.
2. Include ``observed_at`` / ``source_timestamp`` when the provider supplies them.
3. Set ``simulated=False`` only for real official live connectivity.
4. Add tests proving fixture/imported payloads cannot become live.
5. Never scrape; map official API fields only.
"""
