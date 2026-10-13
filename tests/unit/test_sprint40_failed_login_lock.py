"""Durable failed-login lock.

Failures survive the 60-second auth window. Crossing the threshold sets
``locked_until`` from that event, not from the first failure. Clocks are
advanced directly. These tests do not sleep.
"""

from __future__ import annotations

import importlib.util
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.auth.security import AuditLogger, RateLimiterHook
from app.auth.service import AuthService
from app.core.config import Settings
from app.domain.entities.user_platform import User
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformRateLimitError,
)
from app.infrastructure.database.failed_login_lock_store import SqlFailedLoginLockStore
from app.infrastructure.database.models.failed_login_lock import FailedLoginLockModel
from app.launch.failed_login_lock import (
    FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    FAILED_LOGIN_LOCK_DURATION_SECONDS,
    FAILED_LOGIN_LOCK_THRESHOLD,
    LOGIN_ATTEMPT_LIMIT_MESSAGE,
    FailedLoginLock,
    FailedLoginLockState,
    FailedLoginLockUnavailable,
    InMemoryFailedLoginLockStore,
    build_failed_login_lock_store,
    epoch_ms,
)
from app.launch.rate_limit_backend import (
    InMemoryRateLimitStore,
    RateLimitConfigurationError,
)
from app.launch.rate_limit_keys import opaque_subject_key
from app.user.memory import InMemoryUserPlatformStore
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
_REVISION = "f6a7b8c9d0e1"
EMAIL = "lock.user@example.com"
UNKNOWN_EMAIL = "ghost.user@example.com"
PASSWORD = "CorrectPass123!"
WRONG = "WrongPass123!"
_START = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
_PUBLIC_AUTH = "Invalid email or password."


class _Clock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now = self._now + timedelta(**kwargs)


class FastHasher:
    def __init__(self) -> None:
        self.verify_calls = 0

    def hash(self, password: str) -> str:
        return f"fast:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        self.verify_calls += 1
        return password_hash == f"fast:{password}"


class RecordingStore:
    def __init__(self, inner: InMemoryFailedLoginLockStore) -> None:
        self.inner = inner
        self.records = 0
        self.clears = 0

    def get(self, identity: str):
        return self.inner.get(identity)

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ):
        self.records += 1
        return self.inner.record_failure(
            identity,
            now=now,
            threshold=threshold,
            lock_duration_seconds=lock_duration_seconds,
            failure_retention_seconds=failure_retention_seconds,
        )

    def clear(
        self,
        identity: str,
        *,
        now: datetime | None = None,
        failure_retention_seconds: int | None = None,
    ) -> None:
        self.clears += 1
        self.inner.clear(
            identity,
            now=now,
            failure_retention_seconds=failure_retention_seconds,
        )


class UnavailableStore:
    def get(self, identity: str):
        raise FailedLoginLockUnavailable("down")

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ):
        raise FailedLoginLockUnavailable("down")

    def clear(
        self,
        identity: str,
        *,
        now: datetime | None = None,
        failure_retention_seconds: int | None = None,
    ) -> None:
        raise FailedLoginLockUnavailable("down")


class RecordUnavailable:
    def get(self, identity: str):
        return None

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ):
        raise FailedLoginLockUnavailable("down")

    def clear(
        self,
        identity: str,
        *,
        now: datetime | None = None,
        failure_retention_seconds: int | None = None,
    ) -> None:
        raise AssertionError("clear should not run when recording fails")


class ClearUnavailable:
    def get(self, identity: str):
        return None

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ):
        raise AssertionError("record should not run on the success path")

    def clear(
        self,
        identity: str,
        *,
        now: datetime | None = None,
        failure_retention_seconds: int | None = None,
    ) -> None:
        raise FailedLoginLockUnavailable("down")


def _key(email: str) -> str:
    return opaque_subject_key("login", email.strip().lower())


def _platform(*emails: str) -> InMemoryUserPlatformStore:
    platform = InMemoryUserPlatformStore()
    now = _START
    for email in emails or (EMAIL,):
        platform.users.save(
            User(
                user_id=f"user-{email}",
                email=email,
                password_hash=f"fast:{PASSWORD}",
                display_name="Lock User",
                is_active=True,
                email_verified=True,
                created_at=now,
                updated_at=now,
            )
        )
    return platform


def _service(
    *,
    platform: InMemoryUserPlatformStore | None = None,
    clock: _Clock | None = None,
    login_lock: FailedLoginLock | None = None,
    max_attempts: int = 100,
    window_seconds: int = 60,
    threshold: int = 3,
    lock_duration_seconds: int = FAILED_LOGIN_LOCK_DURATION_SECONDS,
    hasher: FastHasher | None = None,
    audit: AuditLogger | None = None,
) -> tuple[
    AuthService,
    FailedLoginLock,
    FastHasher,
    InMemoryUserPlatformStore,
    _Clock,
    AuditLogger,
]:
    clock = clock or _Clock(_START)
    platform = platform or _platform()
    hasher = hasher or FastHasher()
    audit = audit or AuditLogger()
    if login_lock is None:
        login_lock = FailedLoginLock(
            store=InMemoryFailedLoginLockStore(),
            threshold=threshold,
            lock_duration_seconds=lock_duration_seconds,
        )
    auth = AuthService(
        users=platform.users,
        sessions=platform.sessions,
        profiles=platform.profiles,
        password_resets=platform.password_resets,
        email_verifications=platform.email_verifications,
        password_hasher=hasher,
        rate_limiter=RateLimiterHook(
            max_attempts=max_attempts,
            window_seconds=window_seconds,
            clock=clock,
        ),
        login_lock=login_lock,
        audit=audit,
        clock=clock,
    )
    return auth, login_lock, hasher, platform, clock, audit


def _fail(auth: AuthService, count: int = 1, *, email: str = EMAIL, password: str = WRONG) -> None:
    for _ in range(count):
        with pytest.raises(UserPlatformAuthError, match=_PUBLIC_AUTH):
            auth.login(email=email, password=password)


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


def _sql_stores(
    tmp_path: Path,
) -> tuple[SqlFailedLoginLockStore, SqlFailedLoginLockStore, object, object]:
    database = tmp_path / "failed-login-locks.db"
    engine_a = _engine(database)
    engine_b = _engine(database)
    FailedLoginLockModel.__table__.create(engine_a, checkfirst=True)
    factory_a = sessionmaker(bind=engine_a, autoflush=False, expire_on_commit=False)
    factory_b = sessionmaker(bind=engine_b, autoflush=False, expire_on_commit=False)
    return (
        SqlFailedLoginLockStore(factory_a),
        SqlFailedLoginLockStore(factory_b),
        engine_a,
        engine_b,
    )


def _revision_module():
    path = ROOT / "alembic" / "versions" / "f6a7b8c9d0e1_create_failed_login_locks.py"
    spec = importlib.util.spec_from_file_location("failed_login_lock_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_beta_default_is_twenty_failures_then_fifteen_minutes() -> None:
    assert FAILED_LOGIN_LOCK_THRESHOLD == 20
    assert FAILED_LOGIN_LOCK_DURATION_SECONDS == 15 * 60
    assert FAILED_LOGIN_FAILURE_RETENTION_SECONDS == 15 * 60
    assert FAILED_LOGIN_FAILURE_RETENTION_SECONDS > 60
    backend = (ROOT / "app/launch/rate_limit_backend.py").read_text(encoding="utf-8")
    assert "max_attempts=20" in backend
    assert "window_seconds=60" in backend
    lock = FailedLoginLock(store=InMemoryFailedLoginLockStore())
    assert lock.threshold == 20
    assert lock.lock_duration_seconds == 900
    assert lock.failure_retention_seconds == 900


def test_failures_accumulate_after_the_short_window_expires() -> None:
    clock = _Clock(_START)
    auth, login_lock, _hasher, _platform_store, _clock, _audit = _service(
        clock=clock,
        max_attempts=2,
        window_seconds=60,
        threshold=4,
    )
    _fail(auth, 2)
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        auth.login(email=EMAIL, password=WRONG)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 2

    clock.advance(seconds=61)
    state_after_window = login_lock.store.get(_key(EMAIL))
    assert state_after_window is not None
    assert state_after_window.failure_count == 2
    assert state_after_window.locked_until is None

    _fail(auth, 1)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 3
    clock.advance(seconds=1)
    _fail(auth, 1)
    state = login_lock.store.get(_key(EMAIL))
    assert state.failure_count == 4
    assert state.locked_until == _START + timedelta(seconds=62 + FAILED_LOGIN_LOCK_DURATION_SECONDS)


def test_threshold_sets_locked_until_from_the_lock_event() -> None:
    clock = _Clock(_START)
    duration = 900
    auth, login_lock, _hasher, platform, _clock, _audit = _service(
        clock=clock,
        threshold=3,
        lock_duration_seconds=duration,
    )
    _fail(auth, 1)
    clock.advance(seconds=800)
    _fail(auth, 1)
    clock.advance(seconds=50)
    before_calls = auth._hasher.verify_calls
    _fail(auth, 1)
    lock_event = _START + timedelta(seconds=850)
    state = login_lock.store.get(_key(EMAIL))
    assert state.failure_count == 3
    assert state.locked_until == lock_event + timedelta(seconds=duration)
    assert state.locked_until != _START + timedelta(seconds=duration)
    user = platform.users.get_by_email(EMAIL)
    assert user is not None
    assert user.is_active is True

    clock.advance(seconds=duration - 1)
    auth._hasher.verify_calls = 0
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        auth.login(email=EMAIL, password=PASSWORD)
    assert auth._hasher.verify_calls == 0
    assert before_calls >= 1
    assert platform.sessions.list_for_user(user.user_id) == []
    assert login_lock.store.get(_key(EMAIL)).locked_until == state.locked_until

    clock.advance(seconds=1)
    result = auth.login(email=EMAIL, password=PASSWORD)
    assert result.access_token
    assert login_lock.store.get(_key(EMAIL)) is None


def test_later_failures_do_not_extend_an_active_lock() -> None:
    clock = _Clock(_START)
    store = InMemoryFailedLoginLockStore()
    lock = FailedLoginLock(store=store, threshold=2, lock_duration_seconds=900)
    lock.record_failure(_key(EMAIL), now=clock())
    clock.advance(seconds=10)
    established = lock.record_failure(_key(EMAIL), now=clock())
    assert established.locked_until == _START + timedelta(seconds=10 + 900)
    clock.advance(seconds=30)
    again = lock.record_failure(_key(EMAIL), now=clock())
    assert again.locked_until == established.locked_until
    assert again.failure_count == 3


def test_correct_password_is_blocked_until_expiry_then_a_fresh_sequence_starts() -> None:
    clock = _Clock(_START)
    auth, login_lock, hasher, platform, _clock, _audit = _service(
        clock=clock,
        threshold=2,
        lock_duration_seconds=900,
    )
    _fail(auth, 2)
    hasher.verify_calls = 0
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        auth.login(email=EMAIL, password=PASSWORD)
    assert hasher.verify_calls == 0
    assert platform.sessions.list_for_user(f"user-{EMAIL}") == []

    clock.advance(seconds=900)
    _fail(auth, 1)
    state = login_lock.store.get(_key(EMAIL))
    assert state.failure_count == 1
    assert state.locked_until is None
    result = auth.login(email=EMAIL, password=PASSWORD)
    assert result.access_token
    assert login_lock.store.get(_key(EMAIL)) is None


def test_successful_login_clears_durable_failures_before_the_threshold() -> None:
    clock = _Clock(_START)
    auth, login_lock, _hasher, _platform_store, _clock, _audit = _service(
        clock=clock,
        max_attempts=5,
        threshold=4,
    )
    _fail(auth, 3)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 3
    auth.login(email=EMAIL, password=PASSWORD)
    assert login_lock.store.get(_key(EMAIL)) is None
    _fail(auth, 3)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 3
    assert login_lock.is_locked(_key(EMAIL), now=clock()) is False
    with pytest.raises(UserPlatformAuthError):
        auth.login(email=EMAIL, password=WRONG)
    assert login_lock.store.get(_key(EMAIL)).locked_until is not None


def test_unknown_and_known_failures_share_the_public_error() -> None:
    auth, login_lock, _hasher, platform, _clock, audit = _service(threshold=2)
    with pytest.raises(UserPlatformAuthError) as unknown:
        auth.login(email=UNKNOWN_EMAIL, password=WRONG)
    with pytest.raises(UserPlatformAuthError) as known:
        auth.login(email=EMAIL, password=WRONG)
    user = platform.users.get_by_email(EMAIL)
    assert user is not None
    from dataclasses import replace

    platform.users.save(replace(user, is_active=False))
    with pytest.raises(UserPlatformAuthError) as inactive:
        auth.login(email=EMAIL, password=PASSWORD)
    assert str(unknown.value) == str(known.value) == str(inactive.value) == _PUBLIC_AUTH
    assert type(unknown.value) is type(known.value) is type(inactive.value)
    for message in (str(unknown.value), str(known.value), str(inactive.value)):
        lowered = message.lower()
        assert "exist" not in lowered
        assert "locked" not in lowered
        assert "2" not in message

    _fail(auth, 1, email=UNKNOWN_EMAIL)
    with pytest.raises(UserPlatformRateLimitError) as unknown_locked:
        auth.login(email=UNKNOWN_EMAIL, password=PASSWORD)
    # Known email already recorded a bad password and the inactive attempt.
    with pytest.raises(UserPlatformRateLimitError) as known_locked:
        auth.login(email=EMAIL, password=PASSWORD)
    assert str(unknown_locked.value) == str(known_locked.value) == LOGIN_ATTEMPT_LIMIT_MESSAGE
    assert "exist" not in str(known_locked.value).lower()
    assert "locked" not in str(known_locked.value).lower()
    assert platform.users.get_by_email(EMAIL).is_active is False
    locked_audits = [item for item in audit.recent() if item.detail == "login_locked"]
    assert locked_audits
    for security_event in locked_audits:
        assert "email" not in security_event.metadata
        assert EMAIL not in str(security_event.metadata)
        assert UNKNOWN_EMAIL not in str(security_event.metadata)
        assert PASSWORD not in str(security_event.metadata)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 2


def test_normalized_email_shares_one_opaque_identity(tmp_path: Path) -> None:
    store, _other, engine_a, engine_b = _sql_stores(tmp_path)
    try:
        clock = _Clock(_START)
        auth, _lock, _hasher, _platform_store, _clock, _audit = _service(
            clock=clock,
            login_lock=FailedLoginLock(store=store, threshold=3, lock_duration_seconds=900),
        )
        _fail(auth, 1, email="  Lock.User@Example.com ")
        _fail(auth, 1, email="lock.user@example.com")
        identity = _key(EMAIL)
        state = store.get(identity)
        assert state is not None
        assert state.failure_count == 2
        assert EMAIL not in identity
        assert "@" not in identity
        assert identity.startswith("login:")
        digest = identity.split(":", 1)[1]
        assert len(digest) == 64
        int(digest, 16)
        with engine_a.connect() as conn:
            rows = conn.execute(select(FailedLoginLockModel)).all()
        assert len(rows) == 1
        blob = " ".join(str(value) for value in rows[0])
        assert EMAIL not in blob
        assert "Lock.User@Example.com" not in blob
        assert PASSWORD not in blob
        assert WRONG not in blob
        columns = {column["name"] for column in inspect(engine_a).get_columns("failed_login_locks")}
        assert columns == {
            "identity_key",
            "failure_count",
            "locked_until_ms",
            "first_failure_ms",
            "last_failure_ms",
        }
        assert "email" not in columns
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_two_sql_services_share_lock_state_across_instances(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _sql_stores(tmp_path)
    restarted = None
    try:
        clock = _Clock(_START)
        platform = _platform()
        auth_a, _lock_a, _hasher_a, _platform_a, _clock_a, _audit_a = _service(
            platform=platform,
            clock=clock,
            login_lock=FailedLoginLock(store=store_a, threshold=3, lock_duration_seconds=900),
        )
        auth_b, _lock_b, hasher_b, _platform_b, _clock_b, _audit_b = _service(
            platform=platform,
            clock=clock,
            login_lock=FailedLoginLock(store=store_b, threshold=3, lock_duration_seconds=900),
        )
        _fail(auth_a, 3)
        hasher_b.verify_calls = 0
        with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
            auth_b.login(email=EMAIL, password=PASSWORD)
        assert hasher_b.verify_calls == 0
        engine_a.dispose()
        engine_b.dispose()
        restarted, _ignored, engine_c, engine_d = _sql_stores(tmp_path)
        engine_a = engine_c
        engine_b = engine_d
        assert restarted.get(_key(EMAIL)).locked_until == _START + timedelta(seconds=900)
        clock.advance(seconds=900)
        auth_c, _lock_c, _hasher_c, _platform_c, _clock_c, _audit_c = _service(
            platform=platform,
            clock=clock,
            login_lock=FailedLoginLock(store=restarted, threshold=3, lock_duration_seconds=900),
        )
        result = auth_c.login(email=EMAIL, password=PASSWORD)
        assert result.access_token
        assert restarted.get(_key(EMAIL)) is None
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_concurrent_sql_failures_do_not_lose_increments_or_bypass_the_threshold(
    tmp_path: Path,
) -> None:
    store_a, store_b, engine_a, engine_b = _sql_stores(tmp_path)
    stores = (store_a, store_b)
    now = _START
    threshold = 10
    workers = 40
    barrier = threading.Barrier(workers)
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=10)
            stores[index % 2].record_failure(
                _key(EMAIL),
                now=now,
                threshold=threshold,
                lock_duration_seconds=900,
            )
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
        state = store_b.get(_key(EMAIL))
        assert state is not None
        assert state.failure_count == workers
        assert state.locked_until == now + timedelta(seconds=900)
        assert FailedLoginLock(store=store_a, threshold=threshold).is_locked(_key(EMAIL), now=now)
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_store_failure_fails_closed_and_staging_cannot_use_memory(tmp_path: Path) -> None:
    clock = _Clock(_START)
    locked_auth, _lock, hasher, platform, _clock, audit = _service(
        clock=clock,
        login_lock=FailedLoginLock(store=UnavailableStore(), threshold=3),
    )
    hasher.verify_calls = 0
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        locked_auth.login(email=EMAIL, password=PASSWORD)
    assert hasher.verify_calls == 0
    assert platform.sessions.list_for_user(f"user-{EMAIL}") == []
    assert any(event.detail == "login_lock_unavailable" for event in audit.recent())

    record_auth, _record_lock, _record_hasher, _record_platform, _c, _a = _service(
        clock=clock,
        login_lock=FailedLoginLock(store=RecordUnavailable(), threshold=3),
    )
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        record_auth.login(email=EMAIL, password=WRONG)

    clear_auth, _clear_lock, _clear_hasher, clear_platform, _c2, _a2 = _service(
        clock=clock,
        login_lock=FailedLoginLock(store=ClearUnavailable(), threshold=3),
    )
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        clear_auth.login(email=EMAIL, password=PASSWORD)
    assert clear_platform.sessions.list_for_user(f"user-{EMAIL}") == []

    def broken_factory():
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    sql_store = SqlFailedLoginLockStore(broken_factory)
    with pytest.raises(FailedLoginLockUnavailable):
        sql_store.get(_key(EMAIL))
    missing = tmp_path / "missing-lock-table.db"
    engine = create_engine(f"sqlite:///{missing}")
    try:
        bare = SqlFailedLoginLockStore(sessionmaker(bind=engine, autoflush=False))
        with pytest.raises(FailedLoginLockUnavailable):
            bare.record_failure(
                _key(EMAIL),
                now=_START,
                threshold=2,
                lock_duration_seconds=900,
            )
    finally:
        engine.dispose()

    staging_store = build_failed_login_lock_store(Settings(APP_ENV="staging"))
    assert isinstance(staging_store, SqlFailedLoginLockStore)
    assert isinstance(
        build_failed_login_lock_store(Settings(APP_ENV="production")),
        SqlFailedLoginLockStore,
    )
    assert isinstance(
        build_failed_login_lock_store(Settings(APP_ENV="development")),
        InMemoryFailedLoginLockStore,
    )
    for env in ("staging", "production"):
        with pytest.raises(RateLimitConfigurationError):
            build_failed_login_lock_store(Settings(APP_ENV=env, RATE_LIMIT_BACKEND="memory"))
    sql_source = (ROOT / "app/infrastructure/database/failed_login_lock_store.py").read_text(
        encoding="utf-8"
    )
    assert "InMemoryFailedLoginLockStore" not in sql_source
    with pytest.raises(FailedLoginLockUnavailable):
        InMemoryFailedLoginLockStore().record_failure(
            EMAIL,
            now=_START,
            threshold=2,
            lock_duration_seconds=900,
        )


def test_existing_short_window_limiter_still_blocks_and_resets() -> None:
    clock = _Clock(_START)
    auth, login_lock, _hasher, _platform_store, _clock, _audit = _service(
        clock=clock,
        max_attempts=20,
        window_seconds=60,
        threshold=100,
    )
    _fail(auth, 20)
    with pytest.raises(UserPlatformRateLimitError, match=LOGIN_ATTEMPT_LIMIT_MESSAGE):
        auth.login(email=EMAIL, password=WRONG)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 20
    assert login_lock.is_locked(_key(EMAIL), now=clock()) is False

    clock.advance(seconds=61)
    _fail(auth, 1)
    assert login_lock.store.get(_key(EMAIL)).failure_count == 21

    reset_auth, reset_lock, _reset_hasher, _reset_platform, reset_clock, _reset_audit = _service(
        max_attempts=2,
        window_seconds=60,
        threshold=10,
    )
    _fail(reset_auth, 1)
    reset_auth.login(email=EMAIL, password=PASSWORD)
    assert reset_lock.store.get(_key(EMAIL)) is None
    _fail(reset_auth, 1)
    with pytest.raises(UserPlatformAuthError):
        reset_auth.login(email=EMAIL, password=WRONG)
    assert reset_clock().tzinfo is UTC


def test_locked_attempt_does_not_record_another_failure_or_verify_the_password() -> None:
    inner = InMemoryFailedLoginLockStore()
    recording = RecordingStore(inner)
    clock = _Clock(_START)
    auth, _lock, hasher, _platform_store, _clock, _audit = _service(
        clock=clock,
        login_lock=FailedLoginLock(store=recording, threshold=2, lock_duration_seconds=900),
    )
    _fail(auth, 2)
    assert recording.records == 2
    hasher.verify_calls = 0
    with pytest.raises(UserPlatformRateLimitError):
        auth.login(email=EMAIL, password=PASSWORD)
    assert recording.records == 2
    assert recording.clears == 0
    assert hasher.verify_calls == 0


def test_failed_login_lock_migration_upgrades_and_rolls_back(tmp_path: Path) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [_REVISION]
    revision = script.get_revision(_REVISION)
    assert revision is not None
    assert revision.down_revision == "e5f6a7b8c9d0"
    revision_module = _revision_module()

    engine = create_engine(f"sqlite:///{tmp_path / 'migrated-locks.db'}")
    try:
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            revision_module.upgrade()
        assert "failed_login_locks" in inspect(engine).get_table_names()
        index_names = {item["name"] for item in inspect(engine).get_indexes("failed_login_locks")}
        assert "ix_failed_login_locks_locked_until_ms" in index_names
        assert "ix_failed_login_locks_last_failure_ms" in index_names
        columns = {column["name"] for column in inspect(engine).get_columns("failed_login_locks")}
        assert "email" not in columns
        assert "password" not in columns
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        store = SqlFailedLoginLockStore(factory)
        state = store.record_failure(
            _key(EMAIL),
            now=_START,
            threshold=1,
            lock_duration_seconds=900,
        )
        assert state.locked_until == _START + timedelta(seconds=900)
        assert EMAIL not in state.identity_key
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            revision_module.downgrade()
        assert "failed_login_locks" not in inspect(engine).get_table_names()
        with pytest.raises(FailedLoginLockUnavailable):
            store.get(_key(EMAIL))
        with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
            revision_module.upgrade()
        restored = store.record_failure(
            _key(EMAIL),
            now=_START,
            threshold=2,
            lock_duration_seconds=900,
        )
        assert restored.failure_count == 1
        assert restored.locked_until is None
    finally:
        engine.dispose()


def test_memory_rate_limit_store_is_not_the_lock_store() -> None:
    """The short-window store and the lock store remain separate objects."""

    assert not isinstance(InMemoryRateLimitStore(), InMemoryFailedLoginLockStore)
    assert InMemoryFailedLoginLockStore().get(_key(EMAIL)) is None


def _open_store(backend: str, tmp_path: Path):
    if backend == "memory":
        return InMemoryFailedLoginLockStore(), ()
    store, _other, engine_a, engine_b = _sql_stores(tmp_path)
    return store, (engine_a, engine_b)


def _close_store(engines) -> None:
    for engine in engines:
        engine.dispose()


def _record(store, identity: str, now: datetime, *, threshold: int = 20):
    return store.record_failure(
        identity,
        now=now,
        threshold=threshold,
        lock_duration_seconds=FAILED_LOGIN_LOCK_DURATION_SECONDS,
        failure_retention_seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    )


def _plant(
    store,
    engine,
    identity: str,
    *,
    failure_count: int,
    locked_until: datetime | None,
    first_failure_at: datetime,
    last_failure_at: datetime,
) -> None:
    if isinstance(store, InMemoryFailedLoginLockStore):
        store._rows[identity] = FailedLoginLockState(
            identity_key=identity,
            failure_count=failure_count,
            locked_until=locked_until,
            first_failure_at=first_failure_at,
            last_failure_at=last_failure_at,
        )
        return
    with engine.begin() as conn:
        conn.execute(
            FailedLoginLockModel.__table__.insert(),
            {
                "identity_key": identity,
                "failure_count": failure_count,
                "locked_until_ms": None if locked_until is None else epoch_ms(locked_until),
                "first_failure_ms": epoch_ms(first_failure_at),
                "last_failure_ms": epoch_ms(last_failure_at),
            },
        )


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_failures_still_survive_the_sixty_second_window(backend: str, tmp_path: Path) -> None:
    store, engines = _open_store(backend, tmp_path)
    try:
        state = _record(store, _key(EMAIL), _START, threshold=20)
        assert state.failure_count == 1
        state = _record(store, _key(EMAIL), _START + timedelta(seconds=61), threshold=20)
        assert state.failure_count == 2
        assert state.locked_until is None
        assert state.first_failure_at == _START
    finally:
        _close_store(engines)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_sequence_younger_than_retention_continues(backend: str, tmp_path: Path) -> None:
    store, engines = _open_store(backend, tmp_path)
    try:
        _record(store, _key(EMAIL), _START, threshold=20)
        last = _START + timedelta(seconds=10)
        _record(store, _key(EMAIL), last, threshold=20)
        state = _record(store, _key(EMAIL), last + timedelta(seconds=899), threshold=20)
        assert state.failure_count == 3
        assert state.locked_until is None
        assert state.first_failure_at == _START
    finally:
        _close_store(engines)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_unlocked_sequence_older_than_retention_restarts_at_one(
    backend: str, tmp_path: Path
) -> None:
    store, engines = _open_store(backend, tmp_path)
    try:
        last = _START
        for offset in range(4):
            last = _START + timedelta(seconds=offset)
            _record(store, _key(EMAIL), last, threshold=20)
        assert store.get(_key(EMAIL)).failure_count == 4
        restart_at = last + timedelta(seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS)
        state = _record(store, _key(EMAIL), restart_at, threshold=20)
        assert state.failure_count == 1
        assert state.locked_until is None
        assert state.first_failure_at == restart_at
        assert state.last_failure_at == restart_at
    finally:
        _close_store(engines)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_active_lock_survives_stale_cleanup_and_keeps_its_deadline(
    backend: str, tmp_path: Path
) -> None:
    store, engines = _open_store(backend, tmp_path)
    engine = engines[0] if engines else None
    try:
        active = _key("active.lock@example.com")
        stale = _key("stale.row@example.com")
        now = _START + timedelta(hours=3)
        deadline = now + timedelta(seconds=FAILED_LOGIN_LOCK_DURATION_SECONDS)
        _plant(
            store,
            engine,
            active,
            failure_count=FAILED_LOGIN_LOCK_THRESHOLD,
            locked_until=deadline,
            first_failure_at=_START,
            last_failure_at=_START,
        )
        _plant(
            store,
            engine,
            stale,
            failure_count=4,
            locked_until=None,
            first_failure_at=_START,
            last_failure_at=_START,
        )
        state = _record(store, active, now, threshold=FAILED_LOGIN_LOCK_THRESHOLD)
        assert state.failure_count == FAILED_LOGIN_LOCK_THRESHOLD + 1
        assert state.locked_until == deadline
        assert store.get(active).locked_until == deadline
        assert store.get(stale) is None
        assert "active.lock@example.com" not in active
        assert "@" not in active
    finally:
        _close_store(engines)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_expired_lock_starts_a_fresh_sequence(backend: str, tmp_path: Path) -> None:
    store, engines = _open_store(backend, tmp_path)
    try:
        for _ in range(3):
            _record(store, _key(EMAIL), _START, threshold=3)
        locked = store.get(_key(EMAIL))
        assert locked.locked_until == _START + timedelta(seconds=900)
        restart_at = _START + timedelta(seconds=900)
        state = _record(store, _key(EMAIL), restart_at, threshold=3)
        assert state.failure_count == 1
        assert state.locked_until is None
        assert state.first_failure_at == restart_at
    finally:
        _close_store(engines)


def test_stale_unknown_email_rows_do_not_accumulate(tmp_path: Path) -> None:
    store, _other, engine_a, engine_b = _sql_stores(tmp_path)
    try:
        for index in range(25):
            _record(store, _key(f"unknown-{index}@example.com"), _START)
        recent_at = _START + timedelta(seconds=100)
        recent = _key("recent.person@example.com")
        _record(store, recent, recent_at)
        with engine_a.connect() as conn:
            assert len(conn.execute(select(FailedLoginLockModel.identity_key)).all()) == 26

        later = _START + timedelta(seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS)
        later_identity = _key("later.person@example.com")
        _record(store, later_identity, later)
        with engine_a.connect() as conn:
            remaining = {
                row[0] for row in conn.execute(select(FailedLoginLockModel.identity_key)).all()
            }
        assert remaining == {recent, later_identity}
        for row in remaining:
            assert "@" not in row
            assert "example.com" not in row

        for index in range(10):
            _record(store, _key(f"wave-{index}@example.com"), later)
        with engine_a.connect() as conn:
            assert len(conn.execute(select(FailedLoginLockModel.identity_key)).all()) == 12

        final_at = later + timedelta(seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS + 1)
        final_identity = _key("final.person@example.com")
        _record(store, final_identity, final_at)
        with engine_a.connect() as conn:
            rows = conn.execute(select(FailedLoginLockModel)).all()
        assert len(rows) == 1
        assert rows[0].identity_key == final_identity
        assert rows[0].failure_count == 1
        assert rows[0].locked_until_ms is None
        blob = " ".join(str(value) for row in rows for value in row)
        assert "unknown-" not in blob
        assert "recent.person@example.com" not in blob
        assert "final.person@example.com" not in blob
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_concurrent_stale_sql_updates_restart_without_losing_increments(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _sql_stores(tmp_path)
    stores = (store_a, store_b)
    identity = _key(EMAIL)
    _record(store_a, identity, _START, threshold=100)
    now = _START + timedelta(seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS + 1)
    workers = 40
    barrier = threading.Barrier(workers)
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=10)
            stores[index % 2].record_failure(
                identity,
                now=now,
                threshold=100,
                lock_duration_seconds=900,
                failure_retention_seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
            )
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
        state = store_b.get(identity)
        assert state is not None
        assert state.failure_count == workers
        assert state.locked_until is None
        assert state.first_failure_at == now
        assert EMAIL not in state.identity_key
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_successful_login_still_clears_its_row_and_reaps_only_stale_rows(tmp_path: Path) -> None:
    store, _other, engine_a, engine_b = _sql_stores(tmp_path)
    try:
        clock = _Clock(_START)
        _record(store, _key(UNKNOWN_EMAIL), _START, threshold=5)
        recent = _key("recent.person@example.com")
        _record(store, recent, _START + timedelta(seconds=850), threshold=5)
        clock.advance(seconds=FAILED_LOGIN_FAILURE_RETENTION_SECONDS)
        auth, login_lock, _hasher, _platform, _clock, _audit = _service(
            clock=clock,
            login_lock=FailedLoginLock(store=store, threshold=5, lock_duration_seconds=900),
            max_attempts=20,
            window_seconds=60,
        )
        _fail(auth, 1)
        assert login_lock.store.get(_key(EMAIL)).failure_count == 1
        assert login_lock.store.get(_key(UNKNOWN_EMAIL)) is None
        assert login_lock.store.get(recent) is not None
        result = auth.login(email=EMAIL, password=PASSWORD)
        assert result.access_token
        assert login_lock.store.get(_key(EMAIL)) is None
        assert login_lock.store.get(recent) is not None
        assert login_lock.store.get(recent).failure_count == 1
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_retention_cleanup_does_not_store_or_log_a_raw_email(tmp_path: Path, caplog) -> None:
    import logging

    caplog.set_level(logging.DEBUG)
    email = "retention.secret@example.com"
    other = "other.secret@example.com"
    store, _other, engine_a, engine_b = _sql_stores(tmp_path)
    try:
        _record(store, _key(email), _START)
        _record(store, _key(other), _START + timedelta(seconds=901))
        with engine_a.connect() as conn:
            rows = conn.execute(select(FailedLoginLockModel)).all()
        blob = " ".join(str(value) for row in rows for value in row)
        assert email not in blob
        assert other not in blob
        assert "@" not in blob
        assert email not in caplog.text
        assert other not in caplog.text
        for path in (
            ROOT / "app/infrastructure/database/failed_login_lock_store.py",
            ROOT / "app/launch/failed_login_lock.py",
        ):
            for line in path.read_text(encoding="utf-8").splitlines():
                if "logger." not in line:
                    continue
                assert "identity" not in line
                assert "email" not in line
                assert "@" not in line
    finally:
        engine_a.dispose()
        engine_b.dispose()
