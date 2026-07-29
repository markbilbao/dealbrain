"""Demo users for User Platform v1.

Hashed passwords only. Email delivery is not implemented.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.auth.password import hash_password
from app.domain.entities.user_platform import (
    FavoriteBrand,
    FavoriteMarketplace,
    NotificationPreference,
    ProfileVersion,
    RecentlyViewed,
    RecommendationHistory,
    SavedComparison,
    SavedProduct,
    SavedSearch,
    User,
    UserPreference,
    UserProfile,
    UserSettings,
    Wishlist,
)

DEMO_PASSWORD = "DemoPass123!"
DEMO_PASSWORD_HASH = hash_password(DEMO_PASSWORD)

LIMITATIONS: tuple[str, ...] = (
    "Demo users only — not production accounts.",
    "No email sending for verification or password reset.",
    "No MFA and no OAuth / external identity providers.",
    "In-memory persistence only — data resets on process restart.",
    "No production database adapter wired in Sprint 17.",
    "No payment integration.",
)


def _dt() -> datetime:
    return datetime(2026, 7, 1, 12, 0, tzinfo=UTC)


def _user(*, user_id: str, email: str, display_name: str) -> User:
    return User(
        user_id=user_id,
        email=email,
        password_hash=DEMO_PASSWORD_HASH,
        display_name=display_name,
        is_active=True,
        email_verified=True,
        created_at=_dt(),
        updated_at=_dt(),
        data_status="mock",
    )


DEMO_USERS: tuple[dict[str, Any], ...] = (
    {
        "user": _user(
            user_id="user-student",
            email="student@example.com",
            display_name="Demo Student",
        ),
        "preferences": UserPreference(
            user_id="user-student",
            budget=35000.0,
            currency="PHP",
            country="PH",
            shopping_goals=("study", "battery_life"),
            categories=("laptop", "phone"),
            battery_priority=0.85,
            camera_priority=0.35,
            performance_priority=0.45,
            travel_frequency="rare",
            student_mode=True,
            preferred_screen_size=("14", "15"),
            preferred_colors=("black", "gray"),
            personal_profile_id="profile-budget-student",
            updated_at=_dt(),
        ),
        "brands": ("Lenovo", "Acer", "Google"),
        "marketplaces": ("Shopee", "Lazada"),
        "wishlist": ("sa-phone-pixel-9",),
        "owned": (),
        "accessories": (),
        "saved_products": (
            SavedProduct(
                id="saved-student-1",
                user_id="user-student",
                product_id="sa-laptop-loq-15",
                product_name="Lenovo LOQ 15",
                marketplace="Shopee",
                price=48990.0,
                favorite=True,
                created_at=_dt(),
            ),
        ),
        "comparisons": (
            SavedComparison(
                id="cmp-student-1",
                user_id="user-student",
                product_ids=("sa-laptop-loq-15", "sa-laptop-nitro-v15"),
                title="Budget study laptops",
                created_at=_dt(),
            ),
        ),
        "history": (
            RecommendationHistory(
                id="hist-student-1",
                user_id="user-student",
                query="Best laptop under 35000 for students",
                recommendation_summary="LOQ 15 recommended when budget stretches; else Nitro V15.",
                product_ids=("sa-laptop-loq-15",),
                profile_id="profile-budget-student",
                created_at=_dt(),
            ),
        ),
        "searches": (
            SavedSearch(
                id="search-student-1",
                user_id="user-student",
                query="student laptop under 35000",
                filters={"budget_max": 35000, "category": "laptop"},
                created_at=_dt(),
            ),
        ),
        "recent": ("sa-laptop-loq-15", "sa-phone-pixel-9"),
    },
    {
        "user": _user(
            user_id="user-creator",
            email="creator@example.com",
            display_name="Demo Creator",
        ),
        "preferences": UserPreference(
            user_id="user-creator",
            budget=75000.0,
            currency="PHP",
            country="PH",
            shopping_goals=("content_creation", "camera"),
            categories=("phone", "laptop"),
            battery_priority=0.7,
            camera_priority=0.95,
            performance_priority=0.7,
            travel_frequency="monthly",
            creator_mode=True,
            preferred_screen_size=("6.1", "6.7"),
            preferred_colors=("black", "titanium"),
            personal_profile_id="profile-content-creator",
            updated_at=_dt(),
        ),
        "brands": ("Apple", "Google", "Samsung"),
        "marketplaces": ("Shopee", "Lazada"),
        "wishlist": ("sa-phone-iphone-16-pro", "sa-phone-pixel-9"),
        "owned": ("sa-earbuds-airpods-pro-2",),
        "accessories": ("sa-earbuds-airpods-pro-2",),
        "saved_products": (
            SavedProduct(
                id="saved-creator-1",
                user_id="user-creator",
                product_id="sa-phone-iphone-16-pro",
                product_name="iPhone 16 Pro",
                marketplace="Lazada",
                price=72990.0,
                favorite=True,
                created_at=_dt(),
            ),
        ),
        "comparisons": (
            SavedComparison(
                id="cmp-creator-1",
                user_id="user-creator",
                product_ids=("sa-phone-iphone-16-pro", "sa-phone-pixel-9"),
                title="Creator phone shortlist",
                created_at=_dt(),
            ),
        ),
        "history": (
            RecommendationHistory(
                id="hist-creator-1",
                user_id="user-creator",
                query="Best phone for content creation",
                recommendation_summary="iPhone 16 Pro for video; Pixel 9 for stills.",
                product_ids=("sa-phone-iphone-16-pro", "sa-phone-pixel-9"),
                profile_id="profile-content-creator",
                created_at=_dt(),
            ),
        ),
        "searches": (
            SavedSearch(
                id="search-creator-1",
                user_id="user-creator",
                query="creator phone camera",
                filters={"category": "phone"},
                created_at=_dt(),
            ),
        ),
        "recent": ("sa-phone-iphone-16-pro", "sa-phone-pixel-9"),
    },
    {
        "user": _user(
            user_id="user-traveler",
            email="traveler@example.com",
            display_name="Demo Traveler",
        ),
        "preferences": UserPreference(
            user_id="user-traveler",
            budget=55000.0,
            currency="PHP",
            country="PH",
            shopping_goals=("travel", "battery_life"),
            categories=("laptop", "phone"),
            battery_priority=0.9,
            camera_priority=0.55,
            performance_priority=0.55,
            travel_frequency="frequent",
            business_mode=True,
            preferred_screen_size=("13", "14"),
            preferred_colors=("silver", "gray"),
            personal_profile_id="profile-business-traveler",
            updated_at=_dt(),
        ),
        "brands": ("Apple", "Dell", "Lenovo"),
        "marketplaces": ("Lazada",),
        "wishlist": ("sa-laptop-macbook-air-m3",),
        "owned": (),
        "accessories": ("sa-earbuds-airpods-pro-2",),
        "saved_products": (
            SavedProduct(
                id="saved-traveler-1",
                user_id="user-traveler",
                product_id="sa-laptop-macbook-air-m3",
                product_name="MacBook Air M3",
                marketplace="Lazada",
                price=64990.0,
                favorite=True,
                created_at=_dt(),
            ),
        ),
        "comparisons": (
            SavedComparison(
                id="cmp-traveler-1",
                user_id="user-traveler",
                product_ids=("sa-laptop-macbook-air-m3", "sa-laptop-tuf-a15"),
                title="Travel laptops",
                created_at=_dt(),
            ),
        ),
        "history": (
            RecommendationHistory(
                id="hist-traveler-1",
                user_id="user-traveler",
                query="Light laptop for frequent travel",
                recommendation_summary="MacBook Air M3 balances battery and weight.",
                product_ids=("sa-laptop-macbook-air-m3",),
                profile_id="profile-business-traveler",
                created_at=_dt(),
            ),
        ),
        "searches": (
            SavedSearch(
                id="search-traveler-1",
                user_id="user-traveler",
                query="ultrabook travel battery",
                filters={"category": "laptop", "budget_max": 55000},
                created_at=_dt(),
            ),
        ),
        "recent": ("sa-laptop-macbook-air-m3",),
    },
)


def list_demo_users() -> list[User]:
    return [item["user"] for item in DEMO_USERS]


def get_demo_bundle(email: str) -> dict[str, Any] | None:
    cleaned = email.strip().lower()
    for item in DEMO_USERS:
        if item["user"].email == cleaned:
            return item
    return None


def seed_demo_users(store: Any) -> list[User]:
    """Seed an InMemoryUserPlatformStore (duck-typed) with demo accounts."""
    seeded: list[User] = []
    for bundle in DEMO_USERS:
        user: User = bundle["user"]
        store.users.save(user)
        prefs: UserPreference = bundle["preferences"]
        brands = tuple(
            FavoriteBrand(user_id=user.user_id, brand=b, created_at=_dt()) for b in bundle["brands"]
        )
        markets = tuple(
            FavoriteMarketplace(user_id=user.user_id, marketplace=m, created_at=_dt())
            for m in bundle["marketplaces"]
        )
        wishlist = Wishlist(
            user_id=user.user_id,
            product_ids=tuple(bundle["wishlist"]),
            updated_at=_dt(),
        )
        profile = UserProfile(
            user_id=user.user_id,
            display_name=user.display_name,
            preferences=prefs,
            favorite_brands=brands,
            favorite_marketplaces=markets,
            wishlist=wishlist,
            owned_products=tuple(bundle["owned"]),
            accessories=tuple(bundle["accessories"]),
            version=ProfileVersion(
                user_id=user.user_id,
                version=1,
                changed_at=_dt(),
                change_summary="demo_seed",
            ),
        )
        store.profiles.save_profile(profile)
        store.profiles.save_settings(
            UserSettings(
                user_id=user.user_id,
                theme="system",
                language="en",
                notification_settings=NotificationPreference(user_id=user.user_id),
                ai_mode_preference="economy",
                privacy_settings={"share_community_activity": False},
                community_settings={"show_trusted_reviews": True},
                updated_at=_dt(),
            )
        )
        for product in bundle["saved_products"]:
            store.saved.save_product(product)
        for comparison in bundle["comparisons"]:
            store.saved.save_comparison(comparison)
        for history in bundle["history"]:
            store.saved.add_history(history)
        for search in bundle["searches"]:
            store.saved.save_search(search)
        store.saved.save_recently_viewed(
            RecentlyViewed(
                user_id=user.user_id,
                product_ids=tuple(bundle["recent"]),
                updated_at=_dt(),
            )
        )
        seeded.append(user)
    return seeded
