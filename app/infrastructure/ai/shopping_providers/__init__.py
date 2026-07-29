"""Shopping assistant explanation provider adapters (provider-neutral transport)."""

from app.infrastructure.ai.shopping_providers.base import TransportBackedShoppingProvider
from app.infrastructure.ai.shopping_providers.claude_provider import ClaudeShoppingProvider
from app.infrastructure.ai.shopping_providers.deterministic_provider import (
    DeterministicShoppingProviderAdapter,
)
from app.infrastructure.ai.shopping_providers.gemini_provider import GeminiShoppingProvider
from app.infrastructure.ai.shopping_providers.openai_provider import OpenAIShoppingProvider

__all__ = [
    "ClaudeShoppingProvider",
    "DeterministicShoppingProviderAdapter",
    "GeminiShoppingProvider",
    "OpenAIShoppingProvider",
    "TransportBackedShoppingProvider",
]
