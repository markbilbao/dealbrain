# Shopping Assistant API

## Endpoints

### `POST /api/v1/shopping-assistant/query`

Ask a natural-language shopping question.

Request:

```json
{
  "query": "What is the best gaming laptop under ₱60,000?",
  "mode": "economy",
  "conversation_id": null,
  "budget_max": 60000,
  "currency": "PHP",
  "use_cases": ["gaming"]
}
```

Optional structured filters (`budget_min`, `budget_max`, `currency`, `use_cases`,
`category`, `products`) override or enrich deterministic parsing.

Response (normalized):

```json
{
  "query": "What is the best gaming laptop under ₱60,000?",
  "intent": "recommendation",
  "answer": "string",
  "top_recommendation": {
    "product_id": "string",
    "product_name": "string",
    "reason": "string",
    "known_price": 59999,
    "currency": "PHP",
    "marketplace": "Shopee",
    "deal_score": 90.2,
    "confidence": 0.86
  },
  "alternatives": [],
  "evidence": [
    {
      "type": "price",
      "source_id": "Shopee",
      "description": "Known offer price ..."
    }
  ],
  "warnings": [],
  "data_status": "mock",
  "providers_used": ["deterministic"],
  "fallback_used": true,
  "confidence": {"score": 0.78, "band": "High", "factors": []},
  "mode": "economy",
  "comparison": null,
  "conversation_id": "uuid",
  "disagreements": [],
  "buy_now_or_wait": null,
  "action": "answer_from_evidence",
  "requires_research_confirmation": false,
  "research_proposal": null
}
```

Decision-bound Ask responses may set `action` to `answer_from_evidence`,
`refine_session_recommendation`, or `propose_research`. A research proposal is
server-authored, stays `pending_confirmation` until explicit confirmation, and
never starts live research in this phase.

Comparisons also populate `comparison` with category winners, strengths,
weaknesses, price/review differences, recommended use case, overall
recommendation, and unresolved uncertainty.

### `GET /api/v1/shopping-assistant/demo`

Returns a canned demo recommendation (`best gaming laptop under ₱60,000`).
Accepts optional `?mode=`.

### `GET /api/v1/shopping-assistant/meta`

Returns example queries, server-allowed modes, data-status label, and whether
shopping AI is enabled.

## Mode restrictions

Server settings:

- `AI_SHOPPING_ENABLED` (default `false`)
- `AI_SHOPPING_MODE` (`economy|balanced|maximum`, default `economy`)
- `AI_SHOPPING_ALLOW_CLIENT_MODE` (default `true`)
- `AI_SHOPPING_MAX_QUERY_LENGTH` (default `500`)
- `AI_SHOPPING_CONVERSATION_TTL_SECONDS` (default `1800`)
- `AI_SHOPPING_LIVE_HTTP` (default `false`)

Client requests cannot bypass cost limits, provider restrictions, timeout rules,
or server-enabled modes. When AI is disabled, effective mode is always
`economy` with deterministic fallback.

## Conversation

Pass `conversation_id` from a prior response to enable lightweight follow-ups
such as “Which one has the better battery?”. Context stores only safe
structured fields (intent, product ids/names, category, query text). API keys,
hidden prompts, and raw provider payloads are never stored.

## Errors

- `400` — validation (blank query, excessive length, unsupported mode string)
- `404` — missing conversation/resource (reserved)
- `500` — generic failure message without provider stack traces
