"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, intelligence, products

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(products.router, tags=["products"])
api_v1_router.include_router(intelligence.router, tags=["intelligence"])
