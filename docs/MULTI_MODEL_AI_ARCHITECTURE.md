# Multi-Model AI Architecture — Review Summary

Status: implemented (live external HTTP disabled by default)  
Date: 2026-07-29

## Purpose

Prepare DealBrain to integrate OpenAI, Anthropic Claude, and Google Gemini for
review analysis while keeping the Sprint 12 deterministic summarizer as a
guaranteed fallback.

## Operating modes

| Mode | Behavior |
|------|----------|
| **economy** | One primary provider. Fall back to deterministic if unavailable. |
| **balanced** | Primary analyzes; secondary critiques/validates independently. Consensus merges evidence-supported findings. |
| **maximum** | OpenAI, Claude, and Gemini analyze independently. Deterministic application code computes consensus and reports disagreements. |

Server configuration sets the mode ceiling (`AI_REVIEW_MODE`). Clients may
request a mode only at or below that ceiling. Adding API keys alone does **not**
enable expensive maximum mode.

## Components

```
AIReviewProvider (port)
  ├── OpenAIReviewProvider
  ├── ClaudeReviewProvider
  ├── GeminiReviewProvider
  └── DeterministicReviewProvider   ← always available fallback

AIProviderRegistry
ProviderHealthService
ReviewAnalysisValidator             ← evidence + schema gate
ConsensusService                    ← deterministic merge (no self-grading)
MultiModelReviewOrchestrator
ReviewSummaryService
API / Demo UI
```

## Safety rules

- Real external API calls are disabled by default (`AI_REVIEW_ENABLED=false`,
  `AI_REVIEW_LIVE_HTTP=false`).
- API keys are server-side only (`.env` / secret store). Never returned by APIs.
- Tests use `ScriptedTransport` / mocked responses only.
- Claims without supporting `evidence_review_ids` are rejected.
- Invalid review IDs, unsupported numeric fabrications, and malformed JSON are
  rejected or dropped.
- When all external providers fail, the deterministic summary is returned.

## Normalized provider schema

All providers must return:

- `overall_sentiment`: `very_positive | positive | mixed | negative`
- `summary`
- `pros` / `cons` / `warnings` as `{ claim, evidence_review_ids, confidence }`
- `recommendation`: `highly_recommended | recommended | consider_alternatives | not_recommended`
- `confidence`, `provider`, `model`

## Consensus metadata (maximum / balanced)

```json
{
  "mode": "maximum",
  "providers_requested": 3,
  "providers_completed": 3,
  "agreement_score": 0.87,
  "consensus_confidence": 0.84,
  "provider_results": [],
  "disagreements": [],
  "fallback_used": false
}
```

Important disagreements are preserved, not hidden.

## Transport boundary

Provider adapters call `ProviderTransport`. Default is `DisabledTransport`.
No OpenAI / Anthropic / Google SDKs are required for this sprint. Future live
HTTP can be added behind the transport without scattering vendor logic.

## Related docs

- `docs/AI_REVIEW_SUMMARY_V1.md`
- `docs/AI_PROVIDER_SETUP.md`
