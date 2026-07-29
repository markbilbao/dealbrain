"""AI Shopping Assistant — Sprint 13.

Status: implemented (multi-model narrative layer; external AI disabled by default)
Date: 2026-07-29

Scope
-----
Answer product-shopping questions using DealBrain’s existing intelligence
signals and a mock/imported shopping catalog. The assistant combines evidence
from product identity, marketplace offers, price history, DealScore,
recommendation ranking, marketplace/seller signals, review insights, and
review-summary themes when available in the catalog.

External AI providers remain optional and **disabled by default**. Deterministic
intent parsing, ranking, comparison, confidence, and buy/wait logic always run
in application code.

See also:

- ``docs/SHOPPING_ASSISTANT_API.md``
- ``docs/SHOPPING_ASSISTANT_SAFETY.md``
- ``docs/MULTI_MODEL_AI_ARCHITECTURE.md``
- ``docs/AI_PROVIDER_SETUP.md``

Supported question types
------------------------
- Best product under a budget
- Product comparison
- Worth buying?
- Best marketplace offer among known data
- Main complaints
- Buy now or wait (limited, evidence-based)
- Better for gaming / photography / other use cases
- Cheapest-seller trustworthiness (qualified)
- Budget + needs recommendation

Architecture
------------
```
Presentation (demo.html — Shopping Assistant panel)
  ↓
API (/api/v1/shopping-assistant/query|demo|meta)
  ↓
ShoppingAssistantService
  ├── ShoppingIntentService
  ├── ProductCandidateService
  ├── ShoppingEvidenceService
  ├── ShoppingRecommendationRanker
  ├── ProductComparisonService
  ├── ConfidenceCalculator / buy-now-or-wait
  ├── ShoppingResponseValidator
  ├── InMemoryConversationRepository
  └── ShoppingAssistantOrchestrator
        ├── ShoppingExplanationRegistry
        └── ShoppingConsensusService
  ↓
ShoppingExplanationProvider adapters
  (OpenAI · Claude · Gemini · Deterministic) via ProviderTransport
```

Domain
------
Key types in ``app/domain/entities/shopping_assistant.py``:

- ``ShoppingQuery``, ``ShoppingIntent``, ``ShoppingConstraint``
- ``ShoppingCandidate``, ``ShoppingEvidence``, ``ShoppingRecommendation``
- ``ProductComparison``, ``AssistantConfidence``, ``AssistantWarning``
- ``ShoppingAssistantResponse``, conversation context types

Deterministic vs AI
-------------------
Deterministic application code owns:

- budget / currency / use-case extraction (with optional AI later)
- candidate filtering and ranking
- DealScore / rating / review-count comparisons
- confidence bands
- buy-now-or-wait signals from known history fields
- unsupported-claim validation

AI (when enabled) may only:

- interpret intent beyond the deterministic parser
- summarize / narrate explanations
- present comparison narratives
- validate claims in balanced/maximum modes

AI must not invent prices, ratings, reviews, sellers, or availability.

Modes
-----
- ``economy`` — deterministic analysis + one configured provider when enabled
- ``balanced`` — primary explains, secondary validates important claims
- ``maximum`` — configured providers analyze the same structured evidence; consensus resolves supported findings; disagreements are surfaced

Client ``mode`` cannot exceed server ``AI_SHOPPING_MODE``.

Data status labels
------------------
- ``mock`` — demo catalog / fixtures (default for v1)
- ``imported`` — imported offline data
- ``live`` — reserved; v1 does not claim live marketplace access

Confidence
----------
Score combines evidence count, marketplace coverage, review volume, rating
consistency, missing attributes, mock-data penalty, and optional provider
agreement. Display bands: High / Medium / Low. Scores are capped to avoid
false precision.

Buy now or wait
---------------
Uses known price-history direction, near-low flags, and DealScore. Never claims
future prices with certainty.

Protected modules (unchanged)
-----------------------------
Product Identity, Marketplace Collection, Price History, DealScore,
Recommendation Engine, Marketplace Intelligence, Collection Operations,
Watchlists and Price Alerts, Review & Rating Intelligence, AI Review Summary,
Multi-Model AI Provider Architecture (transport / review providers).

Known limitations
-----------------
- Catalog coverage is intentionally incomplete mock/imported data.
- No live scraping or live marketplace APIs.
- Seller trust scores are mock signals, not authenticity guarantees.
- Conversation context is in-memory with TTL and is not durable across restarts.
"""
