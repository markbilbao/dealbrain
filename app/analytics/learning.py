"""Read-only beta-learning aggregates.

This service is not the launch readiness dashboard, the merchant analytics
service, or the shopper watchlist dashboard. It counts consented first-party
analytics events and, separately, feedback reports. It does not write either store.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.analytics.funnel import research_partial_reason
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.schema import ProductAnalyticsEvent
from app.feedback.repository import FirstPartyFeedbackRepository
from app.feedback.schema import FEEDBACK_CATEGORIES, FeedbackReport

MAX_DASHBOARD_SCAN_ROWS = 5_000
MAX_FEEDBACK_REVIEW_LIMIT = 100
DEFAULT_FEEDBACK_REVIEW_LIMIT = 50
ANALYSIS_WINDOWS: frozenset[str] = frozenset({"1d", "7d", "30d"})
_WINDOW_DAYS = {"1d": 1, "7d": 7, "30d": 30}

_FUNNEL_EVENTS = (
    "decision_started",
    "decision_completed",
    "results_viewed",
    "compare_opened",
    "why_opened",
    "outbound_merchant_click",
)
_ASK_EVENTS = (
    "ask_question_submitted",
    "ask_evidence_answered",
    "insufficient_evidence",
)
_RESEARCH_EVENTS = (
    "research_proposed",
    "research_confirmed",
    "research_declined",
    "research_started",
    "research_completed",
    "research_failed",
)
_FEEDBACK_COUNT_KEYS = {
    "recommendation_helpful": "helpful_count",
    "recommendation_not_helpful": "not_helpful_count",
    "incorrect_price": "incorrect_price_reports",
    "incorrect_product_fact": "incorrect_product_fact_reports",
    "outdated_offer": "outdated_offer_reports",
    "misleading_recommendation_evidence": "misleading_evidence_reports",
    "source_issue": "source_issue_reports",
    "bug": "bug_reports",
    "other_feedback": "other_feedback_reports",
}


class ProductLearningDashboardService:
    """Aggregate consented analytics subjects and independent feedback reports."""

    def __init__(
        self,
        analytics: FirstPartyProductAnalyticsRepository,
        feedback: FirstPartyFeedbackRepository,
        *,
        max_scan_rows: int = MAX_DASHBOARD_SCAN_ROWS,
    ) -> None:
        self._analytics = analytics
        self._feedback = feedback
        self._max_scan_rows = max_scan_rows

    def summary(
        self,
        window: str,
        *,
        environment: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if window not in ANALYSIS_WINDOWS:
            raise ValueError("window must be 1d, 7d, or 30d")
        clock = _aware(now)
        selected = window_bounds(window, clock)
        events, event_scan = self._load_events()
        reports, report_scan = self._load_reports()
        truncated = event_scan["truncated"] or report_scan["truncated"]
        in_window = [event for event in events if _in_window(event.occurred_at, selected)]
        feedback_in_window = [
            report for report in reports if _in_window(report.created_at, selected)
        ]
        coverage = _coverage(
            in_window,
            events,
            clock,
            partial=event_scan["truncated"],
        )
        funnel = _funnel(in_window, partial=event_scan["truncated"])
        ask = _ask(in_window, partial=event_scan["truncated"])
        research = _research(in_window, partial=event_scan["truncated"])
        retention = _retention(in_window, partial=event_scan["truncated"])
        identity = _identity_lifecycle(in_window, partial=event_scan["truncated"])
        feedback_metrics = _feedback(feedback_in_window, partial=report_scan["truncated"])
        return {
            "generated_at": clock.isoformat(),
            "environment": environment,
            "window": window,
            "window_start": selected[0].isoformat(),
            "window_end": selected[1].isoformat(),
            "analytics_scope": "consented_analytics_subjects",
            "metrics": {
                "coverage": coverage,
                "core_funnel": funnel,
                "ask": ask,
                "research": research,
                "return_retention": retention,
                "identity_lifecycle": identity,
            },
            "feedback": feedback_metrics,
            "coverage": {
                "truncated": truncated,
                "analytics_truncated": event_scan["truncated"],
                "feedback_truncated": report_scan["truncated"],
                "scanned_rows": event_scan["scanned_rows"],
                "total_rows": event_scan["total_rows"],
                "feedback_scanned_rows": report_scan["scanned_rows"],
                "feedback_total_rows": report_scan["total_rows"],
                "scan_bound": self._max_scan_rows,
            },
            "limitations": _limitations(),
        }

    def feedback_review(
        self,
        *,
        limit: int = DEFAULT_FEEDBACK_REVIEW_LIMIT,
        category: str | None = None,
        window: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if limit < 1 or limit > MAX_FEEDBACK_REVIEW_LIMIT:
            raise ValueError("limit must be from 1 to 100")
        if category is not None and category not in FEEDBACK_CATEGORIES:
            raise ValueError("category is not an allowed feedback category")
        if window is not None and window not in ANALYSIS_WINDOWS:
            raise ValueError("window must be 1d, 7d, or 30d")
        clock = _aware(now)
        bounds = window_bounds(window, clock) if window is not None else None
        reports, scan = self._load_reports()
        selected = reports
        if category is not None:
            selected = [report for report in selected if report.category == category]
        if bounds is not None:
            selected = [report for report in selected if _in_window(report.created_at, bounds)]
        selected.sort(key=lambda report: report.created_at, reverse=True)
        visible = selected[:limit]
        return {
            "generated_at": clock.isoformat(),
            "limit": limit,
            "category": category,
            "window": window,
            "truncated": scan["truncated"],
            "scanned_rows": scan["scanned_rows"],
            "total_rows": scan["total_rows"],
            "returned": len(visible),
            "reports": [_review_row(report) for report in visible],
            "limitations": [
                "Internal staging operator review queue.",
                "Not production IAM.",
                "The submitted message is included because review needs it.",
                "Owner digest, analytics subject, account id, and session id are excluded.",
                "Decision id is excluded.",
            ],
        }

    def _load_events(self) -> tuple[list[ProductAnalyticsEvent], dict[str, int | bool]]:
        total = self._analytics.count()
        rows = self._analytics.list_recent(self._max_scan_rows)
        return rows, {
            "truncated": total > self._max_scan_rows,
            "scanned_rows": len(rows),
            "total_rows": total,
        }

    def _load_reports(self) -> tuple[list[FeedbackReport], dict[str, int | bool]]:
        total = self._feedback.count()
        rows = self._feedback.list_recent(self._max_scan_rows)
        return rows, {
            "truncated": total > self._max_scan_rows,
            "scanned_rows": len(rows),
            "total_rows": total,
        }


def window_bounds(window: str, now: datetime) -> tuple[datetime, datetime]:
    """UTC calendar windows.

    ``1d`` is the current UTC calendar day: ``[today 00:00Z, tomorrow 00:00Z)``.
    ``7d`` is that day plus the previous 6 UTC days.
    ``30d`` is that day plus the previous 29 UTC days.
    Callers cannot request an unbounded range.
    """

    if window not in _WINDOW_DAYS:
        raise ValueError("window must be 1d, 7d, or 30d")
    clock = _aware(now)
    end = datetime(clock.year, clock.month, clock.day, tzinfo=UTC) + timedelta(days=1)
    start = end - timedelta(days=_WINDOW_DAYS[window])
    return start, end


def _coverage(
    window_events: list[ProductAnalyticsEvent],
    scanned_events: list[ProductAnalyticsEvent],
    now: datetime,
    *,
    partial: bool,
) -> dict[str, Any]:
    subjects = {event.anonymous_subject_hash for event in window_events}
    return {
        "recorded_analytics_events": len(window_events),
        "distinct_consented_analytics_subjects": len(subjects),
        "consented_subjects_today": _active_subjects(scanned_events, "1d", now),
        "consented_subjects_7d": _active_subjects(scanned_events, "7d", now),
        "consented_subjects_30d": _active_subjects(scanned_events, "30d", now),
        "partial": partial,
        "label": "consented_analytics_subjects",
    }


def _active_subjects(events: list[ProductAnalyticsEvent], window: str, now: datetime) -> int:
    bounds = window_bounds(window, now)
    return len(
        {event.anonymous_subject_hash for event in events if _in_window(event.occurred_at, bounds)}
    )


def _funnel(events: list[ProductAnalyticsEvent], *, partial: bool) -> dict[str, Any]:
    counts = _counts(events)
    started = [event for event in events if event.event_name == "decision_started"]
    completed = [event for event in events if event.event_name == "decision_completed"]
    started_hashes = {event.decision_hash for event in started if event.decision_hash}
    completed_hashes = {event.decision_hash for event in completed if event.decision_hash}
    matched = started_hashes & completed_hashes
    views = counts["results_viewed"]
    clicks = counts["outbound_merchant_click"]
    return {
        "decision_started": counts["decision_started"],
        "decision_completed": counts["decision_completed"],
        "results_viewed": views,
        "compare_opened": counts["compare_opened"],
        "why_opened": counts["why_opened"],
        "outbound_merchant_click": clicks,
        "decision_started_distinct": len(started_hashes),
        "decision_completed_distinct_matching_start": len(matched),
        "decision_completed_without_start": len(completed_hashes - started_hashes),
        "decision_completion_rate": _rate(
            len(matched),
            len(started_hashes),
            definition="distinct_authorized_decision_hash",
            partial=partial,
        ),
        "results_to_outbound_ctr": _rate(
            clicks,
            views,
            definition="results_to_outbound_ctr_event_ratio",
            partial=partial,
        ),
        "partial": partial,
    }


def _ask(events: list[ProductAnalyticsEvent], *, partial: bool) -> dict[str, Any]:
    counts = _counts(events)
    submitted = counts["ask_question_submitted"]
    insufficient = counts["insufficient_evidence"]
    return {
        "ask_question_submitted": submitted,
        "ask_evidence_answered": counts["ask_evidence_answered"],
        "insufficient_evidence": insufficient,
        "insufficient_evidence_rate": _rate(
            insufficient,
            submitted,
            definition="insufficient_evidence_event_ratio",
            partial=partial,
        ),
        "partial": partial,
    }


def _research(events: list[ProductAnalyticsEvent], *, partial: bool) -> dict[str, Any]:
    counts = _counts(events)
    payload: dict[str, Any] = {name: counts[name] for name in _RESEARCH_EVENTS}
    payload["research_partial"] = {
        "count": None,
        "available": False,
        "reason": research_partial_reason(),
    }
    payload["partial"] = partial
    payload["live_research_operational"] = False
    return payload


_IDENTITY_LIFECYCLE_EVENTS = (
    "registration_completed",
    "registration_verified",
    "login_success",
    "login_failure",
    "account_deleted",
    "authentication_transition",
)


def _identity_lifecycle(events: list[ProductAnalyticsEvent], *, partial: bool) -> dict[str, Any]:
    """Count consented identity events already stored in the scanned window.

    A truncated scan keeps these counts and sets ``partial``. The counts are
    event totals only. They are not account DAU or MAU.
    """

    totals = {name: 0 for name in _IDENTITY_LIFECYCLE_EVENTS}
    for event in events:
        if event.event_name in totals:
            totals[event.event_name] += 1
    return {**totals, "partial": partial}


def _retention(events: list[ProductAnalyticsEvent], *, partial: bool) -> dict[str, Any]:
    if partial:
        return {
            "returning_consented_analytics_subjects": None,
            "repeat_decision_consented_subjects": None,
            "available": False,
            "reason": "truncated_scan",
            "label": "analytics_subject_metrics",
        }
    dates_by_subject: dict[str, set[str]] = defaultdict(set)
    decisions_by_subject: dict[str, set[str]] = defaultdict(set)
    for event in events:
        dates_by_subject[event.anonymous_subject_hash].add(
            event.occurred_at.astimezone(UTC).date().isoformat()
        )
        if event.event_name == "decision_completed" and event.decision_hash:
            decisions_by_subject[event.anonymous_subject_hash].add(event.decision_hash)
    returning = sum(1 for dates in dates_by_subject.values() if len(dates) >= 2)
    repeating = sum(1 for hashes in decisions_by_subject.values() if len(hashes) >= 2)
    return {
        "returning_consented_analytics_subjects": returning,
        "repeat_decision_consented_subjects": repeating,
        "available": True,
        "reason": None,
        "label": "analytics_subject_metrics",
    }


def _feedback(reports: list[FeedbackReport], *, partial: bool) -> dict[str, Any]:
    counts = {key: 0 for key in _FEEDBACK_COUNT_KEYS.values()}
    for report in reports:
        key = _FEEDBACK_COUNT_KEYS.get(report.category)
        if key is not None:
            counts[key] += 1
    helpful = counts["helpful_count"]
    not_helpful = counts["not_helpful_count"]
    return {
        "scope": "feedback_reports_including_consent_off_shoppers",
        "partial": partial,
        "total_feedback_reports": len(reports),
        **counts,
        "helpful_share": _rate(
            helpful,
            helpful + not_helpful,
            definition="helpful_share_of_feedback_ratings",
            partial=partial,
        ),
    }


def _review_row(report: FeedbackReport) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "category": report.category,
        "created_at": report.created_at.isoformat(),
        "product_id": report.product_id,
        "context_version": report.context_version,
        "source_surface": report.source_surface,
        "status": report.status,
        "message": report.message,
    }


def _counts(events: list[ProductAnalyticsEvent]) -> dict[str, int]:
    names = (*_FUNNEL_EVENTS, *_ASK_EVENTS, *_RESEARCH_EVENTS)
    totals = {name: 0 for name in names}
    for event in events:
        if event.event_name in totals:
            totals[event.event_name] += 1
    return totals


def _rate(
    numerator: int,
    denominator: int,
    *,
    definition: str,
    partial: bool,
) -> dict[str, Any]:
    if denominator == 0:
        return {
            "value": None,
            "numerator": numerator,
            "denominator": denominator,
            "definition": definition,
            "available": False,
            "partial": partial,
        }
    return {
        "value": numerator / denominator,
        "numerator": numerator,
        "denominator": denominator,
        "definition": definition,
        "available": True,
        "partial": partial,
    }


def _in_window(moment: datetime, bounds: tuple[datetime, datetime]) -> bool:
    if moment.utcoffset() is None:
        return False
    instant = moment.astimezone(UTC)
    return bounds[0] <= instant < bounds[1]


def _aware(now: datetime | None) -> datetime:
    clock = now or datetime.now(UTC)
    if clock.utcoffset() is None:
        raise ValueError("dashboard clock must be timezone-aware")
    return clock.astimezone(UTC)


def _limitations() -> list[str]:
    return [
        "Consented first-party analytics only.",
        "Non-consenting sessions are absent.",
        "Feedback counts are separate and may include non-consenting shoppers.",
        "Not purchase or conversion analytics.",
        "No affiliate conversion data.",
        "No third-party analytics provider.",
        "Research metrics may be zero while live research is not operational.",
        "research_partial is unavailable because no authoritative partial transition exists.",
        "Returning and repeat-decision figures are analytics-subject metrics.",
        "identity_lifecycle counts consented product events only and is not account DAU or MAU.",
        "account_deleted counts the existing account-deletion operation and does not "
        "claim legal erasure of audit logs, backups, analytics rows, or feedback rows.",
        "Account export and account deletion do not include these stores.",
        "No automatic retention purge is implemented.",
        "Internal staging operator surface. Not production IAM.",
    ]
