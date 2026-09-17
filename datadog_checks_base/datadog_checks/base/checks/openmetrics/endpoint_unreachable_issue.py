# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import errno
import hashlib
import json
from collections import deque
from dataclasses import dataclass
from ipaddress import ip_address
from re import compile
from shlex import quote
from threading import Lock
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

from requests.exceptions import ProxyError as RequestsProxyError
from urllib3.exceptions import ProxyError as Urllib3ProxyError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from datadog_checks.base.checks import AgentCheck

ISSUE_NAME = 'OpenMetrics Endpoint Unreachable'
ISSUE_TYPE = 'openmetrics_endpoint_unreachable'
ISSUE_ID_PREFIX = 'openmetrics-endpoint-unreachable'
ERROR_MESSAGE = 'No route to host'
WSAEHOSTUNREACH = getattr(errno, 'WSAEHOSTUNREACH', 10065)
HOST_UNREACHABLE_ERRNOS = frozenset((errno.EHOSTUNREACH, WSAEHOSTUNREACH))
PROXY_ERROR_TYPES = (RequestsProxyError, Urllib3ProxyError)
SAFE_CHECK_NAME = compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')

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


@dataclass(frozen=True)
class TrackedIssue:
    issue_id: str
    endpoint: str
    namespace: str


class ReporterState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.cancelled = False
        self.issues: dict[str, TrackedIssue] = {}


STATE_ATTRIBUTE = '_openmetrics_endpoint_unreachable_issue_state'
STATE_INITIALIZATION_LOCK = Lock()


class EndpointUnreachableIssueReporter:
    @staticmethod
    def report(check: AgentCheck, endpoint: str | None, error: BaseException, namespace: str = '') -> None:
        """Report an issue when an endpoint failure means no route to host."""
        try:
            details = _endpoint_details(endpoint)
            if details is None:
                _debug(check, 'Cannot report an OpenMetrics endpoint-unreachable issue without a valid endpoint')
                return

            if not _is_unreachable(error):
                return

            namespace = str(namespace)
            issue_id = _issue_id(check.hostname, check.name, endpoint, namespace)
            state = _state(check)
            with state.lock:
                if state.cancelled:
                    return

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
                    'error_message': ERROR_MESSAGE,
                },
                remediation=_remediation(check.name, details),
                tags=[f'integration:{check.name}', 'openmetrics', 'endpoint-unreachable'],
            )

            with state.lock:
                if state.cancelled:
                    resolve_after_cancel = True
                else:
                    state.issues[issue_id] = TrackedIssue(issue_id, endpoint, namespace)
                    resolve_after_cancel = False

            if resolve_after_cancel:
                _resolve_issue_id(check, issue_id)
        except Exception:
            _debug(check, 'Failed to report the OpenMetrics endpoint-unreachable issue', exc_info=True)

    @staticmethod
    def resolve(check: AgentCheck, endpoint: str | None, namespace: str = '') -> None:
        """Resolve the issue associated with an endpoint."""
        try:
            if _endpoint_details(endpoint) is None:
                _debug(check, 'Cannot resolve an OpenMetrics endpoint-unreachable issue without a valid endpoint')
                return

            namespace = str(namespace)
            issue_id = _issue_id(check.hostname, check.name, endpoint, namespace)
            state = _state(check)
            with state.lock:
                tracked_issue = state.issues.get(issue_id)

            if not _resolve_issue_id(check, issue_id):
                return

            with state.lock:
                if state.issues.get(issue_id) is tracked_issue:
                    state.issues.pop(issue_id, None)
        except Exception:
            _debug(check, 'Failed to resolve the OpenMetrics endpoint-unreachable issue', exc_info=True)

    @staticmethod
    def resolve_stale(check: AgentCheck, active_endpoint_namespaces: Iterable[tuple[str, str]]) -> None:
        """Resolve tracked issues whose exact endpoint context is no longer active."""
        try:
            active = {(endpoint, str(namespace)) for endpoint, namespace in active_endpoint_namespaces}
            state = _state(check)
            with state.lock:
                stale_issues = tuple(
                    issue for issue in state.issues.values() if (issue.endpoint, issue.namespace) not in active
                )

            for issue in stale_issues:
                if not _resolve_issue_id(check, issue.issue_id):
                    continue
                with state.lock:
                    if state.issues.get(issue.issue_id) is issue:
                        state.issues.pop(issue.issue_id, None)
        except Exception:
            _debug(check, 'Failed to resolve stale OpenMetrics endpoint-unreachable issues', exc_info=True)

    @staticmethod
    def cancel(check: AgentCheck) -> bool:
        """Mark the check cancelled and best-effort resolve every exactly tracked issue."""
        try:
            state = _state(check)
            with state.lock:
                state.cancelled = True
                tracked_issues = tuple(state.issues.values())
                state.issues.clear()

            for issue in tracked_issues:
                _resolve_issue_id(check, issue.issue_id)
            return bool(tracked_issues)
        except Exception:
            _debug(check, 'Failed to cancel OpenMetrics endpoint-unreachable issue reporting', exc_info=True)
            return False


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

    display_host = f'[{host}]' if ':' in host else host
    sanitized_netloc = display_host if explicit_port is None else f'{display_host}:{explicit_port}'
    path = parsed.path or '/'
    sanitized = urlunsplit((scheme, sanitized_netloc, path, '', ''))

    return EndpointDetails(
        sanitized=sanitized,
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


def _state(check: AgentCheck) -> ReporterState:
    # Read the instance dict directly so mocks and custom checks cannot synthesize this private attribute.
    state = vars(check).get(STATE_ATTRIBUTE)
    if state is not None:
        return state

    with STATE_INITIALIZATION_LOCK:
        state = vars(check).get(STATE_ATTRIBUTE)
        if state is None:
            state = ReporterState()
            setattr(check, STATE_ATTRIBUTE, state)
        return state


def _resolve_issue_id(check: AgentCheck, issue_id: str) -> bool:
    try:
        check.resolve_issue(issue_id)
    except Exception:
        _debug(check, 'Failed to resolve the OpenMetrics endpoint-unreachable issue', exc_info=True)
        return False
    return True


def _debug(check: AgentCheck, message: str, *, exc_info: bool = False) -> None:
    try:
        check.log.debug(message, exc_info=exc_info)
    except Exception:
        pass


def _remediation(check_name: str, details: EndpointDetails) -> dict[str, str | list[dict[str, int | str]]]:
    try:
        target_address = ip_address(details.host)
        if getattr(target_address, 'scope_id', None) is not None:
            raise ValueError
        target_ip = str(target_address)
    except ValueError:
        target_step = (
            'Confirm the endpoint target still exists. If it came from Autodiscovery, inspect and correct stale '
            'configuration. Run: agent configcheck'
        )
    else:
        target_step = (
            f'If {target_ip} is a Kubernetes Pod IP, confirm it still belongs to a live pod. If no live pod owns it, '
            'inspect agent configcheck and fix stale Autodiscovery. To list matching pods, run: '
            f'kubectl get pods -A -o wide --field-selector=status.podIP={quote(target_ip)}'
        )

    if SAFE_CHECK_NAME.fullmatch(check_name):
        verification_step = (
            'The issue resolves automatically after the endpoint becomes reachable. To verify from the same reporting '
            f'Agent or Cluster Check Runner, run: agent check {check_name}'
        )
    else:
        verification_step = (
            'The issue resolves automatically after the endpoint becomes reachable. Re-run this integration check '
            'from the same reporting Agent or Cluster Check Runner.'
        )

    return {
        'summary': REMEDIATION_SUMMARY,
        'steps': [
            {
                'order': 1,
                'text': target_step,
            },
            {
                'order': 2,
                'text': (
                    'Test from the reporting Agent or Cluster Check Runner network namespace. '
                    f'Run: curl -sv --connect-timeout 5 {quote(details.sanitized)}'
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
                'text': verification_step,
            },
        ],
    }
