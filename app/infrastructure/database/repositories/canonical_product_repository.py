"""SQLAlchemy adapter for the Canonical Product Registry store."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.product_relation import ProductRelation, ProductRelationType
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    RegisteredCanonicalProduct,
)
from app.domain.interfaces.canonical_registry import CanonicalProductStore
from app.infrastructure.database.models.canonical_product import (
    CanonicalProductModel,
    CanonicalProductRelationModel,
)


def _to_registered(row: CanonicalProductModel) -> RegisteredCanonicalProduct:
    return RegisteredCanonicalProduct(
        id=row.id,
        identity_key=row.identity_key,
        brand=row.brand,
        family=row.family,
        model=row.model,
        storage=row.storage,
        color=row.color,
        display_name=row.display_name,
        attributes=dict(row.attributes or {}),
        status=CanonicalProductStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_relation(row: CanonicalProductRelationModel) -> ProductRelation:
    return ProductRelation(
        id=row.id,
        source_id=row.source_id,
        target_id=row.target_id,
        relation_type=ProductRelationType(row.relation_type),
        metadata=dict(row.metadata_ or {}),
        created_at=row.created_at,
    )


class SqlAlchemyCanonicalProductStore(CanonicalProductStore):
    """PostgreSQL-backed canonical product and relationship store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_identity_key(self, identity_key: str) -> RegisteredCanonicalProduct | None:
        result = await self._session.execute(
            select(CanonicalProductModel).where(
                CanonicalProductModel.identity_key == identity_key
            )
        )
        row = result.scalar_one_or_none()
        return _to_registered(row) if row else None

    async def get_by_id(self, product_id: UUID) -> RegisteredCanonicalProduct | None:
        row = await self._session.get(CanonicalProductModel, product_id)
        return _to_registered(row) if row else None

    async def create(self, product: RegisteredCanonicalProduct) -> RegisteredCanonicalProduct:
        row = CanonicalProductModel(
            id=product.id,
            identity_key=product.identity_key,
            brand=product.brand,
            family=product.family,
            model=product.model,
            storage=product.storage,
            color=product.color,
            display_name=product.display_name,
            attributes=dict(product.attributes),
            status=product.status.value,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_registered(row)

    async def add_relation(self, relation: ProductRelation) -> ProductRelation:
        row = CanonicalProductRelationModel(
            id=relation.id,
            source_id=relation.source_id,
            target_id=relation.target_id,
            relation_type=relation.relation_type.value,
            metadata_=dict(relation.metadata),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_relation(row)

    async def find_relation(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: ProductRelationType,
    ) -> ProductRelation | None:
        result = await self._session.execute(
            select(CanonicalProductRelationModel).where(
                CanonicalProductRelationModel.source_id == source_id,
                CanonicalProductRelationModel.target_id == target_id,
                CanonicalProductRelationModel.relation_type == relation_type.value,
            )
        )
        row = result.scalar_one_or_none()
        return _to_relation(row) if row else None

    async def list_relations(
        self,
        *,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
        relation_type: ProductRelationType | None = None,
    ) -> list[ProductRelation]:
        stmt = select(CanonicalProductRelationModel)
        if source_id is not None:
            stmt = stmt.where(CanonicalProductRelationModel.source_id == source_id)
        if target_id is not None:
            stmt = stmt.where(CanonicalProductRelationModel.target_id == target_id)
        if relation_type is not None:
            stmt = stmt.where(
                CanonicalProductRelationModel.relation_type == relation_type.value
            )
        stmt = stmt.order_by(CanonicalProductRelationModel.created_at.asc())
        result = await self._session.execute(stmt)
        return [_to_relation(row) for row in result.scalars().all()]
