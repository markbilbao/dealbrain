"""API tests for Early Access registration."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.core.dependencies import get_early_access_service, get_rate_limiter
from app.early_access.memory import InMemoryEarlyAccessRepository
from app.main import create_app
from app.services.early_access_service import EarlyAccessService
from fastapi.testclient import TestClient


class BoomRepository(InMemoryEarlyAccessRepository):
    def create_if_absent(self, registration):  # noqa: ANN001
        raise RuntimeError("operational store exploded")


@pytest.fixture
def repo() -> InMemoryEarlyAccessRepository:
    return InMemoryEarlyAccessRepository()


@pytest.fixture
def client(repo: InMemoryEarlyAccessRepository) -> Iterator[TestClient]:
    app = create_app()
    service = EarlyAccessService(repo)
    app.dependency_overrides[get_early_access_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "country": "PH",
        "shopping_interest": "phones",
    }
    body.update(overrides)
    return body


def test_success(client: TestClient) -> None:
    response = client.post("/api/v1/early-access", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "success"
    assert body["email_confirmation_status"] == "not_sent"
    assert "inbox" not in body["message"].lower()
    assert "sent you" not in body["message"].lower()


def test_validation_errors(client: TestClient) -> None:
    response = client.post("/api/v1/early-access", json=_payload(full_name=""))
    assert response.status_code in {400, 422}
    assert response.json()["error"] == "validation_error"


def test_duplicate_response(client: TestClient) -> None:
    assert client.post("/api/v1/early-access", json=_payload()).status_code == 200
    response = client.post("/api/v1/early-access", json=_payload(full_name="Other"))
    assert response.status_code == 200
    assert response.json()["outcome"] == "already_registered"


def test_invalid_country(client: TestClient) -> None:
    response = client.post("/api/v1/early-access", json=_payload(country="UK"))
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "validation_error"
    assert "IntegrityError" not in str(body)
    assert "operational_entities" not in str(body)


def test_oversized_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/early-access",
        json=_payload(full_name="A" * 200, shopping_interest="x" * 800),
    )
    assert response.status_code in {400, 422}


def test_rate_limit(client: TestClient) -> None:
    limiter = get_rate_limiter()
    limiter.reset()
    limiter.set_enabled(True)
    try:
        statuses = []
        for i in range(8):
            response = client.post(
                "/api/v1/early-access",
                json=_payload(email=f"user{i}@example.com"),
            )
            statuses.append(response.status_code)
        assert 429 in statuses
        limited = next(r for r in statuses if r == 429)
        assert limited == 429
    finally:
        limiter.reset()
        limiter.set_enabled(False)


def test_technical_failure_returns_generic_error() -> None:
    app = create_app()
    service = EarlyAccessService(BoomRepository())
    app.dependency_overrides[get_early_access_service] = lambda: service
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/early-access", json=_payload())
    app.dependency_overrides.clear()
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_error"
    assert "exploded" not in str(body)
    assert "Traceback" not in str(body)
    assert "sqlalchemy" not in str(body).lower()
    assert "IntegrityError" not in str(body)


def test_no_internal_leakage_on_success(client: TestClient) -> None:
    body = client.post("/api/v1/early-access", json=_payload()).json()
    dumped = str(body)
    assert "DealBrain" not in dumped
    assert "operational_entities" not in dumped
    assert "password" not in dumped


def test_openapi_includes_early_access_route() -> None:
    schema = create_app().openapi()
    assert "/api/v1/early-access" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/early-access"]


def test_events_endpoint_accepts_allowed_names(client: TestClient) -> None:
    response = client.post(
        "/api/v1/early-access/events",
        json={"event": "early_access_cta_clicked", "source": "hero"},
    )
    assert response.status_code == 204


def test_events_unknown_name_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/early-access/events",
        json={"event": "hack_the_logs"},
    )
    assert response.status_code in {400, 422}
    body = response.json()
    assert body.get("error") == "validation_error"


def test_events_arbitrary_source_rejected(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO"):
        response = client.post(
            "/api/v1/early-access/events",
            json={
                "event": "early_access_cta_clicked",
                "source": "victim@example.com",
            },
        )
    assert response.status_code in {400, 422}
    event_logger = "app.api.v1.endpoints.early_access"
    event_messages = [rec.getMessage() for rec in caplog.records if rec.name == event_logger]
    assert "early_access_cta_clicked" not in event_messages
    assert all(
        "victim@example.com" not in rec.getMessage()
        for rec in caplog.records
        if rec.name == event_logger
    )


def test_events_extra_metadata_is_not_logged(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO"):
        response = client.post(
            "/api/v1/early-access/events",
            json={
                "event": "early_access_form_started",
                "email": "ada@example.com",
                "full_name": "Ada Lovelace",
                "shopping_interest": "phones",
            },
        )
    assert response.status_code == 204
    dumped = caplog.text.lower()
    assert "ada@example.com" not in dumped
    assert "ada lovelace" not in dumped
    assert "phones" not in dumped


def test_events_rate_limit_is_tighter_than_default(client: TestClient) -> None:
    limiter = get_rate_limiter()
    previous = limiter.enabled
    limiter.reset()
    limiter.set_enabled(True)
    try:
        statuses = [
            client.post(
                "/api/v1/early-access/events",
                json={"event": "how_it_works_viewed"},
            ).status_code
            for _ in range(21)
        ]
        assert statuses.count(204) == 20
        assert 429 in statuses
        limited = client.post(
            "/api/v1/early-access/events",
            json={"event": "how_it_works_viewed"},
        )
        assert limited.status_code == 429
        assert limited.headers.get("X-RateLimit-Bucket") == "early_access_events"
    finally:
        limiter.reset()
        limiter.set_enabled(previous)


def test_registration_rate_limit_bucket_unchanged(client: TestClient) -> None:
    limiter = get_rate_limiter()
    previous = limiter.enabled
    limiter.reset()
    limiter.set_enabled(True)
    try:
        event = client.post(
            "/api/v1/early-access/events",
            json={"event": "how_it_works_viewed"},
        )
        assert event.status_code == 204
        assert event.headers.get("X-RateLimit-Bucket") == "early_access_events"
        signup = client.post("/api/v1/early-access", json=_payload())
        assert signup.status_code == 200
        assert signup.headers.get("X-RateLimit-Bucket") == "registration"
    finally:
        limiter.reset()
        limiter.set_enabled(previous)


def test_landing_page_is_public(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "PiqSavi" in response.text
    assert "Join Early Access" in response.text


def test_demo_remains_separate(client: TestClient) -> None:
    landing = client.get("/")
    demo = client.get("/demo")
    assert landing.status_code == 200
    assert demo.status_code == 200
    assert "/demo" not in landing.text
    assert landing.text != demo.text
