"""Canonical Product Registry — resolve-or-create durable product identities."""

from app.domain.identity import missing_identity_fields
from app.intelligence.canonical_registry.identity import (
    build_display_name,
    build_identity_hash,
    build_identity_key,
)
from app.intelligence.canonical_registry.memory import InMemoryCanonicalProductStore
from app.intelligence.canonical_registry.registry import CanonicalProductRegistryService

__all__ = [
    "CanonicalProductRegistryService",
    "InMemoryCanonicalProductStore",
    "build_display_name",
    "build_identity_hash",
    "build_identity_key",
    "missing_identity_fields",
]
