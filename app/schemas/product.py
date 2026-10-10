"""Product request and response schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.security.url_trust import UrlTrustError, validate_browser_destination


class ProductCreate(BaseModel):
    """Payload for creating a product."""

    brand: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=255)
    model: str = Field(min_length=1, max_length=255)
    variant: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=128)
    manufacturer_sku: str = Field(min_length=1, max_length=128)
    release_date: date | None = None
    msrp: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    image_url: HttpUrl | str | None = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _browser_image_url(cls, value: object) -> object:
        return _validate_product_image_url(value)


class ProductUpdate(BaseModel):
    """Payload for updating a product."""

    brand: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=255)
    model: str | None = Field(default=None, min_length=1, max_length=255)
    variant: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=128)
    manufacturer_sku: str | None = Field(default=None, min_length=1, max_length=128)
    release_date: date | None = None
    msrp: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    image_url: HttpUrl | str | None = None

    @field_validator("image_url", mode="before")
    @classmethod
    def _browser_image_url(cls, value: object) -> object:
        return _validate_product_image_url(value)


def _validate_product_image_url(value: object) -> object:
    """Product images are stored browser resources, not server fetches."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return validate_browser_destination(text, max_length=2_048)
    except UrlTrustError as exc:
        raise ValueError(str(exc)) from exc


class ProductResponse(BaseModel):
    """Product representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand: str
    category: str
    model: str
    variant: str | None
    color: str | None
    manufacturer_sku: str
    release_date: date | None
    msrp: Decimal | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime
