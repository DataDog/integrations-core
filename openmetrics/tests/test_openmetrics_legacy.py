# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.openmetrics import OpenMetricsCheck

from .common import CHECK_NAME

pytestmark = pytest.mark.usefixtures("prometheus_poll_mock")

instance = {
    'prometheus_url': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1_total'],
    'send_histograms_buckets': True,
    'send_monotonic_counter': True,
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
