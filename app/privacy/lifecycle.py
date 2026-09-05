"""Account deletion and personal-data export for the consumer User Platform.

Engineering foundation only. Does not certify legal completeness, statutory
deadlines, backup erasure, or retention exceptions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.auth.security import AuditLogger
from app.domain.entities.user_platform import User
from app.domain.exceptions import UserPlatformAuthError, UserPlatformValidationError
from app.domain.interfaces.notification_center_repository import NotificationCenterRepository
from app.domain.interfaces.user_platform_repository import (
    ConsentRepository,
    EmailChangeRepository,
    EmailVerificationRepository,
    PasswordResetRepository,
    ProfileRepository,
    SavedItemsRepository,
    SessionRepository,
    UserRepository,
)
from app.domain.interfaces.watchlist_repository import WatchlistRepository
from app.privacy.inventory import (
    EXPORT_KIND,
    EXPORT_SCHEMA,
    PERSONAL_DATA_EXPORT_CATEGORIES,
    strip_security_fields,
)

ACCOUNT_DELETE_CONFIRMATION = "DELETE"

RETAINED_LIMITATIONS: tuple[str, ...] = (
    "user_platform.audit_events retained as security/audit evidence; not physically erased",
    "application/request logs are not purged by this endpoint",
    "database backups are not claimed erased",
    "third-party copies (e.g. transactional email provider) are not claimed erased",
    "Early Access waitlist records are not a User account and are not deleted here",
    "guest browser cookies/sessionStorage are client-side and not revoked by this API",
    "shopping-assistant conversations are TTL-bound and not listed by user_id on this path",
    "alert-rule rows in the alerts bounded context are not cascaded by this endpoint",
    "statutory retention exceptions and response deadlines remain counsel-owned",
)


@dataclass(frozen=True, slots=True)
class DeletionResult:
    status: str
    user_id: str
    sessions_revoked: int
    sessions_deleted: int
    watchlists_deleted: int
    notification_preferences_removed: bool
    consent_records_deleted: int
    retained_limitations: tuple[str, ...] = field(default_factory=lambda: RETAINED_LIMITATIONS)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "user_id": self.user_id,
            "sessions_revoked": self.sessions_revoked,
            "sessions_deleted": self.sessions_deleted,
            "watchlists_deleted": self.watchlists_deleted,
            "notification_preferences_removed": self.notification_preferences_removed,
            "consent_records_deleted": self.consent_records_deleted,
            "retained_limitations": list(self.retained_limitations),
        }


class AccountLifecycleService:
    """Delete or export data attributable to one consumer account."""

    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        profiles: ProfileRepository,
        saved: SavedItemsRepository,
        password_resets: PasswordResetRepository | None = None,
        email_verifications: EmailVerificationRepository | None = None,
        email_changes: EmailChangeRepository | None = None,
        consents: ConsentRepository | None = None,
        audit: AuditLogger | None = None,
        watchlists: WatchlistRepository | None = None,
        notification_center: NotificationCenterRepository | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._profiles = profiles
        self._saved = saved
        self._password_resets = password_resets
        self._email_verifications = email_verifications
        self._email_changes = email_changes
        self._consents = consents
        self._audit = audit or AuditLogger()
        self._watchlists = watchlists
        self._notification_center = notification_center
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def delete_account(self, user: User, *, confirmation: str) -> DeletionResult:
        if confirmation != ACCOUNT_DELETE_CONFIRMATION:
            raise UserPlatformValidationError(
                f"Account deletion requires confirmation={ACCOUNT_DELETE_CONFIRMATION!r}."
            )
        existing = self._users.get_by_id(user.user_id)
        if existing is None:
            raise UserPlatformAuthError("Account is not available.")

        sessions_revoked = self._sessions.revoke_all_for_user(user.user_id)
        sessions_deleted = self._sessions.delete_all_for_user(user.user_id)
        self._profiles.delete_for_user(user.user_id)
        self._saved.delete_all_for_user(user.user_id)
        if self._password_resets is not None:
            self._password_resets.delete_for_user(user.user_id)
        if self._email_verifications is not None:
            self._email_verifications.delete_for_user(user.user_id)
        if self._email_changes is not None:
            self._email_changes.delete_for_user(user.user_id)
        consent_deleted = 0
        if self._consents is not None:
            consent_deleted = self._consents.delete_for_user(user.user_id)

        watchlists_deleted = 0
        if self._watchlists is not None:
            owned = self._watchlists.list_watchlists(owner_id=user.user_id)
            for watchlist in owned:
                if self._watchlists.delete_watchlist(watchlist.watchlist_id):
                    watchlists_deleted += 1

        notification_removed = False
        if self._notification_center is not None:
            notification_removed = bool(self._notification_center.delete_preferences(user.user_id))

        self._users.delete(user.user_id)
        self._audit.record(
            "account_deleted",
            user_id=user.user_id,
            detail="consumer_account_deleted",
            metadata={"sessions_revoked": sessions_revoked},
        )
        return DeletionResult(
            status="deleted",
            user_id=user.user_id,
            sessions_revoked=sessions_revoked,
            sessions_deleted=sessions_deleted,
            watchlists_deleted=watchlists_deleted,
            notification_preferences_removed=notification_removed,
            consent_records_deleted=consent_deleted,
        )

    def export_personal_data(self, user: User) -> dict[str, Any]:
        profile = self._profiles.get_profile(user.user_id)
        settings = self._profiles.get_settings(user.user_id)
        wishlist = None
        if profile is not None and profile.wishlist is not None:
            wishlist = profile.wishlist.to_dict()
        elif profile is not None:
            wishlist = {"user_id": user.user_id, "product_ids": []}

        notification_preferences = None
        if settings is not None and settings.notification_settings is not None:
            notification_preferences = settings.notification_settings.to_dict()
        if self._notification_center is not None:
            center = self._notification_center.get_preferences(user.user_id)
            if center is not None:
                notification_preferences = {
                    **(notification_preferences or {}),
                    "notification_center": center.to_dict(),
                }

        consents: list[dict[str, Any]] = []
        if self._consents is not None:
            consents = [record.to_dict() for record in self._consents.list_for_user(user.user_id)]

        sessions = [session.to_dict() for session in self._sessions.list_for_user(user.user_id)]
        payload = {
            "export_schema": EXPORT_SCHEMA,
            "export_kind": EXPORT_KIND,
            "exported_at": self._clock().isoformat(),
            "account": user.to_dict(),
            "profile": profile.to_dict() if profile is not None else None,
            "settings": settings.to_dict() if settings is not None else None,
            "wishlist": wishlist,
            "saved_products": [
                item.to_dict() for item in self._saved.list_saved_products(user.user_id)
            ],
            "saved_comparisons": [
                item.to_dict() for item in self._saved.list_comparisons(user.user_id)
            ],
            "recommendation_history": [
                item.to_dict() for item in self._saved.list_history(user.user_id)
            ],
            "saved_searches": [item.to_dict() for item in self._saved.list_searches(user.user_id)],
            "recently_viewed": (
                self._saved.get_recently_viewed(user.user_id).to_dict()
                if self._saved.get_recently_viewed(user.user_id) is not None
                else {"user_id": user.user_id, "product_ids": []}
            ),
            "consent_records": consents,
            "sessions": sessions,
            "notification_preferences": notification_preferences,
        }
        missing = [key for key in PERSONAL_DATA_EXPORT_CATEGORIES if key not in payload]
        if missing:
            raise RuntimeError(f"export missing inventory categories: {missing}")
        return strip_security_fields(payload)
