"""Durable feedback reports on ``operational_entities``.

Namespace: ``product.feedback_reports``. Creation records are immutable.
A repeated client submission id with the same contents returns the original
report. Different contents for that id fail closed.
"""

from __future__ import annotations

from app.feedback.schema import FeedbackConflict, FeedbackReport
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import PRODUCT_FEEDBACK_REPORTS


class FirstPartyFeedbackRepository(SessionBound):
    """Durable report store. Not an analytics event store and not an email sender."""

    def insert(self, report: FeedbackReport) -> tuple[FeedbackReport, bool]:
        """Return the stored report and whether this call created it."""

        try:
            with self._ops() as ops:
                ops.insert_immutable(
                    PRODUCT_FEEDBACK_REPORTS,
                    report.report_id,
                    report,
                    secondary_key=report.client_submission_id,
                    owner_id=report.owner_digest,
                )
        except PersistenceConflictError:
            existing = self._existing(report)
            if existing is not None and existing.content_digest == report.content_digest:
                return existing, False
            raise FeedbackConflict(report.client_submission_id or report.report_id) from None
        return report, True

    def get(self, report_id: str) -> FeedbackReport | None:
        with self._ops() as ops:
            return ops.get(PRODUCT_FEEDBACK_REPORTS, report_id, FeedbackReport)

    def list_reports(self) -> list[FeedbackReport]:
        with self._ops() as ops:
            return ops.list(PRODUCT_FEEDBACK_REPORTS, FeedbackReport)

    def list_recent(self, limit: int) -> list[FeedbackReport]:
        """Newest inserted reports only. ``limit`` is a hard cap."""

        bounded = max(0, limit)
        with self._ops() as ops:
            return ops.list(
                PRODUCT_FEEDBACK_REPORTS,
                FeedbackReport,
                limit=bounded,
                reverse=True,
            )

    def count(self) -> int:
        with self._ops() as ops:
            return ops.count(PRODUCT_FEEDBACK_REPORTS)

    def _existing(self, report: FeedbackReport) -> FeedbackReport | None:
        with self._ops() as ops:
            if report.client_submission_id:
                found = ops.get_by_secondary(
                    PRODUCT_FEEDBACK_REPORTS,
                    report.client_submission_id,
                    FeedbackReport,
                )
                if found is not None:
                    return found
            return ops.get(PRODUCT_FEEDBACK_REPORTS, report.report_id, FeedbackReport)
