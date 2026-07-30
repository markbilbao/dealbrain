"""ORM model for Sprint 23 operational entity persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infrastructure.database.base import Base


class OperationalEntityModel(Base):
    """Generic durable store for Sprint 17–21 operational aggregates.

    Domain entities are stored as codec-encoded JSON payloads. Secondary keys
    enforce uniqueness (email, token hash, dedupe key, content hash, etc.).
    Adapters must not embed ranking or recommendation logic.
    """

    __tablename__ = "operational_entities"
    __table_args__ = (
        UniqueConstraint("store", "entity_id", name="uq_operational_store_entity"),
        UniqueConstraint("store", "secondary_key", name="uq_operational_store_secondary"),
        Index("ix_operational_store_owner", "store", "owner_id"),
        Index("ix_operational_store_seq", "store", "seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    secondary_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
