"""Sprint 32 production-profile 404 evidence and Shopify capability-policy prep."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from app.domain.entities.decision_snapshot import AffiliateNeutralitySnapshot
from app.domain.entities.research_execution import ResearchCapability, ResearchProviderCertification
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_capability_policy import (
    POLICY_STATES,
    PRODUCTION_CERTIFIED,
    SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
    ShopifyCapabilityPolicyRow,
    piqsavi_internal_operating_rules,
    shopify_capability_policy_grants_production,
    shopify_capability_policy_index,
    shopify_global_catalog_capability_policy_rows,
    shopify_policies_by_state,
)
from app.research.shopify_global_catalog_ph_probe import (
    FORBIDDEN_LOOKUP_TOOL,
    ProbeContractError,
    build_jsonrpc_request,
    build_search_catalog_arguments,
)
from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    piqsavi_profile_deployed_for_url,
    piqsavi_profile_is_shopify_negotiated,
)

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
SPRINT41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
PROBE_DOC = ROOT / "docs/roadmap/evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md"
POLICY_MODULE = ROOT / "app/research/shopify_global_catalog_capability_policy.py"
PROFILE_MODULE = ROOT / "app/ucp/agent_profile.py"
CERTIFICATION_MODULE = ROOT / "app/research/certification.py"
REGISTRY_MODULE = ROOT / "app/research/registry.py"
ROUTING_MODULE = ROOT / "app/research/routing.py"

REQUIRED_ROWS = (
    "product_discovery",
    "current_pricing",
    "current_price",
    "product_identity",
    "variant_identity",
    "seller_identity",
    "seller_url",
    "product_url",
    "checkout_url",
    "availability",
    "ships_to_ph",
    "currency",
    "query_time_comparison",
    "normalization_within_piqsavi",
    "short_lived_retention",
    "caching_search_results",
    "persistent_product_index",
    "ai_training",
    "promoted_placement",
    "get_product",
    "lookup_catalog",
)

EVIDENCE_LINES = (
    "PRODUCTION PROFILE URL CHECKED = yes",
    "PRODUCTION PROFILE HTTP STATUS = 404",
    "PRODUCTION PROFILE DEPLOYED = no",
    "PRODUCTION PROFILE VALIDATED = no",
    "PRODUCTION PROFILE NEGOTIATED = no",
    "PRODUCTION CERTIFIED = no",
    "AWS MUTATION = no",
    "DEPLOYMENT = no",
    "SHOPIFY CALL = no",
    "Production profile deployment belongs to the later Sprint 41 production "
    "environment/deployment path and is not being pulled forward into Sprint 32.",
)


def test_production_profile_404_keeps_deployed_constant_false_today() -> None:
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is True
    assert piqsavi_profile_is_shopify_negotiated() is True
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL) is True
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL) is False
    production = PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    assert piqsavi_profile_deployed_for_url(production + "/") is False
    assert piqsavi_profile_deployed_for_url(production + "?deployed=true") is False


def test_historical_404_does_not_block_a_future_production_deployed_constant() -> None:
    source = PROFILE_MODULE.read_text(encoding="utf-8")
    assert "ProductionProfileHttpCheck" not in source
    assert "PRODUCTION_PROFILE_HTTP_CHECK" not in source
    assert "PRODUCTION_PROFILE_CHECK_DATE" not in source
    assert "PRODUCTION_PROFILE_DEPLOYMENT_OWNER_SPRINT" not in source
    assert "must remain false" not in source.casefold()
    needle = "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED: Final = False"
    assert needle in source
    patched = source.replace(needle, needle.replace("False", "True"), 1)
    namespace: dict[str, object] = {
        "__name__": "piqsavi_profile_future_deploy_probe",
        "__file__": str(PROFILE_MODULE),
    }
    exec(compile(patched, str(PROFILE_MODULE), "exec"), namespace)
    assert namespace["PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED"] is True
    deployed_for_url = namespace["piqsavi_profile_deployed_for_url"]
    assert deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL) is True
    assert deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_STAGING_URL) is True
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL) is False


def test_production_404_evidence_is_recorded_without_a_deploy_claim() -> None:
    documents = (
        SPRINT32.read_text(encoding="utf-8"),
        ROADMAP.read_text(encoding="utf-8"),
        PROBE_DOC.read_text(encoding="utf-8"),
    )
    for text in documents:
        for line in EVIDENCE_LINES:
            assert line in text
        assert "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED" in text
        assert "production certified" in text.casefold()
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    assert "PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` remains **False**" in sprint32
    assert "Sprint 32 is **not complete**" in sprint32
    assert "Sprint 32 acceptance criteria are unchanged" in sprint32
    assert "does not close this sprint" in sprint32
    lowered = sprint32.casefold()
    assert "production profile deployed = yes" not in lowered
    assert "production certified = yes" not in lowered
    assert "piqsavi_ucp_agent_profile_production_deployed = true" not in lowered
    assert "piqsavi_ucp_agent_profile_production_deployed: final = true" not in lowered


def test_roadmap_defers_production_profile_deploy_to_sprint_41() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    sprint41 = SPRINT41.read_text(encoding="utf-8")
    assert "Production UCP profile sequencing (Sprint 32 vs Sprint 41)" in roadmap
    assert "must not force an early production deployment" in roadmap
    assert "Sprint 41 implementation is not started" in roadmap
    assert "Operative sequence" in sprint32
    assert "Defer production-profile deployment and production HTTPS validation to Sprint 41" in (
        sprint32
    )
    assert sprint41.split("**Status:**", 1)[1].splitlines()[0].strip().startswith("Planned")
    assert "not started" in sprint41.split("**Status:**", 1)[1].splitlines()[0].casefold()
    assert "does not start this sprint" in sprint41
    assert "Sprint 32 must not pull production deploy forward" in sprint41
    sprint38 = SPRINT38.read_text(encoding="utf-8")
    assert sprint38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"


def _sample_row(**overrides: object) -> ShopifyCapabilityPolicyRow:
    payload: dict[str, object] = {
        "row_id": "sample",
        "label": "sample",
        "research_capability": None,
        "technical_exposure": "observed",
        "policy": "allowed",
        "shopper_applicability": "not_applicable",
        "evidence_note": "structural sample",
        "restrictions": ("query-time",),
    }
    payload.update(overrides)
    return ShopifyCapabilityPolicyRow(**payload)  # type: ignore[arg-type]


def test_shopify_capability_map_keeps_exposure_policy_and_probe_rules_apart() -> None:
    rows = shopify_global_catalog_capability_policy_rows()
    index = shopify_capability_policy_index()
    grouped = shopify_policies_by_state()
    assert set(index) >= set(REQUIRED_ROWS)
    assert "affiliate_neutrality" not in index
    assert "raw_response_persistence" not in index
    assert grouped["allowed"]
    assert shopify_capability_policy_grants_production() is False
    assert PRODUCTION_CERTIFIED is False
    for row in rows:
        assert row.policy in POLICY_STATES
        assert row.production_eligible is False
        assert row.shopper_applicability != "applicable"
        if row.policy == "unknown":
            assert row.shopper_applicability != "applicable"
    observed_policies = {row.policy for row in rows if row.technical_exposure == "observed"}
    assert "allowed" in observed_policies
    assert len(observed_policies) > 1
    allowed_observed = _sample_row(technical_exposure="observed", policy="allowed")
    observed_restricted = _sample_row(
        row_id="other",
        technical_exposure="observed",
        policy="restricted",
    )
    assert allowed_observed.policy == "allowed"
    assert observed_restricted.policy == "restricted"
    assert allowed_observed.technical_exposure == observed_restricted.technical_exposure
    with pytest.raises(ValueError, match="unknown permission"):
        _sample_row(policy="unknown", shopper_applicability="applicable")
    discovery = index["product_discovery"]
    assert discovery.research_capability is ResearchCapability.PRODUCT_DISCOVERY
    assert discovery.technical_exposure == "observed"
    assert discovery.policy == "allowed"
    assert "query-time" in discovery.restrictions
    assert index["current_pricing"].policy == "allowed"
    assert index["current_pricing"].research_capability is ResearchCapability.CURRENT_PRICING
    assert "do not cache search results" in index["current_pricing"].restrictions
    assert index["availability"].policy == "allowed"
    assert index["query_time_comparison"].policy == "allowed"
    assert index["get_product"].policy == "allowed"
    assert index["get_product"].technical_exposure == "observed"
    assert index["normalization_within_piqsavi"].technical_exposure == "unknown"
    assert index["normalization_within_piqsavi"].policy == "restricted"
    assert index["short_lived_retention"].policy == "restricted"
    assert index["ships_to_ph"].policy == "allowed"
    assert index["ships_to_ph"].shopper_applicability == "unknown"
    assert index["ships_to_ph"].research_capability is None
    assert index["destination_shipping_amount"].policy == "unknown"
    shipping = index["destination_shipping_amount"]
    assert shipping.research_capability is ResearchCapability.SHIPPING
    lookup = index["lookup_catalog"]
    assert lookup.policy == "restricted"
    assert lookup.policy != "prohibited"
    assert lookup.technical_exposure == "documented_not_observed"
    placement = index["promoted_placement"]
    assert placement.policy == "unknown"
    assert placement.policy != "prohibited"
    assert placement.technical_exposure == "documented_not_observed"
    for row_id in ("caching_search_results", "persistent_product_index", "ai_training"):
        assert index[row_id].policy == "prohibited"
        assert index[row_id].shopper_applicability == "not_applicable"
    assert "unless required Shopify or merchant consent exists" in index["ai_training"].restrictions
    for row_id in (
        "seller_discount",
        "platform_discount",
        "voucher_promotion",
        "voucher_eligibility",
        "free_shipping",
        "checkout_other_costs",
    ):
        assert index[row_id].policy == "unknown"
        assert index[row_id].technical_exposure == "unknown"
    rules = {rule.rule_id: rule for rule in piqsavi_internal_operating_rules()}
    assert rules["probe_lookup_catalog_disabled"].mode == "disabled"
    assert rules["promoted_placement_disabled"].mode == "disabled"
    assert rules["probe_raw_payload_not_stored"].mode == "no_raw_payload"
    assert rules["commission_based_organic_ranking"].mode == "integrity"
    assert set(rules).isdisjoint(index)
    AffiliateNeutralitySnapshot()
    with pytest.raises(ValueError, match="affiliate influence"):
        AffiliateNeutralitySnapshot(commission_influenced_ordering=True)
    arguments = build_search_catalog_arguments("wireless earbuds")
    with pytest.raises(ProbeContractError, match="lookup_catalog"):
        build_jsonrpc_request(FORBIDDEN_LOOKUP_TOOL, arguments, request_id=2)
    future_certification = ResearchProviderCertification(
        provider_id="documentary-only",
        capability=ResearchCapability.PRODUCT_DISCOVERY,
        market="PH",
        certification_version="not-registered",
        status="certified",
        policy="allowed",
        source="shopify_global_catalog",
        test_fixture=False,
    )
    assert future_certification.is_production_eligible is True
    unknown_certification = ResearchProviderCertification(
        provider_id="documentary-only",
        capability=ResearchCapability.PRODUCT_DISCOVERY,
        market="PH",
        certification_version="not-registered",
        status="certified",
        policy="unknown",
        source="shopify_global_catalog",
        test_fixture=False,
    )
    assert unknown_certification.is_production_eligible is False
    registry = production_research_provider_registry()
    provider_ids = {provider.provider_id for provider in registry.list_providers()}
    assert SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID not in provider_ids
    assert production_research_provider_certification_catalog().list_records() == ()


def test_capability_prep_does_not_populate_production_registries_or_start_later_sprints() -> None:
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    policy_tree = ast.parse(POLICY_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(policy_tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "app.research.certification" not in imported
    assert "app.research.registry" not in imported
    assert "app.research.routing" not in imported
    for path in (CERTIFICATION_MODULE, REGISTRY_MODULE, ROUTING_MODULE):
        source = path.read_text(encoding="utf-8")
        assert "shopify_global_catalog_capability_policy" not in source
        assert "ph-shopify-global-catalog" not in source
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    assert "Sprint 32 remains open." in sprint32
    assert "Sprint 38 remains unstarted" in sprint32
    assert "Sprint 41 implementation is not started" in sprint32
    status = next(line for line in sprint32.splitlines() if line.startswith("**Status:**"))
    assert "In progress" in status
    assert "not complete" in status.casefold()
