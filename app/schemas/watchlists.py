"""Watchlists & Price Alerts API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WatchlistCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    owner_id: str | None = None
    description: str | None = None
    enabled: bool = True


class WatchlistUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    owner_id: str | None = None
    description: str | None = None
    enabled: bool | None = None


class WatchlistPayload(BaseModel):
    watchlist_id: str
    name: str
    owner_id: str | None = None
    description: str | None = None
    enabled: bool = True
    created_at: str
    updated_at: str
    item_count: int = 0


class WatchlistListResponse(BaseModel):
    watchlists: list[WatchlistPayload] = Field(default_factory=list)


class WatchlistItemCreateRequest(BaseModel):
    canonical_product_id: str = Field(..., min_length=1)
    product_label: str | None = None
    target_price: float | None = Field(default=None, ge=0)
    currency: str = "PHP"
    search_query: str | None = None
    enabled: bool = True
    last_known_price: float | None = Field(default=None, ge=0)
    last_known_dealscore: float | None = Field(default=None, ge=0, le=100)
    last_historical_low: float | None = Field(default=None, ge=0)


class WatchlistItemUpdateRequest(BaseModel):
    product_label: str | None = None
    target_price: float | None = Field(default=None, ge=0)
    clear_target_price: bool = False
    currency: str | None = None
    search_query: str | None = None
    enabled: bool | None = None


class WatchlistItemPayload(BaseModel):
    item_id: str
    watchlist_id: str
    canonical_product_id: str
    product_label: str | None = None
    target_price: float | None = None
    currency: str = "PHP"
    search_query: str | None = None
    last_known_price: float | None = None
    last_known_dealscore: float | None = None
    last_historical_low: float | None = None
    enabled: bool = True
    created_at: str
    updated_at: str
    current_price: float | None = None
    historical_low: float | None = None
    dealscore: float | None = None
    observed_currency: str | None = None
    observation_count: int = 0
    price_available: bool = False


class WatchlistItemListResponse(BaseModel):
    items: list[WatchlistItemPayload] = Field(default_factory=list)


class AlertPayload(BaseModel):
    alert_id: str
    watchlist_id: str
    item_id: str
    canonical_product_id: str
    alert_type: str
    message: str
    previous_value: float | None = None
    current_value: float | None = None
    currency: str | None = None
    dealscore: float | None = None
    status: str
    created_at: str
    notified_at: str | None = None


class AlertListResponse(BaseModel):
    alerts: list[AlertPayload] = Field(default_factory=list)


class NotificationReceiptPayload(BaseModel):
    notification_id: str
    alert_id: str
    channel: str
    status: str
    created_at: str
    detail: str


class AlertEvaluationResponse(BaseModel):
    watchlist_ids: list[str] = Field(default_factory=list)
    items_checked: int = 0
    alerts_count: int = 0
    alerts_created: list[AlertPayload] = Field(default_factory=list)
    notifications: list[NotificationReceiptPayload] = Field(default_factory=list)
    evaluated_at: str
    disclaimer: str = (
        "Notifications are mock-only and return queued status. "
        "No email, SMS, or push notifications are sent."
    )
