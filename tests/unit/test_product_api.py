"""Product API endpoint unit tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.dependencies import get_product_service
from app.domain.exceptions import ProductNotFoundError
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService
from httpx import AsyncClient

PRODUCT_ID = uuid4()
NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _sample_response(**overrides) -> ProductResponse:
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
    return ProductResponse(**defaults)


@pytest.fixture
def product_service() -> AsyncMock:
    return AsyncMock(spec=ProductService)


@pytest.fixture
async def product_client(
    client: AsyncClient,
    product_service: AsyncMock,
) -> AsyncClient:
    client._transport.app.dependency_overrides[get_product_service] = lambda: product_service
    yield client
    client._transport.app.dependency_overrides.pop(get_product_service, None)


@pytest.mark.asyncio
async def test_list_products_endpoint(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.list_products.return_value = [_sample_response()]

    response = await product_client.get("/api/v1/products")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["brand"] == "Apple"
    product_service.list_products.assert_awaited_once_with(skip=0, limit=100)


@pytest.mark.asyncio
async def test_get_product_endpoint(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.get_product.return_value = _sample_response()

    response = await product_client.get(f"/api/v1/products/{PRODUCT_ID}")

    assert response.status_code == 200
    assert response.json()["manufacturer_sku"] == "MQ001LL/A"


@pytest.mark.asyncio
async def test_get_product_not_found(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.get_product.side_effect = ProductNotFoundError(PRODUCT_ID)

    response = await product_client.get(f"/api/v1/products/{PRODUCT_ID}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_product_endpoint(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.create_product.return_value = _sample_response()

    response = await product_client.post(
        "/api/v1/products",
        json={
            "brand": "Apple",
            "category": "Smartphone",
            "model": "iPhone 16",
            "variant": "Pro",
            "color": "Black",
            "manufacturer_sku": "MQ001LL/A",
            "release_date": "2026-09-20",
            "msrp": "999.00",
            "image_url": "https://example.com/iphone16.png",
        },
    )

    assert response.status_code == 201
    assert response.json()["model"] == "iPhone 16"
    product_service.create_product.assert_awaited_once()
    call_arg = product_service.create_product.await_args.args[0]
    assert isinstance(call_arg, ProductCreate)


@pytest.mark.asyncio
async def test_update_product_endpoint(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.update_product.return_value = _sample_response(brand="Apple Inc.")

    response = await product_client.put(
        f"/api/v1/products/{PRODUCT_ID}",
        json={"brand": "Apple Inc."},
    )

    assert response.status_code == 200
    assert response.json()["brand"] == "Apple Inc."
    product_service.update_product.assert_awaited_once()
    args = product_service.update_product.await_args.args
    assert args[0] == PRODUCT_ID
    assert isinstance(args[1], ProductUpdate)


@pytest.mark.asyncio
async def test_update_product_not_found(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.update_product.side_effect = ProductNotFoundError(PRODUCT_ID)

    response = await product_client.put(
        f"/api/v1/products/{PRODUCT_ID}",
        json={"brand": "Missing"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_endpoint(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.delete_product.return_value = None

    response = await product_client.delete(f"/api/v1/products/{PRODUCT_ID}")

    assert response.status_code == 204
    product_service.delete_product.assert_awaited_once_with(PRODUCT_ID)


@pytest.mark.asyncio
async def test_delete_product_not_found(
    product_client: AsyncClient,
    product_service: AsyncMock,
) -> None:
    product_service.delete_product.side_effect = ProductNotFoundError(PRODUCT_ID)

    response = await product_client.delete(f"/api/v1/products/{PRODUCT_ID}")

    assert response.status_code == 404
