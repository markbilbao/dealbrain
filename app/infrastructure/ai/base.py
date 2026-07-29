"""Base AI provider adapter.

Generic ``AIProvider`` remains for future LLM modules. Review-summary adapters
live under ``app.infrastructure.ai.review_providers`` and implement
``AIReviewProvider``.
"""

from app.domain.interfaces.ai_provider import AIProvider

__all__ = ["AIProvider"]
