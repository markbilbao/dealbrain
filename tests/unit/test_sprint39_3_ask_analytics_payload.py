"""Sprint 39.3 ask analytics request serialization at the HTTP boundary."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.schema import (
    CLIENT_EVENT_SEMANTICS,
    EXACT_CLIENT_FIELDS,
    FORBIDDEN_ANALYTICS_FIELDS,
    SERVER_OWNED_FIELDS,
    validate_client_event_payload,
)
from app.analytics.service import ProductAnalyticsService
from app.core.dependencies import get_bound_decision_resolver, get_product_analytics_service
from app.feedback.decisions import BoundDecision
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.session import reset_sync_engine
from app.main import create_app
from app.schemas.product_analytics import ProductAnalyticsEventRequest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ASK_OPENED = {
    "event_name": "ask_opened",
    "surface": "ask",
    "action_type": "open",
    "outcome": "opened",
}
ASK_CLOSED = {
    "event_name": "ask_closed",
    "surface": "ask",
    "action_type": "close",
    "outcome": "closed",
}
DECLARED_OPTIONAL = (
    "event_id",
    "turn_number",
    "evidence_count",
    "latency_band",
    "freshness_band",
    "error_code",
    "decision_id",
)


@pytest.fixture()
def stores(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint39_3.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    analytics_repo = FirstPartyProductAnalyticsRepository(session_factory=factory)
    analytics = ProductAnalyticsService(analytics_repo)
    yield {"analytics_repo": analytics_repo, "analytics": analytics}
    engine.dispose()
    reset_sync_engine()


@pytest.fixture()
async def api(stores: dict):
    app = create_app()

    def _resolve(decision_id: str, owner: object) -> BoundDecision | None:
        del decision_id, owner
        return None

    app.dependency_overrides[get_product_analytics_service] = lambda: stores["analytics"]
    app.dependency_overrides[get_bound_decision_resolver] = lambda: _resolve
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, stores
    app.dependency_overrides.clear()


def _payload(raw: dict[str, object]) -> dict[str, object]:
    return ProductAnalyticsEventRequest.model_validate(raw).client_payload()


def test_client_payload_omits_declared_none_and_keeps_unknown_null() -> None:
    request = ProductAnalyticsEventRequest.model_validate(
        {**ASK_OPENED, "unknown_thing": None, "question": None}
    )
    dumped = request.model_dump()
    for field in DECLARED_OPTIONAL:
        assert dumped[field] is None
    assert dumped["unknown_thing"] is None
    assert dumped["question"] is None

    excluded = request.model_dump(exclude_none=True)
    assert "unknown_thing" not in excluded
    assert "question" not in excluded
    for field in DECLARED_OPTIONAL:
        assert field not in excluded

    extra = request.__pydantic_extra__ or {}
    assert extra["unknown_thing"] is None
    assert extra["question"] is None

    payload = request.client_payload()
    assert set(payload) == {
        "event_name",
        "surface",
        "action_type",
        "outcome",
        "unknown_thing",
        "question",
    }
    assert payload["unknown_thing"] is None
    assert payload["question"] is None
    for field in DECLARED_OPTIONAL:
        assert field not in payload


def test_valid_ask_payload_is_exact_and_protections_are_unchanged() -> None:
    opened = _payload(ASK_OPENED)
    closed = _payload(ASK_CLOSED)
    assert set(opened) == {"event_name", "surface", "action_type", "outcome"}
    assert set(closed) == {"event_name", "surface", "action_type", "outcome"}
    assert validate_client_event_payload(opened) is None
    assert validate_client_event_payload(closed) is None
    assert EXACT_CLIENT_FIELDS["ask_opened"] == frozenset(
        {"event_name", "event_id", "decision_id", "surface", "action_type", "outcome"}
    )
    assert EXACT_CLIENT_FIELDS["ask_closed"] == EXACT_CLIENT_FIELDS["ask_opened"]
    assert CLIENT_EVENT_SEMANTICS["ask_opened"] == {
        "surface": "ask",
        "action_type": "open",
        "outcome": "opened",
    }
    assert CLIENT_EVENT_SEMANTICS["ask_closed"] == {
        "surface": "ask",
        "action_type": "close",
        "outcome": "closed",
    }
    assert "question" in FORBIDDEN_ANALYTICS_FIELDS
    assert "consent_state" in SERVER_OWNED_FIELDS
    assert "event_schema" in SERVER_OWNED_FIELDS


def test_unrelated_declared_value_and_unknown_or_forbidden_nulls_stay_rejected() -> None:
    contradictory = _payload({**ASK_OPENED, "evidence_count": 1})
    assert contradictory["evidence_count"] == 1
    assert validate_client_event_payload(contradictory) == "contradictory_event"

    unknown = _payload({**ASK_OPENED, "unknown_thing": "x"})
    assert unknown["unknown_thing"] == "x"
    assert validate_client_event_payload(unknown) == "unknown_property"

    unknown_null = _payload({**ASK_OPENED, "unknown_thing": None})
    assert "unknown_thing" in unknown_null
    assert unknown_null["unknown_thing"] is None
    assert validate_client_event_payload(unknown_null) == "unknown_property"

    forbidden_null = _payload({**ASK_OPENED, "question": None})
    assert "question" in forbidden_null
    assert forbidden_null["question"] is None
    assert validate_client_event_payload(forbidden_null) == "forbidden_field"

    server_owned = _payload(
        {
            "event_name": "decision_started",
            "surface": "results",
            "action_type": "start",
            "outcome": "started",
        }
    )
    assert validate_client_event_payload(server_owned) == "server_owned_event"


async def _opt_in(client: AsyncClient) -> None:
    opted = await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "analytics_allowed"},
    )
    assert opted.status_code == 200
    assert opted.json()["analytics_allowed"] is True
    assert opted.json()["explicit"] is True


async def test_ask_opened_records_one_row_when_consent_is_on(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post("/api/v1/analytics/events", json=ASK_OPENED)
    assert response.status_code == 200
    assert response.json()["result"] == "recorded"
    events = stores["analytics_repo"].list_events()
    assert stores["analytics_repo"].count() == 1
    assert len(events) == 1
    assert events[0].event_name == "ask_opened"
    blob = json.dumps([asdict(event) for event in events], default=str)
    assert "question" not in blob


async def test_ask_closed_records_one_row_when_consent_is_on(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post("/api/v1/analytics/events", json=ASK_CLOSED)
    assert response.status_code == 200
    assert response.json()["result"] == "recorded"
    events = stores["analytics_repo"].list_events()
    assert stores["analytics_repo"].count() == 1
    assert len(events) == 1
    assert events[0].event_name == "ask_closed"


async def test_ask_opened_is_suppressed_when_consent_is_off(api) -> None:
    client, stores = api
    denied = await client.post(
        "/api/v1/privacy/tracking-preference",
        json={"choice": "essential_only"},
    )
    assert denied.status_code == 200
    assert denied.json()["analytics_allowed"] is False
    response = await client.post("/api/v1/analytics/events", json=ASK_OPENED)
    assert response.status_code == 200
    assert response.json()["result"] == "suppressed_no_consent"
    assert stores["analytics_repo"].count() == 0


async def test_ask_opened_rejects_unrelated_declared_field(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post(
        "/api/v1/analytics/events",
        json={**ASK_OPENED, "evidence_count": 1},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "contradictory_event"
    assert body["message"] == "contradictory_event"
    assert stores["analytics_repo"].count() == 0


async def test_ask_opened_rejects_unknown_extra_field(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post(
        "/api/v1/analytics/events",
        json={**ASK_OPENED, "unknown_thing": "x"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "unknown_property"
    assert stores["analytics_repo"].count() == 0


async def test_ask_opened_rejects_unknown_extra_null(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post(
        "/api/v1/analytics/events",
        json={**ASK_OPENED, "unknown_thing": None},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "unknown_property"
    assert stores["analytics_repo"].count() == 0


async def test_ask_opened_rejects_forbidden_null_field(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post(
        "/api/v1/analytics/events",
        json={**ASK_OPENED, "question": None},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "forbidden_field"
    assert stores["analytics_repo"].count() == 0


async def test_browser_server_owned_event_stays_rejected(api) -> None:
    client, stores = api
    await _opt_in(client)
    response = await client.post(
        "/api/v1/analytics/events",
        json={
            "event_name": "decision_started",
            "surface": "results",
            "action_type": "start",
            "outcome": "started",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "server_owned_event"
    assert stores["analytics_repo"].count() == 0
