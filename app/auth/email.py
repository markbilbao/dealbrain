"""Email delivery interfaces only — Sprint 17 does not send email.

Password reset and email verification architecture lives here as ports.
Concrete SMTP / SES / SendGrid adapters are intentionally out of scope.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """Outbound email payload for a future delivery adapter."""

    to_address: str
    subject: str
    body_text: str
    body_html: str | None = None
    template_id: str | None = None
    metadata: dict[str, Any] | None = None


class EmailSender(ABC):
    """Port for outbound email. No implementation ships in Sprint 17."""

    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        raise NotImplementedError


class NullEmailSender(EmailSender):
    """No-op sender used by default — records intent without delivery."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class PasswordResetTokenService(ABC):
    """Architecture interface for issuing password-reset tokens."""

    @abstractmethod
    def issue(self, user_id: str, email: str) -> dict[str, Any]:
        raise NotImplementedError


class EmailVerificationTokenService(ABC):
    """Architecture interface for issuing email-verification tokens."""

    @abstractmethod
    def issue(self, user_id: str, email: str) -> dict[str, Any]:
        raise NotImplementedError
