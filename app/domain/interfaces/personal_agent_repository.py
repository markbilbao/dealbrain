"""Repository ports for Personal AI Shopping Agent profiles."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.personal_agent import CustomerProfile


class CustomerProfileRepository(ABC):
    """Abstract store for fixture / demo customer profiles."""

    @abstractmethod
    def list_profiles(self) -> list[CustomerProfile]:
        raise NotImplementedError

    @abstractmethod
    def get(self, profile_id: str) -> CustomerProfile | None:
        raise NotImplementedError

    @abstractmethod
    def get_active(self) -> CustomerProfile | None:
        raise NotImplementedError

    @abstractmethod
    def set_active(self, profile_id: str) -> CustomerProfile:
        raise NotImplementedError
