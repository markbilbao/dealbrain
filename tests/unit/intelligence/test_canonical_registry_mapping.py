"""Unit tests for ORM ↔ domain mapping in the canonical registry store."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.product_relation import ProductRelationType
from app.domain.entities.registered_product import CanonicalProductStatus
from app.infrastructure.database.models.canonical_product import (
    CanonicalProductModel,
    CanonicalProductRelationModel,
)
from app.infrastructure.database.repositories.canonical_product_repository import (
    _to_registered,
    _to_relation,
)


def test_to_registered_maps_orm_row() -> None:
    product_id = uuid4()
    now = datetime(2026, 7, 28, 2, 0, tzinfo=UTC)
    row = CanonicalProductModel(
        id=product_id,
        identity_key="apple/iphone/17-pro-max/256gb/black-titanium",
        brand="Apple",
        family="iPhone",
        model="17 Pro Max",
        storage="256GB",
        color="Black Titanium",
        display_name="Apple iPhone 17 Pro Max 256GB Black Titanium",
        attributes={"confidence": 0.98},
        status="active",
        created_at=now,
        updated_at=now,
    )

    product = _to_registered(row)

    assert product.id == product_id
    assert product.status == CanonicalProductStatus.ACTIVE
    assert product.attributes["confidence"] == 0.98
    assert product.identity_key.endswith("black-titanium")


def test_to_relation_maps_orm_row() -> None:
    relation_id = uuid4()
    source_id = uuid4()
    target_id = uuid4()
    now = datetime(2026, 7, 28, 2, 0, tzinfo=UTC)
    row = CanonicalProductRelationModel(
        id=relation_id,
        source_id=source_id,
        target_id=target_id,
        relation_type="successor",
        metadata_={"confidence": 1.0},
        created_at=now,
    )

    relation = _to_relation(row)

    assert relation.id == relation_id
    assert relation.source_id == source_id
    assert relation.target_id == target_id
    assert relation.relation_type == ProductRelationType.SUCCESSOR
    assert relation.metadata["confidence"] == 1.0
