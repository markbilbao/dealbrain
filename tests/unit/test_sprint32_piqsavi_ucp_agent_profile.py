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
    LIVE_PIQSAVI_PROFILE_NOT_DEPLOYED_MESSAGE,
    MAX_GET_PRODUCT_VALIDATIONS,
    MAX_SEARCH_CATALOG_QUERIES,
    SEARCH_TOOL,
    TECHNICAL_TEST_AGENT_PROFILE,
    TECHNICAL_TEST_ONLY,
    AgentProfileSelection,
    LivePiqsaviProfileNotDeployedError,
    ProbeContractError,
    ProbeLimitError,
    assert_live_piqsavi_profile_unlocked,
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
    DECLARED_SERVICE_FIELDS,
    DECLARED_SERVICE_NAMES,
    FORBIDDEN_PROFILE_CAPABILITIES,
    PIQSAVI_UCP_AGENT_PROFILE,
    PIQSAVI_UCP_AGENT_PROFILE_CACHE_CONTROL,
    PIQSAVI_UCP_AGENT_PROFILE_CONTENT_TYPE,
    PIQSAVI_UCP_AGENT_PROFILE_PATH,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    PIQSAVI_UCP_PAYMENT_HANDLERS,
    PIQSAVI_UCP_SERVICE_SCHEMA,
    PIQSAVI_UCP_SERVICE_SPEC,
    PIQSAVI_UCP_SERVICE_TRANSPORT,
    PIQSAVI_UCP_VERSION,
    SERVICE_DEV_UCP_SHOPPING,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    SHOPIFY_TECHNICAL_TEST_AGENT_PROFILE_URL,
    TRUSTED_PIQSAVI_UCP_AGENT_PROFILE_URLS,
    declared_capability_names,
    declared_service_names,
    piqsavi_profile_deployed_for_url,
    piqsavi_profile_is_shopify_negotiated,
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
PROBE_MODULE = ROOT / "app/research/shopify_global_catalog_ph_probe.py"
PROBE_SCRIPT = ROOT / "scripts/shopify_global_catalog_ph_probe.py"
_STALE_PIQSAVI_LABELS = (
    "NOT_YET_DEPLOYED",
    "production-intended profile selected",
    "piqsavi_production_intended",
    "PIQSAVI_PRODUCTION_INTENDED",
)


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def _assert_no_stale_piqsavi_labels(payload: object) -> None:
    blob = payload if isinstance(payload, str) else json.dumps(payload)
    for stale in _STALE_PIQSAVI_LABELS:
        assert stale not in blob


def test_profile_document_is_valid_deterministic_least_privilege_json() -> None:
    body = serialize_piqsavi_ucp_agent_profile()
    parsed = json.loads(body)
    assert parsed == PIQSAVI_UCP_AGENT_PROFILE
    assert parsed["ucp"]["version"] == "2026-08-25"
    assert parsed["ucp"]["version"] == PIQSAVI_UCP_VERSION
    assert tuple(parsed["ucp"]) == ("version", "services", "capabilities", "payment_handlers")
    assert "services" in parsed["ucp"]
    assert declared_service_names(parsed) == DECLARED_SERVICE_NAMES == (SERVICE_DEV_UCP_SHOPPING,)
    assert tuple(parsed["ucp"]["services"]) == (SERVICE_DEV_UCP_SHOPPING,)
    shopping = parsed["ucp"]["services"][SERVICE_DEV_UCP_SHOPPING]
    assert isinstance(shopping, list) and len(shopping) == 1
    service = shopping[0]
    assert tuple(service) == DECLARED_SERVICE_FIELDS
    assert service["version"] == "2026-08-25"
    assert service["spec"] == PIQSAVI_UCP_SERVICE_SPEC
    assert service["spec"] == "https://ucp.dev/2026-08-25/specification/overview"
    assert service["transport"] == PIQSAVI_UCP_SERVICE_TRANSPORT == "mcp"
    assert service["schema"] == PIQSAVI_UCP_SERVICE_SCHEMA
    assert service["schema"] == "https://ucp.dev/2026-08-25/services/shopping/mcp.openrpc.json"
    assert "endpoint" not in service
    assert "payment_handlers" in parsed["ucp"]
    assert parsed["ucp"]["payment_handlers"] == {} == PIQSAVI_UCP_PAYMENT_HANDLERS
    assert declared_capability_names(parsed) == DECLARED_CAPABILITY_NAMES
    assert tuple(parsed["ucp"]["capabilities"]) == DECLARED_CAPABILITY_NAMES
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
    assert "dev.ucp.shopping.fulfillment" not in blob
    assert "dev.ucp.shopping.buyer_consent" not in blob
    assert "dev.ucp.shopping.discount" not in blob
    assert "dev.ucp.shopping.payment" not in blob
    assert 'dev.shopify.catalog"' not in blob
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
    assert body["ucp"]["services"][SERVICE_DEV_UCP_SHOPPING][0]["transport"] == "mcp"
    assert body["ucp"]["payment_handlers"] == {}


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
        monkeypatch.setenv(
            "PIQSAVI_UCP_AGENT_PROFILE_URL",
            "https://evil.example/ucp.json",
        )
        _clear_settings_cache()
        with pytest.raises(ValueError, match="exact trusted"):
            trusted_piqsavi_ucp_agent_profile_url()
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
    assert AGENT_PROFILE_SOURCE_PIQSAVI == "piqsavi"
    assert AGENT_PROFILE_USAGE_PIQSAVI == "PIQSAVI_OWNED_PROFILE"
    assert piqsavi.source == "piqsavi"
    assert piqsavi.usage == AGENT_PROFILE_USAGE_PIQSAVI
    assert piqsavi.not_piqsavi_identity is False
    assert piqsavi.url != fixture.url
    assert piqsavi.piqsavi_profile_deployed is False
    assert piqsavi.piqsavi_profile_staging_deployed is True
    assert piqsavi.piqsavi_profile_production_deployed is False
    assert piqsavi.shopify_has_fetched_profile is False
    assert fixture.piqsavi_profile_deployed is False
    assert fixture.piqsavi_profile_staging_deployed is True
    assert fixture.piqsavi_profile_production_deployed is False
    assert fixture.shopify_has_fetched_profile is False
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert piqsavi_profile_is_shopify_negotiated() is False
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
    assert piqsavi_report.piqsavi_profile_deployed is False
    assert piqsavi_report.piqsavi_profile_staging_deployed is True
    assert piqsavi_report.piqsavi_profile_production_deployed is False
    assert piqsavi_report.shopify_has_fetched_piqsavi_profile is False
    assert "piqsavi_profile_deployed_and_validated" not in piqsavi_report.to_dict()
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
    assert piqsavi_summary["piqsavi_profile_deployed"] is False
    assert piqsavi_summary["piqsavi_profile_staging_deployed"] is True
    assert piqsavi_summary["piqsavi_profile_production_deployed"] is False
    assert piqsavi_summary["shopify_has_fetched_piqsavi_profile"] is False
    assert "piqsavi_profile_deployed_and_validated" not in piqsavi_summary


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
    assert "STAGING PIQSAVI UCP PROFILE DEPLOYED / OWNER HTTPS-VALIDATED" in probe_doc
    assert "PRODUCTION PROFILE NOT VALIDATED" in probe_doc
    assert "SPRINT 32 REMAINS OPEN" in probe_doc
    assert "SPRINT 38 UNSTARTED" in probe_doc
    assert sprint38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert piqsavi_profile_is_shopify_negotiated() is False


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
    script = (ROOT / "scripts/shopify_global_catalog_ph_probe.py").read_text(encoding="utf-8")
    profile_src = PROFILE_SOURCE.read_text(encoding="utf-8")
    assert "NOT YET DEPLOYED/VALIDATED" in sprint32
    assert "PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED" in sprint32
    assert "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED" in sprint32
    assert "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE" in sprint32
    assert "PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED" not in profile_src
    assert "PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED: Final = True" in profile_src
    assert "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED: Final = False" in profile_src
    assert "FAIL CLOSED" in sprint32 or "fail-closed" in sprint32.casefold()
    assert "no live Shopify call made" in probe_doc.casefold() or (
        "This agent did **not** call Shopify" in probe_doc
        or "no live Shopify call" in probe_doc.casefold()
    )
    assert "profile has not yet been fetched by Shopify" in probe_doc.casefold() or (
        "Shopify has not fetched" in probe_doc
    )
    assert "--agent-profile-url" not in script
    assert "A. Merge this foundation PR." in sprint32
    assert "G. Only after that continue capability-policy" in sprint32


def test_sync_client_also_serves_json_without_html() -> None:
    with TestClient(create_app()) as client:
        response = client.get(PIQSAVI_UCP_AGENT_PROFILE_PATH)
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert not response.text.lstrip().startswith("<")
    assert response.json()["ucp"]["version"] == "2026-08-25"


def test_deployment_and_shopify_fetch_states_are_environment_specific() -> None:
    profile_src = PROFILE_SOURCE.read_text(encoding="utf-8")
    assert "PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED: Final = True" in profile_src
    assert "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED: Final = False" in profile_src
    assert "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE: Final = False" in profile_src
    assert "PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED: Final =" not in profile_src
    assert "PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED" not in profile_src
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert piqsavi_profile_is_shopify_negotiated() is False
    unlock_src = inspect.getsource(assert_live_piqsavi_profile_unlocked)
    assert "piqsavi_profile_deployed_for_url(profile.url)" in unlock_src
    assert "if PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED:" not in unlock_src
    assert "if SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE:" not in unlock_src
    derived_src = inspect.getsource(piqsavi_profile_is_shopify_negotiated)
    assert "PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED" in derived_src
    assert "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED" in derived_src
    assert "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE" in derived_src
    assert "does **not** mean Shopify fetched" in derived_src


def test_lifecycle_states_cannot_be_changed_by_user_request_or_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED", "false")
    monkeypatch.setenv("PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED", "true")
    monkeypatch.setenv("PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED", "true")
    monkeypatch.setenv("SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE", "true")
    monkeypatch.setenv("PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED", "true")
    monkeypatch.setenv(
        "PIQSAVI_UCP_AGENT_PROFILE_URL",
        "https://evil.example/ucp.json",
    )
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert piqsavi_profile_is_shopify_negotiated() is False
    assert piqsavi_profile_deployed_for_url("https://evil.example/ucp.json") is False
    settings = Settings()
    assert not hasattr(settings, "piqsavi_ucp_agent_profile_deployed")
    assert not hasattr(settings, "piqsavi_ucp_agent_profile_staging_deployed")
    assert not hasattr(settings, "piqsavi_ucp_agent_profile_production_deployed")
    assert not hasattr(settings, "shopify_has_fetched_piqsavi_profile")
    poisoned = (
        f"{PIQSAVI_UCP_AGENT_PROFILE_PATH}"
        "?PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED=true"
        "&PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED=false"
        "&SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE=true"
        "&PIQSAVI_UCP_AGENT_PROFILE_URL=https://evil.example/ucp.json"
    )
    with TestClient(create_app()) as http:
        response = http.get(
            poisoned,
            headers={
                "X-Piqsavi-Profile-Deployed": "true",
                "Cookie": "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED=true",
            },
        )
    assert response.status_code == 200
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    spoofed = AgentProfileSelection(
        source=AGENT_PROFILE_SOURCE_PIQSAVI,
        url=PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
        usage=AGENT_PROFILE_USAGE_PIQSAVI,
        not_piqsavi_identity=False,
        piqsavi_profile_deployed=True,
        piqsavi_profile_staging_deployed=True,
        piqsavi_profile_production_deployed=True,
        shopify_has_fetched_profile=True,
    )
    with pytest.raises(LivePiqsaviProfileNotDeployedError, match="not yet deployed"):
        assert_live_piqsavi_profile_unlocked(spoofed)
    arbitrary = AgentProfileSelection(
        source=AGENT_PROFILE_SOURCE_PIQSAVI,
        url="https://evil.example/ucp.json",
        usage=AGENT_PROFILE_USAGE_PIQSAVI,
        not_piqsavi_identity=False,
        piqsavi_profile_deployed=True,
        piqsavi_profile_staging_deployed=True,
        piqsavi_profile_production_deployed=True,
        shopify_has_fetched_profile=True,
    )
    with pytest.raises(LivePiqsaviProfileNotDeployedError, match="not yet deployed"):
        assert_live_piqsavi_profile_unlocked(arbitrary)


@pytest.mark.asyncio
async def test_async_request_cannot_flip_lifecycle_states(client: AsyncClient) -> None:
    response = await client.get(
        f"{PIQSAVI_UCP_AGENT_PROFILE_PATH}"
        "?PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED=true"
        "&PIQSAVI_UCP_AGENT_PROFILE_URL=https://evil.example/ucp.json",
        headers={"Cookie": "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE=true"},
    )
    assert response.status_code == 200
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL) is False


def test_live_piqsavi_profile_fails_closed_with_zero_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = {"post": 0, "transport": 0, "run": 0, "httpx": 0}

    def boom_post(*_args: object, **_kwargs: object) -> dict[str, object]:
        calls["post"] += 1
        raise AssertionError("Shopify network must not be called")

    class BoomTransport:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            calls["transport"] += 1
            raise AssertionError("live transport must not be constructed")

    def boom_run(*_args: object, **_kwargs: object) -> object:
        calls["run"] += 1
        raise AssertionError("live probe must not run")

    def boom_httpx(*_args: object, **_kwargs: object) -> object:
        calls["httpx"] += 1
        raise AssertionError("httpx must not be called")

    monkeypatch.setattr(
        "scripts.shopify_global_catalog_ph_probe.post_anonymous_catalog",
        boom_post,
    )
    monkeypatch.setattr(
        "scripts.shopify_global_catalog_ph_probe.LiveAnonymousCatalogTransport",
        BoomTransport,
    )
    monkeypatch.setattr(
        "scripts.shopify_global_catalog_ph_probe.run_ph_coverage_probe",
        boom_run,
    )
    monkeypatch.setattr("httpx.post", boom_httpx)
    outside = tmp_path / "piqsavi-live-refused"
    exit_code = probe_main(
        [
            "--live",
            "--agent-profile-source",
            "piqsavi",
            "--output-dir",
            str(outside),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert calls == {"post": 0, "transport": 0, "run": 0, "httpx": 0}
    assert LIVE_PIQSAVI_PROFILE_NOT_DEPLOYED_MESSAGE in captured.out
    envelope = json.loads((outside / "summary.json").read_text(encoding="utf-8"))
    assert envelope["technical_probe_failure"] is True
    assert envelope["live_piqsavi_profile_refused"] is True
    assert envelope["shopify_network_calls"] == 0
    assert envelope["piqsavi_profile_deployed"] is False
    assert envelope["piqsavi_profile_staging_deployed"] is True
    assert envelope["piqsavi_profile_production_deployed"] is False
    assert envelope["shopify_has_fetched_piqsavi_profile"] is False
    assert envelope["agent_profile_source"] == AGENT_PROFILE_SOURCE_PIQSAVI
    assert envelope["closes_sprint_32"] is False
    assert envelope["starts_sprint_38"] is False
    assert "piqsavi_profile_deployed_and_validated" not in envelope
    assert not (outside / "ph_probe.json").exists()


def test_live_library_piqsavi_path_makes_zero_transport_calls() -> None:
    class CountingTransport:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
            self.calls.append((name, arguments))
            raise AssertionError("transport must not be called")

    transport = CountingTransport()
    profile = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
    with pytest.raises(
        LivePiqsaviProfileNotDeployedError,
        match="not yet deployed/publicly validated",
    ):
        run_ph_coverage_probe(transport=transport, live=True, agent_profile=profile)
    assert transport.calls == []


def test_offline_fixture_may_still_select_piqsavi_and_live_default_stays_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = load_probe_fixture(DEFAULT_FIXTURE)
    report = run_ph_coverage_probe(
        transport=fixture_transport_from_payload(payload),
        live=False,
        agent_profile_source=AGENT_PROFILE_SOURCE_PIQSAVI,
    )
    assert report.live is False
    assert report.agent_profile_source == AGENT_PROFILE_SOURCE_PIQSAVI
    assert report.agent_profile == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    assert report.piqsavi_profile_deployed is False
    assert report.piqsavi_profile_staging_deployed is True
    assert report.piqsavi_profile_production_deployed is False
    assert report.shopify_has_fetched_piqsavi_profile is False
    assert report.search_calls == 12
    assert report.get_product_calls <= 5

    live_calls: list[str] = []

    def fake_post(request, timeout):
        del timeout
        name = request["params"]["name"]
        live_calls.append(str(name))
        if name == SEARCH_TOOL:
            return {"result": {"structuredContent": {"products": []}}}
        return {"result": {"structuredContent": {"product": {}}}}

    monkeypatch.setattr(
        "scripts.shopify_global_catalog_ph_probe.post_anonymous_catalog",
        fake_post,
    )
    outside = tmp_path / "default-live-fixture"
    exit_code = probe_main(["--live", "--output-dir", str(outside)])
    assert exit_code == 0
    summary = json.loads((outside / "summary.json").read_text(encoding="utf-8"))
    assert summary["agent_profile_source"] == AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE
    assert summary["agent_profile"] == TECHNICAL_TEST_AGENT_PROFILE
    assert summary["piqsavi_profile_deployed"] is False
    assert summary["piqsavi_profile_staging_deployed"] is True
    assert summary["piqsavi_profile_production_deployed"] is False
    assert summary["shopify_has_fetched_piqsavi_profile"] is False
    assert live_calls
    assert DEFAULT_AGENT_PROFILE_SOURCE == AGENT_PROFILE_SOURCE_TECHNICAL_FIXTURE


def test_piqsavi_profile_deployed_for_url_is_exact_and_fail_closed() -> None:
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL) is True
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL) is False
    assert piqsavi_profile_deployed_for_url("https://evil.example/ucp.json") is False
    assert piqsavi_profile_deployed_for_url("") is False
    assert piqsavi_profile_deployed_for_url(None) is False
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL + "/") is False
    assert (
        piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL + "?deployed=true")
        is False
    )
    assert piqsavi_profile_deployed_for_url(TECHNICAL_TEST_AGENT_PROFILE) is False
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL in TRUSTED_PIQSAVI_UCP_AGENT_PROFILE_URLS
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL in TRUSTED_PIQSAVI_UCP_AGENT_PROFILE_URLS
    assert TECHNICAL_TEST_AGENT_PROFILE not in TRUSTED_PIQSAVI_UCP_AGENT_PROFILE_URLS


def test_live_staging_piqsavi_profile_passes_deployment_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_settings_cache()
    monkeypatch.setenv(
        "PIQSAVI_UCP_AGENT_PROFILE_URL",
        PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    )
    _clear_settings_cache()
    try:
        profile = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
        assert profile.url == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
        assert profile.piqsavi_profile_deployed is True
        assert profile.piqsavi_profile_staging_deployed is True
        assert profile.piqsavi_profile_production_deployed is False
        assert profile.shopify_has_fetched_profile is False
        assert_live_piqsavi_profile_unlocked(profile)
        payload = load_probe_fixture(DEFAULT_FIXTURE)
        report = run_ph_coverage_probe(
            transport=fixture_transport_from_payload(payload),
            live=True,
            agent_profile=profile,
        )
        assert report.live is True
        assert report.agent_profile == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
        assert report.piqsavi_profile_deployed is True
        assert report.piqsavi_profile_staging_deployed is True
        assert report.piqsavi_profile_production_deployed is False
        assert report.shopify_has_fetched_piqsavi_profile is False
        assert report.production_certified is False
        assert report.closes_sprint_32 is False
        assert report.starts_sprint_38 is False
        assert report.lookup_catalog_calls == 0
        assert report.agent_profile_source == "piqsavi"
        assert report.agent_profile_usage == "PIQSAVI_OWNED_PROFILE"
        assert "PiqSavi-owned profile selected." in report.notes
        assert "Exact selected trusted URL is owner-validated as deployed." in report.notes
        assert "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE remains false." in report.notes
        assert "Not production certification." in report.notes
        assert "Sprint 32 remains open." in report.notes
        _assert_no_stale_piqsavi_labels(report.to_dict())
        _assert_no_stale_piqsavi_labels(list(report.notes))
    finally:
        monkeypatch.delenv("PIQSAVI_UCP_AGENT_PROFILE_URL", raising=False)
        _clear_settings_cache()


def test_live_production_piqsavi_profile_remains_blocked() -> None:
    profile = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
    assert profile.url == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    assert profile.piqsavi_profile_deployed is False
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    with pytest.raises(
        LivePiqsaviProfileNotDeployedError,
        match="not yet deployed/publicly validated",
    ):
        assert_live_piqsavi_profile_unlocked(profile)


def test_sprint32_remains_open_and_sprint38_unstarted() -> None:
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    sprint38 = SPRINT38.read_text(encoding="utf-8")
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    assert "Sprint 32 remains open." in sprint32
    assert "Sprint 38 remains unstarted" in sprint32
    assert "Sprint 32 is **not complete**" in sprint32
    assert "In progress" in sprint32
    assert sprint38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"
    assert "SPRINT 32 REMAINS OPEN" in probe_doc
    assert "SPRINT 38 UNSTARTED" in probe_doc
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()


def test_staging_piqsavi_report_has_no_stale_production_labels(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_settings_cache()
    monkeypatch.setenv(
        "PIQSAVI_UCP_AGENT_PROFILE_URL",
        PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    )
    _clear_settings_cache()
    try:
        profile = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
        payload = load_probe_fixture(DEFAULT_FIXTURE)
        report = run_ph_coverage_probe(
            transport=fixture_transport_from_payload(payload),
            live=False,
            agent_profile=profile,
        )
        assert report.agent_profile == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
        assert report.agent_profile_source == "piqsavi"
        assert report.agent_profile_usage == "PIQSAVI_OWNED_PROFILE"
        assert report.piqsavi_profile_deployed is True
        assert report.piqsavi_profile_staging_deployed is True
        assert report.piqsavi_profile_production_deployed is False
        assert report.shopify_has_fetched_piqsavi_profile is False
        assert "PiqSavi-owned profile selected." in report.notes
        assert "Exact selected trusted URL is owner-validated as deployed." in report.notes
        _assert_no_stale_piqsavi_labels(report.to_dict())
        _assert_no_stale_piqsavi_labels(list(report.notes))
        outside = tmp_path / "staging-labels"
        exit_code = probe_main(
            [
                "--fixture",
                str(DEFAULT_FIXTURE),
                "--agent-profile-source",
                "piqsavi",
                "--output-dir",
                str(outside),
            ]
        )
        assert exit_code == 0
        summary = json.loads((outside / "summary.json").read_text(encoding="utf-8"))
        assert summary["agent_profile"] == PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL
        assert summary["agent_profile_source"] == "piqsavi"
        assert summary["agent_profile_usage"] == "PIQSAVI_OWNED_PROFILE"
        _assert_no_stale_piqsavi_labels(summary)
    finally:
        monkeypatch.delenv("PIQSAVI_UCP_AGENT_PROFILE_URL", raising=False)
        _clear_settings_cache()
    production_profile = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
    assert production_profile.url == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    with pytest.raises(LivePiqsaviProfileNotDeployedError):
        assert_live_piqsavi_profile_unlocked(production_profile)


def test_owner_first_piqsavi_profile_shopify_discovery_failed() -> None:
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    inventory = (
        ROOT / "docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md"
    ).read_text(encoding="utf-8")
    audit = (
        ROOT / "docs/roadmap/evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md"
    ).read_text(encoding="utf-8")
    gap = (ROOT / "docs/roadmap/GAP_INVENTORY.md").read_text(encoding="utf-8")
    for text in (sprint32, probe_doc, inventory, audit, gap):
        assert "HTTP/2 200" in text
        assert "HTTP 422" in text
        assert "profile_malformed" in text
        assert "Missing services" in text
        assert "-32001" in text
        assert "UCP discovery failed" in text
        assert "PUBLIC PROFILE REACHABLE = yes" in text
        assert "SHOPIFY DISCOVERY ATTEMPTED = yes" in text
        assert "SUCCESSFUL UCP NEGOTIATION = no" in text
        assert "PRODUCTION CERTIFIED = no" in text
        assert "SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE" in text
        assert "sprint 32 remains open" in text.casefold() or "SPRINT 32 REMAINS OPEN" in text
        assert "Sprint 38 remains unstarted" in text or "SPRINT 38 UNSTARTED" in text
    assert "search_catalog" in probe_doc
    assert "wireless earbuds" in probe_doc
    assert "no get_product" in probe_doc.casefold() or "get_product = 0" in probe_doc
    assert "lookup_catalog" in probe_doc
    assert "pagination" in probe_doc.casefold()
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert piqsavi_profile_is_shopify_negotiated() is False


def test_piqsavi_source_and_usage_labels_are_environment_neutral() -> None:
    assert AGENT_PROFILE_SOURCE_PIQSAVI == "piqsavi"
    assert AGENT_PROFILE_USAGE_PIQSAVI == "PIQSAVI_OWNED_PROFILE"
    probe_src = PROBE_MODULE.read_text(encoding="utf-8")
    script_src = PROBE_SCRIPT.read_text(encoding="utf-8")
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    probe_doc = PROBE_DOC.read_text(encoding="utf-8")
    _assert_no_stale_piqsavi_labels(probe_src)
    _assert_no_stale_piqsavi_labels(script_src)
    current_sprint32 = sprint32.split("### 2026-09-19", 1)[1]
    current_probe = probe_doc.split("## 2026-09-19 staging PiqSavi", 1)[1]
    _assert_no_stale_piqsavi_labels(current_sprint32)
    _assert_no_stale_piqsavi_labels(current_probe)
    assert "PIQSAVI_OWNED_PROFILE" in probe_doc
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is False
