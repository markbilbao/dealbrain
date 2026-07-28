"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.demo import router as demo_router
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.infrastructure.database.session import close_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown lifecycle hooks."""
    setup_logging()
    logger.info("Starting %s v%s [%s]", settings.app_name, __version__, settings.app_env)

    await init_db()

    yield

    await close_db()
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="DealBrain AI platform backend API",
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    app.include_router(demo_router)

    return app


app = create_app()
