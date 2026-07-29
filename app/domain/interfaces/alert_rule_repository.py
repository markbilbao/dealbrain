"""Alert Rule & Alert Event persistence ports — Sprint 19."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.alerts import AlertEvaluation, AlertEvent, AlertRule


class AlertRuleRepository(ABC):
    """Persistence for user-defined alert rules."""

    @abstractmethod
    def save_rule(self, rule: AlertRule) -> AlertRule:
        """Create or replace an alert rule."""

    @abstractmethod
    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Return a rule by id, or None."""

    @abstractmethod
    def list_rules(
        self,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[AlertRule]:
        """Return rules in insertion order, optionally filtered."""

    @abstractmethod
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule. Returns False if missing."""

    @abstractmethod
    def save_evaluation(self, evaluation: AlertEvaluation) -> AlertEvaluation:
        """Persist an evaluation outcome for audit/debugging purposes."""

    @abstractmethod
    def list_evaluations(
        self,
        *,
        rule_id: str | None = None,
        limit: int = 50,
    ) -> list[AlertEvaluation]:
        """Return evaluation outcomes newest-first, optionally filtered by rule."""


class AlertEventRepository(ABC):
    """Persistence for deduplicable alert events raised by triggered rules."""

    @abstractmethod
    def save_event(self, event: AlertEvent) -> AlertEvent:
        """Create or replace an alert event."""

    @abstractmethod
    def get_event(self, event_id: str) -> AlertEvent | None:
        """Return an event by id, or None."""

    @abstractmethod
    def find_by_dedupe_key(self, dedupe_key: str) -> AlertEvent | None:
        """Return an existing event with the same dedupe key, if any.

        Callers use this to avoid re-raising the same occurrence (e.g. the
        same restock or price drop) across repeated evaluation passes.
        """

    @abstractmethod
    def list_events(
        self,
        *,
        user_id: str | None = None,
        rule_id: str | None = None,
        limit: int = 50,
    ) -> list[AlertEvent]:
        """Return events newest-first, optionally filtered."""
