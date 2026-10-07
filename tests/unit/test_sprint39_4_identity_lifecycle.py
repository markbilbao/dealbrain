"""Sprint 39.4 consent-gated identity lifecycle product analytics."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.analytics.identity import anonymous_subject_hash
from app.analytics.identity_lifecycle import (
    LOGIN_FAILURE_ERROR_CODES,
    login_failure_error_code,
)
from app.analytics.learning import ProductLearningDashboardService
from app.analytics.preference import (
    ANALYTICS_SUBJECT_COOKIE,
    apply_tracking_choice,
)
from app.analytics.repository import FirstPartyProductAnalyticsRepository
from app.analytics.schema import (
    CLIENT_EVENT_NAMES,
    EVENT_NAMES,
    EVENT_SCHEMA,
    IDENTITY_LIFECYCLE_EVENT_NAMES,
    SERVER_EVENT_NAMES,
    AnalyticsWriteResult,
    ProductAnalyticsEvent,
    assert_stored_event_shape,
    semantic_digest,
)
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.auth.security import AuditLogger, RateLimiterHook
from app.auth.service import AuthService
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.consumer.guest_continuity import account_owner_from_session
from app.core.dependencies import (
    get_product_analytics_service,
    get_shopping_conversation_repository,
    get_shopping_decision_snapshot_repository,
    get_user_platform_service,
)
from app.domain.entities.shopping_assistant import ConversationOwner, DecisionContextReference
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformRateLimitError,
    UserPlatformValidationError,
)
from app.feedback.repository import FirstPartyFeedbackRepository
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.errors import PersistenceError
from app.infrastructure.persistence.session import reset_sync_engine
from app.main import create_app
from app.privacy.lifecycle import (
    ACCOUNT_DELETE_CONFIRMATION,
    RETAINED_LIMITATIONS,
    AccountLifecycleService,
)
from app.profile.service import ProfileService
from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.memory import InMemoryUserPlatformStore
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import Response

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "Password123"
NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)
SUBJECT = "ab" * 16
DECISION_UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_IDENTITY_ORDER = (
    "registration_completed",
    "registration_verified",
    "login_success",
    "login_failure",
    "account_deleted",
    "authentication_transition",
)


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class _BoomSink:
    def persist(self, event: ProductAnalyticsEvent) -> AnalyticsWriteResult:
        raise PersistenceError("repository unavailable")


class _RejectingAnalytics(ProductAnalyticsService):
    def record_server_event(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return AnalyticsWriteResult(status="schema_rejected", reason="schema_rejected")


def _platform(
    *,
    clock: _Clock | None = None,
    rate_limiter: RateLimiterHook | None = None,
) -> tuple[InMemoryUserPlatformStore, UserPlatformService]:
    store = InMemoryUserPlatformStore()
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        email_changes=store.email_changes,
        consents=store.consents,
        audit=audit,
        clock=clock,
        rate_limiter=rate_limiter,
    )
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        lifecycle=AccountLifecycleService(
            users=store.users,
            sessions=store.sessions,
            profiles=store.profiles,
            saved=store.saved,
            password_resets=store.password_resets,
            email_verifications=store.email_verifications,
            email_changes=store.email_changes,
            consents=store.consents,
            audit=audit,
            clock=clock,
        ),
        consents=store.consents,
        audit=audit,
        clock=clock,
    )
    return store, service


def _consent_cookies(*, include_subject: bool = True, allowed: bool = True) -> dict[str, str]:
    response = Response()
    choice = "analytics_allowed" if allowed else "essential_only"
    apply_tracking_choice(response, choice, existing_subject=SUBJECT if include_subject else None)
    cookies: dict[str, str] = {}
    for header in response.headers.getlist("set-cookie"):
        pair = header.split(";", 1)[0]
        name, value = pair.split("=", 1)
        if name == ANALYTICS_SUBJECT_COOKIE and not include_subject:
            continue
        if "Max-Age=0" in header:
            continue
        cookies[name] = value
    return cookies


def _register_body(email: str) -> dict[str, object]:
    return {
        "email": email,
        "password": PASSWORD,
        "display_name": "Shopper",
        "terms_accepted": True,
        "privacy_acknowledged": True,
    }


def _email(label: str) -> str:
    return f"{label}-{uuid4().hex[:8]}@example.invalid"


def _names(repo: FirstPartyProductAnalyticsRepository) -> list[str]:
    return [event.event_name for event in repo.list_events()]


def _named(repo: FirstPartyProductAnalyticsRepository, name: str) -> list[ProductAnalyticsEvent]:
    return [event for event in repo.list_events() if event.event_name == name]


def _public_blob(repo: FirstPartyProductAnalyticsRepository) -> str:
    rows = []
    for event in repo.list_events():
        payload = asdict(event)
        payload.pop("anonymous_subject_hash", None)
        payload.pop("content_digest", None)
        rows.append(payload)
    return json.dumps(rows, default=str)


@pytest.fixture()
def stores(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint394.db'}", future=True)
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


def _guest(principal_id: str) -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=NOW + timedelta(hours=2),
    )


@asynccontextmanager
async def _http(stores: dict, service: UserPlatformService, analytics=None, overrides=None):
    app = create_app()
    app.dependency_overrides[get_product_analytics_service] = lambda: (
        stores["analytics"] if analytics is None else analytics
    )
    app.dependency_overrides[get_user_platform_service] = lambda: service
    for key, value in (overrides or {}).items():
        app.dependency_overrides[key] = value
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _store_identity_event(
    repo: FirstPartyProductAnalyticsRepository,
    *,
    name: str,
    when: datetime,
    error_code: str | None = None,
) -> None:
    action = "submit" if name in {"login_success", "login_failure"} else "complete"
    outcome = "failed" if name == "login_failure" else "completed"
    event_id = str(uuid4())
    event = ProductAnalyticsEvent(
        event_schema=EVENT_SCHEMA,
        event_name=name,
        event_id=event_id,
        occurred_at=when,
        anonymous_subject_hash=anonymous_subject_hash(SUBJECT),
        identity_kind="guest",
        decision_hash=None,
        surface="account",
        action_type=action,
        turn_number=None,
        evidence_count=None,
        latency_band=None,
        freshness_band=None,
        error_code=error_code,
        context_version=None,
        selected_market=None,
        outcome=outcome,
        consent_state="analytics_allowed",
        dedup_key=event_id,
        content_digest="",
    )
    stored = replace(event, content_digest=semantic_digest(event))
    assert_stored_event_shape(stored)
    repo.persist(stored)


def test_identity_events_are_server_owned(stores: dict) -> None:
    assert IDENTITY_LIFECYCLE_EVENT_NAMES <= EVENT_NAMES
    assert IDENTITY_LIFECYCLE_EVENT_NAMES <= SERVER_EVENT_NAMES
    assert IDENTITY_LIFECYCLE_EVENT_NAMES.isdisjoint(CLIENT_EVENT_NAMES)
    assert set(_IDENTITY_ORDER) == IDENTITY_LIFECYCLE_EVENT_NAMES
    context = AnalyticsServerContext(
        preference=_preference(),
        subject_id=SUBJECT,
        identity_kind="guest",
    )
    service: ProductAnalyticsService = stores["analytics"]
    for name in _IDENTITY_ORDER:
        action = "submit" if name.startswith("login_") else "complete"
        outcome = "failed" if name == "login_failure" else "completed"
        recorded = service.record_server_event(
            context,
            event_name=name,
            surface="account",
            action_type=action,
            outcome=outcome,
            error_code="auth_failed" if name == "login_failure" else None,
        )
        assert recorded.status == "recorded", name
    assert _names(stores["analytics_repo"]) == list(_IDENTITY_ORDER)


def _preference():
    from app.analytics.preference import CONSENT_SCHEMA, TrackingPreference

    return TrackingPreference(
        choice="analytics_allowed",
        analytics_allowed=True,
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version="1",
        selected_at="2026-10-07T00:00:00+00:00",
        explicit=True,
    )


async def test_browser_cannot_forge_identity_events(stores: dict) -> None:
    _store, service = _platform()
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        for name in _IDENTITY_ORDER:
            rejected = await client.post(
                "/api/v1/analytics/events",
                json={
                    "event_name": name,
                    "surface": "account",
                    "action_type": "complete",
                    "outcome": "completed",
                },
                cookies=cookies,
            )
            assert rejected.status_code == 400
            assert rejected.json()["detail"] == "server_owned_event"
        forbidden = await client.post(
            "/api/v1/analytics/events",
            json={"event_name": "results_viewed", "email": "shopper@example.invalid"},
            cookies=cookies,
        )
        unknown = await client.post(
            "/api/v1/analytics/events",
            json={
                "event_name": "results_viewed",
                "surface": "results",
                "action_type": "view",
                "outcome": "viewed",
                "shopper_note": "free text",
            },
            cookies=cookies,
        )
    assert forbidden.status_code == 400
    assert forbidden.json()["detail"] == "forbidden_field"
    assert unknown.status_code == 400
    assert unknown.json()["detail"] == "unknown_property"
    assert stores["analytics_repo"].count() == 0
    client_js = (ROOT / "app/static/consumer/js/product_analytics.js").read_text(encoding="utf-8")
    for name in _IDENTITY_ORDER:
        assert name not in client_js


async def test_registration_emits_once_with_consent_and_no_raw_identity(stores: dict) -> None:
    _store, service = _platform()
    email = _email("register")
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        created = await client.post(
            "/api/v1/auth/register",
            json=_register_body(email),
            cookies=cookies,
        )
        duplicate = await client.post(
            "/api/v1/auth/register",
            json=_register_body(email),
            cookies=cookies,
        )
    assert created.status_code == 201
    assert duplicate.status_code == 409
    events = stores["analytics_repo"].list_events()
    assert [event.event_name for event in events] == ["registration_completed"]
    event = events[0]
    body = created.json()
    blob = _public_blob(stores["analytics_repo"])
    assert event.surface == "account"
    assert event.action_type == "complete"
    assert event.outcome == "completed"
    assert event.identity_kind == "guest"
    assert event.error_code is None
    assert event.anonymous_subject_hash == anonymous_subject_hash(cookies[ANALYTICS_SUBJECT_COOKIE])
    assert email not in blob
    assert body["user"]["user_id"] not in blob
    assert body["session"]["session_id"] not in blob
    assert body["access_token"] not in blob
    assert PASSWORD not in blob
    assert cookies[ANALYTICS_SUBJECT_COOKIE] not in blob


async def test_registration_without_consent_or_subject_writes_nothing(stores: dict) -> None:
    _store, service = _platform()
    async with _http(stores, service) as client:
        off = await client.post("/api/v1/auth/register", json=_register_body(_email("off")))
        assert off.status_code == 201
        no_subject = await client.post(
            "/api/v1/auth/register",
            json=_register_body(_email("nosubject")),
            cookies=_consent_cookies(include_subject=False),
        )
        assert no_subject.status_code == 201
    assert stores["analytics_repo"].count() == 0


async def test_failed_registration_does_not_emit(stores: dict) -> None:
    _store, service = _platform()
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        invalid = await client.post(
            "/api/v1/auth/register",
            json={
                "email": _email("weak"),
                "password": "password",
                "display_name": "Shopper",
            },
            cookies=cookies,
        )
    assert invalid.status_code == 400
    assert stores["analytics_repo"].count() == 0


async def test_registration_survives_analytics_failure(stores: dict) -> None:
    _store, service = _platform()
    email = _email("boom-register")
    cookies = _consent_cookies()
    boom = ProductAnalyticsService(_BoomSink())
    rejecting = _RejectingAnalytics(_BoomSink())
    async with _http(stores, service, analytics=boom) as client:
        created = await client.post(
            "/api/v1/auth/register",
            json=_register_body(email),
            cookies=cookies,
        )
    assert created.status_code == 201
    async with _http(stores, service, analytics=rejecting) as client:
        logged = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            cookies=cookies,
        )
    assert logged.status_code == 200
    assert stores["analytics_repo"].count() == 0


async def test_verification_emits_only_after_confirmation(stores: dict, monkeypatch) -> None:
    monkeypatch.setattr("app.auth.service.allows_inline_identity_tokens", lambda: True)
    clock = _Clock()
    _store, service = _platform(clock=clock)
    email = _email("verify")
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        created = await client.post("/api/v1/auth/register", json=_register_body(email))
        assert created.status_code == 201
        requested = await client.post(
            "/api/v1/auth/verify-email",
            json={"email": email},
            cookies=cookies,
        )
        assert requested.status_code == 200
        assert "registration_verified" not in _names(stores["analytics_repo"])
        token = requested.json()["verification_token_demo_only"]
        confirmed = await client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": token},
            cookies=cookies,
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["email_verified"] is True
        invalid = await client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": "not-a-real-token"},
            cookies=cookies,
        )
        assert invalid.status_code == 401
    assert _names(stores["analytics_repo"]) == ["registration_verified"]
    assert token not in _public_blob(stores["analytics_repo"])
    assert email not in _public_blob(stores["analytics_repo"])

    expired_email = _email("expired")
    async with _http(stores, service) as client:
        await client.post("/api/v1/auth/register", json=_register_body(expired_email))
        issued = await client.post(
            "/api/v1/auth/verify-email",
            json={"email": expired_email},
        )
        expired_token = issued.json()["verification_token_demo_only"]
        clock.now = clock.now + timedelta(days=2)
        expired = await client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": expired_token},
            cookies=cookies,
        )
    assert expired.status_code == 401
    assert _names(stores["analytics_repo"]) == ["registration_verified"]


async def test_verification_without_consent_still_verifies(stores: dict, monkeypatch) -> None:
    monkeypatch.setattr("app.auth.service.allows_inline_identity_tokens", lambda: True)
    _store, service = _platform()
    email = _email("verify-off")
    async with _http(stores, service) as client:
        await client.post("/api/v1/auth/register", json=_register_body(email))
        requested = await client.post("/api/v1/auth/verify-email", json={"email": email})
        confirmed = await client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": requested.json()["verification_token_demo_only"]},
        )
    assert confirmed.status_code == 200
    assert confirmed.json()["email_verified"] is True
    assert stores["analytics_repo"].count() == 0


async def test_login_success_and_failure_codes_do_not_enumerate(stores: dict) -> None:
    store, service = _platform()
    email = _email("login")
    missing = _email("missing")
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        created = await client.post("/api/v1/auth/register", json=_register_body(email))
        assert created.status_code == 201
        success = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            cookies=cookies,
        )
        unknown = await client.post(
            "/api/v1/auth/login",
            json={"email": missing, "password": "WrongPass123!"},
            cookies=cookies,
        )
        wrong = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"},
            cookies=cookies,
        )
        invalid = await client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "WrongPass123!"},
            cookies=cookies,
        )
    assert success.status_code == 200
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    unknown_body = {key: value for key, value in unknown.json().items() if key != "request_id"}
    wrong_body = {key: value for key, value in wrong.json().items() if key != "request_id"}
    assert unknown_body == wrong_body
    assert unknown_body["detail"] == "Invalid email or password."
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "email must be a valid address."
    failures = _named(stores["analytics_repo"], "login_failure")
    assert [event.error_code for event in failures] == [
        "auth_failed",
        "auth_failed",
        "validation_failed",
    ]
    assert {event.error_code for event in failures} <= LOGIN_FAILURE_ERROR_CODES
    success_events = _named(stores["analytics_repo"], "login_success")
    assert len(success_events) == 1
    assert success_events[0].identity_kind == "guest"
    assert len({event.event_id for event in failures}) == len(failures)
    blob = _public_blob(stores["analytics_repo"])
    assert email not in blob
    assert missing not in blob
    assert "unknown_or_inactive" not in blob
    assert "bad_password" not in blob
    assert "not-an-email" not in blob
    audit_details = [
        event.detail for event in store.audit.list_events() if event.event_type == "login_failure"
    ]
    assert "unknown_or_inactive" in audit_details
    assert "bad_password" in audit_details
    assert login_failure_error_code(UserPlatformAuthError("Invalid email or password.")) == (
        "auth_failed"
    )
    invalid_email = UserPlatformValidationError("email must be a valid address.")
    assert login_failure_error_code(invalid_email) == "validation_failed"
    assert login_failure_error_code(UserPlatformRateLimitError("Too many login attempts.")) == (
        "rate_limited"
    )


async def test_login_rate_limit_uses_generic_code(stores: dict) -> None:
    _store, service = _platform(rate_limiter=RateLimiterHook(max_attempts=1))
    email = _email("limited")
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        await client.post("/api/v1/auth/register", json=_register_body(email))
        first = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"},
            cookies=cookies,
        )
        limited = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"},
            cookies=cookies,
        )
    assert first.status_code == 401
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Too many login attempts. Try again later."
    codes = [
        event.error_code
        for event in stores["analytics_repo"].list_events()
        if event.event_name == "login_failure"
    ]
    assert codes == ["auth_failed", "rate_limited"]
    assert email not in _public_blob(stores["analytics_repo"])


async def test_login_without_consent_keeps_http_semantics(stores: dict) -> None:
    _store, service = _platform()
    email = _email("login-off")
    async with _http(stores, service) as client:
        await client.post("/api/v1/auth/register", json=_register_body(email))
        success = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        )
        failure = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"},
        )
    assert success.status_code == 200
    assert failure.status_code == 401
    assert failure.json()["detail"] == "Invalid email or password."
    assert stores["analytics_repo"].count() == 0


async def test_login_analytics_failure_preserves_http_semantics(stores: dict) -> None:
    _store, service = _platform()
    email = _email("login-boom")
    cookies = _consent_cookies()
    boom = ProductAnalyticsService(_BoomSink())
    async with _http(stores, service, analytics=boom) as client:
        await client.post("/api/v1/auth/register", json=_register_body(email))
        success = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
            cookies=cookies,
        )
        failure = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"},
            cookies=cookies,
        )
    assert success.status_code == 200
    assert success.json()["access_token"]
    assert failure.status_code == 401
    assert failure.json()["detail"] == "Invalid email or password."


async def test_email_change_password_failure_is_not_login_failure(stores: dict) -> None:
    _store, service = _platform()
    email = _email("change")
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        created = await client.post("/api/v1/auth/register", json=_register_body(email))
        changed = await client.post(
            "/api/v1/auth/email-change",
            json={"new_email": _email("next"), "password": "WrongPass123!"},
            headers={"Authorization": f"Bearer {created.json()['access_token']}"},
            cookies=cookies,
        )
    assert changed.status_code == 401
    assert "login_failure" not in _names(stores["analytics_repo"])


async def test_account_deletion_emits_after_success_only(stores: dict) -> None:
    store, service = _platform()
    email = _email("delete")
    cookies = _consent_cookies()
    async with _http(stores, service) as client:
        created = await client.post("/api/v1/auth/register", json=_register_body(email))
        token = created.json()["access_token"]
        user_id = created.json()["user"]["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        rejected = await client.post(
            "/api/v1/auth/account/delete",
            json={"confirmation": "NO", "password": PASSWORD},
            headers=headers,
            cookies=cookies,
        )
        wrong_password = await client.post(
            "/api/v1/auth/account/delete",
            json={"confirmation": ACCOUNT_DELETE_CONFIRMATION, "password": "WrongPass123!"},
            headers=headers,
            cookies=cookies,
        )
        deleted = await client.post(
            "/api/v1/auth/account/delete",
            json={"confirmation": ACCOUNT_DELETE_CONFIRMATION, "password": PASSWORD},
            headers=headers,
            cookies=cookies,
        )
    assert rejected.status_code == 400
    assert wrong_password.status_code == 401
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert store.users.get_by_id(user_id) is None
    limitations = deleted.json()["retained_limitations"]
    assert limitations == list(RETAINED_LIMITATIONS)
    events = _named(stores["analytics_repo"], "account_deleted")
    assert len(events) == 1
    assert events[0].outcome == "completed"
    blob = _public_blob(stores["analytics_repo"])
    assert user_id not in blob
    assert email not in blob
    assert "statutory" not in blob
    for limitation in RETAINED_LIMITATIONS:
        assert limitation in limitations
        assert limitation not in blob


async def test_account_deletion_survives_analytics_failure(stores: dict) -> None:
    store, service = _platform()
    email = _email("delete-boom")
    cookies = _consent_cookies()
    async with _http(stores, service, analytics=ProductAnalyticsService(_BoomSink())) as client:
        created = await client.post("/api/v1/auth/register", json=_register_body(email))
        user_id = created.json()["user"]["user_id"]
        deleted = await client.post(
            "/api/v1/auth/account/delete",
            json={"confirmation": ACCOUNT_DELETE_CONFIRMATION, "password": PASSWORD},
            headers={"Authorization": f"Bearer {created.json()['access_token']}"},
            cookies=cookies,
        )
    assert deleted.status_code == 200
    assert store.users.get_by_id(user_id) is None
    assert stores["analytics_repo"].count() == 0


async def test_authentication_transition_emits_only_for_successful_claim(stores: dict) -> None:
    _store, service = _platform()
    conversations = get_shopping_conversation_repository()
    guest = _guest(f"guest-{uuid4().hex[:8]}")
    created = conversations.create(owner=guest)
    cookies = _consent_cookies()
    cookies[OWNER_COOKIE] = owner_cookie_payload(guest)
    async with _http(stores, service) as client:
        registered = await client.post(
            "/api/v1/auth/register",
            json=_register_body(_email("claim")),
        )
        token = registered.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        missing = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id},
            headers=headers,
            cookies=_consent_cookies(),
        )
        missing_conversation = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": "missing-conversation"},
            headers=headers,
            cookies=cookies,
        )
        claimed = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id, "decision_id": "headphones-standard"},
            headers=headers,
            cookies=cookies,
        )
        again = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id, "decision_id": "headphones-standard"},
            headers=headers,
            cookies=cookies,
        )
    assert missing.json()["claimed"] is False
    assert missing.json()["reason"] == "missing_guest_owner"
    assert missing_conversation.json()["claimed"] is False
    assert missing_conversation.json()["reason"] == "conversation_not_found"
    assert claimed.status_code == 200
    assert claimed.json()["claimed"] is True
    assert claimed.json()["reason"] == "conversation_rebound"
    assert again.json()["claimed"] is False
    transitions = [
        event
        for event in stores["analytics_repo"].list_events()
        if event.event_name == "authentication_transition"
    ]
    assert len(transitions) == 1
    assert transitions[0].identity_kind == "guest"
    assert transitions[0].outcome == "completed"
    blob = _public_blob(stores["analytics_repo"])
    assert created.conversation_id not in blob
    assert registered.json()["user"]["user_id"] not in blob
    assert registered.json()["session"]["session_id"] not in blob
    account = account_owner_from_session(
        user_id=registered.json()["user"]["user_id"],
        session_id=registered.json()["session"]["session_id"],
        expires_at=datetime.fromisoformat(registered.json()["session"]["expires_at"]),
    )
    assert conversations.get_for_owner(created.conversation_id, account) is not None


async def test_immutable_snapshot_claim_does_not_emit(stores: dict) -> None:
    _store, service = _platform()
    conversations = get_shopping_conversation_repository()
    guest = _guest(f"guest-immutable-{uuid4().hex[:8]}")
    created = conversations.create(
        owner=guest,
        decision_context=DecisionContextReference(
            decision_id=DECISION_UUID,
            context_version=1,
            evaluated_product_ids=("sony-wh-1000xm5-canonical",),
            canonical_piqscore_snapshot_sha256="a" * 64,
            recommendation_snapshot_sha256="b" * 64,
        ),
    )

    class _Snapshots:
        def get_latest_for_owner(self, decision_id: str, owner: ConversationOwner):
            if decision_id == DECISION_UUID and owner.has_same_identity(guest):
                return object()
            return None

    cookies = _consent_cookies()
    cookies[OWNER_COOKIE] = owner_cookie_payload(guest)
    async with _http(
        stores,
        service,
        overrides={get_shopping_decision_snapshot_repository: lambda: _Snapshots()},
    ) as client:
        registered = await client.post(
            "/api/v1/auth/register",
            json=_register_body(_email("immutable")),
        )
        refused = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id, "decision_id": DECISION_UUID},
            headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
            cookies=cookies,
        )
    assert refused.status_code == 200
    assert refused.json()["claimed"] is False
    assert refused.json()["reason"] == "immutable_snapshot_owner"
    assert conversations.get_for_owner(created.conversation_id, guest) is not None
    assert "authentication_transition" not in _names(stores["analytics_repo"])


async def test_claim_analytics_failure_keeps_the_claim_result(stores: dict) -> None:
    _store, service = _platform()
    conversations = get_shopping_conversation_repository()
    guest = _guest(f"guest-boom-{uuid4().hex[:8]}")
    created = conversations.create(owner=guest)
    cookies = _consent_cookies()
    cookies[OWNER_COOKIE] = owner_cookie_payload(guest)
    async with _http(stores, service, analytics=ProductAnalyticsService(_BoomSink())) as client:
        registered = await client.post(
            "/api/v1/auth/register",
            json=_register_body(_email("claim-boom")),
        )
        claimed = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id},
            headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
            cookies=cookies,
        )
    assert claimed.status_code == 200
    assert claimed.json()["claimed"] is True
    assert claimed.json()["reason"] == "conversation_rebound"
    assert stores["analytics_repo"].count() == 0


def test_identity_lifecycle_dashboard_windows_and_truncation(stores: dict) -> None:
    repo = stores["analytics_repo"]
    today = datetime(2026, 10, 7, 1, tzinfo=UTC)
    _store_identity_event(repo, name="registration_completed", when=today)
    _store_identity_event(repo, name="login_success", when=datetime(2026, 10, 5, 1, tzinfo=UTC))
    _store_identity_event(repo, name="account_deleted", when=datetime(2026, 9, 20, 1, tzinfo=UTC))
    _store_identity_event(
        repo,
        name="authentication_transition",
        when=datetime(2026, 9, 1, 1, tzinfo=UTC),
    )
    _store_identity_event(
        repo,
        name="login_failure",
        when=datetime(2026, 10, 7, 2, tzinfo=UTC),
        error_code="auth_failed",
    )
    _store_identity_event(
        repo,
        name="login_failure",
        when=datetime(2026, 10, 7, 3, tzinfo=UTC),
        error_code="rate_limited",
    )
    learning = stores["learning"]
    day = learning.summary("1d", environment="test", now=NOW)["metrics"]["identity_lifecycle"]
    week = learning.summary("7d", environment="test", now=NOW)["metrics"]["identity_lifecycle"]
    month = learning.summary("30d", environment="test", now=NOW)["metrics"]["identity_lifecycle"]
    assert day["registration_completed"] == 1
    assert day["login_failure"] == 2
    assert day["login_success"] == 0
    assert day["account_deleted"] == 0
    assert day["authentication_transition"] == 0
    assert day["partial"] is False
    assert week["login_success"] == 1
    assert week["registration_completed"] == 1
    assert week["account_deleted"] == 0
    assert month["account_deleted"] == 1
    assert month["authentication_transition"] == 0
    assert month["login_failure"] == 2
    assert set(day) == {*_IDENTITY_ORDER, "partial"}
    rendered = json.dumps(day)
    assert "@" not in rendered
    assert "user_id" not in rendered
    assert "session" not in rendered
    assert "token" not in rendered
    assert SUBJECT not in rendered
    truncated = ProductLearningDashboardService(
        repo,
        stores["feedback_repo"],
        max_scan_rows=1,
    ).summary("1d", environment="test", now=NOW)
    identity = truncated["metrics"]["identity_lifecycle"]
    assert truncated["coverage"]["truncated"] is True
    assert identity["partial"] is True
    assert identity["login_failure"] == 1
    assert identity["registration_completed"] == 0
    assert "dau" not in json.dumps(truncated["metrics"]["identity_lifecycle"]).lower()
    assert "mau" not in json.dumps(truncated["metrics"]["coverage"]).lower()


def test_sprint_status_boundaries_stay_closed() -> None:
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md").read_text(
        encoding="utf-8"
    )
    identity = (ROOT / "docs/analytics/IDENTITY_LIFECYCLE_EVENTS.md").read_text(encoding="utf-8")
    assert sprint.startswith("# Sprint 39")
    assert "**Status:** IN PROGRESS" in sprint
    assert "not ENGINEERING COMPLETE" in sprint
    assert "Sprint 39.4 does not revise that count" in sprint
    assert "DAU / MAU" in sprint
    for name in _IDENTITY_ORDER:
        assert name in identity
    assert "random server UUIDs" in identity
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
