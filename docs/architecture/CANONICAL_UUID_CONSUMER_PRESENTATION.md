# Canonical UUID consumer presentation

**Status:** Implemented as a read-only adapter over canonical decision snapshots

Results, Compare, Why, and Ask PiqSavi can render one server-owned canonical
decision UUID using the existing Product Foundation UI.

This is not Phase 29.4B or 29.4C. The adapter does not refine Recommendation,
propose research, reprice destinations, or fetch live merchant data.

## Modes

### Canonical UUID mode

Path segment is a UUID. The server:

1. reads the owner/session cookie (`piqsavi_decision_owner`)
2. loads the latest owner-bound snapshot
3. verifies integrity through the existing repository path
4. adapts captured facts into `DecisionPageView`
5. renders the existing Results / Compare / Why templates

Missing, unauthorized, and tampered snapshots all render the same truthful
unavailable state. The page does not reveal whether another user's decision
exists.

### Fixture catalog mode

Explicit development/staging catalog IDs such as `headphones-standard` continue
to use Product Foundation fixtures when `fixture_catalogs_permitted()` is true.

A UUID is never resolved through the fixture catalog fallback.

### Production unavailable

Non-UUID catalog IDs in production remain unavailable. A failed UUID lookup
never substitutes `headphones-standard` or any other fixture.

## Historical authority

The snapshot is the decision. The adapter copies:

- Recommendation / Best Piq
- canonical PiqScore values
- evaluated-set membership and order
- captured offer economics (schema 1.1)
- delivery context used at decision time
- evidence, sources, and unknowns

It does not recalculate PiqScore, discounts, shipping, taxes, import charges, or
price state. Schema 1.0 snapshots render known fields and leave economics
unavailable.

## Location

Canonical pages display the decision-time destination. A later session cookie
for a different city does not rewrite economics or Recommendation. A minimal
note may say the current session location differs.

Schema 1.2 snapshots may also carry qualification, shopper context, product
identity, fit attributes, outbound offer URLs, and Recommendation reasoning.
See [`CANONICAL_DECISION_PRESENTATION_CONTRACT.md`](CANONICAL_DECISION_PRESENTATION_CONTRACT.md).
Older 1.0/1.1 snapshots continue to degrade without fixture backfill.

## Remaining metadata gaps

Schema 1.0/1.1 products currently carry `display_name` and `variant` only.
The adapter does not invent:

- product images
- category / tags
- offer URLs
- fit-attribute scores
- shopper budget / priority narratives
- percentile labels such as Top 5%
- Recommendation qualification unless the snapshot later stores it

Compare PRODUCT FIT cells stay unknown (`—`) for canonical UUID decisions.
View offer is omitted when no outbound URL was captured.

Live research, live merchant integration, and destination repricing remain
separate future work.
