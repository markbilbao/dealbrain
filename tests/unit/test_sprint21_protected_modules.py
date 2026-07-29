"""Guard: Sprint 21 Merchant Platform must not modify prior-sprint protected
modules (DealScore, recommendation ranking, Affiliate Revenue Engine).

Merchant tools never manipulate organic DealScore or recommendation ranking.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_sprint20_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

PROTECTED_DIGESTS = dict(PRIOR)

# Sprint 20 affiliate / ranking modules Sprint 21 must not rewrite in place.
EXTRA_DIGESTS = {
    "app/services/affiliate_merchant_service.py": (
        "68893deb2a88e033a699d7810d50ebb1c4a6e61ea44a8e8d3e5f3a32dd8b83ce"
    ),
    "app/services/affiliate_link_service.py": (
        "4f71cdf81e965b6fec34b2ad3e9e9ed35f0224e5d09413a981e693903ac2865f"
    ),
    "app/services/affiliate_tracking_service.py": (
        "bd15838483d2e75f726eac62f02c34b296bc69a3ccf85bc0ba46e7b866b051ce"
    ),
    "app/services/affiliate_reporting_service.py": (
        "7a23eeb34e820082f6f8c3d071c1a5267fb5b1f9f16059144e651699d63ccb99"
    ),
    "app/services/affiliate_disclosure_service.py": (
        "7f7a1a61813265ec50532bf7fa54753d7e7ca7341d77712321ced0f731229d88"
    ),
    "app/affiliate/linking/builder.py": (
        "7d8836eee8355c82124bda8bc4b7b90e01931d2f7b3523abf447d35ee0ed8097"
    ),
    "app/affiliate/attribution/engine.py": (
        "145376797b6db7ea884a431174d78eea5fc800f59a0b743139aa938084265591"
    ),
    "app/domain/entities/affiliate.py": (
        "c0cdb024ddcbe40287926a6633c02d2113f0b5fd9fe72db77b3d055e411637fe"
    ),
    "app/intelligence/dealscore/engine.py": (
        "6551417b32f8201ab4c7565e2970d71d2f3fd3ce6ef51aaa1b0a3dd1ebdfabf1"
    ),
    "app/intelligence/recommendation/engine.py": (
        "eeca61d051297f84ffb64aa2ad726a36b9306a61293919c444b3733681ef3df0"
    ),
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)

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
    "merchant_submitted",
)

MERCHANT_FORBIDDEN = (
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


def test_ranking_modules_have_no_merchant_or_sponsored_bias() -> None:
    for relative in RANKING_MODULES:
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        for token in RANKING_FORBIDDEN:
            assert token not in lowered, f"{relative} references forbidden token {token!r}"


def test_merchant_package_exists_and_avoids_real_vendors() -> None:
    package_root = ROOT / "app/merchant"
    assert package_root.is_dir()
    python_files = list(package_root.rglob("*.py"))
    assert python_files
    for path in python_files:
        lowered = path.read_text(encoding="utf-8").lower()
        for token in MERCHANT_FORBIDDEN:
            assert token not in lowered, f"{path} references forbidden token {token!r}"


def test_merchant_services_exist() -> None:
    expectations = {
        "app/services/merchant_auth_service.py": "MerchantAuthService",
        "app/services/merchant_organization_service.py": "MerchantOrganizationService",
        "app/services/merchant_membership_service.py": "MerchantMembershipService",
        "app/services/merchant_product_service.py": "MerchantProductService",
        "app/services/merchant_offer_service.py": "MerchantOfferService",
        "app/services/merchant_promotion_service.py": "MerchantPromotionService",
        "app/services/merchant_campaign_service.py": "MerchantCampaignService",
        "app/services/merchant_analytics_service.py": "MerchantAnalyticsService",
        "app/services/merchant_admin_service.py": "MerchantAdminService",
    }
    for relative, class_name in expectations.items():
        path = ROOT / relative
        assert path.is_file(), f"Expected Sprint 21 service missing: {relative}"
        assert f"class {class_name}" in path.read_text(encoding="utf-8")


def test_merchant_never_imports_dealscore_engine() -> None:
    for path in (ROOT / "app/merchant").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "WeightedDealScoreEngine" not in text
        assert "RuleBasedRecommendationEngine" not in text
    for relative in (
        "app/services/merchant_organization_service.py",
        "app/services/merchant_product_service.py",
        "app/services/merchant_campaign_service.py",
        "app/services/merchant_analytics_service.py",
        "app/services/merchant_admin_service.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "WeightedDealScoreEngine" not in text


def test_docs_state_limitations() -> None:
    docs = (
        "docs/MERCHANT_PLATFORM.md",
        "docs/MERCHANT_ROLES.md",
        "docs/MERCHANT_PRODUCT_SUBMISSIONS.md",
        "docs/MERCHANT_OFFER_MANAGEMENT.md",
        "docs/MERCHANT_PROMOTIONS.md",
        "docs/SPONSORED_CAMPAIGNS.md",
        "docs/MERCHANT_ANALYTICS.md",
        "docs/MERCHANT_SECURITY.md",
        "docs/MERCHANT_ADMIN_REVIEW.md",
    )
    phrases = (
        "Demo merchants only",
        "In-memory persistence",
        "No production merchant verification documents",
        "No real sponsored billing",
        "No payment processing",
        "No merchant payouts",
        "No ranking manipulation",
        "No public merchant self-service launch",
        "No production database",
        "No subscription billing",
        "No external email sending",
    )
    for relative in docs:
        doc = (ROOT / relative).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in doc, f"{relative} missing limitation phrase {phrase!r}"


def test_sprint20_docs_still_state_no_merchant_portal_in_affiliate_scope() -> None:
    """Sprint 20 affiliate doc remains historically accurate for that sprint."""
    doc = (ROOT / "docs/AFFILIATE_REVENUE_ENGINE.md").read_text(encoding="utf-8")
    assert "No merchant portal" in doc
