"""Guard: Sprint 20 Affiliate Revenue Engine must not modify prior-sprint
protected modules (DealScore, recommendation ranking, Sprint 19 packages).

Affiliate monetization is a post-rank layer only.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_sprint19_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

PROTECTED_DIGESTS = dict(PRIOR)

# Sprint 19 / ranking modules Sprint 20 must not rewrite in place.
EXTRA_DIGESTS = {
    "app/services/alert_rule_service.py": (
        "88b11c69a3a7fe8323d09288d0e2421a51b7964301f3d8822e276426bd2ffe89"
    ),
    "app/services/alert_evaluation_service.py": (
        "4b0fcb51202df99c7ff220462bf3f62f4229376a3c051a0179fc2d7db7e9632d"
    ),
    "app/services/notification_center_service.py": (
        "3cda83a510649580972f7126fef9d1c0794be2d3179c2fafd2c4529e7ba93195"
    ),
    "app/services/user_dashboard_service.py": (
        "b57727ffd0444dc380907a2099ee308aec47ec777a01fdb27146a8287a021168"
    ),
    "app/alerts/engine/evaluator.py": (
        "d7172543444ffc5dd41c16e06ebcb5198302b49b025fc5654e186f182add88d3"
    ),
    "app/intelligence/shopping_assistant/recommendation.py": (
        "0ae3e1b28011df6ca26ac7c674d08cda73772d6cdc92b820d0e01a7592b47ec5"
    ),
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)

# Ranking / DealScore modules must never reference affiliate/commission payouts.
RANKING_MODULES = (
    "app/intelligence/dealscore/engine.py",
    "app/intelligence/recommendation/engine.py",
    "app/intelligence/shopping_assistant/recommendation.py",
)

RANKING_FORBIDDEN = (
    "commission",
    "affiliate",
    "payout",
    "adsense",
    "sponsored",
    "stripe",
    "paypal",
)

# Affiliate package must not depend on real payment SDKs or scrapers.
AFFILIATE_FORBIDDEN = (
    "stripe",
    "paypal",
    "adsense",
    "scrapy",
    "beautifulsoup",
    "selenium",
    "playwright",
    "smtplib",
    "celery",
)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_ranking_modules_have_no_affiliate_commission_bias() -> None:
    for relative in RANKING_MODULES:
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        for token in RANKING_FORBIDDEN:
            assert token not in lowered, f"{relative} references forbidden token {token!r}"


def test_affiliate_package_exists_and_avoids_real_vendors() -> None:
    package_root = ROOT / "app/affiliate"
    assert package_root.is_dir()
    python_files = list(package_root.rglob("*.py"))
    assert python_files
    for path in python_files:
        lowered = path.read_text(encoding="utf-8").lower()
        for token in AFFILIATE_FORBIDDEN:
            assert token not in lowered, f"{path} references forbidden token {token!r}"


def test_affiliate_services_exist() -> None:
    expectations = {
        "app/services/affiliate_merchant_service.py": "AffiliateMerchantService",
        "app/services/affiliate_link_service.py": "AffiliateLinkService",
        "app/services/affiliate_tracking_service.py": "AffiliateTrackingService",
        "app/services/affiliate_reporting_service.py": "AffiliateReportingService",
        "app/services/affiliate_disclosure_service.py": "AffiliateDisclosureService",
    }
    for relative, class_name in expectations.items():
        path = ROOT / relative
        assert path.is_file(), f"Expected Sprint 20 service missing: {relative}"
        assert f"class {class_name}" in path.read_text(encoding="utf-8")


def test_shopping_assistant_integrates_affiliate_after_ranking_only() -> None:
    text = (ROOT / "app/services/shopping_assistant_service.py").read_text(encoding="utf-8")
    assert "affiliate_link_service" in text
    assert "_attach_affiliate_links" in text
    assert "applied_after_ranking" in text
    # Must not import WeightedDealScoreEngine or rewrite ranking key with commission.
    assert "WeightedDealScoreEngine" not in text
    assert "commission_value" not in text


def test_dealscore_engine_weights_exclude_affiliate() -> None:
    text = (ROOT / "app/intelligence/dealscore/engine.py").read_text(encoding="utf-8")
    assert "DEFAULT_WEIGHTS" in text
    assert "commission" not in text.lower()
    assert "affiliate" not in text.lower()


def test_docs_state_limitations() -> None:
    doc = (ROOT / "docs/AFFILIATE_REVENUE_ENGINE.md").read_text(encoding="utf-8")
    for phrase in (
        "No real affiliate APIs",
        "No real commissions",
        "No real conversions",
        "No billing",
        "No payouts",
        "No merchant portal",
    ):
        assert phrase in doc
