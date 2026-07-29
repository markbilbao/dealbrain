"""Deterministic Alert Rule evaluation engine — Sprint 19.

Pure, scheduler-neutral evaluation: given an :class:`AlertRule` and a fresh
observation snapshot for the item(s) it watches, produce
:class:`~app.domain.entities.alerts.AlertEvaluation` results. The engine never
sleeps, starts background work, or mutates shared state beyond the
``AlertRule`` instances callers explicitly ask it to update
(:meth:`AlertEvaluationEngine.mark_triggered`).

Observation snapshots are plain ``dict``s (or any ``Mapping``) with the
following recognized keys (all optional — missing keys are treated as
unknown/``None`` and simply fail to trigger price/availability-dependent
conditions rather than raising):

``price``, ``previous_price``, ``currency``, ``inventory``, ``availability``,
``previous_availability``, ``seller``, ``previous_seller``, ``marketplace``,
``previous_marketplace``, ``freshness_status``, ``previous_freshness_status``,
``age_hours``, ``dealscore``, ``previous_dealscore``, ``historical_low``,
``target_price``, ``preferred_sellers``, ``preferred_marketplaces``,
``better_offer_price``, ``better_offer_id``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.alerts.engine.dedupe import observation_fingerprint
from app.domain.entities.alerts import (
    AlertCondition,
    AlertConditionType,
    AlertEvaluation,
    AlertRepeatPolicy,
    AlertRule,
    AlertRuleStatus,
)

Observation = Mapping[str, Any]

# Availability strings treated as "in stock" / "out of stock" for restock and
# unavailable conditions. Anything else is treated as neutral (no transition).
_IN_STOCK_VALUES = frozenset({"in_stock", "available", "preorder"})
_OUT_OF_STOCK_VALUES = frozenset({"out_of_stock", "unavailable", "sold_out"})

_DEFAULT_LOW_INVENTORY_THRESHOLD = 3.0


class ConditionEvaluationError(Exception):
    """Raised internally when a single condition cannot be evaluated safely.

    Always caught by :class:`AlertEvaluationEngine` — never escapes
    :meth:`AlertEvaluationEngine.evaluate_rule`; surfaced instead via
    ``AlertEvaluation.partial_failure``/``error``.
    """


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConditionEvaluationError(f"expected numeric value, got {value!r}") from exc


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_sequence(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(value)
    return (value,)


class AlertEvaluationEngine:
    """Evaluates :class:`AlertRule` conditions against observation snapshots."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        low_inventory_threshold: float = _DEFAULT_LOW_INVENTORY_THRESHOLD,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._low_inventory_threshold = low_inventory_threshold
        self._condition_evaluators: dict[
            AlertConditionType, Callable[[AlertCondition, Observation], tuple[bool, str]]
        ] = {
            AlertConditionType.PRICE_DROP: self._eval_price_drop,
            AlertConditionType.PERCENTAGE_PRICE_DECREASE: self._eval_percentage_price_decrease,
            AlertConditionType.ABSOLUTE_PRICE_DECREASE: self._eval_absolute_price_decrease,
            AlertConditionType.PRICE_INCREASE: self._eval_price_increase,
            AlertConditionType.TARGET_PRICE_REACHED: self._eval_target_price_reached,
            AlertConditionType.HISTORICAL_LOW: self._eval_historical_low,
            AlertConditionType.DEALSCORE_IMPROVED: self._eval_dealscore_improved,
            AlertConditionType.DEALSCORE_THRESHOLD: self._eval_dealscore_threshold,
            AlertConditionType.RESTOCKED: self._eval_restocked,
            AlertConditionType.UNAVAILABLE: self._eval_unavailable,
            AlertConditionType.LOW_INVENTORY: self._eval_low_inventory,
            AlertConditionType.BETTER_OFFER: self._eval_better_offer,
            AlertConditionType.PREFERRED_SELLER_AVAILABLE: self._eval_preferred_seller_available,
            AlertConditionType.PREFERRED_MARKETPLACE_AVAILABLE: (
                self._eval_preferred_marketplace_available
            ),
            AlertConditionType.STALE_DATA: self._eval_stale_data,
            AlertConditionType.FRESHNESS_RESTORED: self._eval_freshness_restored,
        }

    # ------------------------------------------------------------------ cooldown / repeat helpers
    def is_in_cooldown(self, rule: AlertRule, now: datetime | None = None) -> bool:
        """Return True if ``rule`` last fired within its cooldown window."""
        if rule.cooldown_seconds <= 0 or rule.last_triggered_at is None:
            return False
        now = now or self._clock()
        elapsed = (now - rule.last_triggered_at).total_seconds()
        return elapsed < rule.cooldown_seconds

    def is_one_time_exhausted(self, rule: AlertRule) -> bool:
        """Return True if a one-time rule has already fired and cannot fire again."""
        return rule.repeat_policy == AlertRepeatPolicy.ONE_TIME and rule.one_time_fired

    def can_fire(self, rule: AlertRule, now: datetime | None = None) -> bool:
        """Return True if ``rule`` is eligible to be evaluated/fired at ``now``.

        Checks the administrative enable flags, one-time exhaustion, and
        cooldown — all independent of whether its conditions currently hold.
        """
        if not rule.enabled or rule.status != AlertRuleStatus.ENABLED:
            return False
        if self.is_one_time_exhausted(rule):
            return False
        return not self.is_in_cooldown(rule, now)

    def mark_triggered(self, rule: AlertRule, now: datetime | None = None) -> AlertRule:
        """Return an updated copy of ``rule`` reflecting a successful firing.

        Sets ``last_triggered_at`` and, for one-time rules, ``one_time_fired``.
        ``AlertRule`` is frozen, so callers must persist the returned copy
        (e.g. via ``AlertRuleRepository.save_rule``) themselves.
        """
        now = now or self._clock()
        return AlertRule(
            rule_id=rule.rule_id,
            user_id=rule.user_id,
            name=rule.name,
            conditions=rule.conditions,
            created_at=rule.created_at,
            watchlist_id=rule.watchlist_id,
            item_id=rule.item_id,
            enabled=rule.enabled,
            status=rule.status,
            cooldown_seconds=rule.cooldown_seconds,
            last_triggered_at=now,
            repeat_policy=rule.repeat_policy,
            severity=rule.severity,
            timezone=rule.timezone,
            channel_preferences=rule.channel_preferences,
            updated_at=now,
            one_time_fired=rule.one_time_fired or rule.repeat_policy == AlertRepeatPolicy.ONE_TIME,
        )

    # ------------------------------------------------------------------------- evaluation
    def evaluate_rule(
        self,
        rule: AlertRule,
        observation: Observation,
        *,
        now: datetime | None = None,
    ) -> AlertEvaluation:
        """Evaluate all of ``rule``'s conditions against ``observation``.

        A rule triggers if *any* of its conditions hold (OR semantics) —
        callers wanting AND semantics should split conditions across
        separate rules. Per-condition evaluation errors are caught and
        reported via ``partial_failure``/``error`` rather than propagating,
        so one malformed condition never blocks the others.
        """
        now = now or self._clock()

        if not self.can_fire(rule, now):
            return AlertEvaluation(
                evaluation_id=self._id_factory(),
                triggered=False,
                reason=self._skip_reason(rule, now),
                evaluated_at=now,
                rule_id=rule.rule_id,
                watchlist_id=rule.watchlist_id,
                item_id=rule.item_id,
            )

        reasons: list[str] = []
        errors: list[str] = []
        triggered_condition_type: AlertConditionType | None = None

        for condition in rule.conditions:
            try:
                is_triggered, reason = self._evaluate_condition(condition, observation)
            except ConditionEvaluationError as exc:
                errors.append(f"{condition.condition_type.value}: {exc}")
                continue
            if is_triggered:
                reasons.append(reason)
                if triggered_condition_type is None:
                    triggered_condition_type = condition.condition_type

        triggered = bool(reasons)
        partial_failure = bool(errors)

        if triggered:
            reason_text = "; ".join(reasons)
        elif partial_failure and not reasons:
            reason_text = "all evaluable conditions were false; some conditions failed to evaluate"
        elif not rule.conditions:
            reason_text = "rule has no conditions"
        else:
            reason_text = "no condition matched current observation"

        fingerprint = (
            observation_fingerprint(dict(observation), triggered_condition_type)
            if triggered and triggered_condition_type is not None
            else None
        )

        return AlertEvaluation(
            evaluation_id=self._id_factory(),
            triggered=triggered,
            reason=reason_text,
            evaluated_at=now,
            rule_id=rule.rule_id,
            watchlist_id=rule.watchlist_id,
            item_id=rule.item_id,
            observation_fingerprint=fingerprint,
            partial_failure=partial_failure,
            error="; ".join(errors) if errors else None,
        )

    def evaluate_rules(
        self,
        rules: list[AlertRule],
        observation: Observation,
        *,
        now: datetime | None = None,
    ) -> list[AlertEvaluation]:
        """Evaluate each rule in ``rules`` against the same observation."""
        now = now or self._clock()
        return [self.evaluate_rule(rule, observation, now=now) for rule in rules]

    def _skip_reason(self, rule: AlertRule, now: datetime) -> str:
        if not rule.enabled or rule.status != AlertRuleStatus.ENABLED:
            return "rule is disabled"
        if self.is_one_time_exhausted(rule):
            return "one-time rule has already fired"
        if self.is_in_cooldown(rule, now):
            return "rule is within its cooldown window"
        return "rule is not eligible to fire"

    def _evaluate_condition(
        self, condition: AlertCondition, observation: Observation
    ) -> tuple[bool, str]:
        evaluator = self._condition_evaluators.get(condition.condition_type)
        if evaluator is None:
            raise ConditionEvaluationError(
                f"no evaluator registered for {condition.condition_type.value}"
            )
        return evaluator(condition, observation)

    # ------------------------------------------------------------ per-condition evaluators
    def _eval_price_drop(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        price = _as_float(obs.get("price"))
        previous = _as_float(obs.get("previous_price"))
        if price is None or previous is None:
            return False, "price_drop: missing price or previous_price"
        if price < previous:
            return True, f"price dropped from {previous} to {price}"
        return False, "price_drop: no decrease"

    def _eval_percentage_price_decrease(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        price = _as_float(obs.get("price"))
        previous = _as_float(obs.get("previous_price"))
        threshold = condition.threshold_percent
        if price is None or previous is None or not previous:
            return False, "percentage_price_decrease: missing price data"
        if threshold is None:
            raise ConditionEvaluationError("percentage_price_decrease requires threshold_percent")
        pct_decrease = (previous - price) / previous * 100
        if pct_decrease >= threshold:
            return True, f"price decreased {pct_decrease:.2f}% (threshold {threshold}%)"
        return False, f"price decreased {pct_decrease:.2f}%, below threshold {threshold}%"

    def _eval_absolute_price_decrease(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        price = _as_float(obs.get("price"))
        previous = _as_float(obs.get("previous_price"))
        threshold = condition.threshold_value
        if price is None or previous is None:
            return False, "absolute_price_decrease: missing price data"
        if threshold is None:
            raise ConditionEvaluationError("absolute_price_decrease requires threshold_value")
        decrease = previous - price
        if decrease >= threshold:
            return True, f"price decreased by {decrease} (threshold {threshold})"
        return False, f"price decreased by {decrease}, below threshold {threshold}"

    def _eval_price_increase(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        price = _as_float(obs.get("price"))
        previous = _as_float(obs.get("previous_price"))
        if price is None or previous is None:
            return False, "price_increase: missing price or previous_price"
        if price > previous:
            return True, f"price increased from {previous} to {price}"
        return False, "price_increase: no increase"

    def _eval_target_price_reached(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        price = _as_float(obs.get("price"))
        target = condition.threshold_value
        if target is None:
            target = _as_float(obs.get("target_price"))
        if price is None or target is None:
            return False, "target_price_reached: missing price or target_price"
        if price <= target:
            return True, f"price {price} reached target {target}"
        return False, f"price {price} has not reached target {target}"

    def _eval_historical_low(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        price = _as_float(obs.get("price"))
        historical_low = _as_float(obs.get("historical_low"))
        if price is None or historical_low is None:
            return False, "historical_low: missing price or historical_low"
        if price <= historical_low:
            return True, f"price {price} matches or beats historical low {historical_low}"
        return False, f"price {price} is above historical low {historical_low}"

    def _eval_dealscore_improved(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        dealscore = _as_float(obs.get("dealscore"))
        previous = _as_float(obs.get("previous_dealscore"))
        if dealscore is None or previous is None:
            return False, "dealscore_improved: missing dealscore data"
        threshold = condition.threshold_value or 0.0
        improvement = dealscore - previous
        if improvement >= threshold:
            return True, f"DealScore improved by {improvement:.2f} to {dealscore}"
        return False, f"DealScore improvement {improvement:.2f} below threshold {threshold}"

    def _eval_dealscore_threshold(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        dealscore = _as_float(obs.get("dealscore"))
        threshold = condition.threshold_value
        if dealscore is None:
            return False, "dealscore_threshold: missing dealscore"
        if threshold is None:
            raise ConditionEvaluationError("dealscore_threshold requires threshold_value")
        comparison = condition.comparison or "gte"
        triggered = dealscore <= threshold if comparison == "lte" else dealscore >= threshold
        if triggered:
            return True, f"DealScore {dealscore} met threshold ({comparison} {threshold})"
        return False, f"DealScore {dealscore} did not meet threshold ({comparison} {threshold})"

    def _eval_restocked(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        availability = _as_str(obs.get("availability"))
        previous_availability = _as_str(obs.get("previous_availability"))
        if availability is None:
            return False, "restocked: missing availability"
        now_in_stock = availability in _IN_STOCK_VALUES
        if not now_in_stock:
            return False, "restocked: currently unavailable"
        if previous_availability is None:
            return False, "restocked: no previous availability to compare"
        was_out_of_stock = previous_availability in _OUT_OF_STOCK_VALUES
        if was_out_of_stock:
            return True, f"item restocked ({previous_availability} -> {availability})"
        return False, "restocked: was already available"

    def _eval_unavailable(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        availability = _as_str(obs.get("availability"))
        previous_availability = _as_str(obs.get("previous_availability"))
        if availability is None:
            return False, "unavailable: missing availability"
        now_out_of_stock = availability in _OUT_OF_STOCK_VALUES
        if not now_out_of_stock:
            return False, "unavailable: currently available"
        if previous_availability is not None and previous_availability in _OUT_OF_STOCK_VALUES:
            return False, "unavailable: was already out of stock"
        return True, f"item became unavailable ({availability})"

    def _eval_low_inventory(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        inventory = _as_float(obs.get("inventory"))
        if inventory is None:
            return False, "low_inventory: missing inventory"
        threshold = condition.threshold_value
        if threshold is None:
            threshold = self._low_inventory_threshold
        if inventory <= threshold:
            return True, f"inventory {inventory} at or below threshold {threshold}"
        return False, f"inventory {inventory} above threshold {threshold}"

    def _eval_better_offer(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        current_price = _as_float(obs.get("price"))
        better_price = _as_float(obs.get("better_offer_price"))
        if better_price is None:
            return False, "better_offer: no competing offer present"
        if current_price is None:
            return True, f"better offer available at {better_price}"
        if better_price < current_price:
            return True, f"better offer at {better_price} beats current price {current_price}"
        return False, "better_offer: no cheaper offer found"

    def _eval_preferred_seller_available(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        seller = _as_str(obs.get("seller"))
        previous_seller = _as_str(obs.get("previous_seller"))
        preferred = _as_sequence(obs.get("preferred_sellers"))
        if seller is None or not preferred:
            return False, "preferred_seller_available: missing seller or preferred_sellers"
        if seller not in preferred:
            return False, f"preferred_seller_available: seller {seller} not preferred"
        if previous_seller == seller:
            return False, "preferred_seller_available: unchanged from previous observation"
        return True, f"preferred seller {seller} is now available"

    def _eval_preferred_marketplace_available(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        marketplace = _as_str(obs.get("marketplace"))
        previous_marketplace = _as_str(obs.get("previous_marketplace"))
        preferred = _as_sequence(obs.get("preferred_marketplaces"))
        if marketplace is None or not preferred:
            return (
                False,
                "preferred_marketplace_available: missing marketplace or preferred_marketplaces",
            )
        if marketplace not in preferred:
            return False, f"preferred_marketplace_available: {marketplace} not preferred"
        if previous_marketplace == marketplace:
            return False, "preferred_marketplace_available: unchanged from previous observation"
        return True, f"preferred marketplace {marketplace} is now available"

    def _eval_stale_data(self, condition: AlertCondition, obs: Observation) -> tuple[bool, str]:
        freshness_status = _as_str(obs.get("freshness_status"))
        age_hours = _as_float(obs.get("age_hours"))
        threshold = condition.threshold_value
        if threshold is not None and age_hours is not None:
            if age_hours >= threshold:
                return True, f"data age {age_hours}h exceeds threshold {threshold}h"
            return False, f"data age {age_hours}h below threshold {threshold}h"
        if freshness_status is None:
            return False, "stale_data: missing freshness_status"
        if freshness_status == "stale":
            return True, "data marked stale"
        return False, "stale_data: data is fresh"

    def _eval_freshness_restored(
        self, condition: AlertCondition, obs: Observation
    ) -> tuple[bool, str]:
        freshness_status = _as_str(obs.get("freshness_status"))
        previous_status = _as_str(obs.get("previous_freshness_status"))
        if freshness_status is None or previous_status is None:
            return False, "freshness_restored: missing freshness status data"
        if previous_status == "stale" and freshness_status != "stale":
            return True, "data freshness restored"
        return False, "freshness_restored: no stale-to-fresh transition"
