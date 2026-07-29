"""Unit tests for multi-model AI review providers and validation."""

from __future__ import annotations

import json

import pytest
from app.domain.entities.review_analysis import ReviewAnalysisRequest, ReviewEvidenceItem
from app.domain.exceptions import (
    AIProviderMalformedResponseError,
    AIProviderTimeoutError,
)
from app.infrastructure.ai.review_providers import (
    ClaudeReviewProvider,
    DeterministicReviewProvider,
    GeminiReviewProvider,
    OpenAIReviewProvider,
)
from app.infrastructure.ai.review_providers.parsing import parse_provider_json
from app.infrastructure.ai.transports import ScriptedTransport
from app.intelligence.review_summary.validator import (
    ReviewAnalysisValidator,
    build_review_evidence,
)

REVIEWS = (
    ReviewEvidenceItem("rv-001", "Battery lasts all day."),
    ReviewEvidenceItem("rv-002", "Camera is excellent."),
    ReviewEvidenceItem("rv-003", "Heats during gaming."),
    ReviewEvidenceItem("rv-004", "Accessories in the box felt cheap."),
    ReviewEvidenceItem("rv-005", "Very fast delivery."),
)


def _request() -> ReviewAnalysisRequest:
    return ReviewAnalysisRequest(
        product_id="p1",
        product="Demo Phone",
        reviews=REVIEWS,
        average_rating=4.7,
        total_review_count=1000,
        timeout_seconds=5,
    )


def _valid_payload(**overrides: object) -> str:
    payload = {
        "product_id": "p1",
        "overall_sentiment": "very_positive",
        "summary": "Buyers like the camera and battery.",
        "pros": [
            {
                "claim": "Excellent camera",
                "evidence_review_ids": ["rv-002"],
                "confidence": 0.9,
            },
            {
                "claim": "Long battery life",
                "evidence_review_ids": ["rv-001"],
                "confidence": 0.88,
            },
        ],
        "cons": [
            {
                "claim": "Warms under heavy gaming",
                "evidence_review_ids": ["rv-003"],
                "confidence": 0.8,
            }
        ],
        "warnings": [
            {
                "claim": "Some complaints about accessories",
                "evidence_review_ids": ["rv-004"],
                "confidence": 0.7,
            }
        ],
        "recommendation": "highly_recommended",
        "confidence": 0.86,
    }
    payload.update(overrides)
    return json.dumps(payload)


@pytest.mark.parametrize(
    ("cls", "name"),
    [
        (OpenAIReviewProvider, "openai"),
        (ClaudeReviewProvider, "anthropic"),
        (GeminiReviewProvider, "gemini"),
    ],
)
def test_external_provider_unavailable_without_keys(cls: type, name: str) -> None:
    provider = cls(api_key="", live_http_enabled=True, ai_review_enabled=True)
    assert provider.provider_name == name
    assert provider.is_available() is False
    result = provider.analyze_reviews(_request())
    assert result.status == "unavailable"
    assert result.error_code == "missing_api_key"


@pytest.mark.parametrize("cls", [OpenAIReviewProvider, ClaudeReviewProvider, GeminiReviewProvider])
def test_external_provider_live_http_disabled(cls: type) -> None:
    provider = cls(
        api_key="sk-test",
        live_http_enabled=False,
        ai_review_enabled=True,
        transport=ScriptedTransport(content=_valid_payload()),
    )
    assert provider.is_available() is False
    result = provider.analyze_reviews(_request())
    assert result.status == "unavailable"
    assert result.error_code == "live_http_disabled"


@pytest.mark.parametrize("cls", [OpenAIReviewProvider, ClaudeReviewProvider, GeminiReviewProvider])
def test_external_provider_scripted_success(cls: type) -> None:
    provider = cls(
        api_key="sk-test",
        live_http_enabled=True,
        ai_review_enabled=True,
        transport=ScriptedTransport(content=_valid_payload()),
    )
    assert provider.is_available() is True
    result = provider.analyze_reviews(_request())
    assert result.status == "ok"
    assert result.overall_sentiment == "very_positive"
    assert result.pros[0].evidence_review_ids == ("rv-002",)
    assert result.usage is not None


@pytest.mark.parametrize("cls", [OpenAIReviewProvider, ClaudeReviewProvider, GeminiReviewProvider])
def test_external_provider_timeout(cls: type) -> None:
    provider = cls(
        api_key="sk-test",
        live_http_enabled=True,
        ai_review_enabled=True,
        transport=ScriptedTransport(
            error=AIProviderTimeoutError("x", 0.01),
        ),
    )
    result = provider.analyze_reviews(_request())
    assert result.status == "timeout"


@pytest.mark.parametrize("cls", [OpenAIReviewProvider, ClaudeReviewProvider, GeminiReviewProvider])
def test_external_provider_malformed_output(cls: type) -> None:
    provider = cls(
        api_key="sk-test",
        live_http_enabled=True,
        ai_review_enabled=True,
        transport=ScriptedTransport(content="not-json{"),
    )
    result = provider.analyze_reviews(_request())
    assert result.status == "malformed"


def test_deterministic_provider_always_available() -> None:
    provider = DeterministicReviewProvider()
    assert provider.is_available() is True
    result = provider.analyze_reviews(_request())
    assert result.status == "ok"
    assert result.provider == "deterministic"
    assert result.pros
    assert all(claim.evidence_review_ids for claim in result.pros)


def test_parse_rejects_bare_string_claims() -> None:
    with pytest.raises(AIProviderMalformedResponseError):
        parse_provider_json(
            json.dumps(
                {
                    "overall_sentiment": "positive",
                    "summary": "ok",
                    "pros": ["no evidence"],
                    "cons": [],
                    "warnings": [],
                    "recommendation": "recommended",
                    "confidence": 0.5,
                }
            ),
            provider="openai",
            model="m",
            product_id="p1",
        )


def test_validator_strips_invalid_evidence_and_fabricated_numbers() -> None:
    validator = ReviewAnalysisValidator()
    provider = OpenAIReviewProvider(
        api_key="sk",
        live_http_enabled=True,
        ai_review_enabled=True,
        transport=ScriptedTransport(
            content=_valid_payload(
                pros=[
                    {
                        "claim": "Camera scores 99.9 percent",
                        "evidence_review_ids": ["rv-002"],
                        "confidence": 0.99,
                    },
                    {
                        "claim": "Excellent camera",
                        "evidence_review_ids": ["rv-999"],
                        "confidence": 0.9,
                    },
                    {
                        "claim": "Long battery life",
                        "evidence_review_ids": ["rv-001"],
                        "confidence": 0.9,
                    },
                ]
            )
        ),
    )
    raw = provider.analyze_reviews(_request())
    validated = validator.validate(raw, _request())
    claims = [item.claim for item in validated.pros]
    assert "Long battery life" in claims
    assert "Camera scores 99.9 percent" not in claims
    assert all("rv-999" not in item.evidence_review_ids for item in validated.pros)


def test_build_review_evidence_ids() -> None:
    items = build_review_evidence(["a", "b"])
    assert items[0].review_id == "rv-001"
    assert items[1].text == "b"
