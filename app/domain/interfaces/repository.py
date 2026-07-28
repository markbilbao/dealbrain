"""Repository port interface.

Implementations belong in ``app.infrastructure.database.repositories``.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class Repository(ABC, Generic[T, ID]):
    """Abstract repository contract for persistence operations."""

    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> T | None:
        """Retrieve an entity by its identifier."""

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Persist a new or updated entity."""

    @abstractmethod
    async def delete(self, entity_id: ID) -> None:
        """Remove an entity by its identifier."""
