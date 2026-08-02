"""Helpers for configuring Alembic with URL-encoded database credentials.

Alembic ``Config.set_main_option`` stores values in a ``ConfigParser`` that
performs ``%``-style interpolation. Percent-encoded usernames/passwords in
``DATABASE_URL`` must therefore be escaped as ``%%`` before assignment.
``ConfigParser.get`` / ``get_main_option`` returns the original single-``%``
URL for the SQLAlchemy driver.
"""

from __future__ import annotations

import re

# Structural patterns — never keyed to a specific password or host.
_DB_URL_RE = re.compile(
    r"(?i)\b(?:postgresql(?:\+\w+)?|postgres(?:\+\w+)?|mysql(?:\+\w+)?"
    r"|mariadb(?:\+\w+)?|sqlite(?:\+\w+)?|mssql(?:\+\w+)?)"
    r"://[^\s\"'<>]+"
)
_DATABASE_URL_ASSIGN_RE = re.compile(r"(?i)\bDATABASE_URL\s*[:=]\s*[\"']?[^\s\"']+")


def escape_alembic_config_url(database_url: str) -> str:
    """Escape ``%`` for Alembic/ConfigParser interpolation (``%`` → ``%%``)."""
    return database_url.replace("%", "%%")


def sanitize_database_url_message(message: str) -> str:
    """Strip connection strings and DATABASE_URL assignments from free-form text."""
    text = _DB_URL_RE.sub("***REDACTED_DATABASE_URL***", message)
    return _DATABASE_URL_ASSIGN_RE.sub("DATABASE_URL=***REDACTED***", text)


def set_alembic_sqlalchemy_url(config: object, database_url: str) -> None:
    """Set ``sqlalchemy.url`` on an Alembic Config without leaking credentials.

    Raises a sanitized ``ValueError`` if ConfigParser rejects the value.
    """
    escaped = escape_alembic_config_url(database_url)
    try:
        config.set_main_option("sqlalchemy.url", escaped)  # type: ignore[attr-defined]
    except ValueError as exc:
        raise ValueError(
            "invalid sqlalchemy.url for Alembic Config "
            f"(credentials redacted; {type(exc).__name__})"
        ) from None
