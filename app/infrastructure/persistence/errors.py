"""Persistence-related domain exceptions (Sprint 23)."""

from __future__ import annotations


class PersistenceError(Exception):
    """Base class for persistence adapter failures."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PersistenceUnavailableError(PersistenceError):
    """Database is unreachable or the engine cannot be constructed."""


class PersistenceConflictError(PersistenceError):
    """Uniqueness or optimistic concurrency conflict."""


class PersistenceForeignKeyError(PersistenceError):
    """Foreign-key / referential integrity violation."""


class PersistenceSchemaError(PersistenceError):
    """Required schema or migration version is missing/invalid."""


class PersistenceRetryableError(PersistenceError):
    """Transient database failure that may succeed on retry."""


class PersistenceConfigurationError(PersistenceError):
    """Production/demo persistence binding is invalid for the active environment."""
