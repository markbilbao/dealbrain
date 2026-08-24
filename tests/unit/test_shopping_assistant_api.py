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


def test_sanitize_processing_allows_exact_research_authorization_metadata() -> None:
    from app.api.v1.mappers.shopping_assistant import _sanitize_processing

    cleaned = _sanitize_processing(
        {
            "research_authorization_id": "auth-1",
            "authorization_status": "authorized_pending_execution",
            "authorization_version": 1,
            "authorization_created": True,
            "execution_available": False,
            "decision_id": "dec-1",
        }
    )
    assert cleaned["research_authorization_id"] == "auth-1"
    assert cleaned["authorization_status"] == "authorized_pending_execution"
    assert cleaned["authorization_version"] == 1
    assert cleaned["authorization_created"] is True
    assert cleaned["execution_available"] is False
    assert cleaned["decision_id"] == "dec-1"


def test_sanitize_processing_strips_authorization_and_credential_keys() -> None:
    from app.api.v1.mappers.shopping_assistant import _sanitize_processing

    cleaned = _sanitize_processing(
        {
            "authorization": "secret-value",
            "authorization_header": "Bearer leaked",
            "authorization_value": "leaked",
            "authorization_bearer": "leaked",
            "provider_authorization": "leaked",
            "merchant_authorization": "leaked",
            "research_authorization": {"scope": "should-not-leak"},
            "api_key": "k",
            "apikey": "k",
            "token": "t",
            "secret": "s",
            "prompt": "system prompt",
            "system_prompt": "system prompt",
            "Authorization_Header": "Bearer leaked",
            "PROVIDER_AUTHORIZATION": "leaked",
            "Api_Key": "k",
            "decision_id": "keep",
            "action": "propose_research",
        }
    )
    assert "authorization" not in cleaned
    assert "authorization_header" not in cleaned
    assert "authorization_value" not in cleaned
    assert "authorization_bearer" not in cleaned
    assert "provider_authorization" not in cleaned
    assert "merchant_authorization" not in cleaned
    assert "research_authorization" not in cleaned
    assert "api_key" not in cleaned
    assert "apikey" not in cleaned
    assert "token" not in cleaned
    assert "secret" not in cleaned
    assert "prompt" not in cleaned
    assert "system_prompt" not in cleaned
    assert "Authorization_Header" not in cleaned
    assert "PROVIDER_AUTHORIZATION" not in cleaned
    assert "Api_Key" not in cleaned
    assert cleaned["decision_id"] == "keep"
    assert cleaned["action"] == "propose_research"


def test_research_handoff_fields_map_after_strict_sanitizer() -> None:
    from app.api.v1.mappers.shopping_assistant import to_assistant_response
    from app.domain.entities.shopping_assistant import AssistantConfidence
    from app.domain.entities.shopping_assistant import (
        ShoppingAssistantResponse as DomainResponse,
    )

    mapped = to_assistant_response(
        DomainResponse(
            query="Yes, research that",
            intent="general",
            answer="Research is approved for this request. Execution is not available yet.",
            top_recommendation=None,
            alternatives=(),
            evidence=(),
            warnings=(),
            data_status="imported",
            providers_used=("propose_research",),
            fallback_used=True,
            confidence=AssistantConfidence(score=0.55, band="Medium"),
            processing={
                "action": "propose_research",
                "research_authorization_id": "auth-handoff-1",
                "authorization_status": "authorized_pending_execution",
                "authorization_version": 1,
                "authorization_created": True,
                "execution_available": False,
                "research_authorization": {"owner_binding": "opaque"},
                "authorization_header": "Bearer leaked",
                "decision_id": "dec-1",
            },
        )
    )
    assert mapped.research_handoff_id == "auth-handoff-1"
    assert mapped.research_handoff_status == "authorized_pending_execution"
    assert mapped.research_handoff_version == 1
    assert mapped.research_handoff_created is True
    assert mapped.execution_available is False
    assert mapped.processing["research_authorization_id"] == "auth-handoff-1"
    assert mapped.processing["authorization_status"] == "authorized_pending_execution"
    assert mapped.processing["authorization_version"] == 1
    assert mapped.processing["authorization_created"] is True
    assert mapped.processing["execution_available"] is False
    assert "authorization_header" not in mapped.processing
    assert "research_authorization" not in mapped.processing
    assert mapped.processing["decision_id"] == "dec-1"
