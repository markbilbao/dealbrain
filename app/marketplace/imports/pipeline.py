"""CSV/JSON import pipeline for marketplace products."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.marketplace_data import (
    ImportBatch,
    ImportBatchStatus,
    ImportRecord,
    SourceMode,
)
from app.domain.exceptions import MarketplaceDataValidationError
from app.marketplace.normalization.normalizer import content_hash
from app.marketplace.security import (
    MAX_IMPORT_ROWS,
    sanitize_csv_cell,
    validate_import_filename,
    validate_import_size,
)

DEFAULT_FIELD_MAPPING: dict[str, str] = {
    "marketplace_product_id": "marketplace_product_id",
    "product_id": "marketplace_product_id",
    "title": "title",
    "brand": "brand",
    "model": "model",
    "category": "category",
    "description": "description",
    "sku": "sku",
    "upc": "upc",
    "ean": "ean",
    "gtin": "gtin",
    "currency": "currency",
    "regular_price": "regular_price",
    "sale_price": "sale_price",
    "shipping_cost": "shipping_cost",
    "availability": "availability",
    "inventory_quantity": "inventory_quantity",
    "seller_id": "seller_id",
    "seller_name": "seller_name",
    "seller_rating": "seller_rating",
    "marketplace_url": "marketplace_url",
    "image_url": "image_url",
    "condition": "condition",
    "warranty": "warranty",
    "observed_at": "observed_at",
}

REQUIRED_FIELDS = frozenset({"marketplace_product_id", "title"})


def detect_content_type(filename: str, content_type: str | None = None) -> str:
    name = filename.lower()
    if name.endswith(".csv"):
        return "text/csv"
    if name.endswith(".json"):
        return "application/json"
    if content_type:
        return content_type.split(";")[0].strip().lower()
    raise MarketplaceDataValidationError("Unable to detect import file type")


def apply_field_mapping(
    row: Mapping[str, Any], mapping: Mapping[str, str] | None = None
) -> dict[str, Any]:
    effective = dict(DEFAULT_FIELD_MAPPING)
    if mapping:
        effective.update({str(k): str(v) for k, v in mapping.items()})
    # Invert: source_field -> canonical
    inverted: dict[str, str] = {}
    for source, canonical in effective.items():
        inverted[source.lower()] = canonical
    out: dict[str, Any] = {}
    for key, value in row.items():
        canon = inverted.get(str(key).strip().lower())
        if canon:
            out[canon] = value
    return out


def validate_mapped_row(row: Mapping[str, Any], *, row_number: int) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if not str(row.get(field) or "").strip():
            errors.append(f"row {row_number}: missing required field '{field}'")
    has_price = row.get("regular_price") not in (None, "") or row.get("sale_price") not in (
        None,
        "",
    )
    if not has_price:
        errors.append(f"row {row_number}: regular_price or sale_price required")
    return errors


def parse_csv_payload(text: str) -> list[dict[str, Any]]:
    # Strip UTF-8 BOM and refuse null bytes
    if "\x00" in text:
        raise MarketplaceDataValidationError("CSV payload contains null bytes")
    cleaned = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(cleaned))
    if not reader.fieldnames:
        raise MarketplaceDataValidationError("CSV missing header row")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(reader, start=2):
        if index - 1 > MAX_IMPORT_ROWS:
            raise MarketplaceDataValidationError(f"CSV exceeds {MAX_IMPORT_ROWS} data rows")
        sanitized = {k: sanitize_csv_cell(v) if isinstance(v, str) else v for k, v in row.items()}
        # Remove leading apostrophe added for formula safety when it was our injection guard
        cleaned_row: dict[str, Any] = {}
        for key, value in sanitized.items():
            if isinstance(value, str) and value.startswith("'") and value[1:2] in "=+-@":
                cleaned_row[key] = value[1:]
            else:
                cleaned_row[key] = value
        rows.append(cleaned_row)
    return rows


def parse_json_payload(text: str) -> list[dict[str, Any]]:
    if "\x00" in text:
        raise MarketplaceDataValidationError("JSON payload contains null bytes")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MarketplaceDataValidationError(f"Invalid JSON: {exc.msg}") from exc
    if isinstance(data, dict):
        if "records" in data and isinstance(data["records"], list):
            data = data["records"]
        else:
            data = [data]
    if not isinstance(data, list):
        raise MarketplaceDataValidationError("JSON import must be an object or array of objects")
    if len(data) > MAX_IMPORT_ROWS:
        raise MarketplaceDataValidationError(f"JSON exceeds {MAX_IMPORT_ROWS} records")
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise MarketplaceDataValidationError("Each JSON record must be an object")
        rows.append(dict(item))
    return rows


def parse_import_payload(
    *,
    filename: str,
    payload: str | bytes,
    content_type: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    try:
        validate_import_filename(filename)
        validate_import_size(payload)
    except ValueError as exc:
        raise MarketplaceDataValidationError(str(exc)) from exc
    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    detected = detect_content_type(filename, content_type)
    if detected in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        return "text/csv", parse_csv_payload(text)
    if detected in {"application/json", "text/json"}:
        return "application/json", parse_json_payload(text)
    raise MarketplaceDataValidationError(f"Unsupported import content type: {detected}")


class ImportPipeline:
    """Validate, map, and stage import rows with duplicate / partial support."""

    def prepare_batch(
        self,
        *,
        batch_id: str,
        filename: str,
        payload: str | bytes,
        content_type: str | None = None,
        field_mapping: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
        now: datetime | None = None,
        known_hashes: set[str] | None = None,
    ) -> tuple[ImportBatch, list[ImportRecord], list[dict[str, Any]]]:
        clock = now or datetime.now(UTC)
        detected, rows = parse_import_payload(
            filename=filename, payload=payload, content_type=content_type
        )
        records: list[ImportRecord] = []
        accepted_payloads: list[dict[str, Any]] = []
        seen_hashes: set[str] = set(known_hashes or ())
        accepted = 0
        rejected = 0
        duplicates = 0
        batch_errors: list[str] = []

        for index, raw_row in enumerate(rows, start=1):
            mapped = apply_field_mapping(raw_row, field_mapping)
            mapped["source_mode"] = SourceMode.IMPORTED.value
            mapped["marketplace"] = mapped.get("marketplace") or "imported"
            row_errors = validate_mapped_row(mapped, row_number=index)
            digest = content_hash(mapped)
            if digest in seen_hashes:
                duplicates += 1
                records.append(
                    ImportRecord(
                        record_id=f"{batch_id}:row:{index}",
                        row_number=index,
                        status="duplicate",
                        payload=mapped,
                        errors=("duplicate of prior import/content hash",),
                        content_hash=digest,
                        duplicate_of=digest,
                    )
                )
                continue
            if row_errors:
                rejected += 1
                records.append(
                    ImportRecord(
                        record_id=f"{batch_id}:row:{index}",
                        row_number=index,
                        status="rejected",
                        payload=mapped,
                        errors=tuple(row_errors),
                        content_hash=digest,
                    )
                )
                batch_errors.extend(row_errors)
                continue
            seen_hashes.add(digest)
            accepted += 1
            accepted_payloads.append(mapped)
            records.append(
                ImportRecord(
                    record_id=f"{batch_id}:row:{index}",
                    row_number=index,
                    status="accepted",
                    payload=mapped,
                    content_hash=digest,
                )
            )

        if accepted == 0 and rejected > 0:
            status = ImportBatchStatus.FAILED
        elif rejected > 0 or duplicates > 0:
            status = ImportBatchStatus.PARTIALLY_COMPLETED
        else:
            status = ImportBatchStatus.COMPLETED

        batch = ImportBatch(
            batch_id=batch_id,
            source_mode=SourceMode.IMPORTED,
            filename=filename,
            content_type=detected,
            status=status,
            created_at=clock,
            completed_at=clock,
            records_total=len(rows),
            records_accepted=accepted,
            records_rejected=rejected,
            records_duplicate=duplicates,
            idempotency_key=idempotency_key,
            field_mapping=dict(field_mapping or {}),
            summary=(
                f"Imported {accepted}/{len(rows)} records "
                f"({rejected} rejected, {duplicates} duplicates)"
            ),
            errors=tuple(batch_errors[:50]),
        )
        return batch, records, accepted_payloads
