"""In-memory profile repository for demo / fixture profiles."""

from __future__ import annotations

from app.domain.entities.personal_agent import CustomerProfile
from app.domain.exceptions import PersonalAgentNotFoundError, PersonalAgentValidationError
from app.domain.interfaces.personal_agent_repository import CustomerProfileRepository
from app.intelligence.personal.fixtures import (
    DEFAULT_PROFILE_ID,
    get_demo_profile,
    list_demo_profiles,
)


class InMemoryCustomerProfileRepository(CustomerProfileRepository):
    """Process-scoped fixture profile store with an active profile pointer."""

    def __init__(self, *, default_profile_id: str = DEFAULT_PROFILE_ID) -> None:
        self._profiles = {p.profile_id: p for p in list_demo_profiles()}
        if default_profile_id not in self._profiles:
            raise PersonalAgentValidationError(
                f"Default profile not found in fixtures: {default_profile_id}"
            )
        self._active_id = default_profile_id

    def list_profiles(self) -> list[CustomerProfile]:
        return [self._profiles[key] for key in sorted(self._profiles)]

    def get(self, profile_id: str) -> CustomerProfile | None:
        cleaned = profile_id.strip()
        if not cleaned:
            return None
        return self._profiles.get(cleaned) or get_demo_profile(cleaned)

    def get_active(self) -> CustomerProfile | None:
        return self._profiles.get(self._active_id)

    def set_active(self, profile_id: str) -> CustomerProfile:
        cleaned = profile_id.strip()
        if not cleaned:
            raise PersonalAgentValidationError("profile_id must not be blank.")
        profile = self.get(cleaned)
        if profile is None:
            raise PersonalAgentNotFoundError(cleaned)
        self._active_id = profile.profile_id
        return profile
