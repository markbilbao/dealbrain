"""Identity transactional-email ports.

`EmailSender` is the only outbound identity-email boundary. Auth/account
code must not call Resend (or any provider) directly.

Sprint 19 notification email (`EmailNotificationProvider`) is a separate
subsystem and is not used here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class EmailDeliveryError(Exception):
    """Raised when the configured email provider fails to accept a message."""

    def __init__(self, message: str = "Transactional email delivery failed.") -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """Outbound identity email payload."""

    to_address: str
    subject: str
    body_text: str
    body_html: str | None = None
    template_id: str | None = None
    metadata: dict[str, Any] | None = None


class EmailSender(ABC):
    """Port for outbound identity email."""

    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        raise NotImplementedError


class NullEmailSender(EmailSender):
    """Records intent without delivery. Development/test only."""

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


class EmailChangeTokenService(ABC):
    """Architecture interface for issuing email-change confirmation tokens."""

    @abstractmethod
    def issue(self, user_id: str, new_email: str) -> dict[str, Any]:
        raise NotImplementedError
