"""Sprint 39.2 funnel instrumentation and beta-learning dashboard."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.analytics.ask_events import emit_ask_product_events
from app.analytics.decision_events import record_decision_completed, record_decision_started
from app.analytics.funnel import emit_refinement_observations, emit_research_observations
from app.analytics.identity import anonymous_subject_hash, decision_hash
from app.analytics.learning import (
    MAX_DASHBOARD_SCAN_ROWS,
    ProductLearningDashboardService,
)
from app.analytics.preference import apply_tracking_choice
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.schema import (
    EVENT_SCHEMA,
    SERVER_EVENT_NAMES,
    ProductAnalyticsEvent,
    assert_stored_event_shape,
    semantic_digest,
)
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.core.dependencies import (
    get_product_analytics_service,
    get_product_learning_dashboard_service,
)
from app.feedback.repository import FirstPartyFeedbackRepository
from app.feedback.schema import FeedbackReport, feedback_content_digest
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.session import reset_sync_engine
from app.main import create_app
from app.research.routing import _CONFIGURED_BUCKET
from app.research.sprint38_live_execution import SHOPIFY_LIVE_CALL_PERMITTED
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request
from starlette.responses import Response

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 1, 15, tzinfo=UTC)
SUBJECT_A = "11" * 16
SUBJECT_B = "22" * 16
SUBJECT_C = "33" * 16
DECISION_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DECISION_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
DECISION_C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
DECISION_D = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
ADMIN = {"Authorization": "Bearer demo-token-internal-admin"}
OWNER_DIGEST = "f" * 64
FEEDBACK_MESSAGE = "The listed price does not match the shelf."


def _preference(allowed: bool):
    from app.analytics.preference import CONSENT_SCHEMA, TrackingPreference

    return TrackingPreference(
        choice="analytics_allowed" if allowed else "essential_only",
        analytics_allowed=allowed,
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version="1",
        selected_at="2026-10-01T00:00:00+00:00" if allowed else None,
        explicit=True,
    )


def _context(
    *,
    allowed: bool = True,
    subject: str = SUBJECT_A,
    decision: str | None = None,
    version: int | None = 1,
) -> AnalyticsServerContext:
    return AnalyticsServerContext(
        preference=_preference(allowed),
        subject_id=subject if allowed else None,
        identity_kind="guest",
        decision_hash=decision_hash(decision) if decision else None,
        context_version=version,
    )


@pytest.fixture()
def stores(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint392.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    analytics_repo = FirstPartyProductAnalyticsRepository(session_factory=factory)
    feedback_repo = FirstPartyFeedbackRepository(session_factory=factory)
    analytics = ProductAnalyticsService(analytics_repo)
    learning = ProductLearningDashboardService(analytics_repo, feedback_repo)
    yield {
        "analytics_repo": analytics_repo,
        "feedback_repo": feedback_repo,
        "analytics": analytics,
        "learning": learning,
    }
    engine.dispose()
    reset_sync_engine()


@pytest.fixture()
async def api(stores: dict):
    app = create_app()
    app.dependency_overrides[get_product_analytics_service] = lambda: stores["analytics"]
    app.dependency_overrides[get_product_learning_dashboard_service] = lambda: stores["learning"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, stores, app
    app.dependency_overrides.clear()


def _store_event(
    repo: FirstPartyProductAnalyticsRepository,
    *,
    name: str,
    subject: str,
    when: datetime,
    decision: str | None = None,
    outcome: str = "viewed",
    surface: str = "results",
    action: str = "view",
) -> ProductAnalyticsEvent:
    event_id = str(uuid4())
    event = ProductAnalyticsEvent(
        event_schema=EVENT_SCHEMA,
        event_name=name,
        event_id=event_id,
        occurred_at=when,
        anonymous_subject_hash=anonymous_subject_hash(subject),
        identity_kind="guest",
        decision_hash=decision_hash(decision) if decision else None,
        surface=surface,
        action_type=action,
        turn_number=None,
        evidence_count=None,
        latency_band=None,
        freshness_band=None,
        error_code=None,
        context_version=1,
        selected_market=None,
        outcome=outcome,
        consent_state="analytics_allowed",
        dedup_key=event_id,
        content_digest="",
    )
    stored = replace(event, content_digest=semantic_digest(event))
    assert_stored_event_shape(stored)
    repo.persist(stored)
    return stored


def _store_report(
    repo: FirstPartyFeedbackRepository,
    *,
    category: str,
    message: str,
    when: datetime,
    decision_id: str | None = None,
    product_id: str | None = None,
) -> FeedbackReport:
    report = FeedbackReport(
        report_id=str(uuid4()),
        category=category,
        created_at=when,
        owner_digest=OWNER_DIGEST,
        decision_id=decision_id,
        product_id=product_id,
        context_version=2 if decision_id else None,
        message=message,
        status="received",
        source_surface="results",
        client_submission_id=None,
        content_digest="",
    )
    stored = replace(report, content_digest=feedback_content_digest(report))
    repo.insert(stored)
    return stored


def _seed_learning(stores: dict) -> None:
    repo = stores["analytics_repo"]
    today = NOW
    in_7d = NOW - timedelta(days=3)
    in_30d = NOW - timedelta(days=10)
    outside = NOW - timedelta(days=40)
    rows = [
        ("decision_started", SUBJECT_A, today, DECISION_A, "started", "start"),
        ("decision_completed", SUBJECT_A, today, DECISION_A, "completed", "complete"),
        ("decision_started", SUBJECT_A, today, DECISION_B, "started", "start"),
        ("results_viewed", SUBJECT_A, today, DECISION_A, "viewed", "view"),
        ("results_viewed", SUBJECT_A, today, DECISION_A, "viewed", "view"),
        ("outbound_merchant_click", SUBJECT_A, today, DECISION_A, "clicked", "click"),
        ("compare_opened", SUBJECT_A, today, DECISION_A, "opened", "open"),
        ("why_opened", SUBJECT_A, today, DECISION_A, "opened", "open"),
        ("ask_question_submitted", SUBJECT_A, today, DECISION_A, "submitted", "submit"),
        ("ask_evidence_answered", SUBJECT_A, today, DECISION_A, "answered", "submit"),
        ("insufficient_evidence", SUBJECT_A, today, DECISION_A, "insufficient_evidence", "submit"),
        ("research_proposed", SUBJECT_A, today, DECISION_A, "proposed", "submit"),
        ("results_viewed", SUBJECT_B, today, None, "viewed", "view"),
        ("results_viewed", SUBJECT_A, in_7d, DECISION_A, "viewed", "view"),
        ("decision_started", SUBJECT_A, in_7d, DECISION_C, "started", "start"),
        ("decision_completed", SUBJECT_A, in_7d, DECISION_C, "completed", "complete"),
        ("decision_started", SUBJECT_A, in_7d, DECISION_D, "started", "start"),
        ("decision_completed", SUBJECT_A, in_7d, DECISION_D, "completed", "complete"),
        ("results_viewed", SUBJECT_C, in_30d, None, "viewed", "view"),
        ("results_viewed", SUBJECT_A, outside, DECISION_A, "viewed", "view"),
    ]
    for name, subject, when, decision, outcome, action in rows:
        surface = "results"
        if name == "compare_opened":
            surface = "compare"
        elif name == "why_opened":
            surface = "why"
        elif (
            name.startswith("ask") or name.startswith("research") or name == "insufficient_evidence"
        ):
            surface = "ask"
        _store_event(
            repo,
            name=name,
            subject=subject,
            when=when,
            decision=decision,
            outcome=outcome,
            surface=surface,
            action=action,
        )
    feedback = stores["feedback_repo"]
    _store_report(feedback, category="recommendation_helpful", message="", when=today)
    _store_report(feedback, category="recommendation_not_helpful", message="", when=today)
    _store_report(
        feedback,
        category="incorrect_price",
        message=FEEDBACK_MESSAGE,
        when=today,
        decision_id=DECISION_A,
        product_id="sku-1",
    )
    _store_report(feedback, category="bug", message="The compare table did not load.", when=in_30d)
    _store_report(feedback, category="recommendation_helpful", message="", when=outside)


def _request_with_consent() -> Request:
    response = Response()
    apply_tracking_choice(response, "analytics_allowed", existing_subject=SUBJECT_A)
    pairs = []
    for header in response.headers.getlist("set-cookie"):
        pairs.append(header.split(";", 1)[0])
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"cookie", "; ".join(pairs).encode())],
        "client": ("127.0.0.1", 5000),
        "server": ("test", 80),
    }
    return Request(scope)


def test_decision_events_only_after_authoritative_success(stores: dict) -> None:
    analytics: ProductAnalyticsService = stores["analytics"]
    repo = stores["analytics_repo"]
    context = _context(decision=DECISION_A, version=1)
    assert record_decision_started(analytics, context, generation_started=False) is None
    assert record_decision_completed(analytics, context, canonical_persisted=False) is None
    assert repo.count() == 0
    assert (
        record_decision_started(
            analytics, _context(decision=None, version=1), generation_started=True
        )
        is None
    )
    started = record_decision_started(analytics, context, generation_started=True)
    assert started is not None and started.status == "recorded"
    replay = record_decision_started(analytics, context, generation_started=True)
    assert replay is not None and replay.status == "duplicate"
    assert repo.count() == 1
    completed = record_decision_completed(analytics, context, canonical_persisted=True)
    assert completed is not None and completed.status == "recorded"
    blob = json.dumps([asdict(event) for event in repo.list_events()], default=str)
    assert "best wireless headphones" not in blob
    assert DECISION_A not in blob
    names = {event.event_name for event in repo.list_events()}
    assert names == {"decision_started", "decision_completed"}


def test_decision_events_are_not_client_or_page_events() -> None:
    client_js = (ROOT / "app/static/consumer/js/product_analytics.js").read_text(encoding="utf-8")
    consumer_js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    shopping = (ROOT / "app/services/shopping_assistant_service.py").read_text(encoding="utf-8")
    assert "decision_started" not in client_js
    assert "decision_completed" not in client_js
    assert "decision_started" not in consumer_js
    assert "record_decision_started" not in shopping
    assert "record_decision_completed" not in shopping
    for name in (
        "decision_started",
        "decision_completed",
        "research_proposed",
        "research_started",
        "ask_evidence_answered",
        "insufficient_evidence",
    ):
        assert name in SERVER_EVENT_NAMES


def test_ask_evidence_answer_has_no_answer_text(stores: dict) -> None:
    analytics: ProductAnalyticsService = stores["analytics"]
    emit_ask_product_events(
        _request_with_consent(),
        Response(),
        surface="results",
        answer_status="answered",
        evidence_count=3,
        decision_id=None,
        owner=None,
        analytics=analytics,
        snapshots=None,
        processing={"action": "answer_from_evidence", "answer_status": "answered"},
    )
    events = stores["analytics_repo"].list_events()
    names = {event.event_name for event in events}
    assert names == {"ask_question_submitted", "ask_evidence_answered"}
    answered = next(event for event in events if event.event_name == "ask_evidence_answered")
    assert answered.evidence_count == 3
    blob = json.dumps([asdict(event) for event in events], default=str)
    assert "Does this include shipping?" not in blob
    assert "Yes, shipping is included." not in blob


def test_ask_open_close_exact_semantics_and_consent(stores: dict) -> None:
    analytics: ProductAnalyticsService = stores["analytics"]
    allowed = _context()
    opened = analytics.record_client_event(
        {
            "event_name": "ask_opened",
            "surface": "ask",
            "action_type": "open",
            "outcome": "opened",
        },
        allowed,
    )
    closed = analytics.record_client_event(
        {
            "event_name": "ask_closed",
            "surface": "ask",
            "action_type": "close",
            "outcome": "closed",
        },
        allowed,
    )
    assert opened.status == "recorded"
    assert closed.status == "recorded"
    extra = analytics.record_client_event(
        {
            "event_name": "ask_opened",
            "surface": "ask",
            "action_type": "open",
            "outcome": "opened",
            "evidence_count": 1,
        },
        allowed,
    )
    wrong = analytics.record_client_event(
        {
            "event_name": "ask_closed",
            "surface": "results",
            "action_type": "close",
            "outcome": "closed",
        },
        allowed,
    )
    assert extra.reason == "contradictory_event"
    assert wrong.reason == "contradictory_event"
    before = stores["analytics_repo"].count()
    suppressed = analytics.record_client_event(
        {
            "event_name": "ask_opened",
            "surface": "ask",
            "action_type": "open",
            "outcome": "opened",
        },
        _context(allowed=False),
    )
    assert suppressed.status == "suppressed_no_consent"
    assert stores["analytics_repo"].count() == before


def test_research_observations_follow_existing_transitions(stores: dict) -> None:
    analytics: ProductAnalyticsService = stores["analytics"]
    context = _context(decision=DECISION_A, version=2)
    proposal_id = str(uuid4())
    processing = {
        "research_lifecycle": "propose",
        "proposal_status": "pending_confirmation",
        "proposal_id": proposal_id,
        "answer_status": "pending_confirmation",
    }
    emit_research_observations(context, processing, analytics)
    emit_research_observations(context, processing, analytics)
    proposed = [
        event
        for event in stores["analytics_repo"].list_events()
        if event.event_name == "research_proposed"
    ]
    assert len(proposed) == 1
    execution_id = str(uuid4())
    emit_research_observations(
        context,
        {
            "research_lifecycle": "confirm",
            "authorization_created": True,
            "research_authorization_id": str(uuid4()),
            "answer_status": "research_confirmation_received_but_execution_unavailable",
            "confirmed_research": {
                "execution_id": execution_id,
                "attempted": False,
                "research_executed": False,
                "live_research_completed": False,
                "block_reason": "live_research_not_operational",
            },
        },
        analytics,
    )
    names = {event.event_name for event in stores["analytics_repo"].list_events()}
    assert "research_confirmed" in names
    assert "research_started" not in names
    assert "research_failed" not in names
    assert "research_partial" not in names
    emit_research_observations(
        context,
        {
            "confirmed_research": {
                "execution_id": execution_id,
                "attempted": True,
                "research_executed": True,
                "live_research_completed": False,
                "block_reason": "timed_out",
            }
        },
        analytics,
    )
    failed = {
        event.event_name: event
        for event in stores["analytics_repo"].list_events()
        if event.event_name in {"research_started", "research_failed", "research_completed"}
    }
    assert failed["research_started"].outcome == "started"
    assert failed["research_failed"].error_code == "timed_out"
    assert "research_completed" not in failed
    emit_research_observations(
        context,
        {
            "research_lifecycle": "cancel",
            "answer_status": "cancelled",
            "proposal_id": proposal_id,
            "proposal_status": "cancelled",
        },
        analytics,
    )
    assert any(
        event.event_name == "research_declined" for event in stores["analytics_repo"].list_events()
    )
    forged = analytics.record_client_event(
        {
            "event_name": "research_completed",
            "surface": "ask",
            "action_type": "complete",
            "outcome": "completed",
        },
        context,
    )
    assert forged.reason == "server_owned_event"


def test_refinement_applied_uses_server_flag(stores: dict) -> None:
    analytics: ProductAnalyticsService = stores["analytics"]
    context = _context(decision=DECISION_A, version=1)
    emit_refinement_observations(
        context,
        {
            "action": "refine_session_recommendation",
            "answer_status": "insufficient_evidence",
            "recommendation_applied": False,
            "surface": "compare",
        },
        analytics,
    )
    names = {event.event_name for event in stores["analytics_repo"].list_events()}
    assert names == {"recommendation_refinement_attempted"}
    emit_refinement_observations(
        context,
        {
            "action": "refine_session_recommendation",
            "answer_status": "recommendation_changed",
            "recommendation_applied": True,
            "session_refinement_version": 2,
            "surface": "results",
        },
        analytics,
    )
    applied = [
        event
        for event in stores["analytics_repo"].list_events()
        if event.event_name == "recommendation_refinement_applied"
    ]
    assert len(applied) == 1
    assert applied[0].outcome == "applied"


def test_learning_windows_funnel_and_feedback(stores: dict) -> None:
    _seed_learning(stores)
    learning: ProductLearningDashboardService = stores["learning"]
    day = learning.summary("1d", environment="test", now=NOW)
    week = learning.summary("7d", environment="test", now=NOW)
    month = learning.summary("30d", environment="test", now=NOW)
    day_funnel = day["metrics"]["core_funnel"]
    week_funnel = week["metrics"]["core_funnel"]
    month_funnel = month["metrics"]["core_funnel"]
    assert day_funnel["decision_started"] == 2
    assert day_funnel["decision_completed"] == 1
    assert day_funnel["results_viewed"] == 3
    assert day_funnel["compare_opened"] == 1
    assert day_funnel["why_opened"] == 1
    assert day_funnel["outbound_merchant_click"] == 1
    assert day_funnel["results_to_outbound_ctr"]["value"] == 1 / 3
    assert day_funnel["results_to_outbound_ctr"]["numerator"] == 1
    assert day_funnel["results_to_outbound_ctr"]["denominator"] == 3
    assert (
        day_funnel["decision_completion_rate"]["definition"] == "distinct_authorized_decision_hash"
    )
    assert day_funnel["decision_completion_rate"]["value"] == 0.5
    assert week_funnel["results_viewed"] == 4
    assert week_funnel["decision_completed_distinct_matching_start"] == 3
    assert week_funnel["decision_started_distinct"] == 4
    assert month_funnel["results_viewed"] == 5
    assert month["metrics"]["coverage"]["recorded_analytics_events"] == 19
    assert day["metrics"]["coverage"]["distinct_consented_analytics_subjects"] == 2
    assert day["metrics"]["coverage"]["consented_subjects_today"] == 2
    assert day["metrics"]["coverage"]["consented_subjects_7d"] == 2
    assert day["metrics"]["coverage"]["consented_subjects_30d"] == 3
    assert day["metrics"]["coverage"]["label"] == "consented_analytics_subjects"
    ask = day["metrics"]["ask"]
    assert ask["ask_question_submitted"] == 1
    assert ask["ask_evidence_answered"] == 1
    assert ask["insufficient_evidence"] == 1
    assert ask["insufficient_evidence_rate"]["value"] == 1
    assert day["metrics"]["research"]["research_proposed"] == 1
    assert day["metrics"]["research"]["research_partial"]["available"] is False
    assert day["metrics"]["research"]["live_research_operational"] is False
    assert day["metrics"]["return_retention"]["returning_consented_analytics_subjects"] == 0
    assert week["metrics"]["return_retention"]["returning_consented_analytics_subjects"] == 1
    assert week["metrics"]["return_retention"]["repeat_decision_consented_subjects"] == 1
    assert day["metrics"]["return_retention"]["label"] == "analytics_subject_metrics"
    feedback = day["feedback"]
    assert feedback["helpful_count"] == 1
    assert feedback["not_helpful_count"] == 1
    assert feedback["helpful_share"]["value"] == 0.5
    assert feedback["helpful_share"]["definition"] == "helpful_share_of_feedback_ratings"
    assert feedback["incorrect_price_reports"] == 1
    assert feedback["bug_reports"] == 0
    assert month["feedback"]["bug_reports"] == 1
    assert month["feedback"]["helpful_count"] == 1
    assert feedback["scope"] == "feedback_reports_including_consent_off_shoppers"
    serialized = json.dumps(day)
    assert anonymous_subject_hash(SUBJECT_A) not in serialized
    assert OWNER_DIGEST not in serialized
    assert DECISION_A not in serialized
    assert FEEDBACK_MESSAGE not in serialized
    assert "all users" not in serialized
    assert "total shoppers" not in serialized


def test_rates_are_unavailable_when_denominator_is_zero(stores: dict) -> None:
    learning: ProductLearningDashboardService = stores["learning"]
    summary = learning.summary("7d", environment="test", now=NOW)
    funnel = summary["metrics"]["core_funnel"]
    assert funnel["decision_completion_rate"]["available"] is False
    assert funnel["decision_completion_rate"]["value"] is None
    assert funnel["results_to_outbound_ctr"]["available"] is False
    assert funnel["results_to_outbound_ctr"]["value"] is None
    assert summary["feedback"]["helpful_share"]["available"] is False
    assert summary["feedback"]["helpful_share"]["value"] is None


def test_ctr_above_one_stays_visible(stores: dict) -> None:
    repo = stores["analytics_repo"]
    _store_event(repo, name="results_viewed", subject=SUBJECT_A, when=NOW, outcome="viewed")
    _store_event(
        repo,
        name="outbound_merchant_click",
        subject=SUBJECT_A,
        when=NOW,
        outcome="clicked",
        action="click",
    )
    _store_event(
        repo,
        name="outbound_merchant_click",
        subject=SUBJECT_A,
        when=NOW,
        outcome="clicked",
        action="click",
    )
    summary = stores["learning"].summary("1d", environment="test", now=NOW)
    ratio = summary["metrics"]["core_funnel"]["results_to_outbound_ctr"]
    assert ratio["value"] == 2
    assert ratio["numerator"] == 2
    assert ratio["denominator"] == 1


def test_truncation_is_disclosed(stores: dict) -> None:
    repo = stores["analytics_repo"]
    for _ in range(3):
        _store_event(repo, name="results_viewed", subject=SUBJECT_A, when=NOW)
    learning = ProductLearningDashboardService(
        repo,
        stores["feedback_repo"],
        max_scan_rows=2,
    )
    summary = learning.summary("30d", environment="test", now=NOW)
    assert summary["coverage"]["truncated"] is True
    assert summary["coverage"]["scanned_rows"] == 2
    assert summary["coverage"]["total_rows"] == 3
    assert summary["coverage"]["scan_bound"] == 2
    assert summary["metrics"]["core_funnel"]["partial"] is True
    retention = summary["metrics"]["return_retention"]
    assert retention["available"] is False
    assert retention["returning_consented_analytics_subjects"] is None
    assert MAX_DASHBOARD_SCAN_ROWS == 5_000


def test_feedback_review_is_bounded_and_omits_identity(stores: dict) -> None:
    _seed_learning(stores)
    review = stores["learning"].feedback_review(limit=50, now=NOW)
    assert review["returned"] == 5
    blob = json.dumps(review)
    assert FEEDBACK_MESSAGE in blob
    assert OWNER_DIGEST not in blob
    assert DECISION_A not in blob
    assert "owner_digest" not in blob
    assert "decision_id" not in blob
    priced = stores["learning"].feedback_review(limit=10, category="incorrect_price", now=NOW)
    assert priced["returned"] == 1
    assert priced["reports"][0]["product_id"] == "sku-1"
    assert priced["reports"][0]["context_version"] == 2
    with pytest.raises(ValueError):
        stores["learning"].feedback_review(limit=101, now=NOW)


async def test_internal_dashboard_gate_and_public_absence(api) -> None:
    client, stores, _app = api
    missing = await client.get("/api/v1/launch/product-learning")
    wrong = await client.get(
        "/api/v1/launch/product-learning",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert missing.status_code == 401
    assert wrong.status_code == 401
    allowed = await client.get("/api/v1/launch/product-learning?window=7d", headers=ADMIN)
    assert allowed.status_code == 200
    assert allowed.json()["analytics_scope"] == "consented_analytics_subjects"
    feedback_missing = await client.get("/api/v1/launch/product-feedback")
    assert feedback_missing.status_code == 401
    feedback = await client.get("/api/v1/launch/product-feedback?limit=1000", headers=ADMIN)
    assert feedback.status_code == 400
    public = await client.get("/api/v1/product-learning")
    consumer = await client.get("/api/v1/shopping-assistant/product-learning")
    assert public.status_code == 404
    assert consumer.status_code == 404
    assert stores["analytics_repo"].count() == 0


async def test_shopping_paths_do_not_emit_decision_events_and_survive_analytics_failure(
    api,
) -> None:
    client, stores, app = api
    await client.post("/api/v1/privacy/tracking-preference", json={"choice": "analytics_allowed"})
    demo = await client.get("/api/v1/shopping-assistant/demo")
    assert demo.status_code == 200
    assert stores["analytics_repo"].count() == 0
    malformed = await client.post("/api/v1/shopping-assistant/query", json={"query": ""})
    assert malformed.status_code == 422
    assert stores["analytics_repo"].count() == 0
    asked = await client.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "headphones under 200"},
    )
    assert asked.status_code == 200
    names = {event.event_name for event in stores["analytics_repo"].list_events()}
    assert "decision_started" not in names
    assert "decision_completed" not in names
    assert "ask_question_submitted" in names
    blob = json.dumps(
        [asdict(event) for event in stores["analytics_repo"].list_events()],
        default=str,
    )
    assert "headphones under 200" not in blob

    class Boom(ProductAnalyticsService):
        def record_server_event(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise RuntimeError("analytics store unavailable")

    app.dependency_overrides[get_product_analytics_service] = lambda: Boom(stores["analytics_repo"])
    survived = await client.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "compare the top two"},
    )
    assert survived.status_code == 200


def test_external_boundaries_remain() -> None:
    register = (ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md").read_text(encoding="utf-8")
    for dependency in ("EXT-15", "EXT-22", "EXT-29"):
        line = next(item for item in register.splitlines() if item.startswith(f"| {dependency} |"))
        assert "not_started" in line
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert _CONFIGURED_BUCKET == 0
    analytics_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "app" / "analytics").glob("*.py")
    )
    for token in ("googletagmanager", "google-analytics", "posthog", "mixpanel", "facebook.com/tr"):
        assert token not in analytics_source
    assert "affiliate_click" not in analytics_source
