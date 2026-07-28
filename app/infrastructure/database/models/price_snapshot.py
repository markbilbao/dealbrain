"""ORM model for timestamped marketplace price snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class PriceSnapshotModel(Base):
    """Durable marketplace price observation.

    Uniqueness: ``(canonical_product_id, marketplace, listing_id, observed_at)``.
    """

    __tablename__ = "price_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "canonical_product_id",
            "marketplace",
            "listing_id",
            "observed_at",
            name="uq_price_snapshot_observation",
        ),
        Index("ix_price_snapshots_canonical_product_id", "canonical_product_id"),
        Index("ix_price_snapshots_listing_id", "listing_id"),
        Index("ix_price_snapshots_observed_at", "observed_at"),
        Index(
            "ix_price_snapshots_product_observed",
            "canonical_product_id",
            "observed_at",
        ),
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    canonical_product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    marketplace: Mapped[str] = mapped_column(String(64), nullable=False)
    listing_id: Mapped[str] = mapped_column(String(128), nullable=False)
    seller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    item_price: Mapped[float] = mapped_column(Float, nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    availability: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
