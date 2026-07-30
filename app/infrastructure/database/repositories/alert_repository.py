"""SQLAlchemy Alert Rule / Event repository — Sprint 23."""

from __future__ import annotations

from app.domain.entities.alerts import AlertEvaluation, AlertEvent, AlertRule
from app.domain.interfaces.alert_rule_repository import AlertEventRepository, AlertRuleRepository
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import ALERT_EVALUATIONS, ALERT_EVENTS, ALERT_RULES, ALERT_STORES


class SqlAlchemyAlertRuleRepository(AlertRuleRepository, AlertEventRepository, SessionBound):
    # ------------------------------------------------------------------- rules
    def save_rule(self, rule: AlertRule) -> AlertRule:
        with self._ops() as ops:
            return ops.upsert(
                ALERT_RULES,
                rule.rule_id,
                rule,
                owner_id=rule.user_id,
            )

    def get_rule(self, rule_id: str) -> AlertRule | None:
        with self._ops() as ops:
            return ops.get(ALERT_RULES, rule_id, AlertRule)

    def list_rules(
        self,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[AlertRule]:
        def _matches(rule: AlertRule) -> bool:
            if user_id is not None and rule.user_id != user_id:
                return False
            if watchlist_id is not None and rule.watchlist_id != watchlist_id:
                return False
            if item_id is not None and rule.item_id != item_id:
                return False
            if enabled is not None and rule.enabled is not enabled:
                return False
            return True

        with self._ops() as ops:
            return ops.list(ALERT_RULES, AlertRule, predicate=_matches)

    def delete_rule(self, rule_id: str) -> bool:
        with self._ops() as ops:
            return ops.delete(ALERT_RULES, rule_id)

    # ------------------------------------------------------------- evaluations
    def save_evaluation(self, evaluation: AlertEvaluation) -> AlertEvaluation:
        with self._ops() as ops:
            return ops.upsert(
                ALERT_EVALUATIONS,
                evaluation.evaluation_id,
                evaluation,
                owner_id=evaluation.rule_id,
            )

    def list_evaluations(
        self,
        *,
        rule_id: str | None = None,
        limit: int = 50,
    ) -> list[AlertEvaluation]:
        predicate = (lambda e: e.rule_id == rule_id) if rule_id is not None else None
        with self._ops() as ops:
            return ops.list(
                ALERT_EVALUATIONS,
                AlertEvaluation,
                reverse=True,
                limit=limit,
                predicate=predicate,
            )

    # ------------------------------------------------------------------- events
    def save_event(self, event: AlertEvent) -> AlertEvent:
        with self._ops() as ops:
            return ops.upsert(
                ALERT_EVENTS,
                event.event_id,
                event,
                secondary_key=event.dedupe_key,
                owner_id=event.user_id,
            )

    def get_event(self, event_id: str) -> AlertEvent | None:
        with self._ops() as ops:
            return ops.get(ALERT_EVENTS, event_id, AlertEvent)

    def find_by_dedupe_key(self, dedupe_key: str) -> AlertEvent | None:
        with self._ops() as ops:
            return ops.get_by_secondary(ALERT_EVENTS, dedupe_key, AlertEvent)

    def list_events(
        self,
        *,
        user_id: str | None = None,
        rule_id: str | None = None,
        limit: int = 50,
    ) -> list[AlertEvent]:
        def _matches(event: AlertEvent) -> bool:
            if user_id is not None and event.user_id != user_id:
                return False
            if rule_id is not None and event.rule_id != rule_id:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                ALERT_EVENTS,
                AlertEvent,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    # -------------------------------------------------------------------- misc
    def clear(self) -> None:
        with self._ops() as ops:
            ops.clear_stores(ALERT_STORES)
