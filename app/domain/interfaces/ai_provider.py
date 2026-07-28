"""AI provider port interface.

Implementations belong in ``app.infrastructure.ai``.
Future AI modules (LLM, embeddings, agents) should implement this contract.
"""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Abstract contract for AI service integrations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""

    @abstractmethod
    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        """Execute an AI operation and return the result."""
