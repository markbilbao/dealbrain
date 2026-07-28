"""Registered canonical product and registry / parse resolution results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from app.domain.entities.canonical_product import ParseSignal


class CanonicalProductStatus(StrEnum):
    """Lifecycle state for a canonical product identity."""

    ACTIVE = "active"
    MERGED = "merged"
    DEPRECATED = "deprecated"


@dataclass(frozen=True, slots=True)
class RegisteredCanonicalProduct:
    """A durable canonical product identity in the registry."""

    id: UUID
    identity_key: str
    brand: str
    family: str
    model: str
    storage: str | None = None
    color: str | None = None
    display_name: str = ""
    attributes: Mapping[str, Any] = field(default_factory=dict)
    status: CanonicalProductStatus = CanonicalProductStatus.ACTIVE
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def to_dict(self) -> dict[str, Any]:
        """Serialize primary registry fields."""
        return {
            "id": str(self.id),
            "identity_key": self.identity_key,
            "brand": self.brand,
            "family": self.family,
            "model": self.model,
            "storage": self.storage,
            "color": self.color,
            "display_name": self.display_name,
            "status": self.status.value,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class RegistryResolveResult:
    """Outcome of resolving a parsed product against the registry."""

    product_id: UUID
    created: bool
    product: RegisteredCanonicalProduct


@dataclass(frozen=True, slots=True)
class ParseListingResult:
    """Application-level result of parse → registry resolve.

    Returned by the Product Intelligence service so the API layer can map to
    HTTP schemas without embedding presentation types in the service.
    """

    original_title: str
    product: RegisteredCanonicalProduct
    confidence: float
    is_new_product: bool
    signals: tuple[ParseSignal, ...] = ()
