"""Map Alert Rules & Alert Events domain objects (Sprint 19) to HTTP schemas."""

from __future__ import annotations

from typing import Any

from app.core.public_brand import present_consumer_text
from app.domain.entities.alerts import AlertCondition, AlertEvaluation, AlertEvent, AlertRule
from app.schemas.alerts_v2 import (
    AlertConditionPayload,
    AlertEvaluationPayload,
    AlertEventPayload,
    AlertRuleEvaluateResponse,
    AlertRulePayload,
)
from app.services.alert_evaluation_service import AlertEvaluationSummary


def _present_payload(payload: dict[str, Any]) -> dict[str, Any]:
    presented: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            presented[key] = present_consumer_text(value)
        else:
            presented[key] = value
    return presented


def to_condition_payload(condition: AlertCondition) -> AlertConditionPayload:
    return AlertConditionPayload(
        condition_type=condition.condition_type.value,
        threshold_value=condition.threshold_value,
        threshold_percent=condition.threshold_percent,
        comparison=condition.comparison,
    )


def to_rule_payload(rule: AlertRule) -> AlertRulePayload:
    return AlertRulePayload(
        rule_id=rule.rule_id,
        user_id=rule.user_id,
        name=present_consumer_text(rule.name),
        conditions=[to_condition_payload(c) for c in rule.conditions],
        watchlist_id=rule.watchlist_id,
        item_id=rule.item_id,
        enabled=rule.enabled,
        status=rule.status.value,
        cooldown_seconds=rule.cooldown_seconds,
        last_triggered_at=(rule.last_triggered_at.isoformat() if rule.last_triggered_at else None),
        repeat_policy=rule.repeat_policy.value,
        severity=rule.severity.value,
        timezone=rule.timezone,
        channel_preferences=[c.value for c in rule.channel_preferences],
        created_at=rule.created_at.isoformat(),
        updated_at=(rule.updated_at or rule.created_at).isoformat(),
        one_time_fired=rule.one_time_fired,
    )


def to_evaluation_payload(evaluation: AlertEvaluation) -> AlertEvaluationPayload:
    return AlertEvaluationPayload(
        evaluation_id=evaluation.evaluation_id,
        rule_id=evaluation.rule_id,
        watchlist_id=evaluation.watchlist_id,
        item_id=evaluation.item_id,
        triggered=evaluation.triggered,
        reason=present_consumer_text(evaluation.reason),
        observation_fingerprint=evaluation.observation_fingerprint,
        evaluated_at=evaluation.evaluated_at.isoformat(),
        partial_failure=evaluation.partial_failure,
        error=present_consumer_text(evaluation.error) if evaluation.error else evaluation.error,
    )


def to_event_payload(event: AlertEvent) -> AlertEventPayload:
    return AlertEventPayload(
        event_id=event.event_id,
        user_id=event.user_id,
        rule_id=event.rule_id,
        alert_id=event.alert_id,
        event_type=event.event_type.value,
        severity=event.severity.value,
        payload=_present_payload(dict(event.payload)),
        created_at=event.created_at.isoformat(),
        dedupe_key=event.dedupe_key,
    )


def to_evaluate_response(summary: AlertEvaluationSummary) -> AlertRuleEvaluateResponse:
    return AlertRuleEvaluateResponse(
        evaluated_at=summary.evaluated_at.isoformat(),
        rules_evaluated=summary.rules_evaluated,
        triggered_count=summary.triggered_count,
        events_created=[to_event_payload(e) for e in summary.events_created],
        failures=[present_consumer_text(item) for item in summary.failures],
    )
