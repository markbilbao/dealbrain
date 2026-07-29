# Personal AI Shopping Agent v1

**Status:** Sprint 16  
**Date:** 2026-07-29  
**Scope:** Provider-neutral, fixture-backed personalization for DealBrain Shopping Assistant recommendations.

## Goal

Give the Shopping Assistant a reusable customer profile so recommendations can reflect budget, brand affinity, use-case priorities, and ownership context — without login, payments, cloud sync, or external databases.

## Architecture

```
demo.html (Personal Agent panel + SA profile toggle)
  → API /api/v1/personal/*
  → PersonalAgentService (facade)
       ├─ ProfileManager + InMemoryCustomerProfileRepository
       ├─ PreferenceEngine
       ├─ PersonalScoringEngine (PersonalDealScore)
       ├─ PersonalRecommendationEngine
       ├─ BuyingAdvisor
       └─ ExplanationEngine

ShoppingAssistantService (optional collaborator)
  → personal_agent_service.shopping_assistant_* hooks
```

## Design principles

- **Fixture profiles only.** Eight demo personas live in `app/intelligence/personal/fixtures.py`.
- **Evidence-first.** Preference and DealScore signals come from catalog attributes and optional community/KG collaborators. Missing signals stay neutral — never fabricated.
- **Optional collaborator.** Shopping Assistant personalizes only when `profile_id` is provided and the personal agent is enabled; otherwise it stays in generic mode.
- **Provider-neutral.** No OpenAI/Anthropic/Gemini dependency in this package.
- **No auth / payment / tracking.** Documented limitations are enforced by design.

## Module layout

| Path | Responsibility |
|------|----------------|
| `app/domain/entities/personal_agent.py` | Profile, preference, PersonalDealScore, advice, recommendation entities |
| `app/domain/interfaces/personal_agent_repository.py` | Profile repository port |
| `app/intelligence/personal/` | Engines, fixtures, profile manager, memory store |
| `app/services/personal_agent_service.py` | Application facade |
| `app/api/v1/endpoints/personal.py` | REST API under `/api/v1/personal` |
| `app/schemas/personal_agent.py` | Pydantic response schemas |

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/personal/demo` | Active profile + ranked deals |
| GET | `/api/v1/personal/meta` | Profile list + limitations |
| GET | `/api/v1/personal/profile` | Active or specified profile |
| POST | `/api/v1/personal/profile/switch` | Switch active demo profile |
| GET | `/api/v1/personal/recommendation/{product_id}` | Personalized product recommendation |
| GET | `/api/v1/personal/deals` | Ranked personalized deals |
| GET | `/api/v1/personal/advice/{product_id}` | Structured buying advice |

## Shopping Assistant integration

`POST /api/v1/shopping-assistant/query` accepts optional `profile_id`. When set:

1. Profile constraints merge into intent overrides (budget, currency, use cases) without overriding explicit query fields.
2. Personal evidence items are appended (`source_id=personal_agent`).
3. Response includes `personal_recommendation` and `processing.personalization_mode=personal`.

If the profile is missing or the agent is disabled, the assistant falls back to generic mode with a `personal_profile_unavailable` warning when a profile was requested.

## Config

| Env | Default | Meaning |
|-----|---------|---------|
| `PERSONAL_AGENT_ENABLED` | `true` | Gate the personal agent service |
| `PERSONAL_AGENT_DEFAULT_PROFILE_ID` | `profile-budget-student` | Active fixture on startup |

## Limitations

- Profiles are fixtures / demo personas only.
- No login, authentication, or cloud sync.
- No purchase history or payment history.
- No user tracking or behavioral analytics.
- Recommendations remain evidence-based; personalization never fabricates fit.

See also: `PROFILE_MODEL.md`, `PREFERENCE_ENGINE.md`, `PERSONAL_DEALSCORE.md`, `BUYING_ADVISOR.md`.
