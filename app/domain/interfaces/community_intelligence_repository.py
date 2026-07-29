"""Ports for Community Intelligence Platform connectors and AI summarizers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence, CommunitySource


class CommunityProvider(ABC):
    """Provider-neutral community source adapter.

    Implementations must not scrape. Live access uses API-backed transports
    when explicitly enabled; otherwise return fixtures / empty.
    """

    @property
    @abstractmethod
    def source_name(self) -> CommunitySource:
        """Stable connector identifier."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Whether this connector is configured to collect."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the connector can serve under current transport/config."""

    @abstractmethod
    def health_check(self) -> bool:
        """Lightweight availability probe (never raises)."""

    @abstractmethod
    def search_product(self, product_id: str, *, product_label: str | None = None) -> list[dict[str, Any]]:
        """Search product-related discussions; return raw provider payloads."""

    @abstractmethod
    def search_threads(self, product_id: str, *, query: str | None = None) -> list[dict[str, Any]]:
        """Search relevant threads for a product."""

    @abstractmethod
    def extract_comments(self, thread_id: str) -> list[dict[str, Any]]:
        """Extract comments/replies for a thread identifier."""

    @abstractmethod
    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[CommunityEvidence]:
        """Collect and return already-normalized evidence for a product."""


class CommunityTransport(ABC):
    """Transport boundary for community APIs (mock / disabled / live)."""

    @abstractmethod
    def fetch(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch a provider payload. Must not leak secrets."""


class CommunitySummaryProvider(ABC):
    """Provider-neutral port for community narrative summarization."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider identifier (e.g. deterministic, openai)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model identifier."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can serve a request under current config."""

    @abstractmethod
    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return summary fields grounded in provided evidence only."""
