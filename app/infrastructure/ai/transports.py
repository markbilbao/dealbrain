"""AI provider transports — live HTTP disabled by default.

Adapters depend on this boundary so OpenAI / Claude / Gemini SDKs are not
required for Sprint 12. Tests inject ``ScriptedTransport`` responses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.domain.exceptions import (
    AIProviderMalformedResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """Raw provider completion payload (already server-side)."""

    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    estimated_cost_usd: float | None = None
    latency_ms: int | None = None
    raw: dict[str, Any] | None = None


class ProviderTransport(ABC):
    """Transport boundary for provider adapters."""

    @abstractmethod
    def complete(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> TransportResponse:
        """Execute a completion. Must never leak API keys."""


class DisabledTransport(ProviderTransport):
    """Default transport — blocks all live external AI HTTP calls."""

    def complete(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> TransportResponse:
        raise AIProviderUnavailableError(
            provider,
            "live AI HTTP is disabled (AI_REVIEW_LIVE_HTTP=false)",
            error_code="unavailable",
        )


class ScriptedTransport(ProviderTransport):
    """Test / demo transport returning a preloaded JSON string or error."""

    def __init__(
        self,
        content: str | None = None,
        *,
        error: Exception | None = None,
        prompt_tokens: int | None = 100,
        completion_tokens: int | None = 200,
        estimated_cost_usd: float | None = 0.002,
        latency_ms: int | None = 12,
    ) -> None:
        self._content = content
        self._error = error
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self._estimated_cost_usd = estimated_cost_usd
        self._latency_ms = latency_ms
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float,
    ) -> TransportResponse:
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "timeout_seconds": timeout_seconds,
                # Store lengths only — never persist full prompts in call logs used by APIs.
                "system_prompt_chars": len(system_prompt),
                "user_prompt_chars": len(user_prompt),
            }
        )
        if self._error is not None:
            raise self._error
        if self._content is None:
            raise AIProviderUnavailableError(provider, "no scripted response configured")
        return TransportResponse(
            content=self._content,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            estimated_cost_usd=self._estimated_cost_usd,
            latency_ms=self._latency_ms,
        )


def raise_typed_transport_error(provider: str, code: str) -> None:
    """Helper for scripted failure injection in tests."""
    if code == "timeout":
        raise AIProviderTimeoutError(provider, 0.01)
    if code == "rate_limited":
        raise AIProviderRateLimitError(provider)
    if code == "malformed":
        raise AIProviderMalformedResponseError(provider, "not valid JSON")
    raise AIProviderUnavailableError(provider, code, error_code=code)
