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
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
ADR = ROOT / "docs/architecture/ADR_SPRINT_37_MARKETCONTEXT.md"
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
    "NOT A SPRINT 37 CLOSURE REQUIREMENT",
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
    sprint38 = _status(SPRINT38).split("**Status:**", 1)[1].strip()
    assert sprint38.startswith("IN PROGRESS")
    assert not sprint38.startswith("COMPLETE")
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


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_normative_sprint37_text_matches_ph_only_closure() -> None:
    text = SPRINT37.read_text(encoding="utf-8")
    objective = _section(text, "## Objective", "## Included requirements")
    assert "PH-only public beta" in objective
    assert "were not QA'd as supported markets" in objective
    staging = _section(text, "## Required staging evidence", "## Required production evidence")
    assert "PH selector and PH default behavior" in staging
    assert "Unsupported-market fail-closed behavior" in staging
    assert "FX-unavailable / fail-closed behavior" in staging
    assert "no live FX provider" in staging
    assert "QA checklist for 5 markets" not in staging
    assert "Selector + FX + unsupported-market paths proven" not in staging
    production = _section(text, "## Required production evidence", "## Acceptance criteria")
    assert "not a Sprint 37 closure requirement" in production
    assert "only if production FX conversion is later enabled" in production
    assert "Sprint 41" in production
    assert "EXT-23 remains `not_started`" in production
    acceptance = _section(text, "## Acceptance criteria", "## Predecessor sprints")
    assert "required_unavailable" in acceptance
    assert "DESTINATION_REEVALUATION_IMPLEMENTED` remains False" in acceptance
    assert "Live evidence-backed re-evaluation is Sprint 38" in acceptance
    assert "were not QA'd as supported" in acceptance
    assert "FR-CA is not applicable because Canada is omitted" in acceptance
    assert "triggers server-side re-evaluation\n" not in acceptance
    requirements = _section(text, "### MarketContext / FX / localization", "### 2026-09-06")
    assert "production FX provider is optional and deferred" in requirements
    assert "EXT-23 remains `not_started`" in requirements
    assert "conversion_unavailable" in requirements
    assert "not applicable because Canada is omitted" in requirements
    gate = _section(text, "## Go / no-go gate", "## Rollback or contingency")
    assert "fail-closed FX + unsupported-market + shipping honesty pass" in gate


def test_related_normative_docs_match_ph_only_closure() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    ec26 = next(line for line in roadmap.splitlines() if line.startswith("| EC-26 |"))
    assert "required_unavailable" in ec26
    assert "live execution is Sprint 38" in ec26
    assert "Not proof of a live executor" in ec26
    assert "DESTINATION_REEVALUATION_IMPLEMENTED` remains False" in ec26
    assert "Staging proof of server-side re-evaluation" not in ec26
    current = _section(
        roadmap,
        "**Current Sprint 37 closure (2026-09-26).**",
        "**One-dominant-price presentation.**",
    )
    assert "required_unavailable" in current
    assert "Live evidence-backed re-evaluation remains Sprint 38" in current
    completion = COMPLETION.read_text(encoding="utf-8")
    assert "NOT A SPRINT 37 CLOSURE REQUIREMENT" in completion
    assert "Required only if production conversion is later enabled" in completion
    assert "were not QA'd as supported" in completion or "not QA'd as supported" in completion
    register = REGISTER.read_text(encoding="utf-8")
    assert "| EXT-23 | FX provider |" in register
    assert "`not_started`" in register.split("| EXT-23 | FX provider |", 1)[1].split("\n", 1)[0]
    assert "Sprint 37 closure on 2026-09-26" in register
    assert "does not provision an FX provider" in register
    gaps = _section(GAPS.read_text(encoding="utf-8"), "## E. Market context", "## F. Connector")
    assert "supersedes the open-work reading" in gaps
    assert "were not QA'd as supported" in gaps
    assert "FR-CA is not applicable because Canada is omitted" in gaps
    assert "Live evidence-backed destination re-evaluation remains Sprint 38" in gaps
    adr = ADR.read_text(encoding="utf-8")
    assert "EXT-23 remains `not_started`" in adr
    assert "Production FX conversion remains disabled" in adr
    assert "FR-CA is not applicable because Canada is omitted" in adr
    assert "Live evidence-backed re-evaluation remains Sprint 38" in adr
    assert "remains Sprint 41" in adr


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
