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

instance_unavailable = {
    'openmetrics_endpoint': 'http://127.0.0.1:4243/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1'],
    'ignore_connection_errors': True,
}


@pytest.mark.parametrize('poll_mock_fixture', ['prometheus_poll_mock', 'openmetrics_poll_mock'])
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
    assert scraper.http.options['headers']['Accept'] == 'text/plain'


def test_openmetrics_use_latest_spec(aggregator, dd_run_check, mock_http_response, openmetrics_payload, caplog):
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

    # We want to make sure that when `use_latest_spec` is enabled, we use the OpenMetrics parser
    # even when the response's `Content-Type` doesn't declare the appropriate media type.
    mock_http_response(openmetrics_payload, normalize_content=False)

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


def test_openmetrics_empty_response(aggregator, dd_run_check, mock_http_response, openmetrics_payload, caplog):
    mock_http_response("")

    check = OpenMetricsCheck('openmetrics', {}, [instance_new])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()


def test_openmetrics_endpoint_unavailable(aggregator, dd_run_check):
    check = OpenMetricsCheck('openmetrics', {}, [instance_unavailable])
    dd_run_check(check)

    # Collects no metrics without error.
    aggregator.assert_all_metrics_covered()
