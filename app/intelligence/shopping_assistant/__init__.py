"""AI Shopping Assistant intelligence package."""

from app.intelligence.shopping_assistant.candidates import ProductCandidateService
from app.intelligence.shopping_assistant.comparison import ProductComparisonService
from app.intelligence.shopping_assistant.deterministic import (
    DeterministicShoppingExplanationProvider,
)
from app.intelligence.shopping_assistant.evidence import ShoppingEvidenceService
from app.intelligence.shopping_assistant.intent import ShoppingIntentService
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.intelligence.shopping_assistant.recommendation import ShoppingRecommendationRanker
from app.intelligence.shopping_assistant.validator import ShoppingResponseValidator

__all__ = [
    "DeterministicShoppingExplanationProvider",
    "InMemoryConversationRepository",
    "ProductCandidateService",
    "ProductComparisonService",
    "ShoppingAssistantOrchestrator",
    "ShoppingEvidenceService",
    "ShoppingExplanationRegistry",
    "ShoppingIntentService",
    "ShoppingRecommendationRanker",
    "ShoppingResponseValidator",
]
