"""Sprint 40.3 shared rate-limit regressions.

Proves two limiter instances share a counter, identities stay isolated, expiry
opens a new window, concurrent increments cannot pass the limit, sensitive
material is not stored, and staging/production cannot fall back to memory.
"""

from __future__ import annotations

import importlib.util
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.auth.security import RateLimiterHook
from app.auth.service import AuthService
from app.core.config import Settings
from app.core.dependencies import get_rate_limiter, get_user_platform_store
from app.core.validation import validate_settings
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.entities.user_platform import UserSession
from app.domain.exceptions import UserPlatformAuthError, UserPlatformRateLimitError
from app.infrastructure.database.models.rate_limit_counter import RateLimitCounterModel
from app.infrastructure.database.rate_limit_store import SqlRateLimitStore
from app.launch.rate_limit import (
    ConfigurableRateLimiter,
    RateLimitRule,
    classify_path,
)
from app.launch.rate_limit_backend import (
    InMemoryRateLimitStore,
    RateLimitConfigurationError,
    RateLimitUnavailable,
    build_rate_limit_store,
    resolve_rate_limit_backend,
)
from app.launch.rate_limit_keys import client_rate_limit_identity, opaque_subject_key
from app.main import create_app
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
_REVISION = "e5f6a7b8c9d0"
_SECRET = b"sprint40-shared-rate-limit-secret"


class _Clock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now = self._now + timedelta(**kwargs)


class _RecordingStore:
    def __init__(self) -> None:
        self.identities: list[str] = []
        self.inner = InMemoryRateLimitStore()

    def consume(self, *, scope: str, identity: str, limit: int, window_seconds: int, now: datetime):
        self.identities.append(identity)
        return self.inner.consume(
            scope=scope,
            identity=identity,
            limit=limit,
            window_seconds=window_seconds,
            now=now,
        )

    def reset(self, *, scope: str | None = None, identity: str | None = None) -> None:
        self.inner.reset(scope=scope, identity=identity)


class _BoomStore:
    def consume(self, **kwargs: object):
        raise RateLimitUnavailable("down")

    def reset(self, **kwargs: object) -> None:
        raise RateLimitUnavailable("down")


def _request(
    *,
    host: str = "203.0.113.10",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/search",
            "raw_path": b"/api/v1/search",
            "query_string": b"",
            "headers": headers or [],
            "client": (host, 443),
            "server": ("test", 80),
        }
    )


def _engine(path: Path):
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False, "timeout": 30},
        pool_size=8,
        max_overflow=16,
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record) -> None:  # noqa: ARG001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    return engine


def _stores(tmp_path: Path) -> tuple[SqlRateLimitStore, SqlRateLimitStore, object, object]:
    database = tmp_path / "rate-limits.db"
    engine_a = _engine(database)
    engine_b = _engine(database)
    RateLimitCounterModel.__table__.create(engine_a, checkfirst=True)
    factory_a = sessionmaker(bind=engine_a, autoflush=False, expire_on_commit=False)
    factory_b = sessionmaker(bind=engine_b, autoflush=False, expire_on_commit=False)
    return SqlRateLimitStore(factory_a), SqlRateLimitStore(factory_b), engine_a, engine_b


def _rules() -> dict[str, RateLimitRule]:
    return {
        "default": RateLimitRule("default", 2, 60),
        "login": RateLimitRule("login", 1, 60),
    }


def _auth_pair(
    store: SqlRateLimitStore,
    *,
    other: SqlRateLimitStore | None = None,
    max_attempts: int = 1,
    clock: _Clock | None = None,
):
    users = InMemoryUserPlatformStore()
    hook_a = RateLimiterHook(
        max_attempts=max_attempts,
        window_seconds=60,
        clock=clock,
        store=store,
    )
    hook_b = RateLimiterHook(
        max_attempts=max_attempts,
        window_seconds=60,
        clock=clock,
        store=other or store,
    )

    def build(hook: RateLimiterHook) -> AuthService:
        return AuthService(
            users=users.users,
            sessions=users.sessions,
            profiles=users.profiles,
            password_resets=users.password_resets,
            email_verifications=users.email_verifications,
            email_changes=users.email_changes,
            rate_limiter=hook,
            clock=clock,
        )

    return build(hook_a), build(hook_b)


def test_two_sql_limiters_share_a_counter_and_isolate_identities(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _stores(tmp_path)
    try:
        limiter_a = ConfigurableRateLimiter(_rules(), store=store_a)
        limiter_b = ConfigurableRateLimiter(_rules(), store=store_b)
        assert limiter_a.check("default", "ip:203.0.113.1").allowed is True
        second = limiter_b.check("default", "ip:203.0.113.1")
        assert second.allowed is True
        assert second.remaining == 0
        blocked = limiter_a.check("default", "ip:203.0.113.1")
        assert blocked.allowed is False
        assert limiter_b.check("default", "ip:203.0.113.1").allowed is False
        other = limiter_b.check("default", "ip:203.0.113.2")
        assert other.allowed is True
        assert limiter_a.check("login", "ip:203.0.113.1").allowed is True
        assert limiter_b.check("login", "ip:203.0.113.1").allowed is False
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_expiry_opens_a_new_shared_window_and_purges_the_old_row(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _stores(tmp_path)
    clock = _Clock(datetime(2026, 10, 9, 12, 0, tzinfo=UTC))
    try:
        limiter_a = ConfigurableRateLimiter(
            {"default": RateLimitRule("default", 1, 30)},
            store=store_a,
            clock=clock,
        )
        limiter_b = ConfigurableRateLimiter(
            {"default": RateLimitRule("default", 1, 30)},
            store=store_b,
            clock=clock,
        )
        assert limiter_a.check("default", "ip:old").allowed is True
        assert limiter_b.check("default", "ip:old").allowed is False
        clock.advance(seconds=31)
        assert limiter_b.check("default", "ip:new").allowed is True
        assert limiter_a.check("default", "ip:old").allowed is True
        with engine_b.connect() as conn:
            rows = conn.execute(
                select(RateLimitCounterModel.identity_key, RateLimitCounterModel.hits)
            ).all()
        identities = {row[0] for row in rows}
        assert "ip:old" in identities
        assert all(row[1] == 1 for row in rows if row[0] == "ip:old")
        # The first window for ip:old was expired by the later consume and replaced.
        assert sum(1 for row in rows if row[0] == "ip:old") == 1
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_concurrent_increments_cannot_exceed_the_shared_limit(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _stores(tmp_path)
    stores = (store_a, store_b)
    allowed: list[bool] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    workers = 16
    barrier = threading.Barrier(workers)
    now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=10)
            decision = stores[index % 2].consume(
                scope="default",
                identity="ip:race",
                limit=5,
                window_seconds=60,
                now=now,
            )
            with lock:
                allowed.append(decision.allowed)
        except BaseException as exc:  # noqa: BLE001 — the assertion reports the thread error
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(workers)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert errors == []
        assert not any(thread.is_alive() for thread in threads)
        assert sum(1 for item in allowed if item) == 5
        assert sum(1 for item in allowed if not item) == workers - 5
        with engine_a.connect() as conn:
            hits = conn.execute(
                select(RateLimitCounterModel.hits).where(
                    RateLimitCounterModel.identity_key == "ip:race"
                )
            ).scalar_one()
        assert hits == 5
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_sensitive_http_identities_omit_tokens_cookies_and_account_ids() -> None:
    token = "super-secret-bearer-token-value"
    cookie = "v1.owner-cookie-payload.signature"
    future = datetime.now(UTC) + timedelta(hours=1)
    public = client_rate_limit_identity(
        _request(),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: None,
        secret=_SECRET,
    )
    assert public == "ip:203.0.113.10"
    unverified = client_rate_limit_identity(
        _request(
            headers=[
                (b"authorization", f"Bearer {token}".encode()),
                (b"cookie", f"piqsavi_decision_owner={cookie}".encode()),
            ]
        ),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: None,
        secret=_SECRET,
    )
    assert unverified == "ip:203.0.113.10"
    assert "tok:" not in unverified
    assert token not in unverified
    assert token[:8] not in unverified
    assert cookie not in unverified

    session = SimpleNamespace(
        user_id="user-42",
        revoked=False,
        expires_at=future,
    )
    verified = client_rate_limit_identity(
        _request(headers=[(b"authorization", f"Bearer {token}".encode())]),
        session_lookup=lambda token_hash: (
            session if token_hash == AuthService.hash_token(token) else None
        ),
        owner_resolver=lambda _request: None,
        secret=_SECRET,
    )
    assert verified == opaque_subject_key("acct", "user-42", secret=_SECRET)
    assert token not in verified
    assert "user-42" not in verified
    assert token[:8] not in verified

    owner = ConversationOwner(
        principal_type="account",
        principal_id="account-principal",
        session_id="session-secret",
        expires_at=future,
    )
    from_cookie = client_rate_limit_identity(
        _request(headers=[(b"cookie", f"piqsavi_decision_owner={cookie}".encode())]),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: owner,
        secret=_SECRET,
    )
    assert from_cookie.startswith("acct:")
    assert cookie not in from_cookie
    assert "account-principal" not in from_cookie
    assert "session-secret" not in from_cookie

    guest = ConversationOwner(
        principal_type="guest",
        principal_id="guest-secret",
        session_id="guest-session",
        expires_at=future,
    )
    guest_identity = client_rate_limit_identity(
        _request(host="198.51.100.8"),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: guest,
        secret=_SECRET,
    )
    assert guest_identity == "ip:198.51.100.8"
    assert "guest-secret" not in guest_identity


def test_auth_abuse_keys_do_not_contain_emails_passwords_or_tokens() -> None:
    recording = _RecordingStore()
    hook = RateLimiterHook(max_attempts=5, window_seconds=60, store=recording)
    users = InMemoryUserPlatformStore()
    auth = AuthService(
        users=users.users,
        sessions=users.sessions,
        profiles=users.profiles,
        password_resets=users.password_resets,
        email_verifications=users.email_verifications,
        email_changes=users.email_changes,
        rate_limiter=hook,
    )
    email = "Person.Secret@Example.com"
    password = "ValidPass123!"
    result = auth.register(email=email, password=password, display_name="Person")
    auth.request_password_reset(email)
    auth.request_email_verification_by_email(email)
    with pytest.raises(UserPlatformAuthError):
        auth.request_email_change(
            result.access_token,
            new_email="next.secret@example.com",
            password="not-the-password",
        )
    normalized = "person.secret@example.com"
    forbidden = (
        email,
        normalized,
        password,
        "not-the-password",
        result.access_token,
        "next.secret@example.com",
        result.user.user_id,
    )
    assert recording.identities
    for identity in recording.identities:
        for secret in forbidden:
            assert secret not in identity
        assert "@" not in identity
    assert opaque_subject_key("register", normalized) in recording.identities
    assert opaque_subject_key("login", normalized) not in recording.identities
    assert opaque_subject_key("password_reset", normalized) in recording.identities
    assert opaque_subject_key("email_verification", normalized) in recording.identities
    assert opaque_subject_key("email_change", result.user.user_id) in recording.identities


def test_two_auth_services_share_login_registration_and_email_limits(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _stores(tmp_path)
    try:
        auth_a, auth_b = _auth_pair(store_a, other=store_b, max_attempts=1)
        email = "shared.limit@example.com"
        password = "ValidPass123!"
        registered = auth_a.register(email=email, password=password, display_name="Shared")
        with pytest.raises(UserPlatformRateLimitError):
            auth_b.register(email=email, password=password, display_name="Shared")
        with pytest.raises(UserPlatformAuthError):
            auth_a.login(email="other.person@example.com", password="nope")
        with pytest.raises(UserPlatformRateLimitError):
            auth_b.login(email="other.person@example.com", password="nope")
        auth_a.request_password_reset("reset.me@example.com")
        with pytest.raises(UserPlatformRateLimitError):
            auth_b.request_password_reset("reset.me@example.com")
        auth_a.request_email_verification_by_email("verify.me@example.com")
        with pytest.raises(UserPlatformRateLimitError):
            auth_b.request_email_verification_by_email("verify.me@example.com")
        with pytest.raises(UserPlatformAuthError):
            auth_a.request_email_change(
                registered.access_token,
                new_email="changed@example.com",
                password="wrong-password",
            )
        with pytest.raises(UserPlatformRateLimitError):
            auth_b.request_email_change(
                registered.access_token,
                new_email="changed@example.com",
                password="wrong-password",
            )
        # A different email is not blocked by the other identity's login counter.
        with pytest.raises(UserPlatformAuthError):
            auth_b.login(email="isolated.person@example.com", password="nope")
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_auth_window_expiry_is_shared(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _stores(tmp_path)
    clock = _Clock(datetime(2026, 10, 9, 8, 0, tzinfo=UTC))
    try:
        auth_a, auth_b = _auth_pair(store_a, other=store_b, max_attempts=1, clock=clock)
        email = "expiry.person@example.com"
        with pytest.raises(UserPlatformAuthError):
            auth_a.login(email=email, password="nope")
        with pytest.raises(UserPlatformRateLimitError):
            auth_b.login(email=email, password="nope")
        clock.advance(seconds=61)
        with pytest.raises(UserPlatformAuthError):
            auth_b.login(email=email, password="nope")
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_successful_login_reset_is_visible_to_the_other_instance(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _stores(tmp_path)
    try:
        users = InMemoryUserPlatformStore()
        from app.user.fixtures import DEMO_PASSWORD, seed_demo_users

        seed_demo_users(users)
        hook_a = RateLimiterHook(max_attempts=2, window_seconds=60, store=store_a)
        hook_b = RateLimiterHook(max_attempts=2, window_seconds=60, store=store_b)
        auth_a = AuthService(
            users=users.users,
            sessions=users.sessions,
            profiles=users.profiles,
            password_resets=users.password_resets,
            email_verifications=users.email_verifications,
            email_changes=users.email_changes,
            rate_limiter=hook_a,
        )
        auth_b = AuthService(
            users=users.users,
            sessions=users.sessions,
            profiles=users.profiles,
            password_resets=users.password_resets,
            email_verifications=users.email_verifications,
            email_changes=users.email_changes,
            rate_limiter=hook_b,
        )
        email = "student@example.com"
        with pytest.raises(UserPlatformAuthError):
            auth_a.login(email=email, password="wrong-password")
        auth_a.login(email=email, password=DEMO_PASSWORD)
        with pytest.raises(UserPlatformAuthError):
            auth_b.login(email=email, password="wrong-password")
        with pytest.raises(UserPlatformAuthError):
            auth_b.login(email=email, password="wrong-password")
        with pytest.raises(UserPlatformRateLimitError):
            auth_a.login(email=email, password="wrong-password")
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_staging_and_production_cannot_select_memory() -> None:
    assert resolve_rate_limit_backend(Settings(APP_ENV="development")) == "memory"
    assert (
        resolve_rate_limit_backend(Settings(APP_ENV="development", RATE_LIMIT_BACKEND="memory"))
        == "memory"
    )
    assert (
        resolve_rate_limit_backend(Settings(APP_ENV="development", RATE_LIMIT_BACKEND="postgres"))
        == "postgres"
    )
    assert resolve_rate_limit_backend(Settings(APP_ENV="staging")) == "postgres"
    assert resolve_rate_limit_backend(Settings(APP_ENV="production")) == "postgres"
    assert (
        resolve_rate_limit_backend(Settings(APP_ENV="production", RATE_LIMIT_BACKEND="postgres"))
        == "postgres"
    )
    for env in ("staging", "production"):
        with pytest.raises(RateLimitConfigurationError):
            resolve_rate_limit_backend(Settings(APP_ENV=env, RATE_LIMIT_BACKEND="memory"))
        result = validate_settings(Settings(APP_ENV=env, RATE_LIMIT_BACKEND="memory"))
        assert any("RATE_LIMIT_BACKEND=memory is forbidden" in error for error in result.errors)
    assert isinstance(build_rate_limit_store(Settings(APP_ENV="staging")), SqlRateLimitStore)
    assert isinstance(build_rate_limit_store(Settings(APP_ENV="production")), SqlRateLimitStore)
    assert isinstance(
        build_rate_limit_store(Settings(APP_ENV="development")),
        InMemoryRateLimitStore,
    )


def test_staging_identity_hmac_does_not_fall_back_to_the_development_key(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "app_secret_key", "")
    with pytest.raises(RateLimitUnavailable):
        opaque_subject_key("login", "person@example.com")
    monkeypatch.setattr(settings, "app_secret_key", "changeme")
    with pytest.raises(RateLimitUnavailable):
        opaque_subject_key("login", "person@example.com")


def test_missing_shared_table_does_not_allow_the_request(tmp_path: Path) -> None:
    engine = _engine(tmp_path / "empty.db")
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    store = SqlRateLimitStore(factory)
    limiter = ConfigurableRateLimiter(
        {"default": RateLimitRule("default", 10, 60)},
        store=store,
    )
    try:
        decision = limiter.check("default", "ip:203.0.113.4")
        assert decision.allowed is False
        assert decision.unavailable is True
        again = limiter.check("default", "ip:203.0.113.4")
        assert again.allowed is False
        assert again.unavailable is True
        hook = RateLimiterHook(max_attempts=5, store=store)
        assert hook.check("login:opaque") is False
    finally:
        engine.dispose()


def test_store_exception_does_not_bypass_http_or_health() -> None:
    limiter = get_rate_limiter()
    previous_store = limiter._store
    previous_enabled = limiter.enabled
    limiter.set_enabled(True)
    limiter._store = _BoomStore()
    app = create_app()
    try:
        client = TestClient(app)
        health = client.get("/health")
        assert health.status_code == 200
        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": "a@b.com", "password": "x"},
        )
        assert blocked.status_code == 503
        body = blocked.json()
        assert body["error"] == "rate_limit_unavailable"
        assert body["status_code"] == 503
        assert body["details"]["bucket"] == "login"
        assert "X-RateLimit-Remaining" not in blocked.headers
        assert blocked.headers["Retry-After"] == "1"
    finally:
        limiter._store = previous_store
        limiter.set_enabled(previous_enabled)


def test_existing_429_body_and_headers_stay_in_place() -> None:
    limiter = get_rate_limiter()
    original = limiter._rules["login"]
    limiter._rules["login"] = RateLimitRule("login", 2, 60)
    limiter.reset()
    limiter.set_enabled(True)
    app = create_app()
    try:
        client = TestClient(app)
        first = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
        assert first.status_code != 429
        assert first.headers["X-RateLimit-Limit"] == "2"
        assert first.headers["X-RateLimit-Bucket"] == "login"
        assert int(first.headers["X-RateLimit-Remaining"]) == 1
        client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
        blocked = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
        assert blocked.status_code == 429
        body = blocked.json()
        assert body["error"] == "rate_limited"
        assert body["status_code"] == 429
        assert body["detail"] == "Rate limit exceeded for login"
        assert body["details"]["bucket"] == "login"
        assert body["details"]["limit"] == 2
        assert body["details"]["retry_after_seconds"] >= 1
        assert blocked.headers["Retry-After"] == str(body["details"]["retry_after_seconds"])
        assert blocked.headers["X-RateLimit-Limit"] == "2"
        assert blocked.headers["X-RateLimit-Remaining"] == "0"
        assert blocked.headers["X-RateLimit-Bucket"] == "login"
    finally:
        limiter._rules["login"] = original
        limiter.reset()
        limiter.set_enabled(True)


def test_buckets_still_classify() -> None:
    assert classify_path("POST", "/api/v1/auth/login") == "login"
    assert classify_path("POST", "/api/v1/auth/register") == "registration"
    assert classify_path("POST", "/api/v1/auth/password-reset") == "auth_email"
    assert classify_path("POST", "/api/v1/auth/verify-email") == "auth_email"
    assert classify_path("POST", "/api/v1/auth/email-change") == "auth_email"
    assert classify_path("POST", "/api/v1/early-access/events") == "early_access_events"
    assert classify_path("POST", "/api/v1/early-access") == "registration"
    assert classify_path("GET", "/api/v1/affiliate/report") == "affiliate"
    assert classify_path("GET", "/api/v1/merchants/org-x") == "merchant"
    assert classify_path("GET", "/api/v1/marketplace/search") == "search"
    assert classify_path("GET", "/api/v1/recommendations/for-you") == "recommendations"
    assert classify_path("GET", "/api/v1/health") == "default"


def test_verified_bearer_is_not_keyed_by_a_token_prefix() -> None:
    token = "middleware-bearer-token-value-not-prefix"
    store = get_user_platform_store()
    now = datetime.now(UTC)
    store.sessions.save(
        UserSession(
            session_id="sprint40-session",
            user_id="user-middleware",
            token_hash=AuthService.hash_token(token),
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
    )
    limiter = get_rate_limiter()
    seen: list[str] = []
    previous = limiter._store.consume

    def spy(**kwargs):
        seen.append(kwargs["identity"])
        return previous(**kwargs)

    limiter._store.consume = spy
    limiter.set_enabled(True)
    limiter.reset()
    app = create_app()
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/launch/performance",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code != 429
        assert seen
        identity = seen[-1]
        assert identity.startswith("acct:")
        assert token not in identity
        assert token[:8] not in identity
        assert "tok:" not in identity
        assert "user-middleware" not in identity
    finally:
        limiter._store.consume = previous
        limiter.reset()
        store.sessions.revoke("sprint40-session")


def _revision_module():
    path = ROOT / "alembic" / "versions" / "e5f6a7b8c9d0_sprint40_rate_limit_counters.py"
    spec = importlib.util.spec_from_file_location("sprint40_rate_limit_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sprint_40_3_record_does_not_close_the_sprint() -> None:
    evidence = (
        ROOT / "docs/roadmap/evidence/SPRINT_40_3_DISTRIBUTED_RATE_LIMIT_2026-10-09.md"
    ).read_text(encoding="utf-8")
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )
    assert "**Status:** Planned" in sprint
    assert "81a4d6aef4e9b49bf3648245190588f87c51c152" in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "Not ENGINEERING COMPLETE" in evidence
    assert "No Included requirement is PROVEN." in evidence
    assert "Abuse controls exercised" in evidence
    assert "is absent" in evidence
    assert "CSRF not enforced" in evidence
    assert "CSP `'unsafe-inline'`" in evidence
    assert "URL validation / SSRF" in evidence
    assert "R6 stays PARTIAL" in evidence
    assert "Class C count remains 19" in evidence
    assert "selected next engineering slice remains NONE" in evidence
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "No deploy was performed." in evidence
    assert "Routing stays 0." in evidence
    assert "not closed" in evidence
    assert "Sprint 40.3" in sprint


def test_rate_limit_migration_upgrades_and_rolls_back(tmp_path: Path) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [_REVISION]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == "d4e5f6a7b8c9"
    revision_module = _revision_module()

    engine = create_engine(f"sqlite:///{tmp_path / 'migrated.db'}")
    try:
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            revision_module.upgrade()
        assert "rate_limit_counters" in inspect(engine).get_table_names()
        columns = {column["name"] for column in inspect(engine).get_columns("rate_limit_counters")}
        assert columns == {
            "scope",
            "identity_key",
            "window_started_ms",
            "hits",
            "expires_at_ms",
        }
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        store = SqlRateLimitStore(factory)
        assert store.consume(
            scope="default",
            identity="ip:migrated",
            limit=1,
            window_seconds=60,
            now=datetime.now(UTC),
        ).allowed
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            revision_module.downgrade()
        assert "rate_limit_counters" not in inspect(engine).get_table_names()
        with pytest.raises(RateLimitUnavailable):
            store.consume(
                scope="default",
                identity="ip:migrated",
                limit=1,
                window_seconds=60,
                now=datetime.now(UTC),
            )
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            revision_module.upgrade()
        assert store.consume(
            scope="default",
            identity="ip:migrated",
            limit=1,
            window_seconds=60,
            now=datetime.now(UTC),
        ).allowed
    finally:
        engine.dispose()
