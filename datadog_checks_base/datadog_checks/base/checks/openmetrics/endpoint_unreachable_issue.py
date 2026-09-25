# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import errno
import hashlib
import json
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from requests.exceptions import ProxyError as RequestsProxyError
from urllib3.exceptions import ProxyError as Urllib3ProxyError

if TYPE_CHECKING:
    from datadog_checks.base.checks import AgentCheck

ISSUE_NAME = 'OpenMetrics Endpoint Unreachable'
ISSUE_TYPE = 'openmetrics_endpoint_unreachable'
ISSUE_ID_PREFIX = 'openmetrics-endpoint-unreachable'
ERROR_MESSAGE = 'No route to host'
WSAEHOSTUNREACH = getattr(errno, 'WSAEHOSTUNREACH', 10065)
HOST_UNREACHABLE_ERRNOS = frozenset((errno.EHOSTUNREACH, WSAEHOSTUNREACH))
PROXY_ERROR_TYPES = (RequestsProxyError, Urllib3ProxyError)


@dataclass(frozen=True)
class EndpointDetails:
    sanitized: str
    host: str
    port: int
    path: str


def report(check: AgentCheck, endpoint: str | None, error: BaseException, namespace: str = '') -> None:
    """Report an issue when an endpoint failure means no route to host."""
    try:
        details = _endpoint_details(endpoint)
        if details is None or not _is_unreachable(error):
            return

        namespace = str(namespace)
        check.report_issue(
            id=_issue_id(check.hostname, check.name, endpoint, namespace),
            issue_name=ISSUE_NAME,
            issue_type=ISSUE_TYPE,
            title=f'OpenMetrics endpoint unreachable: {details.sanitized}',
            description=(
                f'The {check.name} check cannot reach {details.sanitized} because no network route exists from '
                'the reporting Agent or Cluster Check Runner.'
            ),
            category='integration',
            severity=check.IssueSeverity['MEDIUM'],
            extra={
                'check_name': check.name,
                'endpoint': details.sanitized,
                'target_host': details.host,
                'target_port': details.port,
                'target_path': details.path,
                'namespace': namespace,
                'error_kind': 'no_route_to_host',
                'error_message': ERROR_MESSAGE,
            },
            remediation=_remediation(),
            tags=[f'integration:{check.name}', 'openmetrics', 'endpoint-unreachable'],
        )
    except Exception:
        check.log.debug('Failed to report the OpenMetrics endpoint-unreachable issue', exc_info=True)


def resolve(check: AgentCheck, endpoint: str | None, namespace: str = '') -> None:
    """Resolve the issue associated with an endpoint."""
    try:
        if _endpoint_details(endpoint) is None:
            return
        check.resolve_issue(_issue_id(check.hostname, check.name, endpoint, str(namespace)))
    except Exception:
        check.log.debug('Failed to resolve the OpenMetrics endpoint-unreachable issue', exc_info=True)


def _endpoint_details(endpoint: str | None) -> EndpointDetails | None:
    if not isinstance(endpoint, str) or not endpoint:
        return None

    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname
        explicit_port = parsed.port
    except (TypeError, ValueError):
        return None

    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https') or not host or any(character.isspace() for character in host):
        return None

    port = explicit_port if explicit_port is not None else (443 if scheme == 'https' else 80)
    if not 1 <= port <= 65535:
        return None

    # Drop credentials, query, and fragment so secrets in the configured URL never reach the issue.
    display_host = f'[{host}]' if ':' in host else host
    sanitized_netloc = display_host if explicit_port is None else f'{display_host}:{explicit_port}'
    path = parsed.path or '/'
    return EndpointDetails(
        sanitized=urlunsplit((scheme, sanitized_netloc, path, '', '')),
        host=host,
        port=port,
        path=path,
    )


def _is_unreachable(error: BaseException) -> bool:
    pending = deque([error])
    seen: set[int] = set()
    host_unreachable = False

    while pending:
        current = pending.popleft()
        if id(current) in seen:
            continue
        seen.add(id(current))

        if isinstance(current, PROXY_ERROR_TYPES):
            # urllib3 uses ProxyError while connecting to the proxy, so the unreachable host is not the endpoint.
            return False

        if isinstance(current, OSError) and (
            current.errno in HOST_UNREACHABLE_ERRNOS or getattr(current, 'winerror', None) == WSAEHOSTUNREACH
        ):
            host_unreachable = True

        linked = (current.__cause__, current.__context__, getattr(current, 'reason', None), *current.args)
        pending.extend(value for value in linked if isinstance(value, BaseException))

    return host_unreachable


def _issue_id(hostname: str, check_name: str, endpoint: str, namespace: str) -> str:
    identity = json.dumps((hostname, check_name, endpoint, namespace), separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'{ISSUE_ID_PREFIX}:{digest}'


def _remediation() -> dict[str, str | list[dict[str, int | str]]]:
    return {
        'summary': (
            'Restore network reachability from the reporting Agent or Cluster Check Runner to this OpenMetrics '
            'endpoint, or correct a stale endpoint.'
        ),
        'steps': [
            {
                'order': 1,
                'text': (
                    'Confirm the endpoint target still exists. If it came from Autodiscovery, run agent configcheck '
                    'and correct stale configuration, such as the IP of a pod that no longer exists.'
                ),
            },
            {
                'order': 2,
                'text': (
                    'Test the connection from the network namespace of the reporting Agent or Cluster Check Runner, '
                    'for example with curl.'
                ),
            },
            {
                'order': 3,
                'text': (
                    'If the endpoint is reachable locally, inspect firewalls and security groups, Kubernetes '
                    'NetworkPolicy or Cilium policy, and cross-node CNI routing.'
                ),
            },
            {
                'order': 4,
                'text': 'The issue resolves automatically after the endpoint becomes reachable.',
            },
        ],
    }
