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
METRICS_COMMON = [
    NAMESPACE + '.renamed.metric1',
    NAMESPACE + '.metric2'
]

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
    g1.labels(matched_label="foobar", node="localhost", flavor="test").set(99.9)
    g2 = Gauge('metric2', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g2.labels(matched_label="foobar", node="localhost", timestamp="123").set(12.2)

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
    for metric in METRICS_COMMON:
        aggregator.assert_metric(metric, tags=[])
    assert aggregator.metrics_asserted_pct == 100.0
