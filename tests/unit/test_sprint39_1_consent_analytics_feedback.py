"""Sprint 39.1 consent-gated analytics and feedback boundaries."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.analytics.identity import anonymous_subject_hash, decision_hash
from app.analytics.preference import (
    ANALYTICS_SUBJECT_COOKIE,
    CONSENT_SCHEMA,
    PREFERENCE_COOKIE,
    TrackingPreference,
    apply_tracking_choice,
    read_tracking_preference,
)
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.schema import EVENT_NAMES, EVENT_SCHEMA, FORBIDDEN_ANALYTICS_FIELDS
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.consumer.pages import _offer_link
from app.core.dependencies import (
    get_bound_decision_resolver,
    get_feedback_report_service,
    get_product_analytics_service,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.feedback.decisions import BoundDecision
from app.feedback.repository import FirstPartyFeedbackRepository
from app.feedback.schema import MAX_REPORT_MESSAGE_LENGTH
from app.feedback.service import FeedbackReportService
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.session import reset_sync_engine
from app.main import create_app
from app.privacy.tracking import (
    analytics_provider,
    category_allowed,
    cmp_vendor,
    non_essential_tracking_allowed,
    tracking_mode,
)
from app.research.routing import _CONFIGURED_BUCKET
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request
from starlette.responses import Response

OWNED_DECISION = "11111111-1111-4111-8111-111111111111"
FOREIGN_DECISION = "22222222-2222-4222-8222-222222222222"
SUBJECT = "ab" * 16
ROOT = Path(__file__).resolve().parents[2]


def _preference(allowed: bool) -> TrackingPreference:
    return TrackingPreference(
        choice="analytics_allowed" if allowed else "essential_only",
        analytics_allowed=allowed,
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version="1",
        selected_at="2026-10-01T00:00:00+00:00" if allowed else None,
        explicit=True,
    )


def _context(*, allowed: bool, identity: str = "guest") -> AnalyticsServerContext:
    return AnalyticsServerContext(
        preference=_preference(allowed),
        subject_id=SUBJECT if allowed else None,
        identity_kind=identity,
    )


def _resolve(decision_id: str, owner: object) -> BoundDecision | None:
    del owner
    if decision_id == OWNED_DECISION:
        return BoundDecision(
            decision_id=OWNED_DECISION,
            context_version=4,
            product_ids=frozenset({"sku-1"}),
        )
    return None


@pytest.fixture()
def stores(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint39.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    analytics_repo = FirstPartyProductAnalyticsRepository(session_factory=factory)
    feedback_repo = FirstPartyFeedbackRepository(session_factory=factory)
    analytics = ProductAnalyticsService(analytics_repo)
    feedback = FeedbackReportService(feedback_repo, analytics)
    yield {
        "factory": factory,
        "analytics_repo": analytics_repo,
        "feedback_repo": feedback_repo,
        "analytics": analytics,
        "feedback": feedback,
    }
    engine.dispose()
    reset_sync_engine()


@pytest.fixture()
async def api(stores: dict):
    app = create_app()
    app.dependency_overrides[get_product_analytics_service] = lambda: stores["analytics"]
    app.dependency_overrides[get_feedback_report_service] = lambda: stores["feedback"]
    app.dependency_overrides[get_bound_decision_resolver] = lambda: _resolve
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, stores
    app.dependency_overrides.clear()


def _dump_events(repo: FirstPartyProductAnalyticsRepository) -> str:
    return json.dumps([asdict(event) for event in repo.list_events()], default=str)


def test_default_preference_is_essential_only() -> None:
    preference = read_tracking_preference(None)
    assert preference.choice == "essential_only"
    assert preference.analytics_allowed is False
    assert preference.explicit is False
    assert preference.advertising_allowed is False
    assert tracking_mode() == "essential_only"
    assert category_allowed("analytics") is False
    assert analytics_provider() is None
    assert cmp_vendor() is None
    assert non_essential_tracking_allowed() is False


def test_opt_in_and_opt_out_change_only_the_explicit_choice() -> None:
    response = Response()
    allowed, subject = apply_tracking_choice(response, "analytics_allowed", existing_subject=None)
    assert allowed.analytics_allowed is True
    assert allowed.advertising_allowed is False
    assert subject is not None
    raw = response.headers["set-cookie"]
    assert "user_id" not in raw
    assert "email" not in raw
    stored = read_tracking_preference(_cookie_value(response, PREFERENCE_COOKIE))
    assert stored.analytics_allowed is True
    denied_response = Response()
    denied, cleared = apply_tracking_choice(
        denied_response,
        "essential_only",
        existing_subject=subject,
    )
    assert denied.analytics_allowed is False
    assert denied.advertising_allowed is False
    assert cleared is None
    deletion = denied_response.headers.getlist("set-cookie")
    assert any(ANALYTICS_SUBJECT_COOKIE in item and "Max-Age=0" in item for item in deletion)


def test_schema_accepts_known_event_and_rejects_closed_fields(stores: dict) -> None:
    service: ProductAnalyticsService = stores["analytics"]
    recorded = service.record_client_event(
        {"event_name": "results_viewed", "surface": "results", "outcome": "viewed"},
        _context(allowed=True),
    )
    assert recorded.status == "recorded"
    assert stores["analytics_repo"].count() == 1
    stored = stores["analytics_repo"].list_events()[0]
    assert stored.event_schema == EVENT_SCHEMA
    assert stored.event_name == "results_viewed"
    assert stored.anonymous_subject_hash == anonymous_subject_hash(SUBJECT)
    assert stored.anonymous_subject_hash != SUBJECT
    assert stored.identity_kind == "guest"

    unknown = service.record_client_event({"event_name": "page_view"}, _context(allowed=True))
    extra = service.record_client_event(
        {"event_name": "results_viewed", "favorite_color": "blue"},
        _context(allowed=True),
    )
    assert unknown.status == "schema_rejected"
    assert extra.status == "schema_rejected"
    assert extra.reason == "unknown_property"
    for field in (
        "question",
        "answer",
        "email",
        "access_token",
        "session_token",
        "query",
        "conversation_id",
    ):
        rejected = service.record_client_event(
            {"event_name": "results_viewed", field: "secret-value"},
            _context(allowed=True),
        )
        assert rejected.status == "schema_rejected"
        assert rejected.reason == "forbidden_field"
        assert field in FORBIDDEN_ANALYTICS_FIELDS or field in {"query", "question", "answer"}
    assert stores["analytics_repo"].count() == 1


def test_consent_gate_dedup_and_recreation(stores: dict) -> None:
    service: ProductAnalyticsService = stores["analytics"]
    event_id = "33333333-3333-4333-8333-333333333333"
    payload = {
        "event_name": "compare_opened",
        "event_id": event_id,
        "surface": "compare",
        "outcome": "opened",
    }
    suppressed = service.record_client_event(payload, _context(allowed=False))
    assert suppressed.status == "suppressed_no_consent"
    assert stores["analytics_repo"].count() == 0

    class ExplodingSink:
        def persist(self, event: object) -> object:
            raise AssertionError(event)

    assert (
        ProductAnalyticsService(ExplodingSink())
        .record_client_event(payload, _context(allowed=False))
        .status
        == "suppressed_no_consent"
    )

    first = service.record_client_event(payload, _context(allowed=True))
    second = service.record_client_event(payload, _context(allowed=True))
    assert first.status == "recorded"
    assert second.status == "duplicate"
    conflict = service.record_client_event(
        {**payload, "surface": "why", "outcome": "opened"},
        _context(allowed=True),
    )
    assert conflict.status == "identity_conflict"
    assert stores["analytics_repo"].count() == 1
    assert stores["analytics_repo"].get(event_id).surface == "compare"

    recreated_repo = FirstPartyProductAnalyticsRepository(session_factory=stores["factory"])
    recreated = ProductAnalyticsService(recreated_repo)
    assert recreated_repo.count() == 1
    again = recreated.record_client_event(payload, _context(allowed=True))
    assert again.status == "duplicate"
    assert recreated_repo.count() == 1


def test_server_identity_is_opaque_and_ask_text_is_absent(stores: dict) -> None:
    from app.analytics.ask_events import emit_ask_product_events

    owner = ConversationOwner(
        principal_type="account",
        principal_id="user-raw-123",
        session_id="sess-raw-456",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    response = Response()
    _preference_set, subject = apply_tracking_choice(
        response,
        "analytics_allowed",
        existing_subject=None,
    )
    cookie = "; ".join(item.split(";", 1)[0] for item in response.headers.getlist("set-cookie"))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/shopping-assistant/query",
        "raw_path": b"/api/v1/shopping-assistant/query",
        "query_string": b"",
        "headers": [(b"cookie", cookie.encode())],
        "client": ("203.0.113.8", 443),
        "server": ("test", 80),
    }
    question = "raw question about a secret product"
    answer = "raw assistant answer with an email shopper@example.com"
    emit_ask_product_events(
        Request(scope),
        Response(),
        surface="results",
        answer_status="insufficient_evidence",
        evidence_count=1,
        decision_id=FOREIGN_DECISION,
        owner=owner,
        analytics=stores["analytics"],
        snapshots=None,
    )
    blob = _dump_events(stores["analytics_repo"])
    names = {event.event_name for event in stores["analytics_repo"].list_events()}
    assert names == {"ask_question_submitted", "insufficient_evidence"}
    assert question not in blob
    assert answer not in blob
    assert "user-raw-123" not in blob
    assert "sess-raw-456" not in blob
    assert "203.0.113.8" not in blob
    assert "shopper@example.com" not in blob
    assert FOREIGN_DECISION not in blob
    assert subject not in blob
    for event in stores["analytics_repo"].list_events():
        assert event.identity_kind == "authenticated"
        assert event.anonymous_subject_hash == anonymous_subject_hash(subject)
        assert event.decision_hash is None


def test_feedback_persists_without_copying_text_into_analytics(stores: dict) -> None:
    service: FeedbackReportService = stores["feedback"]
    message = "Price shows 10 but checkout is 99. Reference SECRET-REPORT-TEXT."
    report = service.submit(
        _command("incorrect_price", message),
        _context(allowed=False),
        owner=None,
        resolve_decision=_resolve,
    )
    assert report.created is True
    assert report.report.status == "received"
    assert report.analytics_status == "suppressed_no_consent"
    assert stores["feedback_repo"].count() == 1
    assert stores["analytics_repo"].count() == 0
    assert stores["feedback_repo"].list_reports()[0].message == message

    opted = service.submit(
        _command(
            "incorrect_product_fact",
            message,
            decision_id=OWNED_DECISION,
            product_id="sku-1",
        ),
        _context(allowed=True),
        owner=None,
        resolve_decision=_resolve,
    )
    assert opted.analytics_status == "recorded"
    analytics_blob = _dump_events(stores["analytics_repo"])
    assert "SECRET-REPORT-TEXT" not in analytics_blob
    assert message not in analytics_blob
    assert OWNED_DECISION not in analytics_blob
    assert stores["analytics_repo"].list_events()[-1].event_name == "incorrect_information_report"
    assert stores["analytics_repo"].list_events()[-1].decision_hash == decision_hash(OWNED_DECISION)


def test_feedback_rejects_foreign_decision_bad_product_and_unsafe_text(stores: dict) -> None:
    service: FeedbackReportService = stores["feedback"]
    with pytest.raises(Exception) as foreign:
        service.submit(
            _command("outdated_offer", "Offer ended.", decision_id=FOREIGN_DECISION),
            _context(allowed=True),
            owner=None,
            resolve_decision=_resolve,
        )
    assert foreign.value.code == "decision_not_found"
    with pytest.raises(Exception) as missing_product:
        service.submit(
            _command(
                "source_issue",
                "Source mismatch.",
                decision_id=OWNED_DECISION,
                product_id="not-in-decision",
            ),
            _context(allowed=True),
            owner=None,
            resolve_decision=_resolve,
        )
    assert missing_product.value.code == "product_not_in_decision"
    from app.feedback.schema import FeedbackRejected, parse_feedback_command

    with pytest.raises(FeedbackRejected) as too_long:
        parse_feedback_command(
            {"category": "bug", "message": "x" * (MAX_REPORT_MESSAGE_LENGTH + 1)}
        )
    assert too_long.value.code == "message_too_long"
    with pytest.raises(FeedbackRejected) as html:
        parse_feedback_command(
            {"category": "bug", "message": "<script>alert(1)</script>", "surface": "support"}
        )
    assert html.value.code == "html_not_allowed"
    assert stores["feedback_repo"].count() == 0
    assert stores["analytics_repo"].count() == 0


def test_event_vocabulary_covers_the_roadmap() -> None:
    required = {
        "decision_started",
        "decision_completed",
        "results_viewed",
        "compare_opened",
        "why_opened",
        "outbound_merchant_click",
        "ask_question_submitted",
        "insufficient_evidence",
        "recommendation_helpful",
        "recommendation_not_helpful",
        "incorrect_information_report",
        "return_visit",
        "repeat_decision",
    }
    assert required <= EVENT_NAMES


def test_sprint38_affiliate_and_third_party_boundaries() -> None:
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert _CONFIGURED_BUCKET == 0
    link = _offer_link("https://merchant.example/item", "btn")
    assert 'href="https://merchant.example/item"' in link
    assert 'data-analytics-event="outbound_merchant_click"' in link
    assert "affiliate" not in link.lower()
    analytics_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "app" / "analytics").glob("*.py")
    )
    feedback_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "app" / "feedback").glob("*.py")
    )
    combined = analytics_source + feedback_source
    for token in (
        "googletagmanager",
        "google-analytics",
        "posthog",
        "mixpanel",
        "amplitude",
        "facebook.com/tr",
        "MerchantAnalytics",
    ):
        assert token not in combined
    client_js = (ROOT / "app/static/consumer/js/product_analytics.js").read_text(encoding="utf-8")
    assert "catch" in client_js
    assert "preventDefault" not in client_js
    feedback_js = (ROOT / "app/static/consumer/js/product_feedback.js").read_text(encoding="utf-8")
    assert "textContent" in feedback_js
    assert "innerHTML" not in feedback_js


def _command(category: str, message: str, **extra: object):
    from app.feedback.schema import parse_feedback_command

    payload = {"category": category, "message": message, "surface": "support"}
    payload.update(extra)
    return parse_feedback_command(payload)


def _cookie_value(response: Response, name: str) -> str:
    for header in response.headers.getlist("set-cookie"):
        if header.startswith(f"{name}="):
            return header.split(";", 1)[0].split("=", 1)[1]
    raise AssertionError(name)


async def test_preference_api_fails_closed_and_toggles_the_subject(client: AsyncClient) -> None:
    initial = await client.get("/api/v1/privacy/tracking-preference")
    assert initial.status_code == 200
    body = initial.json()
    assert body["choice"] == "essential_only"
    assert body["analytics_allowed"] is False
    assert body["advertising_allowed"] is False
    assert body["explicit"] is False
    assert ANALYTICS_SUBJECT_COOKIE not in initial.headers.get("set-cookie", "")

    malformed = await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "analytics_allowed", "advertising_allowed": True},
    )
    assert malformed.status_code == 422
    unknown = await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "advertising"},
    )
    assert unknown.status_code == 422

    opted = await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "analytics_allowed"},
    )
    assert opted.status_code == 200
    assert opted.json()["analytics_allowed"] is True
    assert opted.json()["advertising_allowed"] is False
    assert client.cookies.get(ANALYTICS_SUBJECT_COOKIE)

    denied = await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "essential_only"},
    )
    assert denied.json()["analytics_allowed"] is False
    assert client.cookies.get(ANALYTICS_SUBJECT_COOKIE) in {None, ""}


async def test_event_and_feedback_http_boundaries(api) -> None:
    client, stores = api
    await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "essential_only"},
    )
    suppressed = await client.post(
        "/api/v1/analytics/events",
        json={"event_name": "results_viewed", "surface": "results", "outcome": "viewed"},
    )
    assert suppressed.status_code == 200
    assert suppressed.json()["result"] == "suppressed_no_consent"
    assert stores["analytics_repo"].count() == 0

    await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "analytics_allowed"},
    )
    rejected = await client.post(
        "/api/v1/analytics/events",
        json={"event_name": "results_viewed", "email": "shopper@example.com"},
    )
    assert rejected.status_code == 400
    assert stores["analytics_repo"].count() == 0

    event_id = "44444444-4444-4444-8444-444444444444"
    payload = {
        "event_name": "why_opened",
        "event_id": event_id,
        "surface": "why",
        "outcome": "opened",
        "decision_id": FOREIGN_DECISION,
    }
    recorded = await client.post("/api/v1/analytics/events", json=payload)
    assert recorded.status_code == 200
    assert recorded.json()["result"] == "recorded"
    duplicate = await client.post("/api/v1/analytics/events", json=payload)
    assert duplicate.json()["result"] == "duplicate"
    conflict = await client.post(
        "/api/v1/analytics/events",
        json={**payload, "surface": "compare"},
    )
    assert conflict.status_code == 409
    assert stores["analytics_repo"].count() == 1
    assert FOREIGN_DECISION not in _dump_events(stores["analytics_repo"])

    helpful = await client.post(
        "/api/v1/feedback/reports",
        json={"category": "recommendation_helpful", "message": "", "surface": "results"},
    )
    assert helpful.status_code == 200
    assert helpful.json()["status"] == "received"
    not_helpful = await client.post(
        "/api/v1/feedback/reports",
        json={"category": "recommendation_not_helpful", "surface": "results"},
    )
    assert not_helpful.status_code == 200
    for category, text in (
        ("incorrect_price", "The listed price is wrong."),
        ("incorrect_product_fact", "The capacity is wrong."),
        ("outdated_offer", "That offer has ended."),
        ("misleading_recommendation_evidence", "The evidence does not match the offer."),
        ("source_issue", "The source page disagrees."),
    ):
        created = await client.post(
            "/api/v1/feedback/reports",
            json={"category": category, "message": text, "surface": "support"},
        )
        assert created.status_code == 200, category
        assert created.json()["report_id"]
    assert stores["feedback_repo"].count() == 7

    foreign = await client.post(
        "/api/v1/feedback/reports",
        json={
            "category": "incorrect_price",
            "message": "Not mine.",
            "decision_id": FOREIGN_DECISION,
        },
    )
    assert foreign.status_code == 404
    bad_product = await client.post(
        "/api/v1/feedback/reports",
        json={
            "category": "incorrect_price",
            "message": "Wrong item.",
            "decision_id": OWNED_DECISION,
            "product_id": "outside-set",
        },
    )
    assert bad_product.status_code == 400
    owned = await client.post(
        "/api/v1/feedback/reports",
        json={
            "category": "incorrect_price",
            "message": "Bound price issue.",
            "decision_id": OWNED_DECISION,
            "product_id": "sku-1",
        },
    )
    assert owned.status_code == 200
    script = await client.post(
        "/api/v1/feedback/reports",
        json={"category": "bug", "message": "<script>alert(1)</script>"},
    )
    assert script.status_code == 400
    long_message = await client.post(
        "/api/v1/feedback/reports",
        json={"category": "bug", "message": "y" * (MAX_REPORT_MESSAGE_LENGTH + 1)},
    )
    assert long_message.status_code == 400


async def test_feedback_still_works_when_analytics_consent_is_off(api) -> None:
    client, stores = api
    await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "essential_only"},
    )
    created = await client.post(
        "/api/v1/feedback/reports",
        json={
            "category": "recommendation_not_helpful",
            "message": "SECRET-OFF-CONSENT",
            "surface": "results",
        },
    )
    assert created.status_code == 200
    assert created.json()["analytics_status"] in {"not_applicable", "suppressed_no_consent"}
    assert stores["feedback_repo"].count() == 1
    assert stores["analytics_repo"].count() == 0
    assert "SECRET-OFF-CONSENT" not in _dump_events(stores["analytics_repo"])


async def test_support_and_results_surfaces(client: AsyncClient) -> None:
    support = await client.get(f"/support?decision_id={FOREIGN_DECISION}")
    assert support.status_code == 200
    assert "support@piqsavi.com" in support.text
    assert "privacy@piqsavi.com" in support.text
    assert "Report incorrect information" in support.text
    assert "Need help or want to report incorrect product information?" in support.text
    assert "incorrect_price" in support.text
    assert "misleading_recommendation_evidence" in support.text
    assert FOREIGN_DECISION not in support.text
    assert "Sprint 39" not in support.text
    assert "noindex" in support.text
    assert support.headers["x-robots-tag"] == "noindex, nofollow"
    assert "does not promise" in support.text

    results = await client.get("/results/headphones-standard")
    assert results.status_code == 200
    assert 'data-analytics-event="outbound_merchant_click"' in results.text
    assert "recommendation_helpful" in results.text
    assert "recommendation_not_helpful" in results.text
    assert "data-tracking-preference" in results.text
    assert 'data-tracking-mode="essential-only"' in results.text

    privacy = await client.get("/privacy")
    terms = await client.get("/terms")
    assert privacy.status_code in {200, 404}
    assert terms.status_code in {200, 404}
    publication = await client.get("/api/v1/legal/publication-status")
    assert publication.json()["analytics_allowed"] is False
    assert publication.json()["advertising_allowed"] is False
    assert publication.json()["non_essential_tracking_allowed"] is False


async def test_account_consent_records_stay_independent(client: AsyncClient) -> None:
    email = "sprint39-consent@example.invalid"
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123",
            "display_name": "Consent Check",
            "terms_accepted": True,
            "privacy_acknowledged": True,
        },
    )
    assert created.status_code in {200, 201}
    token = created.json().get("access_token") or created.json().get("token")
    if token is None and "session" in created.json():
        token = created.json()["session"].get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}
    before = await client.get("/api/v1/auth/account/consents", headers=headers)
    assert before.status_code == 200
    await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "analytics_allowed"},
    )
    after = await client.get("/api/v1/auth/account/consents", headers=headers)
    assert after.status_code == 200
    assert after.json()["records"] == before.json()["records"]
