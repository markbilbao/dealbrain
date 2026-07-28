"""Product Intelligence API request and response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.entities.product_match import MatchType


class IntelligenceParseRequest(BaseModel):
    """Payload for parsing a messy product listing title."""

    title: str = Field(..., description="Raw marketplace / listing title")

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped


class EvidenceItem(BaseModel):
    """Explainability evidence for a single extracted field."""

    field: str
    matched_text: str
    rule: str


class CanonicalProductPayload(BaseModel):
    """Canonical product identity returned by the parse endpoint."""

    id: UUID
    brand: str
    family: str
    model: str
    storage: str | None = None
    color: str | None = None


class IntelligenceParseResponse(BaseModel):
    """End-to-end Product Intelligence parse result."""

    original_title: str
    canonical_product: CanonicalProductPayload
    confidence: float = Field(ge=0.0, le=1.0)
    is_new_product: bool
    evidence: list[EvidenceItem]


class IntelligenceMatchRequest(BaseModel):
    """Payload for comparing two product listing titles."""

    title_a: str = Field(..., description="First raw listing title")
    title_b: str = Field(..., description="Second raw listing title")

    @field_validator("title_a", "title_b")
    @classmethod
    def titles_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped


class MatchConflictPayload(BaseModel):
    """A conflicting attribute between two listings."""

    field: str
    value_a: str
    value_b: str


class IntelligenceMatchResponse(BaseModel):
    """Product matching decision with explainability."""

    is_match: bool
    confidence: float = Field(ge=0.0, le=1.0)
    match_type: MatchType
    matched_fields: list[str]
    conflicts: list[MatchConflictPayload]
    explanation: list[str]
