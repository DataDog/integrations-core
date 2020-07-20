# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.prometheus import PrometheusCheck

# Constants
CHECK_NAME = 'prometheus'
NAMESPACE = 'prometheus'


def test_prometheus_check(aggregator, instance, poll_mock):
    """
    Testing prometheus check.
    """

    c = PrometheusCheck('prometheus', None, {}, [instance])
    c.check(instance)
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
    assert aggregator.metrics_asserted_pct == 100.0


def test_prometheus_check_counter_gauge(aggregator, instance, poll_mock):
    """
    Testing prometheus check.
    """

    instance["send_monotonic_counter"] = False
    c = PrometheusCheck('prometheus', None, {}, [instance])
    c.check(instance)
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
    assert aggregator.metrics_asserted_pct == 100.0


def test_invalid_metric(aggregator, poll_mock):
    """
    Testing that invalid values of metrics are discarded
    """
    bad_metric_instance = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'prometheus',
        'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'metric3'],
        'send_histograms_buckets': True,
    }
    c = PrometheusCheck('prometheus', None, {}, [bad_metric_instance])
    c.check(bad_metric_instance)
    assert aggregator.metrics('metric3') == []


def test_prometheus_wildcard(aggregator, instance, poll_mock):
    instance_wildcard = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'prometheus',
        'metrics': ['metric*'],
    }

    c = PrometheusCheck('prometheus', None, {}, [instance_wildcard])
    c.check(instance)
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
    assert aggregator.metrics_asserted_pct == 100.0


def test_prometheus_default_instance(aggregator, poll_mock):
    """
    Testing prometheus with default instance
    """

    c = PrometheusCheck(
        CHECK_NAME,
        None,
        {},
        [],
        default_instances={
            'prometheus': {
                'prometheus_url': 'http://localhost:10249/metrics',
                'namespace': 'prometheus',
                'metrics': [{'metric1': 'renamed.metric1'}, 'metric2'],
            }
        },
        default_namespace='prometheus',
    )
    c.check({'prometheus_url': 'http://custom:1337/metrics'})
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
    assert aggregator.metrics_asserted_pct == 100.0


def test_prometheus_mixed_instance(aggregator, poll_mock):
    """
    Testing prometheus with default instance
    """

    c = PrometheusCheck(
        CHECK_NAME,
        None,
        {},
        [],
        default_instances={
            'foobar': {
                'prometheus_url': 'http://localhost:10249/metrics',
                'namespace': 'foobar',
                'metrics': ['metric3', 'metric4'],
            },
            'prometheus': {
                'prometheus_url': 'http://localhost:10249/metrics',
                'namespace': 'prometheus',
                'metrics': ['metric2'],
                'label_joins': {'metric2': {'label_to_match': 'matched_label', 'labels_to_get': ['timestamp']}},
                'tags': ['extra:bar'],
            },
        },
        default_namespace='prometheus',
    )
    # run the check twice for label joins
    for _ in range(2):
        c.check(
            {
                'prometheus_url': 'http://custom:1337/metrics',
                'namespace': 'prometheus',
                'metrics': [{'metric1': 'renamed.metric1'}],
                'label_joins': {'renamed.metric1': {'label_to_match': 'matched_label', 'labels_to_get': ['flavor']}},
                'label_to_hostname': 'node',
                'tags': ['extra:foo'],
            }
        )
    aggregator.assert_metric(
        CHECK_NAME + '.renamed.metric1',
        hostname="host1",
        tags=['node:host1', 'flavor:test', 'matched_label:foobar', 'timestamp:123', 'extra:foo'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        CHECK_NAME + '.metric2',
        hostname="host2",
        tags=['timestamp:123', 'node:host2', 'matched_label:foobar', 'timestamp:123', 'extra:foo'],
        metric_type=aggregator.GAUGE,
    )
    assert aggregator.metrics_asserted_pct == 100.0


def test_integration(aggregator, dd_environment):
    c = PrometheusCheck('prometheus', None, {}, [dd_environment])
    c.check(dd_environment)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.sum', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.count', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.quantile', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.go_memstats_mallocs_total', metric_type=aggregator.MONOTONIC_COUNT)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check, e2e_instance):
    aggregator = dd_agent_check(e2e_instance, rate=True)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.sum', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.count', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.quantile', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.go_memstats_mallocs_total', metric_type=aggregator.COUNT)

    aggregator.assert_all_metrics_covered()
