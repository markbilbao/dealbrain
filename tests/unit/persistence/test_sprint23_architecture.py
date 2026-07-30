"""Architecture-regression tests for Sprint 23 neutrality invariants."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_persistence_adapters_contain_no_ranking_logic() -> None:
    forbidden = (
        "DealScore",
        "WeightedDealScore",
        "RuleBasedRecommendation",
        "organic_rank",
        "commission_weight",
    )
    repo_dir = ROOT / "app/infrastructure/database/repositories"
    for path in repo_dir.glob("*_repository.py"):
        if path.name in {
            "canonical_product_repository.py",
            "price_history_repository.py",
            "product_repository.py",
            "collection_job_repository.py",
        }:
            continue
        text = path.read_text()
        for token in forbidden:
            assert token not in text, f"{path.name} must not contain {token}"


def test_sprint5_and_sprint6_engines_unchanged_by_persistence_imports() -> None:
    for rel in (
        "app/intelligence/dealscore",
        "app/intelligence/recommendation",
    ):
        for path in (ROOT / rel).rglob("*.py"):
            text = path.read_text()
            assert "infrastructure.persistence" not in text
            assert "operational_entities" not in text


def test_affiliate_attachment_remains_post_selection() -> None:
    """Affiliate link service must not feed DealScore engine modules."""
    dealscore_text = "\n".join(
        p.read_text() for p in (ROOT / "app/intelligence/dealscore").rglob("*.py")
    )
    assert "AffiliateLink" not in dealscore_text
    assert "commission" not in dealscore_text.lower()
