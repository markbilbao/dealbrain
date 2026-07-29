# Profile Model

**Status:** Sprint 16  
**Entity:** `CustomerProfile` in `app/domain/entities/personal_agent.py`  
**Fixtures:** `app/intelligence/personal/fixtures.py`

## Fields

| Field | Type | Notes |
|-------|------|-------|
| `profile_id` | str | Stable fixture id |
| `display_name` | str | Demo label |
| `persona` | str | Machine persona key |
| `budget` | float \| None | Max spend |
| `currency` | str | Default `PHP` |
| `country` | str | Default `PH` |
| `preferred_marketplaces` | tuple[str] | e.g. Shopee, Lazada |
| `favorite_brands` / `disliked_brands` | tuple[str] | Brand affinity |
| `preferred_screen_sizes` / `preferred_colors` | tuple[str] | Soft preferences |
| `gaming` / `office_work` / `student` / `creator` / `traveler` | bool | Lifestyle flags |
| `battery_priority` / `performance_priority` / `camera_priority` / `storage_priority` | float 0–1 | Feature priorities |
| `price_sensitivity` | float 0–1 | Budget strictness |
| `upgrade_frequency` | str | Qualitative cadence |
| `owned_products` / `wishlist` / `accessories_owned` | tuple[str] | Product ids |
| `favorite_categories` | tuple[str] | e.g. laptop, phone |
| `description` | str | Human-readable demo blurb |
| `data_status` | mock \| imported \| live | Always `mock` in v1 |

`use_cases()` derives shopping use-case tags from lifestyle flags and high priorities.

## Demo personas

1. Budget Student  
2. Gaming Enthusiast  
3. Photographer  
4. Business Traveler  
5. Content Creator  
6. Apple Fan  
7. Android Fan  
8. Minimalist Buyer  

## Limitations

Profiles are **fixtures**. There is no account system, no sync, and no inferred behavioral profile beyond these explicit fields.
