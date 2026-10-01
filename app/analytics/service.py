"""Consent-gated product analytics writes.

Server code calls this service directly. It does not POST to the public
analytics route. The browser cannot supply identity, consent, market, or
decision-hash authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.analytics.identity import anonymous_subject_hash, is_analytics_subject_id
from app.analytics.preference import TrackingPreference
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.schema import (
    EVENT_SCHEMA,
    AnalyticsWriteResult,
    ProductAnalyticsEvent,
    assert_stored_event_shape,
    semantic_digest,
    validate_client_event_payload,
)
from app.analytics.sink import NullProductAnalyticsSink, ProductAnalyticsSink


@dataclass(frozen=True, slots=True)
class AnalyticsServerContext:
    """Identity and consent derived by the server for one request."""

    preference: TrackingPreference
    subject_id: str | None
    identity_kind: str
    decision_hash: str | None = None
    context_version: int | None = None
    selected_market: str | None = None


class ProductAnalyticsService:
    """Choose the null sink or the first-party repository from consent."""

    def __init__(
        self,
        repository: FirstPartyProductAnalyticsRepository | ProductAnalyticsSink | None = None,
        *,
        null_sink: NullProductAnalyticsSink | None = None,
    ) -> None:
        self._repository = repository or FirstPartyProductAnalyticsRepository()
        self._null = null_sink or NullProductAnalyticsSink()

    def record_client_event(
        self,
        payload: Any,
        context: AnalyticsServerContext,
    ) -> AnalyticsWriteResult:
        reason = validate_client_event_payload(payload)
        if reason is not None:
            return AnalyticsWriteResult(status="schema_rejected", reason=reason)
        assert isinstance(payload, dict)
        if not context.preference.analytics_allowed:
            return self._null.suppress()
        return self._record_fields(
            context,
            event_name=str(payload["event_name"]),
            event_id=payload.get("event_id"),
            surface=payload.get("surface"),
            action_type=payload.get("action_type"),
            turn_number=payload.get("turn_number"),
            evidence_count=payload.get("evidence_count"),
            latency_band=payload.get("latency_band"),
            freshness_band=payload.get("freshness_band"),
            error_code=payload.get("error_code"),
            outcome=payload.get("outcome"),
        )

    def record_server_event(
        self,
        context: AnalyticsServerContext,
        *,
        event_name: str,
        surface: str | None = None,
        action_type: str | None = None,
        turn_number: int | None = None,
        evidence_count: int | None = None,
        latency_band: str | None = None,
        freshness_band: str | None = None,
        error_code: str | None = None,
        outcome: str | None = None,
        event_id: str | None = None,
    ) -> AnalyticsWriteResult:
        """Emit one server-known event. There is no free-text parameter."""

        payload = {
            "event_name": event_name,
            "surface": surface,
            "action_type": action_type,
            "turn_number": turn_number,
            "evidence_count": evidence_count,
            "latency_band": latency_band,
            "freshness_band": freshness_band,
            "error_code": error_code,
            "outcome": outcome,
        }
        if event_id is not None:
            payload["event_id"] = event_id
        compact = {key: value for key, value in payload.items() if value is not None}
        return self.record_client_event(compact, context)

    def _record_fields(
        self,
        context: AnalyticsServerContext,
        *,
        event_name: str,
        event_id: str | None,
        surface: str | None,
        action_type: str | None,
        turn_number: int | None,
        evidence_count: int | None,
        latency_band: str | None,
        freshness_band: str | None,
        error_code: str | None,
        outcome: str | None,
    ) -> AnalyticsWriteResult:
        if not is_analytics_subject_id(context.subject_id):
            return self._null.suppress()
        chosen_id = event_id or str(uuid4())
        event = ProductAnalyticsEvent(
            event_schema=EVENT_SCHEMA,
            event_name=event_name,
            event_id=chosen_id,
            occurred_at=datetime.now(UTC),
            anonymous_subject_hash=anonymous_subject_hash(context.subject_id),
            identity_kind=context.identity_kind,
            decision_hash=context.decision_hash,
            surface=surface,
            action_type=action_type,
            turn_number=turn_number,
            evidence_count=evidence_count,
            latency_band=latency_band,
            freshness_band=freshness_band,
            error_code=error_code,
            context_version=context.context_version,
            selected_market=context.selected_market,
            outcome=outcome,
            consent_state=context.preference.choice,
            dedup_key=chosen_id,
            content_digest="",
        )
        digest = semantic_digest(event)
        event = ProductAnalyticsEvent(
            event_schema=event.event_schema,
            event_name=event.event_name,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            anonymous_subject_hash=event.anonymous_subject_hash,
            identity_kind=event.identity_kind,
            decision_hash=event.decision_hash,
            surface=event.surface,
            action_type=event.action_type,
            turn_number=event.turn_number,
            evidence_count=event.evidence_count,
            latency_band=event.latency_band,
            freshness_band=event.freshness_band,
            error_code=event.error_code,
            context_version=event.context_version,
            selected_market=event.selected_market,
            outcome=event.outcome,
            consent_state=event.consent_state,
            dedup_key=event.dedup_key,
            content_digest=digest,
        )
        assert_stored_event_shape(event)
        return self._repository.persist(event)
