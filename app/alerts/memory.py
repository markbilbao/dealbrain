"""In-memory Alert Rule / Alert Event repository — Sprint 19."""

from __future__ import annotations

from app.domain.entities.alerts import AlertEvaluation, AlertEvent, AlertRule
from app.domain.interfaces.alert_rule_repository import AlertEventRepository, AlertRuleRepository


class InMemoryAlertRuleRepository(AlertRuleRepository, AlertEventRepository):
    """Process-local store for alert rules, evaluations, and dedupe-able events."""

    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._rule_order: list[str] = []
        self._evaluations: dict[str, AlertEvaluation] = {}
        self._evaluation_order: list[str] = []
        self._events: dict[str, AlertEvent] = {}
        self._event_order: list[str] = []
        self._events_by_dedupe_key: dict[str, str] = {}

    # ------------------------------------------------------------------- rules
    def save_rule(self, rule: AlertRule) -> AlertRule:
        if rule.rule_id not in self._rules:
            self._rule_order.append(rule.rule_id)
        self._rules[rule.rule_id] = rule
        return rule

    def get_rule(self, rule_id: str) -> AlertRule | None:
        return self._rules.get(rule_id)

    def list_rules(
        self,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[AlertRule]:
        items = [self._rules[rid] for rid in self._rule_order if rid in self._rules]
        if user_id is not None:
            items = [r for r in items if r.user_id == user_id]
        if watchlist_id is not None:
            items = [r for r in items if r.watchlist_id == watchlist_id]
        if item_id is not None:
            items = [r for r in items if r.item_id == item_id]
        if enabled is not None:
            items = [r for r in items if r.enabled is enabled]
        return items

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        self._rule_order = [rid for rid in self._rule_order if rid != rule_id]
        return True

    # ------------------------------------------------------------- evaluations
    def save_evaluation(self, evaluation: AlertEvaluation) -> AlertEvaluation:
        if evaluation.evaluation_id not in self._evaluations:
            self._evaluation_order.append(evaluation.evaluation_id)
        self._evaluations[evaluation.evaluation_id] = evaluation
        return evaluation

    def list_evaluations(
        self,
        *,
        rule_id: str | None = None,
        limit: int = 50,
    ) -> list[AlertEvaluation]:
        ordered = [
            self._evaluations[eid]
            for eid in reversed(self._evaluation_order)
            if eid in self._evaluations
        ]
        if rule_id is not None:
            ordered = [e for e in ordered if e.rule_id == rule_id]
        return ordered[: max(0, limit)]

    # ------------------------------------------------------------------- events
    def save_event(self, event: AlertEvent) -> AlertEvent:
        if event.event_id not in self._events:
            self._event_order.append(event.event_id)
        self._events[event.event_id] = event
        self._events_by_dedupe_key[event.dedupe_key] = event.event_id
        return event

    def get_event(self, event_id: str) -> AlertEvent | None:
        return self._events.get(event_id)

    def find_by_dedupe_key(self, dedupe_key: str) -> AlertEvent | None:
        event_id = self._events_by_dedupe_key.get(dedupe_key)
        return self._events.get(event_id) if event_id else None

    def list_events(
        self,
        *,
        user_id: str | None = None,
        rule_id: str | None = None,
        limit: int = 50,
    ) -> list[AlertEvent]:
        ordered = [self._events[eid] for eid in reversed(self._event_order) if eid in self._events]
        if user_id is not None:
            ordered = [e for e in ordered if e.user_id == user_id]
        if rule_id is not None:
            ordered = [e for e in ordered if e.rule_id == rule_id]
        return ordered[: max(0, limit)]

    # -------------------------------------------------------------------- misc
    def clear(self) -> None:
        """Reset all stored rules, evaluations, and events (tests)."""
        self._rules.clear()
        self._rule_order.clear()
        self._evaluations.clear()
        self._evaluation_order.clear()
        self._events.clear()
        self._event_order.clear()
        self._events_by_dedupe_key.clear()
