"""Sprint 32 Shopify Global Catalog PH coverage probe — not certification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_ph_probe import (
    AFFILIATE_FORBIDDEN_REQUEST_KEYS,
    AGENT_PROFILE_NOT_PIQSAVI_IDENTITY,
    AGENT_PROFILE_USAGE,
    ANONYMOUS_AUTH_TIER,
    ANONYMOUS_USER_AGENT,
    CONTEXT_LANGUAGE,
    DEFAULT_FIXTURE,
    DEFAULT_OUTPUT_DIR,
    FIRST_PAGE_LIMIT,
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    GLOBAL_CATALOG_ENDPOINT,
    INFERRED_FIELD_PATHS,
    LIVE_OUTPUT_INSIDE_REPO_MESSAGE,
    MAX_GET_PRODUCT_VALIDATIONS,
    MAX_SEARCH_CATALOG_QUERIES,
    NO_USEFUL_PH_RESULT,
    NON_PRODUCTION_FIXTURE_MARKER,
    OFFER_VIEW,
    PARTIAL_PH_RESULT,
    PH_COUNTRY,
    PHP_CURRENCY,
    REPOSITORY_ROOT,
    SEARCH_TOOL,
    TECHNICAL_TEST_AGENT_PROFILE,
    TECHNICAL_TEST_ONLY,
    USEFUL_PH_OFFER,
    LiveProbeOutputInsideRepositoryError,
    PhProbeIntent,
    ProbeContractError,
    ProbeLimitError,
    ProbeResponseError,
    anonymous_http_headers,
    assert_live_probe_output_outside_repository,
    build_get_product_arguments,
    build_jsonrpc_request,
    build_search_catalog_arguments,
    classify_query_offers,
    coverage_flags,
    fixture_transport_from_payload,
    inferred_fields_observed,
    live_probe_output_is_inside_repository,
    load_ph_probe_intents,
    load_probe_fixture,
    minimize_offer_evidence,
    offers_from_products,
    products_from_catalog_payload,
    resolve_live_probe_output_dir,
    run_ph_coverage_probe,
    select_promising_product_ids,
    source_offer_fields_observed,
    validate_catalog_tool_response,
)
from scripts.shopify_global_catalog_ph_probe import main as probe_main
from scripts.shopify_global_catalog_ph_probe import post_anonymous_catalog

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
PROBE_DOC = ROOT / "docs/roadmap/evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md"
RANKING_MODULES = (
    "app/intelligence/dealscore/engine.py",
    "app/intelligence/recommendation/engine.py",
    "app/intelligence/shopping_assistant/recommendation.py",
)
EXPECTED_CLASSIFICATIONS = {
    "wireless_earbuds": USEFUL_PH_OFFER,
    "gaming_laptop": PARTIAL_PH_RESULT,
    "mechanical_keyboard": NO_USEFUL_PH_RESULT,
    "usb_c_charger": USEFUL_PH_OFFER,
    "phone_case": PARTIAL_PH_RESULT,
    "portable_power_bank": NO_USEFUL_PH_RESULT,
    "skincare_serum": USEFUL_PH_OFFER,
    "running_shoes": PARTIAL_PH_RESULT,
    "backpack": USEFUL_PH_OFFER,
    "air_fryer": NO_USEFUL_PH_RESULT,
    "coffee_grinder": PARTIAL_PH_RESULT,
    "home_office_chair": USEFUL_PH_OFFER,
}


def _fixture() -> dict:
    payload = load_probe_fixture(DEFAULT_FIXTURE)
    assert NON_PRODUCTION_FIXTURE_MARKER in payload["fixture_marker"]
    return payload


def _run_fixture_probe():
    transport = fixture_transport_from_payload(_fixture())
    report = run_ph_coverage_probe(transport=transport, live=False)
    return transport, report


def test_ph_request_shape_uses_documented_localization_and_offer_view() -> None:
    arguments = build_search_catalog_arguments("wireless earbuds")
    catalog = arguments["catalog"]
    assert catalog["query"] == "wireless earbuds"
    assert catalog["filters"]["ships_to"]["country"] == PH_COUNTRY
    assert catalog["filters"]["available"] is True
    assert catalog["context"]["address_country"] == PH_COUNTRY
    assert catalog["context"]["currency"] == PHP_CURRENCY
    assert catalog["context"]["language"] == CONTEXT_LANGUAGE
    assert catalog["view"] == OFFER_VIEW
    assert catalog["pagination"] == {"limit": FIRST_PAGE_LIMIT}
    assert "cursor" not in catalog["pagination"]
    assert arguments["meta"]["ucp-agent"]["profile"] == TECHNICAL_TEST_AGENT_PROFILE
    for key in AFFILIATE_FORBIDDEN_REQUEST_KEYS:
        assert key not in catalog
    request = build_jsonrpc_request(SEARCH_TOOL, arguments, request_id=1)
    assert request["params"]["name"] == SEARCH_TOOL
    assert request["method"] == "tools/call"


def test_get_product_is_single_id_with_ph_context_and_without_offer_view() -> None:
    arguments = build_get_product_arguments("gid://shopify/p/fixture-ph-chair")
    catalog = arguments["catalog"]
    assert catalog["id"] == "gid://shopify/p/fixture-ph-chair"
    assert "ids" not in catalog
    assert catalog["filters"]["ships_to"]["country"] == PH_COUNTRY
    assert catalog["context"]["address_country"] == PH_COUNTRY
    assert catalog["context"]["currency"] == PHP_CURRENCY
    assert catalog.get("view") != OFFER_VIEW
    assert "pagination" not in catalog
    with pytest.raises(ProbeContractError, match="exactly one product id"):
        build_get_product_arguments("gid://a,gid://b")
    with pytest.raises(ProbeContractError, match="lookup_catalog"):
        build_jsonrpc_request(FORBIDDEN_LOOKUP_TOOL, arguments, request_id=2)


def test_anonymous_mode_requires_no_credentials_and_marks_fixture_profile() -> None:
    headers = anonymous_http_headers()
    assert "Authorization" not in headers
    assert AGENT_PROFILE_USAGE == TECHNICAL_TEST_ONLY
    assert AGENT_PROFILE_NOT_PIQSAVI_IDENTITY is True
    assert ANONYMOUS_AUTH_TIER == "Anonymous"
    assert "valid-with-capabilities.json" in TECHNICAL_TEST_AGENT_PROFILE
    assert "shopify.dev/ucp/agent-profiles" in TECHNICAL_TEST_AGENT_PROFILE
    assert GLOBAL_CATALOG_ENDPOINT == "https://catalog.shopify.com/api/ucp/mcp"


def test_anonymous_http_headers_include_explicit_probe_user_agent() -> None:
    headers = anonymous_http_headers()
    assert headers == {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PiqSavi-Sprint32-PH-Coverage-Probe/1.0",
    }
    assert ANONYMOUS_USER_AGENT == "PiqSavi-Sprint32-PH-Coverage-Probe/1.0"
    assert headers["User-Agent"] == ANONYMOUS_USER_AGENT
    assert "Authorization" not in headers
    assert not any("signature" in key.casefold() for key in headers)
    assert not any(key.casefold().startswith("signature") for key in headers)
    module = (ROOT / "app/research/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    for blob in (module, script, headers["User-Agent"]):
        assert "ucp-cli" not in blob.casefold()
        assert "@shopify/ucp-cli" not in blob.casefold()


def test_live_transport_sends_anonymous_http_headers(monkeypatch) -> None:
    import httpx

    captured: dict[str, object] = {}

    class _DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"structuredContent": {"products": []}},
            }

    def fake_post(url, json, headers, timeout):  # noqa: A002
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["json"] = json
        return _DummyResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    payload = post_anonymous_catalog({"jsonrpc": "2.0", "id": 1}, timeout=5.0)
    assert captured["url"] == GLOBAL_CATALOG_ENDPOINT
    assert captured["headers"] == anonymous_http_headers()
    assert captured["headers"]["User-Agent"] == ANONYMOUS_USER_AGENT
    assert "Authorization" not in captured["headers"]
    assert payload["result"]["structuredContent"]["products"] == []
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    assert "headers = anonymous_http_headers()" in script


def test_query_set_is_twelve_ph_intents_without_apple_samsung_bias() -> None:
    intents = load_ph_probe_intents()
    assert len(intents) == MAX_SEARCH_CATALOG_QUERIES == 12
    queries = [item.query for item in intents]
    assert queries == [
        "wireless earbuds",
        "gaming laptop",
        "mechanical keyboard",
        "USB-C charger",
        "phone case",
        "portable power bank",
        "skincare serum",
        "running shoes",
        "backpack",
        "air fryer",
        "coffee grinder",
        "home office chair",
    ]
    blob = " ".join(queries).casefold()
    assert "iphone" not in blob
    assert "apple" not in blob
    assert "samsung" not in blob
    assert "galaxy" not in blob


def test_fixture_probe_enforces_search_and_get_product_caps() -> None:
    transport, report = _run_fixture_probe()
    assert report.search_calls == 12
    assert report.get_product_calls == 5
    assert report.get_product_calls <= MAX_GET_PRODUCT_VALIDATIONS
    assert report.lookup_catalog_calls == 0
    assert report.pagination_followed is False
    assert report.bulk_ids_used is False
    tools = [name for name, _arguments in transport.calls]
    assert tools.count(SEARCH_TOOL) == 12
    assert tools.count(GET_PRODUCT_TOOL) == 5
    assert FORBIDDEN_LOOKUP_TOOL not in tools
    get_ids = [
        arguments["catalog"]["id"]
        for name, arguments in transport.calls
        if name == GET_PRODUCT_TOOL
    ]
    assert len(get_ids) == len(set(get_ids)) == 5
    assert "gid://shopify/p/fixture-ph-chair" in get_ids
    assert "gid://shopify/p/7f3a2b8c1d9e" not in get_ids
    get_query_ids = [
        item.query_id for item in report.query_results if item.get_product_used
    ]
    assert len(get_query_ids) == len(set(get_query_ids)) == 5
    for _name, arguments in transport.calls:
        catalog = arguments["catalog"]
        assert "cursor" not in (catalog.get("pagination") or {})
        assert "ids" not in catalog
        assert "catalog_id" not in catalog


def test_classification_rules_and_inferred_field_distinction() -> None:
    _transport, report = _run_fixture_probe()
    by_id = {item.query_id: item for item in report.query_results}
    assert {key: item.classification for key, item in by_id.items()} == EXPECTED_CLASSIFICATIONS
    useful = by_id["wireless_earbuds"]
    assert useful.identifiable_product is True
    assert useful.price_present is True
    assert useful.identifiable_seller is True
    assert useful.destination_present is True
    assert useful.usable_for_comparison is True
    inferred = useful.offers[0].inferred_fields_observed
    source = useful.offers[0].source_offer_fields_observed
    assert "description" in inferred
    assert "options" in inferred
    assert "metadata.top_features" in inferred
    assert "variants[].condition" in inferred
    assert "product.id" in source
    assert "variant.price" in source
    assert "variant.seller" in source
    assert set(inferred).isdisjoint(source)
    assert set(inferred) <= set(INFERRED_FIELD_PATHS)
    chair = by_id["home_office_chair"]
    assert chair.get_product_used is True
    assert chair.classification == USEFUL_PH_OFFER
    placeholder = by_id["portable_power_bank"]
    assert placeholder.classification == NO_USEFUL_PH_RESULT
    assert placeholder.offers[0].placeholder_or_test is True
    empty = by_id["mechanical_keyboard"]
    assert empty.classification == NO_USEFUL_PH_RESULT
    assert empty.product_returned is False


def test_classify_does_not_fabricate_missing_offer_fields() -> None:
    product = {"id": "gid://shopify/p/partial"}
    offers = offers_from_products([product])
    assert offers[0].price_present is False
    assert offers[0].seller_identity is None
    assert offers[0].currency is None
    assert offers[0].usable_for_comparison is False
    assert classify_query_offers(offers) == PARTIAL_PH_RESULT
    assert classify_query_offers(()) == NO_USEFUL_PH_RESULT
    useful = minimize_offer_evidence(
        {
            "id": "gid://shopify/p/ok",
            "url": "https://fixture-ok.example.invalid/products/ok",
        },
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 1000, "currency": "PHP"},
            "checkout_url": "https://fixture-ok.example.invalid/cart/ok:1",
            "availability": {"available": True, "status": "in_stock"},
            "seller": {
                "name": "Fixture OK",
                "domain": "fixture-ok.example.invalid",
                "url": "https://fixture-ok.example.invalid",
            },
        },
    )
    assert useful.usable_for_comparison is True
    assert useful.price_amount_minor == 1000
    assert useful.currency == "PHP"
    assert classify_query_offers((useful,)) == USEFUL_PH_OFFER


def _complete_product(product_id: str, *, currency: str = "USD") -> dict:
    slug = product_id.rsplit("/", 1)[-1]
    return {
        "id": product_id,
        "url": f"https://fixture.example.invalid/products/{slug}",
        "variants": [
            {
                "id": f"{product_id}-variant",
                "price": {"amount": 1000, "currency": currency},
                "availability": {"available": True, "status": "in_stock"},
                "seller": {
                    "name": "Fixture Seller",
                    "url": "https://fixture.example.invalid",
                },
            }
        ],
    }


def _incomplete_product(product_id: str) -> dict:
    return {"id": product_id, "title": "incomplete fixture"}


def test_select_promising_product_ids_diversifies_across_query_ids() -> None:
    products = {
        f"query_{index}": [
            _complete_product(f"gid://shopify/p/q{index}-a"),
            _complete_product(f"gid://shopify/p/q{index}-b"),
        ]
        for index in range(12)
    }
    selected = select_promising_product_ids(products)
    assert len(selected) == MAX_GET_PRODUCT_VALIDATIONS == 5
    query_ids = [query_id for query_id, _product_id in selected]
    assert query_ids == ["query_0", "query_1", "query_2", "query_3", "query_4"]
    assert len(set(query_ids)) == 5
    assert selected == (
        ("query_0", "gid://shopify/p/q0-a"),
        ("query_1", "gid://shopify/p/q1-a"),
        ("query_2", "gid://shopify/p/q2-a"),
        ("query_3", "gid://shopify/p/q3-a"),
        ("query_4", "gid://shopify/p/q4-a"),
    )
    assert select_promising_product_ids(products) == selected


def test_select_promising_product_ids_first_pass_is_one_per_query() -> None:
    products = {
        "wireless_earbuds": [
            _complete_product(f"gid://shopify/p/earbuds-{index}") for index in range(10)
        ],
        "gaming_laptop": [_complete_product("gid://shopify/p/laptop-a")],
        "mechanical_keyboard": [_complete_product("gid://shopify/p/keyboard-a")],
        "usb_c_charger": [_complete_product("gid://shopify/p/charger-a")],
        "phone_case": [_complete_product("gid://shopify/p/case-a")],
        "portable_power_bank": [_complete_product("gid://shopify/p/powerbank-a")],
    }
    selected = select_promising_product_ids(products)
    query_ids = [query_id for query_id, _product_id in selected]
    assert query_ids == [
        "wireless_earbuds",
        "gaming_laptop",
        "mechanical_keyboard",
        "usb_c_charger",
        "phone_case",
    ]
    assert "gid://shopify/p/earbuds-1" not in {product_id for _q, product_id in selected}
    assert all(query_ids.count(query_id) == 1 for query_id in query_ids)


def test_select_promising_product_ids_prefers_incomplete_within_query() -> None:
    products = {
        "wireless_earbuds": [
            _complete_product("gid://shopify/p/earbuds-complete"),
            _incomplete_product("gid://shopify/p/earbuds-incomplete"),
        ],
        "gaming_laptop": [
            _complete_product("gid://shopify/p/laptop-complete"),
            _incomplete_product("gid://shopify/p/laptop-incomplete"),
        ],
        "usb_c_charger": [_complete_product("gid://shopify/p/charger-complete")],
        "phone_case": [_incomplete_product("gid://shopify/p/case-incomplete")],
        "skincare_serum": [_complete_product("gid://shopify/p/serum-complete")],
        "backpack": [_complete_product("gid://shopify/p/backpack-complete")],
    }
    selected = select_promising_product_ids(products)
    assert selected == (
        ("wireless_earbuds", "gid://shopify/p/earbuds-incomplete"),
        ("gaming_laptop", "gid://shopify/p/laptop-incomplete"),
        ("phone_case", "gid://shopify/p/case-incomplete"),
        ("usb_c_charger", "gid://shopify/p/charger-complete"),
        ("skincare_serum", "gid://shopify/p/serum-complete"),
    )


def test_select_promising_product_ids_fills_leftovers_after_distinct_query_pass() -> None:
    products = {
        "alpha": [
            _incomplete_product("gid://shopify/p/alpha-1"),
            _incomplete_product("gid://shopify/p/alpha-2"),
            _complete_product("gid://shopify/p/alpha-3"),
        ],
        "beta": [
            _complete_product("gid://shopify/p/beta-1"),
            _complete_product("gid://shopify/p/beta-2"),
        ],
        "gamma": [
            _incomplete_product("gid://shopify/p/gamma-1"),
            _complete_product("gid://shopify/p/gamma-2"),
        ],
    }
    selected = select_promising_product_ids(products)
    assert selected == (
        ("alpha", "gid://shopify/p/alpha-1"),
        ("gamma", "gid://shopify/p/gamma-1"),
        ("beta", "gid://shopify/p/beta-1"),
        ("alpha", "gid://shopify/p/alpha-2"),
        ("alpha", "gid://shopify/p/alpha-3"),
    )
    assert len(selected) == 5
    assert len({query_id for query_id, _product_id in selected[:3]}) == 3


def test_all_complete_twelve_query_probe_keeps_budget_and_distinct_get_product() -> None:
    intents = load_ph_probe_intents()
    responses_by_query_id: dict[str, dict] = {}
    get_product_by_id: dict[str, dict] = {}
    for intent in intents:
        products = [
            _complete_product(
                f"gid://shopify/p/{intent.query_id}-{index}",
                currency="USD",
            )
            for index in range(10)
        ]
        responses_by_query_id[intent.query_id] = {
            "products": products,
            "pagination": {"has_next_page": True, "cursor": "ignore-me"},
        }
        for product in products:
            get_product_by_id[product["id"]] = {"product": product}
    transport = fixture_transport_from_payload(
        {
            "responses_by_query_id": responses_by_query_id,
            "get_product_by_id": get_product_by_id,
        }
    )
    report = run_ph_coverage_probe(transport=transport, live=False)
    assert report.search_calls == 12
    assert report.get_product_calls == 5
    assert report.lookup_catalog_calls == 0
    assert report.pagination_followed is False
    assert report.bulk_ids_used is False
    assert report.closes_sprint_32 is False
    assert report.starts_sprint_38 is False
    assert report.production_certified is False
    tools = [name for name, _arguments in transport.calls]
    assert tools.count(SEARCH_TOOL) == 12
    assert tools.count(GET_PRODUCT_TOOL) == 5
    assert FORBIDDEN_LOOKUP_TOOL not in tools
    get_query_ids = [
        item.query_id for item in report.query_results if item.get_product_used
    ]
    assert get_query_ids == [item.query_id for item in intents[:5]]
    assert all(item.classification == USEFUL_PH_OFFER for item in report.query_results)
    assert all(offer.currency == "USD" for item in report.query_results for offer in item.offers)
    for _name, arguments in transport.calls:
        catalog = arguments["catalog"]
        assert "cursor" not in (catalog.get("pagination") or {})
        assert catalog.get("context", {}).get("currency") == PHP_CURRENCY


def test_php_context_does_not_force_php_or_fabricate_conversion() -> None:
    arguments = build_search_catalog_arguments("wireless earbuds")
    assert arguments["catalog"]["context"]["currency"] == PHP_CURRENCY
    usd = minimize_offer_evidence(
        _complete_product("gid://shopify/p/usd", currency="USD"),
        _complete_product("gid://shopify/p/usd", currency="USD")["variants"][0],
    )
    inr = minimize_offer_evidence(
        _complete_product("gid://shopify/p/inr", currency="INR"),
        _complete_product("gid://shopify/p/inr", currency="INR")["variants"][0],
    )
    gbp = minimize_offer_evidence(
        _complete_product("gid://shopify/p/gbp", currency="GBP"),
        _complete_product("gid://shopify/p/gbp", currency="GBP")["variants"][0],
    )
    assert usd.currency == "USD"
    assert inr.currency == "INR"
    assert gbp.currency == "GBP"
    assert usd.price_amount_minor == 1000
    assert classify_query_offers((usd,)) == USEFUL_PH_OFFER
    mixed = offers_from_products(
        [
            _complete_product("gid://shopify/p/php", currency="PHP"),
            _complete_product("gid://shopify/p/zar", currency="ZAR"),
        ]
    )
    assert {item.currency for item in mixed} == {"PHP", "ZAR"}
    assert PHP_CURRENCY not in {usd.currency, inr.currency, gbp.currency}


def test_owner_live_coverage_is_recorded_without_closing_sprint() -> None:
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    assert "PASSED TECHNICAL COVERAGE TEST" in probe_doc
    assert "120 products" in probe_doc
    assert "122 offer" in probe_doc
    assert "mixed" in probe_doc.casefold()
    assert "INR" in probe_doc
    assert "concentrated in one query" in probe_doc
    assert "rerun" in probe_doc.casefold()
    assert "does **not** close Sprint 32" in probe_doc
    assert "SPRINT 32 REMAINS OPEN" in probe_doc
    assert "SPRINT 38 UNSTARTED" in probe_doc
    assert "OWNER LIVE PH COVERAGE TEST REQUIRED" not in probe_doc
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert "Sprint 38 remains unstarted" in sprint32


def test_budget_rejects_thirteenth_search_and_sixth_get_product() -> None:
    intents = load_ph_probe_intents() + load_ph_probe_intents()[:1]
    transport = fixture_transport_from_payload(_fixture())
    with pytest.raises(ProbeLimitError, match="at most 12"):
        run_ph_coverage_probe(transport=transport, live=False, intents=intents)
    products = {
        f"q{index}": [{"id": f"gid://shopify/p/extra-{index}", "title": "item"}]
        for index in range(8)
    }
    with pytest.raises(ProbeLimitError, match="at most 5"):
        select_promising_product_ids(products, limit=6)


def test_no_raw_response_persistence_by_default(tmp_path: Path) -> None:
    exit_code = probe_main(["--fixture", str(DEFAULT_FIXTURE), "--output-dir", str(tmp_path)])
    assert exit_code == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    probe = json.loads((tmp_path / "ph_probe.json").read_text(encoding="utf-8"))
    assert summary["raw_response_persisted"] is False
    assert summary["production_certified"] is False
    assert summary["closes_sprint_32"] is False
    assert summary["credentials_required"] is False
    assert summary["agent_profile_usage"] == TECHNICAL_TEST_ONLY
    assert not (tmp_path / "raw").exists()
    serialized = json.dumps(probe)
    assert "cdn.example.invalid/earbuds.jpg" not in serialized
    assert "Inferred marketing copy" not in serialized
    assert "Inferred feature" not in serialized
    assert probe["query_results"][0]["offers"][0]["product_id"] == (
        "gid://shopify/p/fixture-ph-earbuds"
    )
    assert probe["query_results"][0]["offers"][0]["price_amount_minor"] == 249900
    assert probe["query_results"][0]["offers"][0]["currency"] == "PHP"


def test_live_output_rejects_paths_inside_the_repository(monkeypatch) -> None:
    monkeypatch.delenv("SHOPIFY_API_KEY", raising=False)
    exit_code = probe_main(["--live", "--output-dir", str(ROOT)])
    assert exit_code == 2
    assert not (ROOT / "summary.json").exists()
    nested = ROOT / "docs" / "live-shopify"
    exit_code = probe_main(["--live", "--output-dir", str(nested)])
    assert exit_code == 2
    assert not nested.exists()


def test_live_path_resolution_covers_relative_and_symlink_bypass(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(ROOT)
    relative_inside = Path("./tmp-shopify-out")
    assert live_probe_output_is_inside_repository(relative_inside) is True
    with pytest.raises(LiveProbeOutputInsideRepositoryError):
        assert_live_probe_output_outside_repository(relative_inside)
    exit_code = probe_main(["--live", "--output-dir", str(relative_inside)])
    assert exit_code == 2
    assert not (ROOT / "tmp-shopify-out").exists()

    link_into_repo = tmp_path / "link-into-docs"
    link_into_repo.symlink_to(ROOT / "docs")
    linked_live = link_into_repo / "live-shopify"
    assert live_probe_output_is_inside_repository(linked_live) is True
    resolved = resolve_live_probe_output_dir(linked_live)
    assert ROOT.resolve() in resolved.parents
    exit_code = probe_main(["--live", "--output-dir", str(linked_live)])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert LIVE_OUTPUT_INSIDE_REPO_MESSAGE in captured.out
    assert not (ROOT / "docs" / "live-shopify").exists()
    assert Path("/tmp/piqsavi-shopify-global-ph") == DEFAULT_OUTPUT_DIR
    assert ROOT.resolve() == REPOSITORY_ROOT


def test_live_anonymous_probe_does_not_require_credentials(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.delenv("SHOPIFY_API_KEY", raising=False)
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)

    def fake_post(request, timeout):
        del timeout
        catalog = request["params"]["arguments"]["catalog"]
        if "filters" in catalog:
            assert catalog["filters"]["ships_to"]["country"] == "PH"
        if request["params"]["name"] == SEARCH_TOOL:
            return {
                "result": {
                    "structuredContent": {
                        "products": [],
                        "pagination": {"has_next_page": True, "cursor": "ignore-me"},
                    }
                }
            }
        return {"result": {"structuredContent": {"product": {}}}}

    monkeypatch.setattr(
        "scripts.shopify_global_catalog_ph_probe.post_anonymous_catalog",
        fake_post,
    )
    outside = tmp_path / "piqsavi-shopify-global-ph"
    exit_code = probe_main(["--live", "--output-dir", str(outside)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "TECHNICAL TEST ONLY" in captured.out
    summary = json.loads((outside / "summary.json").read_text(encoding="utf-8"))
    assert summary["credentials_required"] is False
    assert summary["auth_tier"] == "Anonymous"
    assert summary["search_calls"] == 12
    assert summary["get_product_calls"] == 0
    assert summary["pagination_followed"] is False
    assert summary["raw_response_persisted"] is False
    assert not (outside / "raw").exists()
    assert "SHOPIFY_API_KEY" not in captured.out
    headers = anonymous_http_headers()
    assert "Authorization" not in headers


def test_persist_raw_option_is_removed() -> None:
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    module = (ROOT / "app/research/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    assert "--persist-raw" not in script
    assert "persist_raw" not in script
    assert "persist_raw" not in module
    assert "raw_exchanges" not in script
    with pytest.raises(SystemExit):
        probe_main(["--persist-raw"])


def test_module_has_no_live_http_and_script_is_catalog_only() -> None:
    module = (ROOT / "app/research/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    assert "httpx" not in module
    assert GLOBAL_CATALOG_ENDPOINT in module
    assert "httpx.post(" in script
    assert "Authorization" in script
    assert FORBIDDEN_LOOKUP_TOOL in script
    for host in ("shopee.", "lazada.", "powermaccenter.com", "abenson.com", "tiktok.com"):
        assert host not in script
    assert "catalog.shopify.com" in script


def test_production_catalogs_stay_empty_and_sprint32_stays_open() -> None:
    _transport, report = _run_fixture_probe()
    assert report.production_certified is False
    assert report.closes_sprint_32 is False
    assert report.starts_sprint_38 is False
    assert report.certifies_shopify is False
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    assert "Sprint 32 is **not complete**" in sprint32
    assert "In progress" in sprint32
    assert "PASSED TECHNICAL COVERAGE TEST" in sprint32
    assert "does **not** close Sprint 32" in sprint32
    assert PROBE_DOC.exists()
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    assert "PASSED TECHNICAL COVERAGE TEST" in probe_doc
    assert "SPRINT 32 REMAINS OPEN" in probe_doc
    assert "SPRINT 38 UNSTARTED" in probe_doc
    assert "not production certification" in probe_doc.lower()


def test_affiliate_neutrality_remains_intact() -> None:
    module = (ROOT / "app/research/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    assert "catalog_id" in module
    assert "forbids catalog field" in module
    assert "promoted" in module.casefold()
    assert "affiliate" in script.casefold() or "promoted" in script.casefold()
    _transport, report = _run_fixture_probe()
    assert report.affiliate_or_promoted_placement is False
    for relative in RANKING_MODULES:
        text = (ROOT / relative).read_text(encoding="utf-8").casefold()
        assert "commission" not in text
        assert "affiliate" not in text


def test_inferred_observation_helpers_do_not_treat_inferred_as_source() -> None:
    product = {
        "id": "gid://shopify/p/x",
        "description": {"html": "n"},
        "options": [{"name": "Size"}],
        "metadata": {"attributes": {"Color": "Black"}, "tech_specs": ["spec"]},
        "url": "https://fixture.example.invalid/p",
        "variants": [
            {
                "id": "gid://shopify/ProductVariant/x",
                "condition": ["new"],
                "price": {"amount": 1, "currency": "PHP"},
                "seller": {"name": "N"},
            }
        ],
    }
    variant = product["variants"][0]
    inferred = inferred_fields_observed(product, variant)
    source = source_offer_fields_observed(product, variant)
    assert "description" in inferred
    assert "metadata.attributes" in inferred
    assert "variants[].condition" in inferred
    assert "variant.price" in source
    assert "description" not in source


def test_fixture_cli_does_not_call_shopify(monkeypatch, tmp_path: Path) -> None:
    def fail_post(*_args, **_kwargs):
        raise AssertionError("fixture mode must not call Shopify")

    monkeypatch.setattr("scripts.shopify_global_catalog_ph_probe.post_anonymous_catalog", fail_post)
    exit_code = probe_main(["--fixture", str(DEFAULT_FIXTURE), "--output-dir", str(tmp_path)])
    assert exit_code == 0
    assert (tmp_path / "summary.json").exists()


class _FixedPayloadTransport:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def call_tool(self, name: str, arguments: dict) -> dict:
        del name, arguments
        return self.payload


def _useful_product(*, seller_url=None, product_url=None, checkout_url=None, domain=None) -> dict:
    variant = {
        "id": "gid://shopify/ProductVariant/ok",
        "price": {"amount": 129900, "currency": "PHP"},
        "availability": {"available": True, "status": "in_stock"},
        "seller": {"name": "Fixture Seller PH"},
    }
    if checkout_url:
        variant["checkout_url"] = checkout_url
    seller = variant["seller"]
    if seller_url:
        seller["url"] = seller_url
    if domain:
        seller["domain"] = domain
    product = {"id": "gid://shopify/p/ok", "variants": [variant]}
    if product_url:
        product["url"] = product_url
    return product


def test_http_200_jsonrpc_error_fails_probe_and_is_not_no_useful() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32000,
            "message": "Unauthorized",
            "data": {"secret": "do-not-persist"},
        },
    }
    with pytest.raises(ProbeResponseError, match=r"code=-32000.*Unauthorized") as exc_info:
        run_ph_coverage_probe(
            transport=_FixedPayloadTransport(payload),
            live=True,
            intents=(PhProbeIntent("wireless_earbuds", "wireless earbuds"),),
        )
    text = str(exc_info.value)
    assert "do-not-persist" not in text
    assert NO_USEFUL_PH_RESULT not in text
    with pytest.raises(ProbeResponseError):
        validate_catalog_tool_response(payload)


def test_http_200_mcp_is_error_fails_probe_and_is_not_no_useful() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "isError": True,
            "structuredContent": {
                "messages": [{"type": "error", "code": "unauthorized", "content": "tool failed"}],
                "products": [],
            },
        },
    }
    with pytest.raises(ProbeResponseError, match="MCP tool error") as exc_info:
        run_ph_coverage_probe(
            transport=_FixedPayloadTransport(payload),
            live=True,
            intents=(PhProbeIntent("wireless_earbuds", "wireless earbuds"),),
        )
    text = str(exc_info.value)
    assert "unauthorized" in text
    assert "tool failed" in text
    assert NO_USEFUL_PH_RESULT not in text
    with pytest.raises(ProbeResponseError):
        products_from_catalog_payload(payload)


def test_malformed_success_without_structured_content_fails_closed() -> None:
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
    with pytest.raises(ProbeResponseError, match="neither structuredContent"):
        validate_catalog_tool_response(payload)
    with pytest.raises(ProbeResponseError, match="neither structuredContent"):
        run_ph_coverage_probe(
            transport=_FixedPayloadTransport(payload),
            live=True,
            intents=(PhProbeIntent("wireless_earbuds", "wireless earbuds"),),
        )


def test_successful_products_with_nonfatal_messages_remain_processable() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "structuredContent": {
                "messages": [{"type": "info", "code": "note", "content": "non-fatal"}],
                "products": [
                    _useful_product(
                        seller_url="https://fixture-ok.example.invalid",
                        checkout_url="https://fixture-ok.example.invalid/cart/ok:1",
                    )
                ],
            }
        },
    }
    content = validate_catalog_tool_response(payload)
    assert content["products"]
    report = run_ph_coverage_probe(
        transport=_FixedPayloadTransport(payload),
        live=False,
        intents=(PhProbeIntent("wireless_earbuds", "wireless earbuds"),),
    )
    assert report.query_results[0].classification == USEFUL_PH_OFFER
    assert report.closes_sprint_32 is False


def test_live_cli_jsonrpc_error_writes_failure_not_coverage(tmp_path: Path, monkeypatch) -> None:
    def fake_post(request, timeout):
        del request, timeout
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "Unauthorized", "data": {"raw": "nope"}},
        }

    monkeypatch.setattr(
        "scripts.shopify_global_catalog_ph_probe.post_anonymous_catalog",
        fake_post,
    )
    outside = tmp_path / "piqsavi-shopify-global-ph"
    exit_code = probe_main(["--live", "--output-dir", str(outside)])
    assert exit_code == 2
    summary = json.loads((outside / "summary.json").read_text(encoding="utf-8"))
    blob = json.dumps(summary)
    assert summary["technical_probe_failure"] is True
    assert summary["closes_sprint_32"] is False
    assert summary["starts_sprint_38"] is False
    assert "NO_USEFUL_PH_RESULT" not in blob
    assert "classifications" not in summary
    assert "nope" not in blob
    assert "Unauthorized" in summary["error"]
    assert not (outside / "ph_probe.json").exists()
    assert not (outside / "raw").exists()


def test_price_amount_and_currency_are_required_together() -> None:
    amount_only = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok", "url": "https://fixture-ok.example.invalid/p"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 5000},
            "checkout_url": "https://fixture-ok.example.invalid/cart/ok:1",
            "seller": {"name": "Fixture OK"},
        },
    )
    assert amount_only.price_amount_minor == 5000
    assert amount_only.price_present is True
    assert amount_only.currency is None
    assert amount_only.usable_for_comparison is False
    assert classify_query_offers((amount_only,)) == PARTIAL_PH_RESULT

    currency_only = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok", "url": "https://fixture-ok.example.invalid/p"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"currency": "PHP"},
            "checkout_url": "https://fixture-ok.example.invalid/cart/ok:1",
            "seller": {"name": "Fixture OK"},
        },
    )
    assert currency_only.price_amount_minor is None
    assert currency_only.price_present is False
    assert currency_only.currency == "PHP"
    assert currency_only.usable_for_comparison is False
    assert classify_query_offers((currency_only,)) == PARTIAL_PH_RESULT

    float_amount = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok", "url": "https://fixture-ok.example.invalid/p"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 12.5, "currency": "PHP"},
            "checkout_url": "https://fixture-ok.example.invalid/cart/ok:1",
            "seller": {"name": "Fixture OK"},
        },
    )
    assert float_amount.price_amount_minor is None
    assert float_amount.usable_for_comparison is False


def test_destination_requires_actual_url_not_seller_domain() -> None:
    domain_only = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 1000, "currency": "PHP"},
            "seller": {
                "name": "Fixture OK",
                "domain": "fixture-ok.example.invalid",
            },
        },
    )
    assert domain_only.seller_domain == "fixture-ok.example.invalid"
    assert domain_only.seller_url_present is False
    assert domain_only.product_url_present is False
    assert domain_only.checkout_url_present is False
    assert domain_only.usable_for_comparison is False
    assert classify_query_offers((domain_only,)) == PARTIAL_PH_RESULT

    seller_url = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 1000, "currency": "PHP"},
            "seller": {
                "name": "Fixture OK",
                "domain": "fixture-ok.example.invalid",
                "url": "https://fixture-ok.example.invalid",
            },
        },
    )
    assert seller_url.seller_url_present is True
    assert seller_url.usable_for_comparison is True

    product_url = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok", "url": "https://fixture-ok.example.invalid/products/ok"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 1000, "currency": "PHP"},
            "seller": {"name": "Fixture OK"},
        },
    )
    assert product_url.product_url_present is True
    assert product_url.seller_url_present is False
    assert product_url.usable_for_comparison is True

    checkout_url = minimize_offer_evidence(
        {"id": "gid://shopify/p/ok"},
        {
            "id": "gid://shopify/ProductVariant/ok",
            "price": {"amount": 1000, "currency": "PHP"},
            "checkout_url": "https://fixture-ok.example.invalid/cart/ok:1",
            "seller": {"name": "Fixture OK"},
        },
    )
    assert checkout_url.checkout_url_present is True
    assert checkout_url.usable_for_comparison is True
    flags = coverage_flags((domain_only,))
    assert flags["seller_url_or_domain_present"] is True
    assert flags["destination_present"] is False


def test_no_raw_shopify_payload_persistence_exists() -> None:
    module = (ROOT / "app/research/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    assert "raw_response_persisted=False" in module
    assert "--persist-raw" not in script
    assert "Do not persist raw Shopify catalog responses." in script or (
        "raw catalog payloads are not persisted" in script
    )


def test_sprint38_unstarted_and_production_catalogs_empty() -> None:
    _transport, report = _run_fixture_probe()
    assert report.starts_sprint_38 is False
    assert report.production_certified is False
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    assert "Sprint 32 remains open." in sprint32
    assert "Sprint 38 remains unstarted" in sprint32
    assert "not Sprint 38 execution" in probe_doc
    assert "SPRINT 38 UNSTARTED" in probe_doc
