"""User Platform domain entities — authentication, profile, and saved items.

Provider-neutral, storage-neutral models for multi-user DealBrain accounts.
Demo / in-memory persistence only in Sprint 17. No OAuth, MFA, or email delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

DataStatus = Literal["mock", "imported", "live"]
ThemePreference = Literal["system", "light", "dark"]
AiModePreference = Literal["economy", "balanced", "maximum", "ask"]
SecurityEventType = Literal[
    "register",
    "login_success",
    "login_failure",
    "logout",
    "session_expired",
    "password_reset_requested",
    "password_changed",
    "email_verification_requested",
    "email_verified",
    "rate_limited",
    "csrf_rejected",
    "mfa_challenge",
    "oauth_link_attempt",
    "policy_accepted",
    "account_deletion_requested",
    "account_deleted",
    "data_export_requested",
    "data_export_completed",
]


@dataclass(frozen=True, slots=True)
class User:
    """Registered DealBrain account. Password is stored hashed only."""

    user_id: str
    email: str
    password_hash: str
    display_name: str
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    data_status: DataStatus = "mock"

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        payload = {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "data_status": self.data_status,
        }
        if include_sensitive:
            payload["password_hash"] = self.password_hash
        return payload


@dataclass(frozen=True, slots=True)
class UserPreference:
    """Persisted shopping preference dimensions for a user account."""

    user_id: str
    budget: float | None = None
    currency: str = "PHP"
    country: str = "PH"
    shopping_goals: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    battery_priority: float = 0.5
    camera_priority: float = 0.5
    performance_priority: float = 0.5
    travel_frequency: str = "occasional"
    creator_mode: bool = False
    gaming_mode: bool = False
    student_mode: bool = False
    business_mode: bool = False
    preferred_screen_size: tuple[str, ...] = ()
    preferred_colors: tuple[str, ...] = ()
    personal_profile_id: str | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "budget": self.budget,
            "currency": self.currency,
            "country": self.country,
            "shopping_goals": list(self.shopping_goals),
            "categories": list(self.categories),
            "battery_priority": self.battery_priority,
            "camera_priority": self.camera_priority,
            "performance_priority": self.performance_priority,
            "travel_frequency": self.travel_frequency,
            "creator_mode": self.creator_mode,
            "gaming_mode": self.gaming_mode,
            "student_mode": self.student_mode,
            "business_mode": self.business_mode,
            "preferred_screen_size": list(self.preferred_screen_size),
            "preferred_colors": list(self.preferred_colors),
            "personal_profile_id": self.personal_profile_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True, slots=True)
class FavoriteBrand:
    user_id: str
    brand: str
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "brand": self.brand,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class FavoriteMarketplace:
    user_id: str
    marketplace: str
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "marketplace": self.marketplace,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class Wishlist:
    user_id: str
    product_ids: tuple[str, ...] = ()
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "product_ids": list(self.product_ids),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True, slots=True)
class ProfileVersion:
    """Immutable profile change marker for audit / future sync."""

    user_id: str
    version: int
    changed_at: datetime | None = None
    change_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "version": self.version,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "change_summary": self.change_summary,
        }


@dataclass(frozen=True, slots=True)
class UserProfile:
    """Full account shopping profile composed of preferences and collections."""

    user_id: str
    display_name: str
    preferences: UserPreference
    favorite_brands: tuple[FavoriteBrand, ...] = ()
    favorite_marketplaces: tuple[FavoriteMarketplace, ...] = ()
    wishlist: Wishlist | None = None
    owned_products: tuple[str, ...] = ()
    accessories: tuple[str, ...] = ()
    version: ProfileVersion | None = None
    data_status: DataStatus = "mock"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "preferences": self.preferences.to_dict(),
            "favorite_brands": [item.to_dict() for item in self.favorite_brands],
            "favorite_marketplaces": [item.to_dict() for item in self.favorite_marketplaces],
            "wishlist": self.wishlist.to_dict()
            if self.wishlist
            else {"user_id": self.user_id, "product_ids": []},
            "owned_products": list(self.owned_products),
            "accessories": list(self.accessories),
            "version": self.version.to_dict() if self.version else None,
            "data_status": self.data_status,
            "budget": self.preferences.budget,
            "currency": self.preferences.currency,
            "country": self.preferences.country,
            "shopping_goals": list(self.preferences.shopping_goals),
            "categories": list(self.preferences.categories),
            "battery_priority": self.preferences.battery_priority,
            "camera_priority": self.preferences.camera_priority,
            "performance_priority": self.preferences.performance_priority,
            "travel_frequency": self.preferences.travel_frequency,
            "creator_mode": self.preferences.creator_mode,
            "gaming_mode": self.preferences.gaming_mode,
            "student_mode": self.preferences.student_mode,
            "business_mode": self.preferences.business_mode,
            "preferred_screen_size": list(self.preferences.preferred_screen_size),
            "preferred_colors": list(self.preferences.preferred_colors),
            "personal_profile_id": self.preferences.personal_profile_id,
        }


@dataclass(frozen=True, slots=True)
class NotificationPreference:
    user_id: str
    email_enabled: bool = False
    push_enabled: bool = False
    deal_alerts: bool = True
    price_drop_alerts: bool = True
    newsletter: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email_enabled": self.email_enabled,
            "push_enabled": self.push_enabled,
            "deal_alerts": self.deal_alerts,
            "price_drop_alerts": self.price_drop_alerts,
            "newsletter": self.newsletter,
        }


@dataclass(frozen=True, slots=True)
class UserSettings:
    user_id: str
    theme: ThemePreference = "system"
    language: str = "en"
    notification_settings: NotificationPreference | None = None
    ai_mode_preference: AiModePreference = "economy"
    privacy_settings: dict[str, Any] = field(default_factory=dict)
    community_settings: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "theme": self.theme,
            "language": self.language,
            "notification_settings": (
                self.notification_settings.to_dict() if self.notification_settings else None
            ),
            "ai_mode_preference": self.ai_mode_preference,
            "privacy_settings": dict(self.privacy_settings),
            "community_settings": dict(self.community_settings),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True, slots=True)
class UserSession:
    """Server-side session. Raw tokens are never persisted — only token_hash."""

    session_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    remember_me: bool = False
    last_seen_at: datetime | None = None
    user_agent: str | None = None
    ip_hint: str | None = None
    csrf_token: str | None = None
    revoked: bool = False

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        payload = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "remember_me": self.remember_me,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "user_agent": self.user_agent,
            "ip_hint": self.ip_hint,
            "revoked": self.revoked,
        }
        if include_sensitive:
            payload["token_hash"] = self.token_hash
            payload["csrf_token"] = self.csrf_token
        return payload


@dataclass(frozen=True, slots=True)
class SavedProduct:
    id: str
    user_id: str
    product_id: str
    product_name: str
    marketplace: str | None = None
    price: float | None = None
    currency: str = "PHP"
    notes: str = ""
    favorite: bool = False
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "marketplace": self.marketplace,
            "price": self.price,
            "currency": self.currency,
            "notes": self.notes,
            "favorite": self.favorite,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class SavedComparison:
    id: str
    user_id: str
    product_ids: tuple[str, ...]
    title: str = ""
    notes: str = ""
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_ids": list(self.product_ids),
            "title": self.title,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class RecommendationHistory:
    id: str
    user_id: str
    query: str
    recommendation_summary: str = ""
    product_ids: tuple[str, ...] = ()
    profile_id: str | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "recommendation_summary": self.recommendation_summary,
            "product_ids": list(self.product_ids),
            "profile_id": self.profile_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class SavedSearch:
    id: str
    user_id: str
    query: str
    filters: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "filters": dict(self.filters),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class RecentlyViewed:
    user_id: str
    product_ids: tuple[str, ...] = ()
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "product_ids": list(self.product_ids),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """Security / audit event hook payload. Persistence is optional."""

    event_id: str
    event_type: SecurityEventType
    user_id: str | None = None
    detail: str = ""
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthResult:
    """Successful authentication payload with opaque session token."""

    user: User
    session: UserSession
    access_token: str
    csrf_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user.to_dict(),
            "session": self.session.to_dict(),
            "access_token": self.access_token,
            "csrf_token": self.csrf_token or self.session.csrf_token,
            "token_type": "Bearer",
            "expires_at": self.session.expires_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class PasswordResetRequest:
    """Architecture-only password reset request record. No email is sent."""

    reset_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    consumed: bool = False

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        payload = {
            "reset_id": self.reset_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "consumed": self.consumed,
        }
        if include_sensitive:
            payload["token_hash"] = self.token_hash
        return payload


@dataclass(frozen=True, slots=True)
class EmailVerificationRequest:
    """Architecture-only email verification record. No email is sent."""

    verification_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    consumed: bool = False

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        payload = {
            "verification_id": self.verification_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "consumed": self.consumed,
        }
        if include_sensitive:
            payload["token_hash"] = self.token_hash
        return payload


ConsentPolicyType = Literal["terms", "privacy"]
ConsentSource = Literal["registration", "account", "test"]


def consent_identity_key(user_id: str, policy_type: str, version_id: str) -> str:
    """Durable uniqueness key for user + policy type + version."""
    return f"{user_id}:{policy_type}:{version_id}"


@dataclass(frozen=True, slots=True)
class PolicyAcceptanceRecord:
    """Server-owned acceptance of a *published* legal document version.

    Unpublished drafts must never be stored. Version ids are assigned by the
    server publication catalog, not by the client.
    """

    record_id: str
    user_id: str
    policy_type: ConsentPolicyType
    version_id: str
    accepted_at: datetime
    source: ConsentSource = "registration"
    actor: str | None = None

    @property
    def published_version_id(self) -> str:
        return self.version_id

    @property
    def identity_key(self) -> str:
        return consent_identity_key(self.user_id, self.policy_type, self.version_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "policy_type": self.policy_type,
            "version_id": self.version_id,
            "accepted_at": self.accepted_at.isoformat(),
            "source": self.source,
            "actor": self.actor,
        }
