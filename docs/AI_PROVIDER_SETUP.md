# AI Provider Setup — Review Summary

## Defaults (safe)

External AI is **off** until you explicitly enable it:

```env
AI_REVIEW_ENABLED=false
AI_REVIEW_LIVE_HTTP=false
AI_REVIEW_MODE=economy
```

The app continues to work with **zero** API keys via
`DeterministicReviewProvider`.

## Placeholders (`.env.example`)

Copy placeholders into a local `.env` (never commit real secrets):

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

## Enabling external providers (future / local experiments)

All three gates must be satisfied for live HTTP:

1. `AI_REVIEW_ENABLED=true`
2. `AI_REVIEW_LIVE_HTTP=true`
3. A non-empty API key for the chosen provider(s)

Also set:

```env
AI_REVIEW_MODE=economy   # or balanced / maximum
AI_PRIMARY_PROVIDER=openai
AI_SECONDARY_PROVIDER=anthropic
AI_FALLBACK_ORDER=openai,anthropic,gemini,deterministic
AI_PROVIDER_TIMEOUT_SECONDS=20
AI_MAX_REVIEW_INPUT=40
AI_MAX_ESTIMATED_COST_PER_REQUEST=0.05
```

### Important

- Adding API keys alone must **not** automatically enable maximum mode.
- Set `AI_REVIEW_MODE=maximum` explicitly if you want consensus across three models.
- Client `?mode=` cannot exceed the server mode ceiling.
- Current review texts may be mock fixtures or imported data — this is **not**
  live marketplace scraping.
- AI outputs can be inaccurate; DealBrain keeps evidence validation in-app.

## Current sprint status

Live provider HTTP execution is **not** implemented beyond the transport
boundary. Adapters are fully wired for mocked/scripted completions so the
architecture, modes, consensus, and fallback paths are testable without SDKs.

## Verification

```bash
pytest
```

Confirm responses never include API keys, prompts, or authorization headers.
