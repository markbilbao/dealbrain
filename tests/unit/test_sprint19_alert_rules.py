"""Unit tests for the Sprint 19 rule-driven Alert Engine.

Two layers are exercised:

1. ``AlertEvaluationEngine`` — pure condition logic (all major condition
   types), cooldowns, one-time vs. recurring firing.
2. ``AlertEvaluationService`` — end-to-end batch evaluation against real
   ``WatchlistService``/``PriceHistoryService`` collaborators, covering
   idempotent evaluation, duplicate suppression via dedupe keys, and
   multi-rule batches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.alerts.engine.evaluator import AlertEvaluationEngine
from app.alerts.memory import InMemoryAlertRuleRepository
from app.domain.entities.alerts import (
    AlertCondition,
    AlertConditionType,
    AlertRepeatPolicy,
    AlertRule,
    AlertRuleStatus,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.domain.exceptions import AlertRuleValidationError
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.services.alert_evaluation_service import AlertEvaluationService
from app.services.alert_rule_service import AlertRuleService
from app.services.price_history_service import PriceHistoryService
from app.services.watchlist_service_ext import ExtendedWatchlistService
from app.watchlists.memory import InMemoryWatchlistStore

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _rule(
    *,
    conditions: tuple[AlertCondition, ...],
    cooldown_seconds: int = 0,
    repeat_policy: AlertRepeatPolicy = AlertRepeatPolicy.RECURRING,
    last_triggered_at: datetime | None = None,
    one_time_fired: bool = False,
    enabled: bool = True,
    status: AlertRuleStatus = AlertRuleStatus.ENABLED,
) -> AlertRule:
    return AlertRule(
        rule_id="rule-1",
        user_id="user-1",
        name="Test Rule",
        conditions=conditions,
        created_at=FIXED_NOW,
        enabled=enabled,
        status=status,
        cooldown_seconds=cooldown_seconds,
        repeat_policy=repeat_policy,
        last_triggered_at=last_triggered_at,
        one_time_fired=one_time_fired,
    )


# ============================================================= engine: conditions


def test_engine_price_drop_triggers_on_decrease() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW, id_factory=lambda: "eval-1")
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),))
    result = engine.evaluate_rule(rule, {"price": 90.0, "previous_price": 100.0})
    assert result.triggered is True
    assert "dropped" in result.reason


def test_engine_price_drop_does_not_trigger_on_increase() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),))
    result = engine.evaluate_rule(rule, {"price": 110.0, "previous_price": 100.0})
    assert result.triggered is False


def test_engine_percentage_price_decrease() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(
            AlertCondition(
                condition_type=AlertConditionType.PERCENTAGE_PRICE_DECREASE, threshold_percent=10.0
            ),
        )
    )
    triggered = engine.evaluate_rule(rule, {"price": 85.0, "previous_price": 100.0})
    assert triggered.triggered is True
    not_triggered = engine.evaluate_rule(rule, {"price": 95.0, "previous_price": 100.0})
    assert not_triggered.triggered is False


def test_engine_percentage_price_decrease_requires_threshold() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.PERCENTAGE_PRICE_DECREASE),)
    )
    result = engine.evaluate_rule(rule, {"price": 85.0, "previous_price": 100.0})
    assert result.triggered is False
    assert result.partial_failure is True
    assert "threshold_percent" in (result.error or "")


def test_engine_absolute_price_decrease() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(
            AlertCondition(
                condition_type=AlertConditionType.ABSOLUTE_PRICE_DECREASE, threshold_value=20.0
            ),
        )
    )
    triggered = engine.evaluate_rule(rule, {"price": 75.0, "previous_price": 100.0})
    assert triggered.triggered is True
    not_triggered = engine.evaluate_rule(rule, {"price": 90.0, "previous_price": 100.0})
    assert not_triggered.triggered is False


def test_engine_price_increase() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_INCREASE),))
    result = engine.evaluate_rule(rule, {"price": 110.0, "previous_price": 100.0})
    assert result.triggered is True


def test_engine_restocked_requires_transition_from_out_of_stock() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.RESTOCKED),))
    triggered = engine.evaluate_rule(
        rule, {"availability": "in_stock", "previous_availability": "out_of_stock"}
    )
    assert triggered.triggered is True
    already_available = engine.evaluate_rule(
        rule, {"availability": "in_stock", "previous_availability": "in_stock"}
    )
    assert already_available.triggered is False


def test_engine_unavailable_triggers_on_new_out_of_stock() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.UNAVAILABLE),))
    triggered = engine.evaluate_rule(
        rule, {"availability": "out_of_stock", "previous_availability": "in_stock"}
    )
    assert triggered.triggered is True
    already_out = engine.evaluate_rule(
        rule, {"availability": "out_of_stock", "previous_availability": "out_of_stock"}
    )
    assert already_out.triggered is False


def test_engine_low_inventory_uses_default_and_explicit_threshold() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    default_rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.LOW_INVENTORY),)
    )
    assert engine.evaluate_rule(default_rule, {"inventory": 2}).triggered is True
    assert engine.evaluate_rule(default_rule, {"inventory": 10}).triggered is False

    custom_rule = _rule(
        conditions=(
            AlertCondition(condition_type=AlertConditionType.LOW_INVENTORY, threshold_value=1),
        )
    )
    assert engine.evaluate_rule(custom_rule, {"inventory": 2}).triggered is False


def test_engine_better_offer() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.BETTER_OFFER),))
    triggered = engine.evaluate_rule(rule, {"price": 100.0, "better_offer_price": 80.0})
    assert triggered.triggered is True
    not_triggered = engine.evaluate_rule(rule, {"price": 100.0, "better_offer_price": 120.0})
    assert not_triggered.triggered is False


def test_engine_preferred_seller_available() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.PREFERRED_SELLER_AVAILABLE),)
    )
    triggered = engine.evaluate_rule(
        rule,
        {
            "seller": "Official Store",
            "previous_seller": "Random Reseller",
            "preferred_sellers": ["Official Store"],
        },
    )
    assert triggered.triggered is True
    unchanged = engine.evaluate_rule(
        rule,
        {
            "seller": "Official Store",
            "previous_seller": "Official Store",
            "preferred_sellers": ["Official Store"],
        },
    )
    assert unchanged.triggered is False


def test_engine_stale_data_via_status_and_threshold() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    status_rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.STALE_DATA),))
    assert engine.evaluate_rule(status_rule, {"freshness_status": "stale"}).triggered is True
    assert engine.evaluate_rule(status_rule, {"freshness_status": "fresh"}).triggered is False

    threshold_rule = _rule(
        conditions=(
            AlertCondition(condition_type=AlertConditionType.STALE_DATA, threshold_value=24.0),
        )
    )
    assert engine.evaluate_rule(threshold_rule, {"age_hours": 48.0}).triggered is True
    assert engine.evaluate_rule(threshold_rule, {"age_hours": 2.0}).triggered is False


def test_engine_freshness_restored() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.FRESHNESS_RESTORED),))
    triggered = engine.evaluate_rule(
        rule, {"freshness_status": "fresh", "previous_freshness_status": "stale"}
    )
    assert triggered.triggered is True
    no_transition = engine.evaluate_rule(
        rule, {"freshness_status": "fresh", "previous_freshness_status": "fresh"}
    )
    assert no_transition.triggered is False


def test_engine_dealscore_threshold_gte_and_lte() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    gte_rule = _rule(
        conditions=(
            AlertCondition(
                condition_type=AlertConditionType.DEALSCORE_THRESHOLD,
                threshold_value=80.0,
                comparison="gte",
            ),
        )
    )
    assert engine.evaluate_rule(gte_rule, {"dealscore": 85.0}).triggered is True
    assert engine.evaluate_rule(gte_rule, {"dealscore": 75.0}).triggered is False

    lte_rule = _rule(
        conditions=(
            AlertCondition(
                condition_type=AlertConditionType.DEALSCORE_THRESHOLD,
                threshold_value=40.0,
                comparison="lte",
            ),
        )
    )
    assert engine.evaluate_rule(lte_rule, {"dealscore": 30.0}).triggered is True
    assert engine.evaluate_rule(lte_rule, {"dealscore": 60.0}).triggered is False


def test_engine_or_semantics_across_multiple_conditions() -> None:
    """A rule with multiple conditions fires if ANY condition holds."""
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(
            AlertCondition(condition_type=AlertConditionType.PRICE_DROP),
            AlertCondition(condition_type=AlertConditionType.RESTOCKED),
        )
    )
    result = engine.evaluate_rule(
        rule,
        {
            "price": 100.0,
            "previous_price": 100.0,
            "availability": "in_stock",
            "previous_availability": "out_of_stock",
        },
    )
    assert result.triggered is True
    assert "restocked" in result.reason


# ============================================================= engine: cooldown / one-time


def test_engine_cooldown_blocks_immediate_refire() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
        cooldown_seconds=3600,
        last_triggered_at=FIXED_NOW - timedelta(minutes=5),
    )
    assert engine.is_in_cooldown(rule, FIXED_NOW) is True
    result = engine.evaluate_rule(rule, {"price": 50.0, "previous_price": 100.0}, now=FIXED_NOW)
    assert result.triggered is False
    assert "cooldown" in result.reason


def test_engine_cooldown_expires_after_window() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
        cooldown_seconds=60,
        last_triggered_at=FIXED_NOW - timedelta(minutes=5),
    )
    assert engine.is_in_cooldown(rule, FIXED_NOW) is False
    result = engine.evaluate_rule(rule, {"price": 50.0, "previous_price": 100.0}, now=FIXED_NOW)
    assert result.triggered is True


def test_engine_one_time_rule_fires_once_then_is_exhausted() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
        repeat_policy=AlertRepeatPolicy.ONE_TIME,
    )
    first = engine.evaluate_rule(rule, {"price": 50.0, "previous_price": 100.0}, now=FIXED_NOW)
    assert first.triggered is True

    fired_rule = engine.mark_triggered(rule, FIXED_NOW)
    assert fired_rule.one_time_fired is True

    second = engine.evaluate_rule(
        fired_rule, {"price": 40.0, "previous_price": 50.0}, now=FIXED_NOW
    )
    assert second.triggered is False
    assert "one-time" in second.reason


def test_engine_recurring_rule_can_fire_repeatedly_outside_cooldown() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),))
    fired_once = engine.mark_triggered(rule, FIXED_NOW - timedelta(hours=1))
    result = engine.evaluate_rule(
        fired_once, {"price": 40.0, "previous_price": 50.0}, now=FIXED_NOW
    )
    assert result.triggered is True


def test_engine_disabled_rule_never_fires() -> None:
    engine = AlertEvaluationEngine(clock=lambda: FIXED_NOW)
    rule = _rule(
        conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
        enabled=False,
    )
    result = engine.evaluate_rule(rule, {"price": 50.0, "previous_price": 100.0})
    assert result.triggered is False
    assert "disabled" in result.reason


# ============================================================= AlertRuleService validation


def _rule_service() -> AlertRuleService:
    return AlertRuleService(
        InMemoryAlertRuleRepository(), clock=lambda: FIXED_NOW, id_factory=lambda: "rule-x"
    )


def test_rule_service_requires_at_least_one_condition() -> None:
    service = _rule_service()
    with pytest.raises(AlertRuleValidationError):
        service.create_rule(user_id="user-1", name="Empty", conditions=[])


def test_rule_service_requires_threshold_for_absolute_decrease() -> None:
    service = _rule_service()
    with pytest.raises(AlertRuleValidationError):
        service.create_rule(
            user_id="user-1",
            name="Bad",
            conditions=[{"condition_type": "absolute_price_decrease"}],
        )


def test_rule_service_accepts_dict_conditions_and_pause_resume() -> None:
    service = _rule_service()
    rule = service.create_rule(
        user_id="user-1",
        name="Drop Alert",
        conditions=[{"condition_type": "price_drop"}],
    )
    assert rule.status == AlertRuleStatus.ENABLED

    paused = service.pause_rule(rule.rule_id, user_id="user-1")
    assert paused.status == AlertRuleStatus.DISABLED
    assert paused.enabled is False

    resumed = service.resume_rule(rule.rule_id, user_id="user-1")
    assert resumed.status == AlertRuleStatus.ENABLED
    assert resumed.enabled is True


# ============================================================= AlertEvaluationService integration


_snapshot_seq = {"n": 0}


async def _seed_price_snapshots(
    store: InMemoryPriceHistoryStore, *, product_id: str, prices: list[float]
) -> None:
    price_svc = PriceHistoryService(store, app_env="development")
    for idx, amount in enumerate(prices):
        _snapshot_seq["n"] += 1
        await price_svc.record_snapshot(
            PriceSnapshot(
                snapshot_id=UUID(f"cccccccc-0001-4000-8000-{_snapshot_seq['n']:012d}"),
                canonical_product_id=product_id,
                marketplace="shopee",
                listing_id=f"{product_id}-list-{idx}",
                currency="PHP",
                item_price=amount,
                shipping_cost=0.0,
                total_cost=amount,
                availability=AvailabilityStatus.IN_STOCK,
                observed_at=datetime(2026, 6, 1 + idx, 12, 0, tzinfo=UTC),
                seller_name="Demo Seller",
            )
        )


def _build_evaluation_stack() -> tuple[
    ExtendedWatchlistService,
    AlertRuleService,
    AlertEvaluationService,
    InMemoryWatchlistStore,
    InMemoryPriceHistoryStore,
]:
    watchlist_store = InMemoryWatchlistStore()
    price_store = InMemoryPriceHistoryStore()
    price_service = PriceHistoryService(price_store, app_env="development")
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
    rules = AlertRuleService(
        rule_repo, watchlist_repository=watchlist_store, clock=lambda: FIXED_NOW, id_factory=next_id
    )
    evaluation = AlertEvaluationService(
        rule_repo,
        watchlist_store,
        event_repository=rule_repo,
        price_history_service=price_service,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    return watchlists, rules, evaluation, watchlist_store, price_store


@pytest.mark.asyncio
async def test_evaluation_service_triggers_price_drop_and_creates_event() -> None:
    watchlists, rules, evaluation, _, price_store = _build_evaluation_stack()
    wl = watchlists.create_watchlist(name="Phones", owner_id="user-1")
    await watchlists.add_item_idempotent(
        wl.watchlist_id,
        canonical_product_id="prod-drop",
        last_known_price=100.0,
    )
    await _seed_price_snapshots(price_store, product_id="prod-drop", prices=[90.0])
    rule = rules.create_rule(
        user_id="user-1",
        name="Any drop",
        watchlist_id=wl.watchlist_id,
        conditions=[AlertCondition(condition_type=AlertConditionType.PRICE_DROP)],
    )

    summary = await evaluation.evaluate_rules([rule], now=FIXED_NOW)
    assert summary.triggered_count == 1
    assert len(summary.events_created) == 1
    assert summary.events_created[0].event_type.value == "price_drop"


@pytest.mark.asyncio
async def test_evaluation_service_idempotent_and_dedupes_duplicate_events() -> None:
    """Re-evaluating an unchanged observation must not create a second event."""
    watchlists, rules, evaluation, _, price_store = _build_evaluation_stack()
    wl = watchlists.create_watchlist(name="Phones", owner_id="user-1")
    await watchlists.add_item_idempotent(
        wl.watchlist_id,
        canonical_product_id="prod-dedupe",
        last_known_price=100.0,
    )
    await _seed_price_snapshots(price_store, product_id="prod-dedupe", prices=[80.0])
    rule = rules.create_rule(
        user_id="user-1",
        name="Any drop",
        watchlist_id=wl.watchlist_id,
        conditions=[AlertCondition(condition_type=AlertConditionType.PRICE_DROP)],
    )

    first = await evaluation.evaluate_rules([rule], now=FIXED_NOW)
    assert len(first.events_created) == 1

    refreshed_rule = rules.get_rule(rule.rule_id)
    second = await evaluation.evaluate_rules([refreshed_rule], now=FIXED_NOW + timedelta(seconds=1))
    # Same underlying observation -> same fingerprint/dedupe key -> no new event,
    # even though the condition still evaluates as "triggered".
    assert second.triggered_count == 1
    assert len(second.events_created) == 0


@pytest.mark.asyncio
async def test_evaluation_service_batch_across_multiple_rules_and_items() -> None:
    watchlists, rules, evaluation, _, price_store = _build_evaluation_stack()
    wl = watchlists.create_watchlist(name="Phones", owner_id="user-1")
    await watchlists.add_item_idempotent(
        wl.watchlist_id, canonical_product_id="prod-a", last_known_price=100.0
    )
    await watchlists.add_item_idempotent(
        wl.watchlist_id, canonical_product_id="prod-b", last_known_price=50.0
    )
    await _seed_price_snapshots(price_store, product_id="prod-a", prices=[80.0])
    await _seed_price_snapshots(
        price_store, product_id="prod-b", prices=[60.0]
    )  # increase, no drop

    rules.create_rule(
        user_id="user-1",
        name="Watchlist-wide drop",
        watchlist_id=wl.watchlist_id,
        conditions=[AlertCondition(condition_type=AlertConditionType.PRICE_DROP)],
    )

    summary = await evaluation.evaluate_watchlist(wl.watchlist_id, now=FIXED_NOW)
    assert summary.rules_evaluated == 1
    assert summary.triggered_count == 1  # only prod-a dropped
    assert len(summary.outcomes) == 2  # both items were evaluated


@pytest.mark.asyncio
async def test_evaluation_service_respects_cooldown_across_batches() -> None:
    watchlists, rules, evaluation, _, price_store = _build_evaluation_stack()
    wl = watchlists.create_watchlist(name="Phones", owner_id="user-1")
    await watchlists.add_item_idempotent(
        wl.watchlist_id, canonical_product_id="prod-cd", last_known_price=100.0
    )
    await _seed_price_snapshots(price_store, product_id="prod-cd", prices=[80.0])
    rule = rules.create_rule(
        user_id="user-1",
        name="Cooling down",
        watchlist_id=wl.watchlist_id,
        conditions=[AlertCondition(condition_type=AlertConditionType.PRICE_DROP)],
        cooldown_seconds=3600,
    )

    first = await evaluation.evaluate_watchlist(wl.watchlist_id, now=FIXED_NOW)
    assert first.triggered_count == 1

    refreshed_rule = rules.get_rule(rule.rule_id)
    assert refreshed_rule.last_triggered_at == FIXED_NOW

    second = await evaluation.evaluate_watchlist(
        wl.watchlist_id, now=FIXED_NOW + timedelta(minutes=10)
    )
    assert second.triggered_count == 0
