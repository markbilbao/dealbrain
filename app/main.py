"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app import __version__
from app.api.demo import router as demo_router
from app.api.probes import router as probes_router
from app.api.router import api_router
from app.core.config import settings
from app.core.errors import ErrorBody, register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.validation import run_startup_validation
from app.infrastructure.database.session import close_db, init_db
from app.launch.runtime import mark_startup
from app.schemas.api_common import PaginationMeta

logger = get_logger(__name__)

OPENAPI_TAGS = [
    {"name": "probes", "description": "Liveness, readiness, and health probes (unversioned)"},
    {"name": "health", "description": "Versioned health / ready / live checks"},
    {
        "name": "launch-readiness",
        "description": "Sprint 22 launch dashboard, demo launcher, config",
    },
    {"name": "products", "description": "Product CRUD (bare-list collection; skip/offset alias)"},
    {"name": "intelligence", "description": "Product parsing and matching"},
    {
        "name": "marketplace",
        "description": "Marketplace search (Kind S — no caller sort)",
    },
    {"name": "marketplace-data", "description": "Marketplace sources, sync, offers, history"},
    {
        "name": "dealscore",
        "description": "DealScore ranking (organic — never merchant-biased; no caller sort)",
    },
    {
        "name": "recommendations",
        "description": "Shopping recommendations (no caller sort)",
    },
    {"name": "price-history", "description": "Price history snapshots and ranges"},
    {"name": "collections", "description": "Marketplace collection runs and jobs"},
    {"name": "collection-operations", "description": "Collection operations control plane"},
    {"name": "watchlists", "description": "User watchlists and items"},
    {"name": "alert-rules", "description": "Sprint 19 alert rules, evaluate, and events"},
    {
        "name": "alerts",
        "description": "Sprint 10 legacy alerts (deprecated but still available)",
    },
    {"name": "notifications", "description": "In-app notification center and preferences"},
    {"name": "dashboard", "description": "User dashboard aggregate"},
    {
        "name": "affiliate",
        "description": "Post-rank affiliate link generation (neutrality preserved)",
    },
    {
        "name": "merchant-platform",
        "description": "Merchant org workspace (never alters organic ranking)",
    },
    {"name": "merchant-admin", "description": "Internal merchant review"},
    {"name": "reviews", "description": "Review intelligence"},
    {"name": "review-summary", "description": "AI review summaries"},
    {
        "name": "shopping-assistant",
        "description": "AI shopping assistant (organic ranking — no caller sort)",
    },
    {"name": "community", "description": "Community intelligence"},
    {"name": "knowledge-graph", "description": "Product knowledge graph"},
    {"name": "personal-agent", "description": "Personal AI recommendations"},
    {"name": "user-platform-auth", "description": "User registration and login"},
    {"name": "user-platform-profile", "description": "User profile and preferences"},
    {"name": "user-platform-saved-items", "description": "Saved products, history, searches"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown lifecycle hooks."""
    setup_logging()
    mark_startup()
    logger.info("Starting %s v%s [%s]", settings.app_name, __version__, settings.app_env)

    validation = run_startup_validation()
    if validation.warnings:
        for warning in validation.warnings:
            logger.warning("startup_validation warning=%s", warning)
    if validation.errors:
        for error in validation.errors:
            logger.error("startup_validation error=%s", error)
    else:
        logger.info("startup_validation ok environment=%s", validation.environment)

    if settings.is_production:
        from app.infrastructure.persistence.binding import assert_production_persistence

        assert_production_persistence(settings)

    await init_db()

    from app.infrastructure.persistence.binding import resolve_backend
    from app.infrastructure.persistence.session import require_operational_schema

    needs_sql = any(
        resolve_backend(d) == "sqlalchemy"
        for d in (
            "user_platform",
            "marketplace_data",
            "alerts",
            "notifications",
            "affiliate",
            "merchant",
        )
    )
    if needs_sql:
        try:
            require_operational_schema()
            logger.info("operational persistence schema ok")
        except Exception as exc:
            logger.error("operational persistence schema check failed: %s", exc)
            if settings.is_production or settings.launch_strict_startup:
                raise

    yield

    await close_db()
    logger.info("Shutting down %s", settings.app_name)


def _error_response_ref(status_code: int, description: str) -> dict:
    """OpenAPI response object referencing the shared ErrorBody schema."""
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorBody"},
            }
        },
    }


# Tier-1 (+ closely related) public surfaces that must document ErrorBody errors.
_TIER1_ERROR_DOC_PREFIXES: tuple[str, ...] = (
    "/api/v1/products",
    "/api/v1/watchlists",
    "/api/v1/notifications",
    "/api/v1/alerts",
    "/api/v1/collections",
    "/api/v1/collection-operations",
    "/api/v1/merchants",
    "/api/v1/admin",
    "/api/v1/affiliate",
)


def _ensure_tier1_error_docs(schema: dict) -> None:
    """Attach shared ErrorBody responses to Tier-1 ops missing 4xx/5xx docs.

    Does not change runtime behavior — OpenAPI documentation only.
    """
    components = schema.setdefault("components", {})
    responses = components.setdefault("responses", {})
    responses.setdefault(
        "ErrorBodyValidation",
        _error_response_ref(422, "Validation error (Sprint 22 ErrorBody envelope)"),
    )
    responses.setdefault(
        "ErrorBodyUnauthorized",
        _error_response_ref(401, "Authentication required"),
    )
    responses.setdefault(
        "ErrorBodyForbidden",
        _error_response_ref(403, "Authorization / ownership failure"),
    )
    responses.setdefault(
        "ErrorBodyNotFound",
        _error_response_ref(404, "Resource not found"),
    )
    responses.setdefault(
        "ErrorBodyInternal",
        _error_response_ref(500, "Internal server error"),
    )

    default_errors = {
        "401": {"$ref": "#/components/responses/ErrorBodyUnauthorized"},
        "403": {"$ref": "#/components/responses/ErrorBodyForbidden"},
        "404": {"$ref": "#/components/responses/ErrorBodyNotFound"},
        "422": {"$ref": "#/components/responses/ErrorBodyValidation"},
        "500": {"$ref": "#/components/responses/ErrorBodyInternal"},
    }

    for path, ops in schema.get("paths", {}).items():
        if not any(path.startswith(prefix) for prefix in _TIER1_ERROR_DOC_PREFIXES):
            continue
        for method, operation in ops.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            op_responses = operation.setdefault("responses", {})
            has_client_or_server_error = any(
                isinstance(code, str)
                and code.isdigit()
                and (code.startswith("4") or code.startswith("5"))
                for code in op_responses
            )
            if has_client_or_server_error:
                # Ensure 422 documents ErrorBody when FastAPI only emitted
                # HTTPValidationError, without removing the existing entry.
                if "422" in op_responses:
                    existing = op_responses["422"]
                    if isinstance(existing, dict) and "$ref" not in existing:
                        content = existing.setdefault("content", {})
                        app_json = content.setdefault("application/json", {})
                        # Prefer documenting ErrorBody as the public envelope.
                        app_json["schema"] = {"$ref": "#/components/schemas/ErrorBody"}
                continue
            for code, payload in default_errors.items():
                op_responses.setdefault(code, payload)


def _custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=settings.app_name,
        version=__version__,
        description=(
            "DealBrain AI Commerce Intelligence Platform API.\n\n"
            "## API Stability (Sprint 24)\n"
            "- **Versioning:** `/api/v1` only — **no `/api/v2`**\n"
            "- **Success bodies:** Direct resource objects (no global `{data, meta}` wrapper)\n"
            "- **Collections:** Named keys remain primary; optional additive `items` + "
            "`pagination` where dual-run is safe. Bare lists stay bare lists.\n"
            "- **Pagination:** Prefer `limit` + `offset`. Deprecated `skip` remains an "
            "alias of `offset` on products and watchlists. If both are supplied they "
            "must be equal.\n"
            "- **Sorting:** Optional `sort=field,-other` on allowlisted presentation "
            "endpoints only. **Forbidden** on DealScore, Recommendation, Marketplace "
            "search, and Shopping Assistant organic ranking.\n"
            "- **Errors:** Sprint 22 envelope (`error`, `message`, `status_code`, "
            "`detail`, optional `details` / `request_id`)\n"
            "- **Compatibility:** No mandatory client / frontend changes\n"
            "- Contract: `docs/architecture/SPRINT_24_API_STABILITY.md` · "
            "`docs/API_STANDARDS.md`\n\n"
            "## Launch readiness (Sprint 22)\n"
            "- Probes: `GET /health`, `GET /ready`, `GET /live` "
            "(also under `/api/v1/`)\n"
            "- Rate limiting protects auth, search, affiliate, and merchant routes\n"
            "- Security headers: CSP, HSTS (staging/production), frame options, "
            "referrer & permissions policies\n\n"
            "**Hard rules:** Organic DealScore and recommendation ranking are never "
            "manipulated by affiliate or merchant tools. Merchant isolation is enforced. "
            "Affiliate attachment is post-selection only."
        ),
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema["info"]["contact"] = {
        "name": "DealBrain Platform",
        "url": "https://github.com/markbilbao/dealbrain",
    }
    schema["info"]["x-dealbrain-api-version"] = "v1"
    schema["info"]["x-dealbrain-no-api-v2"] = True
    schema["info"]["x-dealbrain-limitations"] = [
        "No /api/v2 in Sprint 24",
        "No global success envelope",
        "Bare-list product/user collection responses remain arrays",
        "Caller sort never influences DealScore / Recommendation / Shopping Assistant ranking",
        "Sprint 10 legacy /alerts paths deprecated but still available",
    ]
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas.setdefault("ErrorBody", ErrorBody.model_json_schema())
    schemas.setdefault("PaginationMeta", PaginationMeta.model_json_schema())
    # Document bearer auth when not already declared by routes.
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes.setdefault(
        "HTTPBearer",
        {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
    )
    _ensure_tier1_error_docs(schema)
    app.openapi_schema = schema
    return app.openapi_schema


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="DealBrain AI platform backend API",
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_tags=OPENAPI_TAGS,
    )

    # Middleware order: last added = outermost. CORS should stay outer.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(probes_router)
    app.include_router(api_router)
    app.include_router(demo_router)

    app.openapi = lambda: _custom_openapi(app)  # type: ignore[method-assign]

    return app


app = create_app()
