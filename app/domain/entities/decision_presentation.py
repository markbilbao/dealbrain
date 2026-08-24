"""Decision-time presentation facts for schema 1.2 snapshots.

These objects copy shopper context, qualification, product identity, fit
evidence, and Recommendation reasoning already used at decision time. They do
not calculate PiqScore, select Best Piq, or invent marketing copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.domain.exceptions import MerchantValidationError
from app.merchant.security.validation import validate_safe_url

QualificationState = Literal["unqualified", "qualified"]
FitStatus = Literal["known", "estimated", "unknown"]


def _optional_text(value: str | None, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > maximum:
        raise ValueError(f"{field_name} must contain at most {maximum} characters")
    return cleaned


@dataclass(frozen=True, slots=True)
class CanonicalQualification:
    """Explicit Recommendation qualification captured at decision time."""

    state: QualificationState
    reasons: tuple[str, ...] = ()
    material_unknowns: tuple[str, ...] = ()
    could_change_recommendation: bool = False

    def __post_init__(self) -> None:
        if self.state not in {"unqualified", "qualified"}:
            raise ValueError("qualification state must be unqualified or qualified")
        if any(not item.strip() for item in self.reasons):
            raise ValueError("qualification reasons must not contain empty values")
        if any(not item.strip() for item in self.material_unknowns):
            raise ValueError("material unknowns must not contain empty values")
        if self.state == "qualified" and not self.reasons and not self.material_unknowns:
            raise ValueError("qualified Recommendation requires a reason or material unknown")

    @property
    def is_qualified(self) -> bool:
        return self.state == "qualified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "reasons": list(self.reasons),
            "material_unknowns": list(self.material_unknowns),
            "could_change_recommendation": self.could_change_recommendation,
        }


@dataclass(frozen=True, slots=True)
class CanonicalShopperContext:
    """Decision-relevant shopper inputs used when the Recommendation was made."""

    budget_label: str | None = None
    top_priority: str | None = None
    priorities: tuple[str, ...] = ()
    use_case: str | None = None
    urgency: str | None = None
    required_features: tuple[str, ...] = ()
    preferences: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "budget_label", _optional_text(self.budget_label, "budget_label", 80)
        )
        object.__setattr__(
            self, "top_priority", _optional_text(self.top_priority, "top_priority", 80)
        )
        object.__setattr__(self, "use_case", _optional_text(self.use_case, "use_case", 160))
        object.__setattr__(self, "urgency", _optional_text(self.urgency, "urgency", 80))
        for field_name in (
            "priorities",
            "required_features",
            "preferences",
            "constraints",
        ):
            values = getattr(self, field_name)
            if any(not item.strip() or len(item) > 160 for item in values):
                raise ValueError(
                    f"{field_name} must contain non-empty values of at most 160 characters"
                )

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.budget_label,
                self.top_priority,
                self.priorities,
                self.use_case,
                self.urgency,
                self.required_features,
                self.preferences,
                self.constraints,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_label": self.budget_label,
            "top_priority": self.top_priority,
            "priorities": list(self.priorities),
            "use_case": self.use_case,
            "urgency": self.urgency,
            "required_features": list(self.required_features),
            "preferences": list(self.preferences),
            "constraints": list(self.constraints),
        }


@dataclass(frozen=True, slots=True)
class CanonicalFitAttribute:
    """Category-flexible product attribute that participated in the decision."""

    key: str
    label: str
    value: str
    unit: str | None = None
    status: FitStatus = "known"
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key or len(self.key) > 64:
            raise ValueError("fit attribute key must contain 1 to 64 characters")
        if not self.label or len(self.label) > 80:
            raise ValueError("fit attribute label must contain 1 to 80 characters")
        if not self.value or len(self.value) > 160:
            raise ValueError("fit attribute value must contain 1 to 160 characters")
        if self.unit is not None and len(self.unit) > 24:
            raise ValueError("fit attribute unit must contain at most 24 characters")
        if self.status not in {"known", "estimated", "unknown"}:
            raise ValueError("fit attribute status is invalid")
        if any(not item for item in self.evidence_ids):
            raise ValueError("fit evidence IDs must not contain empty values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
        }

    def display_value(self) -> str:
        if self.status == "unknown":
            return "Unknown"
        suffix = f" {self.unit}" if self.unit else ""
        prefix = "Estimated " if self.status == "estimated" else ""
        return f"{prefix}{self.value}{suffix}"


@dataclass(frozen=True, slots=True)
class CanonicalProductPresentation:
    """Stable product identity and offer-action metadata for one evaluated product."""

    product_id: str
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    offer_url: str | None = None
    fit_attributes: tuple[CanonicalFitAttribute, ...] = ()

    def __post_init__(self) -> None:
        if not self.product_id or len(self.product_id) > 128:
            raise ValueError("product_id must contain 1 to 128 characters")
        object.__setattr__(self, "brand", _optional_text(self.brand, "brand", 80))
        object.__setattr__(self, "model", _optional_text(self.model, "model", 160))
        object.__setattr__(self, "category", _optional_text(self.category, "category", 80))
        url = _optional_text(self.offer_url, "offer_url", 2048)
        if url is not None:
            try:
                url = validate_safe_url(url)
            except MerchantValidationError as exc:
                raise ValueError(str(exc)) from exc
        object.__setattr__(self, "offer_url", url)
        keys = tuple(item.key for item in self.fit_attributes)
        if len(keys) != len(set(keys)):
            raise ValueError("fit attribute keys must be unique per product")

    @property
    def is_empty(self) -> bool:
        return not any((self.brand, self.model, self.category, self.offer_url, self.fit_attributes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "offer_url": self.offer_url,
            "fit_attributes": [item.to_dict() for item in self.fit_attributes],
        }


@dataclass(frozen=True, slots=True)
class CanonicalRecommendationReason:
    """Decision-time reason actually used for the Recommendation."""

    reason: str
    evidence_ids: tuple[str, ...] = ()
    shopper_priority: str | None = None
    product_id: str | None = None
    related_attribute: str | None = None

    def __post_init__(self) -> None:
        if not self.reason.strip() or len(self.reason) > 400:
            raise ValueError("Recommendation reason must contain 1 to 400 characters")
        object.__setattr__(
            self,
            "shopper_priority",
            _optional_text(self.shopper_priority, "shopper_priority", 80),
        )
        object.__setattr__(
            self,
            "related_attribute",
            _optional_text(self.related_attribute, "related_attribute", 80),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
            "shopper_priority": self.shopper_priority,
            "product_id": self.product_id,
            "related_attribute": self.related_attribute,
        }


@dataclass(frozen=True, slots=True)
class CanonicalBestFor:
    """Supported Best-for conclusion captured with the decision."""

    label: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.label.strip() or len(self.label) > 160:
            raise ValueError("best-for label must contain 1 to 160 characters")

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "evidence_ids": list(self.evidence_ids)}


@dataclass(frozen=True, slots=True)
class CanonicalAlternativeTradeoff:
    """Evaluated-set trade-off captured with the Recommendation."""

    product_id: str
    reason: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.product_id:
            raise ValueError("trade-off product_id is required")
        if not self.reason.strip() or len(self.reason) > 400:
            raise ValueError("trade-off reason must contain 1 to 400 characters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
        }
