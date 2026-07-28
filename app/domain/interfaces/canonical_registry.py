"""Canonical Product Registry ports.

``CanonicalProductStore`` is the persistence adapter contract.
``CanonicalProductRegistry`` is the resolve-or-create / graph use-case contract.

Neither port knows about marketplaces or HTTP.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.domain.entities.canonical_product import CanonicalProduct
from app.domain.entities.product_relation import (
    ProductRelation,
    ProductRelationType,
    RelationDirection,
)
from app.domain.entities.registered_product import RegisteredCanonicalProduct, RegistryResolveResult


class CanonicalProductStore(ABC):
    """Persistence port for canonical products and their relationships."""

    @abstractmethod
    async def find_by_identity_key(self, identity_key: str) -> RegisteredCanonicalProduct | None:
        """Lookup a product by its deterministic identity key."""

    @abstractmethod
    async def get_by_id(self, product_id: UUID) -> RegisteredCanonicalProduct | None:
        """Lookup a product by UUID."""

    @abstractmethod
    async def create(self, product: RegisteredCanonicalProduct) -> RegisteredCanonicalProduct:
        """Persist a new canonical product."""

    @abstractmethod
    async def add_relation(self, relation: ProductRelation) -> ProductRelation:
        """Persist a directed product relationship."""

    @abstractmethod
    async def find_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: ProductRelationType,
    ) -> ProductRelation | None:
        """Find an existing directed relationship edge."""

    @abstractmethod
    async def list_relations(
        self,
        *,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
        relation_type: ProductRelationType | None = None,
    ) -> list[ProductRelation]:
        """List relationships filtered by endpoint and/or type."""


class CanonicalProductRegistry(ABC):
    """Resolve parsed products to durable canonical identities."""

    @abstractmethod
    async def resolve(self, parsed: CanonicalProduct) -> RegistryResolveResult:
        """Return existing UUID if known, otherwise create and return a new one."""

    @abstractmethod
    async def get(self, product_id: UUID) -> RegisteredCanonicalProduct | None:
        """Fetch a registered product by UUID."""

    @abstractmethod
    async def link(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: ProductRelationType,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> ProductRelation:
        """Create (or return existing) directed relationship between products."""

    @abstractmethod
    async def list_relations(
        self,
        product_id: UUID,
        *,
        relation_type: ProductRelationType | None = None,
        direction: RelationDirection = RelationDirection.OUTGOING,
    ) -> list[ProductRelation]:
        """List relationships for a product (outgoing, incoming, or both)."""
