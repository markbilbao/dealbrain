"""Sprint 27.2 — verified account email-change lifecycle."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from app.auth.email import EmailDeliveryError, NullEmailSender
from app.auth.email_resend import ResendEmailSender
from app.auth.email_templates import EMAIL_CHANGE_NOTICE_SUBJECT, EMAIL_CHANGE_SUBJECT
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.config import Settings
from app.core.dependencies import get_user_platform_service
from app.domain.entities.user_platform import EMAIL_CHANGE_PURPOSE, EmailChangeRequest
from app.domain.exceptions import UserPlatformAuthError, UserPlatformValidationError
from app.main import create_app
from app.privacy.lifecycle import ACCOUNT_DELETE_CONFIRMATION, AccountLifecycleService
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient

PASSWORD = "ValidPass123!"
NEW_EMAIL = "new.owner@example.com"


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now = self.now + timedelta(**kwargs)


def _settings(**overrides: Any) -> Settings:
    payload = {
        "_env_file": None,
        "APP_ENV": "development",
        "ALLOW_DEMO_RESET_TOKENS": "true",
        "PUBLIC_APP_BASE_URL": "https://piqsavi.com",
        "TRANSACTIONAL_EMAIL_FROM": "no-reply@piqsavi.com",
        "TRANSACTIONAL_EMAIL_FROM_NAME": "PiqSavi",
    }
    payload.update(overrides)
    return Settings(**payload)


def make_auth(
    *,
    clock: _Clock | None = None,
    email_sender: NullEmailSender | ResendEmailSender | None = None,
) -> tuple[AuthService, InMemoryUserPlatformStore, NullEmailSender | ResendEmailSender]:
    store = InMemoryUserPlatformStore()
    sender: NullEmailSender | ResendEmailSender = email_sender or NullEmailSender()
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        email_changes=store.email_changes,
        email_sender=sender,
        audit=AuditLogger(store.audit),
        clock=clock,
    )
    return auth, store, sender


def make_platform(
    *,
    email_sender: NullEmailSender | None = None,
    clock: _Clock | None = None,
) -> tuple[UserPlatformService, InMemoryUserPlatformStore, NullEmailSender]:
    store = InMemoryUserPlatformStore()
    sender = email_sender or NullEmailSender()
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        email_changes=store.email_changes,
        email_sender=sender,
        audit=audit,
        clock=clock,
    )
    lifecycle = AccountLifecycleService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        saved=store.saved,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        email_changes=store.email_changes,
        consents=store.consents,
        audit=audit,
    )
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        lifecycle=lifecycle,
        consents=store.consents,
        audit=audit,
    )
    return service, store, sender


def _register(
    auth: AuthService,
    *,
    email: str = "owner@example.com",
    password: str = PASSWORD,
    display_name: str = "Owner",
) -> Any:
    return auth.register(email=email, password=password, display_name=display_name)


@pytest.fixture
def client() -> Iterator[TestClient]:
    service, _store, _sender = make_platform()
    app = create_app()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestEmailChangeRequest:
    def test_unauthenticated_request_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/email-change",
            json={"new_email": NEW_EMAIL, "password": PASSWORD},
        )
        assert response.status_code == 401

    def test_authenticated_user_can_request_own_email_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, sender = make_auth()
        result = _register(auth)
        response = auth.request_email_change(
            result.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )
        assert response["status"] == "accepted"
        assert response["email_delivery"] is False
        raw = response["email_change_token_demo_only"]
        record = store.email_changes.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        assert record.user_id == result.user.user_id
        assert record.new_email == NEW_EMAIL
        assert record.purpose == EMAIL_CHANGE_PURPOSE
        assert record.token_hash != raw
        assert record.consumed is False
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"
        assert isinstance(sender, NullEmailSender)
        change_mail = [item for item in sender.sent if item.template_id == "email_change"]
        assert change_mail[0].to_address == NEW_EMAIL
        assert change_mail[0].subject == EMAIL_CHANGE_SUBJECT

    def test_current_password_reauth_required(self) -> None:
        auth, _store, _sender = make_auth()
        result = _register(auth)
        with pytest.raises(UserPlatformAuthError, match="Invalid credentials"):
            auth.request_email_change(result.access_token, new_email=NEW_EMAIL, password="")

    def test_wrong_password_rejected(self) -> None:
        auth, store, _sender = make_auth()
        result = _register(auth)
        with pytest.raises(UserPlatformAuthError, match="Invalid credentials"):
            auth.request_email_change(
                result.access_token,
                new_email=NEW_EMAIL,
                password="WrongPass123!",
            )
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"

    def test_browser_supplied_user_id_cannot_retarget_account(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        service, store, _sender = make_platform()
        victim = service.register(
            email="victim@example.com",
            password=PASSWORD,
            display_name="Victim",
        )
        attacker = service.register(
            email="attacker@example.com",
            password=PASSWORD,
            display_name="Attacker",
        )
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/email-change",
            json={
                "new_email": "attacker-new@example.com",
                "password": PASSWORD,
                "user_id": victim.user.user_id,
                "profile_id": victim.user.user_id,
                "account_id": victim.user.user_id,
                "email_owner_id": victim.user.user_id,
            },
            headers={"Authorization": f"Bearer {attacker.access_token}"},
        )
        assert response.status_code == 200
        assert store.users.get_by_id(victim.user.user_id).email == "victim@example.com"
        assert store.users.get_by_id(attacker.user.user_id).email == "attacker@example.com"
        query = client.post(
            f"/api/v1/auth/email-change?user_id={victim.user.user_id}",
            json={"new_email": "attacker-other@example.com", "password": PASSWORD},
            headers={"Authorization": f"Bearer {attacker.access_token}"},
        )
        assert query.status_code == 200
        assert store.users.get_by_id(victim.user.user_id).email == "victim@example.com"
        app.dependency_overrides.clear()

    def test_invalid_email_rejected(self) -> None:
        auth, store, _sender = make_auth()
        result = _register(auth)
        with pytest.raises(UserPlatformValidationError, match="email must be a valid address"):
            auth.request_email_change(
                result.access_token,
                new_email="not-an-email",
                password=PASSWORD,
            )
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"

    def test_same_email_rejected(self) -> None:
        auth, _store, _sender = make_auth()
        result = _register(auth)
        with pytest.raises(UserPlatformValidationError, match="must differ"):
            auth.request_email_change(
                result.access_token,
                new_email="Owner@example.com",
                password=PASSWORD,
            )

    def test_occupied_email_handled_safely(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, sender = make_auth()
        owner = _register(auth)
        other = _register(auth, email="taken@example.com", display_name="Taken")
        occupied = auth.request_email_change(
            owner.access_token,
            new_email="taken@example.com",
            password=PASSWORD,
        )
        free = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )
        assert occupied["status"] == free["status"] == "accepted"
        assert occupied["email_delivery"] is False
        assert free["email_delivery"] is False
        assert occupied["detail"] == free["detail"]
        assert "email_change_token_demo_only" not in occupied
        assert "taken@example.com" not in occupied["detail"]
        assert store.users.get_by_id(owner.user.user_id).email == "owner@example.com"
        assert store.users.get_by_id(other.user.user_id).email == "taken@example.com"
        assert isinstance(sender, NullEmailSender)
        change_mail = [item for item in sender.sent if item.template_id == "email_change"]
        assert all(item.to_address != "taken@example.com" for item in change_mail)

    def test_account_email_unchanged_before_confirmation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        result = _register(auth)
        auth.request_email_change(result.access_token, new_email=NEW_EMAIL, password=PASSWORD)
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"
        assert user.email_verified is False

    def test_provider_failure_leaves_account_unchanged(self) -> None:
        def fail(_url: str, **_kwargs: Any) -> httpx.Response:
            return httpx.Response(500, text="provider-secret-body")

        sender = ResendEmailSender(
            api_key="re_sprint27_2_configured_key_not_real",
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=fail,
        )
        auth, store, _sender = make_auth(email_sender=sender)
        result = _register(auth)
        response = auth.request_email_change(
            result.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )
        assert response["status"] == "accepted"
        assert "provider-secret-body" not in str(response)
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"
        events = store.audit.list_events(user_id=result.user.user_id)
        assert any(event.event_type == "email_change_delivery_failed" for event in events)

    def test_staging_and_production_do_not_expose_raw_token(self) -> None:
        auth, store, _sender = make_auth()
        result = _register(auth)
        for env in ("staging", "production"):
            from app.core import config as config_mod

            original = config_mod.settings
            config_mod.settings = _settings(
                APP_ENV=env,
                ALLOW_DEMO_RESET_TOKENS="true",
                TRANSACTIONAL_EMAIL_PROVIDER="resend",
                RESEND_API_KEY="re_sprint27_2_configured_key_not_real",
            )
            try:
                response = auth.request_email_change(
                    result.access_token,
                    new_email=f"{env}.new@example.com",
                    password=PASSWORD,
                )
            finally:
                config_mod.settings = original
            assert response["status"] == "accepted"
            assert "email_change_token_demo_only" not in response
            assert "token" not in response
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"


class TestEmailChangeConfirmation:
    def test_valid_token_changes_email_and_marks_verified(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, sender = make_auth()
        result = _register(auth)
        raw = auth.request_email_change(
            result.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        confirmed = auth.confirm_email_change(raw)
        assert confirmed["status"] == "email_changed"
        assert confirmed["email_verified"] is True
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == NEW_EMAIL
        assert user.email_verified is True
        record = store.email_changes.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        assert record.consumed is True
        assert isinstance(sender, NullEmailSender)
        notice = [item for item in sender.sent if item.template_id == "email_change_notice"]
        assert notice
        assert notice[0].to_address == "owner@example.com"
        assert notice[0].subject == EMAIL_CHANGE_NOTICE_SUBJECT
        assert "token=" not in (notice[0].body_text or "")

    def test_sessions_revoked_and_login_identity_updates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, _store, _sender = make_auth()
        owner = _register(auth)
        other = _register(auth, email="bystander@example.com", display_name="Bystander")
        extra = auth.login(email="owner@example.com", password=PASSWORD)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        auth.confirm_email_change(raw)
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(owner.access_token)
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(extra.access_token)
        with pytest.raises(UserPlatformAuthError):
            auth.login(email="owner@example.com", password=PASSWORD)
        auth.login(email=NEW_EMAIL, password=PASSWORD)
        auth.validate_session(other.access_token)

    def test_expired_token_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock = _Clock()
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth(clock=clock)
        result = _register(auth)
        raw = auth.request_email_change(
            result.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        clock.advance(hours=25)
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(raw)
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == "owner@example.com"

    def test_consumed_token_and_replay_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        result = _register(auth)
        raw = auth.request_email_change(
            result.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        auth.confirm_email_change(raw)
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(raw)
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        assert user.email == NEW_EMAIL

    def test_token_for_another_user_cannot_modify_account(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        service, store, _sender = make_platform()
        owner = service.register(email="owner@example.com", password=PASSWORD, display_name="Owner")
        other = service.register(email="other@example.com", password=PASSWORD, display_name="Other")
        raw = service.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/email-change/confirm",
            json={"token": raw, "user_id": other.user.user_id},
        )
        assert response.status_code == 200
        assert store.users.get_by_id(owner.user.user_id).email == NEW_EMAIL
        assert store.users.get_by_id(other.user.user_id).email == "other@example.com"
        app.dependency_overrides.clear()

    def test_account_deleted_before_confirmation_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        service, store, _sender = make_platform()
        result = service.register(email="gone@example.com", password=PASSWORD, display_name="Gone")
        raw = service.request_email_change(
            result.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        service.delete_account(
            result.access_token,
            confirmation=ACCOUNT_DELETE_CONFIRMATION,
            password=PASSWORD,
        )
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            service.confirm_email_change(raw)
        assert store.users.get_by_email(NEW_EMAIL) is None
        assert store.users.get_by_id(result.user.user_id) is None

    def test_destination_occupied_before_confirmation_fails_safely(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = _register(auth)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        occupant = _register(auth, email=NEW_EMAIL, display_name="Occupant")
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(raw)
        assert store.users.get_by_id(owner.user.user_id).email == "owner@example.com"
        assert store.users.get_by_id(occupant.user.user_id).email == NEW_EMAIL

    def test_newer_request_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock = _Clock()
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth(clock=clock)
        owner = _register(auth)
        first = auth.request_email_change(
            owner.access_token,
            new_email="first@example.com",
            password=PASSWORD,
        )["email_change_token_demo_only"]
        clock.advance(minutes=1)
        second = auth.request_email_change(
            owner.access_token,
            new_email="second@example.com",
            password=PASSWORD,
        )["email_change_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(first)
        auth.confirm_email_change(second)
        user = store.users.get_by_id(owner.user.user_id)
        assert user is not None
        assert user.email == "second@example.com"


class TestEmailChangeTokenIsolation:
    def test_password_reset_token_cannot_confirm_email_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = _register(auth)
        reset = auth.request_password_reset("owner@example.com")["reset_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(reset)
        assert store.users.get_by_id(owner.user.user_id).email == "owner@example.com"

    def test_verification_token_cannot_confirm_email_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = _register(auth)
        verify = auth.request_email_verification(owner.user.user_id)["verification_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(verify)
        assert store.users.get_by_id(owner.user.user_id).email == "owner@example.com"

    def test_email_change_token_cannot_reset_password(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, _store, _sender = make_auth()
        owner = _register(auth)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_password_reset(raw, "AnotherValid9x")
        auth.login(email="owner@example.com", password=PASSWORD)

    def test_email_change_token_cannot_satisfy_verify_email(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = _register(auth)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_verification(raw)
        user = store.users.get_by_id(owner.user.user_id)
        assert user is not None
        assert user.email_verified is False
        assert user.email == "owner@example.com"

    def test_wrong_purpose_record_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = _register(auth)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        record = store.email_changes.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        store.email_changes.save(
            EmailChangeRequest(
                change_id=record.change_id,
                user_id=record.user_id,
                token_hash=record.token_hash,
                new_email=record.new_email,
                created_at=record.created_at,
                expires_at=record.expires_at,
                purpose="password_reset",
                consumed=False,
            )
        )
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_change(raw)
        assert store.users.get_by_id(owner.user.user_id).email == "owner@example.com"


class TestEmailChangeBrandAndLinks:
    def test_email_uses_piqsavi_brand_and_trusted_base_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.core.config.settings",
            _settings(PUBLIC_APP_BASE_URL="https://piqsavi.com"),
        )
        auth, _store, sender = make_auth()
        owner = _register(auth)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        assert isinstance(sender, NullEmailSender)
        change_mail = [item for item in sender.sent if item.template_id == "email_change"]
        body = change_mail[0].body_text or ""
        assert change_mail[0].subject == EMAIL_CHANGE_SUBJECT
        assert "PiqSavi" in change_mail[0].subject
        assert "DealBrain" not in change_mail[0].subject
        assert "DealBrain" not in body
        assert f"https://piqsavi.com/confirm-email-change?token={raw}" in body

    def test_host_header_cannot_change_confirmation_destination(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        service, _store, sender = make_platform()
        owner = service.register(email="owner@example.com", password=PASSWORD, display_name="Owner")
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/email-change",
            json={"new_email": NEW_EMAIL, "password": PASSWORD},
            headers={
                "Authorization": f"Bearer {owner.access_token}",
                "Host": "evil.example",
            },
        )
        assert response.status_code == 200
        change_mail = [item for item in sender.sent if item.template_id == "email_change"]
        body = change_mail[0].body_text or ""
        assert "https://piqsavi.com/confirm-email-change?token=" in body
        assert "evil.example" not in body
        app.dependency_overrides.clear()

    def test_provider_errors_do_not_leak(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())

        class _FailingSender(NullEmailSender):
            def send(self, message: object) -> None:
                raise EmailDeliveryError("provider-secret-body")

        sender = _FailingSender()
        service, store, _sender = make_platform(email_sender=sender)
        owner = service.register(email="owner@example.com", password=PASSWORD, display_name="Owner")
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/email-change",
            json={"new_email": NEW_EMAIL, "password": PASSWORD},
            headers={"Authorization": f"Bearer {owner.access_token}"},
        )
        assert response.status_code == 200
        assert "provider-secret-body" not in response.text
        assert store.users.get_by_id(owner.user.user_id).email == "owner@example.com"
        app.dependency_overrides.clear()

    def test_raw_token_not_in_public_record(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = _register(auth)
        raw = auth.request_email_change(
            owner.access_token,
            new_email=NEW_EMAIL,
            password=PASSWORD,
        )["email_change_token_demo_only"]
        record = store.email_changes.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        public = record.to_dict()
        assert raw not in str(public)
        assert "token_hash" not in public
