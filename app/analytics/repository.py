"""Durable first-party analytics events on ``operational_entities``.

Namespace: ``product.analytics_events``. No new SQL table. Rows are inserted
once. A repeated event id with the same contents is a duplicate. The same id
with different contents fails closed and does not overwrite the stored row.
"""

from __future__ import annotations

from app.analytics.schema import AnalyticsWriteResult, ProductAnalyticsEvent
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import PRODUCT_ANALYTICS_EVENTS


class FirstPartyProductAnalyticsRepository(SessionBound):
    """Consent-on sink. Not an in-memory authority and not merchant analytics."""

    def persist(self, event: ProductAnalyticsEvent) -> AnalyticsWriteResult:
        try:
            with self._ops() as ops:
                ops.insert_immutable(
                    PRODUCT_ANALYTICS_EVENTS,
                    event.event_id,
                    event,
                    owner_id=event.anonymous_subject_hash,
                )
        except PersistenceConflictError:
            existing = self.get(event.event_id)
            if existing is not None and existing.content_digest == event.content_digest:
                return AnalyticsWriteResult(status="duplicate", event_id=existing.event_id)
            return AnalyticsWriteResult(status="identity_conflict", event_id=event.event_id)
        return AnalyticsWriteResult(status="recorded", event_id=event.event_id)

    def get(self, event_id: str) -> ProductAnalyticsEvent | None:
        with self._ops() as ops:
            return ops.get(PRODUCT_ANALYTICS_EVENTS, event_id, ProductAnalyticsEvent)

    def list_events(self) -> list[ProductAnalyticsEvent]:
        with self._ops() as ops:
            return ops.list(PRODUCT_ANALYTICS_EVENTS, ProductAnalyticsEvent)

    def count(self) -> int:
        with self._ops() as ops:
            return ops.count(PRODUCT_ANALYTICS_EVENTS)
