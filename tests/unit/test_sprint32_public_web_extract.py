"""Sprint 32 Tavily Extract technical Level-B harness — not certification."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.domain.entities.public_web_shopping_evidence import (
    SNIPPET_NOT_CANONICAL_PRICE,
    classify_search_hit_as_discovery,
)
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.public_web_extract import (
    DEFAULT_EXTRACT_OUTPUT_DIR,
    DEFAULT_SEARCH_REPORT_PATH,
    LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE,
    LIVE_EXTRACT_PRIVATE_WARNING,
    MAX_EXTRACT_SAMPLE_URLS,
    MISSING_SEARCH_REPORT_MESSAGE,
    PRIVATE_LOCAL_LIVE_ARTIFACT,
    REPOSITORY_ROOT,
    TAVILY_EXTRACT_ENDPOINT,
    TAVILY_EXTRACT_MAX_URLS_PER_REQUEST,
    TECHNICAL_LEVEL_B_CANDIDATE,
    ExtractSampleError,
    LiveExtractOutputInsideRepositoryError,
    MissingSearchReportError,
    assert_artifact_has_no_secrets,
    assert_live_extract_output_outside_repository,
    detect_price_candidate,
    documented_basic_extract_credit_max,
    evaluate_extracted_page,
    hits_from_search_report,
    is_excluded_marketplace_url,
    live_extract_output_is_inside_repository,
    load_search_report,
    refuse_uncertified_extract_price,
    resolve_live_extract_output_dir,
    select_extract_sample,
    select_extract_sample_from_report,
    unknown_shipping_money_line,
)
from app.research.public_web_policy import public_web_provider_policy_audits
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from scripts.public_web_ph_benchmark import (
    LIVE_ENDPOINTS,
)
from scripts.public_web_ph_benchmark import (
    main as benchmark_main,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_REPORT = (
    ROOT / "tests/fixtures/public_web_benchmark/non_production_tavily_search_report.json"
)
RETRIEVED = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
PRODUCT_PAGE = "https://www.powermaccenter.com/products/iphone-17-pro-max"


def _fixture_payload() -> dict:
    payload = json.loads(FIXTURE_REPORT.read_text(encoding="utf-8"))
    assert "NON_PRODUCTION_FIXTURE" in payload["fixture_marker"]
    return payload


def _clean_extract_text() -> str:
    return (
        "# iPhone 17 Pro Max 256GB\n"
        "Power Mac Center official product page.\n"
        "Current price PHP 89990.\n"
        "In stock. Free shipping on selected items.\n"
        "SKU PMC-IP17PM-256. Add to cart.\n"
        "Product details and specifications."
    )


def test_extract_sample_excludes_marketplaces_and_respects_max() -> None:
    hits = hits_from_search_report(_fixture_payload())
    selected = select_extract_sample(hits)
    urls = [item.source_url for item in selected]
    assert len(selected) <= MAX_EXTRACT_SAMPLE_URLS
    assert len(urls) == len(set(urls))
    assert all(not is_excluded_marketplace_url(url) for url in urls)
    assert all(
        token not in " ".join(urls) for token in ("shopee.", "lazada.", "tiktok.com", "amazon.")
    )
    assert all(
        item.source_kind in {"direct_retailer", "manufacturer", "authorized_reseller"}
        for item in selected
    )
    assert "https://unbox.ph/best-wireless-earbuds-under-5000" not in urls
    assert "https://www.powermaccenter.com/collections/iphone" not in urls
    assert "https://www.google.com/search?q=iphone+17+pro+max+philippines" not in urls
    assert PRODUCT_PAGE in urls
    categories = {item.category for item in selected}
    assert len(categories) >= 4
    with pytest.raises(ExtractSampleError, match="first extract benchmark max"):
        select_extract_sample(hits, max_urls=MAX_EXTRACT_SAMPLE_URLS + 1)


def test_direct_retailer_selection_prefers_clean_product_pages() -> None:
    selected = select_extract_sample_from_report(FIXTURE_REPORT)
    kinds = {item.source_kind for item in selected}
    assert "marketplace" not in kinds
    assert "review_editorial" not in kinds
    assert "direct_retailer" in kinds
    assert "manufacturer" in kinds
    assert 12 <= len(selected) <= 15


def test_missing_search_report_fails_without_fabricating_urls(tmp_path: Path) -> None:
    missing = tmp_path / "absent" / "tavily_search.json"
    with pytest.raises(MissingSearchReportError, match="Do not fabricate URLs"):
        load_search_report(missing)
    exit_code = benchmark_main(
        [
            "--provider",
            "tavily_search",
            "--extract-live",
            "--search-report",
            str(missing),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    assert exit_code == 2
    summary = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert summary["production_certified"] is False
    assert summary["closes_sprint_32"] is False
    assert MISSING_SEARCH_REPORT_MESSAGE in summary["owner_action_required"][0]["reason"]


def test_extract_live_requires_tavily_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    exit_code = benchmark_main(
        [
            "--provider",
            "tavily_search",
            "--extract-live",
            "--search-report",
            str(FIXTURE_REPORT),
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 2
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    required = summary["owner_action_required"][0]
    assert required["credential_needed"] == "TAVILY_API_KEY"
    assert "Never paste the secret" in required["store_where"]
    selected = json.loads((tmp_path / "selected_urls.json").read_text(encoding="utf-8"))
    assert selected["selected_count"] <= MAX_EXTRACT_SAMPLE_URLS
    assert "tvly-" not in json.dumps(summary) + json.dumps(selected)


def test_select_only_writes_git_ignored_default_style_artifacts(tmp_path: Path) -> None:
    exit_code = benchmark_main(
        [
            "--provider",
            "tavily_search",
            "--extract-select-only",
            "--search-report",
            str(FIXTURE_REPORT),
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    selected = json.loads((tmp_path / "selected_urls.json").read_text(encoding="utf-8"))
    assert summary["live"] is False
    assert summary["scraping"] is False
    assert selected["raw_content"] if False else selected.get("raw_content") is None
    blob = json.dumps(summary) + json.dumps(selected)
    assert "raw_content" not in selected
    assert "TAVILY_API_KEY" not in blob or "export" in blob
    assert "Authorization" not in blob
    assert Path("/tmp/piqsavi-tavily-extract-ph") == DEFAULT_EXTRACT_OUTPUT_DIR
    assert Path("/tmp/piqsavi-tavily-ph/tavily_search.json") == DEFAULT_SEARCH_REPORT_PATH
    assert str(DEFAULT_EXTRACT_OUTPUT_DIR).startswith("/tmp/")
    assert ROOT not in DEFAULT_EXTRACT_OUTPUT_DIR.parents


def test_raw_content_is_not_persisted_by_default() -> None:
    evaluation = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content=_clean_extract_text(),
        retrieved_at=RETRIEVED,
        extraction_succeeded=True,
        test_fixture=True,
    )
    payload = evaluation.to_dict()
    assert "raw_content" not in payload
    assert payload["extracted_content_length"] == len(_clean_extract_text())
    assert payload["content_hash"] is not None
    assert payload["content_hash"].startswith("sha256:")


def test_technical_level_b_candidate_is_not_offer_evidence() -> None:
    evaluation = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content=_clean_extract_text(),
        retrieved_at=RETRIEVED,
        extraction_succeeded=True,
        test_fixture=True,
    )
    assert evaluation.technical_level_b_candidate is True
    assert evaluation.technical_level_b_reason == TECHNICAL_LEVEL_B_CANDIDATE
    assert evaluation.offer_evidence is False
    assert evaluation.may_enter_evaluated_set is False
    assert evaluation.canonical_price_created is False
    assert evaluation.policy.policy_allowed is False
    assert evaluation.policy.source_site_content_rights == "unknown"
    assert evaluation.policy.production_capability_policy == "unknown"
    assert evaluation.to_dict()["offer_evidence"] is False
    assert evaluation.to_dict()["may_enter_evaluated_set"] is False


def test_unknown_source_policy_blocks_evaluated_set_even_if_source_marked_allowed() -> None:
    evaluation = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content=_clean_extract_text(),
        retrieved_at=RETRIEVED,
        extraction_succeeded=True,
        source_site_policy="allowed",
        test_fixture=True,
    )
    assert evaluation.policy.source_site_content_rights == "allowed"
    assert evaluation.policy.production_capability_policy == "unknown"
    assert evaluation.policy.policy_allowed is False
    assert evaluation.may_enter_evaluated_set is False
    assert evaluation.offer_evidence is False


def test_ambiguous_numeric_text_is_not_canonical_price() -> None:
    installment = detect_price_candidate(
        "iPhone 17 Pro Max available at ₱3749/mo installment for 24 months to pay."
    )
    assert installment.price_candidate_detected is True
    assert installment.price_appears_attributable is False
    assert installment.ambiguity_reason is not None
    voucher = detect_price_candidate("Use voucher to save PHP 2000. 20% off today.")
    assert voucher.price_appears_attributable is False
    msrp = detect_price_candidate("MSRP PHP 99990. Recommended retail only.")
    assert msrp.price_appears_attributable is False
    evaluation = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content="iPhone 17 Pro Max. Pay PHP 3749 monthly installment.",
        retrieved_at=RETRIEVED,
        extraction_succeeded=True,
        test_fixture=True,
    )
    assert evaluation.technical_level_b_candidate is False
    assert evaluation.canonical_price_created is False
    line = refuse_uncertified_extract_price(
        classify_search_hit_as_discovery(
            query_id="tavily-extract-ph",
            discovery_provider_id="tavily_search",
            source_url=PRODUCT_PAGE,
            php_price_text="PHP 3749",
            test_fixture=True,
        )
    )
    assert line.status == "unknown"
    assert line.amount_minor is None
    assert line.applied is False
    assert line.label == SNIPPET_NOT_CANONICAL_PRICE


def test_unknown_shipping_is_not_zero_or_free() -> None:
    evaluation = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content=_clean_extract_text(),
        retrieved_at=RETRIEVED,
        extraction_succeeded=True,
        test_fixture=True,
    )
    assert evaluation.shipping_text_present is True
    assert evaluation.shipping_evidence == "unknown"
    shipping = unknown_shipping_money_line()
    assert shipping.status == "unknown"
    assert shipping.amount_minor is None
    assert shipping.applied is False


def test_no_direct_merchant_http_in_benchmark_implementation() -> None:
    files = (
        ROOT / "app/research/public_web_extract.py",
        ROOT / "app/research/public_web_benchmark.py",
        ROOT / "scripts/public_web_ph_benchmark.py",
    )
    forbidden_hosts = (
        "shopee.",
        "lazada.",
        "tiktok.com",
        "amazon.com",
        "powermaccenter.com",
        "abenson.com",
        "samsung.com",
        "sony.com",
    )
    allowed = {
        "https://api.search.brave.com/res/v1/web/search",
        "https://api.tavily.com/search",
        "https://api.tavily.com/extract",
        "https://api.exa.ai/search",
    }
    assert set(LIVE_ENDPOINTS.values()) == allowed
    assert TAVILY_EXTRACT_ENDPOINT == "https://api.tavily.com/extract"
    assert TAVILY_EXTRACT_MAX_URLS_PER_REQUEST == 20
    for path in files:
        text = path.read_text(encoding="utf-8")
        for host in forbidden_hosts:
            for prefix in (f"https://{host}", f"http://{host}", f"https://www.{host}"):
                if prefix in text:
                    assert "httpx" not in text[max(0, text.find(prefix) - 80) : text.find(prefix)]
        assert "httpx.get(" not in text or "api.search.brave.com" in text
    extract_source = (ROOT / "app/research/public_web_extract.py").read_text(encoding="utf-8")
    assert "httpx" not in extract_source
    assert TAVILY_EXTRACT_ENDPOINT in extract_source
    harness = (ROOT / "scripts/public_web_ph_benchmark.py").read_text(encoding="utf-8")
    assert "TAVILY_EXTRACT_ENDPOINT" in harness
    assert "extract_depth" in harness
    assert "advanced_not_run" in harness
    assert "httpx.post(" in harness
    assert "httpx.get(" in harness
    assert "shopee.ph" not in harness
    assert "powermaccenter.com" not in harness


def test_production_catalogs_stay_empty() -> None:
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()


def test_failed_or_snippet_like_extract_is_not_level_b() -> None:
    failed = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content=None,
        retrieved_at=RETRIEVED,
        extraction_succeeded=False,
        test_fixture=True,
    )
    assert failed.technical_level_b_candidate is False
    assert failed.extraction_succeeded is False
    short = evaluate_extracted_page(
        source_url=PRODUCT_PAGE,
        raw_content="iPhone",
        retrieved_at=RETRIEVED,
        extraction_succeeded=True,
        test_fixture=True,
    )
    assert short.technical_level_b_candidate is False


def test_artifact_secret_guard_rejects_key_material() -> None:
    with pytest.raises(RuntimeError, match="credential"):
        assert_artifact_has_no_secrets({"note": "super-secret-key"}, ("super-secret-key",))
    with pytest.raises(RuntimeError, match="Tavily key"):
        assert_artifact_has_no_secrets({"note": "tvly-abc123"}, ())
    assert_artifact_has_no_secrets({"policy": "unknown", "output_dir": "/tmp/x"}, ())


def test_documented_credit_ceiling_for_basic_extract() -> None:
    assert documented_basic_extract_credit_max(12) == 3
    assert documented_basic_extract_credit_max(15) == 3
    assert documented_basic_extract_credit_max(5) == 1


def test_tavily_terms_do_not_categorically_forbid_shopper_facing_use() -> None:
    tavily = next(
        item for item in public_web_provider_policy_audits() if item.provider_key == "tavily_search"
    )
    api_use = next(item for item in tavily.topics if item.topic == "api_use")
    assert api_use.state == "restricted"
    assert api_use.state != "allowed"
    notes = api_use.notes.casefold()
    assert "customer applications" in notes
    assert "third-party end users" in notes
    assert "not categorically forbidden" in notes
    assert "unrestricted production" in notes
    assert tavily.topic_state("source_site_content_rights") == "unknown"
    assert tavily.topic_state("production_capability_policy") == "unknown"
    assert tavily.topic_state("content_retrieval") == "unknown"
    assert "shopper-facing piqsavi use is not clearly the same" not in tavily.notes.casefold()
    assert PRIVATE_LOCAL_LIVE_ARTIFACT == "PRIVATE_LOCAL_LIVE_ARTIFACT"


def _extract_live_args(output_dir: Path, *, persist_raw: bool = False) -> list[str]:
    args = [
        "--provider",
        "tavily_search",
        "--extract-live",
        "--search-report",
        str(FIXTURE_REPORT),
        "--output-dir",
        str(output_dir),
    ]
    if persist_raw:
        args.append("--persist-raw")
    return args


def test_live_extract_rejects_repo_root_output(monkeypatch, capsys) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    exit_code = benchmark_main(_extract_live_args(ROOT))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_PRIVATE_WARNING in captured.out
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not (ROOT / "summary.json").exists()
    assert not (ROOT / "tavily_extract.json").exists()
    assert not (ROOT / "selected_urls.json").exists()


def test_live_extract_rejects_nested_repo_output_path(monkeypatch, capsys) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    nested = ROOT / "docs" / "live-tavily"
    exit_code = benchmark_main(_extract_live_args(nested))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not nested.exists()


def test_live_extract_accepts_tmp_style_outside_repo_output(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    outside = tmp_path / "piqsavi-tavily-extract-ph"
    assert live_extract_output_is_inside_repository(outside) is False
    assert assert_live_extract_output_outside_repository(outside) == outside.expanduser().resolve()
    exit_code = benchmark_main(_extract_live_args(outside))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_PRIVATE_WARNING in captured.out
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE not in captured.out
    assert (outside / "summary.json").exists()
    assert (outside / "selected_urls.json").exists()
    assert not (outside / "raw").exists()


def test_live_extract_path_resolution_prevents_relative_bypass(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.chdir(ROOT)
    relative_inside = Path("./tmp-output")
    assert live_extract_output_is_inside_repository(relative_inside) is True
    with pytest.raises(LiveExtractOutputInsideRepositoryError):
        assert_live_extract_output_outside_repository(relative_inside)
    exit_code = benchmark_main(_extract_live_args(relative_inside))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not (ROOT / "tmp-output").exists()

    relative_nested = Path("docs/live-tavily")
    assert live_extract_output_is_inside_repository(relative_nested) is True
    exit_code = benchmark_main(_extract_live_args(relative_nested))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not (ROOT / "docs" / "live-tavily").exists()

    relative_outside = Path(os.path.relpath(tmp_path / "outside-extract", start=ROOT))
    assert live_extract_output_is_inside_repository(relative_outside) is False
    exit_code = benchmark_main(_extract_live_args(relative_outside))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE not in captured.out
    assert (tmp_path / "outside-extract" / "summary.json").exists()

    link_into_repo = tmp_path / "link-into-docs"
    link_into_repo.symlink_to(ROOT / "docs")
    linked_live = link_into_repo / "live-tavily"
    assert live_extract_output_is_inside_repository(linked_live) is True
    resolved = resolve_live_extract_output_dir(linked_live)
    assert ROOT.resolve() in resolved.parents
    exit_code = benchmark_main(_extract_live_args(linked_live))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not (ROOT / "docs" / "live-tavily").exists()


def test_persist_raw_cannot_bypass_outside_repo_rule(monkeypatch, capsys) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    nested = ROOT / "artifacts" / "tavily"
    exit_code = benchmark_main(_extract_live_args(nested, persist_raw=True))
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_EXTRACT_PRIVATE_WARNING in captured.out
    assert LIVE_EXTRACT_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not nested.exists()
    assert not (nested / "raw").exists()
    assert ROOT.resolve() == REPOSITORY_ROOT
