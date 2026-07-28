"""Product request and response schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
