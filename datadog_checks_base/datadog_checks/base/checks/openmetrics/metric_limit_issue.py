# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base.checks import AgentCheck

REPORT_FLOOR = 10
RESOLVE_AFTER_CLEAN_RUNS = 3
SEVERITY_HIGH_RATIO = 0.25
SEVERITY_MEDIUM_RATIO = 0.05

ISSUE_NAME = 'OpenMetrics Metrics Dropped By Configured Limit'


@dataclass
class MetricLimitIssueReporter:
    legacy: bool
    clean_runs: int = 0
    store_synchronized: bool = False
    active: bool = False

    def handle(
        self,
        check: AgentCheck,
        endpoint: str | None,
        reached_limit: bool,
        observed: int,
        limit: int,
    ) -> None:
        """Report or resolve an OpenMetrics configured-limit issue for one check run."""
        if not endpoint:
            check.log.debug('Cannot handle the OpenMetrics metric limit state without an endpoint')
            return

        issue_id = _issue_id(endpoint, check.instance.get('namespace', ''))

        if reached_limit:
            self.clean_runs = 0
            dropped = max(0, observed - limit)
            if dropped < REPORT_FLOOR:
                return

            ratio = dropped / observed
            check.report_issue(
                id=issue_id,
                issue_name=ISSUE_NAME,
                title=f'Dropping {dropped} of {observed} metrics from {endpoint}',
                description=(
                    f'The {check.name} check collecting {endpoint} is configured to submit at most {limit} metric '
                    f'contexts per run, but the last collection produced {observed}. The Agent submitted {limit} and '
                    f'discarded the remaining {dropped}. Because the order of collection can change between runs, the '
                    'discarded metrics are not always the same ones, so dashboards and monitors built on this endpoint '
                    'may show intermittent gaps rather than a consistently missing set of metrics.'
                ),
                category='configuration',
                severity=_severity(check, ratio),
                extra={
                    'check_name': check.name,
                    'endpoint': endpoint,
                    'effective_limit': limit,
                    'observed_contexts': observed,
                    'dropped_contexts': dropped,
                    'dropped_ratio': round(ratio, 4),
                    'limit_is_default': limit == check.DEFAULT_METRIC_LIMIT,
                },
                remediation=_remediation(check.name, endpoint, dropped, observed, legacy=self.legacy),
                tags=[f'integration:{check.name}', 'openmetrics', 'metric-limit'],
            )
            self.active = True
            self.store_synchronized = True
            return

        self.clean_runs += 1
        if not self.store_synchronized:
            check.resolve_issue(issue_id)
            self.store_synchronized = True
            return

        if self.active and self.clean_runs >= RESOLVE_AFTER_CLEAN_RUNS:
            check.resolve_issue(issue_id)
            self.active = False
            self.clean_runs = 0


def _issue_id(endpoint: str, namespace: object) -> str:
    digest = hashlib.sha256(f'{endpoint}|{namespace}'.encode('utf-8')).hexdigest()[:16]
    return f'openmetrics-dropped-config:{digest}'


def _severity(check: AgentCheck, ratio: float) -> int:
    if ratio >= SEVERITY_HIGH_RATIO:
        return check.IssueSeverity['HIGH']
    if ratio >= SEVERITY_MEDIUM_RATIO:
        return check.IssueSeverity['MEDIUM']
    return check.IssueSeverity['LOW']


def _remediation(
    check_name: str, endpoint: str, dropped: int, observed: int, *, legacy: bool
) -> dict[str, str | list[dict[str, int | str]]]:
    metric_filter_options = '`metrics` / `ignore_metrics`' if legacy else '`metrics` / `exclude_metrics`'
    return {
        'summary': (
            "Reduce what this endpoint sends to Datadog, or raise this instance's metric limit after checking the cost."
        ),
        'steps': [
            {
                'order': 1,
                'text': (
                    f'Confirm the loss is real and current: this issue reports {dropped} of {observed} metric '
                    f'contexts discarded on the most recent run of {check_name} against {endpoint}.'
                ),
            },
            {
                'order': 2,
                'text': (
                    f'Decide what you actually need. Use {metric_filter_options} on this instance to stop collecting '
                    'series you do not query, alert on, or keep. This is the only remediation that reduces both data '
                    'loss and cost.'
                ),
            },
            {
                'order': 3,
                'text': (
                    'Reduce label cardinality where you can: `exclude_labels`, or dropping high-cardinality labels '
                    'at the exporter, cuts context count faster than removing whole metrics.'
                ),
            },
            {
                'order': 4,
                'text': (
                    'If the endpoint aggregates several workloads, split it into multiple check instances so each '
                    'one stays under its own limit.'
                ),
            },
            {
                'order': 5,
                'text': (
                    'Only then raise `max_returned_metrics` on this instance, to a value above the observed count '
                    'with modest headroom. Set it per instance; there is no Agent-wide override.'
                ),
            },
            {
                'order': 6,
                'text': (
                    'Verify: enable `debug_metrics.metric_contexts: true` on the instance to publish '
                    '`datadog.agent.metrics.contexts.total` and `.limit`, and confirm the total stays below the limit '
                    'at peak. Consider a monitor at 80% of the limit.'
                ),
            },
            {
                'order': 7,
                'text': (
                    'Check the cost before you leave it: additional contexts are billable custom metrics, and they '
                    'increase Agent memory and check duration.'
                ),
            },
        ],
    }
