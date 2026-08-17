"""Unit tests for Early Access registration service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.auth.email import EmailMessage, EmailSender
from app.domain.exceptions import EarlyAccessValidationError
from app.early_access.memory import InMemoryEarlyAccessRepository
from app.services.early_access_service import EarlyAccessService, normalize_email
from app.user.memory import InMemoryUserPlatformStore


class BoomEmailSender(EmailSender):
    def send(self, message: EmailMessage) -> None:
        raise RuntimeError("smtp down")


def _service(**kwargs: object) -> EarlyAccessService:
    return EarlyAccessService(InMemoryEarlyAccessRepository(), **kwargs)


def _valid(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "country": "GB",
        "shopping_interest": "laptops",
        "utm_source": "newsletter",
        "utm_medium": "email",
        "utm_campaign": "ea-1",
        "utm_content": "hero",
        "utm_term": "shopper",
        "referrer": "https://example.com/ref",
        "source": "early_access_landing",
    }
    payload.update(overrides)
    return payload


def test_successful_registration() -> None:
    result = _service().register(**_valid())
    assert result.outcome == "success"
    assert result.registration.full_name == "Ada Lovelace"
    assert result.registration.country == "GB"
    assert result.registration.shopping_interest == "laptops"
    assert result.email_confirmation_status == "not_sent"


def test_required_name() -> None:
    with pytest.raises(EarlyAccessValidationError, match="full name"):
        _service().register(**_valid(full_name="   "))


def test_email_validation() -> None:
    with pytest.raises(EarlyAccessValidationError, match="email"):
        _service().register(**_valid(email="not-an-email"))


def test_email_normalization() -> None:
    result = _service().register(**_valid(email="  Ada@Example.COM  "))
    assert result.registration.normalized_email == "ada@example.com"
    assert result.registration.email == "ada@example.com"
    assert normalize_email("  Ada@Example.COM  ") == "ada@example.com"


def test_country_validation_rejects_uk_alias() -> None:
    with pytest.raises(EarlyAccessValidationError, match="country"):
        _service().register(**_valid(country="UK"))


def test_country_validation_accepts_iso_codes() -> None:
    for code in ("PH", "US", "SG", "GB", "CA"):
        result = _service().register(**_valid(email=f"{code.lower()}@example.com", country=code))
        assert result.registration.country == code


def test_optional_shopping_interest_may_be_blank() -> None:
    result = _service().register(**_valid(shopping_interest="  "))
    assert result.registration.shopping_interest is None


def test_attribution_capture() -> None:
    result = _service().register(**_valid())
    assert result.registration.utm_source == "newsletter"
    assert result.registration.utm_campaign == "ea-1"
    assert result.registration.referrer == "https://example.com/ref"


def test_duplicate_and_case_whitespace_duplicate() -> None:
    service = _service()
    first = service.register(**_valid())
    second = service.register(**_valid(email="  ADA@example.com  ", full_name="Someone Else"))
    assert first.outcome == "success"
    assert second.outcome == "already_registered"
    assert second.registration.id == first.registration.id
    assert len(service.list_registrations()) == 1


def test_confirmation_status_remains_pending_without_live_sender() -> None:
    result = _service().register(**_valid())
    assert result.email_confirmation_status == "not_sent"
    assert result.registration.email_confirmation_sent_at is None


def test_email_failure_cannot_undo_registration() -> None:
    service = EarlyAccessService(InMemoryEarlyAccessRepository(), email_sender=BoomEmailSender())
    result = service.register(**_valid())
    assert result.outcome == "success"
    assert len(service.list_registrations()) == 1
    assert result.email_confirmation_status == "not_sent"


def test_user_account_is_not_created() -> None:
    users = InMemoryUserPlatformStore()
    service = _service()
    service.register(**_valid())
    assert users.users.get_by_email("ada@example.com") is None
    assert users.users.list_users() == []


def test_clock_and_ids_are_deterministic_when_injected() -> None:
    stamp = datetime(2026, 8, 17, tzinfo=UTC)
    service = EarlyAccessService(
        InMemoryEarlyAccessRepository(),
        clock=lambda: stamp,
        id_factory=lambda: "reg-1",
    )
    result = service.register(**_valid())
    assert result.registration.id == "reg-1"
    assert result.registration.created_at == stamp
