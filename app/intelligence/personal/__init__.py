"""Personal AI Shopping Agent intelligence package."""

from app.intelligence.personal.buying_advisor import BuyingAdvisor
from app.intelligence.personal.explanation_engine import ExplanationEngine
from app.intelligence.personal.fixtures import (
    DEFAULT_PROFILE_ID,
    DEMO_PROFILES,
    LIMITATIONS,
    catalog_product_map,
    default_profile,
    get_demo_profile,
    list_demo_profiles,
)
from app.intelligence.personal.memory import InMemoryCustomerProfileRepository
from app.intelligence.personal.preference_engine import PreferenceEngine
from app.intelligence.personal.profile_manager import ProfileManager
from app.intelligence.personal.recommendation_engine import PersonalRecommendationEngine
from app.intelligence.personal.scoring_engine import PersonalScoringEngine

__all__ = [
    "BuyingAdvisor",
    "DEFAULT_PROFILE_ID",
    "DEMO_PROFILES",
    "ExplanationEngine",
    "InMemoryCustomerProfileRepository",
    "LIMITATIONS",
    "PersonalRecommendationEngine",
    "PersonalScoringEngine",
    "PreferenceEngine",
    "ProfileManager",
    "catalog_product_map",
    "default_profile",
    "get_demo_profile",
    "list_demo_profiles",
]
