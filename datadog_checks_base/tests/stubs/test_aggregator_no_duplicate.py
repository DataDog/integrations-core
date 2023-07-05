# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from textwrap import dedent

import pytest

from datadog_checks.base import AgentCheck


def test_assert_no_duplicate_message(aggregator):
    check = AgentCheck()
    check.gauge('check.metric.dup1', 1, tags=['aa'])
    check.gauge('check.metric.dup1', 2, tags=['aa'])
    check.gauge('check.metric.dup2', 3, tags=['aa'])
    check.gauge('check.metric.dup2', 4, tags=['aa'])
    check.gauge('check.metric.no_dup1', 5, tags=['aa'])
    check.gauge('check.metric.no_dup2', 6, tags=['aa'])

    actual_msg = "  "
    try:
        aggregator.assert_no_duplicate_metrics()
    except AssertionError as e:
        actual_msg += str(e).split("assert")[0].lstrip()
    actual_msg = dedent(actual_msg)

    expected_msg = '''
Duplicate metrics found:
- check.metric.dup1
    MetricStub(name='check.metric.dup1', type=0, value=1.0, tags=['aa'], hostname='', device=None, flush_first_value=False)
    MetricStub(name='check.metric.dup1', type=0, value=2.0, tags=['aa'], hostname='', device=None, flush_first_value=False)
- check.metric.dup2
    MetricStub(name='check.metric.dup2', type=0, value=3.0, tags=['aa'], hostname='', device=None, flush_first_value=False)
    MetricStub(name='check.metric.dup2', type=0, value=4.0, tags=['aa'], hostname='', device=None, flush_first_value=False)
'''  # noqa: E501
    assert expected_msg.strip() == actual_msg.strip()


@pytest.mark.parametrize(
    'case_name, metrics, expect_assertion_error',
    [
        (
            'no duplicate with different metric name',
            [
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'gauge', 'name': 'metric.b', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
            ],
            False,
        ),
        (
            'no duplicate with different metric type',
            [
                {'type': 'rate', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
            ],
            False,
        ),
        (
            'no duplicate with different tag',
            [
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['bb'], 'hostname': '1'},
            ],
            False,
        ),
        (
            'no duplicate with different hostname',
            [
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '2'},
            ],
            False,
        ),
        (
            'duplicate allowed for types intended to be submitted multiple times',
            [
                {'type': 'count', 'name': 'metric.count', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'count', 'name': 'metric.count', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'increment', 'name': 'metric.increment', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'increment', 'name': 'metric.increment', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'decrement', 'name': 'metric.decrement', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'decrement', 'name': 'metric.decrement', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
            ],
            False,
        ),
        (
            'duplicate gauge metric',
            [
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
            ],
            True,
        ),
        (
            'duplicate rate metric',
            [
                {'type': 'rate', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'rate', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
            ],
            True,
        ),
        (
            'duplicate monotonic_count metric',
            [
                {'type': 'monotonic_count', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'monotonic_count', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
            ],
            True,
        ),
        (
            'duplicate metric with different values',
            [
                {'type': 'gauge', 'name': 'metric.a', 'value': 1, 'tags': ['aa'], 'hostname': '1'},
                {'type': 'gauge', 'name': 'metric.a', 'value': 2, 'tags': ['aa'], 'hostname': '1'},
            ],
            True,
        ),
    ],
)
def test_assert_no_duplicate_metrics_cases(aggregator, case_name, metrics, expect_assertion_error):
    check = AgentCheck()

    for metric_params in metrics:
        metric_type = metric_params.pop("type")
        getattr(check, metric_type)(**metric_params)

    msg = ''
    try:
        aggregator.assert_no_duplicate_metrics()
        assertion_error_raised = False
    except AssertionError as e:
        assertion_error_raised = True
        msg = str(e)

    assert assertion_error_raised == expect_assertion_error, msg


@pytest.mark.parametrize(
    'case_name, service_checks, expect_assertion_error',
    [
        (
            "no duplicate with different name",
            [
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '1'},
                {'name': "service.check.b", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '1'},
            ],
            False,
        ),
        (
            "no duplicate with different tag",
            [
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '1'},
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['bb'], 'hostname': '1'},
            ],
            False,
        ),
        (
            "no duplicate with different hostname",
            [
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '1'},
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '2'},
            ],
            False,
        ),
        (
            "duplicate metric",
            [
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '1'},
                {'name': "service.check.a", 'status': AgentCheck.OK, 'tags': ['aa'], 'hostname': '1'},
            ],
            True,
        ),
    ],
)
def test_assert_no_duplicate_service_checks_cases(aggregator, case_name, service_checks, expect_assertion_error):
    check = AgentCheck()

    for metric_params in service_checks:
        check.service_check(**metric_params)

    try:
        aggregator.assert_no_duplicate_service_checks()
        assertion_error_raised = False
    except AssertionError:
        assertion_error_raised = True

    assert assertion_error_raised == expect_assertion_error
