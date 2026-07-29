# Community Intelligence Platform v1

**Status:** Sprint 14  
**Date:** 2026-07-29  
**Scope:** Provider-neutral community evidence aggregation for DealBrain Shopping Assistant

## Goal

Aggregate product knowledge from multiple community sources, normalize evidence, analyze with deterministic + optional multi-model AI, and expose an evidence-first API.

Reddit is the first full connector. Other sources ship as provider-ready adapters (mock / disabled by default).

## Architecture

```
demo.html (Community panel)
  → API /api/v1/community/*
  → CommunityIntelligenceService
  → CommunityOrchestrator
       ├─ CommunityCollector + CommunityRegistry
       │    └─ CommunityProvider adapters (Reddit, YouTube, Amazon Q&A, …)
       ├─ EvidenceNormalizer / EvidenceValidator / DuplicateDetector
       ├─ TopicExtractor / TopicAnalysisService
       ├─ CommunityTrustCalculator
       ├─ Timeline / Statistics / Health / Metrics / Search / Dashboard
       └─ CommunityAIOrchestrator + CommunitySummaryRegistry
            └─ OpenAI / Claude / Gemini / Deterministic (DisabledTransport)
```

## Sources

| Source | Status |
|--------|--------|
| Reddit | Full connector (fixture/mock transport by default) |
| YouTube | Adapter ready (mock) |
| Amazon Q&A | Adapter ready (mock) |
| Marketplace Questions | Adapter ready (mock) |
| Manufacturer Forums | Adapter ready (mock) |
| Discord | Architecture only (disabled by default) |

Future connectors register into `CommunityRegistry`.

## Normalized evidence model

Every connector returns the same shape (Shopping Assistant never learns the connector identity beyond optional display metadata):

- `source`, `product`, `evidence_id`, `url`, `title`, `body`
- `topic`, `sentiment`, `confidence`, `engagement`, `timestamp`

## Security

- No client API keys
- No scraping assumptions / browser automation
- Live community HTTP disabled unless configured
- AI dual-gate: `AI_COMMUNITY_ENABLED` **and** `AI_COMMUNITY_LIVE_HTTP`
- Secrets stripped from API `processing` payloads

## Configuration

| Env | Default | Meaning |
|-----|---------|---------|
| `COMMUNITY_ENABLED` | `true` | Feature on for DI / shopping integration |
| `COMMUNITY_REDDIT_ENABLED` | `true` | Reddit connector enabled |
| `COMMUNITY_YOUTUBE_ENABLED` | `false` | YouTube adapter |
| `COMMUNITY_AMAZON_QA_ENABLED` | `false` | Amazon Q&A adapter |
| `COMMUNITY_MARKETPLACE_QA_ENABLED` | `false` | Marketplace Q&A adapter |
| `COMMUNITY_FORUMS_ENABLED` | `false` | Manufacturer forums adapter |
| `COMMUNITY_DISCORD_ENABLED` | `false` | Discord adapter |
| `COMMUNITY_USE_FIXTURES` | `true` | Serve deterministic fixtures when live unavailable |
| `AI_COMMUNITY_ENABLED` | `false` | Allow AI summarization modes |
| `AI_COMMUNITY_LIVE_HTTP` | `false` | Allow live provider HTTP |
| `AI_COMMUNITY_MODE` | `economy` | Server mode ceiling |

Disabled connectors may still contribute **fixture** evidence when `COMMUNITY_USE_FIXTURES=true` (demo source diversity). Discord remains empty unless explicitly enabled.

## Shopping Assistant integration

`ShoppingAssistantService` optionally accepts `community_service` and appends provider-neutral `type="community"` evidence items. Descriptions are connector-agnostic (`source_id="community_intelligence"`).

## Protected modules

Prior sprint digests remain guarded by `tests/unit/test_community_protected_modules.py`. Community code composes; it does not rewrite DealScore / Review Summary / transport cores.

## Known limitations

- Default data is mock/fixture — not live social content
- Live Reddit API credentials / OAuth not wired (transport-ready only)
- Discord is architecture-only
- AI summarization falls back to deterministic unless dual-gated live HTTP is enabled

## Related docs

- [REDDIT_CONNECTOR.md](./REDDIT_CONNECTOR.md)
- [CONNECTOR_SDK.md](./CONNECTOR_SDK.md)
- [COMMUNITY_TRUST_SCORE.md](./COMMUNITY_TRUST_SCORE.md)
- [EVIDENCE_MODEL.md](./EVIDENCE_MODEL.md)
