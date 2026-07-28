"""Brand alias catalog.

Maps normalized aliases → canonical brand display names.
Keys must be lowercase with spaces collapsed to a single space.

Matching prefers longer token windows first (see BrandRule).
"""

from __future__ import annotations

# Prefer multi-word aliases via longer token windows in BrandRule
# (e.g. "apple inc" before "apple").
BRAND_ALIASES: dict[str, str] = {
    "apple": "Apple",
    "apple inc": "Apple",
    "apple computer": "Apple",
    "samsung": "Samsung",
    "samsung electronics": "Samsung",
    "google": "Google",
    "google llc": "Google",
    "sony": "Sony",
    "microsoft": "Microsoft",
    "dell": "Dell",
    "hp": "HP",
    "hewlett packard": "HP",
    "lenovo": "Lenovo",
    "asus": "ASUS",
    "xiaomi": "Xiaomi",
    "oneplus": "OnePlus",
    "one plus": "OnePlus",
    "motorola": "Motorola",
    "moto": "Motorola",
    "nothing": "Nothing",
    "fairphone": "Fairphone",
}
