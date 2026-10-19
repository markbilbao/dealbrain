"""Proposed Alpine exceptions stay exact and stay out of the loaded baseline."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.check_container_vuln_baseline import (
    GRYPE_VERSION,
    _validate_exception,
    load_baseline,
)

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "docs/roadmap/evidence/sprint40-alpine-proposed-grype-exceptions.json"
BASELINE = ROOT / "tests/security/baselines/grype-image.baseline.json"


def test_proposed_alpine_exceptions_stay_out_of_the_baseline() -> None:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert proposal["status"] == "proposed_not_loaded"
    assert proposal["scanner_version"] == GRYPE_VERSION
    items = proposal["exceptions"]
    assert [item["id"] for item in items] == [f"GRYPE-{index:03d}" for index in range(1, 11)]
    assert {item["rationale"] for item in items} == {"not_applicable", "false_positive"}
    false_positives = [item for item in items if item["rationale"] == "false_positive"]
    assert [item["vulnerability_id"] for item in false_positives] == ["CVE-2026-3479"]
    for index, item in enumerate(items):
        _validate_exception(index, item)
    loaded = load_baseline(BASELINE)
    assert loaded["exceptions"] == []
    assert PROPOSAL.resolve() != BASELINE.resolve()
