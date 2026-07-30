"""Sprint 23 persistence contract, restart, concurrency, and readiness tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.alerts.memory import InMemoryAlertRuleRepository
from app.core.config import Settings
from app.domain.entities.alerts import (
    AlertCondition,
    AlertConditionType,
    AlertEvent,
    AlertEventType,
    AlertRule,
    AlertRuleStatus,
    AlertSeverity,
)
from app.domain.entities.user_platform import User, UserSession
from app.domain.exceptions import UserPlatformValidationError
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.alert_repository import SqlAlchemyAlertRuleRepository
from app.infrastructure.database.repositories.user_platform_repository import (
    SqlAlchemyUserPlatformStore,
)
from app.infrastructure.persistence.binding import (
    assert_production_persistence,
    resolve_backend,
)
from app.infrastructure.persistence.codec import decode_entity, encode_entity
from app.infrastructure.persistence.errors import PersistenceConfigurationError
from app.infrastructure.persistence.readiness import evaluate_persistence_readiness
from app.infrastructure.persistence.session import reset_sync_engine
from app.user.memory import InMemoryUserPlatformStore


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    db_path = tmp_path / "sprint23.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _user(user_id: str, email: str) -> User:
    now = datetime.now(UTC)
    return User(
        user_id=user_id,
        email=email,
        password_hash="hashed",
        display_name="Tester",
        created_at=now,
        updated_at=now,
    )


def test_codec_roundtrip_user() -> None:
    user = _user("u1", "a@example.com")
    restored = decode_entity(User, encode_entity(user))
    assert restored == user


@pytest.mark.parametrize(
    "factory_name",
    ["memory", "sql"],
)
def test_user_repository_contract(factory_name: str, sqlite_factory) -> None:
    if factory_name == "memory":
        store = InMemoryUserPlatformStore()
    else:
        store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)

    saved = store.users.save(_user("u1", "one@example.com"))
    assert store.users.get_by_id("u1") == saved
    assert store.users.get_by_email("one@example.com") == saved

    with pytest.raises(UserPlatformValidationError):
        store.users.save(_user("u2", "one@example.com"))


def test_session_restart_recovery(sqlite_factory) -> None:
    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    now = datetime.now(UTC)
    store.users.save(_user("u1", "one@example.com"))
    session = UserSession(
        session_id="s1",
        user_id="u1",
        token_hash="hash-1",
        created_at=now,
        expires_at=now,
        last_seen_at=now,
    )
    store.sessions.save(session)

    # Reconstruct store (simulates process restart with same DB file).
    restarted = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    assert restarted.sessions.get_by_token_hash("hash-1") is not None
    restarted.sessions.revoke("s1")
    revoked = restarted.sessions.get_by_id("s1")
    assert revoked is not None and revoked.revoked is True


def test_alert_dedupe_survives_restart(sqlite_factory) -> None:
    now = datetime.now(UTC)
    repo = SqlAlchemyAlertRuleRepository(session_factory=sqlite_factory)
    rule = AlertRule(
        rule_id="r1",
        user_id="u1",
        name="drop",
        conditions=(
            AlertCondition(condition_type=AlertConditionType.PRICE_DROP, threshold_value=10.0),
        ),
        created_at=now,
        updated_at=now,
        status=AlertRuleStatus.ENABLED,
        severity=AlertSeverity.INFO,
    )
    repo.save_rule(rule)
    event = AlertEvent(
        event_id="e1",
        user_id="u1",
        event_type=AlertEventType.PRICE_DROP,
        severity=AlertSeverity.INFO,
        created_at=now,
        dedupe_key="dedupe-1",
        rule_id="r1",
        payload={"previous_price": 20.0, "current_price": 10.0, "currency": "USD"},
    )
    repo.save_event(event)

    restarted = SqlAlchemyAlertRuleRepository(session_factory=sqlite_factory)
    assert restarted.find_by_dedupe_key("dedupe-1") is not None
    assert restarted.get_rule("r1") is not None


def test_alert_memory_and_sql_list_parity(sqlite_factory) -> None:
    now = datetime.now(UTC)
    memory = InMemoryAlertRuleRepository()
    sql = SqlAlchemyAlertRuleRepository(session_factory=sqlite_factory)
    rule = AlertRule(
        rule_id="r1",
        user_id="u1",
        name="drop",
        conditions=(
            AlertCondition(condition_type=AlertConditionType.PRICE_DROP, threshold_value=10.0),
        ),
        created_at=now,
        updated_at=now,
        status=AlertRuleStatus.ENABLED,
        severity=AlertSeverity.INFO,
    )
    memory.save_rule(rule)
    sql.save_rule(rule)
    assert len(memory.list_rules(user_id="u1")) == len(sql.list_rules(user_id="u1"))


def test_production_rejects_memory_backends() -> None:
    cfg = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        persistence_backend="memory",
        demo_launcher_enabled=False,
        allow_demo_reset_tokens=False,
    )
    assert resolve_backend("user_platform", cfg) == "memory"
    with pytest.raises(PersistenceConfigurationError):
        assert_production_persistence(cfg)


def test_readiness_not_ready_when_production_memory() -> None:
    cfg = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        persistence_backend="memory",
        demo_launcher_enabled=False,
        allow_demo_reset_tokens=False,
        database_url="sqlite:///:memory:",
    )
    result = evaluate_persistence_readiness(cfg)
    assert result["level"] == "NOT_READY"
    assert result["memory_domains_in_production"]


def test_production_rejects_seed_demo_data() -> None:
    cfg = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        persistence_backend="sqlalchemy",
        demo_launcher_enabled=False,
        allow_demo_reset_tokens=False,
        seed_demo_data=True,
    )
    from app.core.validation import validate_settings

    result = validate_settings(cfg)
    assert not result.ok
    assert any("SEED_DEMO_DATA" in e for e in result.errors)


def test_architecture_dealscore_module_untouched() -> None:
    """Sprint 5 engine module must remain the DealScore owner (no persistence imports)."""
    root = Path(__file__).resolve().parents[2]
    files = list((root / "app/intelligence/dealscore").rglob("*.py"))
    for path in files:
        text = path.read_text()
        assert "operational_entities" not in text
        assert "SqlAlchemy" not in text


def test_recommendation_engine_has_no_persistence_coupling() -> None:
    root = Path(__file__).resolve().parents[2]
    for path in (root / "app/intelligence/recommendation").rglob("*.py"):
        text = path.read_text()
        assert "operational_entities" not in text
        assert "SqlAlchemyAffiliate" not in text
        assert "SqlAlchemyMerchant" not in text
