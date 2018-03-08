# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import mock

# 3p
from prometheus_client import generate_latest, CollectorRegistry, Gauge

# project
from datadog_checks.prometheus import PrometheusCheck

instance = {
    'prometheus_url': 'http://localhost:10249/metrics',
    'namespace': 'prometheus',
    'metrics': [
        {'metric1': 'renamed.metric1'},
        'metric2'
    ],
    'send_histograms_buckets': True
}

# Constants
CHECK_NAME = 'prometheus'
NAMESPACE = 'prometheus'

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator

@pytest.fixture(scope="module")
def poll_mock():
    registry = CollectorRegistry()
    # pylint: disable=E1123,E1101
    g1 = Gauge('metric1', 'processor usage', ['matched_label', 'node', 'flavor'], registry=registry)
    g1.labels(matched_label="foobar", node="host1", flavor="test").set(99.9)
    g2 = Gauge('metric2', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g2.labels(matched_label="foobar", node="host2", timestamp="123").set(12.2)

    poll_mock = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: generate_latest(registry).split("\n"),
            headers={'Content-Type': "text/plain"}
        )
    )
    yield poll_mock.start()
    poll_mock.stop()

def test_prometheus_check(aggregator, poll_mock):
    """
    Testing prometheus check.
    """

    c = PrometheusCheck('prometheus', None, {}, [instance])
    c.check(instance)
    aggregator.assert_metric(CHECK_NAME + '.renamed.metric1', tags=['node:host1', 'flavor:test', 'matched_label:foobar'])
    aggregator.assert_metric(CHECK_NAME + '.metric2', tags=['timestamp:123', 'node:host2', 'matched_label:foobar'])
    assert aggregator.metrics_asserted_pct == 100.0

def test_prometheus_wildcard(aggregator, poll_mock):
    instance_wildcard = {
        'prometheus_url': 'http://localhost:10249/metrics',
        'namespace': 'prometheus',
        'metrics': ['metric*'],
    }

    c = PrometheusCheck('prometheus', None, {}, [instance_wildcard])
    c.check(instance)
    aggregator.assert_metric(CHECK_NAME + '.metric1', tags=['node:host1', 'flavor:test', 'matched_label:foobar'])
    aggregator.assert_metric(CHECK_NAME + '.metric2', tags=['timestamp:123', 'node:host2', 'matched_label:foobar'])
    assert aggregator.metrics_asserted_pct == 100.0

def test_prometheus_default_instance(aggregator, poll_mock):
    """
    Testing prometheus with default instance
    """

    c = PrometheusCheck(CHECK_NAME, None, {}, [], default_instances={
        'prometheus': {
            'prometheus_url': 'http://localhost:10249/metrics',
            'namespace': 'prometheus',
            'metrics': [
                {'metric1': 'renamed.metric1'},
                'metric2'
            ]
        }},
        default_namespace='prometheus')
    c.check({
        'prometheus_url': 'http://custom:1337/metrics',
    })
    aggregator.assert_metric(CHECK_NAME + '.renamed.metric1', tags=['node:host1', 'flavor:test', 'matched_label:foobar'])
    aggregator.assert_metric(CHECK_NAME + '.metric2', tags=['timestamp:123', 'node:host2', 'matched_label:foobar'])
    assert aggregator.metrics_asserted_pct == 100.0

def test_prometheus_mixed_instance(aggregator, poll_mock):
    """
    Testing prometheus with default instance
    """

    c = PrometheusCheck(CHECK_NAME, None, {}, [], default_instances={
        'foobar': {
            'prometheus_url': 'http://localhost:10249/metrics',
            'namespace': 'foobar',
            'metrics': [
                'metric3',
                'metric4'
            ]
        }, 'prometheus': {
            'prometheus_url': 'http://localhost:10249/metrics',
            'namespace': 'prometheus',
            'metrics': [
                'metric2'
            ],
            'label_joins': {
                'metric2': {
                    'label_to_match': 'matched_label',
                    'labels_to_get': ['timestamp']
                },
            },
            'tags': ['extra:bar']
        }},
        default_namespace='prometheus')
    # run the check twice for label joins
    for _ in range(2):
        c.check({
            'prometheus_url': 'http://custom:1337/metrics',
            'namespace': 'prometheus',
            'metrics': [
                {'metric1': 'renamed.metric1'}
            ],
            'label_joins': {
                'renamed.metric1': {
                    'label_to_match': 'matched_label',
                    'labels_to_get': ['flavor']
                },
            },
            'label_to_hostname':'node',
            'tags': ['extra:foo']
        })
    aggregator.assert_metric(CHECK_NAME + '.renamed.metric1', hostname="host1", tags=['node:host1', 'flavor:test', 'matched_label:foobar', 'timestamp:123', 'extra:foo'])
    aggregator.assert_metric(CHECK_NAME + '.metric2', hostname="host2", tags=['timestamp:123', 'node:host2', 'matched_label:foobar', 'timestamp:123', 'extra:foo'])
    assert aggregator.metrics_asserted_pct == 100.0
