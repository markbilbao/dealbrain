"""Alert Rules & Alert Events domain entities — Sprint 19.

Rule-driven, scheduler-neutral alerting layered on top of the Sprint 10
Watchlist/Alert primitives (``app.domain.entities.watchlist``). An
``AlertRule`` describes *when* a user wants to be alerted; evaluating it
against fresh observations produces an ``AlertEvaluation`` and, when
triggered, an ``AlertEvent``. Notification fan-out lives in
``app.domain.entities.notifications``.

Identifiers and timestamps are injected by callers — core types never
generate random UUIDs or wall-clock times.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.domain.entities.watchlist import NotificationChannel


class AlertConditionType(StrEnum):
    """Kinds of conditions an alert rule can evaluate.

    Mirrors and extends ``app.domain.entities.watchlist.AlertType`` so rule
    conditions and raised alerts share a common vocabulary.
    """

    PRICE_DROP = "price_drop"
    PERCENTAGE_PRICE_DECREASE = "percentage_price_decrease"
    ABSOLUTE_PRICE_DECREASE = "absolute_price_decrease"
    PRICE_INCREASE = "price_increase"
    TARGET_PRICE_REACHED = "target_price_reached"
    HISTORICAL_LOW = "historical_low"
    DEALSCORE_IMPROVED = "dealscore_improved"
    DEALSCORE_THRESHOLD = "dealscore_threshold"
    RESTOCKED = "restocked"
    UNAVAILABLE = "unavailable"
    LOW_INVENTORY = "low_inventory"
    BETTER_OFFER = "better_offer"
    PREFERRED_SELLER_AVAILABLE = "preferred_seller_available"
    PREFERRED_MARKETPLACE_AVAILABLE = "preferred_marketplace_available"
    STALE_DATA = "stale_data"
    FRESHNESS_RESTORED = "freshness_restored"


class AlertSeverity(StrEnum):
    """Relative importance of an alert, used for UI grouping and quiet hours."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertRepeatPolicy(StrEnum):
    """Whether a rule may fire repeatedly or only once."""

    ONE_TIME = "one_time"
    RECURRING = "recurring"


class AlertRuleStatus(StrEnum):
    """Administrative on/off switch for an alert rule, distinct from ``enabled``.

    ``enabled`` on :class:`AlertRule` remains the primary Sprint-compatible
    flag; ``status`` offers a richer, explicit lifecycle value for UIs/audits.
    """

    ENABLED = "enabled"
    DISABLED = "disabled"


class AlertEventType(StrEnum):
    """Typed event kinds emitted when an alert rule fires."""

    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    RESTOCK = "restock"
    OUT_OF_STOCK = "out_of_stock"
    AVAILABILITY_CHANGE = "availability_change"
    SELLER_CHANGE = "seller_change"
    BETTER_OFFER = "better_offer"
    FRESHNESS_WARNING = "freshness_warning"

    # Sprint 19 application-service additions (AlertEvaluationService) — kept
    # here rather than overloading an existing member so every
    # AlertConditionType has a lossless AlertEventType counterpart.
    LOW_INVENTORY = "low_inventory"
    DEALSCORE_CHANGE = "dealscore_change"


@dataclass(frozen=True, slots=True)
class AlertCondition:
    """A single evaluable condition within an alert rule."""

    condition_type: AlertConditionType
    threshold_value: float | None = None
    threshold_percent: float | None = None
    comparison: str | None = None  # e.g. "lte", "gte", "eq" — free-form, engine-defined.

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_type": self.condition_type.value,
            "threshold_value": self.threshold_value,
            "threshold_percent": self.threshold_percent,
            "comparison": self.comparison,
        }


@dataclass(frozen=True, slots=True)
class AlertThreshold:
    """A resolved numeric threshold used when evaluating a condition."""

    value: float | None = None
    percent: float | None = None
    currency: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "percent": self.percent,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class AlertRule:
    """A user-defined rule describing when to raise an alert.

    Scoped to a watchlist and/or a single item; a rule with neither scope
    applies account-wide (engine-defined).
    """

    rule_id: str
    user_id: str
    name: str
    conditions: tuple[AlertCondition, ...]
    created_at: datetime
    watchlist_id: str | None = None
    item_id: str | None = None
    enabled: bool = True
    status: AlertRuleStatus = AlertRuleStatus.ENABLED
    cooldown_seconds: int = 0
    last_triggered_at: datetime | None = None
    repeat_policy: AlertRepeatPolicy = AlertRepeatPolicy.RECURRING
    severity: AlertSeverity = AlertSeverity.INFO
    timezone: str = "UTC"
    channel_preferences: tuple[NotificationChannel, ...] = ()
    updated_at: datetime | None = None
    one_time_fired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "user_id": self.user_id,
            "name": self.name,
            "conditions": [c.to_dict() for c in self.conditions],
            "watchlist_id": self.watchlist_id,
            "item_id": self.item_id,
            "enabled": self.enabled,
            "status": self.status.value,
            "cooldown_seconds": self.cooldown_seconds,
            "last_triggered_at": (
                self.last_triggered_at.isoformat() if self.last_triggered_at else None
            ),
            "repeat_policy": self.repeat_policy.value,
            "severity": self.severity.value,
            "timezone": self.timezone,
            "channel_preferences": [c.value for c in self.channel_preferences],
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.updated_at or self.created_at).isoformat(),
            "one_time_fired": self.one_time_fired,
        }


@dataclass(frozen=True, slots=True)
class AlertEvaluation:
    """Outcome of evaluating a single rule against current observations."""

    evaluation_id: str
    triggered: bool
    reason: str
    evaluated_at: datetime
    rule_id: str | None = None
    watchlist_id: str | None = None
    item_id: str | None = None
    observation_fingerprint: str | None = None
    partial_failure: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "rule_id": self.rule_id,
            "watchlist_id": self.watchlist_id,
            "item_id": self.item_id,
            "triggered": self.triggered,
            "reason": self.reason,
            "observation_fingerprint": self.observation_fingerprint,
            "evaluated_at": self.evaluated_at.isoformat(),
            "partial_failure": self.partial_failure,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """A discrete, deduplicable occurrence produced by a triggered alert rule."""

    event_id: str
    user_id: str
    event_type: AlertEventType
    severity: AlertSeverity
    created_at: datetime
    dedupe_key: str
    rule_id: str | None = None
    alert_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "rule_id": self.rule_id,
            "alert_id": self.alert_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "payload": dict(self.payload),
            "created_at": self.created_at.isoformat(),
            "dedupe_key": self.dedupe_key,
        }

    # ------------------------------------------------------------------
    # Typed event factories. Each corresponds to a named event concept from
    # the Sprint 19 spec while sharing the single AlertEvent representation
    # (event_type discriminates the shape of ``payload``).
    # ------------------------------------------------------------------

    @classmethod
    def price_drop(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        previous_price: float,
        current_price: float,
        currency: str,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """PriceDropEvent — price decreased below the previous observation."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.PRICE_DROP,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={
                "previous_price": previous_price,
                "current_price": current_price,
                "currency": currency,
            },
        )

    @classmethod
    def price_increase(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        previous_price: float,
        current_price: float,
        currency: str,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """PriceIncreaseEvent — price rose above the previous observation."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.PRICE_INCREASE,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={
                "previous_price": previous_price,
                "current_price": current_price,
                "currency": currency,
            },
        )

    @classmethod
    def restock(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        quantity: int | None = None,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """RestockEvent — a previously unavailable item became available."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.RESTOCK,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={"quantity": quantity},
        )

    @classmethod
    def out_of_stock(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> AlertEvent:
        """OutOfStockEvent — a tracked item became unavailable."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.OUT_OF_STOCK,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={},
        )

    @classmethod
    def availability_change(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        previous_availability: str,
        current_availability: str,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """AvailabilityChangeEvent — availability status transitioned."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.AVAILABILITY_CHANGE,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={
                "previous_availability": previous_availability,
                "current_availability": current_availability,
            },
        )

    @classmethod
    def seller_change(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        seller_name: str,
        is_preferred: bool = False,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """SellerChangeEvent — the winning/available seller changed."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.SELLER_CHANGE,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={"seller_name": seller_name, "is_preferred": is_preferred},
        )

    @classmethod
    def better_offer(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        offer_id: str,
        total_price: float,
        currency: str,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """BetterOfferEvent — a cheaper or higher-DealScore offer surfaced."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.BETTER_OFFER,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={
                "offer_id": offer_id,
                "total_price": total_price,
                "currency": currency,
            },
        )

    @classmethod
    def freshness_warning(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        age_hours: float | None = None,
        restored: bool = False,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> AlertEvent:
        """FreshnessWarningEvent — data staleness crossed a threshold (or recovered)."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.FRESHNESS_WARNING,
            severity=AlertSeverity.INFO if restored else severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={"age_hours": age_hours, "restored": restored},
        )

    @classmethod
    def low_inventory(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        inventory: float | None = None,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> AlertEvent:
        """LowInventoryEvent — tracked inventory fell at or below a threshold."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.LOW_INVENTORY,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={"inventory": inventory},
        )

    @classmethod
    def dealscore_change(
        cls,
        *,
        event_id: str,
        user_id: str,
        dedupe_key: str,
        created_at: datetime,
        dealscore: float | None,
        previous_dealscore: float | None,
        rule_id: str | None = None,
        alert_id: str | None = None,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> AlertEvent:
        """DealScoreChangeEvent — DealScore improved or crossed a threshold."""
        return cls(
            event_id=event_id,
            user_id=user_id,
            event_type=AlertEventType.DEALSCORE_CHANGE,
            severity=severity,
            created_at=created_at,
            dedupe_key=dedupe_key,
            rule_id=rule_id,
            alert_id=alert_id,
            payload={"dealscore": dealscore, "previous_dealscore": previous_dealscore},
        )


class AlertJobTrigger(ABC):
    """Scheduler-neutral job trigger for alert rule evaluation.

    Mirrors ``app.domain.interfaces.marketplace_data_repository.SyncJobTrigger``:
    infrastructure (cron, task queue, manual admin action) may invoke this
    later. Implementations must not start background threads or sleep;
    evaluation only happens when ``trigger_evaluate`` is called.
    """

    @abstractmethod
    def trigger_evaluate(
        self,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        rule_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[AlertEvaluation, ...]:
        """Evaluate due rule(s) and return the evaluation outcomes."""
