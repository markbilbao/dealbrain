"""User Platform API schemas — auth, profile, preferences, and saved items.

Sprint 17: demo/in-memory accounts only. No OAuth, MFA, or email delivery.
Matches the style of app/schemas/personal_agent.py.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --- Auth ---


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=256)
    display_name: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=256)
    remember_me: bool = False


class UserPayload(BaseModel):
    """Public user representation — password_hash is never included."""

    user_id: str
    email: str
    display_name: str
    is_active: bool = True
    email_verified: bool = False
    created_at: str | None = None
    updated_at: str | None = None
    data_status: str = "mock"


class SessionPayload(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    expires_at: str
    remember_me: bool = False
    last_seen_at: str | None = None
    user_agent: str | None = None
    ip_hint: str | None = None
    revoked: bool = False


class AuthResponse(BaseModel):
    user: UserPayload
    access_token: str
    csrf_token: str | None = None
    token_type: str = "Bearer"
    expires_at: str
    session: SessionPayload


# --- Profile / preferences ---


class FavoriteBrandPayload(BaseModel):
    user_id: str
    brand: str
    created_at: str | None = None


class FavoriteMarketplacePayload(BaseModel):
    user_id: str
    marketplace: str
    created_at: str | None = None


class WishlistPayload(BaseModel):
    user_id: str
    product_ids: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class ProfileVersionPayload(BaseModel):
    user_id: str
    version: int
    changed_at: str | None = None
    change_summary: str = ""


class PreferencesPayload(BaseModel):
    user_id: str
    budget: float | None = None
    currency: str = "PHP"
    country: str = "PH"
    shopping_goals: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    battery_priority: float = 0.5
    camera_priority: float = 0.5
    performance_priority: float = 0.5
    travel_frequency: str = "occasional"
    creator_mode: bool = False
    gaming_mode: bool = False
    student_mode: bool = False
    business_mode: bool = False
    preferred_screen_size: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    personal_profile_id: str | None = None
    updated_at: str | None = None


class PreferencesUpdateRequest(BaseModel):
    budget: float | None = None
    currency: str | None = None
    country: str | None = None
    shopping_goals: list[str] | None = None
    categories: list[str] | None = None
    battery_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    camera_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    performance_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    travel_frequency: str | None = None
    creator_mode: bool | None = None
    gaming_mode: bool | None = None
    student_mode: bool | None = None
    business_mode: bool | None = None
    preferred_screen_size: list[str] | None = None
    preferred_colors: list[str] | None = None
    personal_profile_id: str | None = None


class ProfileResponse(BaseModel):
    user_id: str
    display_name: str
    preferences: PreferencesPayload
    favorite_brands: list[FavoriteBrandPayload] = Field(default_factory=list)
    favorite_marketplaces: list[FavoriteMarketplacePayload] = Field(default_factory=list)
    wishlist: WishlistPayload
    owned_products: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    version: ProfileVersionPayload | None = None
    data_status: str = "mock"
    # Flattened preference fields — mirror UserProfile.to_dict() for convenience.
    budget: float | None = None
    currency: str = "PHP"
    country: str = "PH"
    shopping_goals: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    battery_priority: float = 0.5
    camera_priority: float = 0.5
    performance_priority: float = 0.5
    travel_frequency: str = "occasional"
    creator_mode: bool = False
    gaming_mode: bool = False
    student_mode: bool = False
    business_mode: bool = False
    preferred_screen_size: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    personal_profile_id: str | None = None


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    budget: float | None = None
    currency: str | None = None
    country: str | None = None
    shopping_goals: list[str] | None = None
    categories: list[str] | None = None
    battery_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    camera_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    performance_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    travel_frequency: str | None = None
    creator_mode: bool | None = None
    gaming_mode: bool | None = None
    student_mode: bool | None = None
    business_mode: bool | None = None
    preferred_screen_size: list[str] | None = None
    preferred_colors: list[str] | None = None
    personal_profile_id: str | None = None
    favorite_brands: list[str] | None = None
    favorite_marketplaces: list[str] | None = None
    wishlist: list[str] | None = None
    owned_products: list[str] | None = None
    accessories: list[str] | None = None


class NotificationPreferencePayload(BaseModel):
    user_id: str
    email_enabled: bool = False
    push_enabled: bool = False
    deal_alerts: bool = True
    price_drop_alerts: bool = True
    newsletter: bool = False


class SettingsPayload(BaseModel):
    user_id: str
    theme: str = "system"
    language: str = "en"
    notification_settings: NotificationPreferencePayload | None = None
    ai_mode_preference: str = "economy"
    privacy_settings: dict[str, Any] = Field(default_factory=dict)
    community_settings: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class SettingsUpdateRequest(BaseModel):
    theme: str | None = None
    language: str | None = None
    notification_settings: dict[str, Any] | None = None
    ai_mode_preference: str | None = None
    privacy_settings: dict[str, Any] | None = None
    community_settings: dict[str, Any] | None = None


# --- Saved items ---


class SavedProductPayload(BaseModel):
    id: str
    user_id: str
    product_id: str
    product_name: str
    marketplace: str | None = None
    price: float | None = None
    currency: str = "PHP"
    notes: str = ""
    favorite: bool = False
    created_at: str | None = None


class SaveProductRequest(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=128)
    product_name: str = Field(..., min_length=1, max_length=256)
    marketplace: str | None = None
    price: float | None = None
    currency: str = "PHP"
    notes: str = ""
    favorite: bool = False


class SavedComparisonPayload(BaseModel):
    id: str
    user_id: str
    product_ids: list[str] = Field(default_factory=list)
    title: str = ""
    notes: str = ""
    created_at: str | None = None


class SaveComparisonRequest(BaseModel):
    product_ids: list[str] = Field(..., min_length=2)
    title: str = ""
    notes: str = ""


class RecommendationHistoryPayload(BaseModel):
    id: str
    user_id: str
    query: str
    recommendation_summary: str = ""
    product_ids: list[str] = Field(default_factory=list)
    profile_id: str | None = None
    created_at: str | None = None


class SavedSearchPayload(BaseModel):
    id: str
    user_id: str
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class SaveSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=256)
    filters: dict[str, Any] = Field(default_factory=dict)


class RecentlyViewedPayload(BaseModel):
    user_id: str
    product_ids: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class MarkViewedRequest(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=128)


# --- Meta / demo ---


class DemoUserPayload(BaseModel):
    email: str
    display_name: str
    user_id: str
    password_hint: str


class UserPlatformDemoResponse(BaseModel):
    demo_users: list[DemoUserPayload] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    authentication: bool = True
    email_delivery: bool = False
    mfa: bool = False
    oauth: bool = False
    persistence: str = "memory"


class UserPlatformMetaResponse(BaseModel):
    enabled: bool = True
    authentication: bool = True
    email_delivery: bool = False
    mfa: bool = False
    oauth: bool = False
    persistence: str = "memory"
    demo_user_count: int = 0
    limitations: list[str] = Field(default_factory=list)
    endpoints: list[str] = Field(default_factory=list)
