"""Deterministic community summary provider adapter."""

from __future__ import annotations

from typing import Any

from app.domain.interfaces.community_intelligence_repository import CommunitySummaryProvider
from app.intelligence.community.deterministic import DeterministicCommunitySummaryProvider


class DeterministicCommunityProviderAdapter(CommunitySummaryProvider):
    def __init__(self, inner: DeterministicCommunitySummaryProvider | None = None) -> None:
        self._inner = inner or DeterministicCommunitySummaryProvider()

    @property
    def provider_name(self) -> str:
        return self._inner.provider_name

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    def is_available(self) -> bool:
        return self._inner.is_available()

    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._inner.summarize(payload)
