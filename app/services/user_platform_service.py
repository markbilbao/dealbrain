"""User Platform application facade.

Composes auth, profile, session, and saved-items services behind one entry
point for API / Shopping Assistant integration.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.auth.security import AuditLogger
from app.auth.service import AuthService
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
    UserSettings,
)
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformNotFoundError,
    UserPlatformValidationError,
)
from app.domain.interfaces.user_platform_repository import SavedItemsRepository
from app.profile.service import ProfileService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, LIMITATIONS, list_demo_users


class UserPlatformService:
    """Multi-user platform facade — authentication through saved items."""

    def __init__(
        self,
        *,
        auth: AuthService,
        profiles: ProfileService,
        sessions: SessionService,
        saved: SavedItemsRepository,
        audit: AuditLogger | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        enabled: bool = True,
    ) -> None:
        self._auth = auth
        self._profiles = profiles
        self._sessions = sessions
        self._saved = saved
        self._audit = audit or AuditLogger()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._enabled = enabled

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise UserPlatformValidationError("User platform is disabled.")

    # --- Auth ---

    def register(self, **kwargs: Any) -> AuthResult:
        self._require_enabled()
        return self._auth.register(**kwargs)

    def login(self, **kwargs: Any) -> AuthResult:
        self._require_enabled()
        return self._auth.login(**kwargs)

    def logout(self, access_token: str | None) -> None:
        self._require_enabled()
        self._auth.logout(access_token)

    def me(self, access_token: str | None) -> User:
        self._require_enabled()
        return self._auth.current_user(access_token)

    def request_password_reset(self, email: str) -> dict[str, Any]:
        self._require_enabled()
        return self._auth.request_password_reset(email)

    def confirm_password_reset(self, token: str, new_password: str) -> dict[str, Any]:
        self._require_enabled()
        return self._auth.confirm_password_reset(token, new_password)

    def request_email_verification(self, email: str) -> dict[str, Any]:
        self._require_enabled()
        return self._auth.request_email_verification_by_email(email)

    def confirm_email_verification(self, token: str) -> dict[str, Any]:
        self._require_enabled()
        return self._auth.confirm_email_verification(token)

    def require_user(self, access_token: str | None) -> User:
        return self.me(access_token)

    def resolve_user_id(self, access_token: str | None) -> str | None:
        """Return user_id when authenticated, else None (anonymous fallback)."""
        if not access_token or not self._enabled:
            return None
        try:
            return self._auth.current_user(access_token).user_id
        except (UserPlatformAuthError, UserPlatformValidationError):
            return None

    # --- Profile ---

    def get_profile(self, access_token: str | None) -> UserProfile:
        user = self.require_user(access_token)
        return self._profiles.get_profile(user.user_id)

    def update_profile(self, access_token: str | None, updates: dict[str, Any]) -> UserProfile:
        user = self.require_user(access_token)
        return self._profiles.update_profile(user.user_id, updates)

    def get_preferences(self, access_token: str | None) -> UserPreference:
        user = self.require_user(access_token)
        return self._profiles.get_preferences(user.user_id)

    def update_preferences(
        self, access_token: str | None, updates: dict[str, Any]
    ) -> UserPreference:
        user = self.require_user(access_token)
        return self._profiles.update_preferences(user.user_id, updates)

    def get_settings(self, access_token: str | None) -> UserSettings:
        user = self.require_user(access_token)
        return self._profiles.get_settings(user.user_id)

    def update_settings(self, access_token: str | None, updates: dict[str, Any]) -> UserSettings:
        user = self.require_user(access_token)
        return self._profiles.update_settings(user.user_id, updates)

    # --- Saved items ---

    def list_saved_products(self, access_token: str | None) -> list[SavedProduct]:
        user = self.require_user(access_token)
        return self._saved.list_saved_products(user.user_id)

    def save_product(self, access_token: str | None, payload: dict[str, Any]) -> SavedProduct:
        user = self.require_user(access_token)
        product_id = str(payload.get("product_id") or "").strip()
        product_name = str(payload.get("product_name") or "").strip()
        if not product_id or not product_name:
            raise UserPlatformValidationError("product_id and product_name are required.")
        item = SavedProduct(
            id=self._id_factory(),
            user_id=user.user_id,
            product_id=product_id,
            product_name=product_name,
            marketplace=(
                str(payload["marketplace"]).strip() if payload.get("marketplace") else None
            ),
            price=float(payload["price"]) if payload.get("price") is not None else None,
            currency=str(payload.get("currency") or "PHP"),
            notes=str(payload.get("notes") or ""),
            favorite=bool(payload.get("favorite", False)),
            created_at=self._clock(),
        )
        return self._saved.save_product(item)

    def delete_saved_product(self, access_token: str | None, saved_id: str) -> None:
        user = self.require_user(access_token)
        self._saved.delete_saved_product(user.user_id, saved_id)

    def list_history(self, access_token: str | None) -> list[RecommendationHistory]:
        user = self.require_user(access_token)
        return self._saved.list_history(user.user_id)

    def add_history(
        self,
        user_id: str,
        *,
        query: str,
        recommendation_summary: str = "",
        product_ids: tuple[str, ...] = (),
        profile_id: str | None = None,
    ) -> RecommendationHistory:
        item = RecommendationHistory(
            id=self._id_factory(),
            user_id=user_id,
            query=query,
            recommendation_summary=recommendation_summary,
            product_ids=product_ids,
            profile_id=profile_id,
            created_at=self._clock(),
        )
        return self._saved.add_history(item)

    def list_comparisons(self, access_token: str | None) -> list[SavedComparison]:
        user = self.require_user(access_token)
        return self._saved.list_comparisons(user.user_id)

    def save_comparison(self, access_token: str | None, payload: dict[str, Any]) -> SavedComparison:
        user = self.require_user(access_token)
        product_ids = tuple(
            str(p).strip() for p in (payload.get("product_ids") or []) if str(p).strip()
        )
        if len(product_ids) < 2:
            raise UserPlatformValidationError("product_ids must include at least two products.")
        item = SavedComparison(
            id=self._id_factory(),
            user_id=user.user_id,
            product_ids=product_ids,
            title=str(payload.get("title") or ""),
            notes=str(payload.get("notes") or ""),
            created_at=self._clock(),
        )
        return self._saved.save_comparison(item)

    def list_searches(self, access_token: str | None) -> list[SavedSearch]:
        user = self.require_user(access_token)
        return self._saved.list_searches(user.user_id)

    def save_search(self, access_token: str | None, payload: dict[str, Any]) -> SavedSearch:
        user = self.require_user(access_token)
        query = str(payload.get("query") or "").strip()
        if not query:
            raise UserPlatformValidationError("query must not be blank.")
        item = SavedSearch(
            id=self._id_factory(),
            user_id=user.user_id,
            query=query,
            filters=dict(payload.get("filters") or {}),
            created_at=self._clock(),
        )
        return self._saved.save_search(item)

    def get_recently_viewed(self, access_token: str | None) -> RecentlyViewed:
        user = self.require_user(access_token)
        recent = self._saved.get_recently_viewed(user.user_id)
        if recent is None:
            return RecentlyViewed(user_id=user.user_id, product_ids=(), updated_at=self._clock())
        return recent

    def mark_viewed(self, access_token: str | None, product_id: str) -> RecentlyViewed:
        user = self.require_user(access_token)
        cleaned = product_id.strip()
        if not cleaned:
            raise UserPlatformValidationError("product_id must not be blank.")
        current = self.get_recently_viewed(access_token)
        ids = [cleaned, *[p for p in current.product_ids if p != cleaned]][:20]
        return self._saved.save_recently_viewed(
            RecentlyViewed(user_id=user.user_id, product_ids=tuple(ids), updated_at=self._clock())
        )

    # --- Shopping Assistant integration ---

    def shopping_assistant_context(self, user_id: str | None) -> dict[str, Any]:
        """Return personalization context for authenticated users; empty for anonymous."""
        if not user_id or not self._enabled:
            return {"authenticated": False, "personalization_mode": "anonymous"}
        try:
            profile = self._profiles.get_profile(user_id)
            overrides = self._profiles.shopping_assistant_overrides(user_id)
            settings = self._profiles.get_settings(user_id)
        except (UserPlatformNotFoundError, UserPlatformValidationError):
            return {"authenticated": False, "personalization_mode": "anonymous"}
        return {
            "authenticated": True,
            "personalization_mode": "authenticated",
            "user_id": user_id,
            "display_name": profile.display_name,
            "overrides": overrides,
            "personal_profile_id": profile.preferences.personal_profile_id,
            "ai_mode_preference": settings.ai_mode_preference,
            "uses_personal_ai": bool(profile.preferences.personal_profile_id),
            "uses_user_profile": True,
        }

    def record_shopping_recommendation(
        self,
        user_id: str | None,
        *,
        query: str,
        summary: str,
        product_ids: tuple[str, ...] = (),
        profile_id: str | None = None,
    ) -> None:
        if not user_id:
            return
        try:
            self.add_history(
                user_id,
                query=query,
                recommendation_summary=summary,
                product_ids=product_ids,
                profile_id=profile_id,
            )
        except Exception:  # noqa: BLE001
            return

    def demo(self) -> dict[str, Any]:
        users = list_demo_users()
        return {
            "demo_users": [
                {
                    "email": u.email,
                    "display_name": u.display_name,
                    "user_id": u.user_id,
                    "password_hint": DEMO_PASSWORD,
                }
                for u in users
            ],
            "limitations": list(LIMITATIONS),
            "authentication": True,
            "email_delivery": False,
            "mfa": False,
            "oauth": False,
            "persistence": "memory",
        }

    def meta(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "authentication": True,
            "email_delivery": False,
            "mfa": False,
            "oauth": False,
            "persistence": "memory",
            "demo_user_count": len(list_demo_users()),
            "limitations": list(LIMITATIONS),
            "endpoints": [
                "POST /api/v1/auth/register",
                "POST /api/v1/auth/login",
                "POST /api/v1/auth/logout",
                "GET /api/v1/auth/me",
                "POST /api/v1/auth/password-reset",
                "POST /api/v1/auth/password-reset/confirm",
                "POST /api/v1/auth/verify-email",
                "POST /api/v1/auth/verify-email/confirm",
                "GET /api/v1/profile",
                "PUT /api/v1/profile",
                "GET /api/v1/profile/preferences",
                "PUT /api/v1/profile/preferences",
                "GET /api/v1/user/saved-products",
                "POST /api/v1/user/saved-products",
                "DELETE /api/v1/user/saved-products/{id}",
                "GET /api/v1/user/history",
                "GET /api/v1/user/comparisons",
                "GET /api/v1/user/searches",
            ],
        }
