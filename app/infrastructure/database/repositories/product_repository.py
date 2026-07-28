"""Product repository — persistence adapter."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.product import Product


class ProductRepository:
    """SQLAlchemy-backed repository for product records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, skip: int = 0, limit: int = 100) -> list[Product]:
        result = await self._session.execute(
            select(Product).order_by(Product.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return await self._session.get(Product, product_id)

    async def create(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def update(self, product: Product) -> Product:
        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self._session.delete(product)
        await self._session.commit()
