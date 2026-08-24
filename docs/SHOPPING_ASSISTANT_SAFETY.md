# Shopping Assistant Safety

## Evidence requirements

Every recommendation must include evidence items. Important claims should
reference evidence ids for price, rating, review insights, DealScore,
marketplace, seller, price history, or recommendation ranking.

Unsupported claims are rejected or qualified, including:

- “best camera” without supporting feature/strength evidence
- “lowest price online” without complete marketplace coverage
- “guaranteed authentic”
- “price will definitely drop”
- “fake reviews” unless an implemented detector supports the claim

## Untrusted retrieved text

Marketplace reviews, product titles, and seller names are treated as untrusted
data. Instruction-like content inside them must not override system rules.
User queries containing prompt-injection markers are processed deterministically
and surfaced with a warning; they never unlock secrets or prompts.

## Secrets and prompts

- Provider API keys remain server-side only.
- Internal prompts are never returned in API responses.
- Response `processing` metadata is sanitized to strip keys containing
  `api_key`, `secret`, `token`, `authorization`, or `prompt`.
  `authorization` is sensitive by default. Only these exact known-safe
  research-authorization metadata keys are exempt: `research_authorization_id`,
  `authorization_status`, `authorization_version`, `authorization_created`,
  and `execution_available`.
- Provider stack traces and private transport errors are not returned to clients.

## Limits

- Query length capped by `AI_SHOPPING_MAX_QUERY_LENGTH`
- Conversation history capped (turn limit + TTL cleanup)
- Client mode cannot exceed server `AI_SHOPPING_MODE`
- Live external HTTP requires both `AI_SHOPPING_ENABLED` and
  `AI_SHOPPING_LIVE_HTTP`

## Why the assistant cannot guarantee outcomes

DealBrain v1 shopping answers use mock/imported catalog evidence with partial
marketplace coverage. Therefore the assistant cannot guarantee:

- that a displayed price is the current live price
- product authenticity or seller legitimacy
- that a price will fall or rise in the future
- complete review honesty / fake-review detection

Qualified language is required whenever evidence is incomplete.

## Deterministic fallback

If AI is disabled, providers are unavailable, validation fails, or cost/mode
gates block external calls, the deterministic explainer still returns a usable
evidence-grounded response with `fallback_used=true`.
