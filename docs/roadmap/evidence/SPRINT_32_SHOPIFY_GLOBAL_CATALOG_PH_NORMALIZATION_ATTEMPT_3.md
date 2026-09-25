# Sprint 32 — Shopify Global Catalog PH normalization attempt #3

**Document type:** Non-secret owner live normalization evidence  
**Date:** 2026-09-25  
**Generated:** 2026-09-25T04:34:35.325772+00:00  
**Market:** PH  
**Result:** LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED  
**Sprint 32:** OPEN  
**Sprint 38:** UNSTARTED  
**Sprint 41:** UNSTARTED

This record is attempt #3 only. Attempts #1 and #2 remain the earlier 2026-09-25 HTTP 429 fail-closed runs in the Sprint 32 sprint document. This file does not replace them.

This workspace did not call Shopify and did not run the live harness. `cursor_executed_live_harness = false`. `owner_live_validation = true`.

## Execution

- Owner execution.
- AWS CloudShell was the execution environment only. It was not a staging or production infrastructure deployment or mutation.
- Exact merged main: `5022c2ddac80d202db371d1e0e4fa26252e0c397`.
- Exact deployed staging PiqSavi profile.
- `agent_profile_source = piqsavi`.
- `staging_profile_exact_url_classification = exact_deployed_staging`.
- Preflight passed.
- Pacing = PiqSavi conservative 1.25-second cadence.
- `minimum_request_interval_seconds = 1.25`.
- `pacing_sleep_count = 9`.
- Total pacing sleep approximately 9.1589 seconds.

## Calls

- `search_call_count = 5` (`search_catalog` completed).
- `get_product_call_count = 5` (`get_product` completed).
- `lookup_count = 0`.
- `pagination_followed = false`.
- `pagination_metadata_observed = true`.

## Categories

Attempted and normalized successfully:

- wireless_earbuds
- gaming_laptop
- mechanical_keyboard
- usb_c_charger
- phone_case

## Identity, price, and availability

- `products_with_stable_source_product_id = 5`.
- Five distinct selected product identities stayed stable from search to detail.
- `search_variant_ids_observed_count = 5`.
- `search_variants_confirmed_in_detail_count = 5`.
- `variants_with_stable_source_variant_id = 5`.
- `detail_variant_ids_observed_count = 9`.
- `listing_prices_preserved_as_integer_minor_units = 14`.
- `currencies_observed_count = 2`.
- Currency codes preserved as returned: PHP, USD.
- `seller_identity_present_count = 14`.
- `availability_non_unknown_count = 14`.
- `availability_unknown_count = 0`.
- `availability_normalized_count = 14`.
- `canonical_parsing_attempted_count = 14`.
- `exact_variant_comparisons_count = 13`.

Raw Shopify product and variant IDs are not stored. Source identity digests were recorded in the owner summary and are not reconstructed in this repository.

## Ambiguous matches stayed fail-closed

`ambiguous_or_insufficient_matches_count = 5` is not failed normalization.

Those comparisons remained fail-closed. Insufficient parser identity did not become an exact match. `different_variant_conflicts_correctly_held_apart_count = 8`. Source product and variant identities stayed separate and stable. Matching thresholds were not weakened to reduce the ambiguity count.

## What was not fabricated

- `fabricated_shipping_count = 0`
- `fabricated_tax_count = 0`
- `fabricated_voucher_count = 0`
- `raw_payload_persisted = false`
- `raw_response_persistence = false`
- No persistent Shopify product index.

Unknown shipping, tax/import, promotion, and other effective-cost components stay unknown.

## What this pass does not mean

- `production_certification = false` at the time of the owner run.
- `sprint_32_closed = false`.
- `sprint_38_started = false`.
- `sprint_41_started = false`.
- No Shopify partnership, endorsement, special approval, preferred-developer status, or production-app approval.
- Certified reduced capability set, recorded later from this evidence, is not production deployment ready.
