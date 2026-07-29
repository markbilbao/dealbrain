"""Community connector transports — mock / disabled by default, no secrets."""

from __future__ import annotations

from typing import Any

from app.domain.exceptions import AIProviderUnavailableError
from app.domain.interfaces.community_intelligence_repository import CommunityTransport


class DisabledCommunityTransport(CommunityTransport):
    """Refuse all live fetches. Used when connectors are disabled."""

    def fetch(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        raise AIProviderUnavailableError(
            "community",
            f"live community transport disabled for path={path}",
            error_code="disabled",
        )


class MockCommunityTransport(CommunityTransport):
    """Deterministic in-memory transport for fixture-backed connectors."""

    def __init__(self, payloads: dict[str, dict[str, Any]] | None = None) -> None:
        self._payloads = payloads or {}
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def fetch(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((path, params))
        if path in self._payloads:
            return dict(self._payloads[path])
        return {"path": path, "params": params or {}, "items": []}


class ScriptedCommunityTransport(CommunityTransport):
    """Return a scripted sequence of responses (tests)."""

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self._responses = list(responses or [])
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def fetch(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((path, params))
        if not self._responses:
            return {"path": path, "items": []}
        return dict(self._responses.pop(0))
