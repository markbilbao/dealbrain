"""Shopify catalog transport.

``post_json`` is the only operation. Production composition may hold an
:class:`UrllibJsonTransport` instance. Constructing it does not connect, and
current closed gates never call ``post_json``. Importing this module does not
open a socket. Tests inject a fake that implements :class:`JsonPostTransport`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CatalogTransportResult:
    """Parsed transport outcome. The raw body is not retained."""

    status_code: int
    payload: dict[str, Any] | None
    timed_out: bool = False
    malformed: bool = False
    transport_unavailable: bool = False
    raw_body_persisted: bool = False

    def __post_init__(self) -> None:
        if self.raw_body_persisted:
            raise ValueError("raw Shopify bodies must not be persisted")
        if self.timed_out and self.transport_unavailable:
            raise ValueError("a timeout is not a connection failure")
        if self.timed_out and (self.payload is not None or self.malformed):
            raise ValueError("a timeout has no payload")
        if self.transport_unavailable and (
            self.payload is not None or self.malformed or self.status_code != 0
        ):
            raise ValueError("a connection failure has no HTTP response")


class JsonPostTransport(Protocol):
    """Narrow injected transport. Callers choose the implementation."""

    def post_json(
        self,
        endpoint: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> CatalogTransportResult:
        """Post one JSON body. Implementations must not retry."""


_PRODUCTION_TRANSPORT_TOKEN = object()


class ProductionTransportAuthority:
    """Opaque server marker that a transport may carry production evidence.

    The production composition factory is the issuer. The marker is not a
    secret, is not browser input, and is not written to evidence rows.
    """

    def __init__(self, token: object) -> None:
        if token is not _PRODUCTION_TRANSPORT_TOKEN:
            raise ValueError("production transport authority is server-issued")
        self._token = token

    def proves_production_transport(self) -> bool:
        return self._token is _PRODUCTION_TRANSPORT_TOKEN


def issue_production_transport_authority() -> ProductionTransportAuthority:
    """Mint the in-memory marker. Callers do not persist it."""

    return ProductionTransportAuthority(_PRODUCTION_TRANSPORT_TOKEN)


class UrllibJsonTransport:
    """HTTP-capable catalog transport.

    Constructing this object does not connect. ``post_json`` performs one
    request with the caller-supplied timeout and does not retry. Production
    composition may construct this object with a server-issued authority.
    A bare instance is not that authority. Current gates do not call it.
    """

    def __init__(self, *, authority: ProductionTransportAuthority | None = None) -> None:
        if authority is not None and type(authority) is not ProductionTransportAuthority:
            raise ValueError("production transport authority is server-issued")
        if authority is not None and not authority.proves_production_transport():
            raise ValueError("production transport authority is server-issued")
        self.production_transport_authority = authority

    def post_json(
        self,
        endpoint: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> CatalogTransportResult:
        encoded = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=encoded,
            headers={str(key): str(value) for key, value in headers.items()},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                body = response.read()
        except TimeoutError:
            return CatalogTransportResult(status_code=0, payload=None, timed_out=True)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            body = exc.read()
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                return CatalogTransportResult(status_code=0, payload=None, timed_out=True)
            return CatalogTransportResult(status_code=0, payload=None, transport_unavailable=True)
        return _parse_body(status, body)


def _parse_body(status: int, body: bytes) -> CatalogTransportResult:
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return CatalogTransportResult(status_code=status, payload=None, malformed=True)
    if not isinstance(parsed, dict):
        return CatalogTransportResult(status_code=status, payload=None, malformed=True)
    return CatalogTransportResult(status_code=status, payload=parsed)
