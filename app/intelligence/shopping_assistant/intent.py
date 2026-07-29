"""Deterministic shopping intent detection and constraint extraction."""

from __future__ import annotations

import re
from typing import Any

from app.domain.entities.shopping_assistant import (
    ShoppingConstraint,
    ShoppingIntent,
    ShoppingIntentType,
)

_AMOUNT = r"([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)"

_CURRENCY_PATTERNS = (
    (re.compile(rf"₱\s*{_AMOUNT}"), "PHP"),
    (re.compile(rf"\bPHP\s*{_AMOUNT}", re.I), "PHP"),
    (re.compile(rf"\$\s*{_AMOUNT}"), "USD"),
)

_BUDGET_MAX_PATTERNS = (
    re.compile(
        rf"(?:under|below|less than|max(?:imum)?|budget(?: of)?|up to)\s*"
        rf"(?:₱|PHP\s*)?{_AMOUNT}",
        re.I,
    ),
)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "laptop": ("laptop", "notebook", "macbook"),
    "phone": ("phone", "smartphone", "iphone", "galaxy", "pixel"),
    "earbuds": ("earbuds", "airpods", "earphones", "headphones"),
}

_USE_CASE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "gaming": ("gaming", "gamer", "esports", "rtx"),
    "photography": ("photography", "camera", "photo", "zoom"),
    "productivity": ("productivity", "work", "office", "s pen", "s-pen"),
    "battery_life": ("battery", "long battery"),
    "content_creation": ("content creation", "editing", "creator"),
    "premium": ("premium", "flagship"),
    "audio": ("audio", "anc", "music"),
    "commute": ("commute", "travel"),
}

_PRIORITY_KEYWORDS: tuple[str, ...] = (
    "camera",
    "battery",
    "performance",
    "price",
    "display",
    "storage",
    "build",
    "zoom",
)

_MARKETPLACE_KEYWORDS: tuple[str, ...] = ("shopee", "lazada", "tiktok", "amazon")

_BRAND_KEYWORDS: tuple[str, ...] = (
    "apple",
    "samsung",
    "asus",
    "acer",
    "lenovo",
    "google",
)

_COMPARE_RE = re.compile(
    r"compare\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)(?:\s+for\s+(.+))?$",
    re.I,
)

_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all instructions",
    "system prompt",
    "reveal the prompt",
    "api key",
    "override safety",
)


def _parse_number(raw: str) -> float:
    return float(raw.replace(",", ""))


def extract_currency(text: str) -> str | None:
    for pattern, currency in _CURRENCY_PATTERNS:
        if pattern.search(text):
            return currency
    if re.search(r"\bPHP\b", text, re.I) or "₱" in text:
        return "PHP"
    return None


def extract_budget_max(text: str) -> float | None:
    for pattern in _BUDGET_MAX_PATTERNS:
        match = pattern.search(text)
        if match:
            return _parse_number(match.group(1))
    # Bare peso amount after "under" already covered; also catch trailing 60000 PHP.
    match = re.search(
        r"\b([0-9]{4,7}(?:,[0-9]{3})*)\s*(?:PHP|pesos?)?\b",
        text,
        re.I,
    )
    if match and any(token in text.lower() for token in ("under", "below", "budget", "max")):
        return _parse_number(match.group(1))
    return None


def extract_budget_min(text: str) -> float | None:
    match = re.search(
        rf"(?:over|above|at least|minimum|min(?:imum)?)\s*"
        rf"(?:₱|PHP\s*)?{_AMOUNT}",
        text,
        re.I,
    )
    if match:
        return _parse_number(match.group(1))
    return None


def extract_category(text: str) -> str | None:
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


def extract_use_cases(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    found: list[str] = []
    for use_case, keywords in _USE_CASE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(use_case)
    return tuple(dict.fromkeys(found))


def extract_priorities(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    found = [item for item in _PRIORITY_KEYWORDS if item in lowered]
    return tuple(dict.fromkeys(found))


def extract_marketplace(text: str) -> str | None:
    lowered = text.lower()
    for marketplace in _MARKETPLACE_KEYWORDS:
        if marketplace in lowered:
            return marketplace.title() if marketplace != "tiktok" else "TikTok"
    return None


def extract_brand(text: str) -> str | None:
    lowered = text.lower()
    for brand in _BRAND_KEYWORDS:
        if re.search(rf"\b{re.escape(brand)}\b", lowered):
            return brand.title() if brand != "asus" else "ASUS"
    return None


def extract_product_names(text: str, known_names: list[str] | None = None) -> tuple[str, ...]:
    """Extract product names via compare grammar and known catalog matches."""
    names: list[str] = []
    compare = _COMPARE_RE.search(text.strip())
    if compare:
        left = compare.group(1).strip(" .,?\"'")
        right = compare.group(2).strip(" .,?\"'")
        # Drop trailing "for camera..." already captured separately.
        right = re.split(r"\s+for\s+", right, maxsplit=1, flags=re.I)[0].strip()
        names.extend([left, right])

    catalog = known_names or []
    lowered = text.lower()
    for name in sorted(catalog, key=len, reverse=True):
        if name.lower() in lowered and name not in names:
            names.append(name)

    # Lightweight proper-noun-ish capture for "iPhone A and Galaxy B".
    and_match = re.search(
        r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z0-9][A-Za-z0-9+]*){0,5})\s+and\s+"
        r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z0-9][A-Za-z0-9+]*){0,5})\b",
        text,
    )
    if and_match:
        for group in and_match.groups():
            cleaned = group.strip()
            if cleaned and cleaned not in names and len(cleaned) > 2:
                names.append(cleaned)

    return tuple(dict.fromkeys(names))


def detect_intent(text: str) -> ShoppingIntentType:
    lowered = text.lower()
    if "compare" in lowered or " vs " in lowered or "versus" in lowered:
        return "comparison"
    if "buy now" in lowered or "or wait" in lowered or "should i wait" in lowered:
        return "buy_now_or_wait"
    if "complaint" in lowered or "main issue" in lowered or "problems with" in lowered:
        return "complaints"
    if "trustworthy" in lowered or "trusted seller" in lowered or "cheap seller" in lowered:
        return "seller_trust"
    if (
        "best offer" in lowered
        or "which marketplace" in lowered
        or "cheapest marketplace" in lowered
    ):
        return "best_offer"
    if "worth buying" in lowered or "should i buy" in lowered:
        return "worth_buying"
    use_case_tokens = ("best for", "better for", "for gaming", "for photography")
    if any(token in lowered for token in use_case_tokens):
        return "use_case"
    if any(token in lowered for token in ("recommend", "best ", "under ", "budget")):
        return "recommendation"
    if "which one" in lowered:
        return "comparison"
    return "general"


def contains_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _INJECTION_MARKERS)


class ShoppingIntentService:
    """Detect structured shopping intent from natural-language questions."""

    def __init__(self, known_product_names: list[str] | None = None) -> None:
        self._known_names = list(known_product_names or [])

    def parse(
        self,
        query: str,
        *,
        overrides: dict[str, Any] | None = None,
        prior_products: tuple[str, ...] = (),
        prior_intent: ShoppingIntentType | None = None,
    ) -> ShoppingIntent:
        cleaned = query.strip()
        intent = detect_intent(cleaned)
        products = extract_product_names(cleaned, self._known_names)

        # Follow-up: "Which one has the better battery?" with prior products.
        if (
            not products
            and prior_products
            and (
                "which one" in cleaned.lower()
                or intent in {"comparison", "general", "use_case", "complaints", "buy_now_or_wait"}
            )
        ):
            products = prior_products
            if prior_intent == "comparison" or "which one" in cleaned.lower():
                intent = "comparison" if intent in {"general", "use_case"} else intent

        constraints = ShoppingConstraint(
            category=extract_category(cleaned),
            products=products,
            budget_min=extract_budget_min(cleaned),
            budget_max=extract_budget_max(cleaned),
            currency=extract_currency(cleaned),
            preferred_marketplace=extract_marketplace(cleaned),
            use_cases=extract_use_cases(cleaned),
            preferred_features=extract_priorities(cleaned),
            excluded_features=(),
            brand_preference=extract_brand(cleaned),
            urgency=(
                "urgent" if "now" in cleaned.lower() and "wait" not in cleaned.lower() else None
            ),
            location="PH" if extract_currency(cleaned) == "PHP" or "₱" in cleaned else None,
            priorities=extract_priorities(cleaned),
        )

        if overrides:
            constraints = ShoppingConstraint(
                category=overrides.get("category", constraints.category),
                products=tuple(overrides.get("products", constraints.products)),
                budget_min=overrides.get("budget_min", constraints.budget_min),
                budget_max=overrides.get("budget_max", constraints.budget_max),
                currency=overrides.get("currency", constraints.currency),
                preferred_marketplace=overrides.get(
                    "preferred_marketplace",
                    constraints.preferred_marketplace,
                ),
                use_cases=tuple(overrides.get("use_cases", constraints.use_cases)),
                preferred_features=constraints.preferred_features,
                excluded_features=constraints.excluded_features,
                brand_preference=overrides.get("brand_preference", constraints.brand_preference),
                urgency=constraints.urgency,
                location=constraints.location,
                priorities=tuple(overrides.get("priorities", constraints.priorities)),
            )

        return ShoppingIntent(
            intent=intent,
            constraints=constraints,
            raw_query=cleaned,
            parser="deterministic",
        )
