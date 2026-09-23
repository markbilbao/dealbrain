"""Sprint 32 public-web policy audit and PH benchmark harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.research.certification import production_research_provider_certification_catalog
from app.research.philippines_public_web_evidence import (
    philippines_public_web_certification_evidence_catalog,
    philippines_public_web_certification_evidence_records,
    philippines_public_web_provider_ids,
)
from app.research.public_web_benchmark import (
    evaluate_public_web_hit,
    load_public_web_benchmark_intents,
    owner_action_required,
    summarize_public_web_benchmark,
)
from app.research.public_web_policy import (
    BRAVE_WEB_SEARCH_COUNTRY_ENUM_COMPLETE,
    brave_ph_country_parameter_verified,
    brave_web_search_request_params,
    first_live_benchmark_candidates,
    public_web_provider_policy_audits,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from scripts.public_web_ph_benchmark import main as benchmark_main

from tests.unit.production_catalog_boundaries import assert_production_shopify_evidence_only

ROOT = Path(__file__).resolve().parents[2]
RANKING_MODULES = (
    "app/intelligence/dealscore/engine.py",
    "app/intelligence/recommendation/engine.py",
    "app/intelligence/shopping_assistant/recommendation.py",
)


def test_policy_audits_do_not_convert_ambiguity_into_allowed() -> None:
    audits = public_web_provider_policy_audits()
    assert {item.provider_key for item in audits} == {
        "brave_search",
        "tavily_search",
        "exa_search",
    }
    assert first_live_benchmark_candidates() == ("brave_search", "tavily_search")
    for audit in audits:
        assert audit.completeness == "incomplete"
        assert audit.grants_certification is False
        for topic in audit.topics:
            assert topic.state in {"allowed", "restricted", "prohibited", "unknown"}
            if "ambiguous" in topic.notes.casefold() or "not clearly" in topic.notes.casefold():
                assert topic.state != "allowed"
        assert audit.topic_state("current_pricing") == "unknown"


def test_brave_hard_restrictions_are_not_softened() -> None:
    brave = next(
        item for item in public_web_provider_policy_audits() if item.provider_key == "brave_search"
    )
    topics = {item.topic for item in brave.topics}
    assert "ai_llm_use" not in topics
    assert brave.topic_state("caching") == "restricted"
    assert brave.topic_state("model_training_evaluation_improvement") == "prohibited"
    assert brave.topic_state("runtime_ai_llm_grounding_or_inference") == "unknown"
    assert brave.topic_state("runtime_ai_llm_grounding_or_inference") != "prohibited"
    assert brave.topic_state("runtime_ai_llm_grounding_or_inference") != "allowed"
    assert brave.topic_state("api_use") == "allowed"
    assert "third-party" in brave.structured_content_notes.casefold()
    runtime = next(
        item for item in brave.topics if item.topic == "runtime_ai_llm_grounding_or_inference"
    )
    training = next(
        item for item in brave.topics if item.topic == "model_training_evaluation_improvement"
    )
    assert "derivative" in runtime.notes.casefold()
    assert "url-only discovery" in runtime.notes.casefold()
    assert "third-party" in runtime.notes.casefold()
    assert "not a blanket ban" in training.notes.casefold()
    assert "create, evaluate, train" in training.notes.casefold()


def test_tavily_and_exa_runtime_llm_remain_unknown() -> None:
    audits = {item.provider_key: item for item in public_web_provider_policy_audits()}
    for key in ("tavily_search", "exa_search"):
        audit = audits[key]
        assert "ai_llm_use" not in {item.topic for item in audit.topics}
        assert audit.topic_state("model_training_evaluation_improvement") == "unknown"
        assert audit.topic_state("runtime_ai_llm_grounding_or_inference") == "unknown"
        assert audit.topic_state("runtime_ai_llm_grounding_or_inference") != "allowed"


def test_tavily_api_use_is_restricted_not_categorically_forbidden() -> None:
    tavily = next(
        item for item in public_web_provider_policy_audits() if item.provider_key == "tavily_search"
    )
    notes = tavily.topic_state
    assert notes("api_use") == "restricted"
    assert notes("source_site_content_rights") == "unknown"
    assert notes("production_capability_policy") == "unknown"
    api_notes = next(item.notes for item in tavily.topics if item.topic == "api_use")
    assert "Customer Applications" in api_notes
    assert "third-party end users" in api_notes
    assert "not categorically forbidden" in api_notes
    assert "Unrestricted production shopping use is not established" in api_notes


def test_brave_does_not_send_unverified_ph_country_parameter() -> None:
    assert BRAVE_WEB_SEARCH_COUNTRY_ENUM_COMPLETE is False
    assert brave_ph_country_parameter_verified() is False
    query = "iPhone 17 Pro Max Philippines price"
    params = brave_web_search_request_params(query, count=10)
    assert params == {"q": query, "count": 10}
    assert "country" not in params
    assert "search_lang" not in params
    with pytest.raises(ValueError, match="refusing to send country='PH'"):
        brave_web_search_request_params(query, country="PH")
    with pytest.raises(ValueError, match="refusing to send country='US'"):
        brave_web_search_request_params(query, country="US")
    harness = (ROOT / "scripts/public_web_ph_benchmark.py").read_text(encoding="utf-8")
    assert "country=PH" not in harness
    assert '"country": "PH"' not in harness
    assert "brave_web_search_request_params" in harness
    assert '"country": "philippines"' in harness


def test_documentary_public_web_evidence_is_incomplete_and_not_production() -> None:
    records = philippines_public_web_certification_evidence_records()
    catalog = philippines_public_web_certification_evidence_catalog()
    assert len(records) == 3
    assert set(philippines_public_web_provider_ids()) == {
        "ph-brave-search",
        "ph-tavily-search",
        "ph-exa-search",
    }
    assert catalog.list_records() == records
    for record in records:
        assert record.market == "PH"
        assert record.source_scope == "source_agnostic"
        assert record.completeness == "incomplete"
        assert record.grants_certification is False
        assert record.grants_eligibility is False
        assert "search snippet is not canonical price evidence" in record.restrictions
        assert record.test_fixture is False
    assert_production_shopify_evidence_only()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()


def test_benchmark_has_at_least_thirty_ph_intents() -> None:
    intents = load_public_web_benchmark_intents()
    assert len(intents) >= 30
    categories = {item.category for item in intents}
    for required in (
        "smartphones",
        "laptops",
        "cameras",
        "tvs",
        "headphones",
        "appliances",
        "gaming",
        "home electronics",
        "household goods",
        "beauty/personal care",
    ):
        assert required in categories
    assert all("Philippines" in item.query for item in intents)
    assert any(item.kind == "generic_purchase" for item in intents)
    assert any(item.kind == "recognizable_product" for item in intents)


def test_fixture_hits_remain_discovery_only_and_do_not_certify() -> None:
    intents = {item.intent_id: item for item in load_public_web_benchmark_intents()}
    payload = json.loads(
        (ROOT / "tests/fixtures/public_web_benchmark/non_production_search_hits.json").read_text(
            encoding="utf-8"
        )
    )
    assert "NON_PRODUCTION_FIXTURE" in payload["fixture_marker"]
    evaluations = []
    for intent_id, hits in payload["results_by_intent"].items():
        for hit in hits:
            _result, evaluation = evaluate_public_web_hit(
                intent=intents[intent_id],
                provider_key="brave_search",
                source_url=hit["url"],
                title=hit["title"],
                snippet=hit["snippet"],
                test_fixture=True,
            )
            evaluations.append(evaluation)
            assert evaluation.may_enter_evaluated_set is False
            assert evaluation.evidence_tier == "level_d"
            assert evaluation.role == "discovery_only"
            assert evaluation.shipping_evidence == "unknown"
    shopee = next(item for item in evaluations if "shopee.ph" in item.source_url)
    assert shopee.source_kind == "marketplace"
    assert shopee.marketplace_url_not_direct_integration is True
    assert shopee.snippet_only_price is True
    editorial = next(item for item in evaluations if "unbox.ph" in item.source_url)
    assert editorial.source_kind == "review_editorial"
    summary = summarize_public_web_benchmark(
        provider_key="brave_search",
        intents=tuple(intents.values()),
        evaluations=tuple(evaluations),
        requests_made=2,
        live=False,
        fixture=True,
    )
    assert summary.offer_evidence_count == 0
    assert summary.certifies_provider is False
    assert summary.fixture is True


def test_offline_harness_writes_non_secret_artifacts(tmp_path: Path) -> None:
    exit_code = benchmark_main(
        [
            "--provider",
            "brave_search",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "brave_search.json").read_text(encoding="utf-8"))
    assert summary["production_certified"] is False
    assert summary["closes_sprint_32"] is False
    assert summary["scraping"] is False
    assert report["production_certified"] is False
    assert report["summary"]["offer_evidence_count"] == 0
    blob = json.dumps(summary) + json.dumps(report)
    assert "BRAVE_SEARCH_API_KEY" not in blob or "export" in blob
    assert "X-Subscription-Token" not in blob


def test_live_harness_without_credentials_requests_owner_action(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    exit_code = benchmark_main(
        [
            "--provider",
            "brave_search",
            "--live",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 2
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    required = summary["owner_action_required"][0]
    expected = owner_action_required("brave_search")
    assert required["provider"] == "brave_search"
    assert required["credential_needed"] == expected["credential_needed"]
    assert "api-dashboard.search.brave.com" in required["signup_step"]
    assert "Never paste the secret" in required["store_where"]


def test_ranking_modules_are_not_hard_coded_to_search_vendors() -> None:
    for relative in RANKING_MODULES:
        text = (ROOT / relative).read_text(encoding="utf-8").casefold()
        for token in ("brave_search", "tavily", "exa.ai", "exa_search", "commission", "affiliate"):
            assert token not in text, f"{relative} references {token!r}"
