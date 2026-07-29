"""Email notification provider port — Sprint 19.

All implementations are simulated. No live SMTP/API transport exists in this
codebase; :class:`MockEmailNotificationProvider` is the only concrete
implementation and its result detail always makes the simulation explicit.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

SIMULATED_EMAIL_MARKER = "SIMULATED EMAIL — NO REAL MESSAGE SENT"


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """A plain email payload — already-rendered subject and body."""

    to_address: str
    subject: str
    body_text: str
    body_html: str | None = None


@dataclass(frozen=True, slots=True)
class EmailSendResult:
    """Outcome of an :meth:`EmailNotificationProvider.send` call."""

    message_id: str
    to_address: str
    subject: str
    sent_at: datetime
    simulated: bool
    detail: str
    metadata: dict[str, str] = field(default_factory=dict)


class EmailNotificationProvider(ABC):
    """Port for sending a rendered email message.

    Implementations MUST NOT perform real network I/O to an email transport
    in this codebase; the sole concrete implementation
    (:class:`MockEmailNotificationProvider`) always simulates delivery.
    """

    @abstractmethod
    def send(self, message: EmailMessage) -> EmailSendResult:
        """ "Send" (simulate sending) an email message and return the result."""


class MockEmailNotificationProvider(EmailNotificationProvider):
    """Always-simulated email provider — never sends a real message.

    Every result's ``detail`` includes the literal marker
    ``"SIMULATED EMAIL — NO REAL MESSAGE SENT"`` so downstream consumers and
    tests can assert no real delivery is implied.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._sent: list[EmailSendResult] = []

    def send(self, message: EmailMessage) -> EmailSendResult:
        result = EmailSendResult(
            message_id=self._id_factory(),
            to_address=message.to_address,
            subject=message.subject,
            sent_at=self._clock(),
            simulated=True,
            detail=(
                f"{SIMULATED_EMAIL_MARKER}. Would have sent "
                f"'{message.subject}' to {message.to_address}."
            ),
            metadata={"body_length": str(len(message.body_text))},
        )
        self._sent.append(result)
        return result

    @property
    def sent_messages(self) -> list[EmailSendResult]:
        """All simulated sends recorded in this process (tests / demo)."""
        return list(self._sent)

    def clear(self) -> None:
        self._sent.clear()
