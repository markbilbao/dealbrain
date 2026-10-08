"""Sprint 39.5 canonical Results recommendation and PiqScore observation."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from app.analytics.identity import anonymous_subject_hash, decision_hash
from app.analytics.learning import ProductLearningDashboardService
from app.analytics.preference import (
    ANALYTICS_SUBJECT_COOKIE,
    PREFERENCE_COOKIE,
    apply_tracking_choice,
)
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.results_events import (
    PIQSCORE_VIEW_MARKER,
    RECOMMENDATION_VIEW_MARKER,
    emit_canonical_results_visibility,
)
from app.analytics.schema import (
    CLIENT_EVENT_NAMES,
    EVENT_NAMES,
    EVENT_SCHEMA,
    SERVER_EVENT_NAMES,
    ProductAnalyticsEvent,
    assert_stored_event_shape,
    semantic_digest,
    validate_client_event_payload,
    validate_server_event_payload,
)
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.core.dependencies import (
    get_db,
    get_product_analytics_service,
    get_shopping_decision_snapshot_repository,
)
from app.feedback.repository import FirstPartyFeedbackRepository
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.infrastructure.persistence.session import reset_sync_engine
from app.main import create_app
from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import SHOPIFY_LIVE_CALL_PERMITTED
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from tests.unit.test_canonical_uuid_consumer_presentation import (
    BOSE_ID,
    DECISION_ID,
    SONY_ID,
    START,
    _bind,
    _economics_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
SUBJECT = "ab" * 16
NOW = datetime(2026, 10, 8, 12, tzinfo=UTC)
_VISIBILITY = ("recommendation_viewed", "piqscore_viewed")


def _preference(allowed: bool = True):
    from app.analytics.preference import CONSENT_SCHEMA, TrackingPreference

    return TrackingPreference(
        choice="analytics_allowed" if allowed else "essential_only",
        analytics_allowed=allowed,
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version="1",
        selected_at="2026-10-08T00:00:00+00:00",
        explicit=True,
    )


def _context(*, allowed: bool = True, subject: str | None = SUBJECT) -> AnalyticsServerContext:
    return AnalyticsServerContext(
        preference=_preference(allowed),
        subject_id=subject if allowed else None,
        identity_kind="guest",
        decision_hash=decision_hash(DECISION_ID),
        context_version=1,
    )


def _counts(repo: FirstPartyProductAnalyticsRepository) -> Counter[str]:
    return Counter(event.event_name for event in repo.list_events())


def _consent_cookies(*, include_subject: bool = True, allowed: bool = True) -> dict[str, str]:
    response = Response()
    choice = "analytics_allowed" if allowed else "essential_only"
    apply_tracking_choice(response, choice, existing_subject=SUBJECT if include_subject else None)
    cookies: dict[str, str] = {}
    for header in response.headers.getlist("set-cookie"):
        if "Max-Age=0" in header:
            continue
        name, value = header.split(";", 1)[0].split("=", 1)
        if name == ANALYTICS_SUBJECT_COOKIE and not include_subject:
            continue
        cookies[name] = value
    return cookies


def _apply_consent(client: AsyncClient, **kwargs: Any) -> None:
    for name, value in _consent_cookies(**kwargs).items():
        client.cookies.set(name, value)


def _marked(*, recommendation: bool, piqscore: bool) -> str:
    chunks = ["<html><body>"]
    if recommendation:
        chunks.append(f"<article {RECOMMENDATION_VIEW_MARKER}></article>")
    if piqscore:
        chunks.append(f"<div {PIQSCORE_VIEW_MARKER}></div>")
    chunks.append("</body></html>")
    return "".join(chunks)


def _set_cookie_names(response: Response) -> set[str]:
    names: set[str] = set()
    for header in response.headers.get_list("set-cookie"):
        names.add(header.split("=", 1)[0])
    return names


class _BoomAnalytics(ProductAnalyticsService):
    def record_server_event(self, *args: Any, **kwargs: Any):  # noqa: ANN401
        raise RuntimeError("analytics repository failed")


class _FailAfterRender:
    def __init__(self, inner: InMemoryDecisionSnapshotRepository) -> None:
        self._inner = inner
        self.calls = 0

    def get_latest_for_owner(self, decision_id: str, owner: Any) -> Any:
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("telemetry snapshot lookup failed")
        return self._inner.get_latest_for_owner(decision_id, owner)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.fixture()
def stores(tmp_path: Path) -> dict[str, Any]:
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint395.db'}", future=True)
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
def snapshots() -> InMemoryDecisionSnapshotRepository:
    return InMemoryDecisionSnapshotRepository(clock=lambda: START)


@asynccontextmanager
async def _http(
    mock_db_session: Any,
    snapshots: Any,
    analytics: ProductAnalyticsService,
) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shopping_decision_snapshot_repository] = lambda: snapshots
    app.dependency_overrides[get_product_analytics_service] = lambda: analytics
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _server_payload(name: str) -> dict[str, str]:
    return {
        "event_name": name,
        "surface": "results",
        "action_type": "view",
        "outcome": "viewed",
    }


def test_visibility_events_are_server_owned(stores: dict[str, Any]) -> None:
    assert "recommendation_viewed" in EVENT_NAMES
    assert "piqscore_viewed" in EVENT_NAMES
    assert "dealscore_viewed" not in EVENT_NAMES
    for name in _VISIBILITY:
        assert name in SERVER_EVENT_NAMES
        assert name not in CLIENT_EVENT_NAMES
        assert validate_server_event_payload(_server_payload(name)) is None
        assert validate_client_event_payload(_server_payload(name)) == "server_owned_event"
    service: ProductAnalyticsService = stores["analytics"]
    for name in _VISIBILITY:
        recorded = service.record_server_event(_context(), **_server_payload(name))
        assert recorded.status == "recorded"
    queried = {**_server_payload("recommendation_viewed"), "query": "h"}
    assert validate_server_event_payload(queried) == "forbidden_field"
    assert (
        validate_server_event_payload({**_server_payload("piqscore_viewed"), "piqscore": 91})
        == "unknown_property"
    )
    assert (
        validate_client_event_payload(
            {**_server_payload("recommendation_viewed"), "unknown_thing": "x"}
        )
        == "unknown_property"
    )
    client_js = (ROOT / "app/static/consumer/js/product_analytics.js").read_text(encoding="utf-8")
    assert "recommendation_viewed" not in client_js
    assert "piqscore_viewed" not in client_js


@pytest.mark.asyncio
async def test_browser_cannot_submit_visibility_events(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        for name in _VISIBILITY:
            rejected = await client.post("/api/v1/analytics/events", json=_server_payload(name))
            assert rejected.status_code == 400
            assert rejected.json()["detail"] == "server_owned_event"
        forbidden = await client.post(
            "/api/v1/analytics/events",
            json={**_server_payload("recommendation_viewed"), "query": "headphones", "score": 90},
        )
        unknown = await client.post(
            "/api/v1/analytics/events",
            json={**_server_payload("piqscore_viewed"), "product_id": SONY_ID},
        )
    assert forbidden.status_code == 400
    assert forbidden.json()["detail"] == "forbidden_field"
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "unknown_property"
    assert stores["analytics_repo"].count() == 0


def _owned_snapshot(**changes: Any):
    snapshot = _economics_snapshot()
    if changes:
        snapshot = replace(snapshot, **changes)
    return snapshot


async def _open_results(
    client: AsyncClient,
    snapshots: InMemoryDecisionSnapshotRepository,
    *,
    version: int = 1,
    consent: bool = True,
    subject: bool = True,
) -> Any:
    snapshot = _owned_snapshot(context_version=version)
    snapshots.add(snapshot)
    _bind(client, snapshot.owner)
    if consent:
        _apply_consent(client, include_subject=subject, allowed=True)
    return await client.get(f"/results/{DECISION_ID}")


@pytest.mark.asyncio
async def test_canonical_results_records_both_visibility_events(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        page = await _open_results(client, snapshots)
    assert page.status_code == 200
    assert page.text.count(RECOMMENDATION_VIEW_MARKER) == 1
    assert page.text.count(PIQSCORE_VIEW_MARKER) == 1
    events = stores["analytics_repo"].list_events()
    names = _counts(stores["analytics_repo"])
    assert names["recommendation_viewed"] == 1
    assert names["piqscore_viewed"] == 1
    assert names["updated_results_viewed"] == 0
    expected_hash = decision_hash(DECISION_ID)
    for event in events:
        assert event.decision_hash == expected_hash
        assert event.context_version == 1
        assert event.surface == "results"
        assert event.action_type == "view"
        assert event.outcome == "viewed"
        payload = asdict(event)
        blob = json.dumps(payload, default=str)
        assert DECISION_ID not in blob
        assert SONY_ID not in blob
        assert BOSE_ID not in blob
        assert "Sony" not in blob
        assert "Best Piq" not in blob
        assert SUBJECT not in blob
        assert "session-" not in blob
        assert "piqscore" not in payload
        assert "score" not in payload
        assert "product_id" not in payload
        assert "query" not in payload
        assert event.anonymous_subject_hash == anonymous_subject_hash(SUBJECT)


@pytest.mark.asyncio
async def test_context_version_above_one_still_records_visibility(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        page = await _open_results(client, snapshots, version=2)
    assert page.status_code == 200
    names = _counts(stores["analytics_repo"])
    assert names["recommendation_viewed"] == 1
    assert names["piqscore_viewed"] == 1
    assert names["updated_results_viewed"] == 1
    for event in stores["analytics_repo"].list_events():
        if event.event_name in _VISIBILITY:
            assert event.context_version == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("allowed", "subject"),
    [(False, False), (True, False), (False, True)],
)
async def test_missing_consent_or_subject_writes_zero_rows(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
    allowed: bool,
    subject: bool,
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        snapshot = _owned_snapshot()
        snapshots.add(snapshot)
        _bind(client, snapshot.owner)
        if allowed or subject:
            _apply_consent(client, include_subject=subject, allowed=allowed)
        page = await client.get(f"/results/{DECISION_ID}")
    assert page.status_code == 200
    assert RECOMMENDATION_VIEW_MARKER in page.text
    assert stores["analytics_repo"].count() == 0
    assert ANALYTICS_SUBJECT_COOKIE not in _set_cookie_names(page)


@pytest.mark.asyncio
async def test_existing_subject_records_and_silence_does_not(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        snapshot = _owned_snapshot()
        snapshots.add(snapshot)
        _bind(client, snapshot.owner)
        silent = await client.get(f"/results/{DECISION_ID}")
        assert silent.status_code == 200
        assert stores["analytics_repo"].count() == 0
        _apply_consent(client, include_subject=True, allowed=True)
        recorded = await client.get(f"/results/{DECISION_ID}")
    assert recorded.status_code == 200
    names = _counts(stores["analytics_repo"])
    assert names["recommendation_viewed"] == 1
    assert names["piqscore_viewed"] == 1
    assert ANALYTICS_SUBJECT_COOKIE not in _set_cookie_names(recorded)
    assert PREFERENCE_COOKIE not in _set_cookie_names(recorded)


@pytest.mark.asyncio
async def test_fixture_unavailable_compare_and_why_write_zero_rows(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        snapshot = _owned_snapshot()
        snapshots.add(snapshot)
        _bind(client, snapshot.owner)
        _apply_consent(client, include_subject=True, allowed=True)
        fixture = await client.get("/results/headphones-standard")
        unavailable_url = await client.get("/results/unavailable")
        unknown = await client.get("/results/00000000-0000-4000-8000-000000000099")
        compare = await client.get(f"/compare/{DECISION_ID}")
        why = await client.get(f"/why-best-piq/{DECISION_ID}")
        monkeypatch.setattr("app.consumer.mode.fixture_catalogs_permitted", lambda: False)
        blocked_fixture = await client.get("/results/unavailable")
    assert fixture.status_code == 200
    assert 'data-presentation-mode="fixture"' in fixture.text
    assert "PiqScore" in fixture.text
    assert RECOMMENDATION_VIEW_MARKER not in fixture.text
    assert PIQSCORE_VIEW_MARKER not in fixture.text
    assert unavailable_url.status_code == 200
    assert unknown.status_code == 200
    assert 'data-unavailable="true"' in unknown.text
    assert RECOMMENDATION_VIEW_MARKER not in unknown.text
    assert compare.status_code == 200
    assert why.status_code == 200
    assert "PiqScore" in why.text
    assert PIQSCORE_VIEW_MARKER not in why.text
    assert PIQSCORE_VIEW_MARKER not in compare.text
    assert blocked_fixture.status_code == 200
    assert 'data-unavailable="true"' in blocked_fixture.text
    assert stores["analytics_repo"].count() == 0


@pytest.mark.asyncio
async def test_fixture_markers_still_write_zero_rows(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _render(view: Any, show_tracking_choice: bool = False) -> str:
        return (
            f'<html data-presentation-mode="{view.presentation_mode}">'
            f"<article {RECOMMENDATION_VIEW_MARKER}></article>"
            f"<div {PIQSCORE_VIEW_MARKER}></div></html>"
        )

    monkeypatch.setattr("app.api.consumer.render_page", _render)
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        _apply_consent(client, include_subject=True, allowed=True)
        page = await client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert "fixture" in page.text
    assert RECOMMENDATION_VIEW_MARKER in page.text
    assert stores["analytics_repo"].count() == 0


@pytest.mark.asyncio
async def test_production_early_access_redirect_writes_zero_rows(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.consumer.mode.get_settings",
        lambda: SimpleNamespace(app_env="production"),
    )
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        snapshot = _owned_snapshot()
        snapshots.add(snapshot)
        _bind(client, snapshot.owner)
        _apply_consent(client, include_subject=True, allowed=True)
        page = await client.get(f"/results/{DECISION_ID}")
    assert page.status_code == 303
    assert page.headers["location"] == "/"
    assert stores["analytics_repo"].count() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("recommendation", "piqscore", "recommendation_count", "piqscore_count"),
    [(True, True, 1, 1), (True, False, 1, 0), (False, True, 0, 1), (False, False, 0, 0)],
)
async def test_markers_are_checked_independently(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    recommendation: bool,
    piqscore: bool,
    recommendation_count: int,
    piqscore_count: int,
) -> None:
    html = _marked(recommendation=recommendation, piqscore=piqscore)

    def _render(view: Any, show_tracking_choice: bool = False) -> str:
        return html

    monkeypatch.setattr("app.api.consumer.render_page", _render)
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        page = await _open_results(client, snapshots)
    assert page.status_code == 200
    assert page.text == html
    names = _counts(stores["analytics_repo"])
    assert names["recommendation_viewed"] == recommendation_count
    assert names["piqscore_viewed"] == piqscore_count


@pytest.mark.asyncio
async def test_repeated_canonical_gets_are_separate_views(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        first = await _open_results(client, snapshots)
        second = await client.get(f"/results/{DECISION_ID}")
    assert first.status_code == 200
    assert second.status_code == 200
    names = _counts(stores["analytics_repo"])
    assert names["recommendation_viewed"] == 2
    assert names["piqscore_viewed"] == 2
    ids = [
        event.event_id
        for event in stores["analytics_repo"].list_events()
        if event.event_name == "recommendation_viewed"
    ]
    assert len(ids) == 2
    assert ids[0] != ids[1]


@pytest.mark.asyncio
async def test_analytics_failure_does_not_change_results(
    mock_db_session: Any,
    snapshots: InMemoryDecisionSnapshotRepository,
    stores: dict[str, Any],
) -> None:
    async with _http(mock_db_session, snapshots, stores["analytics"]) as client:
        healthy = await _open_results(client, snapshots)
    boom = _BoomAnalytics(stores["analytics_repo"])
    async with _http(mock_db_session, snapshots, boom) as client:
        snapshot = snapshots.get(DECISION_ID, 1)
        assert snapshot is not None
        _bind(client, snapshot.owner)
        _apply_consent(client, include_subject=True, allowed=True)
        failed = await client.get(f"/results/{DECISION_ID}")
    assert healthy.status_code == 200
    assert failed.status_code == 200
    assert failed.text == healthy.text
    assert "analytics repository failed" not in failed.text
    assert _counts(stores["analytics_repo"])["recommendation_viewed"] == 1


@pytest.mark.asyncio
async def test_telemetry_snapshot_failure_does_not_break_results(
    mock_db_session: Any,
    stores: dict[str, Any],
) -> None:
    inner = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    snapshot = _owned_snapshot()
    inner.add(snapshot)
    flaky = _FailAfterRender(inner)
    async with _http(mock_db_session, flaky, stores["analytics"]) as client:
        _bind(client, snapshot.owner)
        _apply_consent(client, include_subject=True, allowed=True)
        page = await client.get(f"/results/{DECISION_ID}")
    assert page.status_code == 200
    assert RECOMMENDATION_VIEW_MARKER in page.text
    assert PIQSCORE_VIEW_MARKER in page.text
    assert flaky.calls >= 2
    assert stores["analytics_repo"].count() == 0


def test_markers_without_an_authorized_snapshot_write_nothing(stores: dict[str, Any]) -> None:
    response = HTMLResponse(_marked(recommendation=True, piqscore=True))
    emit_canonical_results_visibility(
        _request(),
        response,
        decision_id=DECISION_ID,
        analytics=stores["analytics"],
        snapshots=InMemoryDecisionSnapshotRepository(clock=lambda: START),
    )
    assert stores["analytics_repo"].count() == 0


def _request() -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": f"/results/{DECISION_ID}",
        "raw_path": b"/results",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 5000),
        "server": ("test", 80),
    }
    return Request(scope)


def _store_visibility(
    repo: FirstPartyProductAnalyticsRepository,
    *,
    name: str,
    when: datetime,
) -> None:
    event_id = str(uuid4())
    event = ProductAnalyticsEvent(
        event_schema=EVENT_SCHEMA,
        event_name=name,
        event_id=event_id,
        occurred_at=when,
        anonymous_subject_hash=anonymous_subject_hash(SUBJECT),
        identity_kind="guest",
        decision_hash=decision_hash(DECISION_ID),
        surface="results",
        action_type="view",
        turn_number=None,
        evidence_count=None,
        latency_band=None,
        freshness_band=None,
        error_code=None,
        context_version=1,
        selected_market=None,
        outcome="viewed",
        consent_state="analytics_allowed",
        dedup_key=event_id,
        content_digest="",
    )
    stored = replace(event, content_digest=semantic_digest(event))
    assert_stored_event_shape(stored)
    repo.persist(stored)


def test_recommendation_visibility_dashboard_windows_and_truncation(
    stores: dict[str, Any],
) -> None:
    repo = stores["analytics_repo"]
    learning: ProductLearningDashboardService = stores["learning"]
    blank = learning.summary("1d", environment="test", now=NOW)["metrics"]
    assert blank["recommendation_visibility"] == {
        "recommendation_viewed": 0,
        "piqscore_viewed": 0,
        "partial": False,
    }
    _store_visibility(repo, name="results_viewed", when=datetime(2026, 10, 8, 1, tzinfo=UTC))
    _store_visibility(repo, name="recommendation_viewed", when=datetime(2026, 10, 8, 2, tzinfo=UTC))
    _store_visibility(repo, name="piqscore_viewed", when=datetime(2026, 10, 5, 1, tzinfo=UTC))
    _store_visibility(repo, name="recommendation_viewed", when=datetime(2026, 9, 20, 1, tzinfo=UTC))
    _store_visibility(repo, name="piqscore_viewed", when=datetime(2026, 9, 20, 2, tzinfo=UTC))
    _store_visibility(repo, name="recommendation_viewed", when=datetime(2026, 8, 1, 1, tzinfo=UTC))
    day = learning.summary("1d", environment="test", now=NOW)["metrics"]
    day = day["recommendation_visibility"]
    week = learning.summary("7d", environment="test", now=NOW)["metrics"][
        "recommendation_visibility"
    ]
    month = learning.summary("30d", environment="test", now=NOW)
    visibility = month["metrics"]["recommendation_visibility"]
    funnel = month["metrics"]["core_funnel"]
    assert day["recommendation_viewed"] == 1
    assert day["piqscore_viewed"] == 0
    assert day["partial"] is False
    assert week["recommendation_viewed"] == 1
    assert week["piqscore_viewed"] == 1
    assert visibility["recommendation_viewed"] == 2
    assert visibility["piqscore_viewed"] == 2
    assert visibility["partial"] is False
    assert set(visibility) == {"recommendation_viewed", "piqscore_viewed", "partial"}
    assert funnel["results_viewed"] == 1
    assert "recommendation_viewed" not in funnel
    assert "piqscore_viewed" not in funnel
    rendered = json.dumps(visibility)
    assert "dealscore" not in rendered
    assert "Sony" not in rendered
    assert DECISION_ID not in rendered
    assert "90" not in rendered
    _store_visibility(repo, name="piqscore_viewed", when=datetime(2026, 10, 8, 3, tzinfo=UTC))
    truncated = ProductLearningDashboardService(
        repo,
        stores["feedback_repo"],
        max_scan_rows=1,
    ).summary("30d", environment="test", now=NOW)
    scanned = truncated["metrics"]["recommendation_visibility"]
    assert truncated["coverage"]["analytics_truncated"] is True
    assert scanned["partial"] is True
    assert scanned["piqscore_viewed"] == 1
    assert scanned["recommendation_viewed"] == 0


def test_sprint_39_5_does_not_close_sprint_39_or_touch_shopify() -> None:
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md").read_text(
        encoding="utf-8"
    )
    assert sprint.startswith("# Sprint 39")
    assert "**Status:** IN PROGRESS" in sprint
    assert "not ENGINEERING COMPLETE" in sprint
    assert "current Class C count is 21" in sprint
    assert "Class C count remains 21" in sprint
    assert "The current Class C count is 19" in sprint
    assert "| Recommendation views | B |" in sprint
    assert "| DealScore / PiqScore views | B |" in sprint
    assert "Neither row is A." in sprint
    assert "Sprint 39.5" in sprint
    assert "No staging proof is claimed" in sprint
    assert "No next engineering slice is selected by this reconciliation." in sprint
    assert "recommendation_viewed" in sprint
    assert "piqscore_viewed" in sprint
    assert "dealscore_viewed" in sprint
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
