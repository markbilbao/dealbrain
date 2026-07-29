"""Alert Evaluation orchestration — Sprint 19.

Wires :class:`AlertEvaluationEngine` (pure condition evaluation) to
persistence (:class:`AlertRuleRepository` / :class:`AlertEventRepository` /
``WatchlistRepository``) and optional read-side collaborators
(``MarketplaceDataService`` for freshness/availability/seller signals,
``PriceHistoryService`` for price statistics, ``DealRecommendationService``
for DealScore). Implements :class:`AlertJobTrigger` so future scheduler
infrastructure can invoke evaluation without this module ever starting
background work itself — every entry point here is a synchronous-in-intent,
manually-triggered call.

Deviation from the domain contract: :class:`AlertJobTrigger.trigger_evaluate`
is declared as a synchronous method, but this implementation defines it
``async`` because it must await ``PriceHistoryService``/``DealRecommendationService``
reads. Python does not enforce a sync/async match for ABC method overrides,
so this satisfies the interface mechanically; callers must ``await`` it. All
other public methods on this service are likewise ``async`` for the same
reason.

Previous-observation tracking (needed for delta-based conditions like
``restocked``/``preferred_seller_available``) is kept as a process-local
cache here rather than a new persistence port, mirroring how Sprint 10's
``AlertService`` stashes its own baseline on ``WatchlistItem.last_known_*``
fields. A production deployment would likely persist this via a dedicated
observation-history store; documented here as a deliberate scope boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.alerts.engine.dedupe import build_dedupe_key
from app.alerts.engine.evaluator import AlertEvaluationEngine
from app.domain.entities.alerts import (
    AlertConditionType,
    AlertEvaluation,
    AlertEvent,
    AlertJobTrigger,
    AlertRule,
)
from app.domain.entities.watchlist import Alert, AlertStatus, AlertType, Watchlist, WatchlistItem
from app.domain.exceptions import DealScoreValidationError, PriceHistoryValidationError
from app.domain.interfaces.alert_rule_repository import AlertEventRepository, AlertRuleRepository
from app.domain.interfaces.notification_service import NotificationService
from app.domain.interfaces.watchlist_repository import AlertRepository, WatchlistRepository
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.price_history_service import PriceHistoryService

# AlertConditionType and AlertType share identical string values member-for-
# member (see both enums' Sprint 19 docstrings), so a triggered condition
# maps directly onto a Sprint 10-compatible Alert type.
_CONDITION_TO_ALERT_TYPE: dict[AlertConditionType, AlertType] = {
    member: AlertType(member.value) for member in AlertConditionType
}


@dataclass(frozen=True, slots=True)
class ItemEvaluationOutcome:
    """Per-item evaluation outcome within a batch."""

    item_id: str
    rule_id: str
    evaluation: AlertEvaluation
    event: AlertEvent | None = None
    alert: Alert | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "rule_id": self.rule_id,
            "evaluation": self.evaluation.to_dict(),
            "event": self.event.to_dict() if self.event else None,
            "alert": self.alert.to_dict() if self.alert else None,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class AlertEvaluationSummary:
    """Aggregate outcome of one manual evaluation pass."""

    evaluated_at: datetime
    rules_evaluated: int
    triggered_count: int
    events_created: tuple[AlertEvent, ...] = ()
    alerts_created: tuple[Alert, ...] = ()
    outcomes: tuple[ItemEvaluationOutcome, ...] = ()
    failures: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_at": self.evaluated_at.isoformat(),
            "rules_evaluated": self.rules_evaluated,
            "triggered_count": self.triggered_count,
            "events_created": [e.to_dict() for e in self.events_created],
            "alerts_created": [a.to_dict() for a in self.alerts_created],
            "outcomes": [o.to_dict() for o in self.outcomes],
            "failures": list(self.failures),
        }


class AlertEvaluationService(AlertJobTrigger):
    """Scheduler-neutral orchestrator for rule-driven alert evaluation."""

    def __init__(
        self,
        rule_repository: AlertRuleRepository,
        watchlist_repository: WatchlistRepository,
        *,
        event_repository: AlertEventRepository | None = None,
        alert_repository: AlertRepository | None = None,
        notification_service: NotificationService | None = None,
        notification_center_service: Any | None = None,
        price_history_service: PriceHistoryService | None = None,
        deal_recommendation_service: DealRecommendationService | None = None,
        marketplace_data_service: MarketplaceDataService | None = None,
        engine: AlertEvaluationEngine | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._rules = rule_repository
        # Most in-memory implementations (e.g. InMemoryAlertRuleRepository)
        # satisfy both ports on one object; fall back to the rule repository
        # itself when a distinct event_repository isn't supplied.
        self._events: AlertEventRepository = event_repository or rule_repository  # type: ignore[assignment]
        self._watchlists = watchlist_repository
        self._alerts = alert_repository
        self._notifications = notification_service
        self._notification_center = notification_center_service
        self._price_history = price_history_service
        self._deal_recommendation = deal_recommendation_service
        self._marketplace_data = marketplace_data_service
        self._engine = engine or AlertEvaluationEngine(clock=clock, id_factory=id_factory)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        # Process-local previous-observation cache; see module docstring.
        self._previous_observations: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------- AlertJobTrigger
    async def trigger_evaluate(  # type: ignore[override]
        self,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        rule_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[AlertEvaluation, ...]:
        """Evaluate due rule(s) matching the given scope and return outcomes.

        Declared ``async`` despite the (sync) ``AlertJobTrigger`` ABC
        signature — see module docstring. Exactly one of ``user_id`` /
        ``watchlist_id`` / ``rule_id`` should typically be supplied; when
        none are, every rule is evaluated (equivalent to :meth:`evaluate_all`).
        """
        if rule_id is not None:
            rule = self._rules.get_rule(rule_id)
            rules = [rule] if rule is not None else []
        elif watchlist_id is not None:
            rules = self._rules.list_rules(watchlist_id=watchlist_id)
        elif user_id is not None:
            rules = self._rules.list_rules(user_id=user_id)
        else:
            rules = self._rules.list_rules()
        summary = await self._evaluate_rule_batch(rules, now=now)
        return tuple(outcome.evaluation for outcome in summary.outcomes)

    # ------------------------------------------------------------------- public API
    async def evaluate_all(self, *, now: datetime | None = None) -> AlertEvaluationSummary:
        """Evaluate every enabled alert rule across all users."""
        return await self._evaluate_rule_batch(self._rules.list_rules(enabled=True), now=now)

    async def evaluate_for_user(
        self, user_id: str, *, now: datetime | None = None
    ) -> AlertEvaluationSummary:
        """Evaluate every enabled alert rule owned by ``user_id``."""
        return await self._evaluate_rule_batch(
            self._rules.list_rules(user_id=user_id, enabled=True), now=now
        )

    async def evaluate_watchlist(
        self, watchlist_id: str, *, now: datetime | None = None
    ) -> AlertEvaluationSummary:
        """Evaluate every enabled alert rule scoped to ``watchlist_id``."""
        return await self._evaluate_rule_batch(
            self._rules.list_rules(watchlist_id=watchlist_id, enabled=True), now=now
        )

    async def evaluate_item(
        self, item_id: str, *, now: datetime | None = None
    ) -> AlertEvaluationSummary:
        """Evaluate every enabled alert rule scoped to a single item."""
        return await self._evaluate_rule_batch(
            self._rules.list_rules(item_id=item_id, enabled=True), now=now
        )

    async def evaluate_rules(
        self, rules: list[AlertRule], *, now: datetime | None = None
    ) -> AlertEvaluationSummary:
        """Evaluate an explicit, caller-supplied batch of rules."""
        return await self._evaluate_rule_batch(rules, now=now)

    # ------------------------------------------------------------------ batch engine
    async def _evaluate_rule_batch(
        self, rules: list[AlertRule], *, now: datetime | None
    ) -> AlertEvaluationSummary:
        stamp = now or self._clock()
        outcomes: list[ItemEvaluationOutcome] = []
        events: list[AlertEvent] = []
        alerts: list[Alert] = []
        failures: list[str] = []
        triggered_count = 0

        for rule in rules:
            try:
                items = await self._resolve_items_for_rule(rule)
            except Exception as exc:  # noqa: BLE001 - isolate per-rule failures
                failures.append(f"rule {rule.rule_id}: failed to resolve items ({exc})")
                continue

            for item in items:
                try:
                    outcome = await self._evaluate_rule_for_item(rule, item, now=stamp)
                except Exception as exc:  # noqa: BLE001 - isolate per-item failures
                    failures.append(f"rule {rule.rule_id} / item {item.item_id}: {exc}")
                    continue
                outcomes.append(outcome)
                if outcome.evaluation.triggered:
                    triggered_count += 1
                if outcome.event is not None:
                    events.append(outcome.event)
                if outcome.alert is not None:
                    alerts.append(outcome.alert)

            if not items:
                # Account-wide or unscoped rules with nothing to observe still
                # count as "evaluated" (a no-op pass) for summary accuracy.
                continue

        return AlertEvaluationSummary(
            evaluated_at=stamp,
            rules_evaluated=len(rules),
            triggered_count=triggered_count,
            events_created=tuple(events),
            alerts_created=tuple(alerts),
            outcomes=tuple(outcomes),
            failures=tuple(failures),
        )

    async def _resolve_items_for_rule(self, rule: AlertRule) -> list[WatchlistItem]:
        if rule.item_id is not None:
            item = self._watchlists.get_item(rule.item_id)
            return [item] if item is not None and item.enabled else []
        if rule.watchlist_id is not None:
            return self._watchlists.list_items(watchlist_id=rule.watchlist_id, enabled=True)
        # Account-wide rule: evaluate across every watchlist the user owns.
        watchlists = self._watchlists.list_watchlists(owner_id=rule.user_id, enabled=True)
        items: list[WatchlistItem] = []
        for watchlist in watchlists:
            items.extend(
                self._watchlists.list_items(watchlist_id=watchlist.watchlist_id, enabled=True)
            )
        return items

    async def _evaluate_rule_for_item(
        self, rule: AlertRule, item: WatchlistItem, *, now: datetime
    ) -> ItemEvaluationOutcome:
        observation = await self._build_observation(item)
        evaluation = self._engine.evaluate_rule(rule, observation, now=now)
        self._rules.save_evaluation(evaluation)
        self._previous_observations[item.item_id] = dict(observation)

        if not evaluation.triggered:
            return ItemEvaluationOutcome(
                item_id=item.item_id, rule_id=rule.rule_id, evaluation=evaluation
            )

        condition_type = self._identify_triggered_condition(rule, observation, now=now)
        if condition_type is None:
            return ItemEvaluationOutcome(
                item_id=item.item_id, rule_id=rule.rule_id, evaluation=evaluation
            )

        dedupe_key = build_dedupe_key(
            user_id=rule.user_id,
            condition_type=condition_type,
            rule_id=rule.rule_id,
            watchlist_id=item.watchlist_id,
            item_id=item.item_id,
            fingerprint=evaluation.observation_fingerprint,
        )
        if self._events.find_by_dedupe_key(dedupe_key) is not None:
            # Already raised for this exact occurrence — do not re-notify,
            # but still persist the rule's fired-cooldown/one-time state.
            self._rules.save_rule(self._engine.mark_triggered(rule, now))
            return ItemEvaluationOutcome(
                item_id=item.item_id, rule_id=rule.rule_id, evaluation=evaluation
            )

        self._rules.save_rule(self._engine.mark_triggered(rule, now))

        event = self._build_event(
            condition_type,
            rule=rule,
            item=item,
            observation=observation,
            dedupe_key=dedupe_key,
            now=now,
        )
        self._events.save_event(event)

        watchlist = self._watchlists.get_watchlist(item.watchlist_id)
        alert = self._create_legacy_alert(
            condition_type,
            rule=rule,
            item=item,
            observation=observation,
            evaluation=evaluation,
            now=now,
        )
        self._fan_out(event, watchlist=watchlist, item=item, alert=alert)

        return ItemEvaluationOutcome(
            item_id=item.item_id,
            rule_id=rule.rule_id,
            evaluation=evaluation,
            event=event,
            alert=alert,
        )

    def _identify_triggered_condition(
        self, rule: AlertRule, observation: Mapping[str, Any], *, now: datetime
    ) -> AlertConditionType | None:
        """Determine which single condition triggered ``rule``.

        ``AlertEvaluationEngine.evaluate_rule`` intentionally reports only an
        aggregate OR-triggered result (no per-condition detail in its public
        return value). We re-run each condition in isolation — using a
        cooldown/one-time-reset clone of ``rule`` so a condition that would
        legitimately fire isn't masked by state already consumed by the
        first, aggregate evaluation pass — to recover which one fired for
        typed ``AlertEvent`` construction.
        """
        for condition in rule.conditions:
            probe = replace(
                rule,
                conditions=(condition,),
                cooldown_seconds=0,
                last_triggered_at=None,
                one_time_fired=False,
            )
            result = self._engine.evaluate_rule(probe, observation, now=now)
            if result.triggered:
                return condition.condition_type
        return None

    # ------------------------------------------------------------- observation building
    async def _build_observation(self, item: WatchlistItem) -> dict[str, Any]:
        previous = self._previous_observations.get(item.item_id, {})
        observation: dict[str, Any] = {
            "previous_price": item.last_known_price,
            "previous_dealscore": item.last_known_dealscore,
            "historical_low": item.last_historical_low,
            "target_price": item.target_price,
            "preferred_sellers": item.preferred_sellers,
            "preferred_marketplaces": item.preferred_marketplaces,
        }
        # Carry forward previous-cycle observation fields not re-derivable
        # from WatchlistItem baselines (availability/seller/marketplace/
        # freshness), so delta-based conditions have something to compare.
        for key in (
            "availability",
            "seller",
            "marketplace",
            "freshness_status",
        ):
            if key in previous:
                observation[f"previous_{key}"] = previous[key]

        await self._apply_price_history(item, observation)
        await self._apply_dealscore(item, observation)
        self._apply_marketplace_offer(item, observation)
        return observation

    async def _apply_price_history(self, item: WatchlistItem, observation: dict[str, Any]) -> None:
        if self._price_history is None:
            observation["price"] = item.last_known_price
            return
        try:
            history = await self._price_history.get_product_history(item.canonical_product_id)
        except PriceHistoryValidationError:
            observation["price"] = item.last_known_price
            return
        if history is not None and history.statistics is not None:
            stats = history.statistics
            observation["price"] = stats.current_total_cost
            observation["currency"] = stats.currency
            if stats.lowest_recorded_total_cost is not None:
                observation["historical_low"] = stats.lowest_recorded_total_cost
        else:
            observation["price"] = item.last_known_price

    async def _apply_dealscore(self, item: WatchlistItem, observation: dict[str, Any]) -> None:
        if self._deal_recommendation is None:
            observation["dealscore"] = item.last_known_dealscore
            return
        query = (item.search_query or item.product_label or "").strip()
        if not query:
            observation["dealscore"] = item.last_known_dealscore
            return
        try:
            ranking = self._deal_recommendation.recommend(query)
        except DealScoreValidationError:
            observation["dealscore"] = item.last_known_dealscore
            return
        if ranking.recommended is not None:
            observation["dealscore"] = ranking.recommended.deal_score.score
        else:
            observation["dealscore"] = item.last_known_dealscore

    def _apply_marketplace_offer(self, item: WatchlistItem, observation: dict[str, Any]) -> None:
        if self._marketplace_data is None or not item.marketplace_offer_id:
            return
        try:
            offer = self._marketplace_data.get_offer(item.marketplace_offer_id)
        except Exception:  # noqa: BLE001 - freshness enrichment is best-effort
            return
        observation["availability"] = offer.availability.value
        observation["inventory"] = offer.inventory_quantity
        if offer.seller is not None:
            observation["seller"] = offer.seller.name
        observation["marketplace"] = offer.marketplace
        observation["better_offer_price"] = None
        if offer.freshness is not None:
            observation["freshness_status"] = offer.freshness.status.value
            observation["age_hours"] = offer.freshness.age_hours

    # -------------------------------------------------------------------- event building
    def _build_event(
        self,
        condition_type: AlertConditionType,
        *,
        rule: AlertRule,
        item: WatchlistItem,
        observation: Mapping[str, Any],
        dedupe_key: str,
        now: datetime,
    ) -> AlertEvent:
        common = {
            "event_id": self._id_factory(),
            "user_id": rule.user_id,
            "dedupe_key": dedupe_key,
            "created_at": now,
            "rule_id": rule.rule_id,
            "severity": rule.severity,
        }
        currency = observation.get("currency") or item.currency
        price = observation.get("price")
        previous_price = observation.get("previous_price")

        if condition_type in (
            AlertConditionType.PRICE_DROP,
            AlertConditionType.PERCENTAGE_PRICE_DECREASE,
            AlertConditionType.ABSOLUTE_PRICE_DECREASE,
            AlertConditionType.TARGET_PRICE_REACHED,
            AlertConditionType.HISTORICAL_LOW,
        ):
            return AlertEvent.price_drop(
                previous_price=previous_price if previous_price is not None else price,
                current_price=price,
                currency=currency,
                **common,
            )
        if condition_type == AlertConditionType.PRICE_INCREASE:
            return AlertEvent.price_increase(
                previous_price=previous_price if previous_price is not None else price,
                current_price=price,
                currency=currency,
                **common,
            )
        if condition_type == AlertConditionType.RESTOCKED:
            return AlertEvent.restock(quantity=observation.get("inventory"), **common)
        if condition_type == AlertConditionType.UNAVAILABLE:
            return AlertEvent.out_of_stock(**common)
        if condition_type == AlertConditionType.LOW_INVENTORY:
            return AlertEvent.low_inventory(inventory=observation.get("inventory"), **common)
        if condition_type == AlertConditionType.BETTER_OFFER:
            return AlertEvent.better_offer(
                offer_id=str(observation.get("better_offer_id") or item.marketplace_offer_id or ""),
                total_price=observation.get("better_offer_price") or price or 0.0,
                currency=currency,
                **common,
            )
        if condition_type == AlertConditionType.PREFERRED_SELLER_AVAILABLE:
            return AlertEvent.seller_change(
                seller_name=str(observation.get("seller") or ""), is_preferred=True, **common
            )
        if condition_type == AlertConditionType.PREFERRED_MARKETPLACE_AVAILABLE:
            return AlertEvent.availability_change(
                previous_availability=str(observation.get("previous_marketplace") or "unknown"),
                current_availability=str(observation.get("marketplace") or "unknown"),
                **common,
            )
        if condition_type in (
            AlertConditionType.DEALSCORE_IMPROVED,
            AlertConditionType.DEALSCORE_THRESHOLD,
        ):
            return AlertEvent.dealscore_change(
                dealscore=observation.get("dealscore"),
                previous_dealscore=observation.get("previous_dealscore"),
                **common,
            )
        if condition_type == AlertConditionType.STALE_DATA:
            return AlertEvent.freshness_warning(
                age_hours=observation.get("age_hours"), restored=False, **common
            )
        if condition_type == AlertConditionType.FRESHNESS_RESTORED:
            return AlertEvent.freshness_warning(
                age_hours=observation.get("age_hours"), restored=True, **common
            )
        # Exhaustive over AlertConditionType; unreachable in practice.
        return AlertEvent.price_drop(
            previous_price=previous_price or 0.0,
            current_price=price or 0.0,
            currency=currency,
            **common,
        )

    def _create_legacy_alert(
        self,
        condition_type: AlertConditionType,
        *,
        rule: AlertRule,
        item: WatchlistItem,
        observation: Mapping[str, Any],
        evaluation: AlertEvaluation,
        now: datetime,
    ) -> Alert | None:
        """Create a Sprint-10-compatible ``Alert`` record, when possible."""
        if self._alerts is None:
            return None
        alert_type = _CONDITION_TO_ALERT_TYPE[condition_type]
        alert = Alert(
            alert_id=self._id_factory(),
            watchlist_id=item.watchlist_id,
            item_id=item.item_id,
            canonical_product_id=item.canonical_product_id,
            alert_type=alert_type,
            message=evaluation.reason,
            previous_value=observation.get("previous_price")
            or observation.get("previous_dealscore"),
            current_value=observation.get("price") or observation.get("dealscore"),
            currency=observation.get("currency"),
            dealscore=observation.get("dealscore"),
            status=AlertStatus.PENDING,
            created_at=now,
            notified_at=None,
        )
        saved = self._alerts.save_alert(alert)
        if self._notifications is not None:
            receipt = self._notifications.notify(saved)
            saved = self._alerts.save_alert(
                replace(saved, status=AlertStatus.NOTIFIED, notified_at=receipt.created_at)
            )
        return saved

    def _fan_out(
        self,
        event: AlertEvent,
        *,
        watchlist: Watchlist | None,
        item: WatchlistItem,
        alert: Alert | None,
    ) -> None:
        if self._notification_center is None:
            return
        create_from_event = getattr(self._notification_center, "create_from_alert_event", None)
        if not callable(create_from_event):
            return
        try:
            create_from_event(event, watchlist=watchlist, item=item)
        except TypeError:
            # Collaborator doesn't accept the optional keyword args.
            create_from_event(event)
        except Exception:  # noqa: BLE001 - notification fan-out must never break evaluation.
            return
