"""Sprint 27.1 — Resend identity email + reset/verify confirm lifecycle."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from app.auth.email import EmailDeliveryError, EmailMessage, NullEmailSender
from app.auth.email_factory import (
    allows_inline_identity_tokens,
    build_identity_email_sender,
    build_trusted_action_url,
)
from app.auth.email_resend import RESEND_EMAILS_URL, ResendEmailSender
from app.auth.email_templates import EMAIL_VERIFICATION_SUBJECT, PASSWORD_RESET_SUBJECT
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.config import Settings
from app.core.dependencies import get_user_platform_service
from app.core.validation import exportable_settings, validate_settings
from app.domain.exceptions import (
    ConfigurationValidationError,
    UserPlatformAuthError,
    UserPlatformValidationError,
)
from app.main import create_app
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient

DEMO_EMAIL = "student@example.com"
NEW_PASSWORD = "Replacement9x"


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

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


def register_unverified(auth: AuthService, email: str = "new.verify@example.com") -> str:
    result = auth.register(
        email=email,
        password="ValidPass123!",
        display_name="Unverified",
    )
    return result.user.user_id


def make_auth(
    *,
    clock: _Clock | None = None,
    email_sender: NullEmailSender | ResendEmailSender | None = None,
) -> tuple[AuthService, InMemoryUserPlatformStore, NullEmailSender | ResendEmailSender]:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    sender: NullEmailSender | ResendEmailSender = email_sender or NullEmailSender()
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        email_sender=sender,
        audit=AuditLogger(store.audit),
        clock=clock,
    )
    return auth, store, sender


def make_platform(
    *,
    email_sender: NullEmailSender | None = None,
) -> tuple[UserPlatformService, NullEmailSender]:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    sender = email_sender or NullEmailSender()
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        email_sender=sender,
        audit=audit,
    )
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        audit=audit,
    )
    return service, sender


@pytest.fixture
def client() -> Iterator[TestClient]:
    service, _sender = make_platform()
    app = create_app()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestPasswordReset:
    def test_known_account_request_prepares_hashed_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, sender = make_auth()
        response = auth.request_password_reset(DEMO_EMAIL)
        assert response["status"] == "accepted"
        assert response["email_delivery"] is False
        assert "reset_token_demo_only" in response
        raw = response["reset_token_demo_only"]
        record = store.password_resets.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        assert record.token_hash != raw
        assert record.consumed is False
        assert isinstance(sender, NullEmailSender)
        assert sender.sent[0].subject == PASSWORD_RESET_SUBJECT
        body = sender.sent[0].body_text or ""
        assert f"https://piqsavi.com/reset-password?token={raw}" in body
        assert "Reset token (demo only" not in body

    def test_unknown_account_is_enumeration_safe(self) -> None:
        auth, _store, _sender = make_auth()
        known = auth.request_password_reset(DEMO_EMAIL)
        unknown = auth.request_password_reset("nobody@example.com")
        assert known["status"] == unknown["status"]
        assert known["email_delivery"] is False
        assert unknown["email_delivery"] is False
        assert known["detail"] == unknown["detail"]
        assert "reset_token_demo_only" not in unknown

    def test_valid_confirm_changes_password_and_revokes_sessions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        first = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        second = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        raw = auth.request_password_reset(DEMO_EMAIL)["reset_token_demo_only"]
        result = auth.confirm_password_reset(raw, NEW_PASSWORD)
        assert result["status"] == "password_changed"
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(first.access_token)
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(second.access_token)
        auth.login(email=DEMO_EMAIL, password=NEW_PASSWORD)
        with pytest.raises(UserPlatformAuthError):
            auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        record = store.password_resets.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        assert record.consumed is True

    def test_expired_token_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock = _Clock()
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, _store, _sender = make_auth(clock=clock)
        raw = auth.request_password_reset(DEMO_EMAIL)["reset_token_demo_only"]
        clock.advance(hours=2)
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_password_reset(raw, NEW_PASSWORD)
        auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)

    def test_reused_token_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, _store, _sender = make_auth()
        raw = auth.request_password_reset(DEMO_EMAIL)["reset_token_demo_only"]
        auth.confirm_password_reset(raw, NEW_PASSWORD)
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_password_reset(raw, "AnotherValid9x")

    def test_wrong_purpose_token_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        verify_raw = auth.request_email_verification(user.user_id)["verification_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_password_reset(verify_raw, NEW_PASSWORD)
        auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)

    def test_password_unchanged_until_valid_confirm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, _store, _sender = make_auth()
        auth.request_password_reset(DEMO_EMAIL)
        auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        with pytest.raises(UserPlatformAuthError):
            auth.confirm_password_reset("not-a-real-token", NEW_PASSWORD)
        auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)


class TestVerification:
    def test_valid_verification_persists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, sender = make_auth()
        user_id = register_unverified(auth)
        user = store.users.get_by_id(user_id)
        assert user is not None
        assert user.email_verified is False
        raw = auth.request_email_verification(user.user_id)["verification_token_demo_only"]
        result = auth.confirm_email_verification(raw)
        assert result["status"] == "email_verified"
        assert result["email_verified"] is True
        stored = store.users.get_by_id(user.user_id)
        assert stored is not None
        assert stored.email_verified is True
        assert isinstance(sender, NullEmailSender)
        assert sender.sent[0].subject == EMAIL_VERIFICATION_SUBJECT

    def test_expired_verification_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock = _Clock()
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth(clock=clock)
        user_id = register_unverified(auth)
        user = store.users.get_by_id(user_id)
        assert user is not None
        raw = auth.request_email_verification(user.user_id)["verification_token_demo_only"]
        clock.advance(hours=25)
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_verification(raw)
        stored = store.users.get_by_id(user.user_id)
        assert stored is not None
        assert stored.email_verified is False

    def test_reused_verification_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        user_id = register_unverified(auth)
        user = store.users.get_by_id(user_id)
        assert user is not None
        raw = auth.request_email_verification(user.user_id)["verification_token_demo_only"]
        auth.confirm_email_verification(raw)
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_verification(raw)
        stored = store.users.get_by_id(user.user_id)
        assert stored is not None
        assert stored.email_verified is True

    def test_account_binding_rejects_reset_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        user_id = register_unverified(auth)
        raw = auth.request_password_reset("new.verify@example.com")["reset_token_demo_only"]
        with pytest.raises(UserPlatformAuthError, match="Invalid or expired"):
            auth.confirm_email_verification(raw)
        user = store.users.get_by_id(user_id)
        assert user is not None
        assert user.email_verified is False

    def test_public_request_is_enumeration_safe(self) -> None:
        auth, _store, _sender = make_auth()
        known = auth.request_email_verification_by_email(DEMO_EMAIL)
        unknown = auth.request_email_verification_by_email("ghost@example.com")
        assert known["status"] == unknown["status"]
        assert known["email_delivery"] is False
        assert unknown["email_delivery"] is False
        assert known["detail"] == unknown["detail"]
        assert "verification_token_demo_only" not in unknown


class TestEnvironmentSafety:
    def test_development_may_expose_demo_token(self) -> None:
        assert allows_inline_identity_tokens(_settings(APP_ENV="development")) is True

    def test_staging_never_exposes_demo_token(self) -> None:
        assert (
            allows_inline_identity_tokens(
                _settings(APP_ENV="staging", ALLOW_DEMO_RESET_TOKENS="true")
            )
            is False
        )

    def test_production_never_exposes_demo_token(self) -> None:
        assert (
            allows_inline_identity_tokens(
                _settings(APP_ENV="production", ALLOW_DEMO_RESET_TOKENS="true")
            )
            is False
        )

    def test_unknown_environment_fails_closed_for_tokens(self) -> None:
        cfg = SimpleNamespace(
            app_env="lab",
            allow_demo_reset_tokens=True,
            is_development=True,
        )
        assert allows_inline_identity_tokens(cfg) is False  # type: ignore[arg-type]

    def test_production_rejects_null_sender(self) -> None:
        cfg = _settings(
            APP_ENV="production",
            TRANSACTIONAL_EMAIL_PROVIDER="null",
            RESEND_API_KEY="re_sprint27_1_configured_key_not_real",
        )
        with pytest.raises(ConfigurationValidationError):
            build_identity_email_sender(cfg)

    def test_production_builds_resend_sender(self) -> None:
        cfg = _settings(
            APP_ENV="production",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY="re_sprint27_1_configured_key_not_real",
        )
        sender = build_identity_email_sender(cfg)
        assert isinstance(sender, ResendEmailSender)
        assert sender.from_header == "PiqSavi <no-reply@piqsavi.com>"

    def test_staging_uses_resend_when_configured(self) -> None:
        cfg = _settings(
            APP_ENV="staging",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY="re_sprint27_1_configured_key_not_real",
        )
        sender = build_identity_email_sender(cfg)
        assert isinstance(sender, ResendEmailSender)

    def test_unknown_environment_refuses_sender(self) -> None:
        cfg = SimpleNamespace(
            app_env="lab",
            transactional_email_provider="null",
            is_staging=False,
            is_production=False,
        )
        with pytest.raises(ConfigurationValidationError):
            build_identity_email_sender(cfg)  # type: ignore[arg-type]

    def test_staging_validation_rejects_demo_tokens(self) -> None:
        cfg = _settings(
            APP_ENV="staging",
            ALLOW_DEMO_RESET_TOKENS="true",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY="re_sprint27_1_configured_key_not_real",
            PUBLIC_APP_BASE_URL="https://piqsavi.com",
        )
        result = validate_settings(cfg)
        assert result.ok is False
        assert any("ALLOW_DEMO_RESET_TOKENS" in error for error in result.errors)


class TestSenderAndLinks:
    def test_configured_sender_used(self) -> None:
        captured: dict[str, Any] = {}

        def fake_post(url: str, **kwargs: Any) -> httpx.Response:
            captured["url"] = url
            captured["json"] = kwargs["json"]
            captured["auth"] = kwargs["headers"]["Authorization"]
            return httpx.Response(200, json={"id": "msg_1"})

        sender = ResendEmailSender(
            api_key="re_sprint27_1_configured_key_not_real",
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=fake_post,
        )
        sender.send(
            EmailMessage(
                to_address="user@example.com",
                subject=PASSWORD_RESET_SUBJECT,
                body_text="Reset your password",
                body_html="<p>Reset</p>",
            )
        )
        assert captured["url"] == RESEND_EMAILS_URL
        assert captured["json"]["from"] == "PiqSavi <no-reply@piqsavi.com>"
        assert captured["json"]["to"] == ["user@example.com"]
        assert captured["auth"].startswith("Bearer ")
        assert "re_sprint27_1_configured_key_not_real" not in str(captured["json"])

    def test_trusted_base_url_used_and_host_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "app.core.config.settings",
            _settings(PUBLIC_APP_BASE_URL="https://piqsavi.com"),
        )
        auth, _store, sender = make_auth()
        auth.request_password_reset(DEMO_EMAIL)
        assert isinstance(sender, NullEmailSender)
        body = sender.sent[0].body_text
        assert "https://piqsavi.com/reset-password?token=" in body
        assert "evil.example" not in body
        url = build_trusted_action_url("https://piqsavi.com", "/reset-password", "abc")
        assert url == "https://piqsavi.com/reset-password?token=abc"
        with pytest.raises(UserPlatformValidationError):
            build_trusted_action_url("not-a-url", "/reset-password", "abc")

    def test_provider_failure_stays_enumeration_safe(self) -> None:
        def fail(_url: str, **_kwargs: Any) -> httpx.Response:
            return httpx.Response(500, text="provider-secret-body")

        sender = ResendEmailSender(
            api_key="re_sprint27_1_configured_key_not_real",
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=fail,
        )
        auth, store, _sender = make_auth(email_sender=sender)
        known = auth.request_password_reset(DEMO_EMAIL)
        unknown = auth.request_password_reset("ghost@example.com")
        assert known["status"] == unknown["status"] == "accepted"
        assert known["detail"] == unknown["detail"]
        assert known["email_delivery"] is False
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        events = store.audit.list_events(user_id=user.user_id)
        assert any(event.detail == "email_delivery_failed" for event in events)

    def test_provider_error_does_not_leak_body(self) -> None:
        def fail(_url: str, **_kwargs: Any) -> httpx.Response:
            return httpx.Response(401, text="api-key-rejected-secret")

        sender = ResendEmailSender(
            api_key="re_sprint27_1_configured_key_not_real",
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=fail,
        )
        with pytest.raises(EmailDeliveryError, match="Transactional email delivery failed"):
            sender.send(
                EmailMessage(
                    to_address="user@example.com",
                    subject="x",
                    body_text="y",
                )
            )


class TestSecretSafety:
    def test_raw_token_not_in_public_record(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        raw = auth.request_password_reset(DEMO_EMAIL)["reset_token_demo_only"]
        record = store.password_resets.get_by_token_hash(AuthService.hash_token(raw))
        assert record is not None
        public = record.to_dict()
        assert raw not in str(public)
        assert "token_hash" not in public

    def test_exportable_settings_redact_resend_key(self) -> None:
        cfg = _settings(
            APP_ENV="production",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY="re_sprint27_1_configured_key_not_real",
        )
        payload = exportable_settings(cfg)
        assert payload["resend_api_key"] == "***REDACTED***"
        assert "re_sprint27_1_configured_key_not_real" not in str(payload)


class TestHttpRoutes:
    def test_reset_request_enumeration_safe_http(self, client: TestClient) -> None:
        known = client.post("/api/v1/auth/password-reset", json={"email": DEMO_EMAIL})
        unknown = client.post("/api/v1/auth/password-reset", json={"email": "ghost@example.com"})
        assert known.status_code == unknown.status_code == 200
        assert known.json()["status"] == unknown.json()["status"]
        assert known.json()["detail"] == unknown.json()["detail"]
        assert unknown.json().get("reset_token_demo_only") in {None, ""}

    def test_reset_confirm_http(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.auth.service.allows_inline_identity_tokens", lambda: True)
        requested = client.post("/api/v1/auth/password-reset", json={"email": DEMO_EMAIL})
        token = requested.json().get("reset_token_demo_only")
        assert token
        confirm = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "new_password": NEW_PASSWORD},
        )
        assert confirm.status_code == 200
        assert confirm.json()["status"] == "password_changed"
        login = client.post(
            "/api/v1/auth/login",
            json={"email": DEMO_EMAIL, "password": NEW_PASSWORD},
        )
        assert login.status_code == 200

    def test_verify_confirm_http(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.auth.service.allows_inline_identity_tokens", lambda: True)
        requested = client.post("/api/v1/auth/verify-email", json={"email": DEMO_EMAIL})
        token = requested.json().get("verification_token_demo_only")
        assert token
        confirm = client.post(
            "/api/v1/auth/verify-email/confirm",
            json={"token": token},
        )
        assert confirm.status_code == 200
        assert confirm.json()["email_verified"] is True

    def test_staging_http_does_not_expose_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.auth.service.allows_inline_identity_tokens", lambda: False)
        service, _sender = make_platform()
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        with TestClient(app) as test_client:
            known = test_client.post("/api/v1/auth/password-reset", json={"email": DEMO_EMAIL})
            unknown = test_client.post(
                "/api/v1/auth/password-reset", json={"email": "ghost@example.com"}
            )
        app.dependency_overrides.clear()
        assert known.status_code == unknown.status_code == 200
        assert known.json().get("reset_token_demo_only") in {None, ""}
        assert unknown.json().get("reset_token_demo_only") in {None, ""}
        assert known.json()["detail"] == unknown.json()["detail"]

    def test_host_header_cannot_control_action_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        service, sender = make_platform()
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        with TestClient(app) as test_client:
            test_client.post(
                "/api/v1/auth/password-reset",
                json={"email": DEMO_EMAIL},
                headers={"Host": "evil.example"},
            )
        app.dependency_overrides.clear()
        assert sender.sent
        assert "https://piqsavi.com/reset-password?token=" in sender.sent[0].body_text
        assert "evil.example" not in sender.sent[0].body_text
