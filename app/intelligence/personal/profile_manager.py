"""Profile manager for fixture-backed customer profiles."""

from __future__ import annotations

from app.domain.entities.personal_agent import CustomerProfile
from app.domain.exceptions import PersonalAgentNotFoundError, PersonalAgentValidationError
from app.domain.interfaces.personal_agent_repository import CustomerProfileRepository
from app.intelligence.personal.memory import InMemoryCustomerProfileRepository


class ProfileManager:
    """Load, list, and switch demo customer profiles."""

    def __init__(self, repository: CustomerProfileRepository | None = None) -> None:
        self._repo = repository or InMemoryCustomerProfileRepository()

    @property
    def repository(self) -> CustomerProfileRepository:
        return self._repo

    def list_profiles(self) -> list[CustomerProfile]:
        return self._repo.list_profiles()

    def get_profile(self, profile_id: str | None = None) -> CustomerProfile:
        if profile_id is None or not str(profile_id).strip():
            active = self._repo.get_active()
            if active is None:
                raise PersonalAgentNotFoundError("active")
            return active
        profile = self._repo.get(str(profile_id).strip())
        if profile is None:
            raise PersonalAgentNotFoundError(str(profile_id).strip())
        return profile

    def get_active(self) -> CustomerProfile:
        return self.get_profile(None)

    def set_active(self, profile_id: str) -> CustomerProfile:
        return self._repo.set_active(profile_id)

    def intent_overrides(self, profile: CustomerProfile) -> dict:
        """Map profile fields into Shopping Assistant intent overrides."""
        overrides: dict = {
            "currency": profile.currency,
            "use_cases": list(profile.use_cases()),
        }
        if profile.budget is not None:
            overrides["budget_max"] = profile.budget
        if profile.favorite_categories:
            overrides["category"] = profile.favorite_categories[0]
        return overrides

    def require_profile_id(self, profile_id: str | None) -> str:
        if profile_id is None or not str(profile_id).strip():
            active = self.get_active()
            return active.profile_id
        cleaned = str(profile_id).strip()
        if self._repo.get(cleaned) is None:
            raise PersonalAgentNotFoundError(cleaned)
        return cleaned

    def validate_switch(self, profile_id: str) -> CustomerProfile:
        if not profile_id or not profile_id.strip():
            raise PersonalAgentValidationError("profile_id must not be blank.")
        return self.set_active(profile_id.strip())
