"""Wrap deterministic shopping explainer as a ShoppingExplanationProvider."""

from __future__ import annotations

from typing import Any

from app.domain.interfaces.shopping_assistant_repository import ShoppingExplanationProvider
from app.intelligence.shopping_assistant.deterministic import (
    DeterministicShoppingExplanationProvider,
)


class DeterministicShoppingProviderAdapter(ShoppingExplanationProvider):
    def __init__(self, inner: DeterministicShoppingExplanationProvider | None = None) -> None:
        self._inner = inner or DeterministicShoppingExplanationProvider()

    @property
    def provider_name(self) -> str:
        return self._inner.provider_name

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    def is_available(self) -> bool:
        return self._inner.is_available()

    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._inner.explain(payload)
