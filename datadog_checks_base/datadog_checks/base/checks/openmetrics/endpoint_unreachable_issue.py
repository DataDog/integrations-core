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
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

if TYPE_CHECKING:
    from datadog_checks.base.checks import AgentCheck

ISSUE_NAME = 'OpenMetrics Endpoint Unreachable'
ISSUE_TYPE = 'openmetrics_endpoint_unreachable'

REMEDIATION_SUMMARY = (
    'Restore network reachability from the reporting Agent or Cluster Check Runner to this OpenMetrics endpoint, '
    'or correct a stale endpoint.'
)


@dataclass(frozen=True)
class EndpointDetails:
    sanitized: str
    host: str
    port: int
    path: str
    secrets: frozenset[str]
    query: str


class EndpointUnreachableIssueReporter:
    @staticmethod
    def report(check: AgentCheck, endpoint: str | None, error: BaseException, namespace: str = '') -> None:
        """Report an issue when an endpoint failure means no route to host."""
        details = _endpoint_details(endpoint)
        if details is None:
            check.log.debug('Cannot report an OpenMetrics endpoint-unreachable issue without a valid endpoint')
            return

        is_unreachable, error_message = _classify_error(error)
        if not is_unreachable:
            return

        issue_id = _issue_id(check.hostname, check.name, endpoint, namespace)
        try:
            check.report_issue(
                id=issue_id,
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
                    'error_message': _sanitize_error_message(error_message, endpoint, details),
                },
                remediation=_remediation(check.name, details),
                tags=[f'integration:{check.name}', 'openmetrics', 'endpoint-unreachable'],
            )
        except Exception:
            check.log.debug('Failed to report the OpenMetrics endpoint-unreachable issue', exc_info=True)

    @staticmethod
    def resolve(check: AgentCheck, endpoint: str | None, namespace: str = '') -> None:
        """Resolve the issue associated with an endpoint."""
        if _endpoint_details(endpoint) is None:
            check.log.debug('Cannot resolve an OpenMetrics endpoint-unreachable issue without a valid endpoint')
            return

        issue_id = _issue_id(check.hostname, check.name, endpoint, namespace)
        try:
            check.resolve_issue(issue_id)
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

    port = explicit_port or (443 if scheme == 'https' else 80)
    if not 1 <= port <= 65535:
        return None

    display_host = f'[{host}]' if ':' in host else host
    sanitized_netloc = display_host if explicit_port is None else f'{display_host}:{explicit_port}'
    sanitized = urlunsplit((scheme, sanitized_netloc, parsed.path, '', ''))

    raw_userinfo, separator, _ = parsed.netloc.rpartition('@')
    secrets = set()
    if separator:
        secrets.add(raw_userinfo)
        secrets.update(unquote(part) for part in raw_userinfo.split(':', 1) if part)
    if parsed.query:
        secrets.add(parsed.query)
        secrets.update(value for _, value in parse_qsl(parsed.query, keep_blank_values=True) if value)

    return EndpointDetails(
        sanitized=sanitized,
        host=host,
        port=port,
        path=parsed.path or '/',
        secrets=frozenset(secrets),
        query=parsed.query,
    )


def _classify_error(error: BaseException) -> tuple[bool, str]:
    pending = deque([error])
    seen: set[int] = set()
    messages: list[str] = []
    errno_match = False

    while pending:
        current = pending.popleft()
        if id(current) in seen:
            continue
        seen.add(id(current))

        try:
            message = str(current)
        except Exception:
            message = current.__class__.__name__
        if message:
            messages.append(message)

        if isinstance(current, OSError) and current.errno == errno.EHOSTUNREACH:
            errno_match = True

        linked = (current.__cause__, current.__context__, getattr(current, 'reason', None), *current.args)
        pending.extend(value for value in linked if isinstance(value, BaseException))

    flattened = ': '.join(messages) or error.__class__.__name__
    fallback = f'[Errno {errno.EHOSTUNREACH}]' in flattened
    return errno_match or fallback, flattened


def _issue_id(hostname: str, check_name: str, endpoint: str, namespace: str) -> str:
    identity = json.dumps((hostname, check_name, endpoint, namespace), separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'openmetrics-endpoint-unreachable:{digest}'


def _sanitize_error_message(message: str, endpoint: str, details: EndpointDetails) -> str:
    sanitized = message.replace(endpoint, details.sanitized)
    if details.query:
        sanitized = sanitized.replace(f'?{details.query}', '')
    for secret in sorted(details.secrets, key=len, reverse=True):
        sanitized = sanitized.replace(secret, '[redacted]')
    return sanitized


def _remediation(check_name: str, details: EndpointDetails) -> dict[str, str | list[dict[str, int | str]]]:
    return {
        'summary': REMEDIATION_SUMMARY,
        'steps': [
            {
                'order': 1,
                'text': (
                    f'If {details.host} is a Kubernetes Pod IP, confirm it still belongs to a live pod. '
                    f'Run: kubectl get pods -A -o wide --field-selector=status.podIP={details.host}. '
                    'If no live pod owns it, inspect agent configcheck and fix stale Autodiscovery.'
                ),
            },
            {
                'order': 2,
                'text': (
                    'Test from the reporting Agent or Cluster Check Runner network namespace. '
                    f"Run: curl -sv --connect-timeout 5 '{details.sanitized}'."
                ),
            },
            {
                'order': 3,
                'text': (
                    f'Verify the target listener is on port {details.port} and bound to the pod or host interface or '
                    '0.0.0.0. For Envoy, test /stats/prometheus locally.'
                ),
            },
            {
                'order': 4,
                'text': (
                    'If the endpoint is locally reachable, inspect firewall and security groups, Kubernetes '
                    'NetworkPolicy or Cilium policy, and cross-node CNI routing.'
                ),
            },
            {
                'order': 5,
                'text': (
                    f'From the same runner, use Run: agent check {check_name}. The issue resolves automatically after '
                    'the endpoint becomes reachable.'
                ),
            },
        ],
    }
