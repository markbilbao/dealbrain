"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    collection_operations,
    collections,
    community,
    dealscore,
    graph,
    health,
    intelligence,
    marketplace,
    personal,
    price_history,
    products,
    recommendations,
    review_summary,
    reviews,
    shopping_assistant,
    watchlists,
)

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(products.router, tags=["products"])
api_v1_router.include_router(intelligence.router, tags=["intelligence"])
api_v1_router.include_router(marketplace.router, tags=["marketplace"])
api_v1_router.include_router(dealscore.router, tags=["dealscore"])
api_v1_router.include_router(recommendations.router, tags=["recommendations"])
api_v1_router.include_router(price_history.router, tags=["price-history"])
api_v1_router.include_router(collections.router, tags=["collections"])
api_v1_router.include_router(collection_operations.router, tags=["collection-operations"])
api_v1_router.include_router(watchlists.router, tags=["watchlists"])
api_v1_router.include_router(watchlists.alerts_router, tags=["alerts"])
api_v1_router.include_router(reviews.router, tags=["reviews"])
api_v1_router.include_router(review_summary.router, tags=["review-summary"])
api_v1_router.include_router(shopping_assistant.router, tags=["shopping-assistant"])
api_v1_router.include_router(community.router, tags=["community"])
api_v1_router.include_router(graph.router, tags=["knowledge-graph"])
api_v1_router.include_router(personal.router, tags=["personal-agent"])
