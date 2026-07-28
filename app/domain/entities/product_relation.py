"""Canonical product relationship value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID


class ProductRelationType(StrEnum):
    """Directed relationship types between canonical products.

    Edges are always stored as ``source → target``:
    - ACCESSORY: source is an accessory for target (e.g. case → phone)
    - COMPATIBLE: source works with target
    - SUCCESSOR: source is succeeded by target (newer model)
    - ALTERNATIVE: source is a substitute for target
    """

    ACCESSORY = "accessory"
    COMPATIBLE = "compatible"
    SUCCESSOR = "successor"
    ALTERNATIVE = "alternative"


class RelationDirection(StrEnum):
    """Traversal direction when listing relationships for a product."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


@dataclass(frozen=True, slots=True)
class ProductRelation:
    """A typed directed edge in the canonical product graph."""

    id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: ProductRelationType
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        """Serialize relationship fields for logging and debugging."""
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relation_type": self.relation_type.value,
            "metadata": dict(self.metadata),
        }
