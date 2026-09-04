"""Resend-backed EmailSender adapter for identity transactional mail.

No API key, recipient, or raw token is logged. Provider response bodies are
not surfaced to callers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from app.auth.email import EmailDeliveryError, EmailMessage, EmailSender

RESEND_EMAILS_URL = "https://api.resend.com/emails"
_DEFAULT_TIMEOUT_SECONDS = 10.0


class ResendEmailSender(EmailSender):
    """Deliver identity email through the Resend HTTP API."""

    def __init__(
        self,
        *,
        api_key: str,
        from_address: str,
        from_name: str,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        http_post: Callable[..., httpx.Response] | None = None,
    ) -> None:
        key = (api_key or "").strip()
        sender = (from_address or "").strip()
        if not key:
            raise EmailDeliveryError("Resend API key is not configured.")
        if not sender:
            raise EmailDeliveryError("Transactional sender address is not configured.")
        self._api_key = key
        self._from_address = sender
        self._from_name = (from_name or "").strip()
        self._timeout = timeout_seconds
        self._http_post = http_post or self._default_http_post

    @property
    def from_header(self) -> str:
        if self._from_name:
            return f"{self._from_name} <{self._from_address}>"
        return self._from_address

    def send(self, message: EmailMessage) -> None:
        payload: dict[str, Any] = {
            "from": self.from_header,
            "to": [message.to_address],
            "subject": message.subject,
            "text": message.body_text,
        }
        if message.body_html:
            payload["html"] = message.body_html
        try:
            response = self._http_post(
                RESEND_EMAILS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        except EmailDeliveryError:
            raise
        except Exception as exc:
            raise EmailDeliveryError("Transactional email delivery failed.") from exc
        if response.status_code >= 400:
            raise EmailDeliveryError("Transactional email delivery failed.")

    def _default_http_post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        return httpx.post(url, json=json, headers=headers, timeout=timeout)
