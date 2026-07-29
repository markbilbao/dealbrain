"""Future persistence adapters for the User Platform.

Sprint 17 ships in-memory repositories only. These stubs document how
SQLAlchemy / document-store backends should implement the same ports
without locking the architecture to one database.
"""

from __future__ import annotations

from typing import Any

from app.domain.entities.user_platform import (
    EmailVerificationRequest,
    FavoriteBrand,
    FavoriteMarketplace,
    PasswordResetRequest,
    RecentlyViewed,
    RecommendationHistory,
    SavedComparison,
    SavedProduct,
    SavedSearch,
    SecurityEvent,
    User,
    UserPreference,
    UserProfile,
    UserSession,
    UserSettings,
    Wishlist,
)
from app.domain.interfaces.user_platform_repository import (
    AuditLogRepository,
    EmailVerificationRepository,
    PasswordResetRepository,
    ProfileRepository,
    SavedItemsRepository,
    SessionRepository,
    UserRepository,
)


class FutureSqlUserRepository(UserRepository):
    """Placeholder SQLAlchemy adapter — not wired in Sprint 17."""

    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory

    def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError("SQL user adapter is not implemented in Sprint 17.")

    def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError("SQL user adapter is not implemented in Sprint 17.")

    def save(self, user: User) -> User:
        raise NotImplementedError("SQL user adapter is not implemented in Sprint 17.")

    def list_users(self) -> list[User]:
        raise NotImplementedError("SQL user adapter is not implemented in Sprint 17.")


class FutureSqlSessionRepository(SessionRepository):
    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory

    def get_by_id(self, session_id: str) -> UserSession | None:
        raise NotImplementedError("SQL session adapter is not implemented in Sprint 17.")

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        raise NotImplementedError("SQL session adapter is not implemented in Sprint 17.")

    def save(self, session: UserSession) -> UserSession:
        raise NotImplementedError("SQL session adapter is not implemented in Sprint 17.")

    def revoke(self, session_id: str) -> None:
        raise NotImplementedError("SQL session adapter is not implemented in Sprint 17.")

    def revoke_all_for_user(self, user_id: str) -> int:
        raise NotImplementedError("SQL session adapter is not implemented in Sprint 17.")

    def list_for_user(self, user_id: str) -> list[UserSession]:
        raise NotImplementedError("SQL session adapter is not implemented in Sprint 17.")


class FutureSqlProfileRepository(ProfileRepository):
    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory

    def get_profile(self, user_id: str) -> UserProfile | None:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def save_profile(self, profile: UserProfile) -> UserProfile:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def get_preferences(self, user_id: str) -> UserPreference | None:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def save_preferences(self, preferences: UserPreference) -> UserPreference:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def get_settings(self, user_id: str) -> UserSettings | None:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def save_settings(self, settings: UserSettings) -> UserSettings:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def save_wishlist(self, wishlist: Wishlist) -> Wishlist:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def set_favorite_brands(self, user_id: str, brands: list[FavoriteBrand]) -> list[FavoriteBrand]:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")

    def set_favorite_marketplaces(
        self, user_id: str, marketplaces: list[FavoriteMarketplace]
    ) -> list[FavoriteMarketplace]:
        raise NotImplementedError("SQL profile adapter is not implemented in Sprint 17.")


class FutureNoSqlSavedItemsRepository(SavedItemsRepository):
    """Placeholder document-store adapter — not wired in Sprint 17."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def list_saved_products(self, user_id: str) -> list[SavedProduct]:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def get_saved_product(self, user_id: str, saved_id: str) -> SavedProduct | None:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def save_product(self, item: SavedProduct) -> SavedProduct:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def delete_saved_product(self, user_id: str, saved_id: str) -> None:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def list_comparisons(self, user_id: str) -> list[SavedComparison]:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def save_comparison(self, item: SavedComparison) -> SavedComparison:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def list_history(self, user_id: str) -> list[RecommendationHistory]:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def add_history(self, item: RecommendationHistory) -> RecommendationHistory:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def list_searches(self, user_id: str) -> list[SavedSearch]:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def save_search(self, item: SavedSearch) -> SavedSearch:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def get_recently_viewed(self, user_id: str) -> RecentlyViewed | None:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")

    def save_recently_viewed(self, item: RecentlyViewed) -> RecentlyViewed:
        raise NotImplementedError("NoSQL saved-items adapter is not implemented in Sprint 17.")


class FutureSqlPasswordResetRepository(PasswordResetRepository):
    def save(self, request: PasswordResetRequest) -> PasswordResetRequest:
        raise NotImplementedError("SQL password-reset adapter is not implemented in Sprint 17.")

    def get_by_token_hash(self, token_hash: str) -> PasswordResetRequest | None:
        raise NotImplementedError("SQL password-reset adapter is not implemented in Sprint 17.")

    def mark_consumed(self, reset_id: str) -> None:
        raise NotImplementedError("SQL password-reset adapter is not implemented in Sprint 17.")


class FutureSqlEmailVerificationRepository(EmailVerificationRepository):
    def save(self, request: EmailVerificationRequest) -> EmailVerificationRequest:
        raise NotImplementedError("SQL email-verification adapter is not implemented in Sprint 17.")

    def get_by_token_hash(self, token_hash: str) -> EmailVerificationRequest | None:
        raise NotImplementedError("SQL email-verification adapter is not implemented in Sprint 17.")

    def mark_consumed(self, verification_id: str) -> None:
        raise NotImplementedError("SQL email-verification adapter is not implemented in Sprint 17.")


class FutureSqlAuditLogRepository(AuditLogRepository):
    def append(self, event: SecurityEvent) -> SecurityEvent:
        raise NotImplementedError("SQL audit adapter is not implemented in Sprint 17.")

    def list_events(self, *, user_id: str | None = None, limit: int = 100) -> list[SecurityEvent]:
        raise NotImplementedError("SQL audit adapter is not implemented in Sprint 17.")


USER_PLATFORM_BACKENDS: tuple[str, ...] = ("memory", "sqlalchemy", "nosql")
