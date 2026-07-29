# Reddit Connector

**Status:** Sprint 14 — full connector via provider abstraction  
**Live HTTP:** Disabled by default (fixtures / mock transport)

## Design

`RedditCommunityProvider` implements `CommunityProvider`.

- API-backed transport boundary (`CommunityTransport`)
- No scraping logic
- Deterministic fixtures when live access is unavailable or disabled

## Capabilities

- Product search (`search_product`)
- Relevant thread search (`search_threads`)
- Comment extraction (`extract_comments`)
- Thread metadata (upvotes, comment count, age, author, permalink)
- Evidence IDs (`reddit:{thread_id}` / `reddit:{comment_id}`)

## Fixture fallback

When `enabled=True` and the transport returns no items (or raises), fixtures from `app/intelligence/community/fixtures.py` (`REDDIT_FIXTURES`) are used if `use_fixtures_when_unavailable=True`.

## Configuration

- `COMMUNITY_REDDIT_ENABLED` (default `true`)
- `COMMUNITY_USE_FIXTURES` (default `true`)

Client ID / secret constructor args exist for future OAuth-shaped transports and are never returned in API payloads.

## Output

Normalized `CommunityEvidence` only — same model as every other connector.
