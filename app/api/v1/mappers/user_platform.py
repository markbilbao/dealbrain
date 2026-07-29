"""Map User Platform domain objects to HTTP schemas."""

from __future__ import annotations

from typing import Any

from app.domain.entities.user_platform import (
    AuthResult,
    RecentlyViewed,
    RecommendationHistory,
    SavedComparison,
    SavedProduct,
    SavedSearch,
    User,
    UserPreference,
    UserProfile,
    UserSession,
    UserSettings,
)
from app.schemas.user_platform import (
    AuthResponse,
    PreferencesPayload,
    ProfileResponse,
    RecentlyViewedPayload,
    RecommendationHistoryPayload,
    SavedComparisonPayload,
    SavedProductPayload,
    SavedSearchPayload,
    SessionPayload,
    SettingsPayload,
    UserPayload,
    UserPlatformDemoResponse,
    UserPlatformMetaResponse,
)


def to_user_payload(user: User) -> UserPayload:
    return UserPayload(**user.to_dict())


def to_session_payload(session: UserSession) -> SessionPayload:
    return SessionPayload(**session.to_dict())


def to_auth_response(result: AuthResult) -> AuthResponse:
    data = result.to_dict()
    return AuthResponse(
        user=UserPayload(**data["user"]),
        session=SessionPayload(**data["session"]),
        access_token=data["access_token"],
        csrf_token=data.get("csrf_token"),
        token_type=data.get("token_type", "Bearer"),
        expires_at=data["expires_at"],
    )


def to_profile_response(profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(**profile.to_dict())


def to_preferences_payload(preferences: UserPreference) -> PreferencesPayload:
    return PreferencesPayload(**preferences.to_dict())


def to_settings_payload(settings: UserSettings) -> SettingsPayload:
    return SettingsPayload(**settings.to_dict())


def to_saved_product_payload(item: SavedProduct) -> SavedProductPayload:
    return SavedProductPayload(**item.to_dict())


def to_saved_comparison_payload(item: SavedComparison) -> SavedComparisonPayload:
    return SavedComparisonPayload(**item.to_dict())


def to_history_payload(item: RecommendationHistory) -> RecommendationHistoryPayload:
    return RecommendationHistoryPayload(**item.to_dict())


def to_saved_search_payload(item: SavedSearch) -> SavedSearchPayload:
    return SavedSearchPayload(**item.to_dict())


def to_recently_viewed_payload(item: RecentlyViewed) -> RecentlyViewedPayload:
    return RecentlyViewedPayload(**item.to_dict())


def to_meta_response(data: dict[str, Any]) -> UserPlatformMetaResponse:
    return UserPlatformMetaResponse(**data)


def to_demo_response(data: dict[str, Any]) -> UserPlatformDemoResponse:
    return UserPlatformDemoResponse(**data)
