"""AI Review Summary & Sentiment Intelligence — Sprint 12.

Status: implemented (multi-model architecture; external AI disabled by default)
Date: 2026-07-29

Scope
-----
Analyze Sprint 11 Review Intelligence outputs plus mock review text fixtures
to produce shopping insights: overall sentiment, summary paragraph, ranked
pros / cons, warnings, and a purchase recommendation.

External AI providers (OpenAI, Claude, Gemini) are integrated behind a
provider-neutral port. Live HTTP is **disabled by default**. The deterministic
summarizer remains the always-available fallback.

See also:

- ``docs/MULTI_MODEL_AI_ARCHITECTURE.md``
- ``docs/AI_PROVIDER_SETUP.md``

Architecture
------------
```
Presentation (demo.html — Review Summary panel)
  ↓
API (/api/v1/review-summary[?mode=])
  ↓
ReviewSummaryService
  ↓
MultiModelReviewOrchestrator
  ├── AIProviderRegistry
  ├── ReviewAnalysisValidator
  ├── ConsensusService
  └── ProviderHealthService
  ↓
AIReviewProvider adapters
  (OpenAI · Claude · Gemini · Deterministic)
  ↓
Review Intelligence inputs + mock / imported review texts
```

Domain
------
``ReviewSummary`` fields:

- ``summary_id`` / ``product_id`` / ``product``
- ``overall_sentiment``
- ``summary`` (paragraph)
- ``pros`` / ``cons`` / ``warnings`` / ``recommendation``
- ``insights`` (ranked theme hits)
- ``average_rating`` / ``total_review_count``
- ``provider`` / ``generated_at``
- Multi-model metadata: ``mode``, ``providers_used``, ``fallback_used``,
  ``agreement_score``, ``consensus_confidence``, ``disagreements``,
  ``evidence_*``, ``processing``

Supporting value objects: ``Pros``, ``Cons``, ``Warning``,
``Recommendation``, ``ReviewInsight``, plus analysis types in
``review_analysis.py`` (``EvidenceClaim``, ``ProviderAnalysis``,
``ConsensusMetadata``).

Modes
-----
- ``economy`` — primary provider, deterministic fallback
- ``balanced`` — primary + secondary critique/validation
- ``maximum`` — OpenAI + Claude + Gemini consensus with disagreement reporting

Client ``?mode=`` cannot exceed server ``AI_REVIEW_MODE``.

Repository / ports
------------------
``ReviewSummaryRepository`` (in-memory):

- ``save()``
- ``get_by_product_id()``

``ReviewSummarizer`` (legacy deterministic port) remains for compatibility.

``AIReviewProvider`` (multi-model port):

- ``analyze_reviews(...)``
- ``provider_name`` / ``model_name``
- ``is_available()``

Services
--------
``ReviewSummaryService``:

- ``summarize(product_id, mode=...)``
- ``get_summary(product_id, mode=...)``
- ``demo_summary(mode=...)``

Sentiment rules (deterministic provider)
----------------------------------------
- average rating ``> 4.6`` → Very Positive
- ``4.2``–``4.6`` → Positive
- ``3.8``–``4.2`` → Mixed
- else → Negative

API endpoints
-------------
Base path: ``/api/v1/review-summary``

- ``GET /review-summary/{product_id}?mode=economy|balanced|maximum``
- ``GET /review-summary/demo?mode=...``

Responses include mode, providers used, fallback status, agreement score when
applicable, evidence references, and processing metadata. Secrets and prompts
are never included.

Protected modules (unchanged)
-----------------------------
- Product Identity
- Marketplace Collection
- Price History
- DealScore
- Recommendation Engine
- Marketplace Intelligence
- Collection Operations
- Watchlists
- Review Intelligence

Known limitations
-----------------
- Live external AI HTTP is disabled by default
- No OpenAI / Claude / Gemini SDKs required in this sprint
- Mock / imported review texts (not live marketplace scraping)
- In-memory persistence only
- AI outputs can be inaccurate and must remain evidence-grounded
"""
