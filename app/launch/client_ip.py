"""Client address for rate limits behind the AWS ALB.

The socket peer is trusted only when it belongs to a configured proxy network.
AWS ALB appends the address it observed to ``X-Forwarded-For``. The client is
the rightmost address in that header that is not itself a trusted proxy.
Addresses to the left were supplied by the caller and are ignored.

A direct caller outside the trusted networks cannot rotate buckets by sending
``X-Forwarded-For``. ``*`` and a default route are rejected.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence

_REJECTED_NETWORKS = frozenset({"0.0.0.0/0", "::/0"})


class TrustedProxyConfigurationError(ValueError):
    """``TRUSTED_PROXY_CIDRS`` is empty of meaning or not a set of IP networks."""


def parse_trusted_networks(
    values: Sequence[str],
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """Parse proxy CIDRs. Bare addresses become a single-host network."""

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in values:
        item = raw.strip()
        if not item:
            continue
        if item == "*" or item in _REJECTED_NETWORKS:
            raise TrustedProxyConfigurationError(
                "TRUSTED_PROXY_CIDRS must name the ALB and local proxy networks"
            )
        try:
            if "/" in item:
                network = ipaddress.ip_network(item, strict=True)
            else:
                address = ipaddress.ip_address(item)
                network = ipaddress.ip_network(f"{address}/{address.max_prefixlen}")
        except ValueError as exc:
            raise TrustedProxyConfigurationError(
                "TRUSTED_PROXY_CIDRS contains an invalid network"
            ) from exc
        networks.append(network)
    return tuple(networks)


def client_host_for_rate_limit(
    *,
    peer: str | None,
    forwarded_for: str,
    trusted_proxy_cidrs: Sequence[str],
) -> str:
    """Return the rate-limit client host, or ``unknown`` when no peer exists."""

    peer_text = (peer or "").strip()
    if not peer_text:
        return "unknown"
    try:
        networks = parse_trusted_networks(trusted_proxy_cidrs)
    except TrustedProxyConfigurationError:
        return _display(peer_text)
    if not networks or not _is_trusted(peer_text, networks):
        return _display(peer_text)

    hops = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    for hop in reversed(hops):
        parsed = _parse_hop(hop)
        if parsed is None:
            return _display(peer_text)
        if _address_is_trusted(parsed, networks):
            continue
        return _display_address(parsed)
    return _display(peer_text)


def _is_trusted(
    host: str,
    networks: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    parsed = _parse_hop(host)
    if parsed is None:
        return False
    return _address_is_trusted(parsed, networks)


def _address_is_trusted(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    candidate = _mapped_ipv4(address)
    return any(
        candidate.version == network.version and candidate in network for network in networks
    )


def _mapped_ipv4(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _parse_hop(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    host = value.strip().strip('"')
    if not host:
        return None
    if host.startswith("["):
        end = host.find("]")
        if end <= 1:
            return None
        host = host[1:end]
    elif host.count(":") == 1:
        host, _separator, port = host.rpartition(":")
        if not port.isdigit():
            return None
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _display(host: str) -> str:
    parsed = _parse_hop(host)
    if parsed is None:
        return host
    return _display_address(parsed)


def _display_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    return str(_mapped_ipv4(address))
