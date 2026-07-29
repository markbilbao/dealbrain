"""Marketplace Data Imports — Sprint 18.

Status: implemented (CSV/JSON, in-memory)
Date: 2026-07-29

Scope
-----
Structured product import from CSV or JSON into the marketplace data store with
explicit ``imported`` source mode. Imports are never labeled live.

Architecture
------------
```
POST /api/v1/marketplaces/imports
  → MarketplaceDataService.import_payload
      → ImportPipeline.prepare_batch
          → validate filename / size
          → parse CSV or JSON
          → apply field mapping
          → validate required fields
          → duplicate detection via content hash
          → partial accept / reject
      → RawMarketplaceRecord + MarketplaceOffer (+ price/inventory snapshots)
```

Supported formats
-----------------
- **CSV** — header row required; UTF-8; null bytes rejected; max 5,000 data rows
- **JSON** — object, array of objects, or ``{"records": [...]}``
- Max payload size: 1 MiB
- Filenames must be ``.csv`` / ``.json`` without path components

Field mapping
-------------
Default aliases map common headers (``product_id`` → ``marketplace_product_id``,
price / seller / availability fields, etc.). Callers may supply
``field_mapping`` overrides. Required after mapping:

- ``marketplace_product_id``
- ``title``
- ``regular_price`` **or** ``sale_price``

Validation and partial imports
------------------------------
- Invalid rows are rejected with row-level errors; valid rows are accepted
- Batch status: ``completed`` / ``partially_completed`` / ``failed``
- Duplicate content hashes (within batch or prior offers) are marked
  ``duplicate`` without re-writing
- ``idempotency_key`` returns the prior batch without reprocessing

Security
--------
- CSV formula injection: cells starting with ``= + - @`` (and tab/CR) are
  neutralized via ``sanitize_csv_cell``
- Secrets are never accepted as first-class import credentials
- Audit events redact secret-looking keys

Limitations
-----------
- No remote URL fetch of import files
- No spreadsheet formula evaluation
- In-memory only; no durable object storage
- Auth required for create-import when ops auth is enabled

Extension guide
---------------
1. Extend ``DEFAULT_FIELD_MAPPING`` / validators for new canonical fields.
2. Keep ``source_mode=imported`` immutable through normalization.
3. Add tests for schema failures, partial imports, duplicates, and idempotency.
4. Never promote imported rows to ``live``.
"""
