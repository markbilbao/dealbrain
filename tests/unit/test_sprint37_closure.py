"""Sprint 37 PH-only closure. Does not start Sprint 38 or enable FX."""

from __future__ import annotations

from pathlib import Path

from app.consumer.pricing import MoneyComponent, shipping_display
from app.domain.entities.connector_reliability import ConnectorOperationalStatus
from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.market.coverage import PH_PREPARING_COVERAGE_DISCLOSURE, assess_shopping_coverage
from app.market.destination_reevaluation import live_destination_reevaluation_available
from app.market.fx import (
    PRODUCTION_FX_CONVERSION_ENABLED,
    production_fx_quotes,
)
from app.market.support import production_certified_shopping_markets
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import (
    SPRINT_38_STATUS,
    SPRINT_41_STATUS,
)

ROOT = Path(__file__).resolve().parents[2]
COMPLETION = ROOT / "docs/roadmap/evidence/SPRINT_37_COMPLETION.md"
SPRINT37 = ROOT / "docs/roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
SPRINT41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
REGISTER = ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md"
_ALLOWED = {
    "PASS",
    "DEFERRED TO SPRINT 38",
    "DEFERRED",
    "DEFERRED TO SPRINT 41",
    "DEFERRED TO SPRINT 44",
    "DEFERRED TO SPRINT 44 / 45",
    "NOT APPLICABLE TO PH-ONLY BETA",
    "NOT APPLICABLE TO THIS CLOSE",
    "NOT APPLICABLE",
}


def _status(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(line for line in lines if line.startswith("**Status:**"))


def test_sprint37_status_is_closed_for_ph_only_scope() -> None:
    status = _status(SPRINT37)
    completion = COMPLETION.read_text(encoding="utf-8")
    assert "COMPLETE / CLOSED" in status
    assert "2026-09-26" in status
    assert "PH-only" in status
    assert "SPRINT 37 COMPLETE / CLOSED" in completion
    assert "NOT LIVE DESTINATION RE-EVALUATION" in completion
    assert "NOT PRODUCTION FX" in completion
    assert "NOT PUBLIC PH SHOPPING COVERAGE" in completion


def test_live_destination_reevaluation_stays_deferred() -> None:
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert live_destination_reevaluation_available() is False
    text = COMPLETION.read_text(encoding="utf-8")
    assert "DEFERRED TO SPRINT 38" in text
    assert _status(SPRINT38).split("**Status:**", 1)[1].strip() == "Planned"
    assert SPRINT_38_STATUS == "UNSTARTED"


def test_production_fx_and_ext23_stay_unavailable() -> None:
    assert PRODUCTION_FX_CONVERSION_ENABLED is False
    assert production_fx_quotes() == ()
    register = REGISTER.read_text(encoding="utf-8")
    assert "| EXT-23 |" in register
    assert "`not_started`" in register
    assert "no cross-currency compare" in register.casefold()
    sprint41 = _status(SPRINT41)
    assert "Planned" in sprint41
    assert "not started" in sprint41.casefold()
    assert SPRINT_41_STATUS == "UNSTARTED"


def test_shipping_unknown_is_not_free_and_markets_stay_closed() -> None:
    unknown = MoneyComponent(kind="shipping", label="Shipping", amount=None, status="unknown")
    assert shipping_display(unknown) == "Not verified"
    assert shipping_display(unknown) != "FREE"
    assert production_certified_shopping_markets().to_tuple() == ()
    coverage = assess_shopping_coverage(account_country="PH", display_currency="PHP")
    assert coverage.connector_invocation_eligible is False
    assert coverage.disclosure == PH_PREPARING_COVERAGE_DISCLOSURE


def test_sprint32_fail_closed_state_is_unchanged() -> None:
    providers = production_research_provider_registry().list_providers()
    assert len(providers) == 1
    assert providers[0].descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    assert production_research_provider_routing_policy_catalog().list_records() == ()


def test_completion_matrix_has_no_open_sprint37_owned_item() -> None:
    text = COMPLETION.read_text(encoding="utf-8")
    matrix = text.split("## Acceptance matrix", 1)[1].split("## Explicit non-claims", 1)[0]
    results: list[str] = []
    for line in matrix.splitlines():
        if not line.startswith("|") or line.startswith("| Criterion") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        results.append(cells[1])
    assert results
    assert set(results) <= _ALLOWED
    ownership = text.split("## Ownership reconciliation", 1)[1].split("## FX and EXT-23", 1)[0]
    assert "| B." not in ownership
    assert "still required" not in ownership.casefold()
