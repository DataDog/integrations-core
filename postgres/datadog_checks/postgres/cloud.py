# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Helpers for discovering managed cloud database endpoints.

This module has two intentionally separate layers:

1. ``resolve_cname_chain`` - a provider-agnostic DNS helper that follows a host's
   CNAME chain and returns every hostname in it. It knows nothing about cloud
   providers.
2. A small, named registry (``CLOUD_HOSTNAME_PATTERNS``) plus
   ``find_cloud_endpoint_in_chain`` / ``detect_cloud_endpoint`` that match the
   resolved hostnames against known managed-DB hostname suffixes. Today only AWS
   RDS/Aurora is registered, but GCP and Azure can be added as registry entries
   without changing any control flow.

This is deliberately kept separate from ``resolve_db_host`` (which computes the
reported hostname): cloud-resource attribution must not change a check's
reported hostname, and it relies on CNAME-chain resolution rather than IP
comparison.
"""

import ipaddress
import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__file__)

AWS_RDS_HOSTNAME_SUFFIX = ".rds.amazonaws.com"

# Default bounds for DNS resolution so check initialization never hangs.
DEFAULT_DNS_TIMEOUT = 1.0
DEFAULT_MAX_HOPS = 10


@dataclass
class CloudEndpoint:
    """A managed cloud database endpoint discovered from a hostname."""

    provider: str
    product: str
    resource_type: str
    endpoint: str


# (product, hostname_suffix, resource_type)
CloudPattern = tuple[str, str, str]

# provider -> list of CloudPattern
CLOUD_HOSTNAME_PATTERNS: dict[str, list[CloudPattern]] = {
    "aws": [
        ("rds", AWS_RDS_HOSTNAME_SUFFIX, "aws_rds_instance"),
    ],
    # Future providers, e.g.:
    # "gcp": [("cloudsql", ".<suffix>", "gcp_sql_database_instance")],
    # "azure": [("flexible_server", ".<suffix>", "azure_postgresql_flexible_server")],
}


def resolve_cname_chain(
    host: str,
    timeout: float = DEFAULT_DNS_TIMEOUT,
    max_hops: int = DEFAULT_MAX_HOPS,
    stop: Callable[[str], bool] | None = None,
) -> list[str]:
    """Follow ``host``'s CNAME chain and return the ordered list of hostnames.

    The returned list always starts with ``host`` (lowercased, trailing dot
    stripped) and is followed by each CNAME target encountered. This is
    provider-agnostic and resolves gracefully: on any DNS error, an import
    failure, or a loop/hop-limit, it returns whatever chain has been collected
    so far (at minimum the original host).

    ``stop`` is an optional predicate evaluated against each resolved hostname
    (including ``host``). When it returns ``True`` resolution stops early, so a
    caller can avoid resolving the rest of the chain once it has found what it
    needs.
    """
    chain: list[str] = []
    if not host:
        return chain

    name = _normalize_hostname(host)
    chain.append(name)

    if stop is not None and stop(name):
        return chain

    # Skip DNS for hosts that can never be a managed cloud endpoint behind a CNAME
    # (unix sockets, localhost, .local, and IP literals). This avoids needless
    # lookups and latency during check initialization.
    if _should_skip_dns(name):
        return chain

    try:
        import dns.resolver
        from dns.exception import DNSException
    except ImportError as e:  # pragma: no cover - dnspython is bundled with the agent
        logger.debug("dnspython unavailable, skipping CNAME resolution for '%s': %r", host, e)
        return chain

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    seen = {name}
    for _ in range(max_hops):
        try:
            answer = resolver.resolve(name, 'CNAME')
        except DNSException as e:
            logger.debug("stopped resolving CNAME chain for '%s' at '%s': %r", host, name, e)
            break
        except Exception as e:
            logger.debug("unexpected error resolving CNAME chain for '%s' at '%s': %r", host, name, e)
            break

        target = _normalize_hostname(str(answer[0].target))
        if not target or target in seen:
            break
        seen.add(target)
        chain.append(target)
        name = target

        if stop is not None and stop(name):
            break

    return chain


def match_cloud_hostname(hostname: str) -> CloudEndpoint | None:
    """Return a ``CloudEndpoint`` if ``hostname`` matches a known cloud pattern, else ``None``."""
    if not hostname:
        return None
    for provider, patterns in CLOUD_HOSTNAME_PATTERNS.items():
        for product, suffix, resource_type in patterns:
            if hostname.endswith(suffix):
                return CloudEndpoint(provider=provider, product=product, resource_type=resource_type, endpoint=hostname)
    return None


def find_cloud_endpoint_in_chain(chain: list[str]) -> CloudEndpoint | None:
    """Return the first hostname in ``chain`` that matches a known cloud pattern."""
    for hostname in chain:
        result = match_cloud_hostname(hostname)
        if result is not None:
            return result
    return None


def detect_cloud_endpoint(
    host: str, timeout: float = DEFAULT_DNS_TIMEOUT, max_hops: int = DEFAULT_MAX_HOPS
) -> CloudEndpoint | None:
    """Resolve ``host``'s CNAME chain and return any matching managed-DB endpoint.

    Resolution short-circuits at the first hop that matches a known cloud pattern,
    so the rest of the chain (e.g. internal compute hostnames) is not resolved.
    Returns ``None`` when ``host`` does not resolve to a recognized managed cloud
    database endpoint, so callers can safely fall back to existing behavior.
    """
    chain = resolve_cname_chain(
        host, timeout=timeout, max_hops=max_hops, stop=lambda h: match_cloud_hostname(h) is not None
    )
    return find_cloud_endpoint_in_chain(chain)


def _normalize_hostname(hostname: str) -> str:
    return hostname.strip().rstrip('.').lower() if hostname else ''


def _should_skip_dns(host: str) -> bool:
    if not host or host == 'localhost' or host.startswith('/') or host.endswith('.local'):
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
