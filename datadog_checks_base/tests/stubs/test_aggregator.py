# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


@pytest.mark.parametrize(
    'case_name, metrics, expect_assertion_error',
    [
        (
            "no duplicate with different metric",
            [
                dict(name="metric.a", value=1, tags=['aa'], hostname='1'),
                dict(name="metric.b", value=1, tags=['aa'], hostname='1'),
            ],
            False,
        ),
        (
            "no duplicate with different tag",
            [
                dict(name="metric.a", value=1, tags=['aa'], hostname='1'),
                dict(name="metric.a", value=1, tags=['bb'], hostname='1'),
            ],
            False,
        ),
        (
            "no duplicate with different hostname",
            [
                dict(name="metric.a", value=1, tags=['aa'], hostname='1'),
                dict(name="metric.a", value=1, tags=['aa'], hostname='2'),
            ],
            False,
        ),
        (
            "duplicate metric",
            [
                dict(name="metric.a", value=1, tags=['aa'], hostname='1'),
                dict(name="metric.a", value=1, tags=['aa'], hostname='1'),
            ],
            True,
        ),
        (
            "duplicate metric with different values",
            [
                dict(name="metric.a", value=1, tags=['aa'], hostname='1'),
                dict(name="metric.a", value=2, tags=['aa'], hostname='1'),
            ],
            True,
        ),
    ],
)
def test_assert_no_duplicate_cases(aggregator, case_name, metrics, expect_assertion_error):
    check = AgentCheck()

    for metric_params in metrics:
        check.gauge(**metric_params)

    try:
        aggregator.assert_no_duplicate_metric()
        assertion_error_raised = False
    except AssertionError:
        assertion_error_raised = True

    assert assertion_error_raised == expect_assertion_error


def test_assert_no_duplicate_message(aggregator):
    check = AgentCheck()
    check.gauge('check.metric.dup1', 1, tags=['aa'])
    check.gauge('check.metric.dup1', 2, tags=['aa'])
    check.gauge('check.metric.dup2', 3, tags=['aa'])
    check.gauge('check.metric.dup2', 4, tags=['aa'])
    check.gauge('check.metric.no_dup1', 5, tags=['aa'])
    check.gauge('check.metric.no_dup2', 6, tags=['aa'])

    actual_msg = ""
    try:
        aggregator.assert_no_duplicate_metric()
    except AssertionError as e:
        actual_msg = str(e)

    expected_msg = '''
Duplicate metrics found:
  - check.metric.dup1
      MetricStub(name='check.metric.dup1', type=0, value=1.0, tags=['aa'], hostname='')
      MetricStub(name='check.metric.dup1', type=0, value=2.0, tags=['aa'], hostname='')
  - check.metric.dup2
      MetricStub(name='check.metric.dup2', type=0, value=3.0, tags=['aa'], hostname='')
      MetricStub(name='check.metric.dup2', type=0, value=4.0, tags=['aa'], hostname='')
assert 2 == 0
'''
    print("\n===\n{}\n===\n".format(expected_msg.strip()))
    print("\n===\n{}\n===\n".format(actual_msg.strip()))
    assert expected_msg.strip() == actual_msg.strip()
