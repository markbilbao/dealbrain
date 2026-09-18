"""Sprint 32 PiqSavi UCP agent-profile foundation — not certification."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from app.core.config import Settings, get_settings
from app.main import create_app
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_ph_probe import (
    AGENT_PROFILE_SOURCE_PIQSAVI,
    AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE,
    AGENT_PROFILE_USAGE,
    AGENT_PROFILE_USAGE_PIQSAVI,
    DEFAULT_AGENT_PROFILE_SOURCE,
    DEFAULT_FIXTURE,
    FORBIDDEN_LOOKUP_TOOL,
    GET_PRODUCT_TOOL,
    MAX_GET_PRODUCT_VALIDATIONS,
    MAX_SEARCH_CATALOG_QUERIES,
    SEARCH_TOOL,
    TECHNICAL_TEST_AGENT_PROFILE,
    TECHNICAL_TEST_ONLY,
    ProbeContractError,
    ProbeLimitError,
    build_get_product_arguments,
    build_jsonrpc_request,
    build_search_catalog_arguments,
    fixture_transport_from_payload,
    load_ph_probe_intents,
    load_probe_fixture,
    run_ph_coverage_probe,
    select_agent_profile,
    select_promising_product_ids,
)
from app.ucp.agent_profile import (
    CAPABILITY_CATALOG_LOOKUP,
    CAPABILITY_CATALOG_SEARCH,
    CAPABILITY_SHOPIFY_GLOBAL_CATALOG,
    DECLARED_CAPABILITY_NAMES,
    FORBIDDEN_PROFILE_CAPABILITIES,
    PIQSAVI_UCP_AGENT_PROFILE,
    PIQSAVI_UCP_AGENT_PROFILE_CACHE_CONTROL,
    PIQSAVI_UCP_AGENT_PROFILE_CONTENT_TYPE,
    PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED,
    PIQSAVI_UCP_AGENT_PROFILE_PATH,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    PIQSAVI_UCP_VERSION,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL,
    declared_capability_names,
    profile_contains_secrets,
    serialize_piqsavi_ucp_agent_profile,
    trusted_piqsavi_ucp_agent_profile_url,
)
from fastapi.testclient import TestClient
from httpx import AsyncClient
from scripts.shopify_global_catalog_ph_probe import main as probe_main

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
PROBE_DOC = ROOT / "docs/roadmap/evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
ROUTE_SOURCE = ROOT / "app/api/ucp.py"
PROFILE_SOURCE = ROOT / "app/ucp/agent_profile.py"


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_profile_document_is_valid_deterministic_least_privilege_json() -> None:
    body = serialize_piqsavi_ucp_agent_profile()
    parsed = json.loads(body)
    assert parsed == PIQSAVI_UCP_AGENT_PROFILE
    assert parsed["ucp"]["version"] == "2026-08-25"
    assert parsed["ucp"]["version"] == PIQSAVI_UCP_VERSION
    assert declared_capability_names(parsed) == DECLARED_CAPABILITY_NAMES
    assert CAPABILITY_CATALOG_SEARCH in parsed["ucp"]["capabilities"]
    assert CAPABILITY_CATALOG_LOOKUP in parsed["ucp"]["capabilities"]
    assert CAPABILITY_SHOPIFY_GLOBAL_CATALOG in parsed["ucp"]["capabilities"]
    global_ext = parsed["ucp"]["capabilities"][CAPABILITY_SHOPIFY_GLOBAL_CATALOG][0]
    assert global_ext["extends"] == [
        CAPABILITY_CATALOG_SEARCH,
        CAPABILITY_CATALOG_LOOKUP,
    ]
    blob = json.dumps(parsed)
    for name in FORBIDDEN_PROFILE_CAPABILITIES:
        assert name not in parsed["ucp"]["capabilities"]
        assert name not in blob or name == "dev.shopify.catalog"
    assert "dev.ucp.shopping.checkout" not in blob
    assert "dev.ucp.shopping.cart" not in blob
    assert "dev.ucp.shopping.order" not in blob
    assert "payment_handlers" not in parsed["ucp"]
    assert "services" not in parsed["ucp"]
    assert profile_contains_secrets(parsed) is False
    assert serialize_piqsavi_ucp_agent_profile() == body


def test_lookup_is_declared_only_because_global_catalog_extends_it() -> None:
    source = PROFILE_SOURCE.read_text(encoding="utf-8")
    assert "dev.shopify.catalog.global" in source
    assert "extends both catalog.search and catalog.lookup" in source
    assert "not permission to run bulk" in source
    assert "lookup_catalog" in source


@pytest.mark.asyncio
async def test_profile_route_http_contract_is_public_json(client: AsyncClient) -> None:
    first = await client.get(PIQSAVI_UCP_AGENT_PROFILE_PATH)
    second = await client.get(PIQSAVI_UCP_AGENT_PROFILE_PATH)
    assert first.status_code == 200
    assert second.status_code == 200
    assert PIQSAVI_UCP_AGENT_PROFILE_CONTENT_TYPE in first.headers["content-type"]
    assert "application/json" in first.headers["content-type"]
    assert "text/html" not in first.headers["content-type"]
    assert first.headers["cache-control"] == PIQSAVI_UCP_AGENT_PROFILE_CACHE_CONTROL
    assert first.headers.get("location") is None
    assert "set-cookie" not in {key.casefold() for key in first.headers}
    body = json.loads(first.text)
    assert body["ucp"]["version"] == "2026-08-25"
    assert first.content == second.content
    assert first.text == serialize_piqsavi_ucp_agent_profile()


@pytest.mark.asyncio
async def test_profile_route_requires_no_authentication_and_ignores_input(
    client: AsyncClient,
) -> None:
    poisoned = (
        f"{PIQSAVI_UCP_AGENT_PROFILE_PATH}"
        "?profile=https://evil.example/ucp.json"
        "&PIQSAVI_UCP_AGENT_PROFILE_URL=https://evil.example/ucp.json"
    )
    response = await client.get(
        poisoned,
        headers={
            "Authorization": "Bearer shopper-token",
            "X-UCP-Agent-Profile": "https://evil.example/ucp.json",
            "Cookie": "profile=https://evil.example/ucp.json",
        },
    )
    assert response.status_code == 200
    assert response.json() == PIQSAVI_UCP_AGENT_PROFILE
    assert "evil.example" not in response.text
    posted = await client.post(
        PIQSAVI_UCP_AGENT_PROFILE_PATH,
        json={"ucp": {"version": "evil"}},
    )
    assert posted.status_code == 405


def test_profile_route_has_no_db_or_network_dependency() -> None:
    route_src = ROUTE_SOURCE.read_text(encoding="utf-8")
    profile_src = PROFILE_SOURCE.read_text(encoding="utf-8")
    assert "get_db" not in route_src
    assert "import redis" not in route_src.casefold()
    assert "httpx" not in route_src
    assert "Depends" not in route_src
    assert "httpx" not in profile_src
    source = inspect.getsource(serialize_piqsavi_ucp_agent_profile)
    assert "httpx" not in source
    assert "get_db" not in source


def test_trusted_profile_url_is_server_owned_and_not_shopify_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_cache()
    try:
        assert trusted_piqsavi_ucp_agent_profile_url() == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
        assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL != TECHNICAL_TEST_AGENT_PROFILE
        assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL.startswith("https://piqsavi.com/")
        assert PIQSAVI_UCP_AGENT_PROFILE_PATH in PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
        assert "shopify.dev" not in PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
        monkeypatch.setenv(
            "PIQSAVI_UCP_AGENT_PROFILE_URL",
            SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL,
        )
        _clear_settings_cache()
        with pytest.raises(ValueError, match="not Shopify"):
            trusted_piqsavi_ucp_agent_profile_url()
        monkeypatch.setenv("PIQSAVI_UCP_AGENT_PROFILE_URL", "http://piqsavi.com/ucp.json")
        _clear_settings_cache()
        with pytest.raises(ValueError, match="HTTPS"):
            trusted_piqsavi_ucp_agent_profile_url()
        monkeypatch.setenv(
            "PIQSAVI_UCP_AGENT_PROFILE_URL",
            PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
        )
        _clear_settings_cache()
        assert trusted_piqsavi_ucp_agent_profile_url() == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
    finally:
        monkeypatch.delenv("PIQSAVI_UCP_AGENT_PROFILE_URL", raising=False)
        _clear_settings_cache()


def test_settings_default_is_production_piqsavi_url() -> None:
    settings = Settings()
    assert settings.piqsavi_ucp_agent_profile_url == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL


def test_technical_fixture_and_piqsavi_profiles_are_explicitly_distinct() -> None:
    fixture = select_agent_profile(AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE)
    piqsavi = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
    assert DEFAULT_AGENT_PROFILE_SOURCE == AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE
    assert fixture.url == TECHNICAL_TEST_AGENT_PROFILE
    assert fixture.usage == TECHNICAL_TEST_ONLY == AGENT_PROFILE_USAGE
    assert fixture.not_piqsavi_identity is True
    assert piqsavi.url == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    assert piqsavi.usage == AGENT_PROFILE_USAGE_PIQSAVI
    assert piqsavi.not_piqsavi_identity is False
    assert piqsavi.url != fixture.url
    assert piqsavi.deployed_and_validated is False
    assert piqsavi.shopify_has_fetched_profile is False
    assert PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    with pytest.raises(ProbeContractError, match="unsupported agent profile source"):
        select_agent_profile("https://evil.example/ucp.json")


def test_probe_defaults_to_shopify_fixture_and_can_select_piqsavi_explicitly() -> None:
    fixture_args = build_search_catalog_arguments("wireless earbuds")
    assert fixture_args["meta"]["ucp-agent"]["profile"] == TECHNICAL_TEST_AGENT_PROFILE
    piqsavi = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
    piqsavi_args = build_search_catalog_arguments("wireless earbuds", profile=piqsavi)
    assert piqsavi_args["meta"]["ucp-agent"]["profile"] == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    get_args = build_get_product_arguments("gid://shopify/p/fixture", profile=piqsavi)
    assert get_args["meta"]["ucp-agent"]["profile"] == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    payload = load_probe_fixture(DEFAULT_FIXTURE)
    transport = fixture_transport_from_payload(payload)
    report = run_ph_coverage_probe(transport=transport, live=False)
    assert report.agent_profile == TECHNICAL_TEST_AGENT_PROFILE
    assert report.agent_profile_source == AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE
    assert report.agent_profile_usage == TECHNICAL_TEST_ONLY
    piqsavi_report = run_ph_coverage_probe(
        transport=fixture_transport_from_payload(payload),
        live=False,
        agent_profile_source=AGENT_PROFILE_SOURCE_PIQSAVI,
    )
    assert piqsavi_report.agent_profile == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    assert piqsavi_report.agent_profile_source == AGENT_PROFILE_SOURCE_PIQSAVI
    assert piqsavi_report.piqsavi_profile_deployed_and_validated is False
    assert piqsavi_report.shopify_has_fetched_piqsavi_profile is False
    assert piqsavi_report.production_certified is False
    assert piqsavi_report.closes_sprint_32 is False


def test_probe_cli_keeps_fixture_default_and_rejects_request_style_url_override(
    tmp_path: Path,
) -> None:
    exit_code = probe_main(["--fixture", str(DEFAULT_FIXTURE), "--output-dir", str(tmp_path)])
    assert exit_code == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["agent_profile"] == TECHNICAL_TEST_AGENT_PROFILE
    assert summary["agent_profile_source"] == AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE
    assert summary["agent_profile_usage"] == TECHNICAL_TEST_ONLY
    with pytest.raises(SystemExit):
        probe_main(
            [
                "--agent-profile-url",
                "https://evil.example/ucp.json",
                "--output-dir",
                str(tmp_path / "evil"),
            ]
        )
    piqsavi_dir = tmp_path / "piqsavi"
    exit_code = probe_main(
        [
            "--fixture",
            str(DEFAULT_FIXTURE),
            "--agent-profile-source",
            "piqsavi",
            "--output-dir",
            str(piqsavi_dir),
        ]
    )
    assert exit_code == 0
    piqsavi_summary = json.loads((piqsavi_dir / "summary.json").read_text(encoding="utf-8"))
    assert piqsavi_summary["agent_profile"] == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    assert piqsavi_summary["agent_profile_source"] == AGENT_PROFILE_SOURCE_PIQSAVI
    assert piqsavi_summary["piqsavi_profile_deployed_and_validated"] is False
    assert piqsavi_summary["shopify_has_fetched_piqsavi_profile"] is False


def test_existing_ph_probe_limits_and_forbidden_tools_remain() -> None:
    assert MAX_SEARCH_CATALOG_QUERIES == 12
    assert MAX_GET_PRODUCT_VALIDATIONS == 5
    assert len(load_ph_probe_intents()) == 12
    payload = load_probe_fixture(DEFAULT_FIXTURE)
    transport = fixture_transport_from_payload(payload)
    report = run_ph_coverage_probe(transport=transport, live=False)
    assert report.search_calls == 12
    assert report.get_product_calls <= 5
    assert report.lookup_catalog_calls == 0
    assert report.pagination_followed is False
    assert report.scraping is False
    tools = [name for name, _arguments in transport.calls]
    assert FORBIDDEN_LOOKUP_TOOL not in tools
    assert SEARCH_TOOL in tools
    assert GET_PRODUCT_TOOL in tools
    arguments = build_search_catalog_arguments("wireless earbuds")
    with pytest.raises(ProbeContractError, match="lookup_catalog"):
        build_jsonrpc_request(FORBIDDEN_LOOKUP_TOOL, arguments, request_id=2)
    extra = load_ph_probe_intents() + load_ph_probe_intents()[:1]
    with pytest.raises(ProbeLimitError, match="at most 12"):
        run_ph_coverage_probe(
            transport=fixture_transport_from_payload(payload),
            live=False,
            intents=extra,
        )
    products = {
        f"q{index}": [{"id": f"gid://shopify/p/extra-{index}", "title": "item"}]
        for index in range(8)
    }
    with pytest.raises(ProbeLimitError, match="at most 5"):
        select_promising_product_ids(products, limit=6)


def test_production_registries_remain_empty_and_sprints_remain_open() -> None:
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    sprint38 = SPRINT38.read_text(encoding="utf-8")
    assert "Sprint 32 remains open." in sprint32
    assert "Sprint 38 remains unstarted" in sprint32
    assert "IMPLEMENTED LOCALLY — NOT YET DEPLOYED/VALIDATED" in probe_doc
    assert "SPRINT 32 REMAINS OPEN" in probe_doc
    assert "SPRINT 38 UNSTARTED" in probe_doc
    assert sprint38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"
    assert PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False


def test_profile_is_omitted_from_openapi() -> None:
    schema = create_app().openapi()
    assert PIQSAVI_UCP_AGENT_PROFILE_PATH not in schema.get("paths", {})


def test_profile_route_is_skipped_by_rate_limiter() -> None:
    from app.core.middleware.rate_limiting import RateLimitMiddleware

    source = inspect.getsource(RateLimitMiddleware.dispatch)
    assert "PIQSAVI_UCP_AGENT_PROFILE_PATH" in source


def test_no_deployment_or_live_shopify_call_in_this_slice() -> None:
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    assert "NOT YET DEPLOYED/VALIDATED" in sprint32
    assert "no live Shopify call made" in probe_doc.casefold() or (
        "This agent did **not** call Shopify" in probe_doc
        or "no live Shopify call" in probe_doc.casefold()
    )
    assert "profile has not yet been fetched by Shopify" in probe_doc.casefold() or (
        "Shopify has not fetched" in probe_doc
    )


def test_sync_client_also_serves_json_without_html() -> None:
    with TestClient(create_app()) as client:
        response = client.get(PIQSAVI_UCP_AGENT_PROFILE_PATH)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert not response.text.lstrip().startswith("<")
    assert response.json()["ucp"]["version"] == "2026-08-25"
