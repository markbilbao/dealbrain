"""Product REST API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_product_service
from app.domain.exceptions import ProductNotFoundError
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products")


@router.get("", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: ProductService = Depends(get_product_service),
) -> list[ProductResponse]:
    """List products with pagination."""
    return await service.list_products(skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """Retrieve a single product by ID."""
    try:
        return await service.get_product(product_id)
    except ProductNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """Create a new product."""
    return await service.create_product(payload)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """Update an existing product."""
    try:
        return await service.update_product(product_id, payload)
    except ProductNotFoundError as exc:
        raise _not_found(exc) from exc


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
) -> None:
    """Delete a product."""
    try:
        await service.delete_product(product_id)
    except ProductNotFoundError as exc:
        raise _not_found(exc) from exc


def _not_found(exc: ProductNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product not found: {exc.product_id}",
    )
