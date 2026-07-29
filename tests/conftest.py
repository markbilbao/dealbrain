"""Shared pytest fixtures."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.dependencies import get_db, get_performance_cache, get_rate_limiter
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def _isolate_launch_middleware_state() -> Generator[None, None, None]:
    """Disable process-scoped rate limits and clear caches between tests.

    The HTTP rate limiter is shared across the pytest process; leaving it
    enabled would eventually 429 prior-sprint suites that share one client IP.
    """
    limiter = get_rate_limiter()
    cache = get_performance_cache()
    previous = limiter.enabled
    limiter.set_enabled(False)
    limiter.reset()
    cache.clear()
    yield
    limiter.reset()
    limiter.set_enabled(previous)
    cache.clear()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Provide a mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())
    return session


@pytest.fixture
async def client(mock_db_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client with mocked database dependency."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend() -> Generator[str, None, None]:
    """Use asyncio as the anyio backend."""
    yield "asyncio"
