"""Normalize marketplace-specific records into DealBrain canonical offer models."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.marketplace_data import (
    DataFreshness,
    DataProvenance,
    MarketplaceOffer,
    MarketplaceSeller,
    MatchAmbiguityStatus,
    ProductAvailability,
    SourceMode,
)
from app.marketplace.freshness.rules import evaluate_freshness
from app.marketplace.security import validate_url


def content_hash(payload: Mapping[str, Any]) -> str:
    """Stable hash for idempotent writes / duplicate detection."""
    canonical = json.dumps(dict(payload), sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_availability(value: Any) -> ProductAvailability:
    text = str(value or "unknown").strip().lower().replace(" ", "_")
    mapping = {
        "in_stock": ProductAvailability.IN_STOCK,
        "instock": ProductAvailability.IN_STOCK,
        "available": ProductAvailability.IN_STOCK,
        "out_of_stock": ProductAvailability.OUT_OF_STOCK,
        "outofstock": ProductAvailability.OUT_OF_STOCK,
        "unavailable": ProductAvailability.OUT_OF_STOCK,
        "limited": ProductAvailability.LIMITED,
        "low_stock": ProductAvailability.LIMITED,
        "preorder": ProductAvailability.PREORDER,
        "pre_order": ProductAvailability.PREORDER,
    }
    return mapping.get(text, ProductAvailability.UNKNOWN)


def parse_source_mode(value: Any, *, default: SourceMode) -> SourceMode:
    text = str(value or default.value).strip().lower()
    if text in {"fixture", "mock", "demo"}:
        return SourceMode.FIXTURE
    if text in {"imported", "import"}:
        return SourceMode.IMPORTED
    if text in {"live"}:
        return SourceMode.LIVE
    return default


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class MarketplaceRecordNormalizer:
    """Convert raw marketplace payloads into ``MarketplaceOffer`` with provenance."""

    def normalize(
        self,
        raw: Mapping[str, Any],
        *,
        source_mode: SourceMode,
        source_id: str,
        connector_id: str | None = None,
        import_batch_id: str | None = None,
        raw_record_id: str | None = None,
        ingested_at: datetime | None = None,
        now: datetime | None = None,
        connector_healthy: bool | None = None,
        freshness_thresholds: tuple[float, float, float] = (6.0, 24.0, 72.0),
        simulated: bool = False,
        offer_id: str | None = None,
        product_id: str | None = None,
    ) -> MarketplaceOffer:
        clock = now or datetime.now(UTC)
        ingested = ingested_at or clock
        marketplace = str(raw.get("marketplace") or source_id or "unknown")
        marketplace_product_id = str(
            raw.get("marketplace_product_id") or raw.get("product_id") or ""
        ).strip()
        title = str(raw.get("title") or "").strip()
        if not marketplace_product_id or not title:
            raise ValueError("marketplace_product_id and title are required")

        currency = str(raw.get("currency") or "PHP").strip().upper() or "PHP"
        regular = _as_float(raw.get("regular_price"))
        sale = _as_float(raw.get("sale_price"))
        shipping = _as_float(raw.get("shipping_cost")) or 0.0
        unit = sale if sale is not None else regular
        if unit is None:
            raise ValueError("regular_price or sale_price is required")
        total = float(unit) + float(shipping)

        observed_at = parse_datetime(raw.get("observed_at")) or clock
        source_ts = parse_datetime(raw.get("source_timestamp")) or observed_at
        is_simulated = bool(raw.get("simulated")) or simulated or marketplace == "simulated_live"
        mode = parse_source_mode(raw.get("source_mode"), default=source_mode)
        # Never promote fixture/imported to live based on payload alone unless connector is live
        # and simulated is explicit for mock-live.
        if mode == SourceMode.LIVE and source_mode != SourceMode.LIVE:
            mode = source_mode
        if source_mode == SourceMode.FIXTURE:
            mode = SourceMode.FIXTURE
            is_simulated = False
        if source_mode == SourceMode.IMPORTED:
            mode = SourceMode.IMPORTED
            is_simulated = False

        seller = None
        seller_name = raw.get("seller_name")
        seller_id = str(raw.get("seller_id") or seller_name or "").strip()
        if seller_id or seller_name:
            seller = MarketplaceSeller(
                seller_id=seller_id or "unknown-seller",
                name=str(seller_name or seller_id),
                marketplace=marketplace,
                rating=_as_float(raw.get("seller_rating")),
                review_count=_as_int(raw.get("seller_review_count")),
                url=validate_url(raw.get("seller_url")) if raw.get("seller_url") else None,
                source_mode=mode,
            )

        provenance = DataProvenance(
            source_mode=mode,
            source_id=source_id,
            connector_id=connector_id,
            import_batch_id=import_batch_id,
            raw_record_id=raw_record_id,
            observed_at=observed_at,
            source_timestamp=source_ts,
            ingested_at=ingested,
            confidence=float(raw.get("confidence") or 1.0),
            notes=str(raw.get("notes") or ""),
            simulated=is_simulated,
        )
        freshness = evaluate_freshness(
            source_mode=mode,
            observed_at=observed_at,
            source_timestamp=source_ts,
            ingested_at=ingested,
            now=clock,
            connector_healthy=connector_healthy,
            thresholds=freshness_thresholds,
            simulated=is_simulated,
        )

        pid = product_id or f"{marketplace}:{marketplace_product_id}"
        oid = offer_id or f"offer:{marketplace}:{marketplace_product_id}:{content_hash(raw)[:12]}"

        return MarketplaceOffer(
            offer_id=oid,
            product_id=pid,
            marketplace=marketplace,
            marketplace_product_id=marketplace_product_id,
            title=title,
            currency=currency,
            regular_price=regular,
            sale_price=sale,
            shipping_cost=float(shipping),
            total_price=total,
            availability=parse_availability(raw.get("availability")),
            inventory_quantity=_as_int(raw.get("inventory_quantity")),
            seller=seller,
            marketplace_url=validate_url(raw.get("marketplace_url")),
            image_url=validate_url(raw.get("image_url")),
            condition=(str(raw["condition"]).strip() if raw.get("condition") else None),
            warranty=(str(raw["warranty"]).strip() if raw.get("warranty") else None),
            brand=(str(raw["brand"]).strip() if raw.get("brand") else None),
            model=(str(raw["model"]).strip() if raw.get("model") else None),
            category=(str(raw["category"]).strip() if raw.get("category") else None),
            sku=(str(raw["sku"]).strip() if raw.get("sku") else None),
            source_mode=mode,
            provenance=provenance,
            freshness=freshness,
            confidence=float(raw.get("confidence") or 1.0),
            match_ambiguity=MatchAmbiguityStatus.UNMATCHED,
            observed_at=observed_at,
            raw_record_id=raw_record_id,
            simulated=is_simulated,
        )


# Re-export for type checkers / callers expecting freshness on module
__all__ = [
    "MarketplaceRecordNormalizer",
    "content_hash",
    "parse_availability",
    "parse_datetime",
    "parse_source_mode",
    "DataFreshness",
]
