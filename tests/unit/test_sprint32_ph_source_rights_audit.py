"""Lock Sprint 32 PH source-rights audit: Global Catalog survivor, sprint open."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md"
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
INVENTORY = ROOT / "docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md"
GAP = ROOT / "docs/roadmap/GAP_INVENTORY.md"
POLICY_STATES = {"allowed", "restricted", "prohibited", "unknown"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FIFTH_STATE_RE = re.compile(r"\b(permitted|denied|approved|disallowed)\b", re.IGNORECASE)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_audit_document_exists_and_records_outcome_a() -> None:
    text = _read(AUDIT)
    assert "2026-09-18" in text
    assert "629ab4eb92c2a1bb743632b5c1d0d195e5aa6111" in text
    assert "**Outcome:** **A**" in text
    assert "**OUTCOME A.**" in text
    assert "S-1 — Shopify Global Catalog UCP" in text
    assert "SPRINT 32 REMAINS OPEN" in text
    assert "Sprint 32 remains **OPEN**" in text
    assert "PH LIVE COVERAGE VALIDATION STILL REQUIRED" in text


def test_audit_does_not_certify_or_scrape() -> None:
    text = _read(AUDIT)
    assert "This document does **not** certify" in text
    assert "Do not send any email from this workspace." in text
    assert "This audit performed no Shopify live call." in text
    assert "Unauthorized public-page reuse remains not accepted." in text
    assert "Tavily Extract does not solve PMC rights" in text
    assert "Engineering interpretation is not counsel approval." in text
    assert "legal under Philippine law" in text


def test_global_catalog_is_survivor_separate_from_shop_and_pmc() -> None:
    text = _read(AUDIT)
    assert "PiqSavi shopper query" in text
    assert "Shopify Global Catalog" in text
    assert "Do not place Tavily between PiqSavi and Shopify Global Catalog" in text
    assert "Power Mac Center written permission is **not** a prerequisite" in text
    assert "Shop.app personal-agent skill" in text
    assert "personal use only" in text
    assert "do **not** disqualify the commercial Global Catalog" in text
    assert "Actual PH merchant coverage is **unverified**" in text
    assert "Canonical evaluated offer" in text
    assert "**No.** Rights survivor ≠ production certification." in text


def test_capability_matrix_uses_only_sprint31_states() -> None:
    text = _read(AUDIT)
    matrix = text.split("## 5. Capability-policy matrix", 1)[1].split("## 6.", 1)[0]
    found = set(re.findall(r"\b(allowed|restricted|prohibited|unknown)\b", matrix.lower()))
    assert found <= POLICY_STATES
    assert "allowed" in found
    assert "prohibited" in found
    assert "restricted" in found
    assert FIFTH_STATE_RE.search(matrix) is None
    assert "persistent product indexing" in matrix.lower()
    assert "AI model training" in matrix or "AI model training/improvement" in matrix


def test_sprint32_status_remains_in_progress_and_links_audit() -> None:
    text = _read(SPRINT32)
    status_line = next(line for line in text.splitlines() if line.startswith("**Status:**"))
    assert "In progress" in status_line
    assert "not complete" in status_line.lower()
    assert "Sprint 32 is **not complete**" in text
    assert "SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md" in text
    assert "rights survivor" in text.lower()
    assert "Sprint 32 remains open." in text
    assert "not** production-certified" in text or "**not** production-certified" in text


def test_inventory_and_gap_record_outcome_a_without_closing_sprint() -> None:
    inventory = _read(INVENTORY)
    gap = _read(GAP)
    assert "Reassessment outcome: **A**" in inventory
    assert "Sprint 32 is **not complete**." in inventory
    assert "Outcome | **A** — Shopify Global Catalog UCP rights survivor" in gap
    assert "does **not** close Sprint 32" in gap
    assert "SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md" in inventory
    assert "SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md" in gap
    assert "actual PH inventory **unverified**" in gap


def test_audit_relative_links_resolve() -> None:
    missing: list[str] = []
    text = _read(AUDIT)
    for match in LINK_RE.finditer(text):
        target = match.group(1).split("#", 1)[0].split(" ", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (AUDIT.parent / target).resolve()
        if not resolved.exists():
            missing.append(target)
    assert missing == []
