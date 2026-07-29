"""Sprint 19 Shopping Assistant integration with Watchlists/Alerts/Notifications.

Covers authenticated add-to-watchlist, anonymous fallback (rejected write /
still-functional read paths), and the assistant's alert-rule/notification
summarization and buy-or-wait guidance surfaces. Mirrors the collaborator
wiring pattern in ``tests/unit/test_marketplace_data_shopping_integration.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.alerts.memory import InMemoryAlertRuleRepository
from app.domain.entities.alerts import AlertCondition, AlertConditionType
from app.domain.entities.notifications import NotificationType
from app.domain.exceptions import ShoppingAssistantValidationError
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.notifications.memory import InMemoryNotificationCenterRepository
from app.services.alert_rule_service import AlertRuleService
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_preference_service import NotificationPreferenceService
from app.services.price_history_service import PriceHistoryService
from app.services.shopping_assistant_service import ShoppingAssistantService
from app.services.watchlist_service_ext import ExtendedWatchlistService
from app.watchlists.memory import InMemoryWatchlistStore

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _make_assistant() -> tuple[
    ShoppingAssistantService, ExtendedWatchlistService, AlertRuleService, NotificationCenterService
]:
    watchlist_store = InMemoryWatchlistStore()
    price_service = PriceHistoryService(InMemoryPriceHistoryStore(), app_env="development")
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"id-{counter['n']}"

    watchlists = ExtendedWatchlistService(
        watchlist_store,
        price_history_service=price_service,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    rule_repo = InMemoryAlertRuleRepository()
    alert_rules = AlertRuleService(
        rule_repo, watchlist_repository=watchlist_store, clock=lambda: FIXED_NOW, id_factory=next_id
    )
    notif_repo = InMemoryNotificationCenterRepository()
    notif_prefs = NotificationPreferenceService(notif_repo, clock=lambda: FIXED_NOW)
    notifications = NotificationCenterService(
        notif_repo, preference_service=notif_prefs, clock=lambda: FIXED_NOW, id_factory=next_id
    )

    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
        allow_client_mode=True,
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    assistant = ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=60),
        watchlist_service=watchlists,
        alert_rule_service=alert_rules,
        notification_center_service=notifications,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    return assistant, watchlists, alert_rules, notifications


# --------------------------------------------------------------------- add_to_watchlist


@pytest.mark.asyncio
async def test_authenticated_add_to_watchlist_creates_default_watchlist() -> None:
    assistant, watchlists, _, _ = _make_assistant()
    result = await assistant.add_to_watchlist(
        user_id="user-1", canonical_product_id="prod-1", product_label="Phone"
    )
    assert result["added"] is True
    wl = watchlists.get_watchlist(result["watchlist_id"])
    assert wl.owner_id == "user-1"
    assert wl.is_default is True


@pytest.mark.asyncio
async def test_authenticated_add_to_watchlist_is_idempotent() -> None:
    assistant, _, _, _ = _make_assistant()
    first = await assistant.add_to_watchlist(user_id="user-1", canonical_product_id="prod-1")
    second = await assistant.add_to_watchlist(user_id="user-1", canonical_product_id="prod-1")
    assert first["item"]["item_id"] == second["item"]["item_id"]


@pytest.mark.asyncio
async def test_anonymous_add_to_watchlist_is_rejected() -> None:
    assistant, _, _, _ = _make_assistant()
    with pytest.raises(ShoppingAssistantValidationError):
        await assistant.add_to_watchlist(user_id=None, canonical_product_id="prod-1")


@pytest.mark.asyncio
async def test_add_to_watchlist_without_collaborator_fails_gracefully() -> None:
    """Anonymous fallback: when no watchlist_service is wired in at all,
    an authenticated request degrades to a structured failure instead of
    raising an AttributeError."""
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
        allow_client_mode=True,
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    assistant = ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=60),
        watchlist_service=None,
        clock=lambda: FIXED_NOW,
    )
    result = await assistant.add_to_watchlist(user_id="user-1", canonical_product_id="prod-1")
    assert result["added"] is False
    assert result["reason"] == "watchlist_service_unavailable"


# --------------------------------------------------------- alert rule / notification surfaces


def test_describe_active_alert_rules_empty_for_anonymous() -> None:
    assistant, _, _, _ = _make_assistant()
    assert assistant.describe_active_alert_rules(None) == []


def test_describe_active_alert_rules_lists_enabled_rules_for_user() -> None:
    assistant, _, alert_rules, _ = _make_assistant()
    alert_rules.create_rule(
        user_id="user-1",
        name="Drop watcher",
        conditions=[AlertCondition(condition_type=AlertConditionType.PRICE_DROP)],
    )
    rules = assistant.describe_active_alert_rules("user-1")
    assert len(rules) == 1
    assert rules[0]["name"] == "Drop watcher"


def test_summarize_recent_alerts_unavailable_for_anonymous() -> None:
    assistant, _, _, _ = _make_assistant()
    summary = assistant.summarize_recent_alerts(None)
    assert summary == {"count": 0, "notifications": [], "available": False}


def test_summarize_recent_alerts_returns_user_notifications() -> None:
    assistant, _, _, notifications = _make_assistant()
    notifications.create_notification(
        user_id="user-1", title="Price drop!", body="p", type=NotificationType.PRICE_DROP
    )
    summary = assistant.summarize_recent_alerts("user-1")
    assert summary["available"] is True
    assert summary["count"] == 1


def test_explain_alert_trigger_returns_notification_detail() -> None:
    assistant, _, _, notifications = _make_assistant()
    notification = notifications.create_notification(
        user_id="user-1",
        title="Restock",
        body="Back in stock",
        type=NotificationType.RESTOCK,
        metadata={"rule_id": "rule-1"},
    )
    explanation = assistant.explain_alert_trigger(
        user_id="user-1", notification_id=notification.notification_id
    )
    assert explanation["explained"] is True
    assert explanation["type"] == "restock"
    assert explanation["metadata"]["rule_id"] == "rule-1"


def test_explain_alert_trigger_not_found_for_wrong_user() -> None:
    assistant, _, _, notifications = _make_assistant()
    notification = notifications.create_notification(
        user_id="user-1", title="Restock", body="body", type=NotificationType.RESTOCK
    )
    explanation = assistant.explain_alert_trigger(
        user_id="someone-else", notification_id=notification.notification_id
    )
    assert explanation["explained"] is False


def test_recent_price_changes_and_freshness_warnings_filter_by_type() -> None:
    assistant, _, _, notifications = _make_assistant()
    notifications.create_notification(
        user_id="user-1", title="Drop", body="p", type=NotificationType.PRICE_DROP
    )
    notifications.create_notification(
        user_id="user-1", title="Stale", body="s", type=NotificationType.FRESHNESS_WARNING
    )
    notifications.create_notification(
        user_id="user-1", title="Sys", body="sys", type=NotificationType.SYSTEM
    )

    price_changes = assistant.recent_price_changes("user-1")
    assert {n["type"] for n in price_changes} == {"price_drop"}

    freshness = assistant.freshness_warnings("user-1")
    assert {n["type"] for n in freshness} == {"freshness_warning"}


# --------------------------------------------------------------------- buy-or-wait guidance


def test_recommend_buy_or_wait_works_anonymously() -> None:
    assistant, _, _, _ = _make_assistant()
    result = assistant.recommend_buy_or_wait("iPhone 15 Pro")
    # Either a real catalog match with buy/wait guidance, or a clear no-match
    # message — both are valid, anonymous-safe, read-only outcomes.
    assert "guidance" in result or "message" in result


def test_recommend_buy_or_wait_returns_guidance_for_catalog_match() -> None:
    assistant, _, _, _ = _make_assistant()
    result = assistant.recommend_buy_or_wait("Lenovo LOQ 15 RTX 4060")
    assert result["product_id"] == "sa-laptop-loq-15"
    assert isinstance(result["guidance"], str) and result["guidance"]
