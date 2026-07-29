"""Unit tests for preference engine, scoring, and buying advisor."""

from __future__ import annotations

from app.intelligence.personal.buying_advisor import BuyingAdvisor
from app.intelligence.personal.fixtures import get_demo_profile
from app.intelligence.personal.preference_engine import PreferenceEngine
from app.intelligence.personal.scoring_engine import PersonalScoringEngine
from app.intelligence.shopping_assistant.fixtures import get_product_by_id


def test_preference_scores_are_normalized_and_weighted() -> None:
    engine = PreferenceEngine()
    profile = get_demo_profile("profile-gaming-enthusiast")
    assert profile is not None
    product = get_product_by_id("sa-laptop-tuf-a15")
    assert product is not None
    result = engine.score(profile, product)
    assert 0.0 <= result.total_score <= 1.0
    assert abs(sum(d.weight for d in result.dimensions) - 1.0) < 1e-6
    assert abs(sum(d.weighted_score for d in result.dimensions) - result.total_score) < 1e-6
    assert result.confidence_band in {"High", "Medium", "Low"}


def test_disliked_brand_reduces_brand_affinity() -> None:
    engine = PreferenceEngine()
    profile = get_demo_profile("profile-apple-fan")
    assert profile is not None
    samsung = get_product_by_id("sa-phone-galaxy-s25-ultra")
    apple = get_product_by_id("sa-laptop-macbook-air-m3")
    assert samsung and apple
    disliked = engine.score(profile, samsung)
    liked = engine.score(profile, apple)
    brand_disliked = next(d for d in disliked.dimensions if d.dimension == "brand_affinity")
    brand_liked = next(d for d in liked.dimensions if d.dimension == "brand_affinity")
    assert brand_liked.score > brand_disliked.score
    assert brand_disliked.score < 0.2


def test_budget_student_prefers_cheaper_products() -> None:
    engine = PreferenceEngine()
    profile = get_demo_profile("profile-budget-student")
    assert profile is not None
    pixel = get_product_by_id("sa-phone-pixel-9")
    iphone = get_product_by_id("sa-phone-iphone-16-pro")
    assert pixel and iphone
    cheap = engine.score(profile, pixel)
    expensive = engine.score(profile, iphone)
    assert cheap.total_score >= expensive.total_score


def test_personal_deal_score_composes_global_dealscore() -> None:
    scoring = PersonalScoringEngine()
    profile = get_demo_profile("profile-gaming-enthusiast")
    product = get_product_by_id("sa-laptop-loq-15")
    assert profile and product
    score = scoring.score(profile, product)
    assert 0.0 <= score.personal_deal_score <= 100.0
    assert score.global_deal_score == product["deal_score"]
    assert score.factors
    assert "preference_fit=" in score.factors[1]


def test_buying_advisor_flags_disliked_brand() -> None:
    advisor = BuyingAdvisor()
    profile = get_demo_profile("profile-android-fan")
    product = get_product_by_id("sa-laptop-macbook-air-m3")
    assert profile and product
    advice = advisor.advise(profile, product)
    assert advice.verdict == "not_recommended"
    assert advice.label == "Not recommended"
    assert advice.explanation


def test_buying_advisor_excellent_or_good_for_strong_fit() -> None:
    advisor = BuyingAdvisor()
    profile = get_demo_profile("profile-gaming-enthusiast")
    product = get_product_by_id("sa-laptop-loq-15")
    assert profile and product
    advice = advisor.advise(profile, product)
    assert advice.verdict in {"excellent_choice", "good_value", "price_likely_to_drop"}
    assert advice.personal_deal_score is not None


def test_missing_optional_signals_stay_neutral() -> None:
    engine = PreferenceEngine()
    profile = get_demo_profile("profile-minimalist-buyer")
    product = get_product_by_id("sa-phone-pixel-9")
    assert profile and product
    result = engine.score(profile, product)
    community = next(d for d in result.dimensions if d.dimension == "community_sentiment")
    graph = next(d for d in result.dimensions if d.dimension == "knowledge_graph_proximity")
    assert community.score == 0.5
    assert graph.score == 0.5
