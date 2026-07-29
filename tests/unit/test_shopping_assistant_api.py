"""API tests for AI Shopping Assistant endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core.dependencies import get_shopping_assistant_service
from app.domain.interfaces.shopping_assistant_repository import ShoppingExplanationProvider
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.main import create_app
from app.services.shopping_assistant_service import ShoppingAssistantService
from httpx import ASGITransport, AsyncClient


class _UnavailableProvider(ShoppingExplanationProvider):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return f"{self._name}-test"

    def is_available(self) -> bool:
        return False

    def explain(self, payload):  # noqa: ANN001
        return {
            "provider": self._name,
            "model": self.model_name,
            "status": "unavailable",
            "answer": "",
        }


def _build_service(*, ai_enabled: bool = False, mode: str = "economy") -> ShoppingAssistantService:
    registry = ShoppingExplanationRegistry(
        [
            _UnavailableProvider("openai"),
            _UnavailableProvider("anthropic"),
            _UnavailableProvider("gemini"),
            DeterministicShoppingProviderAdapter(),
        ]
    )
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=ai_enabled,
        configured_mode=mode,  # type: ignore[arg-type]
        allow_client_mode=True,
    )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=300),
        max_query_length=500,
        clock=lambda: datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
async def client():
    app = create_app()
    service = _build_service(ai_enabled=False, mode="economy")
    app.dependency_overrides[get_shopping_assistant_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http, service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_query_recommendation(client) -> None:
    http, _service = client
    response = await http.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "What is the best gaming laptop under ₱60,000?", "mode": "economy"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "recommendation"
    assert body["top_recommendation"]["product_name"]
    assert body["evidence"]
    assert body["data_status"] == "mock"
    assert body["fallback_used"] is True
    assert "api_key" not in response.text.lower()
    assert "disclaimer" in body


@pytest.mark.asyncio
async def test_get_demo(client) -> None:
    http, _service = client
    response = await http.get("/api/v1/shopping-assistant/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["top_recommendation"] is not None
    assert body["data_status"] == "mock"


@pytest.mark.asyncio
async def test_get_meta(client) -> None:
    http, service = client
    response = await http.get("/api/v1/shopping-assistant/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["example_queries"]
    assert "economy" in body["allowed_modes"]
    assert body["allowed_modes"] == service.allowed_modes()


@pytest.mark.asyncio
async def test_query_length_restriction_api(client) -> None:
    http, _service = client
    response = await http.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "x" * 501},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_mode_restriction_clamps_to_server(client) -> None:
    http, _service = client
    response = await http.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "Best gaming laptop under 60000", "mode": "maximum"},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "economy"


@pytest.mark.asyncio
async def test_structured_filters_accepted(client) -> None:
    http, _service = client
    response = await http.post(
        "/api/v1/shopping-assistant/query",
        json={
            "query": "Recommend a laptop",
            "budget_max": 60000,
            "currency": "PHP",
            "use_cases": ["gaming"],
            "mode": "economy",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["top_recommendation"] is not None
    assert body["top_recommendation"]["known_price"] <= 60000


@pytest.mark.asyncio
async def test_comparison_response_shape(client) -> None:
    http, _service = client
    response = await http.post(
        "/api/v1/shopping-assistant/query",
        json={
            "query": (
                "Compare iPhone 17 Pro Max and Samsung Galaxy S25 Ultra for camera and battery"
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "comparison"
    assert body["comparison"] is not None
    assert body["comparison"]["category_winners"]


@pytest.mark.asyncio
async def test_no_secrets_in_api_response(client) -> None:
    http, _service = client
    response = await http.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "Best gaming laptop under 60000"},
    )
    text = response.text.lower()
    assert "api_key" not in text
    assert "authorization" not in text
    assert "sk-" not in text
