"""In-memory persistence adapters for the User Platform.

Process-scoped stores implementing repository ports. Designed so SQL/NoSQL
adapters can replace these without changing services or API layers.
"""

from __future__ import annotations

from app.domain.entities.user_platform import (
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
from app.domain.exceptions import UserPlatformNotFoundError, UserPlatformValidationError
from app.domain.interfaces.user_platform_repository import (
    AuditLogRepository,
    ConsentRepository,
    EmailVerificationRepository,
    PasswordResetRepository,
    ProfileRepository,
    SavedItemsRepository,
    SessionRepository,
    UserRepository,
)


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, str] = {}

    def get_by_id(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        user_id = self._by_email.get(email.strip().lower())
        return self._by_id.get(user_id) if user_id else None

    def save(self, user: User) -> User:
        email = user.email.strip().lower()
        existing_id = self._by_email.get(email)
        if existing_id and existing_id != user.user_id:
            raise UserPlatformValidationError(f"Email already registered: {email}")
        # Drop stale email index if email changed.
        for key, value in list(self._by_email.items()):
            if value == user.user_id and key != email:
                del self._by_email[key]
        self._by_id[user.user_id] = user
        self._by_email[email] = user.user_id
        return user

    def list_users(self) -> list[User]:
        return [self._by_id[key] for key in sorted(self._by_id)]

    def delete(self, user_id: str) -> bool:
        user = self._by_id.pop(user_id, None)
        if user is None:
            return False
        email = user.email.strip().lower()
        if self._by_email.get(email) == user_id:
            del self._by_email[email]
        return True


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, UserSession] = {}
        self._by_token: dict[str, str] = {}

    def get_by_id(self, session_id: str) -> UserSession | None:
        return self._by_id.get(session_id)

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        session_id = self._by_token.get(token_hash)
        return self._by_id.get(session_id) if session_id else None

    def save(self, session: UserSession) -> UserSession:
        # Remove previous token index for this session.
        previous = self._by_id.get(session.session_id)
        if (
            previous is not None
            and previous.token_hash in self._by_token
            and self._by_token[previous.token_hash] == session.session_id
        ):
            del self._by_token[previous.token_hash]
        self._by_id[session.session_id] = session
        self._by_token[session.token_hash] = session.session_id
        return session

    def revoke(self, session_id: str) -> None:
        session = self._by_id.get(session_id)
        if session is None:
            return
        revoked = UserSession(
            session_id=session.session_id,
            user_id=session.user_id,
            token_hash=session.token_hash,
            created_at=session.created_at,
            expires_at=session.expires_at,
            remember_me=session.remember_me,
            last_seen_at=session.last_seen_at,
            user_agent=session.user_agent,
            ip_hint=session.ip_hint,
            csrf_token=session.csrf_token,
            revoked=True,
        )
        self.save(revoked)

    def revoke_all_for_user(self, user_id: str) -> int:
        count = 0
        for session in list(self._by_id.values()):
            if session.user_id == user_id and not session.revoked:
                self.revoke(session.session_id)
                count += 1
        return count

    def list_for_user(self, user_id: str) -> list[UserSession]:
        return [s for s in self._by_id.values() if s.user_id == user_id]

    def delete_all_for_user(self, user_id: str) -> int:
        count = 0
        for session in list(self._by_id.values()):
            if session.user_id != user_id:
                continue
            if self._by_token.get(session.token_hash) == session.session_id:
                del self._by_token[session.token_hash]
            del self._by_id[session.session_id]
            count += 1
        return count


class InMemoryProfileRepository(ProfileRepository):
    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._preferences: dict[str, UserPreference] = {}
        self._settings: dict[str, UserSettings] = {}
        self._wishlists: dict[str, Wishlist] = {}
        self._brands: dict[str, list[FavoriteBrand]] = {}
        self._markets: dict[str, list[FavoriteMarketplace]] = {}

    def get_profile(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)

    def save_profile(self, profile: UserProfile) -> UserProfile:
        self._profiles[profile.user_id] = profile
        self._preferences[profile.user_id] = profile.preferences
        if profile.wishlist is not None:
            self._wishlists[profile.user_id] = profile.wishlist
        self._brands[profile.user_id] = list(profile.favorite_brands)
        self._markets[profile.user_id] = list(profile.favorite_marketplaces)
        return profile

    def get_preferences(self, user_id: str) -> UserPreference | None:
        return self._preferences.get(user_id)

    def save_preferences(self, preferences: UserPreference) -> UserPreference:
        self._preferences[preferences.user_id] = preferences
        profile = self._profiles.get(preferences.user_id)
        if profile is not None:
            self._profiles[preferences.user_id] = UserProfile(
                user_id=profile.user_id,
                display_name=profile.display_name,
                preferences=preferences,
                favorite_brands=profile.favorite_brands,
                favorite_marketplaces=profile.favorite_marketplaces,
                wishlist=profile.wishlist,
                owned_products=profile.owned_products,
                accessories=profile.accessories,
                version=profile.version,
                data_status=profile.data_status,
            )
        return preferences

    def get_settings(self, user_id: str) -> UserSettings | None:
        return self._settings.get(user_id)

    def save_settings(self, settings: UserSettings) -> UserSettings:
        self._settings[settings.user_id] = settings
        return settings

    def save_wishlist(self, wishlist: Wishlist) -> Wishlist:
        self._wishlists[wishlist.user_id] = wishlist
        profile = self._profiles.get(wishlist.user_id)
        if profile is not None:
            self._profiles[wishlist.user_id] = UserProfile(
                user_id=profile.user_id,
                display_name=profile.display_name,
                preferences=profile.preferences,
                favorite_brands=profile.favorite_brands,
                favorite_marketplaces=profile.favorite_marketplaces,
                wishlist=wishlist,
                owned_products=profile.owned_products,
                accessories=profile.accessories,
                version=profile.version,
                data_status=profile.data_status,
            )
        return wishlist

    def set_favorite_brands(self, user_id: str, brands: list[FavoriteBrand]) -> list[FavoriteBrand]:
        self._brands[user_id] = list(brands)
        return list(brands)

    def set_favorite_marketplaces(
        self, user_id: str, marketplaces: list[FavoriteMarketplace]
    ) -> list[FavoriteMarketplace]:
        self._markets[user_id] = list(marketplaces)
        return list(marketplaces)

    def delete_for_user(self, user_id: str) -> None:
        self._profiles.pop(user_id, None)
        self._preferences.pop(user_id, None)
        self._settings.pop(user_id, None)
        self._wishlists.pop(user_id, None)
        self._brands.pop(user_id, None)
        self._markets.pop(user_id, None)


class InMemorySavedItemsRepository(SavedItemsRepository):
    def __init__(self) -> None:
        self._products: dict[str, SavedProduct] = {}
        self._comparisons: dict[str, SavedComparison] = {}
        self._history: dict[str, RecommendationHistory] = {}
        self._searches: dict[str, SavedSearch] = {}
        self._recent: dict[str, RecentlyViewed] = {}

    def list_saved_products(self, user_id: str) -> list[SavedProduct]:
        return sorted(
            [p for p in self._products.values() if p.user_id == user_id],
            key=lambda p: p.created_at.isoformat() if p.created_at else p.id,
            reverse=True,
        )

    def get_saved_product(self, user_id: str, saved_id: str) -> SavedProduct | None:
        item = self._products.get(saved_id)
        if item is None or item.user_id != user_id:
            return None
        return item

    def save_product(self, item: SavedProduct) -> SavedProduct:
        self._products[item.id] = item
        return item

    def delete_saved_product(self, user_id: str, saved_id: str) -> None:
        item = self.get_saved_product(user_id, saved_id)
        if item is None:
            raise UserPlatformNotFoundError(saved_id)
        del self._products[saved_id]

    def list_comparisons(self, user_id: str) -> list[SavedComparison]:
        return [c for c in self._comparisons.values() if c.user_id == user_id]

    def save_comparison(self, item: SavedComparison) -> SavedComparison:
        self._comparisons[item.id] = item
        return item

    def list_history(self, user_id: str) -> list[RecommendationHistory]:
        return sorted(
            [h for h in self._history.values() if h.user_id == user_id],
            key=lambda h: h.created_at.isoformat() if h.created_at else h.id,
            reverse=True,
        )

    def add_history(self, item: RecommendationHistory) -> RecommendationHistory:
        self._history[item.id] = item
        return item

    def list_searches(self, user_id: str) -> list[SavedSearch]:
        return [s for s in self._searches.values() if s.user_id == user_id]

    def save_search(self, item: SavedSearch) -> SavedSearch:
        self._searches[item.id] = item
        return item

    def get_recently_viewed(self, user_id: str) -> RecentlyViewed | None:
        return self._recent.get(user_id)

    def save_recently_viewed(self, item: RecentlyViewed) -> RecentlyViewed:
        self._recent[item.user_id] = item
        return item

    def delete_all_for_user(self, user_id: str) -> None:
        for saved_id, item in list(self._products.items()):
            if item.user_id == user_id:
                del self._products[saved_id]
        for item_id, item in list(self._comparisons.items()):
            if item.user_id == user_id:
                del self._comparisons[item_id]
        for item_id, item in list(self._history.items()):
            if item.user_id == user_id:
                del self._history[item_id]
        for item_id, item in list(self._searches.items()):
            if item.user_id == user_id:
                del self._searches[item_id]
        self._recent.pop(user_id, None)


class InMemoryPasswordResetRepository(PasswordResetRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, PasswordResetRequest] = {}
        self._by_token: dict[str, str] = {}

    def save(self, request: PasswordResetRequest) -> PasswordResetRequest:
        self._by_id[request.reset_id] = request
        self._by_token[request.token_hash] = request.reset_id
        return request

    def get_by_token_hash(self, token_hash: str) -> PasswordResetRequest | None:
        reset_id = self._by_token.get(token_hash)
        return self._by_id.get(reset_id) if reset_id else None

    def mark_consumed(self, reset_id: str) -> None:
        request = self._by_id.get(reset_id)
        if request is None:
            return
        self._by_id[reset_id] = PasswordResetRequest(
            reset_id=request.reset_id,
            user_id=request.user_id,
            token_hash=request.token_hash,
            created_at=request.created_at,
            expires_at=request.expires_at,
            consumed=True,
        )

    def delete_for_user(self, user_id: str) -> int:
        count = 0
        for reset in list(self._by_id.values()):
            if reset.user_id != user_id:
                continue
            del self._by_id[reset.reset_id]
            if self._by_token.get(reset.token_hash) == reset.reset_id:
                del self._by_token[reset.token_hash]
            count += 1
        return count


class InMemoryEmailVerificationRepository(EmailVerificationRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, EmailVerificationRequest] = {}
        self._by_token: dict[str, str] = {}

    def save(self, request: EmailVerificationRequest) -> EmailVerificationRequest:
        self._by_id[request.verification_id] = request
        self._by_token[request.token_hash] = request.verification_id
        return request

    def get_by_token_hash(self, token_hash: str) -> EmailVerificationRequest | None:
        verification_id = self._by_token.get(token_hash)
        return self._by_id.get(verification_id) if verification_id else None

    def mark_consumed(self, verification_id: str) -> None:
        request = self._by_id.get(verification_id)
        if request is None:
            return
        self._by_id[verification_id] = EmailVerificationRequest(
            verification_id=request.verification_id,
            user_id=request.user_id,
            token_hash=request.token_hash,
            created_at=request.created_at,
            expires_at=request.expires_at,
            consumed=True,
        )

    def delete_for_user(self, user_id: str) -> int:
        count = 0
        for item in list(self._by_id.values()):
            if item.user_id != user_id:
                continue
            del self._by_id[item.verification_id]
            if self._by_token.get(item.token_hash) == item.verification_id:
                del self._by_token[item.token_hash]
            count += 1
        return count


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._events: list[SecurityEvent] = []

    def append(self, event: SecurityEvent) -> SecurityEvent:
        self._events.append(event)
        return event

    def list_events(self, *, user_id: str | None = None, limit: int = 100) -> list[SecurityEvent]:
        items = [e for e in self._events if user_id is None or e.user_id == user_id]
        return items[-limit:]


class InMemoryConsentRepository(ConsentRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, PolicyAcceptanceRecord] = {}

    def get(self, user_id: str, policy_type: str, version_id: str) -> PolicyAcceptanceRecord | None:
        for record in self._by_id.values():
            if (
                record.user_id == user_id
                and record.policy_type == policy_type
                and record.version_id == version_id
            ):
                return record
        return None

    def save(self, record: PolicyAcceptanceRecord) -> PolicyAcceptanceRecord:
        existing = self.get(record.user_id, record.policy_type, record.version_id)
        if existing is not None:
            return existing
        self._by_id[record.record_id] = record
        return record

    def list_for_user(self, user_id: str) -> list[PolicyAcceptanceRecord]:
        return sorted(
            [item for item in self._by_id.values() if item.user_id == user_id],
            key=lambda item: item.accepted_at.isoformat(),
        )

    def delete_for_user(self, user_id: str) -> int:
        count = 0
        for record_id, record in list(self._by_id.items()):
            if record.user_id == user_id:
                del self._by_id[record_id]
                count += 1
        return count


class InMemoryUserPlatformStore:
    """Composite in-memory unit of work for wiring services and demo seeding."""

    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.sessions = InMemorySessionRepository()
        self.profiles = InMemoryProfileRepository()
        self.saved = InMemorySavedItemsRepository()
        self.password_resets = InMemoryPasswordResetRepository()
        self.email_verifications = InMemoryEmailVerificationRepository()
        self.audit = InMemoryAuditLogRepository()
        self.consents = InMemoryConsentRepository()
