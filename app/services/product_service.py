"""Product CRUD service."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.exceptions import ProductNotFoundError
from app.infrastructure.database.models.product import Product
from app.infrastructure.database.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate


class ProductService:
    """Application service for product use cases."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def list_products(self, *, skip: int = 0, limit: int = 100) -> list[ProductResponse]:
        products = await self._repository.list(skip=skip, limit=limit)
        return [ProductResponse.model_validate(product) for product in products]

    async def get_product(self, product_id: UUID) -> ProductResponse:
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return ProductResponse.model_validate(product)

    async def create_product(self, data: ProductCreate) -> ProductResponse:
        product = Product(
            brand=data.brand,
            category=data.category,
            model=data.model,
            variant=data.variant,
            color=data.color,
            manufacturer_sku=data.manufacturer_sku,
            release_date=data.release_date,
            msrp=data.msrp,
            image_url=str(data.image_url) if data.image_url is not None else None,
        )
        created = await self._repository.create(product)
        return ProductResponse.model_validate(created)

    async def update_product(self, product_id: UUID, data: ProductUpdate) -> ProductResponse:
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)

        update_data = data.model_dump(exclude_unset=True)
        if "image_url" in update_data and update_data["image_url"] is not None:
            update_data["image_url"] = str(update_data["image_url"])

        for field, value in update_data.items():
            setattr(product, field, value)

        product.updated_at = datetime.now(UTC)
        updated = await self._repository.update(product)
        return ProductResponse.model_validate(updated)

    async def delete_product(self, product_id: UUID) -> None:
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        await self._repository.delete(product)
