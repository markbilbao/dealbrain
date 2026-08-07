"""Phase 1 public/internal brand boundary tests for PiqSavi + PiqScore.

PUBLIC: PiqSavi / PiqScore
INTERNAL: DealBrain / DealScore

These tests do not require the repository to be free of DealBrain or DealScore.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from app.core.config import Settings
from app.core.public_brand import (
    INTERNAL_CODENAME,
    INTERNAL_SCORE_NAME,
    PUBLIC_BRAND,
    PUBLIC_PERSONAL_SCORE_LABEL,
    PUBLIC_SCORE_NAME,
    PUBLIC_TAGLINE,
    present_consumer_text,
    present_public_brand_text,
    present_public_score_text,
)
from app.main import create_app
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]


def test_public_brand_and_score_constants() -> None:
    assert PUBLIC_BRAND == "PiqSavi"
    assert PUBLIC_TAGLINE == "Your AI Personal Shopper"
    assert INTERNAL_CODENAME == "DealBrain"
    assert PUBLIC_SCORE_NAME == "PiqScore"
    assert INTERNAL_SCORE_NAME == "DealScore"
    assert PUBLIC_PERSONAL_SCORE_LABEL == "Personalized PiqScore"


def test_present_public_brand_text_rewrites_codename_only() -> None:
    assert present_public_brand_text("DealBrain may earn a commission") == (
        "PiqSavi may earn a commission"
    )
    assert present_public_brand_text("DealScore remains DealScore") == (
        "DealScore remains DealScore"
    )
    assert present_public_brand_text("DealBrain's quality threshold") == (
        "PiqSavi's quality threshold"
    )


def test_present_public_score_text_rewrites_score_feature_only() -> None:
    assert present_public_score_text("DealScore of 84") == "PiqScore of 84"
    assert present_public_score_text("tied DealScores") == "tied PiqScores"
    assert present_public_score_text("highest DealScore") == "highest PiqScore"
    assert present_public_score_text("PersonalDealScore is 77") == ("Personalized PiqScore is 77")
    assert present_public_score_text("Personal Deal Score available") == (
        "Personalized PiqScore available"
    )
    assert "PersonalPiqScore" not in present_public_score_text("PersonalDealScore")
    # Machine-like identifiers without DealScore token stay untouched.
    assert present_public_score_text("deal_score=84") == "deal_score=84"
    assert present_public_score_text("dealscore_threshold") == "dealscore_threshold"


def test_present_consumer_text_composes_brand_and_score() -> None:
    text = "DealBrain uses DealScore; PersonalDealScore may also apply."
    assert present_consumer_text(text) == (
        "PiqSavi uses PiqScore; Personalized PiqScore may also apply."
    )
    assert "PersonalPiqScore" not in present_consumer_text(text)


def test_settings_default_app_name_is_piqsavi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://dealbrain:dealbrain@localhost:5432/dealbrain",
    )
    assert settings.app_name == "PiqSavi"


def test_env_examples_set_public_app_name() -> None:
    for relative in (
        ".env.example",
        ".env.staging.example",
        ".env.production.example",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "APP_NAME=PiqSavi" in text
        assert "APP_NAME=DealBrain" not in text


def test_openapi_public_branding_and_x_dealbrain_compat() -> None:
    schema = create_app().openapi()
    info = schema["info"]
    assert info["title"] == "PiqSavi"
    assert "PiqSavi" in info["description"]
    assert "Your AI Personal Shopper" in info["description"]
    assert "PiqScore" in info["description"]
    assert info["contact"]["name"] == "PiqSavi Platform"
    assert info["contact"]["url"] == "https://github.com/markbilbao/dealbrain"
    assert info["x-dealbrain-api-version"] == "v1"
    assert info["x-dealbrain-no-api-v2"] is True
    assert isinstance(info["x-dealbrain-limitations"], list)
    assert info["x-dealbrain-limitations"]
    assert "x-piqsavi-api-version" not in info


@pytest.mark.asyncio
async def test_health_service_uses_public_brand(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["service"] == "PiqSavi"


@pytest.mark.asyncio
async def test_demo_html_presents_piqsavi_and_piqscore(
    client: AsyncClient,
) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    body = response.text
    assert "PiqSavi" in body
    assert PUBLIC_TAGLINE in body
    assert "DealBrain" not in body
    assert "PiqScore" in body
    assert "Personalized PiqScore" in body
    assert "PiqScore Engine" in body
    # Consumer feature labels should not present DealScore; JS identifiers may.
    assert '<div class="label">DealScore</div>' not in body
    assert "<th>DealScore</th>" not in body
    assert "dealbrain.local" in body
    assert "/api/v1/dealscore/search" in body or "dealscore/search" in body
    assert "deal_score" in body
    assert "personal_deal_score" in body


def test_affiliate_disclosure_fixture_uses_public_brand_and_score() -> None:
    from app.affiliate.fixtures import DEFAULT_DISCLOSURES, PLACEHOLDER_MERCHANTS

    general = next(d for d in DEFAULT_DISCLOSURES if d["disclosure_id"] == "disc-general-en")
    amazon = next(d for d in DEFAULT_DISCLOSURES if d["disclosure_id"] == "disc-merchant-amazon")
    assert "PiqSavi may earn" in general["text"]
    assert "DealBrain" not in general["text"]
    assert "PiqScore" in general["text"]
    assert "DealScore" not in general["text"]
    assert "PiqSavi may earn" in amazon["text"]
    templates = " ".join(m["tracking_template"] for m in PLACEHOLDER_MERCHANTS)
    assert "utm_source=dealbrain" in templates or "aff_platform=dealbrain" in templates


def test_auth_email_subjects_use_public_brand() -> None:
    text = (ROOT / "app/auth/service.py").read_text(encoding="utf-8")
    assert 'subject="PiqSavi password reset"' in text
    assert 'subject="Verify your PiqSavi email"' in text
    assert "DealBrain password reset" not in text
    assert "Verify your DealBrain email" not in text


def test_price_history_public_disclaimer_uses_piqsavi() -> None:
    from app.api.v1.mappers.price_history import _DISCLAIMER

    assert "PiqSavi" in _DISCLAIMER
    assert "DealBrain" not in _DISCLAIMER


def test_recommendation_mapper_rewrites_protected_engine_branding() -> None:
    from app.api.v1.mappers.recommendation import _to_recommendation_payload
    from app.domain.entities.recommendation import (
        AlternativeRecommendation,
        PurchaseDecision,
        Recommendation,
        RecommendationConfidence,
        RecommendationReason,
        RecommendationTradeoff,
        RecommendationWarning,
    )

    payload = _to_recommendation_payload(
        Recommendation(
            decision=PurchaseDecision.CONSIDER,
            recommended_listing_id="listing-1",
            headline="DealBrain found a candidate",
            summary="It has a DealScore of 84.",
            reasoning=(RecommendationReason(text="tied DealScores were close."),),
            tradeoffs=(RecommendationTradeoff(text="Trade-off text"),),
            warnings=(RecommendationWarning(text="DealBrain data is limited."),),
            confidence=RecommendationConfidence(value=0.4),
            alternatives=(
                AlternativeRecommendation(
                    listing_id="listing-2",
                    label="Alt",
                    reason="Does not meet DealBrain's threshold.",
                ),
            ),
        )
    )
    assert payload.summary == "It has a PiqScore of 84."
    assert payload.reasoning[0] == "tied PiqScores were close."
    assert "DealBrain" not in payload.warnings[0]
    assert "PiqSavi's threshold" in payload.alternatives[0].reason
    assert payload.decision == PurchaseDecision.CONSIDER.value
    assert payload.confidence == 0.4


def test_dealscore_mapper_presents_piqscore_explanations() -> None:
    from app.api.v1.mappers.dealscore import _to_deal_score_payload
    from app.domain.entities.deal_score import (
        DealRating,
        DealScore,
        DealScoreComponents,
    )

    payload = _to_deal_score_payload(
        DealScore(
            listing_id="listing-1",
            marketplace="lazada",
            score=84.0,
            rating=DealRating.GOOD,
            rank=1,
            total_cost=100.0,
            components=DealScoreComponents(
                price_score=80.0,
                seller_score=80.0,
                shipping_score=80.0,
                availability_score=80.0,
                official_store_score=80.0,
                warranty_score=80.0,
                return_policy_score=80.0,
            ),
            explanation=("Strong DealScore driven by price.",),
            warnings=("DealScore confidence is limited.",),
            applied_weights={"price": 0.4},
        )
    )
    assert payload.score == 84.0
    assert payload.explanation == ["Strong PiqScore driven by price."]
    assert payload.warnings == ["PiqScore confidence is limited."]


def test_openapi_piqscore_human_text_keeps_dealscore_machine_contract() -> None:
    schema = create_app().openapi()
    tags = schema.get("tags", [])
    assert any(tag.get("name") == "dealscore" for tag in tags)
    dealscore_tag = next(tag for tag in tags if tag.get("name") == "dealscore")
    assert "PiqScore" in dealscore_tag.get("description", "")
    assert "/api/v1/dealscore/search" in schema["paths"]
    op = schema["paths"]["/api/v1/dealscore/search"]["get"]
    assert "PiqScore" in op.get("summary", "")
    assert "dealscore" in op.get("operationId", "").lower()
    # Schema component / field machine identifiers remain DealScore/deal_score.
    assert "DealScorePayload" in schema["components"]["schemas"]
    props = schema["components"]["schemas"]["DealScoreResultItem"]["properties"]
    assert "deal_score" in props
    assert props["deal_score"].get("title") == "PiqScore"


def test_internal_score_and_dealbrain_identifiers_preserved() -> None:
    assert (ROOT / "app/intelligence/dealscore/engine.py").is_file()
    engine_text = (ROOT / "app/intelligence/dealscore/engine.py").read_text(encoding="utf-8")
    assert "class WeightedDealScoreEngine" in engine_text

    service_text = (ROOT / "app/services/deal_recommendation_service.py").read_text(
        encoding="utf-8"
    )
    assert "class DealRecommendationService" in service_text

    # Representative machine identifiers remain DealScore/dealscore.
    assert "dealscore_threshold" in (ROOT / "app/domain/entities/alerts.py").read_text(
        encoding="utf-8"
    ) or "dealscore_threshold" in (ROOT / "app/alerts/engine/evaluator.py").read_text(
        encoding="utf-8"
    )

    compose = (ROOT / "infra/compose/docker-compose.production.yml").read_text(encoding="utf-8")
    assert "DEALBRAIN_IMAGE" in compose

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "dealbrain"' in pyproject

    secrets_out = ROOT / "infra/terraform/modules/secrets/outputs.tf"
    assert "dealbrain/" in secrets_out.read_text(encoding="utf-8")

    host_deploy = ROOT / "scripts/deploy/host/dealbrain-staging-deploy.sh"
    assert "/opt/dealbrain" in host_deploy.read_text(encoding="utf-8")

    ssm_vars = ROOT / "infra/terraform/modules/ssm_deploy_document/variables.tf"
    assert "DealBrain-StagingDeploy" in ssm_vars.read_text(encoding="utf-8")

    oidc_test = ROOT / "tests/unit/test_sprint25b5f_immutable_oidc_subject.py"
    assert "markbilbao/dealbrain" in oidc_test.read_text(encoding="utf-8")


def test_protected_dealscore_engine_digest_unchanged() -> None:
    from tests.unit.test_sprint22_protected_modules import PROTECTED_DIGESTS

    relative = "app/intelligence/dealscore/engine.py"
    assert relative in PROTECTED_DIGESTS
    digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    assert digest == PROTECTED_DIGESTS[relative]


def test_notification_center_protected_residual_documented() -> None:
    """Protected notification service may still contain DealBrain/DealScore copy."""
    text = (ROOT / "app/services/notification_center_service.py").read_text(encoding="utf-8")
    assert "DealBrain" in text or "DealScore" in text
    mapper = (ROOT / "app/api/v1/mappers/notifications.py").read_text(encoding="utf-8")
    assert "present_consumer_text" in mapper
