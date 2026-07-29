"""Guard: Sprint 19 (Watchlists v2, Alert Engine, Notifications, Dashboard)
must not modify prior-sprint protected modules — including Sprint 18
Marketplace Data Synchronization, which Sprint 19 only ever reads from
(``UserDashboardService`` takes an optional ``MarketplaceDataService``
collaborator; nothing in ``app/alerts``, ``app/notifications``,
``app/watchlists``, or ``app/dashboard`` imports or rewrites it).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.unit.test_marketplace_data_protected_modules import PROTECTED_DIGESTS as PRIOR

ROOT = Path(__file__).resolve().parents[2]

# Inherit every digest protected transitively since Sprint 13 (Sprint 18 ->
# Sprint 17/User Platform -> Sprint 16/Personal Agent -> ... ), so DealScore,
# recommendation engine, shopping assistant, user platform, and marketplace
# data modules are all still protected here.
PROTECTED_DIGESTS = dict(PRIOR)

# Sprint 18 Marketplace Data Synchronization modules that Sprint 19 must not
# rewrite in place (the dashboard integrates via a read-only, optional
# ``marketplace_data_service`` collaborator only — see
# ``app/services/user_dashboard_service.py``).
EXTRA_DIGESTS = {
    "app/services/marketplace_data_service.py": (
        "1e643dc8b79f880d67ac039a5428a736eadddc2468c78e1f79cdda03e0c409a5"
    ),
    "app/marketplace/sync/engine.py": (
        "685858035e7c30e7a0f4b8c79389240ca470420e934fa23d894bff76fd15dd44"
    ),
    "app/marketplace/connectors/fixture.py": (
        "efb15268b39666ee4bcae269b5eb40c3eb056e6c26b36311a1b4a1202908bb18"
    ),
    "app/marketplace/connectors/imported.py": (
        "f72f58d105a9095f2d66f8608dcd7a6987eab049d1e5506bfc58df3a4a5a25e5"
    ),
    "app/marketplace/connectors/mock_live.py": (
        "3cde5093a9fad412ecc5de5ab9545c96697348b9afc2b42c6ac953e22080d7e6"
    ),
    "app/marketplace/connectors/stubs.py": (
        "156f1c04d0e148b0f1d95454b44bdb3910af760c7b492a95a7ba9fa0d5d8a4c4"
    ),
}

PROTECTED_DIGESTS.update(EXTRA_DIGESTS)

# New Sprint 19 packages — never allowed to touch payment/affiliate/ads
# vendors or web-scraping tooling, matching every prior sprint's guard.
SPRINT19_PACKAGES = ("app/alerts", "app/notifications", "app/watchlists", "app/dashboard")

FORBIDDEN_TOKENS = (
    "stripe",
    "paypal",
    "affiliate",
    "adsense",
    "sponsored",
    "scrapy",
    "beautifulsoup",
    "selenium",
    "playwright",
)


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_sprint19_packages_have_no_payment_affiliate_or_scraping_dependencies() -> None:
    for package in SPRINT19_PACKAGES:
        package_root = ROOT / package
        assert package_root.is_dir(), f"Expected Sprint 19 package missing: {package}"
        python_files = list(package_root.rglob("*.py"))
        assert python_files, f"Sprint 19 package has no source files: {package}"
        for path in python_files:
            lowered = path.read_text(encoding="utf-8").lower()
            for token in FORBIDDEN_TOKENS:
                assert token not in lowered, f"{path} references forbidden token {token!r}"


def test_sprint19_endpoints_have_no_payment_affiliate_or_scraping_dependencies() -> None:
    for relative in (
        "app/api/v1/endpoints/alert_rules.py",
        "app/api/v1/endpoints/notifications.py",
        "app/api/v1/endpoints/dashboard.py",
        "app/api/v1/endpoints/watchlists.py",
    ):
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS:
            assert token not in lowered, f"{relative} references forbidden token {token!r}"


def test_sprint19_services_exist() -> None:
    expectations = {
        "app/services/watchlist_service_ext.py": "ExtendedWatchlistService",
        "app/services/alert_rule_service.py": "AlertRuleService",
        "app/services/alert_evaluation_service.py": "AlertEvaluationService",
        "app/services/notification_center_service.py": "NotificationCenterService",
        "app/services/notification_preference_service.py": "NotificationPreferenceService",
        "app/services/user_dashboard_service.py": "UserDashboardService",
    }
    for relative, class_name in expectations.items():
        path = ROOT / relative
        assert path.is_file(), f"Expected Sprint 19 service module missing: {relative}"
        text = path.read_text(encoding="utf-8")
        assert f"class {class_name}" in text, f"{relative} does not define {class_name}"


def test_sprint19_notification_email_is_explicitly_simulated() -> None:
    """The one Sprint 19 "email" path must be unmistakably a mock — no SMTP,
    no real provider SDK, and a marker string proving nothing real is sent.
    """
    provider_path = ROOT / "app/notifications/email/provider.py"
    text = provider_path.read_text(encoding="utf-8")
    assert "MockEmailNotificationProvider" in text
    assert "SIMULATED" in text.upper()

    lowered = text.lower()
    for forbidden in ("smtplib", "sendgrid", "mailgun", "amazon ses", "postmark", "twilio"):
        assert forbidden not in lowered, f"email provider references real transport {forbidden!r}"


def test_sprint19_has_no_sms_or_push_notification_channels() -> None:
    from app.domain.entities.watchlist import NotificationChannel

    # Sprint 10's NotificationChannel enum is the single source of truth for
    # deliverable channels; Sprint 19 must not have quietly added SMS/push.
    channel_names = {member.name for member in NotificationChannel}
    channel_values = {member.value for member in NotificationChannel}
    assert channel_names == {"MOCK", "IN_APP", "EMAIL"}
    assert "sms" not in channel_values
    assert "push" not in channel_values

    for relative in ("app/notifications/delivery.py", "app/notifications/memory.py"):
        lowered = (ROOT / relative).read_text(encoding="utf-8").lower()
        assert "twilio" not in lowered
        assert "firebase" not in lowered
        assert "apns" not in lowered
        assert "fcm" not in lowered


def test_sprint19_does_not_introduce_external_scheduler_dependency() -> None:
    for package in ("app/alerts", "app/notifications"):
        for path in (ROOT / package).rglob("*.py"):
            lowered = path.read_text(encoding="utf-8").lower()
            for scheduler in ("celery", "apscheduler", "airflow", "cron"):
                assert scheduler not in lowered, (
                    f"{path} references external scheduler {scheduler!r}"
                )
