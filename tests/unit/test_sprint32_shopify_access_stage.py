"""Sprint 32 Shopify Anonymous catalog access stages and real evidence rows."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pytest
from app.domain.entities.decision_snapshot import AffiliateNeutralitySnapshot
from app.domain.entities.research_certification_decision import CertificationDecisionRequest
from app.domain.entities.research_execution import ResearchCapability
from app.research.certification import (
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.certification_evidence import (
    make_research_provider_certification_evidence,
    production_research_provider_certification_evidence_catalog,
    research_provider_certification_evidence_catalog_for_tests,
)
from app.research.market_access_path import (
    LegitimateAccessPath,
    access_requirements_satisfied,
    known_market_access_paths,
    lazada_ext01_product_data_access_path,
    may_name_market,
    missing_credentials_block_path,
    missing_provider_preapproval_blocks_path,
    shopee_ext01_product_data_access_path,
    shopify_anonymous_global_catalog_access_path,
)
from app.research.registry import (
    production_research_provider_registry,
    research_provider_registry_for_tests,
)
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import (
    APPLICATION_NOT_REQUIRED,
    PREAPPROVAL_NOT_REQUIRED,
    PRODUCTION_PROFILE_UNDEPLOYED,
    STAGING_AGENT_PROFILE_VALIDATED,
    TECHNICAL_CONNECTION_VALIDATED,
    anonymous_global_catalog_access_stage,
    shopify_anonymous_catalog_stage_truth,
)
from app.research.shopify_global_catalog_capability_policy import (
    piqsavi_internal_operating_rules,
    shopify_capability_policy_index,
    shopify_global_catalog_capability_policy_rows,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_EVIDENCE_CAPABILITIES,
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
    SHOPIFY_PERMANENT_OPERATING_CONDITIONS,
    SHOPIFY_UNRESOLVED_CERTIFICATION_RESTRICTIONS,
    shopify_global_catalog_certification_evidence_records,
)
from app.research.shopify_global_catalog_ph_probe import (
    AGENT_PROFILE_SOURCE_PIQSAVI,
    LivePiqsaviProfileNotDeployedError,
    select_agent_profile,
)
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)
from app.services.research_execution_router import plan_authorized_research
from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED,
    PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL,
    PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED,
    SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE,
    piqsavi_profile_deployed_for_url,
)

from tests.unit.production_catalog_boundaries import assert_production_shopify_evidence_only
from tests.unit.test_phase_29_4b_refine_session_recommendation import _owner
from tests.unit.test_sprint31_certification_authority import _pricing_scope
from tests.unit.test_sprint31_research_execution_router import _authorization, _provider

ROOT = Path(__file__).resolve().parents[2]
REGISTER = (ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md").read_text(encoding="utf-8")
SPRINT32_PATH = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
SPRINT32 = SPRINT32_PATH.read_text(encoding="utf-8")
SPRINT38 = (ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md").read_text(
    encoding="utf-8"
)
SPRINT41 = (ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md").read_text(
    encoding="utf-8"
)
ROADMAP = (ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md").read_text(encoding="utf-8")
NEW_MODULES = (
    ROOT / "app/research/shopify_global_catalog_access_stage.py",
    ROOT / "app/research/shopify_global_catalog_certification_evidence.py",
    ROOT / "app/research/market_access_path.py",
)


def _status_cell(row_id: str) -> str:
    for line in REGISTER.splitlines():
        if line.startswith(f"| {row_id} |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            return cells[7]
    raise AssertionError(f"missing register row {row_id}")


def _shopify_decision(policy: str) -> CertificationDecisionRequest:
    return CertificationDecisionRequest(
        provider_id="ph-shopify-global-catalog",
        capability=ResearchCapability.PRODUCT_DISCOVERY,
        market="PH",
        source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        requested_status="certified",
        requested_policy=policy,
        certification_version="evidence-is-not-certification",
        reviewer="Sprint 32 access-stage test",
        decided_at=date(2026, 9, 23),
    )


def test_anonymous_catalog_mode_does_not_require_credentials_or_approval() -> None:
    stage = anonymous_global_catalog_access_stage()
    assert stage.credentials_required is False
    assert stage.agent_profile_required is True
    assert stage.application_required is False
    assert stage.application_disposition == APPLICATION_NOT_REQUIRED
    assert stage.separate_provider_preapproval_required is False
    assert stage.preapproval_disposition == PREAPPROVAL_NOT_REQUIRED
    assert stage.signed_or_token_required_for_anonymous_catalog_tools is False
    assert stage.promoted_placement_enrolled is False
    assert stage.promoted_placement_enabled is False
    assert stage.promoted_placement_policy == "unknown"


def test_staging_connection_is_validated_and_production_stays_uncertified() -> None:
    stage = anonymous_global_catalog_access_stage()
    truth = shopify_anonymous_catalog_stage_truth()
    assert PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED is True
    assert SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE is True
    assert stage.staging_agent_profile_deployed is True
    assert stage.staging_agent_profile_disposition == STAGING_AGENT_PROFILE_VALIDATED
    assert stage.technical_connection_validated is True
    assert stage.technical_connection_disposition == TECHNICAL_CONNECTION_VALIDATED
    assert stage.ph_technical_coverage_validated is True
    assert stage.contractual_reduced_mode_evidence == "recorded/prepared"
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert stage.production_profile_deployed is False
    assert stage.production_profile_disposition == PRODUCTION_PROFILE_UNDEPLOYED
    assert stage.production_certified is False
    assert stage.production_ready is False
    assert truth["production_certified"] == "NO"
    assert truth["production_profile"] == "not deployed"
    assert truth["production_provider"] == "registered, operationally disabled"
    assert truth["executable_production_certification"] == "none"
    assert truth["routing"] == "none"
    assert truth["production_ready"] == "NO"
    assert truth["credentials"] == "N/A / not required for Anonymous catalog mode"
    joined = " ".join(str(value) for value in stage.to_dict().values())
    for phrase in (
        "shopify partner",
        "endorsed by shopify",
        "preferred developer",
        "preferred-developer",
        "production-app approval",
        "special approval",
    ):
        assert phrase not in joined.casefold()


def test_ext01_stays_applied_and_ext06_does_not_block_anonymous_shopify() -> None:
    assert _status_cell("EXT-01") == "`applied`"
    assert _status_cell("EXT-06") == "`not_started`"
    assert "`provisioned`" not in _status_cell("EXT-01")
    assert "`provisioned`" not in _status_cell("EXT-06")
    assert "NOT APPLICABLE" in REGISTER
    assert "S-1 Anonymous Shopify Global Catalog" in REGISTER
    assert "Do not mark this row `provisioned`" in REGISTER
    shopee = shopee_ext01_product_data_access_path()
    lazada = lazada_ext01_product_data_access_path()
    assert shopee.application_state == "applied"
    assert lazada.application_state == "applied"
    assert shopee.provider_preapproval_state == "not_approved"
    assert lazada.provider_preapproval_state == "not_approved"
    assert shopee.credentials_state == "not_issued"
    assert lazada.credentials_state == "not_issued"
    assert access_requirements_satisfied(shopee) is False
    assert access_requirements_satisfied(lazada) is False
    assert missing_credentials_block_path(shopee) is True
    assert missing_credentials_block_path(lazada) is True
    shopify = shopify_anonymous_global_catalog_access_path()
    assert shopify.credentials_required is False
    assert missing_credentials_block_path(shopify) is False
    assert "NOT APPLICABLE" in REGISTER.split("EXT-06", 1)[1][:2500]


def test_market_naming_accepts_documented_keyless_paths_only() -> None:
    shopify = shopify_anonymous_global_catalog_access_path()
    assert shopify.official_keyless_anonymous_mode_documented is True
    assert access_requirements_satisfied(shopify) is True
    assert missing_provider_preapproval_blocks_path(shopify) is False
    assert may_name_market(shopify) is False
    documented = [
        path
        for path in known_market_access_paths()
        if path.official_keyless_anonymous_mode_documented
    ]
    assert [path.path_id for path in documented] == ["s1-shopify-global-catalog-anonymous"]
    undocumented = LegitimateAccessPath(
        path_id="undocumented-keyless-claim",
        market="PH",
        application_required=False,
        separate_provider_preapproval_required=False,
        credentials_required=False,
        official_keyless_anonymous_mode_documented=False,
        application_state="not_required",
        provider_preapproval_state="not_required",
        credentials_state="not_required",
        remaining_certification_satisfied=True,
    )
    assert access_requirements_satisfied(undocumented) is False
    assert may_name_market(undocumented) is False
    credentialed = LegitimateAccessPath(
        path_id="credential-required-example",
        market="PH",
        application_required=True,
        separate_provider_preapproval_required=True,
        credentials_required=True,
        official_keyless_anonymous_mode_documented=False,
        application_state="satisfied",
        provider_preapproval_state="approved",
        credentials_state="issued",
        remaining_certification_satisfied=False,
    )
    assert access_requirements_satisfied(credentialed) is True
    assert may_name_market(credentialed) is False
    waived_by_lie = LegitimateAccessPath(
        path_id="credential-required-called-keyless",
        market="PH",
        application_required=True,
        separate_provider_preapproval_required=True,
        credentials_required=True,
        official_keyless_anonymous_mode_documented=True,
        application_state="applied",
        provider_preapproval_state="not_approved",
        credentials_state="not_issued",
        remaining_certification_satisfied=False,
    )
    assert access_requirements_satisfied(waived_by_lie) is False
    assert "does not weaken Shopee, Lazada" in REGISTER
    assert "actual access requirements are satisfied" in ROADMAP


def test_production_evidence_is_shopify_only_and_grants_nothing() -> None:
    records = shopify_global_catalog_certification_evidence_records()
    assert len(records) == 4
    assert [record.capability for record in records] == list(SHOPIFY_EVIDENCE_CAPABILITIES)
    for record in records:
        assert record.provider_id == "ph-shopify-global-catalog"
        assert record.market == "PH"
        assert record.source == SHOPIFY_GLOBAL_CATALOG_SOURCE
        assert record.completeness == "recorded"
        assert record.evidence_date == date(2026, 9, 25)
        assert record.review_date == date(2026, 9, 25)
        assert "attempt #3" in record.notes
        assert "fail-closed" in record.notes
        assert "ambiguous_or_insufficient_matches_count 5" in record.notes
        assert record.reviewer
        assert "counsel approval" in record.reviewer
        assert record.program_reference
        assert record.restrictions == SHOPIFY_UNRESOLVED_CERTIFICATION_RESTRICTIONS == ()
        assert record.attribution_requirements
        assert "retain source and seller attribution" in record.attribution_requirements
        assert record.review_after is None
        assert "evidence, not certification" in record.notes
        for condition in SHOPIFY_PERMANENT_OPERATING_CONDITIONS:
            assert condition in record.notes
            assert condition not in record.restrictions
        for absent in (
            "shipping",
            "promotion",
            "voucher",
            "production profile",
            "provider not registered",
            "Sprint 32",
        ):
            assert absent.casefold() not in " ".join(record.restrictions).casefold()
        assert record.grants_certification is False
        assert record.grants_eligibility is False
        assert record.is_decision_ready(as_of=date(2026, 9, 23)) is True
    assert_production_shopify_evidence_only()
    assert len(production_research_provider_registry().list_providers()) == 1
    assert len(production_research_provider_certification_catalog().list_records()) == 4
    assert len(production_research_provider_certification_evidence_catalog().list_records()) == 4
    assert len(production_research_provider_routing_policy_catalog().list_records()) == 0
    service = ResearchProviderCertificationDecisionService(
        production_research_provider_certification_evidence_catalog(),
        production_research_provider_certification_catalog(),
        production_research_provider_registry(),
    )
    allowed = service.decide(_shopify_decision("allowed"))
    restricted = service.decide(_shopify_decision("restricted"))
    assert allowed.accepted is False
    assert allowed.reason == "version_mismatch"
    assert allowed.certification is None
    assert restricted.accepted is False
    assert restricted.reason == "version_mismatch"
    assert restricted.certification is None
    assert len(production_research_provider_certification_catalog().list_records()) == 4
    authorization = _authorization(_pricing_scope(source=SHOPIFY_GLOBAL_CATALOG_SOURCE))
    planned = plan_authorized_research(
        authorization,
        owner=_owner(),
        conversation_id=authorization.conversation_id,
        decision_id=authorization.decision_id,
        canonical_context_version=authorization.canonical_context_version,
        registry=production_research_provider_registry(),
    )
    assert planned.plan is not None
    assert planned.plan.eligible_steps == ()
    index = shopify_capability_policy_index()
    assert index["product_discovery"].policy == "allowed"
    assert index["query_time_comparison"].policy == "allowed"
    assert index["current_pricing"].policy == "allowed"
    assert index["availability"].policy == "allowed"
    assert "query-time" in index["product_discovery"].restrictions
    assert index["caching_search_results"].policy == "prohibited"
    assert index["persistent_product_index"].policy == "prohibited"
    assert index["ai_training"].policy == "prohibited"
    assert index["short_lived_retention"].policy == "restricted"
    assert index["lookup_catalog"].policy == "restricted"
    assert index["normalization_within_piqsavi"].policy == "restricted"


def test_synthetic_allowed_certification_succeeds_when_blockers_are_clear() -> None:
    """Architecture path only. Test catalogs. Not a production Shopify certification."""

    source_row = shopify_global_catalog_certification_evidence_records()[0]
    assert source_row.capability is ResearchCapability.PRODUCT_DISCOVERY
    assert source_row.restrictions == ()
    provider_id = "test-shopify-like-allowed"
    evidence = make_research_provider_certification_evidence(
        provider_id=provider_id,
        capability=source_row.capability,
        market=source_row.market,
        source=source_row.source,
        evidence_source="tests/unit/test_sprint32_shopify_access_stage.py",
        program_reference=source_row.program_reference,
        evidence_date=source_row.evidence_date,
        review_date=source_row.review_date,
        reviewer="Sprint 32 synthetic architecture regression",
        restrictions=(),
        attribution_requirements=source_row.attribution_requirements,
        completeness="recorded",
        notes=source_row.notes,
        test_fixture=True,
    )
    for condition in SHOPIFY_PERMANENT_OPERATING_CONDITIONS:
        assert condition in evidence.notes
        assert condition not in evidence.restrictions
    provider = _provider(
        provider_id,
        markets=("PH",),
        capabilities=(ResearchCapability.PRODUCT_DISCOVERY,),
        sources=(SHOPIFY_GLOBAL_CATALOG_SOURCE,),
    )
    assert provider.descriptor.test_fixture is True
    registry = research_provider_registry_for_tests((provider,))
    certifications = research_provider_certification_catalog_for_tests(())
    service = ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests((evidence,)),
        certifications,
        registry,
    )
    result = service.decide(
        CertificationDecisionRequest(
            provider_id=provider_id,
            capability=ResearchCapability.PRODUCT_DISCOVERY,
            market="PH",
            source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
            requested_status="certified",
            requested_policy="allowed",
            certification_version="synthetic-allowed-v1",
            reviewer="Sprint 32 synthetic architecture regression",
            decided_at=date(2026, 9, 23),
        )
    )
    assert result.accepted is True
    assert result.reason == "approved"
    assert result.certification is not None
    assert result.certification.status == "certified"
    assert result.certification.policy == "allowed"
    assert result.certification.test_fixture is True
    assert result.certification.is_production_eligible is False
    assert result.certification.provider_id == provider_id
    assert registry.get(provider_id) is provider
    assert certifications.list_records() == (result.certification,)
    blocked = make_research_provider_certification_evidence(
        provider_id=provider_id,
        capability=source_row.capability,
        market=source_row.market,
        source=source_row.source,
        evidence_source="tests/unit/test_sprint32_shopify_access_stage.py",
        evidence_date=source_row.evidence_date,
        review_date=source_row.review_date,
        reviewer="Sprint 32 synthetic architecture regression",
        restrictions=("query-time use only",),
        completeness="recorded",
        notes=source_row.notes,
        test_fixture=True,
    )
    blocked_result = ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests((blocked,)),
        research_provider_certification_catalog_for_tests(()),
        registry,
    ).decide(
        CertificationDecisionRequest(
            provider_id=provider_id,
            capability=ResearchCapability.PRODUCT_DISCOVERY,
            market="PH",
            source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
            requested_status="certified",
            requested_policy="allowed",
            certification_version="synthetic-allowed-v1",
            reviewer="Sprint 32 synthetic architecture regression",
            decided_at=date(2026, 9, 23),
        )
    )
    assert blocked_result.accepted is False
    assert blocked_result.reason == "restrictions_unresolved"
    assert blocked_result.certification is None
    assert_production_shopify_evidence_only()
    assert len(production_research_provider_registry().list_providers()) == 1
    assert len(production_research_provider_certification_catalog().list_records()) == 4
    assert len(production_research_provider_routing_policy_catalog().list_records()) == 0
    assert production_research_provider_registry().get("ph-shopify-global-catalog") is not None
    assert production_research_provider_registry().get(provider_id) is None


def test_shipping_and_promotion_stay_unknown_and_fail_closed() -> None:
    evidenced = {
        record.capability for record in shopify_global_catalog_certification_evidence_records()
    }
    assert ResearchCapability.SHIPPING not in evidenced
    assert ResearchCapability.PROMOTION_EVIDENCE not in evidenced
    index = shopify_capability_policy_index()
    assert index["destination_shipping_amount"].policy == "unknown"
    assert index["destination_shipping_amount"].research_capability is ResearchCapability.SHIPPING
    assert index["voucher_promotion"].policy == "unknown"
    assert index["voucher_promotion"].research_capability is ResearchCapability.PROMOTION_EVIDENCE
    assert index["promoted_placement"].policy == "unknown"
    for row in shopify_global_catalog_capability_policy_rows():
        if row.policy == "unknown":
            assert row.shopper_applicability != "applicable"
    rules = {rule.rule_id: rule for rule in piqsavi_internal_operating_rules()}
    assert rules["commission_based_organic_ranking"].mode == "integrity"
    AffiliateNeutralitySnapshot()
    with pytest.raises(ValueError, match="affiliate influence"):
        AffiliateNeutralitySnapshot(commission_influenced_ordering=True)


def test_production_profile_stays_fail_closed_and_no_shopify_client_is_imported() -> None:
    assert piqsavi_profile_deployed_for_url(PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL) is False
    profile = select_agent_profile(AGENT_PROFILE_SOURCE_PIQSAVI)
    assert profile.url == PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_URL
    with pytest.raises(LivePiqsaviProfileNotDeployedError):
        from app.research.shopify_global_catalog_ph_probe import (
            assert_live_piqsavi_profile_unlocked,
        )

        assert_live_piqsavi_profile_unlocked(profile)
    forbidden_imports = {"httpx", "requests", "urllib", "urllib.request", "socket"}
    for path in NEW_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert imported.isdisjoint(forbidden_imports)
        source = path.read_text(encoding="utf-8")
        assert "httpx." not in source
        assert "catalog.shopify.com" not in source


def test_sprint_32_stays_open_and_later_sprints_stay_unstarted() -> None:
    truth = shopify_anonymous_catalog_stage_truth()
    assert truth["sprint_32"] == "COMPLETE / CLOSED"
    assert truth["sprint_38"] == "UNSTARTED"
    assert truth["sprint_41"] == "UNSTARTED"
    status = next(line for line in SPRINT32.splitlines() if line.startswith("**Status:**"))
    assert "COMPLETE / CLOSED" in status
    assert "not production-deployment ready" in status.casefold()
    assert "Sprint 32 remains open." in SPRINT32
    assert "Sprint 38 remains unstarted" in SPRINT32
    assert "Sprint 41 remains unstarted" in SPRINT32
    assert "No merchant has a real approved product-data / API path" not in SPRINT32
    assert "production ready" in SPRINT32.casefold()
    assert SPRINT38.split("**Status:**", 1)[1].splitlines()[0].strip() == "Planned"
    sprint41_status = SPRINT41.split("**Status:**", 1)[1].splitlines()[0].strip()
    assert sprint41_status.startswith("Planned")
    assert "not started" in sprint41_status.casefold()
