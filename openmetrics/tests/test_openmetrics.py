# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import PY2

from datadog_checks.openmetrics import OpenMetricsCheck

from .common import CHECK_NAME

pytestmark = [
    pytest.mark.skipif(PY2, reason='Test only available on Python 3'),
]

instance_new = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1', 'counter2'],
    'collect_histogram_buckets': True,
}

instance_new_strict = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1'],
    'collect_histogram_buckets': True,
    'use_latest_spec': True,
}


@pytest.mark.parametrize('poll_mock_fixture', ['poll_mock', 'strict_poll_mock'])
def test_openmetrics(aggregator, dd_run_check, request, poll_mock_fixture):
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

    request.getfixturevalue(poll_mock_fixture)

    check = OpenMetricsCheck('openmetrics', {}, [instance_new])
    scraper = OpenMetricsScraper(check, instance_new)
    dd_run_check(check)

    aggregator.assert_metric(
        '{}.renamed.metric1'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.metric2'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.counter1.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_metric(
        '{}.counter2.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_all_metrics_covered()

    assert check.http.options['headers']['Accept'] == '*/*'
    assert scraper.http.options['headers']['Accept'] == (
        'application/openmetrics-text;version=1.0.0,application/openmetrics-text;version=0.0.1;q=0.75,'
        'text/plain;version=0.0.4;q=0.5,*/*;q=0.1'
    )


@pytest.mark.usefixtures("strict_poll_mock")
def test_openmetrics_strict(aggregator, dd_run_check, caplog):
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

    check = OpenMetricsCheck('openmetrics', {}, [instance_new_strict])
    scraper = OpenMetricsScraper(check, instance_new_strict)
    dd_run_check(check)

    aggregator.assert_metric(
        '{}.renamed.metric1'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.metric2'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.counter1.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_all_metrics_covered()

    assert check.http.options['headers']['Accept'] == '*/*'
    assert caplog.text == ''
    assert scraper.http.options['headers']['Accept'] == (
        'application/openmetrics-text;version=1.0.0,application/openmetrics-text;version=0.0.1'
    )
