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
    metric_filter_config: str

    def handle(
        self,
        check: AgentCheck,
        endpoints: Iterable[str] | None,
        reached_limit: bool,
        observed_count: int,
        limit: int,
    ) -> None:
        """Report or resolve an OpenMetrics configured-limit issue for one check run.

        ``endpoints`` is any iterable of configured scraper endpoint strings. It is normalized to a
        deterministic, de-duplicated, sorted tuple and empty values are discarded; the call is a no-op
        if no endpoint remains. The metric limiter state is aggregate across the whole check run and
        cannot attribute drops to a single scraper, so exactly one issue is reported for the entire
        endpoint set rather than one per endpoint.
        """
        normalized = tuple(sorted({endpoint for endpoint in (endpoints or ()) if endpoint}))
        if not normalized:
            check.log.debug('Cannot handle the OpenMetrics metric limit state without an endpoint')
            return

        namespace = check.instance.get('namespace', '')
        # Preserve the original single-endpoint public issue id; for several endpoints hash the
        # structured ordered endpoint set rather than display text.
        issue_id = (
            _issue_id(check.hostname, check.name, normalized[0], namespace)
            if len(normalized) == 1
            else _issue_id_set(check.hostname, check.name, normalized, namespace)
        )

        if reached_limit:
            dropped = max(0, observed_count - limit)
            ratio = dropped / observed_count
            title, description = _describe(check, normalized, limit, observed_count, dropped)
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
                    'endpoints': list(normalized),
                    'effective_limit': limit,
                    'observed_contexts': observed_count,
                    'dropped_contexts': dropped,
                    'dropped_ratio': round(ratio, 4),
                    'limit_is_default': limit == check.DEFAULT_METRIC_LIMIT,
                },
                remediation=_remediation(metric_filter_config=self.metric_filter_config),
                tags=[f'integration:{check.name}', 'openmetrics', 'metric-limit'],
            )
            return

        check.resolve_issue(issue_id)


def _issue_id(hostname: str, check_name: str, endpoint: str, namespace: object) -> str:
    identity = json.dumps((hostname, check_name, endpoint, str(namespace)), separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'openmetrics-dropped-config:{digest}'


def _issue_id_set(hostname: str, check_name: str, endpoints: tuple[str, ...], namespace: object) -> str:
    """Identity for a multi-endpoint issue: hash the structured ordered endpoint set, not display text."""
    identity = json.dumps((hostname, check_name, list(endpoints), str(namespace)), separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16]
    return f'openmetrics-dropped-config:{digest}'


def _describe(
    check: AgentCheck, endpoints: tuple[str, ...], limit: int, observed_count: int, dropped: int
) -> tuple[str, str]:
    if len(endpoints) == 1:
        endpoint = endpoints[0]
        title = f'Dropping {dropped} of {observed_count} metrics from {endpoint}'
        description = (
            f'The {check.name} check collecting {endpoint} is configured to submit at most {limit} metric '
            f'contexts per run, but the last collection produced {observed_count}. The Agent submitted {limit} '
            f'and discarded the remaining {dropped}.'
        )
        return title, description

    endpoint_list = ', '.join(endpoints)
    count = len(endpoints)
    title = f'Dropping {dropped} of {observed_count} metrics across {count} endpoints'
    description = (
        f'The {check.name} check collects {count} endpoints: {endpoint_list}. It is configured to submit at '
        f'most {limit} metric contexts per run, and the last collection produced {observed_count} across all '
        f'{count} endpoints. The reported observed and dropped counts are combined across these endpoints and '
        f'cannot be attributed to a single one. The Agent submitted {limit} and discarded the remaining {dropped}.'
    )
    return title, description


def _severity(check: AgentCheck, ratio: float) -> int:
    if ratio >= SEVERITY_HIGH_RATIO:
        return check.IssueSeverity['HIGH']
    if ratio >= SEVERITY_MEDIUM_RATIO:
        return check.IssueSeverity['MEDIUM']
    return check.IssueSeverity['LOW']


def _remediation(*, metric_filter_config: str) -> dict[str, str | list[dict[str, int | str]]]:
    return {
        'summary': (
            "Reduce what this endpoint sends to Datadog, or raise this instance's metric limit after checking the cost."
        ),
        'steps': [
            {
                'order': 1,
                'text': (
                    f'Decide what you actually need. Use {metric_filter_config} on this instance to stop collecting '
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
