# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.metric_limit_issue import (
    ISSUE_NAME,
    RESOLVE_AFTER_CLEAN_RUNS,
    MetricLimitIssueReporter,
)

ENDPOINT = 'http://example.test/metrics'
ISSUE_ID = 'openmetrics-dropped-config:81b0b5348322bbd4'


class GenericLimitedCheck(AgentCheck):
    def check(self, _: Any) -> None:
        for value in range(12):
            self.gauge('generic.metric', value)


class MetricLimitOpenMetricsCheck(OpenMetricsBaseCheckV2):
    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)
        self.observed = 0

    def configure_scrapers(self) -> None:
        pass

    def check(self, _: Any) -> None:
        for value in range(self.observed):
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


def test_reporter_is_explicitly_owned_by_openmetrics_base_classes(datadog_agent: Any) -> None:
    check = create_check()
    assert isinstance(check.metric_limit_issue_reporter, MetricLimitIssueReporter)
    assert check.metric_limit_issue_reporter.legacy is False

    legacy_check = OpenMetricsBaseCheck('legacy_openmetrics_test', {}, {})
    assert isinstance(legacy_check.metric_limit_issue_reporter, MetricLimitIssueReporter)
    assert legacy_check.metric_limit_issue_reporter.legacy is True

    check.observed = 20
    check.run()
    assert not hasattr(check, '_openmetrics_metric_limit_issue_state')


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
    assert issue['severity'] == check.IssueSeverity['HIGH']
    assert issue['extra'] == {
        'check_name': 'openmetrics_test',
        'endpoint': ENDPOINT,
        'effective_limit': 5,
        'observed_contexts': 20,
        'dropped_contexts': 15,
        'dropped_ratio': 0.75,
        'limit_is_default': False,
    }
    assert issue['tags'] == ['integration:openmetrics_test', 'openmetrics', 'metric-limit']
    assert len(issue['remediation']['steps']) == 7


def test_repeated_over_limit_runs_report_same_id(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20

    check.run()
    check.run()

    assert [issue['id'] for issue in reported_issues(datadog_agent)] == [ISSUE_ID, ISSUE_ID]


def test_dropped_below_report_floor_does_not_report(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 14

    check.run()

    assert reported_issues(datadog_agent) == []


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


def test_resolves_after_consecutive_clean_runs(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20
    check.run()

    check.observed = 5
    for _ in range(RESOLVE_AFTER_CLEAN_RUNS - 1):
        check.run()
    assert datadog_agent._sent_resolved_issues == []

    check.run()
    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]

    check.run()
    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


def test_first_clean_run_unconditionally_resolves(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 5

    check.run()
    check.run()

    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


def test_recurrence_after_resolution_reports_same_id(datadog_agent: Any) -> None:
    check = create_check()
    check.observed = 20
    check.run()

    check.observed = 5
    for _ in range(RESOLVE_AFTER_CLEAN_RUNS):
        check.run()

    check.observed = 20
    check.run()

    assert [issue['id'] for issue in reported_issues(datadog_agent)] == [ISSUE_ID, ISSUE_ID]
    assert datadog_agent._sent_resolved_issues == [ISSUE_ID]


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
