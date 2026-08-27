# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from datadog_checks.base.checks import AgentCheck

SEVERITY_HIGH_RATIO = 0.25
SEVERITY_MEDIUM_RATIO = 0.05

ISSUE_NAME = 'OpenMetrics Metrics Dropped By Configured Limit'
ISSUE_TYPE = 'openmetrics_metrics_dropped_by_configured_limit'


@dataclass
class MetricLimitIssueReporter:
    filter_option_text: str

    def handle(
        self,
        check: AgentCheck,
        endpoints: Iterable[str | None] | None,
        reached_limit: bool,
        observed_count: int,
        limit: int,
    ) -> None:
        """Report or resolve one configured-limit issue for an OpenMetrics check run."""
        endpoints = _normalize_endpoints(endpoints or ())
        if not endpoints:
            check.log.debug('Cannot handle the OpenMetrics metric limit state without an endpoint')
            return

        issue_id = _issue_id(check.hostname, check.name, endpoints, check.instance.get('namespace', ''))

        if reached_limit:
            dropped = max(0, observed_count - limit)
            ratio = dropped / observed_count
            title, description = _issue_text(check.name, endpoints, limit, observed_count, dropped)
            check.report_issue(
                id=issue_id,
                issue_name=ISSUE_NAME,
                issue_type=ISSUE_TYPE,
                title=title,
                description=description,
                category='integration',
                severity=_severity(check, ratio),
                extra={
                    'check_name': check.name,
                    'endpoints': list(endpoints),
                    'effective_limit': limit,
                    'observed_contexts': observed_count,
                    'dropped_contexts': dropped,
                    'dropped_ratio': round(ratio, 4),
                    'limit_is_default': limit == check.DEFAULT_METRIC_LIMIT,
                },
                remediation=_remediation(filter_option_text=self.filter_option_text),
                tags=[f'integration:{check.name}', 'openmetrics', 'metric-limit'],
            )
            return

        check.resolve_issue(issue_id)


def _normalize_endpoints(endpoints: Iterable[str | None]) -> tuple[str, ...]:
    return tuple(sorted({endpoint for endpoint in endpoints if endpoint}))


def _issue_id(hostname: str, check_name: str, endpoints: tuple[str, ...], namespace: object) -> str:
    # Keep the original identity for one endpoint while representing multiple endpoints structurally.
    endpoint_identity: str | list[str] = endpoints[0] if len(endpoints) == 1 else list(endpoints)
    identity = json.dumps((hostname, check_name, endpoint_identity, str(namespace)), separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'openmetrics-dropped-config:{digest}'


def _issue_text(
    check_name: str, endpoints: tuple[str, ...], limit: int, observed_count: int, dropped: int
) -> tuple[str, str]:
    endpoint_count = len(endpoints)
    endpoint_noun = 'endpoint' if endpoint_count == 1 else 'endpoints'
    title = f'Dropping {dropped} of {observed_count} OpenMetrics metrics'
    description = (
        f'The {check_name} check collected {observed_count} metric contexts from {endpoint_count} configured '
        f'{endpoint_noun}: {", ".join(endpoints)}. These totals cover the complete check run. The check is configured '
        f'to submit at most {limit} metric contexts per run, so the Agent submitted {limit} and discarded the '
        f'remaining {dropped}.'
    )
    return title, description


def _severity(check: AgentCheck, ratio: float) -> int:
    if ratio >= SEVERITY_HIGH_RATIO:
        return check.IssueSeverity['HIGH']
    if ratio >= SEVERITY_MEDIUM_RATIO:
        return check.IssueSeverity['MEDIUM']
    return check.IssueSeverity['LOW']


def _remediation(*, filter_option_text: str) -> dict[str, str | list[dict[str, int | str]]]:
    return {
        'summary': (
            "Reduce what this endpoint sends to Datadog, or raise this instance's metric limit after checking the cost."
        ),
        'steps': [
            {
                'order': 1,
                'text': (
                    f'Decide what you actually need. Use {filter_option_text} on this instance to stop collecting '
                    'series you do not query, alert on, or keep.'
                ),
            },
            {
                'order': 2,
                'text': 'Only then raise max_returned_metrics on this instance to a value above the observed count.',
            },
            {
                'order': 3,
                'text': (
                    'Verify: on the instance, set metric_contexts to true under the debug_metrics section. '
                    'This publishes datadog.agent.metrics.contexts.total and '
                    'datadog.agent.metrics.contexts.limit; confirm the total stays below the limit at peak. '
                    'Consider a monitor at 80% of the limit.'
                ),
            },
            {
                'order': 4,
                'text': (
                    'Check the cost before you leave it: additional contexts are billable custom metrics and increase '
                    'Agent memory.'
                ),
            },
        ],
    }
