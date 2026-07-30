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
from app.core.errors import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.validation import run_startup_validation
from app.infrastructure.database.session import close_db, init_db
from app.launch.runtime import mark_startup

logger = get_logger(__name__)

OPENAPI_TAGS = [
    {"name": "probes", "description": "Liveness, readiness, and health probes"},
    {"name": "health", "description": "Versioned health / ready / live checks"},
    {
        "name": "launch-readiness",
        "description": "Sprint 22 launch dashboard, demo launcher, config",
    },
    {"name": "products", "description": "Product CRUD"},
    {"name": "intelligence", "description": "Product parsing and matching"},
    {"name": "marketplace", "description": "Marketplace search"},
    {"name": "dealscore", "description": "DealScore ranking (organic — never merchant-biased)"},
    {"name": "recommendations", "description": "Shopping recommendations"},
    {"name": "affiliate", "description": "Post-rank affiliate link generation"},
    {"name": "merchant-platform", "description": "Merchant org workspace (demo)"},
    {"name": "merchant-admin", "description": "Internal merchant review"},
    {"name": "user-platform-auth", "description": "User registration and login"},
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
        if settings.is_production or settings.launch_strict_startup:
            from app.domain.exceptions import ConfigurationValidationError

            raise ConfigurationValidationError(list(validation.errors))
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


def _custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=settings.app_name,
        version=__version__,
        description=(
            "DealBrain AI Commerce Intelligence Platform API.\n\n"
            "## Launch readiness (Sprint 22)\n"
            "- Probes: `GET /health`, `GET /ready`, `GET /live` "
            "(also under `/api/v1/`)\n"
            "- Errors use a consistent JSON envelope (`error`, `message`, "
            "`status_code`, plus legacy `detail`)\n"
            "- Rate limiting protects auth, search, affiliate, and merchant routes\n"
            "- Security headers: CSP, HSTS (staging/production), frame options, "
            "referrer & permissions policies\n\n"
            "**Hard rules:** Organic DealScore and recommendation ranking are never "
            "manipulated by affiliate or merchant tools. Merchant isolation is enforced. "
            "Demo/in-memory — no production secrets, payments, or real email/SMS."
        ),
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema["info"]["contact"] = {
        "name": "DealBrain Platform",
        "url": "https://github.com/markbilbao/dealbrain",
    }
    schema["info"]["x-dealbrain-limitations"] = [
        "No real cloud deployment in this sprint",
        "No production database / secrets",
        "No payment processing",
        "No real email / SMS / push providers",
    ]
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
