# Canonical offer economics

**Status:** Implemented as a backward-compatible snapshot extension (schema 1.1)

Canonical offer economics capture the **economic state PiqSavi actually evaluated**
when a buying decision was committed. They are historical decision evidence.

They are not:

- a live merchant price feed
- Product Foundation presentation fixtures
- affiliate commission or payout economics
- a second pricing engine
- Phase 29.4B Recommendation refinement
- Phase 29.4C research

## Relationship to Phase 29.3 snapshots

Phase 29.3 `CanonicalDecisionSnapshot` (schema `1.0`) preserves:

- evaluated-set membership
- canonical PiqScore outputs
- Recommendation / Best Piq
- evidence provenance
- unknowns
- affiliate-neutrality proof
- SHA-256 content integrity

Schema `1.0` payloads do **not** include offer economics. Those snapshots remain
valid. Their original `content_sha256` still verifies. Asking price or shipping
questions against them continues to return **insufficient evidence**.

## Schema 1.1

When economics are captured at decision creation time, the snapshot serializes as
schema `1.1` and includes `offer_economics`. Empty economics are omitted, so a
snapshot without economics still serializes as schema `1.0` and keeps the original
digest.

Integrity protection for 1.1 snapshots includes every captured economic field.
Tampering with listing, voucher, shipping, tax, import estimate, dominant amount,
price state, merchant, or delivery context changes `content_sha256`.

No database migration is required. Economics live inside the existing serialized
canonical snapshot payload on the operational store.

## Per-offer contract

Each `CanonicalOfferEconomics` record may include:

| Field | Meaning |
|---|---|
| `offer_id` / `product_id` | Evaluated offer identity |
| `merchant` / `marketplace` / `seller_id` | Seller identity when known |
| `currency` | Explicit currency |
| `listing` | Item / listing price |
| `voucher` | Public savings line |
| `shipping` | Shipping line and status |
| `taxes` | Taxes / duties |
| `import_charges` | Cross-border import line |
| `price_state` | Dominant evaluated state |
| `dominant_amount_minor` | Amount for that state, integer minor units |
| `delivery` | City / postal / country used for evaluation |
| `unknowns` | Structured economic gaps |
| `provenance_source` / `evidence_ids` | Proven sources only |
| `checked_at` / `freshness` | Only when genuinely known |

Amounts use integer minor units. Unknown lines store `amount_minor: null`.

## Price states

Stable identifiers, not display strings:

- `final_effective_cost` — Final effective cost
- `estimated_landed_cost` — Estimated landed cost
- `price_before_shipping` — Price before shipping
- `before_unverified_import_charges` — Before unverified import charges
- `potential_checkout_price` — Potential checkout price

## Known / unknown / estimated / not applicable

These are distinct:

- verified shipping `0` (FREE) is not unknown shipping
- taxes `not_applicable` is not unknown tax
- estimated import charges are not verified import charges
- unverified or expired vouchers are stored but `applied=false`

Partial economics are valid. A known listing with unknown shipping may be captured
as **Price before shipping**.

## Capture path

Upstream evaluation already determines applied voucher, shipping, taxes, import
status, price state, and dominant amount. `capture_offer_economics` copies those
values into the snapshot. It does not recompute discounts.

Production must not pass Product Foundation `non_live_contract_fixture` components
unless fixture catalogs are explicitly permitted **and** the caller opts in.

A later marketplace price change does not rewrite an old snapshot. A new research
run may create a new snapshot version.

## Phase 29.4A

`packet_from_snapshot` now reads canonical economics when present. Ask PiqSavi can
explain listing, voucher, shipping, import, merchant, and evaluated total from the
snapshot. Missing economics still return insufficient evidence. Production still
does not fall back to Product Foundation fixtures.

## Product Foundation

Results / Compare / Why remain presentation adapters. They do not yet load
canonical UUID snapshots on document routes. Live production pages without a
canonical snapshot continue to show unavailable offer economics rather than
fixture catalogs.

## Immutability

Reading or answering from a snapshot does not mutate economics, digest, PiqScore,
Recommendation, evaluated set, or evidence provenance.
