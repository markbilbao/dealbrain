"""Lock Sprint 26 PH validation-beta launch-scope reconciliation."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/roadmap"
REGISTER = (DOCS / "EXTERNAL_DEPENDENCY_REGISTER.md").read_text(encoding="utf-8")
ROADMAP = (DOCS / "GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md").read_text(encoding="utf-8")
SPRINT_26 = (DOCS / "sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md").read_text(encoding="utf-8")
COMPLETION = (DOCS / "evidence/SPRINT_26_COMPLETION_DRAFT.md").read_text(encoding="utf-8")
SPRINT_45 = (DOCS / "sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md").read_text(
    encoding="utf-8"
)

RECONCILED_DOCS = [
    DOCS / "EXTERNAL_DEPENDENCY_REGISTER.md",
    DOCS / "GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md",
    DOCS / "GAP_INVENTORY.md",
    DOCS / "README.md",
    DOCS / "sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md",
    DOCS / "sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md",
    DOCS / "sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md",
    DOCS / "sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md",
    DOCS / "sprints/README.md",
    DOCS / "evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md",
    DOCS / "evidence/SPRINT_26_COMPLETION_DRAFT.md",
    DOCS / "evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md",
    DOCS / "evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md",
]


def _status_cell(row_id: str) -> str:
    for line in REGISTER.splitlines():
        if line.startswith(f"| {row_id} |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            return cells[7]
    raise AssertionError(f"missing register row {row_id}")


def test_ext_status_reconciliation() -> None:
    assert _status_cell("EXT-01") == "`not_started`"
    assert _status_cell("EXT-02") == "`n_a_beta`"
    assert _status_cell("EXT-03") == "`n_a_beta`"
    assert _status_cell("EXT-04") == "`n_a_beta`"
    assert _status_cell("EXT-05") == "`n_a_beta`"
    assert _status_cell("EXT-07") == "`n_a_beta`"
    assert _status_cell("EXT-19") == "`applied`"
    assert "PH merchant/product-data access" in REGISTER
    assert "Affiliate permission ≠ product-data permission." in REGISTER
    assert "Affiliate approval does **not** satisfy EXT-01" in REGISTER


def test_sprint_26_remains_open_for_ph_product_data() -> None:
    assert "SPRINT 26 TECHNICAL COMPLETE — PH DATA-ACCESS BOOTSTRAP REMAINS" in SPRINT_26
    assert "SPRINT 26 TECHNICAL COMPLETE — PH DATA-ACCESS BOOTSTRAP REMAINS" in COMPLETION
    assert "Sprint 26 remains OPEN" in SPRINT_26
    assert "79bd03f" in SPRINT_26
    assert "NOT YET CLOSED" in COMPLETION


def test_ph_only_no_affiliate_launch_scope() -> None:
    assert "Philippines-first product-validation beta without affiliate monetization" in ROADMAP
    assert "Philippines only" in ROADMAP
    assert "Affiliate revenue is not a launch acceptance requirement" in ROADMAP
    assert "Sprint 47 remains post-beta" in ROADMAP
    assert "not unconditional legal approval" in ROADMAP
    assert (
        "Mixed affiliate/non-affiliate runtime comparison is required only if affiliate-enabled merchants are active"
        in ROADMAP
    )
    assert "Philippines only" in SPRINT_45
    assert "If zero affiliate-enabled merchants are active" in SPRINT_45


def test_reconciled_docs_relative_links_exist() -> None:
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    missing: list[str] = []
    for path in RECONCILED_DOCS:
        text = path.read_text(encoding="utf-8")
        for match in link_re.finditer(text):
            target = match.group(1).split("#", 1)[0].split(" ", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {target}")
    assert missing == []
