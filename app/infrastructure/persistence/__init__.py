"""Sprint 23 operational persistence package."""

from app.infrastructure.persistence.codec import decode, decode_entity, encode, encode_entity
from app.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceConfigurationError,
    PersistenceError,
    PersistenceForeignKeyError,
    PersistenceRetryableError,
    PersistenceSchemaError,
    PersistenceUnavailableError,
)
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session import (
    get_sync_engine,
    get_sync_session_factory,
    ping_sync_database,
    require_operational_schema,
    reset_sync_engine,
    sync_session,
    to_sync_database_url,
    translate_db_error,
)
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence import stores

__all__ = [
    "OperationalStore",
    "PersistenceConflictError",
    "PersistenceConfigurationError",
    "PersistenceError",
    "PersistenceForeignKeyError",
    "PersistenceRetryableError",
    "PersistenceSchemaError",
    "PersistenceUnavailableError",
    "SessionBound",
    "decode",
    "decode_entity",
    "encode",
    "encode_entity",
    "get_sync_engine",
    "get_sync_session_factory",
    "ping_sync_database",
    "require_operational_schema",
    "reset_sync_engine",
    "stores",
    "sync_session",
    "to_sync_database_url",
    "translate_db_error",
]
