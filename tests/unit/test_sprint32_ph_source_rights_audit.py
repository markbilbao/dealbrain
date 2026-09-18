"""Lock the 2026-09-18 Sprint 32 PH source-rights audit: no survivor, sprint remains open."""

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


def test_audit_document_exists_and_records_outcome_c() -> None:
    text = _read(AUDIT)
    assert "2026-09-18" in text
    assert "629ab4eb92c2a1bb743632b5c1d0d195e5aa6111" in text
    assert "**Outcome:** **C**" in text
    assert "**None.**" in text
    assert "SPRINT 32 REMAINS OPEN" in text
    assert "Sprint 32 remains **OPEN**" in text
    assert "no survivor" in text.lower() or "**None.**" in text


def test_audit_does_not_certify_or_scrape() -> None:
    text = _read(AUDIT)
    assert "This document does **not** certify" in text
    assert "Do not send any email from this workspace." in text
    assert "merchant API call, or scrape" in text
    assert "Unauthorized public-page reuse is not accepted." in text
    assert "Tavily Extract does not solve PMC rights." in text
    assert "Engineering interpretation is not counsel approval." in text
    assert "legal under Philippine law" in text


def test_strongest_path_is_owner_action_not_certified() -> None:
    text = _read(AUDIT)
    assert "OA-1 — Shopify commercial UCP catalog + Power Mac Center" in text
    assert "Canonical evaluated offer" in text
    assert "**No.**" in text
    assert "Shop.app personal-agent skill" in text
    assert "personal, individual use only" in text
    assert "EXT-01 already records" in text


def test_capability_matrix_uses_only_sprint31_states() -> None:
    text = _read(AUDIT)
    matrix = text.split("## 5. Capability-policy matrix", 1)[1].split("## 6.", 1)[0]
    found = set(re.findall(r"\b(allowed|restricted|prohibited|unknown)\b", matrix.lower()))
    assert found <= POLICY_STATES
    assert "unknown" in found
    assert FIFTH_STATE_RE.search(matrix) is None


def test_sprint32_status_remains_in_progress_and_links_audit() -> None:
    text = _read(SPRINT32)
    status_line = next(line for line in text.splitlines() if line.startswith("**Status:**"))
    assert "In progress" in status_line
    assert "not complete" in status_line.lower()
    assert "Sprint 32 is **not complete**" in text
    assert "SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md" in text
    assert "no survivor" in text.lower()
    assert "Sprint 32 remains open." in text


def test_inventory_and_gap_record_outcome_c_without_closing_sprint() -> None:
    inventory = _read(INVENTORY)
    gap = _read(GAP)
    assert "Audit outcome: **C** — no survivor." in inventory
    assert "Sprint 32 is **not complete**." in inventory
    assert "no survivor licensed PH product-data path" in gap
    assert "does **not** close Sprint 32" in gap
    assert "SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md" in inventory
    assert "SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md" in gap


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
