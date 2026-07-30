"""Product REST API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import products_pagination
from app.core.dependencies import get_product_service
from app.domain.exceptions import ProductNotFoundError
from app.schemas.api_common import SORT_ALLOWLIST_PRODUCTS, apply_sort, parse_sort
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products")


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="List products with pagination",
    description=(
        "Bare-list response (Sprint 1–23). Remains a JSON array — not wrapped. "
        "Pagination: prefer ``offset``; deprecated ``skip`` remains an alias. "
        "Optional presentation ``sort`` allowlist: created_at, brand, category."
    ),
)
async def list_products(
    pagination: tuple[int, int] = Depends(products_pagination),
    sort: str | None = Query(
        default=None,
        description="Optional presentation sort, e.g. sort=-created_at,brand",
    ),
    service: ProductService = Depends(get_product_service),
) -> list[ProductResponse]:
    """List products with pagination."""
    limit, offset = pagination
    directives = parse_sort(sort, SORT_ALLOWLIST_PRODUCTS)
    if directives:
        # Presentation sort requires a stable full ordering before paging.
        # Fetch a bounded window then slice — products remain a bare list.
        all_items = await service.list_products(skip=0, limit=10_000)
        sorted_items = apply_sort(all_items, directives)
        return sorted_items[offset : offset + limit]
    return await service.list_products(skip=offset, limit=limit)


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
