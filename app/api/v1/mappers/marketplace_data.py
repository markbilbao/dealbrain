"""Mappers for Marketplace Data Synchronization API."""

from __future__ import annotations

from app.domain.entities.marketplace_data import (
    ConnectorHealth,
    ImportBatch,
    ImportRecord,
    MarketplaceConnectorInfo,
    MarketplaceOffer,
    MarketplaceSource,
    SyncConflict,
    SyncJob,
)
from app.schemas.marketplace_data import (
    ConnectorCapabilityPayload,
    ConnectorHealthPayload,
    ImportBatchPayload,
    ImportErrorPayload,
    MarketplaceOfferPayload,
    MarketplaceSourcePayload,
    SyncConflictPayload,
    SyncJobPayload,
)


def to_source_payload(source: MarketplaceSource) -> MarketplaceSourcePayload:
    data = source.to_dict()
    return MarketplaceSourcePayload(**data)


def to_connector_payload(
    info: MarketplaceConnectorInfo,
    *,
    configuration: dict | None = None,
    health: dict | None = None,
) -> ConnectorCapabilityPayload:
    data = info.to_dict()
    return ConnectorCapabilityPayload(
        **data,
        configuration=configuration,
        health=health,
    )


def to_health_payload(health: ConnectorHealth) -> ConnectorHealthPayload:
    return ConnectorHealthPayload(**health.to_dict())


def to_import_payload(batch: ImportBatch) -> ImportBatchPayload:
    return ImportBatchPayload(**batch.to_dict())


def to_import_error_payload(record: ImportRecord) -> ImportErrorPayload:
    return ImportErrorPayload(
        record_id=record.record_id,
        row_number=record.row_number,
        status=record.status,
        errors=list(record.errors),
        payload=dict(record.payload),
    )


def to_sync_payload(job: SyncJob) -> SyncJobPayload:
    return SyncJobPayload(**job.to_dict())


def to_conflict_payload(conflict: SyncConflict) -> SyncConflictPayload:
    return SyncConflictPayload(**conflict.to_dict())


def to_offer_payload(offer: MarketplaceOffer) -> MarketplaceOfferPayload:
    data = offer.to_dict()
    return MarketplaceOfferPayload(
        offer_id=data["offer_id"],
        product_id=data["product_id"],
        marketplace=data["marketplace"],
        marketplace_product_id=data["marketplace_product_id"],
        title=data["title"],
        currency=data["currency"],
        regular_price=data["regular_price"],
        sale_price=data["sale_price"],
        shipping_cost=data["shipping_cost"],
        total_price=data["total_price"],
        availability=data["availability"],
        inventory_quantity=data["inventory_quantity"],
        seller=data["seller"],
        marketplace_url=data["marketplace_url"],
        image_url=data["image_url"],
        brand=data["brand"],
        model=data["model"],
        category=data["category"],
        sku=data["sku"],
        source_mode=data["source_mode"],
        provenance=data["provenance"],
        freshness=data["freshness"],
        confidence=data["confidence"],
        matched_canonical_product_id=data["matched_canonical_product_id"],
        match_confidence=data["match_confidence"],
        match_reasons=data["match_reasons"],
        match_ambiguity=data["match_ambiguity"],
        observed_at=data["observed_at"],
        simulated=data["simulated"],
        label=data["label"],
    )
