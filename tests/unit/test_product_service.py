"""Product service unit tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.domain.exceptions import ProductNotFoundError
from app.infrastructure.database.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import ProductService

PRODUCT_ID = uuid4()
NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _sample_product(**overrides) -> Product:
    defaults = {
        "id": PRODUCT_ID,
        "brand": "Apple",
        "category": "Smartphone",
        "model": "iPhone 16",
        "variant": "Pro",
        "color": "Black",
        "manufacturer_sku": "MQ001LL/A",
        "release_date": date(2026, 9, 20),
        "msrp": Decimal("999.00"),
        "image_url": "https://example.com/iphone16.png",
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Product(**defaults)


def _sample_create(**overrides) -> ProductCreate:
    defaults = {
        "brand": "Apple",
        "category": "Smartphone",
        "model": "iPhone 16",
        "variant": "Pro",
        "color": "Black",
        "manufacturer_sku": "MQ001LL/A",
        "release_date": date(2026, 9, 20),
        "msrp": Decimal("999.00"),
        "image_url": "https://example.com/iphone16.png",
    }
    defaults.update(overrides)
    return ProductCreate(**defaults)


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(repository: AsyncMock) -> ProductService:
    return ProductService(repository)


@pytest.mark.asyncio
async def test_list_products(service: ProductService, repository: AsyncMock) -> None:
    product = _sample_product()
    repository.list.return_value = [product]

    results = await service.list_products(skip=0, limit=10)

    assert len(results) == 1
    assert results[0].id == PRODUCT_ID
    assert results[0].brand == "Apple"
    repository.list.assert_awaited_once_with(skip=0, limit=10)


@pytest.mark.asyncio
async def test_get_product_returns_product(service: ProductService, repository: AsyncMock) -> None:
    repository.get_by_id.return_value = _sample_product()

    result = await service.get_product(PRODUCT_ID)

    assert result.manufacturer_sku == "MQ001LL/A"
    repository.get_by_id.assert_awaited_once_with(PRODUCT_ID)


@pytest.mark.asyncio
async def test_get_product_raises_when_not_found(
    service: ProductService,
    repository: AsyncMock,
) -> None:
    repository.get_by_id.return_value = None

    with pytest.raises(ProductNotFoundError):
        await service.get_product(PRODUCT_ID)


@pytest.mark.asyncio
async def test_create_product(service: ProductService, repository: AsyncMock) -> None:
    async def persist(product: Product) -> Product:
        product.id = PRODUCT_ID
        product.created_at = NOW
        product.updated_at = NOW
        return product

    repository.create.side_effect = persist

    result = await service.create_product(_sample_create())

    assert result.brand == "Apple"
    assert result.image_url == "https://example.com/iphone16.png"
    repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_product(service: ProductService, repository: AsyncMock) -> None:
    product = _sample_product()
    repository.get_by_id.return_value = product
    repository.update.return_value = product

    result = await service.update_product(
        PRODUCT_ID,
        ProductUpdate(brand="Apple Inc.", msrp=Decimal("1099.00")),
    )

    assert result.brand == "Apple Inc."
    assert product.msrp == Decimal("1099.00")
    repository.update.assert_awaited_once_with(product)


@pytest.mark.asyncio
async def test_update_product_raises_when_not_found(
    service: ProductService,
    repository: AsyncMock,
) -> None:
    repository.get_by_id.return_value = None

    with pytest.raises(ProductNotFoundError):
        await service.update_product(PRODUCT_ID, ProductUpdate(brand="Updated"))


@pytest.mark.asyncio
async def test_delete_product(service: ProductService, repository: AsyncMock) -> None:
    product = _sample_product()
    repository.get_by_id.return_value = product

    await service.delete_product(PRODUCT_ID)

    repository.delete.assert_awaited_once_with(product)


@pytest.mark.asyncio
async def test_delete_product_raises_when_not_found(
    service: ProductService,
    repository: AsyncMock,
) -> None:
    repository.get_by_id.return_value = None

    with pytest.raises(ProductNotFoundError):
        await service.delete_product(PRODUCT_ID)
