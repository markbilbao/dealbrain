"""The loaded baseline is exactly the approved Alpine exception set."""

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
APPROVED = (
    (
        "GRYPE-001",
        "CVE-2025-60876",
        "busybox",
        "1.37.0-r31",
        "not_applicable",
        "af374eb82e451484d6d8fc70fda50e8030d9b1fa92477ded368cbd8ec4dda630",
    ),
    (
        "GRYPE-002",
        "CVE-2025-60876",
        "busybox-binsh",
        "1.37.0-r31",
        "not_applicable",
        "580bd18a79c8ed298c06d7a63a691c0022d3994f6fcaac925197c389810d27a7",
    ),
    (
        "GRYPE-003",
        "CVE-2025-60876",
        "ssl_client",
        "1.37.0-r31",
        "not_applicable",
        "d0c255f2f714db9ba04a8948b9315b791865fbb88cea4be2a8d8d8fa9e4162a0",
    ),
    (
        "GRYPE-004",
        "CVE-2025-12781",
        "python",
        "3.12.15",
        "not_applicable",
        "19f5b7ee2ba48646e37d29170249a26647c40f584bc65d86bb6a415baade2f3d",
    ),
    (
        "GRYPE-005",
        "CVE-2025-15366",
        "python",
        "3.12.15",
        "not_applicable",
        "a91f28a7d75a4f98526e2c1e9078432ff90ef12f77a1fa7e4c3f42109e048502",
    ),
    (
        "GRYPE-006",
        "CVE-2025-15367",
        "python",
        "3.12.15",
        "not_applicable",
        "eea63833c14932c7683b2dd4509b1c2f02b8d61555ea72bf1306809cb418ed5e",
    ),
    (
        "GRYPE-007",
        "CVE-2026-3446",
        "python",
        "3.12.15",
        "not_applicable",
        "3ae063f814dd51fa1c04f9c6f6c32a9d225d68b0ddf88a6ffd96640972341159",
    ),
    (
        "GRYPE-008",
        "CVE-2026-12345",
        "python",
        "3.12.15",
        "not_applicable",
        "9bb51031077d89677ab27f02340fbcdf56f888595383312f9d916bf8a750fb50",
    ),
    (
        "GRYPE-009",
        "CVE-2026-6019",
        "python",
        "3.12.15",
        "not_applicable",
        "d8308e625054761fc058649e7acd96f4b1c0f8a1e2bd8911bd704ab2660a3a78",
    ),
    (
        "GRYPE-010",
        "CVE-2026-3479",
        "python",
        "3.12.15",
        "false_positive",
        "93fb72fea50f23280c2adc7733d607e1a1229b5ec01fe0247a95a43abd27334b",
    ),
)


def _row(item: dict) -> tuple[str, str, str, str, str, str]:
    return (
        item["id"],
        item["vulnerability_id"],
        item["package_name"],
        item["package_version"],
        item["rationale"],
        item["fingerprint"],
    )


def test_loaded_baseline_is_exactly_the_approved_alpine_set() -> None:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    assert proposal["scanner_version"] == GRYPE_VERSION
    approved = proposal["exceptions"]
    assert [_row(item) for item in approved] == list(APPROVED)
    assert {item["rationale"] for item in approved} == {"not_applicable", "false_positive"}
    assert [
        item["vulnerability_id"] for item in approved if item["rationale"] == "false_positive"
    ] == ["CVE-2026-3479"]
    for index, item in enumerate(approved):
        _validate_exception(index, item)
        blob = json.dumps(item)
        assert "*" not in blob
    loaded = load_baseline(BASELINE)
    assert loaded["exceptions"] == approved
    assert len(loaded["exceptions"]) == len(APPROVED)
    assert PROPOSAL.resolve() != BASELINE.resolve()
