"""Alert Rule application service — Sprint 19.

CRUD for user-defined :class:`~app.domain.entities.alerts.AlertRule` records
with ownership checks and condition/threshold validation. Persists
exclusively through :class:`AlertRuleRepository`; never touches Sprint 10
``Alert``/``WatchlistService`` internals directly (only reads a watchlist's
``owner_id`` for ownership enforcement when a rule is scoped to a watchlist).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.alerts import (
    AlertCondition,
    AlertConditionType,
    AlertRepeatPolicy,
    AlertRule,
    AlertRuleStatus,
    AlertSeverity,
)
from app.domain.entities.watchlist import NotificationChannel
from app.domain.exceptions import (
    AlertRuleNotFoundError,
    AlertRuleValidationError,
    WatchlistNotFoundError,
    WatchlistOwnershipError,
)
from app.domain.interfaces.alert_rule_repository import AlertRuleRepository
from app.domain.interfaces.watchlist_repository import WatchlistRepository

# Sentinel distinguishing "field not supplied" from "field explicitly cleared
# to None" for optional-scope update parameters (watchlist_id / item_id).
_UNSET = object()

# Condition types that require an explicit numeric threshold to be meaningful.
_REQUIRES_THRESHOLD_VALUE = frozenset(
    {
        AlertConditionType.ABSOLUTE_PRICE_DECREASE,
        AlertConditionType.DEALSCORE_THRESHOLD,
    }
)
_REQUIRES_THRESHOLD_PERCENT = frozenset({AlertConditionType.PERCENTAGE_PRICE_DECREASE})


class AlertRuleService:
    """CRUD and validation for user-defined alert rules."""

    def __init__(
        self,
        repository: AlertRuleRepository,
        *,
        watchlist_repository: WatchlistRepository | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._watchlists = watchlist_repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    # ---------------------------------------------------------------------- CRUD
    def create_rule(
        self,
        *,
        user_id: str,
        name: str,
        conditions: Sequence[AlertCondition | dict[str, Any]],
        watchlist_id: str | None = None,
        item_id: str | None = None,
        enabled: bool = True,
        status: AlertRuleStatus = AlertRuleStatus.ENABLED,
        cooldown_seconds: int = 0,
        repeat_policy: AlertRepeatPolicy = AlertRepeatPolicy.RECURRING,
        severity: AlertSeverity = AlertSeverity.INFO,
        timezone: str = "UTC",
        channel_preferences: Sequence[NotificationChannel] = (),
        rule_id: str | None = None,
    ) -> AlertRule:
        cleaned_user = self._require_user_id(user_id)
        cleaned_name = self._require_name(name)
        built_conditions = self._normalize_conditions(conditions)
        cleaned_timezone = self._require_timezone(timezone)
        if watchlist_id is not None:
            self._ensure_watchlist_owned(watchlist_id, cleaned_user)
        if cooldown_seconds < 0:
            raise AlertRuleValidationError("cooldown_seconds must be non-negative.")

        stamp = self._clock()
        rule = AlertRule(
            rule_id=rule_id or self._id_factory(),
            user_id=cleaned_user,
            name=cleaned_name,
            conditions=built_conditions,
            created_at=stamp,
            watchlist_id=watchlist_id,
            item_id=item_id,
            enabled=enabled,
            status=status,
            cooldown_seconds=int(cooldown_seconds),
            repeat_policy=repeat_policy,
            severity=severity,
            timezone=cleaned_timezone,
            channel_preferences=tuple(channel_preferences),
            updated_at=stamp,
        )
        return self._repository.save_rule(rule)

    def get_rule(self, rule_id: str, *, user_id: str | None = None) -> AlertRule:
        rule = self._repository.get_rule(rule_id)
        if rule is None or (user_id is not None and rule.user_id != user_id):
            raise AlertRuleNotFoundError(rule_id)
        return rule

    def list_rules(
        self,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[AlertRule]:
        return self._repository.list_rules(
            user_id=user_id, watchlist_id=watchlist_id, item_id=item_id, enabled=enabled
        )

    def update_rule(
        self,
        rule_id: str,
        *,
        user_id: str | None = None,
        name: str | None = None,
        conditions: Sequence[AlertCondition | dict[str, Any]] | None = None,
        watchlist_id: object = _UNSET,
        item_id: object = _UNSET,
        enabled: bool | None = None,
        status: AlertRuleStatus | None = None,
        cooldown_seconds: int | None = None,
        repeat_policy: AlertRepeatPolicy | None = None,
        severity: AlertSeverity | None = None,
        timezone: str | None = None,
        channel_preferences: Sequence[NotificationChannel] | None = None,
    ) -> AlertRule:
        rule = self.get_rule(rule_id, user_id=user_id)
        updates: dict[str, Any] = {"updated_at": self._clock()}

        if name is not None:
            updates["name"] = self._require_name(name)
        if conditions is not None:
            updates["conditions"] = self._normalize_conditions(conditions)
        if watchlist_id is not _UNSET:
            if watchlist_id is not None:
                self._ensure_watchlist_owned(str(watchlist_id), rule.user_id)
            updates["watchlist_id"] = watchlist_id
        if item_id is not _UNSET:
            updates["item_id"] = item_id
        if enabled is not None:
            updates["enabled"] = enabled
        if status is not None:
            updates["status"] = status
        if cooldown_seconds is not None:
            if cooldown_seconds < 0:
                raise AlertRuleValidationError("cooldown_seconds must be non-negative.")
            updates["cooldown_seconds"] = int(cooldown_seconds)
        if repeat_policy is not None:
            updates["repeat_policy"] = repeat_policy
        if severity is not None:
            updates["severity"] = severity
        if timezone is not None:
            updates["timezone"] = self._require_timezone(timezone)
        if channel_preferences is not None:
            updates["channel_preferences"] = tuple(channel_preferences)

        updated = replace(rule, **updates)
        return self._repository.save_rule(updated)

    def delete_rule(self, rule_id: str, *, user_id: str | None = None) -> None:
        self.get_rule(rule_id, user_id=user_id)  # existence + ownership check
        self._repository.delete_rule(rule_id)

    def pause_rule(self, rule_id: str, *, user_id: str | None = None) -> AlertRule:
        return self.update_rule(
            rule_id, user_id=user_id, status=AlertRuleStatus.DISABLED, enabled=False
        )

    def resume_rule(self, rule_id: str, *, user_id: str | None = None) -> AlertRule:
        return self.update_rule(
            rule_id, user_id=user_id, status=AlertRuleStatus.ENABLED, enabled=True
        )

    def list_evaluations(self, *, rule_id: str | None = None, limit: int = 50) -> list[Any]:
        return self._repository.list_evaluations(rule_id=rule_id, limit=limit)

    # ---------------------------------------------------------------- validation
    def _require_user_id(self, user_id: str | None) -> str:
        cleaned = (user_id or "").strip()
        if not cleaned:
            raise AlertRuleValidationError("user_id is required to create an alert rule.")
        return cleaned

    def _require_name(self, name: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise AlertRuleValidationError("Alert rule name must not be blank.")
        return cleaned

    def _require_timezone(self, timezone: str) -> str:
        cleaned = timezone.strip()
        if not cleaned:
            raise AlertRuleValidationError("timezone must not be blank.")
        return cleaned

    def _normalize_conditions(
        self, conditions: Sequence[AlertCondition | dict[str, Any]]
    ) -> tuple[AlertCondition, ...]:
        if not conditions:
            raise AlertRuleValidationError("At least one condition is required.")
        built: list[AlertCondition] = []
        for raw in conditions:
            condition = raw if isinstance(raw, AlertCondition) else self._condition_from_dict(raw)
            self._validate_condition(condition)
            built.append(condition)
        return tuple(built)

    def _condition_from_dict(self, raw: dict[str, Any]) -> AlertCondition:
        raw_type = raw.get("condition_type")
        try:
            condition_type = AlertConditionType(raw_type)
        except ValueError as exc:
            raise AlertRuleValidationError(f"Invalid condition_type: {raw_type!r}") from exc
        return AlertCondition(
            condition_type=condition_type,
            threshold_value=raw.get("threshold_value"),
            threshold_percent=raw.get("threshold_percent"),
            comparison=raw.get("comparison"),
        )

    def _validate_condition(self, condition: AlertCondition) -> None:
        if (
            condition.condition_type in _REQUIRES_THRESHOLD_VALUE
            and condition.threshold_value is None
        ):
            raise AlertRuleValidationError(
                f"{condition.condition_type.value} requires threshold_value."
            )
        if (
            condition.condition_type in _REQUIRES_THRESHOLD_PERCENT
            and condition.threshold_percent is None
        ):
            raise AlertRuleValidationError(
                f"{condition.condition_type.value} requires threshold_percent."
            )
        if condition.threshold_value is not None and condition.threshold_value < 0:
            raise AlertRuleValidationError("threshold_value must be non-negative.")
        if condition.threshold_percent is not None and not (0 < condition.threshold_percent <= 100):
            raise AlertRuleValidationError("threshold_percent must be between 0 and 100.")
        if condition.comparison is not None and condition.comparison not in {"lte", "gte", "eq"}:
            raise AlertRuleValidationError(
                f"Unsupported comparison operator: {condition.comparison!r}"
            )

    def _ensure_watchlist_owned(self, watchlist_id: str, user_id: str) -> None:
        """Raise if ``watchlist_id`` exists and is owned by someone else."""
        if self._watchlists is None:
            return
        watchlist = self._watchlists.get_watchlist(watchlist_id)
        if watchlist is None:
            raise WatchlistNotFoundError(watchlist_id)
        if watchlist.owner_id is not None and watchlist.owner_id != user_id:
            raise WatchlistOwnershipError(watchlist_id, user_id)
