"""Ordinary shopping-assistant submission replay. Not Sprint 40.8."""

from __future__ import annotations

import json
import threading
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.analytics.ask_events import emit_ask_product_events
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.consumer.guest_continuity import account_owner_from_session
from app.core.config import Settings
from app.core.dependencies import (
    get_shopping_conversation_repository,
    get_shopping_decision_snapshot_repository,
    get_shopping_submission_ledger,
    get_user_platform_store,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.infrastructure.database.models.shopping_submission import (
    ShoppingAssistantSubmissionModel,
)
from app.infrastructure.database.shopping_submission_store import SqlShoppingSubmissionStore
from app.launch.rate_limit_backend import RateLimitConfigurationError
from app.main import create_app
from app.shopping.submission_idempotency import (
    DETAIL_CONFLICT,
    DETAIL_INVALID,
    DETAIL_REQUIRED,
    DETAIL_UNAVAILABLE,
    PROCESSING_HORIZON_SECONDS,
    SUBMISSION_RETENTION_SECONDS,
    InMemoryShoppingSubmissionStore,
    ShoppingSubmissionLedger,
    ShoppingSubmissionUnavailable,
    apply_shopping_submission,
    build_shopping_submission_store,
    parse_submission_key,
    request_fingerprint,
    submission_authority_scope,
    submission_key_hash,
)
from app.user.fixtures import DEMO_PASSWORD
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    _owner,
    _presentation,
)

ROOT = Path(__file__).resolve().parents[2]
QUERY = "/api/v1/shopping-assistant/query"
_NOW = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
_SECRET = b"shopping-submission-test-secret"
_KEY = "submission-key-0001"


def _headers(key: str = _KEY, extra: dict[str, str] | None = None) -> dict[str, str]:
    merged = {"Idempotency-Key": key}
    if extra:
        merged.update(extra)
    return merged


def _request(
    host: str = "203.0.113.10",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": QUERY,
            "raw_path": QUERY.encode(),
            "query_string": b"",
            "headers": headers or [],
            "client": (host, 443),
            "server": ("test", 80),
        }
    )


def _fingerprint(query: str = "best laptop", **extra: object) -> str:
    payload: dict[str, object] = {"query": query, "mode": "economy"}
    payload.update(extra)
    return request_fingerprint(
        payload,
        scope="ask-anon:scope",
        location=None,
        selected_market=None,
    )


def _ledger() -> ShoppingSubmissionLedger:
    return ShoppingSubmissionLedger(InMemoryShoppingSubmissionStore())


@pytest.fixture
async def http_client(monkeypatch: pytest.MonkeyPatch):
    app = create_app()
    calls: list[int] = []
    emitted: list[dict[str, object]] = []
    from app.services.shopping_assistant_service import ShoppingAssistantService

    original = ShoppingAssistantService.query

    def _counted(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    def _spy(*args, **kwargs):
        emitted.append({"args": args, "kwargs": kwargs})
        return emit_ask_product_events(*args, **kwargs)

    monkeypatch.setattr(ShoppingAssistantService, "query", _counted)
    monkeypatch.setattr("app.api.v1.endpoints.shopping_assistant.emit_ask_product_events", _spy)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, calls, emitted, app
    app.dependency_overrides.clear()


def test_missing_and_malformed_keys_fail_before_a_claim() -> None:
    with pytest.raises(Exception, match=DETAIL_REQUIRED):
        parse_submission_key(None)
    with pytest.raises(Exception, match=DETAIL_REQUIRED):
        parse_submission_key("   ")
    with pytest.raises(Exception, match=DETAIL_INVALID):
        parse_submission_key("short")
    with pytest.raises(Exception, match=DETAIL_INVALID):
        parse_submission_key("bad key with spaces!!")
    with pytest.raises(Exception, match=DETAIL_INVALID):
        parse_submission_key(f"{_KEY},{_KEY}")
    assert parse_submission_key(f"  {_KEY}  ") == _KEY


def test_fingerprint_ignores_body_identity_and_changes_with_the_question() -> None:
    base = _fingerprint("same question", user_id="body-user", profile_id="body-profile")
    without_ids = _fingerprint("same question")
    assert base == without_ids
    assert _fingerprint("same question", conversation_id="conv-1") != without_ids
    assert _fingerprint("different question") != without_ids


def test_scopes_are_opaque_and_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.launch.rate_limit_keys.rate_limit_identity_secret",
        lambda: _SECRET,
    )
    guest = ConversationOwner(
        principal_type="guest",
        principal_id="guest-principal",
        session_id="guest-session-secret",
        expires_at=_NOW + timedelta(days=1),
    )
    account = ConversationOwner(
        principal_type="account",
        principal_id="account-principal",
        session_id="account-session-secret",
        expires_at=_NOW + timedelta(days=1),
    )
    other = replace(account, principal_id="other-account")
    guest_scope = submission_authority_scope(guest, _request(), secret=_SECRET)
    account_scope = submission_authority_scope(account, _request(), secret=_SECRET)
    other_scope = submission_authority_scope(other, _request(), secret=_SECRET)
    anonymous = submission_authority_scope(None, _request(host="198.51.100.20"), secret=_SECRET)
    assert guest_scope.startswith("ask-guest:")
    assert account_scope.startswith("ask-acct:")
    assert anonymous.startswith("ask-anon:")
    assert len({guest_scope, account_scope, other_scope, anonymous}) == 4
    for scope in (guest_scope, account_scope, anonymous):
        assert "guest-principal" not in scope
        assert "account-principal" not in scope
        assert "guest-session-secret" not in scope
        assert "198.51.100.20" not in scope
        assert "@" not in scope


def test_same_key_replays_and_a_different_payload_conflicts() -> None:
    ledger = _ledger()
    calls: list[str] = []
    fingerprint = _fingerprint()

    def execute() -> str:
        calls.append("run")
        return '{"answer":"once"}'

    first = apply_shopping_submission(
        ledger,
        scope="ask-anon:one",
        key=_KEY,
        fingerprint=fingerprint,
        execute=execute,
        now=_NOW,
    )
    second = apply_shopping_submission(
        ledger,
        scope="ask-anon:one",
        key=_KEY,
        fingerprint=fingerprint,
        execute=execute,
        now=_NOW,
    )
    conflict = apply_shopping_submission(
        ledger,
        scope="ask-anon:one",
        key=_KEY,
        fingerprint=_fingerprint("other question"),
        execute=execute,
        now=_NOW,
    )
    fresh = apply_shopping_submission(
        ledger,
        scope="ask-anon:one",
        key="submission-key-0002",
        fingerprint=fingerprint,
        execute=execute,
        now=_NOW,
    )
    assert first.outcome == "completed" and first.fresh is True
    assert second.outcome == "replay" and second.fresh is False
    assert second.response_json == first.response_json
    assert conflict.outcome == "conflict"
    assert fresh.fresh is True
    assert calls == ["run", "run"]


def test_owners_do_not_share_a_key_and_body_ids_do_not_choose_the_scope() -> None:
    ledger = _ledger()
    calls: list[str] = []
    fingerprint = _fingerprint()

    def execute() -> str:
        calls.append("run")
        return '{"answer":"owner"}'

    left = apply_shopping_submission(
        ledger,
        scope="ask-acct:left",
        key=_KEY,
        fingerprint=fingerprint,
        execute=execute,
        now=_NOW,
    )
    right = apply_shopping_submission(
        ledger,
        scope="ask-acct:right",
        key=_KEY,
        fingerprint=fingerprint,
        execute=execute,
        now=_NOW,
    )
    assert left.fresh is True and right.fresh is True
    assert calls == ["run", "run"]
    stored = ledger.read(scope="ask-acct:left", key=_KEY)
    assert stored is not None
    blob = json.dumps(
        {
            "scope": stored.scope,
            "key_hash": stored.key_hash,
            "fingerprint": stored.fingerprint,
            "response": stored.response_body,
        }
    )
    assert _KEY not in blob
    assert stored.key_hash == submission_key_hash(_KEY)
    assert "bearer" not in blob
    assert "password" not in blob


def test_concurrent_apply_executes_once() -> None:
    ledger = _ledger()
    calls: list[int] = []
    entered = threading.Event()
    release = threading.Event()
    errors: list[BaseException] = []

    def execute() -> str:
        calls.append(1)
        entered.set()
        assert release.wait(timeout=5)
        return '{"answer":"concurrent"}'

    def winner() -> None:
        try:
            apply_shopping_submission(
                ledger,
                scope="ask-anon:race",
                key=_KEY,
                fingerprint=_fingerprint(),
                execute=execute,
                now=_NOW,
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=winner)
    thread.start()
    assert entered.wait(timeout=5)
    duplicate = apply_shopping_submission(
        ledger,
        scope="ask-anon:race",
        key=_KEY,
        fingerprint=_fingerprint(),
        execute=execute,
        now=_NOW,
    )
    assert duplicate.outcome == "in_progress"
    assert calls == [1]
    release.set()
    thread.join(timeout=5)
    assert errors == []
    assert not thread.is_alive()
    replay = apply_shopping_submission(
        ledger,
        scope="ask-anon:race",
        key=_KEY,
        fingerprint=_fingerprint(),
        execute=execute,
        now=_NOW,
    )
    assert replay.outcome == "replay"
    assert calls == [1]


def test_query_exception_is_indeterminate_and_release_is_only_before_execution() -> None:
    ledger = _ledger()
    calls: list[int] = []

    def execute() -> str:
        calls.append(1)
        raise RuntimeError("partial write is unknown")

    with pytest.raises(RuntimeError, match="partial write"):
        apply_shopping_submission(
            ledger,
            scope="ask-anon:crash",
            key=_KEY,
            fingerprint=_fingerprint(),
            execute=execute,
            now=_NOW,
        )
    again = apply_shopping_submission(
        ledger,
        scope="ask-anon:crash",
        key=_KEY,
        fingerprint=_fingerprint(),
        execute=execute,
        now=_NOW,
    )
    assert again.outcome == "indeterminate"
    assert calls == [1]
    released = _ledger()
    claim = released.begin(scope="ask-anon:free", key=_KEY, fingerprint=_fingerprint(), now=_NOW)
    assert claim.outcome == "execute"
    assert released.release_unentered(scope="ask-anon:free", key=_KEY) is True
    retried = apply_shopping_submission(
        released,
        scope="ask-anon:free",
        key=_KEY,
        fingerprint=_fingerprint(),
        execute=lambda: '{"answer":"after release"}',
        now=_NOW,
    )
    assert retried.fresh is True


def test_cleanup_keeps_processing_rows_and_retention_is_bounded() -> None:
    ledger = _ledger()
    fingerprint = _fingerprint()
    apply_shopping_submission(
        ledger,
        scope="ask-anon:done",
        key=_KEY,
        fingerprint=fingerprint,
        execute=lambda: '{"answer":"kept"}',
        now=_NOW,
    )
    ledger.begin(
        scope="ask-anon:open",
        key="submission-key-0003",
        fingerprint=fingerprint,
        now=_NOW,
    )
    assert ledger.cleanup(_NOW + timedelta(days=30)) == 1
    processing = ledger.read(scope="ask-anon:open", key="submission-key-0003")
    assert processing is not None and processing.state == "processing"
    horizon = _NOW + timedelta(seconds=PROCESSING_HORIZON_SECONDS)
    sealed = ledger.store.seal_stale_processing(horizon)
    assert sealed == 1
    indeterminate = ledger.read(scope="ask-anon:open", key="submission-key-0003")
    assert indeterminate is not None and indeterminate.state == "indeterminate"
    assert ledger.cleanup(_NOW + timedelta(seconds=PROCESSING_HORIZON_SECONDS)) == 0
    later = _NOW + timedelta(seconds=PROCESSING_HORIZON_SECONDS + SUBMISSION_RETENTION_SECONDS)
    assert ledger.cleanup(later) == 1
    assert ledger.read(scope="ask-anon:open", key="submission-key-0003") is None
    assert SUBMISSION_RETENTION_SECONDS == 24 * 60 * 60


def test_store_failure_fails_closed() -> None:
    def broken_factory():
        raise RuntimeError("database down")

    store = SqlShoppingSubmissionStore(broken_factory)
    with pytest.raises(ShoppingSubmissionUnavailable):
        store.claim(scope="ask-anon:down", key_hash="a" * 64, fingerprint="b" * 64, now=_NOW)


def test_staging_and_production_use_the_shared_store() -> None:
    with pytest.raises(RateLimitConfigurationError):
        build_shopping_submission_store(Settings(APP_ENV="staging", RATE_LIMIT_BACKEND="memory"))
    with pytest.raises(RateLimitConfigurationError):
        build_shopping_submission_store(Settings(APP_ENV="production", RATE_LIMIT_BACKEND="memory"))
    assert isinstance(
        build_shopping_submission_store(Settings(APP_ENV="staging")),
        SqlShoppingSubmissionStore,
    )
    assert isinstance(
        build_shopping_submission_store(Settings(APP_ENV="production")),
        SqlShoppingSubmissionStore,
    )
    assert isinstance(
        build_shopping_submission_store(Settings(APP_ENV="development")),
        InMemoryShoppingSubmissionStore,
    )


def _sqlite_engines(tmp_path: Path):
    database = tmp_path / "submissions.db"

    def engine_for():
        engine = create_engine(
            f"sqlite:///{database}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _record) -> None:  # noqa: ARG001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

        return engine

    engine_a = engine_for()
    engine_b = engine_for()
    ShoppingAssistantSubmissionModel.__table__.create(engine_a, checkfirst=True)
    factory_a = sessionmaker(bind=engine_a, autoflush=False, expire_on_commit=False)
    factory_b = sessionmaker(bind=engine_b, autoflush=False, expire_on_commit=False)
    return (
        SqlShoppingSubmissionStore(factory_a),
        SqlShoppingSubmissionStore(factory_b),
        engine_a,
        engine_b,
    )


def test_sql_ledger_is_shared_across_connections(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _sqlite_engines(tmp_path)
    ledger_a = ShoppingSubmissionLedger(store_a)
    ledger_b = ShoppingSubmissionLedger(store_b)
    fingerprint = _fingerprint()
    calls: list[int] = []
    entered = threading.Event()
    release = threading.Event()

    def execute() -> str:
        calls.append(1)
        entered.set()
        assert release.wait(timeout=5)
        return '{"answer":"shared"}'

    errors: list[BaseException] = []

    def winner() -> None:
        try:
            apply_shopping_submission(
                ledger_a,
                scope="ask-acct:shared",
                key=_KEY,
                fingerprint=fingerprint,
                execute=execute,
                now=_NOW,
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=winner)
    thread.start()
    try:
        assert entered.wait(timeout=5)
        duplicate = apply_shopping_submission(
            ledger_b,
            scope="ask-acct:shared",
            key=_KEY,
            fingerprint=fingerprint,
            execute=execute,
            now=_NOW,
        )
        assert duplicate.outcome == "in_progress"
        assert calls == [1]
        release.set()
        thread.join(timeout=5)
        assert errors == []
        replay = apply_shopping_submission(
            ledger_b,
            scope="ask-acct:shared",
            key=_KEY,
            fingerprint=fingerprint,
            execute=execute,
            now=_NOW,
        )
        assert replay.outcome == "replay" and replay.fresh is False
        assert calls == [1]
        with engine_a.connect() as conn:
            rows = conn.execute(select(ShoppingAssistantSubmissionModel)).all()
        assert len(rows) == 1
        blob = " ".join(str(value) for value in rows[0])
        assert _KEY not in blob
        assert "203.0.113.10" not in blob
        assert rows[0].key_hash == submission_key_hash(_KEY)
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_sql_claim_barrier_has_one_winner(tmp_path: Path) -> None:
    store_a, store_b, engine_a, engine_b = _sqlite_engines(tmp_path)
    stores = (store_a, store_b)
    outcomes: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()
    workers = 8
    barrier = threading.Barrier(workers)
    fingerprint = "c" * 64
    key_hash = "d" * 64

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=5)
            claim = stores[index % 2].claim(
                scope="ask-anon:barrier",
                key_hash=key_hash,
                fingerprint=fingerprint,
                now=_NOW,
            )
            with lock:
                outcomes.append(claim.outcome)
        except BaseException as exc:  # noqa: BLE001
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(workers)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert errors == []
        assert not any(thread.is_alive() for thread in threads)
        assert outcomes.count("execute") == 1
        assert outcomes.count("in_progress") == workers - 1
    finally:
        engine_a.dispose()
        engine_b.dispose()


def test_migration_is_the_alembic_head() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["a7b8c9d0e1f2"]
    revision = script.get_revision("a7b8c9d0e1f2")
    assert revision is not None
    assert revision.down_revision == "f6a7b8c9d0e1"


def test_consumer_creates_one_key_before_fetch_and_reuses_it() -> None:
    source = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    generator = source.split("function newSubmissionKey()", 1)[1].split("function ", 1)[0]
    assert "crypto.randomUUID" in generator
    assert "question" not in generator
    assert "decision_id" not in generator
    assert source.index("newSubmissionKey()") < source.index('"Idempotency-Key": key')
    assert "pendingAskSubmission.body === body" in source
    assert 'form.dataset.askSubmitting === "1"' in source
    assert "Request already in progress." in source


@pytest.mark.asyncio
async def test_http_replay_skips_query_analytics_and_a_second_turn(http_client) -> None:
    client, calls, emitted, _app = http_client
    body = {"query": "What is the best gaming laptop under 60000?", "mode": "economy"}
    first = await client.post(QUERY, json=body, headers=_headers())
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    repository = get_shopping_conversation_repository()
    stored = repository.get(conversation_id)
    assert stored is not None
    turns = len(stored.turns)
    assert turns == 1
    assert calls == [1]
    assert len(emitted) == 1
    replay = await client.post(QUERY, json=body, headers=_headers())
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert calls == [1]
    assert len(emitted) == 1
    assert len(repository.get(conversation_id).turns) == turns
    changed = await client.post(
        QUERY,
        json={**body, "query": "Show me a cheaper laptop"},
        headers=_headers(),
    )
    assert changed.status_code == 409
    assert changed.json()["detail"] == DETAIL_CONFLICT
    assert calls == [1]
    assert len(emitted) == 1
    again = await client.post(QUERY, json=body, headers=_headers("submission-key-0002"))
    assert again.status_code == 200
    assert calls == [1, 1]
    assert len(emitted) == 2
    assert len(repository.get(again.json()["conversation_id"]).turns) == 1


@pytest.mark.asyncio
async def test_missing_key_store_outage_and_body_identity_do_not_execute(http_client) -> None:
    client, calls, emitted, app = http_client
    missing = await client.post(QUERY, json={"query": "Best gaming laptop under 60000"})
    assert missing.status_code == 400
    assert missing.json()["detail"] == DETAIL_REQUIRED
    malformed = await client.post(
        QUERY,
        json={"query": "Best gaming laptop under 60000"},
        headers={"Idempotency-Key": "nope"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["detail"] == DETAIL_INVALID
    assert calls == []
    assert emitted == []

    previous = app.dependency_overrides.get(get_shopping_submission_ledger)

    class _Down:
        def begin(self, **kwargs):
            raise ShoppingSubmissionUnavailable(DETAIL_UNAVAILABLE)

    app.dependency_overrides[get_shopping_submission_ledger] = lambda: _Down()
    outage = await client.post(
        QUERY,
        json={"query": "Best gaming laptop under 60000", "mode": "economy"},
        headers=_headers("submission-key-0005"),
    )
    assert outage.status_code == 503
    assert outage.json()["detail"] == DETAIL_UNAVAILABLE
    assert calls == []
    if previous is None:
        app.dependency_overrides.pop(get_shopping_submission_ledger, None)
    else:
        app.dependency_overrides[get_shopping_submission_ledger] = previous

    body = {
        "query": "Best gaming laptop under 60000",
        "mode": "economy",
        "user_id": "attacker-user",
        "profile_id": "attacker-profile",
    }
    first = await client.post(QUERY, json=body, headers=_headers("submission-key-0006"))
    assert first.status_code == 200, first.text
    recorded = len(calls)
    replay = await client.post(
        QUERY,
        json={**body, "user_id": "someone-else", "profile_id": "other-profile"},
        headers=_headers("submission-key-0006"),
    )
    assert replay.status_code == 200
    assert replay.json()["conversation_id"] == first.json()["conversation_id"]
    assert len(calls) == recorded


@pytest.mark.asyncio
async def test_recommendation_history_is_written_once(http_client) -> None:
    client, calls, _emitted, _app = http_client
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200, login.text
    auth = login.json()
    user_id = auth["user"]["user_id"]
    owner = account_owner_from_session(
        user_id=user_id,
        session_id=auth["session"]["session_id"],
        expires_at=datetime.fromisoformat(auth["expires_at"]),
    )
    before = len(get_user_platform_store().saved.list_history(user_id))
    headers = _headers(
        "submission-key-0007",
        {"Origin": "http://localhost:8000"},
    )
    cookies = {OWNER_COOKIE: owner_cookie_payload(owner)}
    body = {"query": "What is the best gaming laptop under 60000?", "mode": "economy"}
    first = await client.post(QUERY, json=body, headers=headers, cookies=cookies)
    assert first.status_code == 200, first.text
    assert len(get_user_platform_store().saved.list_history(user_id)) == before + 1
    replay = await client.post(QUERY, json=body, headers=headers, cookies=cookies)
    assert replay.status_code == 200
    assert replay.json()["answer"] == first.json()["answer"]
    assert len(get_user_platform_store().saved.list_history(user_id)) == before + 1
    assert calls == [1]


@pytest.mark.asyncio
async def test_research_proposal_refinement_and_confirmation_apply_once(http_client) -> None:
    client, calls, emitted = http_client[:3]
    owner = _owner(principal_id=f"guest-replay-{uuid4()}")
    decision_id = str(uuid4())
    snapshot = replace(_presentation(owner), decision_id=decision_id)
    get_shopping_decision_snapshot_repository().add(snapshot)
    cookies = {OWNER_COOKIE: owner_cookie_payload(owner)}
    origin = {"Origin": "http://localhost:8000"}
    proposal_key = "submission-key-0008"
    ask = await client.post(
        QUERY,
        json={"query": "What about AirPods Max?", "decision_id": decision_id, "surface": "results"},
        headers=_headers(proposal_key, origin),
        cookies=cookies,
    )
    assert ask.status_code == 200, ask.text
    proposal = ask.json()["research_proposal"]
    assert proposal["proposal_version"] == 1
    conversation_id = ask.json()["conversation_id"]
    repository = get_shopping_conversation_repository()
    context = repository.get(conversation_id)
    assert context is not None
    turns = len(context.turns)
    replay = await client.post(
        QUERY,
        json={"query": "What about AirPods Max?", "decision_id": decision_id, "surface": "results"},
        headers=_headers(proposal_key, origin),
        cookies=cookies,
    )
    assert replay.status_code == 200
    assert replay.json()["research_proposal"]["proposal_id"] == proposal["proposal_id"]
    assert replay.json()["research_proposal"]["proposal_version"] == 1
    assert len(repository.get(conversation_id).turns) == turns
    proposal_calls = len(calls)
    renewed = await client.post(
        QUERY,
        json={"query": "What about AirPods Max?", "decision_id": decision_id, "surface": "results"},
        headers=_headers("submission-key-0009", origin),
        cookies=cookies,
    )
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["research_proposal"]["proposal_version"] == 2
    assert len(calls) == proposal_calls + 1

    refine_key = "submission-key-0010"
    refine = await client.post(
        QUERY,
        json={"query": "Comfort matters more.", "decision_id": decision_id, "surface": "results"},
        headers=_headers(refine_key, origin),
        cookies=cookies,
    )
    assert refine.status_code == 200, refine.text
    assert refine.json()["action"] == "refine_session_recommendation"
    refine_conversation = refine.json()["conversation_id"]
    refined = repository.get(refine_conversation)
    assert refined is not None and refined.session_refinement is not None
    version = refined.session_refinement.refinement_version
    refine_turns = len(refined.turns)
    refine_replay = await client.post(
        QUERY,
        json={"query": "Comfort matters more.", "decision_id": decision_id, "surface": "results"},
        headers=_headers(refine_key, origin),
        cookies=cookies,
    )
    assert refine_replay.status_code == 200
    assert refine_replay.json()["answer"] == refine.json()["answer"]
    still = repository.get(refine_conversation)
    assert still is not None and still.session_refinement is not None
    assert still.session_refinement.refinement_version == version
    assert len(still.turns) == refine_turns

    confirm_key = "submission-key-0011"
    confirm_body = {
        "query": "Yes, research that",
        "decision_id": decision_id,
        "conversation_id": renewed.json()["conversation_id"],
        "surface": "results",
        "proposal_id": renewed.json()["research_proposal"]["proposal_id"],
        "proposal_version": renewed.json()["research_proposal"]["proposal_version"],
    }
    confirm_calls = len(calls)
    confirm_events = len(emitted)
    confirm = await client.post(
        QUERY,
        json=confirm_body,
        headers=_headers(confirm_key, origin),
        cookies=cookies,
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["research_handoff_created"] is True
    handoff_id = confirm.json()["research_handoff_id"]
    authorized = repository.get(conversation_id)
    assert authorized is not None
    assert len(authorized.research_authorizations) == 1
    assert authorized.research_authorizations[0].idempotency_key.startswith("research-auth:")
    confirm_replay = await client.post(
        QUERY,
        json=confirm_body,
        headers=_headers(confirm_key, origin),
        cookies=cookies,
    )
    assert confirm_replay.status_code == 200
    assert confirm_replay.json()["research_handoff_id"] == handoff_id
    assert confirm_replay.json()["research_handoff_created"] is True
    assert len(calls) == confirm_calls + 1
    assert len(emitted) == confirm_events + 1
    assert len(repository.get(conversation_id).research_authorizations) == 1
    repeat = await client.post(
        QUERY,
        json=confirm_body,
        headers=_headers("submission-key-0012", origin),
        cookies=cookies,
    )
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["research_handoff_id"] == handoff_id
    assert repeat.json()["research_handoff_created"] is False
    assert len(repository.get(conversation_id).research_authorizations) == 1


def test_evidence_keeps_r17_implemented_not_proven_and_sprint_40_open() -> None:
    evidence = (
        ROOT / "docs/roadmap/evidence/SPRINT_40_MESSAGE_SUBMISSION_IDEMPOTENCY_2026-10-13.md"
    ).read_text(encoding="utf-8")
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md").read_text(
        encoding="utf-8"
    )
    gaps = (ROOT / "docs/roadmap/GAP_INVENTORY.md").read_text(encoding="utf-8")
    readme = (ROOT / "docs/roadmap/sprints/README.md").read_text(encoding="utf-8")
    assert "591bcf751aae5e8f7cc14c1ffac17b81211b395a" in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "not PROVEN" in evidence
    assert "R17" in evidence
    assert "24 hours" in evidence
    assert "Sprint 40.8" not in evidence
    assert "**Status:** Planned" in sprint
    assert "not ENGINEERING COMPLETE" in sprint
    assert "not ENGINEERING COMPLETE" in roadmap
    assert "R17 | IMPLEMENTED-NOT-PROVEN" in gaps or "R17 is IMPLEMENTED-NOT-PROVEN" in gaps
    assert "message submission" in readme
    for text in (sprint, roadmap, gaps, readme, evidence):
        assert "Sprint 38 stays IN PROGRESS" in text or "IN PROGRESS" in text
        assert "Class C count remains 19" in text or "Class C count remains 19" in evidence
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "Routing stays 0" in evidence
