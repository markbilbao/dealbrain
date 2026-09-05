"""SQLAlchemy persistence adapters for the User Platform — Sprint 23."""

from __future__ import annotations

from dataclasses import dataclass

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
    consent_identity_key,
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
from app.infrastructure.persistence.errors import PersistenceConflictError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import (
    AUDIT_EVENTS,
    CONSENT_RECORDS,
    EMAIL_VERIFICATIONS,
    FAVORITE_BRANDS,
    FAVORITE_MARKETPLACES,
    PASSWORD_RESETS,
    PREFERENCES,
    PROFILES,
    RECENTLY_VIEWED,
    RECOMMENDATION_HISTORY,
    SAVED_COMPARISONS,
    SAVED_PRODUCTS,
    SAVED_SEARCHES,
    SESSIONS,
    SETTINGS,
    USERS,
    WISHLISTS,
)


@dataclass(frozen=True, slots=True)
class _BrandList:
    user_id: str
    brands: tuple[FavoriteBrand, ...]


@dataclass(frozen=True, slots=True)
class _MarketplaceList:
    user_id: str
    marketplaces: tuple[FavoriteMarketplace, ...]


class SqlAlchemyUserRepository(UserRepository, SessionBound):
    def get_by_id(self, user_id: str) -> User | None:
        with self._ops() as ops:
            return ops.get(USERS, user_id, User)

    def get_by_email(self, email: str) -> User | None:
        with self._ops() as ops:
            return ops.get_by_secondary(USERS, email.strip().lower(), User)

    def save(self, user: User) -> User:
        email = user.email.strip().lower()
        with self._ops() as ops:
            existing = ops.get_by_secondary(USERS, email, User)
            if existing is not None and existing.user_id != user.user_id:
                raise UserPlatformValidationError(f"Email already registered: {email}")
            try:
                return ops.upsert(
                    USERS,
                    user.user_id,
                    user,
                    secondary_key=email,
                )
            except PersistenceConflictError as exc:
                raise UserPlatformValidationError(
                    f"Email already registered: {email}"
                ) from exc

    def list_users(self) -> list[User]:
        with self._ops() as ops:
            users = ops.list(USERS, User)
            return sorted(users, key=lambda u: u.user_id)

    def delete(self, user_id: str) -> bool:
        with self._ops() as ops:
            if ops.get(USERS, user_id, User) is None:
                return False
            return ops.delete(USERS, user_id)


class SqlAlchemySessionRepository(SessionRepository, SessionBound):
    def get_by_id(self, session_id: str) -> UserSession | None:
        with self._ops() as ops:
            return ops.get(SESSIONS, session_id, UserSession)

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        with self._ops() as ops:
            return ops.get_by_secondary(SESSIONS, token_hash, UserSession)

    def save(self, session: UserSession) -> UserSession:
        with self._ops() as ops:
            return ops.upsert(
                SESSIONS,
                session.session_id,
                session,
                secondary_key=session.token_hash,
                owner_id=session.user_id,
            )

    def revoke(self, session_id: str) -> None:
        with self._ops() as ops:
            session = ops.get(SESSIONS, session_id, UserSession)
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
            ops.upsert(
                SESSIONS,
                revoked.session_id,
                revoked,
                secondary_key=revoked.token_hash,
                owner_id=revoked.user_id,
            )

    def revoke_all_for_user(self, user_id: str) -> int:
        with self._ops() as ops:
            sessions = ops.list(SESSIONS, UserSession, owner_id=user_id)
            count = 0
            for session in sessions:
                if not session.revoked:
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
                    ops.upsert(
                        SESSIONS,
                        revoked.session_id,
                        revoked,
                        secondary_key=revoked.token_hash,
                        owner_id=revoked.user_id,
                    )
                    count += 1
            return count

    def list_for_user(self, user_id: str) -> list[UserSession]:
        with self._ops() as ops:
            return ops.list(SESSIONS, UserSession, owner_id=user_id)

    def delete_all_for_user(self, user_id: str) -> int:
        with self._ops() as ops:
            sessions = ops.list(SESSIONS, UserSession, owner_id=user_id)
            for session in sessions:
                ops.delete(SESSIONS, session.session_id)
            return len(sessions)


class SqlAlchemyProfileRepository(ProfileRepository, SessionBound):
    def get_profile(self, user_id: str) -> UserProfile | None:
        with self._ops() as ops:
            return ops.get(PROFILES, user_id, UserProfile)

    def save_profile(self, profile: UserProfile) -> UserProfile:
        with self._ops() as ops:
            ops.upsert(PROFILES, profile.user_id, profile, owner_id=profile.user_id)
            ops.upsert(
                PREFERENCES,
                profile.user_id,
                profile.preferences,
                owner_id=profile.user_id,
            )
            if profile.wishlist is not None:
                ops.upsert(
                    WISHLISTS,
                    profile.user_id,
                    profile.wishlist,
                    owner_id=profile.user_id,
                )
            ops.upsert(
                FAVORITE_BRANDS,
                profile.user_id,
                _BrandList(profile.user_id, tuple(profile.favorite_brands)),
                owner_id=profile.user_id,
            )
            ops.upsert(
                FAVORITE_MARKETPLACES,
                profile.user_id,
                _MarketplaceList(profile.user_id, tuple(profile.favorite_marketplaces)),
                owner_id=profile.user_id,
            )
            return profile

    def get_preferences(self, user_id: str) -> UserPreference | None:
        with self._ops() as ops:
            return ops.get(PREFERENCES, user_id, UserPreference)

    def save_preferences(self, preferences: UserPreference) -> UserPreference:
        with self._ops() as ops:
            ops.upsert(
                PREFERENCES,
                preferences.user_id,
                preferences,
                owner_id=preferences.user_id,
            )
            profile = ops.get(PROFILES, preferences.user_id, UserProfile)
            if profile is not None:
                ops.upsert(
                    PROFILES,
                    profile.user_id,
                    UserProfile(
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
                    ),
                    owner_id=profile.user_id,
                )
            return preferences

    def get_settings(self, user_id: str) -> UserSettings | None:
        with self._ops() as ops:
            return ops.get(SETTINGS, user_id, UserSettings)

    def save_settings(self, settings: UserSettings) -> UserSettings:
        with self._ops() as ops:
            return ops.upsert(
                SETTINGS,
                settings.user_id,
                settings,
                owner_id=settings.user_id,
            )

    def save_wishlist(self, wishlist: Wishlist) -> Wishlist:
        with self._ops() as ops:
            ops.upsert(WISHLISTS, wishlist.user_id, wishlist, owner_id=wishlist.user_id)
            profile = ops.get(PROFILES, wishlist.user_id, UserProfile)
            if profile is not None:
                ops.upsert(
                    PROFILES,
                    profile.user_id,
                    UserProfile(
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
                    ),
                    owner_id=profile.user_id,
                )
            return wishlist

    def set_favorite_brands(self, user_id: str, brands: list[FavoriteBrand]) -> list[FavoriteBrand]:
        with self._ops() as ops:
            ops.upsert(
                FAVORITE_BRANDS,
                user_id,
                _BrandList(user_id, tuple(brands)),
                owner_id=user_id,
            )
            return list(brands)

    def set_favorite_marketplaces(
        self, user_id: str, marketplaces: list[FavoriteMarketplace]
    ) -> list[FavoriteMarketplace]:
        with self._ops() as ops:
            ops.upsert(
                FAVORITE_MARKETPLACES,
                user_id,
                _MarketplaceList(user_id, tuple(marketplaces)),
                owner_id=user_id,
            )
            return list(marketplaces)

    def delete_for_user(self, user_id: str) -> None:
        with self._ops() as ops:
            ops.delete(PROFILES, user_id)
            ops.delete(PREFERENCES, user_id)
            ops.delete(SETTINGS, user_id)
            ops.delete(WISHLISTS, user_id)
            ops.delete(FAVORITE_BRANDS, user_id)
            ops.delete(FAVORITE_MARKETPLACES, user_id)


class SqlAlchemySavedItemsRepository(SavedItemsRepository, SessionBound):
    def list_saved_products(self, user_id: str) -> list[SavedProduct]:
        with self._ops() as ops:
            items = ops.list(SAVED_PRODUCTS, SavedProduct, owner_id=user_id)
            return sorted(
                items,
                key=lambda p: p.created_at.isoformat() if p.created_at else p.id,
                reverse=True,
            )

    def get_saved_product(self, user_id: str, saved_id: str) -> SavedProduct | None:
        with self._ops() as ops:
            item = ops.get(SAVED_PRODUCTS, saved_id, SavedProduct)
            if item is None or item.user_id != user_id:
                return None
            return item

    def save_product(self, item: SavedProduct) -> SavedProduct:
        with self._ops() as ops:
            return ops.upsert(SAVED_PRODUCTS, item.id, item, owner_id=item.user_id)

    def delete_saved_product(self, user_id: str, saved_id: str) -> None:
        with self._ops() as ops:
            item = ops.get(SAVED_PRODUCTS, saved_id, SavedProduct)
            if item is None or item.user_id != user_id:
                raise UserPlatformNotFoundError(saved_id)
            ops.delete(SAVED_PRODUCTS, saved_id)

    def list_comparisons(self, user_id: str) -> list[SavedComparison]:
        with self._ops() as ops:
            return ops.list(SAVED_COMPARISONS, SavedComparison, owner_id=user_id)

    def save_comparison(self, item: SavedComparison) -> SavedComparison:
        with self._ops() as ops:
            return ops.upsert(SAVED_COMPARISONS, item.id, item, owner_id=item.user_id)

    def list_history(self, user_id: str) -> list[RecommendationHistory]:
        with self._ops() as ops:
            items = ops.list(RECOMMENDATION_HISTORY, RecommendationHistory, owner_id=user_id)
            return sorted(
                items,
                key=lambda h: h.created_at.isoformat() if h.created_at else h.id,
                reverse=True,
            )

    def add_history(self, item: RecommendationHistory) -> RecommendationHistory:
        with self._ops() as ops:
            return ops.upsert(
                RECOMMENDATION_HISTORY,
                item.id,
                item,
                owner_id=item.user_id,
            )

    def list_searches(self, user_id: str) -> list[SavedSearch]:
        with self._ops() as ops:
            return ops.list(SAVED_SEARCHES, SavedSearch, owner_id=user_id)

    def save_search(self, item: SavedSearch) -> SavedSearch:
        with self._ops() as ops:
            return ops.upsert(SAVED_SEARCHES, item.id, item, owner_id=item.user_id)

    def get_recently_viewed(self, user_id: str) -> RecentlyViewed | None:
        with self._ops() as ops:
            return ops.get(RECENTLY_VIEWED, user_id, RecentlyViewed)

    def save_recently_viewed(self, item: RecentlyViewed) -> RecentlyViewed:
        with self._ops() as ops:
            return ops.upsert(
                RECENTLY_VIEWED,
                item.user_id,
                item,
                owner_id=item.user_id,
            )

    def delete_all_for_user(self, user_id: str) -> None:
        with self._ops() as ops:
            for item in ops.list(SAVED_PRODUCTS, SavedProduct, owner_id=user_id):
                ops.delete(SAVED_PRODUCTS, item.id)
            for item in ops.list(SAVED_COMPARISONS, SavedComparison, owner_id=user_id):
                ops.delete(SAVED_COMPARISONS, item.id)
            for item in ops.list(RECOMMENDATION_HISTORY, RecommendationHistory, owner_id=user_id):
                ops.delete(RECOMMENDATION_HISTORY, item.id)
            for item in ops.list(SAVED_SEARCHES, SavedSearch, owner_id=user_id):
                ops.delete(SAVED_SEARCHES, item.id)
            ops.delete(RECENTLY_VIEWED, user_id)


class SqlAlchemyPasswordResetRepository(PasswordResetRepository, SessionBound):
    def save(self, request: PasswordResetRequest) -> PasswordResetRequest:
        with self._ops() as ops:
            return ops.upsert(
                PASSWORD_RESETS,
                request.reset_id,
                request,
                secondary_key=request.token_hash,
                owner_id=request.user_id,
            )

    def get_by_token_hash(self, token_hash: str) -> PasswordResetRequest | None:
        with self._ops() as ops:
            return ops.get_by_secondary(PASSWORD_RESETS, token_hash, PasswordResetRequest)

    def mark_consumed(self, reset_id: str) -> None:
        with self._ops() as ops:
            request = ops.get(PASSWORD_RESETS, reset_id, PasswordResetRequest)
            if request is None:
                return
            consumed = PasswordResetRequest(
                reset_id=request.reset_id,
                user_id=request.user_id,
                token_hash=request.token_hash,
                created_at=request.created_at,
                expires_at=request.expires_at,
                consumed=True,
            )
            ops.upsert(
                PASSWORD_RESETS,
                consumed.reset_id,
                consumed,
                secondary_key=consumed.token_hash,
                owner_id=consumed.user_id,
            )

    def delete_for_user(self, user_id: str) -> int:
        with self._ops() as ops:
            items = ops.list(PASSWORD_RESETS, PasswordResetRequest, owner_id=user_id)
            for item in items:
                ops.delete(PASSWORD_RESETS, item.reset_id)
            return len(items)


class SqlAlchemyEmailVerificationRepository(EmailVerificationRepository, SessionBound):
    def save(self, request: EmailVerificationRequest) -> EmailVerificationRequest:
        with self._ops() as ops:
            return ops.upsert(
                EMAIL_VERIFICATIONS,
                request.verification_id,
                request,
                secondary_key=request.token_hash,
                owner_id=request.user_id,
            )

    def get_by_token_hash(self, token_hash: str) -> EmailVerificationRequest | None:
        with self._ops() as ops:
            return ops.get_by_secondary(
                EMAIL_VERIFICATIONS, token_hash, EmailVerificationRequest
            )

    def mark_consumed(self, verification_id: str) -> None:
        with self._ops() as ops:
            request = ops.get(EMAIL_VERIFICATIONS, verification_id, EmailVerificationRequest)
            if request is None:
                return
            consumed = EmailVerificationRequest(
                verification_id=request.verification_id,
                user_id=request.user_id,
                token_hash=request.token_hash,
                created_at=request.created_at,
                expires_at=request.expires_at,
                consumed=True,
            )
            ops.upsert(
                EMAIL_VERIFICATIONS,
                consumed.verification_id,
                consumed,
                secondary_key=consumed.token_hash,
                owner_id=consumed.user_id,
            )

    def delete_for_user(self, user_id: str) -> int:
        with self._ops() as ops:
            items = ops.list(EMAIL_VERIFICATIONS, EmailVerificationRequest, owner_id=user_id)
            for item in items:
                ops.delete(EMAIL_VERIFICATIONS, item.verification_id)
            return len(items)


class SqlAlchemyAuditLogRepository(AuditLogRepository, SessionBound):
    def append(self, event: SecurityEvent) -> SecurityEvent:
        with self._ops() as ops:
            entity_id = event.event_id or f"audit-{event.created_at.isoformat()}"
            return ops.upsert(
                AUDIT_EVENTS,
                entity_id,
                event,
                owner_id=event.user_id,
            )

    def list_events(self, *, user_id: str | None = None, limit: int = 100) -> list[SecurityEvent]:
        with self._ops() as ops:
            if user_id is not None:
                items = ops.list(AUDIT_EVENTS, SecurityEvent, owner_id=user_id)
            else:
                items = ops.list(AUDIT_EVENTS, SecurityEvent)
            return items[-max(0, limit) :]


class SqlAlchemyConsentRepository(ConsentRepository, SessionBound):
    def get(
        self, user_id: str, policy_type: str, version_id: str
    ) -> PolicyAcceptanceRecord | None:
        with self._ops() as ops:
            return ops.get_by_secondary(
                CONSENT_RECORDS,
                consent_identity_key(user_id, policy_type, version_id),
                PolicyAcceptanceRecord,
            )

    def save(self, record: PolicyAcceptanceRecord) -> PolicyAcceptanceRecord:
        existing = self.get(record.user_id, record.policy_type, record.version_id)
        if existing is not None:
            return existing
        try:
            with self._ops() as ops:
                return ops.upsert(
                    CONSENT_RECORDS,
                    record.record_id,
                    record,
                    owner_id=record.user_id,
                    secondary_key=record.identity_key,
                )
        except PersistenceConflictError:
            existing = self.get(record.user_id, record.policy_type, record.version_id)
            if existing is not None:
                return existing
            raise

    def list_for_user(self, user_id: str) -> list[PolicyAcceptanceRecord]:
        with self._ops() as ops:
            items = ops.list(CONSENT_RECORDS, PolicyAcceptanceRecord, owner_id=user_id)
            return sorted(items, key=lambda item: item.accepted_at.isoformat())

    def delete_for_user(self, user_id: str) -> int:
        with self._ops() as ops:
            items = ops.list(CONSENT_RECORDS, PolicyAcceptanceRecord, owner_id=user_id)
            for item in items:
                ops.delete(CONSENT_RECORDS, item.record_id)
            return len(items)


class SqlAlchemyUserPlatformStore:
    """Composite SQLAlchemy unit of work mirroring InMemoryUserPlatformStore."""

    def __init__(
        self,
        session_factory=None,
        session=None,
    ) -> None:
        kwargs = {"session_factory": session_factory, "session": session}
        self.users = SqlAlchemyUserRepository(**kwargs)
        self.sessions = SqlAlchemySessionRepository(**kwargs)
        self.profiles = SqlAlchemyProfileRepository(**kwargs)
        self.saved = SqlAlchemySavedItemsRepository(**kwargs)
        self.password_resets = SqlAlchemyPasswordResetRepository(**kwargs)
        self.email_verifications = SqlAlchemyEmailVerificationRepository(**kwargs)
        self.audit = SqlAlchemyAuditLogRepository(**kwargs)
        self.consents = SqlAlchemyConsentRepository(**kwargs)
