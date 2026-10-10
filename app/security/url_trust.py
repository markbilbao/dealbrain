"""Class-specific URL checks for browser destinations and server fetches.

Server-fetch checks do not resolve DNS names. Numeric hosts that Python's
``ipaddress`` module rejects, but that the platform numeric parser accepts,
are classified with ``socket.getaddrinfo(..., AI_NUMERICHOST)``. That flag
does not query DNS. A hostname that is not a numeric address is not resolved.
DNS rebinding is outside this check.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit

BROWSER_URL_SCHEMES = frozenset({"http", "https"})
SERVER_FETCH_SCHEMES = frozenset({"https"})

_LOCAL_NAMES = frozenset({"localhost", "localhost.localdomain"})
_UNSAFE_TEXT = re.compile(r"[\x00-\x20\x7f\\\"'<>\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_NUMERIC_HOST = re.compile(
    r"^(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+))*$",
    re.IGNORECASE,
)
_DNS_LABEL = re.compile(r"[a-z0-9-]+")


class UrlTrustError(ValueError):
    """A URL failed its trust-boundary check.

    Messages name the rule. They do not echo the URL, so a rejected credential
    cannot be copied into a log or an API error.
    """


def validate_browser_destination(url: str, *, max_length: int | None = None) -> str:
    """Accept an http(s) browser link or resource URL.

    Canonical private, loopback, link-local, and other non-global addresses
    are allowed. The server does not fetch this class. Unusual textual IP
    forms and IPv4-mapped addresses are rejected because parsers disagree
    about the host they name.
    """

    return _validate(
        url,
        schemes=BROWSER_URL_SCHEMES,
        server_fetch=False,
        max_length=max_length,
    )


def validate_server_fetch_url(url: str, *, max_length: int = 2048) -> str:
    """Accept an https URL that is safe to pass to a server-side HTTP client.

    Hostnames are not resolved. Callers that own a fixed provider endpoint
    must still require that exact URL.
    """

    return _validate(
        url,
        schemes=SERVER_FETCH_SCHEMES,
        server_fetch=True,
        max_length=max_length,
    )


def _validate(
    url: str,
    *,
    schemes: frozenset[str],
    server_fetch: bool,
    max_length: int | None,
) -> str:
    if not isinstance(url, str):
        raise UrlTrustError("URL is malformed")
    cleaned = url.strip()
    if not cleaned:
        raise UrlTrustError("URL is missing a host")
    if max_length is not None and len(cleaned) > max_length:
        raise UrlTrustError("URL is too long")
    if _UNSAFE_TEXT.search(cleaned):
        raise UrlTrustError("URL contains an unsupported character")

    try:
        parsed = urlsplit(cleaned)
    except ValueError as exc:
        raise UrlTrustError("URL is malformed") from exc

    scheme = parsed.scheme.lower()
    if scheme not in schemes:
        raise UrlTrustError("URL scheme is not allowed")
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise UrlTrustError("URL must not contain embedded credentials")
    if "%" in parsed.netloc:
        raise UrlTrustError("URL host is malformed")

    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UrlTrustError("URL host is malformed") from exc
    if not hostname:
        raise UrlTrustError("URL is missing a host")
    if hostname.startswith(".") or ".." in hostname or "[" in hostname or "]" in hostname:
        raise UrlTrustError("URL host is malformed")
    if port == 0:
        raise UrlTrustError("URL host is malformed")

    address = _address_for_host(hostname)
    if address is not None:
        mapped = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else None
        if mapped is not None:
            raise UrlTrustError("URL host uses an IPv4-mapped address")
        if server_fetch and _is_blocked_address(address):
            raise UrlTrustError("URL host is not an approved network destination")
        return cleaned

    if not _is_dns_hostname(hostname):
        raise UrlTrustError("URL host is malformed")
    if server_fetch and _is_local_name(hostname):
        raise UrlTrustError("URL host is not an approved network destination")
    return cleaned


def _address_for_host(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        pass
    if _NUMERIC_HOST.fullmatch(hostname) is None:
        return None
    try:
        infos = socket.getaddrinfo(
            hostname,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=0,
            flags=socket.AI_NUMERICHOST,
        )
    except OSError as exc:
        raise UrlTrustError("URL host is malformed") from exc
    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        addresses.add(ipaddress.ip_address(sockaddr[0]))
    if len(addresses) != 1:
        raise UrlTrustError("URL host is malformed")
    # ``ipaddress`` rejected this text. The platform numeric parser accepted it.
    # That disagreement is the bypass, including when the result is public.
    raise UrlTrustError("URL host uses an unusual IP form")


def _is_blocked_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _is_blocked_address(ip.ipv4_mapped)
    return bool(
        ip.is_multicast
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_private
        or ip.is_reserved
        or not ip.is_global
    )


def _is_local_name(hostname: str) -> bool:
    name = hostname.rstrip(".").lower()
    return name in _LOCAL_NAMES or name.endswith(".localhost")


def _is_dns_hostname(hostname: str) -> bool:
    name = hostname[:-1] if hostname.endswith(".") else hostname
    if not name or name.startswith(".") or ".." in name:
        return False
    try:
        encoded = name.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    if len(encoded) > 253:
        return False
    labels = encoded.split(".")
    for label in labels:
        if not label or len(label) > 63:
            return False
        if label.startswith("-") or label.endswith("-"):
            return False
        if _DNS_LABEL.fullmatch(label) is None:
            return False
    return True
