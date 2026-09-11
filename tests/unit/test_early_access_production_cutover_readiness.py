"""Contracts for the 2026-09-11 Early Access production-cutover readiness audit."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT / "docs/roadmap/evidence/EARLY_ACCESS_PRODUCTION_CUTOVER_READINESS_2026-09-11.md"
).read_text(encoding="utf-8")
RUNBOOK = (ROOT / "docs/runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_RUNBOOK.md").read_text(
    encoding="utf-8"
)
REGISTER = (ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md").read_text(encoding="utf-8")

BLOCKED = (
    "EARLY ACCESS PRODUCTION CUTOVER BLOCKED — SPECIFIC INFRASTRUCTURE/OPERATIONS ITEMS REMAIN"
)
READY = "EARLY ACCESS PRODUCTION CUTOVER READY — OWNER AUTHORIZATION REQUIRED"


def test_cutover_audit_is_blocked_not_ready() -> None:
    assert BLOCKED in EVIDENCE
    assert READY not in EVIDENCE
    assert EVIDENCE.index("Resulting state") < EVIDENCE.index(BLOCKED)
    assert "No production deployment occurred" in EVIDENCE
    assert "No DNS change occurred" in EVIDENCE
    assert "No shopping / merchant / affiliate activation occurred" in EVIDENCE


def test_locked_staging_identities_are_recorded() -> None:
    assert "c4135859663a482b078da6959af746fd2d5dc098" in EVIDENCE
    assert "34573790133" in EVIDENCE
    assert "sha256:8140f6588bff07877885b6774767929c6561cfb6220c63ee4c2322931ebfbeaa" in EVIDENCE
    assert "rel-20260911T071047Z-c4135859663a" in EVIDENCE
    assert "privacy-2026-09-11" in EVIDENCE
    assert "terms-2026-09-11" in EVIDENCE


def test_production_workflow_and_environment_remain_absent_claims() -> None:
    # Historical audit recorded absence at cutover-audit time. Phase 1 adds the
    # workflow in-repo; the GitHub Environment is still owner-created.
    assert "deploy-production.yml" in EVIDENCE
    assert "GitHub Environment `production`" in EVIDENCE
    assert "Absent" in EVIDENCE or "absent" in EVIDENCE
    assert (ROOT / ".github/workflows/deploy-production.yml").is_file()


def test_runbook_does_not_authorize_cutover() -> None:
    assert "HOLD until the owner explicitly authorizes" in RUNBOOK
    assert BLOCKED in RUNBOOK
    assert "IRREVERSIBLE OR PUBLIC-FACING" in RUNBOOK
    assert "OWNER ACTION REQUIRED" in RUNBOOK
    assert "SAFE / READ-ONLY" in RUNBOOK
    assert "Do not deploy production from this document alone" in RUNBOOK
    assert "Do not attach public DNS to staging" in RUNBOOK


def test_register_ext_rows_not_advanced_by_cutover_audit() -> None:
    def status(row_id: str) -> str:
        for line in REGISTER.splitlines():
            if line.startswith(f"| {row_id} |"):
                return [cell.strip() for cell in line.strip("|").split("|")][7]
        raise AssertionError(f"missing {row_id}")

    assert status("EXT-11") == "`not_started`"
    assert status("EXT-12") == "`not_started`"
    assert "In-repo TF complete; not applied" in status("EXT-13")
    assert status("EXT-14") == "`not_started`"
    assert status("EXT-20") == "`applied`"
    assert status("EXT-21") == "`applied`"
    assert "EARLY_ACCESS_PRODUCTION_CUTOVER_READINESS_2026-09-11.md" in REGISTER
    assert "EARLY_ACCESS_PRODUCTION_FOUNDATION_PHASE1_2026-09-11.md" in REGISTER
