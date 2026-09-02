# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.metric_limit_issue import ISSUE_NAME, _issue_id

ENDPOINT = 'http://example.test/metrics'
ISSUE_ID = 'openmetrics-dropped-config:5505571e531f7cf6'


class GenericLimitedCheck(AgentCheck):
    """A non-OpenMetrics check that exceeds its metric limit.

    This verifies that AgentCheck does not report an Agent Health issue by
    default; only OpenMetrics checks do so by overriding _on_metric_limit_state.
    """

    def check(self, _: Any) -> None:
        for value in range(12):
            self.gauge('generic.metric', value)


class MetricLimitOpenMetricsCheck(OpenMetricsBaseCheckV2):
    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)
        self.observed = 0

    def configure_scrapers(self) -> None:
        self.scrapers = {config.get('openmetrics_endpoint', ''): None for config in self.scraper_configs}

    def check(self, _: Any) -> None:
        for value in range(self.observed):
            self.gauge('openmetrics.metric', value)


class IsolatedMetricLimitOpenMetricsCheck(MetricLimitOpenMetricsCheck):
    """Submits a fixed number of contexts.

    The isolated child process reconstructs the check from serialized configuration
    alone, so parent-object attributes such as ``observed`` do not reach it.
    """

    def check(self, _: Any) -> None:
        for value in range(20):
            self.gauge('openmetrics.metric', value)


def create_check(limit: int = 5, endpoint: str = ENDPOINT) -> MetricLimitOpenMetricsCheck:
    instance = {
        'openmetrics_endpoint': endpoint,
        'namespace': 'demo',
        'max_returned_metrics': limit,
    }
    return MetricLimitOpenMetricsCheck('openmetrics_test', {}, [instance])


def reported_issues(datadog_agent: Any) -> list[dict[str, Any]]:
    return datadog_agent._sent_reported_issues['openmetrics_test']


def test_generic_agent_check_metric_limiter_does_not_report(datadog_agent: Any) -> None:
    check = GenericLimitedCheck('generic', {}, [{'max_returned_metrics': 2}])

    assert check.run() == ''

    assert not datadog_agent._sent_reported_issues


def test_over_limit_run_reports_expected_issue(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20

    assert check.run() == ''

    [issue] = reported_issues(datadog_agent)
    assert issue['id'] == ISSUE_ID
    assert issue['issue_name'] == ISSUE_NAME
    assert issue['issue_type'] == 'openmetrics_metrics_dropped_by_configured_limit'
    assert issue['category'] == 'integration'
    assert issue['severity'] == check.IssueSeverity['HIGH']
    assert issue['extra'] == {
        'check_name': 'openmetrics_test',
        'endpoints': [ENDPOINT],
        'effective_limit': 5,
        'observed_contexts': 20,
        'dropped_contexts': 15,
        'dropped_ratio': 0.75,
        'limit_is_default': False,
    }
    assert issue['tags'] == ['integration:openmetrics_test', 'openmetrics', 'metric-limit']
    assert len(issue['remediation']['steps']) == 4

    verify_step = issue['remediation']['steps'][2]['text']
    # The Fleet UI renders remediation text as plain text, so the config key must
    # be described as nested (not as a dotted single-line key, which the check does
    # not parse) and both emitted metric names must be spelled out in full.
    assert 'debug_metrics.metric_contexts: true' not in verify_step
    assert 'metric_contexts to true under the debug_metrics section' in verify_step
    assert 'datadog.agent.metrics.contexts.total' in verify_step
    assert 'datadog.agent.metrics.contexts.limit' in verify_step


def test_repeated_over_limit_runs_report_same_id(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20

    check.run()
    check.run()

    assert [issue['id'] for issue in reported_issues(datadog_agent)] == [ISSUE_ID, ISSUE_ID]


def test_one_dropped_metric_reports_low_severity(datadog_agent: Any) -> None:
    check = create_check(limit=100)
    check.observed = 101

    check.run()

    [issue] = reported_issues(datadog_agent)
    assert issue['severity'] == check.IssueSeverity['LOW']
    assert issue['extra']['dropped_contexts'] == 1


@pytest.mark.parametrize(
    ('observed', 'limit', 'severity'),
    [
        pytest.param(1000, 990, 'LOW', id='low'),
        pytest.param(200, 190, 'MEDIUM', id='medium'),
        pytest.param(40, 30, 'HIGH', id='high'),
    ],
)
def test_severity_thresholds(datadog_agent: Any, observed: int, limit: int, severity: str) -> None:
    check = create_check(limit=limit)
    check.observed = observed

    check.run()

    [issue] = reported_issues(datadog_agent)
    assert issue['severity'] == check.IssueSeverity[severity]


def test_resolves_on_first_clean_run(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20
    check.run()

    check.observed = 5
    check.run()

    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


def test_clean_runs_resolve_idempotently(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 5

    check.run()
    check.run()

    assert datadog_agent._sent_resolved_issues == [ISSUE_ID, ISSUE_ID]


def test_recurrence_after_resolution_reports_same_id(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20
    check.run()

    check.observed = 5
    check.run()

    check.observed = 20
    check.run()

    assert [issue['id'] for issue in reported_issues(datadog_agent)] == [ISSUE_ID, ISSUE_ID]
    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


def test_failed_run_does_not_resolve_active_issue(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20
    check.run()

    check.check = mock.Mock(side_effect=RuntimeError('scrape failure'))
    error_report = check.run()

    assert 'scrape failure' in error_report
    assert datadog_agent._sent_resolved_issues == []


@pytest.mark.parametrize(
    ('hostname', 'check_name', 'endpoint', 'namespace'),
    [
        pytest.param('other.hostname', 'openmetrics_test', ENDPOINT, 'demo', id='hostname'),
        pytest.param('stubbed.hostname', 'other_openmetrics_test', ENDPOINT, 'demo', id='check-name'),
        pytest.param(
            'stubbed.hostname', 'openmetrics_test', 'http://other.example.test/metrics', 'demo', id='endpoint'
        ),
        pytest.param('stubbed.hostname', 'openmetrics_test', ENDPOINT, 'other', id='namespace'),
    ],
)
def test_issue_id_changes_with_identity_component(
    hostname: str, check_name: str, endpoint: str, namespace: str
) -> None:
    base_id = _issue_id('stubbed.hostname', 'openmetrics_test', (ENDPOINT,), 'demo')

    assert _issue_id(hostname, check_name, (endpoint,), namespace) != base_id


def test_issue_id_does_not_include_metric_limit(datadog_agent: Any) -> None:
    first_check = create_check(limit=5)
    first_check.observed = 20
    first_check.run()
    first_id = reported_issues(datadog_agent)[0]['id']

    second_check = create_check(limit=10)
    second_check.observed = 25
    second_check.run()
    second_id = reported_issues(datadog_agent)[1]['id']

    assert first_check.metric_limiter.limit != second_check.metric_limiter.limit
    assert first_id == second_id == ISSUE_ID


def test_report_issue_failure_does_not_break_limiter_reset_or_next_run(aggregator: Any) -> None:
    check = create_check(limit=2)
    check.observed = 12
    check.report_issue = mock.Mock(side_effect=RuntimeError('bridge failure'))

    assert check.run() == ''
    assert check.metric_limiter.reached_limit is False
    assert len(aggregator.metrics('openmetrics.metric')) == 2

    check.observed = 2
    assert check.run() == ''
    assert check.metric_limiter.reached_limit is False
    assert len(aggregator.metrics('openmetrics.metric')) == 4


def test_missing_endpoint_does_nothing(datadog_agent: Any, caplog: Any) -> None:
    check = create_check(endpoint='')
    check.observed = 20

    with caplog.at_level('DEBUG'):
        check.run()

    assert not datadog_agent._sent_reported_issues
    assert datadog_agent._sent_resolved_issues == []
    assert 'without an endpoint' in caplog.text


def test_isolated_parent_does_not_invoke_metric_limit_state(datadog_agent: Any) -> None:
    check = create_check()
    check.instance['process_isolation'] = True
    check._on_metric_limit_state = mock.Mock()

    with mock.patch('datadog_checks.base.utils.replay.execute.run_with_isolation'):
        assert check.run() == ''

    check._on_metric_limit_state.assert_not_called()


def test_isolated_check_reports_metric_limit_issue(datadog_agent: Any) -> None:
    """The over-limit condition is observed by the isolated child process, whose
    report_issue call is replayed back to this process through the Agent stub."""
    check = IsolatedMetricLimitOpenMetricsCheck(
        'openmetrics_test',
        {},
        [
            {
                'openmetrics_endpoint': ENDPOINT,
                'namespace': 'demo',
                'max_returned_metrics': 5,
                'process_isolation': True,
            }
        ],
    )
    check.check_id = 'test:123'

    assert check.run() == ''

    # The parent never submitted metrics, so its limiter stayed untouched; the
    # issue below could only have been reported by the isolated child process.
    assert check.metric_limiter.count == 0

    [issue] = reported_issues(datadog_agent)
    assert issue['id'] == ISSUE_ID
    assert issue['issue_name'] == ISSUE_NAME
    assert issue['issue_type'] == 'openmetrics_metrics_dropped_by_configured_limit'
    assert issue['extra']['observed_contexts'] == 20
    assert issue['extra']['dropped_contexts'] == 15
    assert datadog_agent._sent_resolved_issues == []
