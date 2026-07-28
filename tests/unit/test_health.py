"""Health endpoint unit tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_up_when_database_is_available(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"
    assert data["service"] == "DealBrain"
    assert data["database"] == "up"


@pytest.mark.asyncio
async def test_health_returns_degraded_when_database_is_down(
    client: AsyncClient,
    mock_db_session,
) -> None:
    mock_db_session.execute.side_effect = ConnectionError("Database unavailable")

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "down"
