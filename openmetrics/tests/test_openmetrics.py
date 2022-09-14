# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import PY2

from datadog_checks.openmetrics import OpenMetricsCheck

from .common import CHECK_NAME

pytestmark = pytest.mark.usefixtures("poll_mock")

instance = {
    'prometheus_url': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1_total'],
    'send_histograms_buckets': True,
    'send_monotonic_counter': True,
}
instance_new = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1', 'counter2'],
    'collect_histogram_buckets': True,
}


def test_openmetrics_check(dd_run_check, aggregator):
    c = OpenMetricsCheck('openmetrics', {}, [instance])
    dd_run_check(c)
    aggregator.assert_metric(
        CHECK_NAME + '.renamed.metric1',
        tags=['node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        CHECK_NAME + '.metric2',
        tags=['timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        CHECK_NAME + '.counter1_total', tags=['node:host2'], metric_type=aggregator.MONOTONIC_COUNT
    )
    aggregator.assert_all_metrics_covered()


def test_openmetrics_check_counter_gauge(dd_run_check, aggregator):
    instance['send_monotonic_counter'] = False
    c = OpenMetricsCheck('openmetrics', {}, [instance])
    dd_run_check(c)
    aggregator.assert_metric(
        CHECK_NAME + '.renamed.metric1',
        tags=['node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        CHECK_NAME + '.metric2',
        tags=['timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(CHECK_NAME + '.counter1_total', tags=['node:host2'], metric_type=aggregator.GAUGE)
    aggregator.assert_all_metrics_covered()


def test_invalid_metric(dd_run_check, aggregator):
    """
    Testing that invalid values of metrics are discarded
    """
    bad_metric_instance = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'openmetrics',
        'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'metric3'],
        'send_histograms_buckets': True,
    }
    c = OpenMetricsCheck('openmetrics', {}, [bad_metric_instance])
    dd_run_check(c)
    assert aggregator.metrics('metric3') == []


def test_openmetrics_wildcard(dd_run_check, aggregator):
    instance_wildcard = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'openmetrics',
        'metrics': ['metric*'],
    }

    c = OpenMetricsCheck('openmetrics', {}, [instance_wildcard])
    dd_run_check(c)
    aggregator.assert_metric(
        CHECK_NAME + '.metric1',
        tags=['node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        CHECK_NAME + '.metric2',
        tags=['timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_all_metrics_covered()


@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_linkerd_v2_new(aggregator, dd_run_check):
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

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
