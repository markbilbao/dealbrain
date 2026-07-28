"""ORM models for the Canonical Product Registry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class CanonicalProductModel(Base):
    """Durable canonical product identity (intelligence layer).

    Separate from marketplace/SKU ``products`` — this table is the node set
    for the product knowledge graph.
    """

    __tablename__ = "canonical_products"
    __table_args__ = (
        Index("ix_canonical_products_brand_family_model", "brand", "family", "model"),
        Index("ix_canonical_products_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    identity_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    storage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    # Extensible bag for future attributes without schema churn.
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CanonicalProductRelationModel(Base):
    """Typed directed edge between canonical products.

    Supports accessories, compatibility, successor chains, and alternatives
    via ``relation_type`` without per-type junction tables.
    """

    __tablename__ = "canonical_product_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "target_id",
            "relation_type",
            name="uq_canonical_product_relation_edge",
        ),
        Index("ix_canonical_product_relations_source_type", "source_id", "relation_type"),
        Index("ix_canonical_product_relations_target_type", "target_id", "relation_type"),
        Index("ix_canonical_product_relations_type", "relation_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
