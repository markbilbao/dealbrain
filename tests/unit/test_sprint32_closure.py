"""Sprint 32 closure. No Shopify calls, no harness edits, no production deploy."""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import ConnectorOperationalStatus, KillSwitch
from app.domain.entities.research_execution import ResearchCapability
from app.market.coverage import (
    PH_PREPARING_COVERAGE_DISCLOSURE,
    assess_shopping_coverage,
    connector_invocation_eligible,
)
from app.market.support import production_certified_shopping_markets
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import (
    SPRINT_32_STATUS,
    anonymous_global_catalog_access_stage,
)
from app.research.shopify_global_catalog_provider import shopify_global_catalog_ph_provider
from app.research.shopify_global_catalog_sprint32_closure import (
    CERTIFIED_CAPABILITIES,
    ENGINEERING_KILL_SWITCH_VALIDATION,
    FORBIDDEN_MONITORING_LABELS,
    NOT_PRODUCTION_DEPLOYMENT_READY,
    PUBLIC_PH_COVERAGE_DISCLOSURE,
    SELECTED_PATH,
    SPRINT_32_CLOSURE_DATE,
    SPRINT_38_STATUS,
    SPRINT_41_STATUS,
    STAGING_CERTIFICATION,
    STAGING_CERTIFICATION_SCOPE,
    UNCERTIFIED_CAPABILITIES,
    real_provider_descriptor_for_kill_switch_check,
    real_provider_eligibility_reasons,
    real_provider_is_operationally_available,
    shopify_reduced_path_effective_cost_table,
)
from app.research.shopify_global_catalog_sprint32_closure import (
    SPRINT_32_STATUS as CLOSURE_STATUS,
)
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

ROOT = Path(__file__).resolve().parents[2]
COMPLETION = ROOT / "docs/roadmap/evidence/SPRINT_32_COMPLETION.md"
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
SPRINT41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
HEALTH = ROOT / "docs/CONNECTOR_HEALTH.md"
HARNESS = ROOT / "scripts/shopify_global_catalog_normalization_validation.py"
CLOSURE_MODULE = ROOT / "app/research/shopify_global_catalog_sprint32_closure.py"
_ALLOWED_RESULTS = {
    "PASS",
    "DEFERRED TO SPRINT 38",
    "DEFERRED TO SPRINT 38 / 42",
    "DEFERRED TO SPRINT 41",
    "DEFERRED TO SPRINT 41 / 44 / 45",
    "DEFERRED TO SPRINT 38/41",
    "DEFERRED TO SPRINT 44",
    "NOT APPLICABLE TO SELECTED PATH",
}


def _status_line(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(line for line in lines if line.startswith("**Status:**"))


def test_selected_path_is_the_reduced_shopify_path() -> None:
    completion = COMPLETION.read_text(encoding="utf-8")
    assert SELECTED_PATH in completion
    assert "Shopify Global Catalog Anonymous reduced capability path" in completion
    assert [item.value for item in CERTIFIED_CAPABILITIES] == [
        "product_discovery",
        "offer_discovery",
        "current_pricing",
        "availability",
    ]
    stage = anonymous_global_catalog_access_stage()
    assert stage.catalog_mode == "anonymous_global_catalog"
    assert stage.production_ready is False
    assert stage.production_certified is False


def test_staging_certification_closure_evidence_exists() -> None:
    completion = COMPLETION.read_text(encoding="utf-8")
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    assert STAGING_CERTIFICATION == "PASSED"
    assert STAGING_CERTIFICATION_SCOPE == "REDUCED CAPABILITY SET ONLY"
    assert NOT_PRODUCTION_DEPLOYMENT_READY in completion
    assert "SPRINT 32 STAGING CERTIFICATION = PASSED" in sprint32
    assert "NOT PRODUCTION DEPLOYMENT READY" in sprint32
    assert "operationally live" in sprint32.casefold()
    assert SPRINT_32_CLOSURE_DATE.isoformat() == "2026-09-25"


def test_real_provider_kill_switch_engaged_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Shopify or other network call")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    descriptor = real_provider_descriptor_for_kill_switch_check(
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(engaged=True, reason="server-owned"),
    )
    assert descriptor.provider_id == "ph-shopify-global-catalog"
    assert descriptor.test_fixture is False
    assert descriptor.is_operationally_available is False
    assert (
        real_provider_is_operationally_available(
            descriptor,
            browser_disengage_kill_switch=True,
            request_disengage_kill_switch=True,
            shopper_disengage_kill_switch=True,
        )
        is False
    )
    assert "kill_switch" in real_provider_eligibility_reasons(descriptor)
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    provider = production_research_provider_registry().get("ph-shopify-global-catalog")
    assert provider is not None
    with pytest.raises(NotImplementedError):
        provider.execute(None)  # type: ignore[arg-type]
    assert ENGINEERING_KILL_SWITCH_VALIDATION == "PASSED"


def test_client_input_cannot_disengage_kill_switch() -> None:
    descriptor = real_provider_descriptor_for_kill_switch_check(
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(engaged=True, reason="server-owned"),
    )
    assert (
        real_provider_is_operationally_available(
            descriptor,
            browser_disengage_kill_switch=True,
            request_disengage_kill_switch=True,
            shopper_disengage_kill_switch=True,
        )
        is False
    )
    assert descriptor.kill_switch.engaged is True


def test_production_provider_stays_disabled_when_kill_switch_is_off() -> None:
    before = shopify_global_catalog_ph_provider().descriptor
    copy = real_provider_descriptor_for_kill_switch_check(
        operational_status=ConnectorOperationalStatus.DISABLED,
        kill_switch=KillSwitch(engaged=False),
    )
    assert copy.is_operationally_available is False
    stored = production_research_provider_registry().get("ph-shopify-global-catalog")
    assert stored is not None
    assert stored.descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    assert stored.descriptor.is_operationally_available is False
    assert before.operational_status is ConnectorOperationalStatus.DISABLED
    assert production_research_provider_registry().get("ph-shopify-global-catalog") is not None


def test_routing_count_remains_zero() -> None:
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert len(production_research_provider_registry().list_providers()) == 1


def test_public_certified_market_catalog_remains_empty() -> None:
    catalog = production_certified_shopping_markets()
    assert catalog.to_tuple() == ()
    assert catalog.is_certified("PH") is False


def test_ph_public_connector_invocation_remains_false() -> None:
    assert connector_invocation_eligible() is False
    coverage = assess_shopping_coverage()
    assert coverage.connector_invocation_eligible is False
    assert coverage.certified is False


def test_current_ph_disclosure_remains_truthful() -> None:
    coverage = assess_shopping_coverage()
    assert coverage.disclosure == PH_PREPARING_COVERAGE_DISCLOSURE
    assert PUBLIC_PH_COVERAGE_DISCLOSURE == (
        "PiqSavi is preparing shopping-source coverage for the Philippines."
    )
    lowered = coverage.disclosure.casefold()
    assert "shopee" not in lowered
    assert "lazada" not in lowered
    assert "complete" not in lowered
    assert "partner" not in lowered
    assert "endors" not in lowered
    completion = COMPLETION.read_text(encoding="utf-8").casefold()
    assert "preparing shopping-source coverage for the philippines" in completion


def test_account_country_cannot_enable_ph_coverage() -> None:
    coverage = assess_shopping_coverage(account_country="PH")
    assert coverage.connector_invocation_eligible is False
    assert coverage.certified is False


def test_display_currency_cannot_enable_ph_coverage() -> None:
    coverage = assess_shopping_coverage(display_currency="PHP")
    assert coverage.connector_invocation_eligible is False


def test_affiliate_state_cannot_enable_ph_coverage() -> None:
    coverage = assess_shopping_coverage(
        affiliate_available=True,
        account_country="PH",
        display_currency="USD",
    )
    assert coverage.connector_invocation_eligible is False
    assert "locale" not in coverage.to_dict()


def test_effective_cost_unknown_fields_stay_unknown() -> None:
    table = {row.component: row for row in shopify_reduced_path_effective_cost_table()}
    listing = table["current_listing_price"]
    assert listing.technical == "exposed"
    assert listing.policy == "allowed"
    assert listing.shopper_applicability == "usable only as observed current listing price"
    assert listing.included_in_effective_cost is True
    for name in (
        "seller_discount",
        "platform_discount",
        "voucher_promotion",
        "voucher_eligibility",
        "destination_shipping",
        "free_shipping",
        "checkout_other_costs",
        "tax_import",
    ):
        row = table[name]
        assert row.technical == "unknown"
        assert row.policy == "unknown"
        assert row.shopper_applicability == "unknown"
        assert row.included_in_effective_cost is False
        assert row.technical != "0"


def test_shipping_taxes_and_promotion_are_not_certified() -> None:
    records = production_research_provider_certification_catalog().list_records()
    certified = {record.capability for record in records}
    assert ResearchCapability.SHIPPING not in certified
    assert ResearchCapability.TAXES_IMPORT not in certified
    assert ResearchCapability.PROMOTION_EVIDENCE not in certified
    assert set(UNCERTIFIED_CAPABILITIES).isdisjoint(certified)


def test_production_counts_stay_fail_closed() -> None:
    assert len(production_research_provider_registry().list_providers()) == 1
    assert len(production_research_provider_certification_evidence_catalog().list_records()) == 4
    assert len(production_research_provider_certification_catalog().list_records()) == 4
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert anonymous_global_catalog_access_stage().production_profile_deployed is False


def test_later_sprints_remain_unstarted() -> None:
    assert SPRINT_38_STATUS == "UNSTARTED"
    assert SPRINT_41_STATUS == "UNSTARTED"
    assert _status_line(SPRINT38).split("**Status:**", 1)[1].strip() == "Planned"
    sprint41 = _status_line(SPRINT41)
    assert "Planned" in sprint41
    assert "not started" in sprint41.casefold()
    assert CLOSURE_STATUS == "COMPLETE / CLOSED"
    assert SPRINT_32_STATUS == "COMPLETE / CLOSED"
    status = _status_line(SPRINT32)
    assert "COMPLETE / CLOSED" in status
    assert "2026-09-25" in status
    assert "not production-deployment ready" in status.casefold()


def test_closure_module_makes_no_shopify_or_deploy_call() -> None:
    source = CLOSURE_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint({"httpx", "requests", "urllib", "socket", "boto3"})
    assert "catalog.shopify.com" not in source
    harness = HARNESS.read_text(encoding="utf-8")
    assert "shopify_global_catalog_sprint32_closure" not in harness
    assert "attempt #4" not in harness


def test_completion_matrix_has_no_unresolved_sprint32_owned_criterion() -> None:
    text = COMPLETION.read_text(encoding="utf-8")
    assert "mostly done" not in text.casefold()
    matrix = text.split("## Acceptance matrix", 1)[1].split("## Explicit non-claims", 1)[0]
    results = []
    for line in matrix.splitlines():
        if not line.startswith("|") or line.startswith("| Criterion") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) >= 2
        results.append(cells[1])
    assert results
    assert set(results) <= _ALLOWED_RESULTS
    ownership = text.split("## Ownership reconciliation", 1)[1]
    ownership = ownership.split("## Staging certification", 1)[0]
    assert "| B." not in ownership
    assert "still needs work" not in ownership.casefold()


def test_monitoring_does_not_call_disabled_provider_healthy() -> None:
    health = HEALTH.read_text(encoding="utf-8")
    assert "ph-shopify-global-catalog" in health
    assert "DISABLED" in health
    assert "must not call this provider healthy, live, available, or" in health
    for label in FORBIDDEN_MONITORING_LABELS:
        assert label in health.casefold()
    section = health.split("Shopify Global Catalog PH provider status", 1)[1]
    assert "status: healthy" not in section.casefold()
    assert "Sprint 38" in section
