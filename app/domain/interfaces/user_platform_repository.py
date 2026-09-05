"""Repository ports for the User Platform bounded context.

Storage-neutral interfaces. Sprint 17 ships in-memory adapters only;
SQL / NoSQL adapters are designed as future implementations of these ports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.user_platform import (
    EmailChangeRequest,
    EmailVerificationRequest,
    FavoriteBrand,
    FavoriteMarketplace,
    PasswordResetRequest,
    PolicyAcceptanceRecord,
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


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Remove the user record. Returns False if the user was already absent."""
        raise NotImplementedError


class SessionRepository(ABC):
    @abstractmethod
    def get_by_id(self, session_id: str) -> UserSession | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, session: UserSession) -> UserSession:
        raise NotImplementedError

    @abstractmethod
    def revoke(self, session_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def revoke_all_for_user(self, user_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_for_user(self, user_id: str) -> list[UserSession]:
        raise NotImplementedError

    @abstractmethod
    def delete_all_for_user(self, user_id: str) -> int:
        """Physically remove session records for the user. Returns count removed."""
        raise NotImplementedError


class ProfileRepository(ABC):
    @abstractmethod
    def get_profile(self, user_id: str) -> UserProfile | None:
        raise NotImplementedError

    @abstractmethod
    def save_profile(self, profile: UserProfile) -> UserProfile:
        raise NotImplementedError

    @abstractmethod
    def get_preferences(self, user_id: str) -> UserPreference | None:
        raise NotImplementedError

    @abstractmethod
    def save_preferences(self, preferences: UserPreference) -> UserPreference:
        raise NotImplementedError

    @abstractmethod
    def get_settings(self, user_id: str) -> UserSettings | None:
        raise NotImplementedError

    @abstractmethod
    def save_settings(self, settings: UserSettings) -> UserSettings:
        raise NotImplementedError

    @abstractmethod
    def save_wishlist(self, wishlist: Wishlist) -> Wishlist:
        raise NotImplementedError

    @abstractmethod
    def set_favorite_brands(self, user_id: str, brands: list[FavoriteBrand]) -> list[FavoriteBrand]:
        raise NotImplementedError

    @abstractmethod
    def set_favorite_marketplaces(
        self, user_id: str, marketplaces: list[FavoriteMarketplace]
    ) -> list[FavoriteMarketplace]:
        raise NotImplementedError

    @abstractmethod
    def delete_for_user(self, user_id: str) -> None:
        """Remove profile, preferences, settings, wishlist, and favorites."""
        raise NotImplementedError


class SavedItemsRepository(ABC):
    @abstractmethod
    def list_saved_products(self, user_id: str) -> list[SavedProduct]:
        raise NotImplementedError

    @abstractmethod
    def get_saved_product(self, user_id: str, saved_id: str) -> SavedProduct | None:
        raise NotImplementedError

    @abstractmethod
    def save_product(self, item: SavedProduct) -> SavedProduct:
        raise NotImplementedError

    @abstractmethod
    def delete_saved_product(self, user_id: str, saved_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_comparisons(self, user_id: str) -> list[SavedComparison]:
        raise NotImplementedError

    @abstractmethod
    def save_comparison(self, item: SavedComparison) -> SavedComparison:
        raise NotImplementedError

    @abstractmethod
    def list_history(self, user_id: str) -> list[RecommendationHistory]:
        raise NotImplementedError

    @abstractmethod
    def add_history(self, item: RecommendationHistory) -> RecommendationHistory:
        raise NotImplementedError

    @abstractmethod
    def list_searches(self, user_id: str) -> list[SavedSearch]:
        raise NotImplementedError

    @abstractmethod
    def save_search(self, item: SavedSearch) -> SavedSearch:
        raise NotImplementedError

    @abstractmethod
    def get_recently_viewed(self, user_id: str) -> RecentlyViewed | None:
        raise NotImplementedError

    @abstractmethod
    def save_recently_viewed(self, item: RecentlyViewed) -> RecentlyViewed:
        raise NotImplementedError

    @abstractmethod
    def delete_all_for_user(self, user_id: str) -> None:
        """Remove saved products, comparisons, history, searches, and recently viewed."""
        raise NotImplementedError


class PasswordResetRepository(ABC):
    @abstractmethod
    def save(self, request: PasswordResetRequest) -> PasswordResetRequest:
        raise NotImplementedError

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> PasswordResetRequest | None:
        raise NotImplementedError

    @abstractmethod
    def mark_consumed(self, reset_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_for_user(self, user_id: str) -> int:
        raise NotImplementedError


class EmailVerificationRepository(ABC):
    @abstractmethod
    def save(self, request: EmailVerificationRequest) -> EmailVerificationRequest:
        raise NotImplementedError

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> EmailVerificationRequest | None:
        raise NotImplementedError

    @abstractmethod
    def mark_consumed(self, verification_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_for_user(self, user_id: str) -> int:
        raise NotImplementedError


class EmailChangeRepository(ABC):
    @abstractmethod
    def save(self, request: EmailChangeRequest) -> EmailChangeRequest:
        raise NotImplementedError

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> EmailChangeRequest | None:
        raise NotImplementedError

    @abstractmethod
    def mark_consumed(self, change_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_for_user(self, user_id: str) -> list[EmailChangeRequest]:
        raise NotImplementedError

    @abstractmethod
    def invalidate_for_user(self, user_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def delete_for_user(self, user_id: str) -> int:
        raise NotImplementedError


class ConsentRepository(ABC):
    """Persistence for published-policy acceptance records."""

    @abstractmethod
    def save(self, record: PolicyAcceptanceRecord) -> PolicyAcceptanceRecord:
        raise NotImplementedError

    @abstractmethod
    def list_for_user(self, user_id: str) -> list[PolicyAcceptanceRecord]:
        raise NotImplementedError

    @abstractmethod
    def get(self, user_id: str, policy_type: str, version_id: str) -> PolicyAcceptanceRecord | None:
        raise NotImplementedError

    @abstractmethod
    def delete_for_user(self, user_id: str) -> int:
        raise NotImplementedError


class AuditLogRepository(ABC):
    """Optional audit sink for security events."""

    @abstractmethod
    def append(self, event: SecurityEvent) -> SecurityEvent:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, *, user_id: str | None = None, limit: int = 100) -> list[SecurityEvent]:
        raise NotImplementedError
