"""Sprint 27.3 — transactional email cutover readiness (no live inbox claims)."""

from __future__ import annotations

import importlib.util
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.auth.email import EmailDeliveryError, EmailMessage, NullEmailSender
from app.auth.email_factory import (
    EXTERNAL_EVIDENCE_PENDING,
    allows_inline_identity_tokens,
    build_identity_email_sender,
    build_trusted_action_url,
    identity_email_configured,
    identity_email_status,
)
from app.auth.email_resend import ResendEmailSender
from app.auth.email_templates import (
    EMAIL_CHANGE_NOTICE_SUBJECT,
    EMAIL_CHANGE_SUBJECT,
    EMAIL_VERIFICATION_SUBJECT,
    PASSWORD_RESET_SUBJECT,
    build_email_change_message,
    build_email_changed_notice,
    build_email_verification_message,
    build_password_reset_message,
)
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.config import Settings
from app.core.dependencies import get_user_platform_service
from app.core.public_brand import INTERNAL_CODENAME, PUBLIC_BRAND
from app.core.validation import validate_settings
from app.domain.exceptions import (
    ConfigurationValidationError,
    UserPlatformAuthError,
    UserPlatformValidationError,
)
from app.main import create_app
from app.profile.service import ProfileService
from app.services.launch_health_service import LaunchHealthService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HOST_ASSEMBLE = ROOT / "scripts/deploy/host/assemble-runtime-env.py"
STAGING_EXAMPLE = ROOT / ".env.staging.example"
PRODUCTION_EXAMPLE = ROOT / ".env.production.example"
STAGING_COMPOSE = ROOT / "infra/compose/docker-compose.staging.yml"
PRODUCTION_COMPOSE = ROOT / "infra/compose/docker-compose.production.yml"
DEMO_EMAIL = "student@example.com"
CONFIGURED_KEY = "re_sprint27_3_configured_key_not_real"


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


def _load_assemble_module():
    spec = importlib.util.spec_from_file_location("assemble_runtime_env_27_3", HOST_ASSEMBLE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_auth(
    *,
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
        email_changes=store.email_changes,
        email_sender=sender,
        audit=AuditLogger(store.audit),
    )
    return auth, store, sender


def make_platform() -> tuple[UserPlatformService, InMemoryUserPlatformStore, NullEmailSender]:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    sender = NullEmailSender()
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
    )
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        audit=audit,
    )
    return service, store, sender


@pytest.fixture
def client() -> Iterator[TestClient]:
    service, _store, _sender = make_platform()
    app = create_app()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestDemoTokenPolicy:
    def test_development_may_expose_demo_tokens_when_enabled(self) -> None:
        assert allows_inline_identity_tokens(_settings(APP_ENV="development")) is True

    def test_development_hides_demo_tokens_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.core.config.settings",
            _settings(APP_ENV="development", ALLOW_DEMO_RESET_TOKENS="false"),
        )
        auth, _store, _sender = make_auth()
        reset = auth.request_password_reset(DEMO_EMAIL)
        verify = auth.request_email_verification_by_email(DEMO_EMAIL)
        assert "reset_token_demo_only" not in reset
        assert "verification_token_demo_only" not in verify

    def test_staging_never_exposes_demo_tokens_even_if_flag_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.core.config.settings",
            _settings(APP_ENV="staging", ALLOW_DEMO_RESET_TOKENS="true"),
        )
        auth, _store, _sender = make_auth()
        owner = auth.register(
            email="cutover.owner@example.com",
            password="ValidPass123!",
            display_name="Owner",
        )
        reset = auth.request_password_reset("cutover.owner@example.com")
        verify = auth.request_email_verification_by_email("cutover.owner@example.com")
        change = auth.request_email_change(
            owner.access_token,
            new_email="cutover.new@example.com",
            password="ValidPass123!",
        )
        assert allows_inline_identity_tokens() is False
        assert "reset_token_demo_only" not in reset
        assert "verification_token_demo_only" not in verify
        assert "email_change_token_demo_only" not in change

    def test_production_never_exposes_demo_tokens_even_if_flag_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.core.config.settings",
            _settings(APP_ENV="production", ALLOW_DEMO_RESET_TOKENS="true"),
        )
        auth, _store, _sender = make_auth()
        reset = auth.request_password_reset(DEMO_EMAIL)
        verify = auth.request_email_verification_by_email(DEMO_EMAIL)
        assert allows_inline_identity_tokens() is False
        assert "reset_token_demo_only" not in reset
        assert "verification_token_demo_only" not in verify


class TestSenderConstruction:
    def test_production_rejects_null_sender(self) -> None:
        cfg = _settings(
            APP_ENV="production",
            TRANSACTIONAL_EMAIL_PROVIDER="null",
            RESEND_API_KEY=CONFIGURED_KEY,
        )
        with pytest.raises(ConfigurationValidationError):
            build_identity_email_sender(cfg)

    def test_staging_resend_requires_usable_key_and_from(self) -> None:
        missing_key = _settings(
            APP_ENV="staging",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY="",
        )
        with pytest.raises(EmailDeliveryError, match="Resend API key is not configured"):
            build_identity_email_sender(missing_key)
        placeholder_key = _settings(
            APP_ENV="staging",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY="CHANGE_ME",
        )
        with pytest.raises(EmailDeliveryError, match="Resend API key is not configured"):
            build_identity_email_sender(placeholder_key)
        missing_from = _settings(
            APP_ENV="staging",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY=CONFIGURED_KEY,
            TRANSACTIONAL_EMAIL_FROM="",
        )
        with pytest.raises(
            EmailDeliveryError, match="Transactional sender address is not configured"
        ):
            build_identity_email_sender(missing_from)
        cfg = _settings(
            APP_ENV="staging",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY=CONFIGURED_KEY,
        )
        sender = build_identity_email_sender(cfg)
        assert isinstance(sender, ResendEmailSender)
        assert sender.from_header == "PiqSavi <no-reply@piqsavi.com>"

    def test_invalid_from_address_rejected(self) -> None:
        with pytest.raises(EmailDeliveryError, match="Transactional sender address"):
            ResendEmailSender(
                api_key=CONFIGURED_KEY,
                from_address="not-an-email",
                from_name="PiqSavi",
            )


class TestActionUrls:
    def test_trusted_configured_base_is_used(self) -> None:
        url = build_trusted_action_url("https://staging.piqsavi.com", "/reset-password", "abc")
        assert url == "https://staging.piqsavi.com/reset-password?token=abc"

    def test_malformed_action_base_rejected(self) -> None:
        for base in (
            "",
            "   ",
            "not-a-url",
            "ftp://staging.piqsavi.com",
            "javascript:alert(1)",
            "https://user:pass@staging.piqsavi.com",
            "/relative",
        ):
            with pytest.raises(UserPlatformValidationError):
                build_trusted_action_url(base, "/reset-password", "abc")

    def test_production_http_base_rejected_by_builder_and_validation(self) -> None:
        with pytest.raises(UserPlatformValidationError):
            build_trusted_action_url(
                "http://piqsavi.com",
                "/reset-password",
                "abc",
                require_https=True,
            )
        result = validate_settings(
            _settings(
                APP_ENV="production",
                ALLOW_DEMO_RESET_TOKENS="false",
                TRANSACTIONAL_EMAIL_PROVIDER="resend",
                RESEND_API_KEY=CONFIGURED_KEY,
                PUBLIC_APP_BASE_URL="http://piqsavi.com",
            )
        )
        assert result.ok is False
        assert any("PUBLIC_APP_BASE_URL" in error for error in result.errors)

    def test_forwarded_host_cannot_control_action_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.core.config.settings",
            _settings(PUBLIC_APP_BASE_URL="https://staging.piqsavi.com"),
        )
        service, _store, sender = make_platform()
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        with TestClient(app) as test_client:
            test_client.post(
                "/api/v1/auth/password-reset",
                json={"email": DEMO_EMAIL},
                headers={
                    "Host": "evil.example",
                    "X-Forwarded-Host": "evil.example",
                    "X-Forwarded-Proto": "https",
                    "Forwarded": "host=evil.example;proto=https",
                },
            )
        app.dependency_overrides.clear()
        assert sender.sent
        body = sender.sent[0].body_text
        assert "https://staging.piqsavi.com/reset-password?token=" in body
        assert "evil.example" not in body


class TestReadinessTruth:
    def test_configured_resend_is_not_ready(self) -> None:
        cfg = _settings(
            APP_ENV="staging",
            ALLOW_DEMO_RESET_TOKENS="false",
            TRANSACTIONAL_EMAIL_PROVIDER="resend",
            RESEND_API_KEY=CONFIGURED_KEY,
            PUBLIC_APP_BASE_URL="https://staging.piqsavi.com",
        )
        status = identity_email_status(cfg)
        assert status["adapter"] == "resend"
        assert status["configured"] is True
        assert status["external_evidence"] == EXTERNAL_EVIDENCE_PENDING
        assert status["ready"] is False
        assert identity_email_configured(cfg) is True
        report = LaunchHealthService(cfg=cfg).health()
        assert report.checks["identity_email_adapter"] == "resend"
        assert report.checks["identity_email_ready"] is False

    def test_null_adapter_is_not_configured_or_ready(self) -> None:
        cfg = _settings(
            APP_ENV="staging",
            ALLOW_DEMO_RESET_TOKENS="false",
            TRANSACTIONAL_EMAIL_PROVIDER="null",
        )
        status = identity_email_status(cfg)
        assert status["adapter"] == "null"
        assert status["configured"] is False
        assert status["external_evidence"] == EXTERNAL_EVIDENCE_PENDING
        assert status["ready"] is False


class TestProviderFailureSafety:
    def test_timeout_and_transport_errors_do_not_leak_secrets(self) -> None:
        def timeout(_url: str, **_kwargs: Any) -> httpx.Response:
            raise httpx.TimeoutException("timed out contacting resend")

        sender = ResendEmailSender(
            api_key=CONFIGURED_KEY,
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=timeout,
        )
        with pytest.raises(EmailDeliveryError, match="Transactional email delivery failed") as exc:
            sender.send(
                EmailMessage(
                    to_address="user@example.com",
                    subject="x",
                    body_text="reset-token-should-not-leak",
                )
            )
        text = str(exc.value)
        assert CONFIGURED_KEY not in text
        assert "reset-token-should-not-leak" not in text

    def test_non_2xx_and_invalid_response_do_not_leak_body(self) -> None:
        def redirect(_url: str, **_kwargs: Any) -> httpx.Response:
            return httpx.Response(302, text="secret-redirect-body")

        sender = ResendEmailSender(
            api_key=CONFIGURED_KEY,
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=redirect,
        )
        with pytest.raises(EmailDeliveryError, match="Transactional email delivery failed") as exc:
            sender.send(EmailMessage(to_address="user@example.com", subject="x", body_text="y"))
        assert "secret-redirect-body" not in str(exc.value)

        def invalid(_url: str, **_kwargs: Any) -> object:
            return object()

        sender = ResendEmailSender(
            api_key=CONFIGURED_KEY,
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=invalid,
        )
        with pytest.raises(EmailDeliveryError, match="Transactional email delivery failed"):
            sender.send(EmailMessage(to_address="user@example.com", subject="x", body_text="y"))

    def test_resend_failure_stays_enumeration_safe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings(APP_ENV="staging"))

        def fail(_url: str, **_kwargs: Any) -> httpx.Response:
            return httpx.Response(500, text=f"provider-body-{CONFIGURED_KEY}")

        sender = ResendEmailSender(
            api_key=CONFIGURED_KEY,
            from_address="no-reply@piqsavi.com",
            from_name="PiqSavi",
            http_post=fail,
        )
        auth, _store, _sender = make_auth(email_sender=sender)
        known = auth.request_password_reset(DEMO_EMAIL)
        unknown = auth.request_password_reset("ghost@example.com")
        assert known == unknown
        assert "reset_token_demo_only" not in known
        assert CONFIGURED_KEY not in str(known)
        assert "provider-body" not in str(known)


class TestBranding:
    def test_consumer_templates_use_piqsavi_not_dealbrain(self) -> None:
        messages = [
            build_password_reset_message(
                to_address="a@example.com",
                action_url="https://staging.piqsavi.com/reset-password?token=abc",
            ),
            build_password_reset_message(to_address="a@example.com", action_url=None),
            build_email_verification_message(
                to_address="a@example.com",
                action_url="https://staging.piqsavi.com/verify-email?token=abc",
            ),
            build_email_verification_message(to_address="a@example.com", action_url=None),
            build_email_change_message(
                to_address="a@example.com",
                action_url="https://staging.piqsavi.com/confirm-email-change?token=abc",
            ),
            build_email_change_message(to_address="a@example.com", action_url=None),
            build_email_changed_notice(to_address="old@example.com"),
        ]
        subjects = {
            PASSWORD_RESET_SUBJECT,
            EMAIL_VERIFICATION_SUBJECT,
            EMAIL_CHANGE_SUBJECT,
            EMAIL_CHANGE_NOTICE_SUBJECT,
        }
        for message in messages:
            blob = " ".join(
                part for part in (message.subject, message.body_text, message.body_html) if part
            )
            assert PUBLIC_BRAND in blob
            assert INTERNAL_CODENAME not in blob
            assert message.subject in subjects


class TestHttpAndHtmlDoNotExposeTokens:
    def test_staging_http_bodies_omit_identity_tokens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.auth.service.allows_inline_identity_tokens", lambda: False)
        service, _store, _sender = make_platform()
        owner = service.register(
            email="html.owner@example.com",
            password="ValidPass123!",
            display_name="Owner",
        )
        app = create_app()
        app.dependency_overrides[get_user_platform_service] = lambda: service
        with TestClient(app) as test_client:
            reset = test_client.post(
                "/api/v1/auth/password-reset", json={"email": "html.owner@example.com"}
            )
            verify = test_client.post(
                "/api/v1/auth/verify-email", json={"email": "html.owner@example.com"}
            )
            change = test_client.post(
                "/api/v1/auth/email-change",
                json={"new_email": "html.new@example.com", "password": "ValidPass123!"},
                headers={"Authorization": f"Bearer {owner.access_token}"},
            )
            html_reset = test_client.get("/reset-password")
            html_verify = test_client.get("/verify-email")
        app.dependency_overrides.clear()
        for response in (reset, verify, change):
            assert response.status_code == 200
            body = response.json()
            assert "reset_token_demo_only" not in body
            assert "verification_token_demo_only" not in body
            assert "email_change_token_demo_only" not in body
            assert body.get("email_delivery") is False
        for page in (html_reset, html_verify):
            assert page.status_code == 200
            assert "reset_token_demo_only" not in page.text
            assert "verification_token_demo_only" not in page.text
            assert "email_change_token_demo_only" not in page.text


class TestTokenLifecycleStillBound:
    def test_reset_token_single_use_and_old_sessions_revoked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, _store, _sender = make_auth()
        first = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        raw = auth.request_password_reset(DEMO_EMAIL)["reset_token_demo_only"]
        auth.confirm_password_reset(raw, "Replacement9x")
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(first.access_token)
        with pytest.raises(UserPlatformAuthError):
            auth.confirm_password_reset(raw, "AnotherValid9x")

    def test_purpose_separation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.settings", _settings())
        auth, store, _sender = make_auth()
        owner = auth.register(
            email="purpose@example.com",
            password="ValidPass123!",
            display_name="Purpose",
        )
        reset = auth.request_password_reset("purpose@example.com")["reset_token_demo_only"]
        verify = auth.request_email_verification(owner.user.user_id)["verification_token_demo_only"]
        change = auth.request_email_change(
            owner.access_token,
            new_email="purpose.new@example.com",
            password="ValidPass123!",
        )["email_change_token_demo_only"]
        with pytest.raises(UserPlatformAuthError):
            auth.confirm_password_reset(verify, "Replacement9x")
        with pytest.raises(UserPlatformAuthError):
            auth.confirm_email_verification(reset)
        with pytest.raises(UserPlatformAuthError):
            auth.confirm_email_change(reset)
        with pytest.raises(UserPlatformAuthError):
            auth.confirm_password_reset(change, "Replacement9x")
        user = store.users.get_by_id(owner.user.user_id)
        assert user is not None
        assert user.email == "purpose@example.com"


class TestStagingContractFiles:
    def test_staging_example_forbids_demo_tokens_and_has_resend_contract(self) -> None:
        text = STAGING_EXAMPLE.read_text(encoding="utf-8")
        assert "ALLOW_DEMO_RESET_TOKENS=false" in text
        assert "ALLOW_DEMO_RESET_TOKENS=true" not in text
        assert "TRANSACTIONAL_EMAIL_PROVIDER=resend" in text
        assert "TRANSACTIONAL_EMAIL_FROM=no-reply@piqsavi.com" in text
        assert "TRANSACTIONAL_EMAIL_FROM_NAME=PiqSavi" in text
        assert "PUBLIC_APP_BASE_URL=https://staging.piqsavi.com" in text
        assert "dealbrain/staging/resend_api_key" in text
        assert "RESEND_API_KEY=" not in text
        assert CONFIGURED_KEY not in text
        assert "re_" not in text

    def test_production_example_requires_resend_without_key(self) -> None:
        text = PRODUCTION_EXAMPLE.read_text(encoding="utf-8")
        assert "ALLOW_DEMO_RESET_TOKENS=false" in text
        assert "TRANSACTIONAL_EMAIL_PROVIDER=resend" in text
        assert "PUBLIC_APP_BASE_URL=https://piqsavi.com" in text
        assert "Sprint 41" in text
        assert "RESEND_API_KEY=" not in text

    def test_staging_compose_pins_demo_token_false(self) -> None:
        text = STAGING_COMPOSE.read_text(encoding="utf-8")
        assert 'ALLOW_DEMO_RESET_TOKENS: "false"' in text
        assert 'TRANSACTIONAL_EMAIL_FROM_NAME: "PiqSavi"' in text
        assert "https://staging.piqsavi.com" in text
        assert "dealbrain/staging/resend_api_key" in text

    def test_production_compose_requires_resend(self) -> None:
        text = PRODUCTION_COMPOSE.read_text(encoding="utf-8")
        assert 'TRANSACTIONAL_EMAIL_PROVIDER: "resend"' in text
        assert 'ALLOW_DEMO_RESET_TOKENS: "false"' in text


class TestAssembleRuntimeEnvContract:
    def test_missing_resend_secret_keeps_provider_null(self, tmp_path: Path) -> None:
        mod = _load_assemble_module()
        env_file = tmp_path / "staging.env"
        rds = tmp_path / "rds.json"
        rds.write_text(
            json.dumps(
                {
                    "endpoint": "db.example",
                    "port": 5432,
                    "db_name": "dealbrain",
                    "master_user_secret_arn": "arn:aws:secretsmanager:us-east-1:1:secret:rds",
                }
            ),
            encoding="utf-8",
        )

        def fake_plain(secret_id: str, _region: str) -> str:
            mapping = {
                "dealbrain/staging/app_secret_key": "staging-only-not-for-production-use-32c",
                "dealbrain/staging/cors_origins": "https://staging.piqsavi.com",
            }
            if secret_id not in mapping:
                raise mod.SecretAssemblyError(f"missing {secret_id}")
            return mapping[secret_id]

        def fake_json(_secret_id: str, _region: str) -> dict[str, str]:
            return {"username": "dealbrain", "password": "staging-db-password-ok"}

        previous = os.environ.get("DEALBRAIN_IMAGE")
        os.environ["DEALBRAIN_IMAGE"] = "ghcr.io/example/dealbrain@sha256:abc"
        try:
            mod._get_plain_secret = fake_plain
            mod._get_json_secret = fake_json
            mod.assemble(
                env_file=env_file,
                region="us-east-1",
                rds_nonsecret=rds,
                secrets_prefix="dealbrain/staging",
            )
        finally:
            if previous is None:
                os.environ.pop("DEALBRAIN_IMAGE", None)
            else:
                os.environ["DEALBRAIN_IMAGE"] = previous
        written = env_file.read_text(encoding="utf-8")
        assert 'ALLOW_DEMO_RESET_TOKENS="false"' in written
        assert 'TRANSACTIONAL_EMAIL_PROVIDER="null"' in written
        assert 'TRANSACTIONAL_EMAIL_FROM="no-reply@piqsavi.com"' in written
        assert 'TRANSACTIONAL_EMAIL_FROM_NAME="PiqSavi"' in written
        assert 'PUBLIC_APP_BASE_URL="https://staging.piqsavi.com"' in written
        assert 'RESEND_API_KEY=""' in written
        assert CONFIGURED_KEY not in written

    def test_present_resend_secret_selects_resend_provider(self, tmp_path: Path) -> None:
        mod = _load_assemble_module()
        env_file = tmp_path / "staging.env"
        rds = tmp_path / "rds.json"
        rds.write_text(
            json.dumps(
                {
                    "endpoint": "db.example",
                    "port": 5432,
                    "db_name": "dealbrain",
                    "master_user_secret_arn": "arn:aws:secretsmanager:us-east-1:1:secret:rds",
                }
            ),
            encoding="utf-8",
        )

        def fake_plain(secret_id: str, _region: str) -> str:
            mapping = {
                "dealbrain/staging/app_secret_key": "staging-only-not-for-production-use-32c",
                "dealbrain/staging/cors_origins": "https://staging.piqsavi.com",
                "dealbrain/staging/resend_api_key": CONFIGURED_KEY,
            }
            if secret_id not in mapping:
                raise mod.SecretAssemblyError(f"missing {secret_id}")
            return mapping[secret_id]

        def fake_json(_secret_id: str, _region: str) -> dict[str, str]:
            return {"username": "dealbrain", "password": "staging-db-password-ok"}

        previous = os.environ.get("DEALBRAIN_IMAGE")
        os.environ["DEALBRAIN_IMAGE"] = "ghcr.io/example/dealbrain@sha256:abc"
        try:
            mod._get_plain_secret = fake_plain
            mod._get_json_secret = fake_json
            mod.assemble(
                env_file=env_file,
                region="us-east-1",
                rds_nonsecret=rds,
                secrets_prefix="dealbrain/staging",
            )
        finally:
            if previous is None:
                os.environ.pop("DEALBRAIN_IMAGE", None)
            else:
                os.environ["DEALBRAIN_IMAGE"] = previous
        written = env_file.read_text(encoding="utf-8")
        assert 'TRANSACTIONAL_EMAIL_PROVIDER="resend"' in written
        assert f'RESEND_API_KEY="{CONFIGURED_KEY}"' in written

    def test_placeholder_resend_secret_does_not_select_provider(self) -> None:
        mod = _load_assemble_module()
        assert mod._usable_resend_api_key("") is False
        assert mod._usable_resend_api_key("CHANGE_ME") is False
        assert mod._usable_resend_api_key("${RESEND_API_KEY}") is False
        assert mod._usable_resend_api_key(CONFIGURED_KEY) is True
