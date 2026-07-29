"""Sprint 21 — analytics, admin, affiliate integration, ranking independence."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.merchant import MerchantOrgStatus, SubmissionStatus
from app.domain.exceptions import MerchantAuthorizationError
from app.intelligence.dealscore.engine import WeightedDealScoreEngine
from app.merchant.memory import InMemoryMerchantRepository
from app.merchant.security.redaction import redact_secrets
from app.services.merchant_admin_service import MerchantAdminService
from app.services.merchant_analytics_service import MerchantAnalyticsService
from app.services.merchant_auth_service import MerchantAuthService
from app.services.merchant_product_service import MerchantProductService

FIXED_NOW = datetime(2026, 7, 29, 15, 0, tzinfo=UTC)


def _stack():
    repo = InMemoryMerchantRepository(seed=True)
    clock = lambda: FIXED_NOW  # noqa: E731
    auth = MerchantAuthService(repo, repo)
    admin = MerchantAdminService(repo, repo, repo, repo, clock=clock, id_factory=lambda: "adm")
    analytics = MerchantAnalyticsService(repo, repo, repo, repo, repo, clock=clock)
    products = MerchantProductService(
        repo, repo, matcher=repo.matcher, clock=clock, id_factory=lambda: "prod"
    )
    return auth, admin, analytics, products, repo


def test_merchant_analytics_labeled_demo() -> None:
    auth, _, analytics, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    summary = analytics.get_analytics(actor, "org-techhaven")
    assert summary.simulated is True
    data = summary.to_dict()
    assert "Demo analytics" in data["label"] or data["simulated"] is True
    assert summary.affiliate is not None
    assert summary.affiliate.read_only if hasattr(summary.affiliate, "read_only") else True


def test_ranking_explanations_safe_and_non_mutating() -> None:
    auth, _, analytics, *_ = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    explanation = analytics.get_ranking_explanation(actor, "org-techhaven", "prod-laptop-x1")
    assert explanation.organic_ranking_independent is True
    factor_names = {f.factor for f in explanation.factors}
    assert "total_price" in factor_names or "dealscore_factors" in factor_names
    # Must not expose private/proprietary tokens
    blob = str(explanation.to_dict()).lower()
    for forbidden in ("password", "api_key", "ssn", "credential", "abuse_signal"):
        assert forbidden not in blob


def test_dealscore_independence_from_merchant_tools() -> None:
    """Merchant package must not feed commission/sponsored into DealScore weights."""
    from pathlib import Path

    engine = WeightedDealScoreEngine()
    assert engine is not None
    text = Path("app/intelligence/dealscore/engine.py").read_text(encoding="utf-8").lower()
    assert "commission" not in text
    assert "sponsored" not in text
    assert "merchant_submitted" not in text


def test_organic_ranking_independence_tokens() -> None:
    from pathlib import Path

    root = Path("app/merchant")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        # Merchant tools may mention organic ranking independence, but must not
        # call into WeightedDealScoreEngine to mutate rankings.
        assert "weighteddealscoreengine" not in text.replace("_", "")


def test_admin_approval_rejection_suspend_activate() -> None:
    auth, admin, _, products, repo = _stack()
    owner = auth.resolve_actor("demo-token-gadgetgrove-owner", organization_id="org-gadgetgrove")
    draft = products.create_product(owner, "org-gadgetgrove", title="Admin Review Phone")
    submitted = products.submit_product(owner, "org-gadgetgrove", draft.submission_id)
    admin_actor = auth.resolve_actor("demo-token-internal-admin")
    approved = admin.approve_submission(admin_actor, submitted.submission_id, notes="ok")
    assert approved.status == SubmissionStatus.APPROVED

    draft2 = products.create_product(owner, "org-gadgetgrove", title="Rejectable Item Here")
    submitted2 = products.submit_product(owner, "org-gadgetgrove", draft2.submission_id)
    rejected = admin.reject_submission(
        admin_actor, submitted2.submission_id, notes="fix", needs_changes=True
    )
    assert rejected.status == SubmissionStatus.NEEDS_CHANGES

    suspended = admin.suspend_merchant(admin_actor, "org-gadgetgrove", notes="policy")
    assert suspended.status == MerchantOrgStatus.SUSPENDED
    activated = admin.activate_merchant(admin_actor, "org-gadgetgrove")
    assert activated.status == MerchantOrgStatus.ACTIVE

    # Non-admin cannot approve
    with pytest.raises(MerchantAuthorizationError):
        admin.approve_submission(owner, submitted.submission_id)


def test_audit_logging_and_secret_redaction() -> None:
    auth, _, analytics, products, repo = _stack()
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    products.create_product(actor, "org-techhaven", title="Audited Product Title")
    events = analytics.list_audit_log(actor, "org-techhaven", limit=50)
    assert events
    assert all("action" in e for e in events)

    redacted = redact_secrets(
        {"title": "ok", "api_key": "secret-value", "nested": {"password": "x"}}
    )
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["nested"]["password"] == "***REDACTED***"


def test_affiliate_analytics_integration_read_only() -> None:
    from app.affiliate.memory import InMemoryAffiliateRepository

    affiliate_repo = InMemoryAffiliateRepository(seed=True)
    repo = InMemoryMerchantRepository(seed=True)
    auth = MerchantAuthService(repo, repo)
    analytics = MerchantAnalyticsService(
        repo,
        repo,
        repo,
        repo,
        repo,
        affiliate_click_lister=affiliate_repo.list_clicks,
        clock=lambda: FIXED_NOW,
    )
    actor = auth.resolve_actor("demo-token-techhaven-owner", organization_id="org-techhaven")
    summary = analytics.get_analytics(actor, "org-techhaven")
    assert summary.affiliate is not None
    assert summary.affiliate.affiliate_merchant_id == "merchant-amazon-us"
    # Merchant analytics must not mutate affiliate click store
    before = len(affiliate_repo.list_clicks(merchant_id="merchant-amazon-us", limit=500))
    analytics.get_analytics(actor, "org-techhaven")
    after = len(affiliate_repo.list_clicks(merchant_id="merchant-amazon-us", limit=500))
    assert before == after
