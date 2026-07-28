"""In-memory CanonicalProductStore for tests and local prototyping."""

from __future__ import annotations

from uuid import UUID

from app.domain.entities.product_relation import ProductRelation, ProductRelationType
from app.domain.entities.registered_product import RegisteredCanonicalProduct
from app.domain.interfaces.canonical_registry import CanonicalProductStore


class InMemoryCanonicalProductStore(CanonicalProductStore):
    """Process-local store — replaceable with the SQLAlchemy adapter."""

    def __init__(self) -> None:
        self._products_by_id: dict[UUID, RegisteredCanonicalProduct] = {}
        self._products_by_key: dict[str, RegisteredCanonicalProduct] = {}
        self._relations: list[ProductRelation] = []

    async def find_by_identity_key(self, identity_key: str) -> RegisteredCanonicalProduct | None:
        return self._products_by_key.get(identity_key)

    async def get_by_id(self, product_id: UUID) -> RegisteredCanonicalProduct | None:
        return self._products_by_id.get(product_id)

    async def create(self, product: RegisteredCanonicalProduct) -> RegisteredCanonicalProduct:
        if product.identity_key in self._products_by_key:
            return self._products_by_key[product.identity_key]
        self._products_by_id[product.id] = product
        self._products_by_key[product.identity_key] = product
        return product

    async def add_relation(self, relation: ProductRelation) -> ProductRelation:
        existing = await self.find_relation(
            relation.source_id,
            relation.target_id,
            relation.relation_type,
        )
        if existing is not None:
            return existing
        self._relations.append(relation)
        return relation

    async def find_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: ProductRelationType,
    ) -> ProductRelation | None:
        for relation in self._relations:
            if (
                relation.source_id == source_id
                and relation.target_id == target_id
                and relation.relation_type == relation_type
            ):
                return relation
        return None

    async def list_relations(
        self,
        *,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
        relation_type: ProductRelationType | None = None,
    ) -> list[ProductRelation]:
        results: list[ProductRelation] = []
        for relation in self._relations:
            if source_id is not None and relation.source_id != source_id:
                continue
            if target_id is not None and relation.target_id != target_id:
                continue
            if relation_type is not None and relation.relation_type != relation_type:
                continue
            results.append(relation)
        return results
