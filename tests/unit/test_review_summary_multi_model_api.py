"""API tests for multi-model mode restrictions and response metadata."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from app.core.dependencies import (
    get_multi_model_review_orchestrator,
    get_review_repository,
    get_review_service,
    get_review_summary_repository,
    get_review_summary_service,
)
from app.infrastructure.ai.review_providers import (
    ClaudeReviewProvider,
    DeterministicReviewProvider,
    GeminiReviewProvider,
    OpenAIReviewProvider,
)
from app.infrastructure.ai.transports import ScriptedTransport
from app.intelligence.review_summary import (
    DeterministicMockReviewSummarizer,
    InMemoryReviewSummaryRepository,
)
from app.intelligence.review_summary.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)
from app.intelligence.review_summary.orchestrator import MultiModelReviewOrchestrator
from app.intelligence.review_summary.registry import AIProviderRegistry
from app.intelligence.reviews import (
    InMemoryReviewRepository,
    MockAmazonReviewCollector,
    MockLazadaReviewCollector,
    MockShopeeReviewCollector,
    MockTikTokShopReviewCollector,
)
from app.main import create_app
from app.services.review_service import ReviewService
from app.services.review_summary_service import ReviewSummaryService
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 29, 16, 0, tzinfo=UTC)


def _payload(sentiment: str = "very_positive") -> str:
    return json.dumps(
        {
            "product_id": IPHONE_DEMO_PRODUCT_ID,
            "overall_sentiment": sentiment,
            "summary": "Most buyers are satisfied with camera and battery.",
            "pros": [
                {
                    "claim": "Excellent camera",
                    "evidence_review_ids": ["rv-002"],
                    "confidence": 0.9,
                }
            ],
            "cons": [
                {
                    "claim": "Warms under heavy gaming",
                    "evidence_review_ids": ["rv-004"],
                    "confidence": 0.8,
                }
            ],
            "warnings": [
                {
                    "claim": "Some complaints about accessories",
                    "evidence_review_ids": ["rv-013"],
                    "confidence": 0.7,
                }
            ],
            "recommendation": "highly_recommended",
            "confidence": 0.84,
        }
    )


def _build_orchestrator(
    *,
    mode: str = "economy",
    enabled: bool = True,
) -> MultiModelReviewOrchestrator:
    registry = AIProviderRegistry(
        [
            OpenAIReviewProvider(
                api_key="sk-test",
                live_http_enabled=True,
                ai_review_enabled=enabled,
                transport=ScriptedTransport(content=_payload()),
            ),
            ClaudeReviewProvider(
                api_key="sk-test",
                live_http_enabled=True,
                ai_review_enabled=enabled,
                transport=ScriptedTransport(content=_payload("positive")),
            ),
            GeminiReviewProvider(
                api_key="sk-test",
                live_http_enabled=True,
                ai_review_enabled=enabled,
                transport=ScriptedTransport(content=_payload("very_positive")),
            ),
            DeterministicReviewProvider(),
        ]
    )
    return MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=enabled,
        configured_mode=mode,  # type: ignore[arg-type]
        allow_client_mode=True,
        primary_provider="openai",
        secondary_provider="anthropic",
        clock=lambda: FIXED_NOW,
    )


@pytest.fixture
async def multi_client() -> AsyncGenerator[AsyncClient, None]:
    review_repo = InMemoryReviewRepository()
    summary_repo = InMemoryReviewSummaryRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"mm-{counter['n']}"

    review_service = ReviewService(
        review_repo,
        [
            MockShopeeReviewCollector(),
            MockLazadaReviewCollector(),
            MockTikTokShopReviewCollector(),
            MockAmazonReviewCollector(),
        ],
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
        seed_demo_history=False,
    )
    orchestrator = _build_orchestrator(mode="balanced", enabled=True)
    summary_service = ReviewSummaryService(
        summary_repo,
        DeterministicMockReviewSummarizer(),
        review_service,
        orchestrator=orchestrator,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "summary-mm",
        auto_collect=True,
    )
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: review_repo
    app.dependency_overrides[get_review_service] = lambda: review_service
    app.dependency_overrides[get_review_summary_repository] = lambda: summary_repo
    app.dependency_overrides[get_multi_model_review_orchestrator] = lambda: orchestrator
    app.dependency_overrides[get_review_summary_service] = lambda: summary_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_includes_mode_providers_and_evidence(multi_client: AsyncClient) -> None:
    response = await multi_client.get(
        f"/api/v1/review-summary/{IPHONE_DEMO_PRODUCT_ID}?mode=balanced"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == IPHONE_DEMO_PRODUCT_LABEL
    assert body["mode"] == "balanced"
    assert body["providers_used"]
    assert body["fallback_used"] is False
    assert "evidence" in body
    assert body["evidence"]["pros"]
    assert body["evidence"]["pros"][0]["evidence_review_ids"]
    assert body["consensus_confidence"] is not None
    # No secrets in response
    blob = json.dumps(body).lower()
    assert "sk-test" not in blob
    assert "api_key" not in blob
    assert "authorization" not in blob


@pytest.mark.asyncio
async def test_api_mode_ceiling_enforced(multi_client: AsyncClient) -> None:
    # Server configured to balanced; maximum request must be capped.
    response = await multi_client.get("/api/v1/review-summary/demo?mode=maximum")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "balanced"


@pytest.mark.asyncio
async def test_api_disabled_ai_uses_deterministic_fallback() -> None:
    review_repo = InMemoryReviewRepository()
    summary_repo = InMemoryReviewSummaryRepository()
    review_service = ReviewService(
        review_repo,
        [
            MockShopeeReviewCollector(),
            MockLazadaReviewCollector(),
            MockTikTokShopReviewCollector(),
            MockAmazonReviewCollector(),
        ],
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "x1",
        seed_demo_history=False,
    )
    orchestrator = _build_orchestrator(mode="maximum", enabled=False)
    summary_service = ReviewSummaryService(
        summary_repo,
        DeterministicMockReviewSummarizer(),
        review_service,
        orchestrator=orchestrator,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "summary-disabled",
    )
    app = create_app()
    app.dependency_overrides[get_review_summary_service] = lambda: summary_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/review-summary/demo?mode=maximum")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "economy"
    assert body["fallback_used"] is True
    assert "deterministic" in body["providers_used"]
