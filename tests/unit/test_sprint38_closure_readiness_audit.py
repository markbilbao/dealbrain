"""Sprint 38 closure-readiness audit. Does not close the sprint or call Shopify."""

from __future__ import annotations

from pathlib import Path

from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.market.support import production_certified_shopping_markets
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import (
    SPRINT_38_LIVE_EXECUTION_STATUS,
    SPRINT_38_STATUS,
    SPRINT_41_STATUS,
)
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPIFY_PERSISTENT_CACHE_ALLOWED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    SPRINT_38_ENGINEERING_STATUS,
)
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_38_CLOSURE_READINESS_AUDIT_2026-09-30.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
VERDICT = (
    "SPRINT 38 ENGINEERING COMPLETE — CLOSURE VALIDATION BLOCKED ON SPRINT 41 / DOWNSTREAM GATES"
)
STATUS_VERDICT = "ENGINEERING COMPLETE — CLOSURE VALIDATION BLOCKED ON SPRINT 41 / DOWNSTREAM GATES"


def _status_line(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(line for line in lines if line.startswith("**Status:**"))


def test_audit_verdict_is_engineering_complete_and_not_sprint_closure() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    assert VERDICT in audit
    assert "Class B count: 0." in audit
    assert "This audit does not close Sprint 38." in audit
    assert "Not COMPLETE / CLOSED." in audit
    assert "does not mark Sprint 38 COMPLETE / CLOSED" in audit
    status = _status_line(SPRINT38).split("**Status:**", 1)[1].strip()
    assert status.startswith("IN PROGRESS")
    assert not status.startswith("COMPLETE")
    assert STATUS_VERDICT in status
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_LIVE_EXECUTION_STATUS == "NOT OPERATIONAL"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert SPRINT_41_STATUS == "UNSTARTED"


def test_audit_keeps_production_truth_closed() -> None:
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert SHOPIFY_PERSISTENT_CACHE_ALLOWED is False
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()


def test_audit_classifies_superseded_closure_blockers() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    assert "Multi-connector live chaos is not a Sprint 38 closure requirement" in audit
    assert "belong to Sprint 42" in audit
    assert "production profile belong to Sprint 41" in audit
    assert "execute_production_shopify_catalog" in audit
    assert "DESTINATION_REEVALUATION_IMPLEMENTED" in audit
    assert "A synthetic-only contract test is not worthwhile" in audit
