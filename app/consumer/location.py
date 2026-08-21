"""Session-scoped delivery context for Product Foundation pages.

Guest location is cookie-backed for the browser session only. Precise coordinates
are never persisted. Reverse-geocoding is not available in the current runtime.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import unquote

from starlette.responses import Response

DELIVERY_COOKIE = "piqsavi_delivery"
COOKIE_MAX_BYTES = 512
CITY_MAX_LEN = 80
POSTAL_MAX_LEN = 12
_CITY_RE = re.compile(r"^[A-Za-zÀ-ÿÑñ .'-]{2,80}$")
_POSTAL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{1,11}$")

LocationSource = Literal["manual", "skip", "absent"]


class LocationValidationError(ValueError):
    """Raised when manual delivery input cannot be accepted."""


@dataclass(frozen=True, slots=True)
class DeliveryContext:
    """Minimum destination needed to present offer economics."""

    city: str | None = None
    postal_code: str | None = None
    skipped: bool = False
    source: LocationSource = "absent"

    @property
    def is_known(self) -> bool:
        return bool(self.city) and not self.skipped

    @property
    def is_skipped(self) -> bool:
        return self.skipped or self.source == "skip"

    @property
    def is_absent(self) -> bool:
        return not self.is_known and not self.is_skipped

    @property
    def display_place(self) -> str:
        if not self.is_known or self.city is None:
            return ""
        if self.postal_code:
            return f"{self.city} {self.postal_code}"
        return self.city

    @property
    def delivering_to_label(self) -> str:
        if not self.is_known:
            return ""
        return f"Delivering to {self.display_place}"

    @property
    def destination_key(self) -> str:
        if not self.is_known or self.city is None:
            return "unknown"
        return normalize_destination_key(self.city, self.postal_code)

    def to_cookie_payload(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "postal_code": self.postal_code,
            "skipped": self.skipped,
            "source": self.source,
        }


def normalize_destination_key(city: str, postal_code: str | None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", city.casefold()).strip("-")
    if postal_code:
        postal_slug = re.sub(r"[^a-z0-9]+", "-", postal_code.casefold()).strip("-")
        return f"{slug}-{postal_slug}"
    return slug


def parse_delivery_cookie(raw: str | None) -> DeliveryContext:
    if not raw:
        return DeliveryContext()
    try:
        payload = json.loads(unquote(raw))
    except (json.JSONDecodeError, TypeError, ValueError):
        return DeliveryContext()
    if not isinstance(payload, dict):
        return DeliveryContext()
    skipped = bool(payload.get("skipped"))
    source = payload.get("source")
    if source not in {"manual", "skip", "absent"}:
        source = "skip" if skipped else "absent"
    city = _clean_optional_text(payload.get("city"))
    postal = _clean_optional_text(payload.get("postal_code"))
    if skipped:
        return DeliveryContext(skipped=True, source="skip")
    if city and _CITY_RE.match(city):
        postal_ok = postal if postal and _POSTAL_RE.match(postal) else None
        return DeliveryContext(city=city, postal_code=postal_ok, source="manual")
    return DeliveryContext()


def context_from_manual(city: str, postal_code: str | None) -> DeliveryContext:
    cleaned_city = " ".join((city or "").split()).strip()
    cleaned_postal = " ".join((postal_code or "").split()).strip() or None
    if not cleaned_city:
        raise LocationValidationError("Enter a city or municipality.")
    if len(cleaned_city) > CITY_MAX_LEN or not _CITY_RE.match(cleaned_city):
        raise LocationValidationError("Enter a valid city or municipality.")
    if cleaned_postal and (
        len(cleaned_postal) > POSTAL_MAX_LEN or not _POSTAL_RE.match(cleaned_postal)
    ):
        raise LocationValidationError("Enter a valid postal code, or leave it blank.")
    return DeliveryContext(
        city=cleaned_city,
        postal_code=cleaned_postal,
        skipped=False,
        source="manual",
    )


def skipped_context() -> DeliveryContext:
    return DeliveryContext(skipped=True, source="skip")


def set_delivery_cookie(response: Response, context: DeliveryContext) -> None:
    encoded = json.dumps(context.to_cookie_payload(), separators=(",", ":"))
    if len(encoded) > COOKIE_MAX_BYTES:
        raise LocationValidationError("Delivery context is too large to store.")
    response.set_cookie(
        DELIVERY_COOKIE,
        encoded,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_delivery_cookie(response: Response) -> None:
    response.delete_cookie(DELIVERY_COOKIE, path="/")


def _clean_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned or None
