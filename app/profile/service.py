"""Profile and preference management for authenticated users."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.user_platform import (
    FavoriteBrand,
    FavoriteMarketplace,
    NotificationPreference,
    ProfileVersion,
    UserPreference,
    UserProfile,
    UserSettings,
    Wishlist,
)
from app.domain.exceptions import UserPlatformNotFoundError, UserPlatformValidationError
from app.domain.interfaces.user_platform_repository import ProfileRepository, UserRepository


class ProfileService:
    """Read / update UserProfile, preferences, and settings."""

    def __init__(
        self,
        *,
        users: UserRepository,
        profiles: ProfileRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_profile(self, user_id: str) -> UserProfile:
        self._require_user(user_id)
        profile = self._profiles.get_profile(user_id)
        if profile is None:
            raise UserPlatformNotFoundError(user_id)
        return profile

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> UserProfile:
        profile = self.get_profile(user_id)
        prefs = profile.preferences
        pref_updates = dict(updates.get("preferences") or {})
        # Allow flat top-level preference fields as well.
        for key in (
            "budget",
            "currency",
            "country",
            "shopping_goals",
            "categories",
            "battery_priority",
            "camera_priority",
            "performance_priority",
            "travel_frequency",
            "creator_mode",
            "gaming_mode",
            "student_mode",
            "business_mode",
            "preferred_screen_size",
            "preferred_colors",
            "personal_profile_id",
        ):
            if key in updates and key not in pref_updates:
                pref_updates[key] = updates[key]

        new_prefs = self._merge_preferences(prefs, pref_updates)
        brands = profile.favorite_brands
        if "favorite_brands" in updates:
            brands = tuple(
                FavoriteBrand(user_id=user_id, brand=str(b).strip(), created_at=self._clock())
                for b in updates["favorite_brands"]
                if str(b).strip()
            )
            self._profiles.set_favorite_brands(user_id, list(brands))

        markets = profile.favorite_marketplaces
        if "favorite_marketplaces" in updates:
            markets = tuple(
                FavoriteMarketplace(
                    user_id=user_id,
                    marketplace=str(m).strip(),
                    created_at=self._clock(),
                )
                for m in updates["favorite_marketplaces"]
                if str(m).strip()
            )
            self._profiles.set_favorite_marketplaces(user_id, list(markets))

        wishlist = profile.wishlist
        if "wishlist" in updates:
            product_ids = tuple(str(p).strip() for p in updates["wishlist"] if str(p).strip())
            wishlist = Wishlist(user_id=user_id, product_ids=product_ids, updated_at=self._clock())
            self._profiles.save_wishlist(wishlist)

        owned = profile.owned_products
        if "owned_products" in updates:
            owned = tuple(str(p).strip() for p in updates["owned_products"] if str(p).strip())

        accessories = profile.accessories
        if "accessories" in updates:
            accessories = tuple(str(p).strip() for p in updates["accessories"] if str(p).strip())

        display_name = profile.display_name
        if "display_name" in updates and str(updates["display_name"]).strip():
            display_name = str(updates["display_name"]).strip()

        now = self._clock()
        current_version = profile.version.version if profile.version else 1
        version = ProfileVersion(
            user_id=user_id,
            version=current_version + 1,
            changed_at=now,
            change_summary="profile_updated",
        )
        self._profiles.save_preferences(new_prefs)
        updated = UserProfile(
            user_id=user_id,
            display_name=display_name,
            preferences=new_prefs,
            favorite_brands=brands,
            favorite_marketplaces=markets,
            wishlist=wishlist,
            owned_products=owned,
            accessories=accessories,
            version=version,
            data_status=profile.data_status,
        )
        return self._profiles.save_profile(updated)

    def get_preferences(self, user_id: str) -> UserPreference:
        self._require_user(user_id)
        prefs = self._profiles.get_preferences(user_id)
        if prefs is None:
            raise UserPlatformNotFoundError(user_id)
        return prefs

    def update_preferences(self, user_id: str, updates: dict[str, Any]) -> UserPreference:
        prefs = self.get_preferences(user_id)
        merged = self._merge_preferences(prefs, updates)
        saved = self._profiles.save_preferences(merged)
        # Keep composed profile in sync.
        profile = self._profiles.get_profile(user_id)
        if profile is not None:
            now = self._clock()
            version = ProfileVersion(
                user_id=user_id,
                version=(profile.version.version + 1) if profile.version else 2,
                changed_at=now,
                change_summary="preferences_updated",
            )
            self._profiles.save_profile(
                UserProfile(
                    user_id=profile.user_id,
                    display_name=profile.display_name,
                    preferences=saved,
                    favorite_brands=profile.favorite_brands,
                    favorite_marketplaces=profile.favorite_marketplaces,
                    wishlist=profile.wishlist,
                    owned_products=profile.owned_products,
                    accessories=profile.accessories,
                    version=version,
                    data_status=profile.data_status,
                )
            )
        return saved

    def get_settings(self, user_id: str) -> UserSettings:
        self._require_user(user_id)
        settings = self._profiles.get_settings(user_id)
        if settings is None:
            raise UserPlatformNotFoundError(user_id)
        return settings

    def update_settings(self, user_id: str, updates: dict[str, Any]) -> UserSettings:
        settings = self.get_settings(user_id)
        notif = settings.notification_settings or NotificationPreference(user_id=user_id)
        if "notification_settings" in updates and isinstance(
            updates["notification_settings"], dict
        ):
            ns = updates["notification_settings"]
            notif = NotificationPreference(
                user_id=user_id,
                email_enabled=bool(ns.get("email_enabled", notif.email_enabled)),
                push_enabled=bool(ns.get("push_enabled", notif.push_enabled)),
                deal_alerts=bool(ns.get("deal_alerts", notif.deal_alerts)),
                price_drop_alerts=bool(ns.get("price_drop_alerts", notif.price_drop_alerts)),
                newsletter=bool(ns.get("newsletter", notif.newsletter)),
            )
        theme = updates.get("theme", settings.theme)
        if theme not in {"system", "light", "dark"}:
            raise UserPlatformValidationError("theme must be system|light|dark.")
        ai_mode = updates.get("ai_mode_preference", settings.ai_mode_preference)
        if ai_mode not in {"economy", "balanced", "maximum", "ask"}:
            raise UserPlatformValidationError(
                "ai_mode_preference must be economy|balanced|maximum|ask."
            )
        updated = UserSettings(
            user_id=user_id,
            theme=theme,  # type: ignore[arg-type]
            language=str(updates.get("language", settings.language)),
            notification_settings=notif,
            ai_mode_preference=ai_mode,  # type: ignore[arg-type]
            privacy_settings=dict(updates.get("privacy_settings", settings.privacy_settings)),
            community_settings=dict(updates.get("community_settings", settings.community_settings)),
            updated_at=self._clock(),
        )
        return self._profiles.save_settings(updated)

    def shopping_assistant_overrides(self, user_id: str) -> dict[str, Any]:
        """Map UserProfile into Shopping Assistant query overrides."""
        try:
            profile = self.get_profile(user_id)
        except UserPlatformNotFoundError:
            return {}
        prefs = profile.preferences
        use_cases: list[str] = list(prefs.shopping_goals)
        if prefs.gaming_mode:
            use_cases.append("gaming")
        if prefs.student_mode:
            use_cases.append("student")
        if prefs.creator_mode:
            use_cases.append("content_creation")
        if prefs.business_mode:
            use_cases.append("productivity")
        if prefs.travel_frequency in {"frequent", "weekly", "monthly"}:
            use_cases.append("travel")
        overrides: dict[str, Any] = {
            "currency": prefs.currency,
            "use_cases": tuple(dict.fromkeys(use_cases)),
        }
        if prefs.budget is not None:
            overrides["budget_max"] = prefs.budget
        if prefs.categories:
            overrides["category"] = prefs.categories[0]
        if prefs.personal_profile_id:
            overrides["profile_id"] = prefs.personal_profile_id
        return overrides

    def _require_user(self, user_id: str) -> None:
        if not user_id or not user_id.strip():
            raise UserPlatformValidationError("user_id must not be blank.")
        if self._users.get_by_id(user_id) is None:
            raise UserPlatformNotFoundError(user_id)

    def _merge_preferences(self, base: UserPreference, updates: dict[str, Any]) -> UserPreference:
        def _tuple(key: str, current: tuple[str, ...]) -> tuple[str, ...]:
            if key not in updates:
                return current
            value = updates[key]
            if value is None:
                return ()
            return tuple(str(v).strip() for v in value if str(v).strip())

        def _prio(key: str, current: float) -> float:
            if key not in updates or updates[key] is None:
                return current
            value = float(updates[key])
            if value < 0 or value > 1:
                raise UserPlatformValidationError(f"{key} must be between 0 and 1.")
            return value

        budget = base.budget
        if "budget" in updates:
            budget = None if updates["budget"] is None else float(updates["budget"])
            if budget is not None and budget < 0:
                raise UserPlatformValidationError("budget must be >= 0.")

        return UserPreference(
            user_id=base.user_id,
            budget=budget,
            currency=str(updates.get("currency", base.currency) or base.currency),
            country=str(updates.get("country", base.country) or base.country),
            shopping_goals=_tuple("shopping_goals", base.shopping_goals),
            categories=_tuple("categories", base.categories),
            battery_priority=_prio("battery_priority", base.battery_priority),
            camera_priority=_prio("camera_priority", base.camera_priority),
            performance_priority=_prio("performance_priority", base.performance_priority),
            travel_frequency=str(
                updates.get("travel_frequency", base.travel_frequency) or base.travel_frequency
            ),
            creator_mode=bool(updates.get("creator_mode", base.creator_mode)),
            gaming_mode=bool(updates.get("gaming_mode", base.gaming_mode)),
            student_mode=bool(updates.get("student_mode", base.student_mode)),
            business_mode=bool(updates.get("business_mode", base.business_mode)),
            preferred_screen_size=_tuple("preferred_screen_size", base.preferred_screen_size),
            preferred_colors=_tuple("preferred_colors", base.preferred_colors),
            personal_profile_id=(
                str(updates["personal_profile_id"]).strip()
                if updates.get("personal_profile_id")
                else (None if "personal_profile_id" in updates else base.personal_profile_id)
            ),
            updated_at=self._clock(),
        )
