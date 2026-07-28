"""Base AI provider adapter.

Concrete providers (OpenAI, Anthropic, local models) should subclass
``app.domain.interfaces.ai_provider.AIProvider`` and live in this package.
"""

from app.domain.interfaces.ai_provider import AIProvider

__all__ = ["AIProvider"]
