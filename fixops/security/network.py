from __future__ import annotations

import ipaddress

_LOOPBACK_HOSTNAMES = {"localhost", "localhost.localdomain"}


def is_loopback_host(host: str | None) -> bool:
    """Return True only if ``host`` is a loopback hostname or address."""
    if not host:
        return False
    candidate = host.strip().lower()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1]
    if candidate in _LOOPBACK_HOSTNAMES:
        return True
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback
