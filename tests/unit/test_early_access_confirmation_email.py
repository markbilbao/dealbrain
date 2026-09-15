"""Early Access confirmation-email send, persist, and copy tests."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest
from app.auth.email import EmailDeliveryError, EmailMessage, EmailSender, NullEmailSender
from app.auth.email_factory import build_identity_email_sender
from app.auth.email_resend import ResendEmailSender
from app.core.config import Settings
from app.core.dependencies import get_early_access_service
from app.domain.exceptions import ConfigurationValidationError
from app.early_access.confirmation_email import (
    CONFIRMATION_SUBJECT,
    build_early_access_confirmation_message,
    greeting_first_name,
)
from app.early_access.memory import InMemoryEarlyAccessRepository
from app.main import create_app
from app.services.early_access_service import EarlyAccessService
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient


class RecordingEmailSender(EmailSender):
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class BoomEmailSender(EmailSender):
    def send(self, message: EmailMessage) -> None:
        raise EmailDeliveryError("Transactional email delivery failed.")


class LeakyFailSender(EmailSender):
    def send(self, message: EmailMessage) -> None:
        raise EmailDeliveryError("provider rejected key=re_secret_should_never_appear")


class PendingObserver(EmailSender):
    def __init__(self, repo: InMemoryEarlyAccessRepository) -> None:
        self._repo = repo
        self.pending_seen = False
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        loaded = self._repo.get_by_normalized_email(message.to_address)
        self.pending_seen = loaded is not None and loaded.email_confirmation_status == "pending"
        self.sent.append(message)


def _valid(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "country": "GB",
        "shopping_interest": "laptops",
        "policies_acknowledged": True,
    }
    payload.update(overrides)
    return payload


def _service(
    repo: InMemoryEarlyAccessRepository | None = None,
    **kwargs: object,
) -> tuple[EarlyAccessService, InMemoryEarlyAccessRepository]:
    store = repo or InMemoryEarlyAccessRepository()
    return EarlyAccessService(store, **kwargs), store


def _prod_settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "_env_file": None,
        "APP_ENV": "production",
        "TRANSACTIONAL_EMAIL_PROVIDER": "resend",
        "RESEND_API_KEY": "re_early_access_test_key_not_real",
        "TRANSACTIONAL_EMAIL_FROM": "no-reply@piqsavi.com",
        "TRANSACTIONAL_EMAIL_FROM_NAME": "PiqSavi",
        "PUBLIC_APP_BASE_URL": "https://piqsavi.com",
        "ALLOW_DEMO_RESET_TOKENS": "false",
    }
    payload.update(overrides)
    return Settings(**payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Copy / first-name / HTML
# ---------------------------------------------------------------------------


def test_greeting_uses_first_usable_word() -> None:
    assert greeting_first_name("Ada Lovelace") == "Ada"
    assert greeting_first_name("  José  García ") == "José"


def test_greeting_falls_back_when_name_is_awkward() -> None:
    assert greeting_first_name("") is None
    assert greeting_first_name("   ") is None
    assert greeting_first_name("12345") is None
    assert greeting_first_name("user@example.com") is None
    assert greeting_first_name("../evil") is None


def test_confirmation_copy_and_html_escape() -> None:
    message = build_early_access_confirmation_message(
        to_address="ada@example.com",
        full_name="Ada&Eve <script>alert(1)</script>",
    )
    assert message.subject == "You're on the PiqSavi Early Access list"
    assert message.to_address == "ada@example.com"
    assert message.body_text.startswith("Hi Ada&Eve,")
    assert "You're officially on the PiqSavi Early Access list." in message.body_text
    assert "We'll let you know when Early Access opens." in message.body_text
    assert "PiqSavi — Your AI Personal Shopper" in message.body_text
    assert "Buy Smarter." in message.body_text
    assert "unsubscribe" not in message.body_text.lower()
    assert "verify" not in message.body_text.lower()
    assert "login" not in message.body_text.lower()
    assert "affiliate" not in message.body_text.lower()
    assert "shopee" not in message.body_text.lower()
    assert "lazada" not in message.body_text.lower()
    assert message.body_html is not None
    assert "<script>" not in message.body_html
    assert "Hi Ada&Eve," not in message.body_html
    assert "Hi Ada&amp;Eve," in message.body_html
    assert "You're officially on the PiqSavi Early Access list." in message.body_html


def test_confirmation_falls_back_to_hi_there() -> None:
    message = build_early_access_confirmation_message(
        to_address="anon@example.com",
        full_name="***",
    )
    assert message.body_text.startswith("Hi there,")
    assert message.body_html is not None
    assert "<p>Hi there,</p>" in message.body_html


# ---------------------------------------------------------------------------
# Successful / failed / null senders
# ---------------------------------------------------------------------------


def test_successful_sender_persists_sent_and_sends_once() -> None:
    sender = RecordingEmailSender()
    stamp = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
    service, repo = _service(email_sender=sender, clock=lambda: stamp, id_factory=lambda: "reg-1")
    result = service.register(**_valid(email="  Ada@Example.COM  "))
    assert result.outcome == "success"
    assert result.email_confirmation_status == "sent"
    assert result.registration.email_confirmation_status == "sent"
    assert result.registration.email_confirmation_sent_at == stamp
    assert len(sender.sent) == 1
    message = sender.sent[0]
    assert message.to_address == "ada@example.com"
    assert message.subject == CONFIRMATION_SUBJECT
    assert message.body_text.startswith("Hi Ada,")
    assert "You're officially on the PiqSavi Early Access list." in message.body_text
    loaded = repo.get_by_normalized_email("ada@example.com")
    assert loaded is not None
    assert loaded.email_confirmation_status == "sent"
    assert loaded.email_confirmation_sent_at == stamp
    assert loaded.terms_version_id is not None
    assert loaded.privacy_version_id is not None
    assert loaded.policies_acknowledged_at == stamp


def test_pending_is_persisted_before_send() -> None:
    repo = InMemoryEarlyAccessRepository()
    sender = PendingObserver(repo)
    service = EarlyAccessService(repo, email_sender=sender)
    result = service.register(**_valid())
    assert sender.pending_seen is True
    assert result.email_confirmation_status == "sent"
    assert len(sender.sent) == 1


def test_failed_sender_keeps_registration_and_reports_failed() -> None:
    service, repo = _service(email_sender=BoomEmailSender())
    result = service.register(**_valid())
    assert result.outcome == "success"
    assert result.email_confirmation_status == "failed"
    assert result.registration.email_confirmation_sent_at is None
    stored = repo.get_by_normalized_email("ada@example.com")
    assert stored is not None
    assert stored.email_confirmation_status == "failed"
    assert stored.email_confirmation_sent_at is None
    assert stored.terms_version_id is not None
    assert stored.privacy_version_id is not None


def test_null_sender_does_not_fake_sent() -> None:
    sender = NullEmailSender()
    service, repo = _service(email_sender=sender)
    result = service.register(**_valid())
    assert result.outcome == "success"
    assert result.email_confirmation_status == "not_sent"
    assert result.registration.email_confirmation_sent_at is None
    assert sender.sent == []
    stored = repo.get_by_normalized_email("ada@example.com")
    assert stored is not None
    assert stored.email_confirmation_status == "not_sent"


def test_duplicate_does_not_resend_and_preserves_status() -> None:
    sender = RecordingEmailSender()
    service, _repo = _service(email_sender=sender)
    first = service.register(**_valid())
    assert first.email_confirmation_status == "sent"
    assert len(sender.sent) == 1
    second = service.register(**_valid(email="  ADA@example.com  ", full_name="Someone Else"))
    assert second.outcome == "already_registered"
    assert second.registration.id == first.registration.id
    assert second.email_confirmation_status == "sent"
    assert second.registration.email_confirmation_status == "sent"
    assert len(sender.sent) == 1
    assert len(service.list_registrations()) == 1


def test_duplicate_preserves_failed_status_without_resend() -> None:
    service, _repo = _service(email_sender=BoomEmailSender())
    first = service.register(**_valid())
    assert first.email_confirmation_status == "failed"
    second = service.register(**_valid())
    assert second.outcome == "already_registered"
    assert second.email_confirmation_status == "failed"
    assert second.registration.email_confirmation_sent_at is None


def test_user_account_is_not_created_when_email_sends() -> None:
    users = InMemoryUserPlatformStore()
    service, _repo = _service(email_sender=RecordingEmailSender())
    service.register(**_valid())
    assert users.users.get_by_email("ada@example.com") is None
    assert users.users.list_users() == []


def test_status_persist_failure_after_send_does_not_fake_sent() -> None:
    class _FailSentRepo(InMemoryEarlyAccessRepository):
        def update_email_confirmation(self, registration_id, **kwargs):  # noqa: ANN001
            if kwargs.get("status") == "sent":
                raise RuntimeError("cannot persist sent")
            return super().update_email_confirmation(registration_id, **kwargs)

    sender = RecordingEmailSender()
    service, repo = _service(_FailSentRepo(), email_sender=sender)
    result = service.register(**_valid())
    assert result.outcome == "success"
    assert result.email_confirmation_status == "pending"
    assert result.registration.email_confirmation_status == "pending"
    assert result.registration.email_confirmation_sent_at is None
    assert len(sender.sent) == 1
    assert len(repo.list_all()) == 1


def test_status_persist_failure_never_raises_out_of_register() -> None:
    class _FailAllUpdates(InMemoryEarlyAccessRepository):
        def update_email_confirmation(self, registration_id, **kwargs):  # noqa: ANN001
            raise RuntimeError("disk full")

    sender = RecordingEmailSender()
    service, repo = _service(_FailAllUpdates(), email_sender=sender)
    result = service.register(**_valid())
    assert result.outcome == "success"
    assert result.email_confirmation_status == "not_sent"
    assert len(sender.sent) == 1
    assert len(repo.list_all()) == 1


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_api_reports_sent_after_successful_sender() -> None:
    api_repo = InMemoryEarlyAccessRepository()
    sender = RecordingEmailSender()
    app = create_app()
    service = EarlyAccessService(api_repo, email_sender=sender)
    app.dependency_overrides[get_early_access_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/api/v1/early-access", json=_valid())
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "success"
    assert body["email_confirmation_status"] == "sent"
    assert body["message"] == "You're on the list."
    assert len(sender.sent) == 1


def test_api_reports_failed_without_http_500(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api_repo = InMemoryEarlyAccessRepository()
    app = create_app()
    service = EarlyAccessService(api_repo, email_sender=LeakyFailSender())
    app.dependency_overrides[get_early_access_service] = lambda: service
    with caplog.at_level("WARNING"), TestClient(app) as client:
        response = client.post("/api/v1/early-access", json=_valid())
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "success"
    assert body["email_confirmation_status"] == "failed"
    assert body["message"] == "You're on the list."
    dumped = str(body) + caplog.text
    assert "re_secret_should_never_appear" not in dumped
    assert "ada@example.com" not in caplog.text
    assert "RESEND_API_KEY" not in dumped


def test_api_duplicate_does_not_resend() -> None:
    repo = InMemoryEarlyAccessRepository()
    sender = RecordingEmailSender()
    app = create_app()
    service = EarlyAccessService(repo, email_sender=sender)
    app.dependency_overrides[get_early_access_service] = lambda: service
    with TestClient(app) as client:
        first = client.post("/api/v1/early-access", json=_valid())
        second = client.post("/api/v1/early-access", json=_valid(full_name="Other"))
    app.dependency_overrides.clear()
    assert first.status_code == 200
    assert first.json()["email_confirmation_status"] == "sent"
    assert second.status_code == 200
    assert second.json()["outcome"] == "already_registered"
    assert second.json()["email_confirmation_status"] == "sent"
    assert len(sender.sent) == 1


# ---------------------------------------------------------------------------
# Production / factory wiring
# ---------------------------------------------------------------------------


def test_provider_source_uses_identity_email_factory() -> None:
    source = inspect.getsource(get_early_access_service)
    assert "build_identity_email_sender" in source
    assert "email_sender=" in source
    assert "ResendEmailSender(" not in source
    service_source = inspect.getsource(EarlyAccessService)
    assert "ResendEmailSender(" not in service_source
    assert "api.resend.com" not in service_source
    confirm_source = inspect.getsource(build_early_access_confirmation_message)
    assert "ResendEmailSender" not in confirm_source


def test_production_factory_cannot_silently_use_null_sender() -> None:
    with pytest.raises(ConfigurationValidationError, match="NullEmailSender is not permitted"):
        build_identity_email_sender(_prod_settings(TRANSACTIONAL_EMAIL_PROVIDER="null"))
    sender = build_identity_email_sender(_prod_settings())
    assert isinstance(sender, ResendEmailSender)
    assert sender.from_header == "PiqSavi <no-reply@piqsavi.com>"


def test_development_factory_may_use_null_sender() -> None:
    cfg = Settings(
        _env_file=None,  # type: ignore[arg-type]
        APP_ENV="development",
        TRANSACTIONAL_EMAIL_PROVIDER="null",
    )
    sender = build_identity_email_sender(cfg)
    assert isinstance(sender, NullEmailSender)


def test_get_early_access_service_injects_factory_sender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.dependencies as deps

    captured: dict[str, object] = {}

    def _fake_factory(cfg: Settings | None = None) -> RecordingEmailSender:
        captured["called"] = True
        captured["cfg"] = cfg
        return RecordingEmailSender()

    monkeypatch.setattr(deps, "_EARLY_ACCESS_SERVICE", None)
    monkeypatch.setattr(
        "app.auth.email_factory.build_identity_email_sender",
        _fake_factory,
    )
    try:
        service = deps.get_early_access_service()
        assert captured["called"] is True
        assert isinstance(service._email, RecordingEmailSender)
    finally:
        deps._EARLY_ACCESS_SERVICE = None


def test_production_get_early_access_service_refuses_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.dependencies as deps

    cfg = _prod_settings(
        TRANSACTIONAL_EMAIL_PROVIDER="null",
        PERSISTENCE_BACKEND="memory",
    )
    monkeypatch.setattr(deps, "settings", cfg)
    monkeypatch.setattr(deps, "_EARLY_ACCESS_SERVICE", None)
    monkeypatch.setattr(deps, "get_early_access_repository", InMemoryEarlyAccessRepository)
    try:
        with pytest.raises(ConfigurationValidationError, match="NullEmailSender is not permitted"):
            deps.get_early_access_service()
    finally:
        deps._EARLY_ACCESS_SERVICE = None


def test_production_runtime_email_contract_is_resend_piqsavi() -> None:
    """Configuration presence only — never read or print secret values."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    compose = (root / "infra/compose/docker-compose.production.yml").read_text(encoding="utf-8")
    assemble = (root / "scripts/deploy/host/assemble-runtime-env.py").read_text(encoding="utf-8")
    example = (root / ".env.production.example").read_text(encoding="utf-8")
    assert 'TRANSACTIONAL_EMAIL_PROVIDER: "resend"' in compose
    assert 'TRANSACTIONAL_EMAIL_FROM_NAME: "PiqSavi"' in compose
    assert 'TRANSACTIONAL_EMAIL_FROM = "no-reply@piqsavi.com"' in assemble
    assert 'TRANSACTIONAL_EMAIL_FROM_NAME = "PiqSavi"' in assemble
    assert 'mapping["TRANSACTIONAL_EMAIL_PROVIDER"] = "resend"' in assemble
    assert '("resend_api_key", "RESEND_API_KEY")' in assemble
    assert "TRANSACTIONAL_EMAIL_FROM=no-reply@piqsavi.com" in example
    assert "TRANSACTIONAL_EMAIL_FROM_NAME=PiqSavi" in example
    assert "re_" not in example
    assert "re_" not in compose


def test_acknowledgement_still_required_with_live_sender() -> None:
    from app.domain.exceptions import EarlyAccessValidationError

    sender = RecordingEmailSender()
    service, repo = _service(email_sender=sender)
    with pytest.raises(EarlyAccessValidationError, match="Terms of Service"):
        service.register(**_valid(policies_acknowledged=False))
    assert sender.sent == []
    assert repo.list_all() == []
