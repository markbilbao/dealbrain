"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    affiliate,
    alert_rules,
    auth,
    collection_operations,
    collections,
    community,
    dashboard,
    dealscore,
    graph,
    health,
    intelligence,
    launch,
    marketplace,
    marketplace_data,
    merchant,
    notifications,
    personal,
    price_history,
    products,
    profile,
    recommendations,
    review_summary,
    reviews,
    shopping_assistant,
    user,
    watchlists,
)

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router, tags=["health"])
# Sprint 22 launch readiness — dashboard, demo launcher, config export
api_v1_router.include_router(launch.router)
api_v1_router.include_router(products.router, tags=["products"])
api_v1_router.include_router(intelligence.router, tags=["intelligence"])
api_v1_router.include_router(marketplace.router, tags=["marketplace"])
api_v1_router.include_router(marketplace_data.router, tags=["marketplace-data"])
api_v1_router.include_router(marketplace_data.history_router, tags=["marketplace-data"])
api_v1_router.include_router(dealscore.router, tags=["dealscore"])
api_v1_router.include_router(recommendations.router, tags=["recommendations"])
api_v1_router.include_router(price_history.router, tags=["price-history"])
api_v1_router.include_router(collections.router, tags=["collections"])
api_v1_router.include_router(collection_operations.router, tags=["collection-operations"])
api_v1_router.include_router(watchlists.router, tags=["watchlists"])
# Sprint 19 alert-rules/evaluate/events routes must be registered BEFORE the
# Sprint 10 ``watchlists.alerts_router`` (``/alerts/{alert_id}``), otherwise
# FastAPI would match ``/alerts/rules`` and ``/alerts/evaluate`` against the
# Sprint 10 ``{alert_id}`` path parameter first.
api_v1_router.include_router(alert_rules.rules_router, tags=["alert-rules"])
api_v1_router.include_router(alert_rules.evaluate_router, tags=["alert-rules"])
api_v1_router.include_router(watchlists.alerts_router, tags=["alerts"])
api_v1_router.include_router(notifications.router, tags=["notifications"])
api_v1_router.include_router(notifications.preferences_router, tags=["notifications"])
api_v1_router.include_router(dashboard.router, tags=["dashboard"])
# Sprint 20 Affiliate Revenue Engine — post-recommendation monetization only.
api_v1_router.include_router(affiliate.link_router, tags=["affiliate"])
api_v1_router.include_router(affiliate.click_router, tags=["affiliate"])
api_v1_router.include_router(affiliate.report_router, tags=["affiliate"])
api_v1_router.include_router(affiliate.merchant_router, tags=["affiliate"])
api_v1_router.include_router(affiliate.disclosure_router, tags=["affiliate"])
# Sprint 21 Merchant Platform v1 — never manipulates organic DealScore/ranking.
api_v1_router.include_router(merchant.router, tags=["merchant-platform"])
api_v1_router.include_router(merchant.admin_router, tags=["merchant-admin"])
api_v1_router.include_router(reviews.router, tags=["reviews"])
api_v1_router.include_router(review_summary.router, tags=["review-summary"])
api_v1_router.include_router(shopping_assistant.router, tags=["shopping-assistant"])
api_v1_router.include_router(community.router, tags=["community"])
api_v1_router.include_router(graph.router, tags=["knowledge-graph"])
api_v1_router.include_router(personal.router, tags=["personal-agent"])
api_v1_router.include_router(auth.router, tags=["user-platform-auth"])
api_v1_router.include_router(profile.router, tags=["user-platform-profile"])
api_v1_router.include_router(user.router, tags=["user-platform-saved-items"])
