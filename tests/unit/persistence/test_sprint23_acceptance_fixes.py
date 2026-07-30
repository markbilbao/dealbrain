"""Sprint 23 acceptance fixes — expanded adapter, concurrency, rollback, auth tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities.affiliate import (
    AffiliateClick,
    AffiliateLink,
    AffiliateMerchant,
    AffiliateNetwork,
    AttributionModel,
    AttributionResult,
    ClickSource,
    CommissionType,
    ConversionStatus,
    MarketplacePlaceholder,
    MerchantHealthStatus,
    MerchantStatus,
)
from app.domain.entities.alerts import (
    AlertCondition,
    AlertConditionType,
    AlertEvent,
    AlertEventType,
    AlertRule,
    AlertRuleStatus,
    AlertSeverity,
)
from app.domain.entities.marketplace_data import (
    MarketplaceOffer,
    ProductAvailability,
    SourceMode,
    SyncCheckpoint,
)
from app.domain.entities.merchant import (
    MerchantAccount,
    MerchantActor,
    MerchantOrgStatus,
    MerchantOrganization,
    MerchantProfile,
)
from app.domain.entities.notifications import (
    Notification,
    NotificationSeverity,
    NotificationType,
)
from app.domain.entities.user_platform import User
from app.domain.exceptions import MerchantIsolationError, UserPlatformValidationError
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.affiliate_repository import (
    SqlAlchemyAffiliateRepository,
)
from app.infrastructure.database.repositories.alert_repository import SqlAlchemyAlertRuleRepository
from app.infrastructure.database.repositories.marketplace_data_repository import (
    SqlAlchemyMarketplaceDataRepository,
)
from app.infrastructure.database.repositories.merchant_repository import (
    SqlAlchemyMerchantRepository,
)
from app.infrastructure.database.repositories.notification_repository import (
    SqlAlchemyNotificationCenterRepository,
)
from app.infrastructure.database.repositories.user_platform_repository import (
    SqlAlchemyUserPlatformStore,
)
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import USERS
from app.merchant.security.permissions import require_membership


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    db_path = tmp_path / "sprint23_acceptance.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _now() -> datetime:
    return datetime.now(UTC)


def _user(user_id: str, email: str) -> User:
    now = _now()
    return User(
        user_id=user_id,
        email=email,
        password_hash="hashed",
        display_name="Tester",
        created_at=now,
        updated_at=now,
    )


def _offer(offer_id: str, *, product_id: str = "p1") -> MarketplaceOffer:
    return MarketplaceOffer(
        offer_id=offer_id,
        product_id=product_id,
        marketplace="fixture",
        marketplace_product_id=f"ext-{offer_id}",
        title="Test Offer",
        currency="USD",
        regular_price=100.0,
        sale_price=90.0,
        shipping_cost=0.0,
        total_price=90.0,
        availability=ProductAvailability.IN_STOCK,
        source_mode=SourceMode.FIXTURE,
        observed_at=_now(),
    )


def test_marketplace_offer_and_checkpoint_restart(sqlite_factory) -> None:
    repo = SqlAlchemyMarketplaceDataRepository(session_factory=sqlite_factory)
    repo.save_offer(_offer("offer-1"))
    repo.save_checkpoint(SyncCheckpoint(connector_id="conn-1", cursor="c-100", updated_at=_now()))

    restarted = SqlAlchemyMarketplaceDataRepository(session_factory=sqlite_factory)
    assert restarted.get_offer("offer-1") is not None
    loaded = restarted.get_checkpoint("conn-1")
    assert loaded is not None
    assert loaded.cursor == "c-100"


def test_marketplace_duplicate_offer_id_is_upsert(sqlite_factory) -> None:
    repo = SqlAlchemyMarketplaceDataRepository(session_factory=sqlite_factory)
    repo.save_offer(_offer("offer-1", product_id="p1"))
    repo.save_offer(_offer("offer-1", product_id="p2"))
    saved = repo.get_offer("offer-1")
    assert saved is not None
    assert saved.product_id == "p2"
    assert len(repo.list_offers(limit=10)) == 1


def test_notification_ack_survives_restart(sqlite_factory) -> None:
    repo = SqlAlchemyNotificationCenterRepository(session_factory=sqlite_factory)
    repo.save_notification(
        Notification(
            notification_id="n1",
            user_id="u1",
            title="Hello",
            body="World",
            type=NotificationType.SYSTEM,
            severity=NotificationSeverity.INFO,
            created_at=_now(),
        )
    )
    repo.mark_read("n1")
    repo.archive_notification("n1")

    restarted = SqlAlchemyNotificationCenterRepository(session_factory=sqlite_factory)
    loaded = restarted.get_notification("n1")
    assert loaded is not None
    assert loaded.read_at is not None
    assert loaded.archived_at is not None
    assert restarted.count_unread("u1") == 0


def test_affiliate_attribution_survives_restart(sqlite_factory) -> None:
    repo = SqlAlchemyAffiliateRepository(session_factory=sqlite_factory, seed=False)
    now = _now()
    repo.save_merchant(
        AffiliateMerchant(
            merchant_id="m1",
            merchant_name="Demo",
            marketplace=MarketplacePlaceholder.AMAZON,
            country="US",
            affiliate_network=AffiliateNetwork.DEMO_NETWORK,
            tracking_template="https://example.test/{product_ref}",
            commission_type=CommissionType.PERCENT,
            commission_value=5.0,
            cookie_days=7,
            status=MerchantStatus.ACTIVE,
            priority=1,
            created_at=now,
            updated_at=now,
            health_status=MerchantHealthStatus.HEALTHY,
        )
    )
    repo.save_link(
        AffiliateLink(
            link_id="l1",
            merchant_id="m1",
            product_id="p1",
            product_name="Phone",
            original_url="https://example.test/p1",
            affiliate_url="https://example.test/aff/p1",
            marketplace=MarketplacePlaceholder.AMAZON,
            campaign_id="c1",
            sub_id="s1",
            click_id="clk1",
            deep_link=False,
            created_at=now,
        )
    )
    repo.save_click(
        AffiliateClick(
            click_id="clk1",
            user_id="u1",
            session_id="sess1",
            merchant_id="m1",
            product_id="p1",
            timestamp=now,
            device="desktop",
            country="US",
            campaign_id="c1",
            source=ClickSource.DIRECT_LINK,
            referrer=None,
            conversion_status=ConversionStatus.CLICKED,
            revenue=0.0,
            link_id="l1",
        )
    )
    repo.save_attribution(
        AttributionResult(
            attribution_id="attr-1",
            model=AttributionModel.LAST_CLICK,
            click_id="clk1",
            merchant_id="m1",
            product_id="p1",
            attributed_at=now,
            revenue=10.0,
            estimated_commission=0.5,
            reason="last_click",
        )
    )

    restarted = SqlAlchemyAffiliateRepository(session_factory=sqlite_factory, seed=False)
    assert restarted.get_merchant("m1") is not None
    assert restarted.get_click("clk1") is not None
    assert any(a.attribution_id == "attr-1" for a in restarted.list_attributions(limit=10))


def test_merchant_records_survive_restart(sqlite_factory) -> None:
    repo = SqlAlchemyMerchantRepository(session_factory=sqlite_factory, seed=False)
    now = _now()
    repo.save_account(
        MerchantAccount(
            account_id="acc-1",
            email="merchant@example.com",
            display_name="Merchant",
            created_at=now,
            updated_at=now,
            demo_token="tok-1",
        )
    )
    repo.save_organization(
        MerchantOrganization(
            organization_id="org-1",
            profile=MerchantProfile(
                business_name="Biz",
                legal_name="Biz LLC",
                display_name="Biz",
                country="US",
                business_category="electronics",
            ),
            status=MerchantOrgStatus.ACTIVE,
            owner_account_id="acc-1",
            created_at=now,
            updated_at=now,
        )
    )

    restarted = SqlAlchemyMerchantRepository(session_factory=sqlite_factory, seed=False)
    assert restarted.get_account_by_email("merchant@example.com") is not None
    assert restarted.get_account_by_token("tok-1") is not None
    assert restarted.get_organization("org-1") is not None


def test_sqlalchemy_affiliate_and_merchant_seed_default_is_off(sqlite_factory) -> None:
    affiliate = SqlAlchemyAffiliateRepository(session_factory=sqlite_factory)
    merchant = SqlAlchemyMerchantRepository(session_factory=sqlite_factory)
    assert affiliate.list_merchants() == []
    assert merchant.list_organizations() == []


def test_concurrent_duplicate_user_registration(sqlite_factory) -> None:
    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)

    def _register(suffix: str) -> str:
        try:
            store.users.save(_user(f"u-{suffix}", "same@example.com"))
            return "ok"
        except UserPlatformValidationError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_register, str(i)) for i in range(8)]
        results = [f.result() for f in as_completed(futures)]

    assert results.count("ok") == 1
    assert results.count("conflict") == 7
    assert len(store.users.list_users()) == 1


def test_concurrent_alert_dedupe_key(sqlite_factory) -> None:
    repo = SqlAlchemyAlertRuleRepository(session_factory=sqlite_factory)
    now = _now()

    def _write(i: int) -> str:
        event = AlertEvent(
            event_id=f"e-{i}",
            user_id="u1",
            event_type=AlertEventType.PRICE_DROP,
            severity=AlertSeverity.INFO,
            created_at=now,
            dedupe_key="shared-dedupe",
            payload={"i": i},
        )
        try:
            repo.save_event(event)
            return "ok"
        except PersistenceConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = [f.result() for f in as_completed(pool.submit(_write, i) for i in range(6))]

    assert results.count("ok") == 1
    assert results.count("conflict") == 5
    assert repo.find_by_dedupe_key("shared-dedupe") is not None


def test_concurrent_affiliate_attribution_duplicate_id(sqlite_factory) -> None:
    """Concurrent saves with the same attribution_id remain a single upserted row.

    ``save_attribution`` uses ``ops.upsert`` (update-in-place after first insert).
    Under races some writers may hit ``PersistenceConflictError`` on insert; others
    may succeed via update. The durable guarantee is uniqueness of the entity id,
    not a fixed ok/conflict split.
    """
    repo = SqlAlchemyAffiliateRepository(session_factory=sqlite_factory, seed=False)
    now = _now()

    def _write(i: int) -> str:
        try:
            repo.save_attribution(
                AttributionResult(
                    attribution_id="attr-shared",
                    model=AttributionModel.LAST_CLICK,
                    click_id=f"clk-{i}",
                    merchant_id="m1",
                    product_id="p1",
                    attributed_at=now,
                    revenue=float(i),
                    estimated_commission=0.1,
                    reason="idempotent",
                )
            )
            return "ok"
        except PersistenceConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = [f.result() for f in as_completed(pool.submit(_write, i) for i in range(4))]

    assert len(results) == 4
    assert set(results) <= {"ok", "conflict"}
    assert results.count("ok") >= 1
    loaded = repo.list_attributions(limit=20)
    assert len(loaded) == 1
    assert loaded[0].attribution_id == "attr-shared"


def test_operational_store_rollback_leaves_no_partial_user(sqlite_factory) -> None:
    session: Session = sqlite_factory()
    try:
        ops = OperationalStore(session)
        ops.upsert(
            USERS,
            "u-roll",
            _user("u-roll", "roll@example.com"),
            secondary_key="roll@example.com",
        )
        raise RuntimeError("force rollback")
    except RuntimeError:
        session.rollback()
    finally:
        session.close()

    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    assert store.users.get_by_id("u-roll") is None
    assert store.users.get_by_email("roll@example.com") is None


def test_alert_and_notification_user_isolation(sqlite_factory) -> None:
    alerts = SqlAlchemyAlertRuleRepository(session_factory=sqlite_factory)
    notes = SqlAlchemyNotificationCenterRepository(session_factory=sqlite_factory)
    now = _now()
    alerts.save_rule(
        AlertRule(
            rule_id="r-a",
            user_id="user-a",
            name="A",
            conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
            created_at=now,
            updated_at=now,
            status=AlertRuleStatus.ENABLED,
            severity=AlertSeverity.INFO,
        )
    )
    alerts.save_rule(
        AlertRule(
            rule_id="r-b",
            user_id="user-b",
            name="B",
            conditions=(AlertCondition(condition_type=AlertConditionType.RESTOCKED),),
            created_at=now,
            updated_at=now,
            status=AlertRuleStatus.ENABLED,
            severity=AlertSeverity.INFO,
        )
    )
    notes.save_notification(
        Notification(
            notification_id="n-a",
            user_id="user-a",
            title="A",
            body="A",
            type=NotificationType.SYSTEM,
            severity=NotificationSeverity.INFO,
            created_at=now,
        )
    )
    notes.save_notification(
        Notification(
            notification_id="n-b",
            user_id="user-b",
            title="B",
            body="B",
            type=NotificationType.SYSTEM,
            severity=NotificationSeverity.INFO,
            created_at=now,
        )
    )

    assert [r.rule_id for r in alerts.list_rules(user_id="user-a")] == ["r-a"]
    assert [n.notification_id for n in notes.list_notifications(user_id="user-a")] == ["n-a"]
    assert all(n.user_id == "user-a" for n in notes.list_notifications(user_id="user-a"))


def test_cross_merchant_membership_denied(sqlite_factory) -> None:
    now = _now()
    account = MerchantAccount(
        account_id="acc-b",
        email="other@example.com",
        display_name="Other",
        created_at=now,
        updated_at=now,
    )
    actor = MerchantActor(account=account, organization_id="org-b")
    with pytest.raises(MerchantIsolationError):
        require_membership(actor, "org-a")
