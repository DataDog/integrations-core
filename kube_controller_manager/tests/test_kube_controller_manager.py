# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.kube_controller_manager import KubeControllerManagerCheck

import os
import pytest
import mock


instance = {
    'prometheus_url': 'http://localhost:10252/metrics',
    'extra_queues': ['extra'],
    'extra_limiters': ['extra_controller'],
}

# Constants
CHECK_NAME = 'kube_controller_manager'
NAMESPACE = 'kube_controller_manager'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    mocked = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: text_data.split("\n"),
            headers={'Content-Type': "text/plain"}
        ),
    )
    yield mocked.start()
    mocked.stop()


def test_check_metrics(aggregator, mock_metrics):
    c = KubeControllerManagerCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.goroutines')
    assert_metric('.threads')
    assert_metric('.open_fds')

    assert_metric('.nodes.evictions', metric_type=aggregator.MONOTONIC_COUNT, value=33, tags=["zone:test"])
    assert_metric('.nodes.count', value=5, tags=["zone:test"])
    assert_metric('.nodes.unhealthy', value=1, tags=["zone:test"])

    assert_metric('.rate_limiter.use', value=1, tags=["limiter:job_controller"])
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:daemon_controller"])

    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=29, tags=["queue:replicaset"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=3, tags=["queue:service"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=13, tags=["queue:deployment"])

    assert_metric('.queue.work_duration.sum', value=255667, tags=["queue:replicaset"])
    assert_metric('.queue.work_duration.count', value=29, tags=["queue:replicaset"])
    assert_metric('.queue.work_duration.quantile', value=110, tags=["queue:replicaset", "quantile:0.5"])

    assert_metric('.queue.latency.sum', value=423889, tags=["queue:deployment"])
    assert_metric('.queue.latency.count', value=29, tags=["queue:deployment"])
    assert_metric('.queue.latency.quantile', value=1005, tags=["queue:deployment", "quantile:0.9"])

    # Extra name from the instance
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:extra_controller"])
    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=13, tags=["queue:extra"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=2, tags=["queue:extra"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=55, tags=["queue:extra"])
    assert_metric('.queue.work_duration.sum', value=45171, tags=["queue:extra"])
    assert_metric('.queue.work_duration.count', value=13, tags=["queue:extra"])
    assert_metric('.queue.work_duration.quantile', value=6, tags=["queue:extra", "quantile:0.5"])
    assert_metric('.queue.latency.sum', value=9309, tags=["queue:extra"])
    assert_metric('.queue.latency.count', value=13, tags=["queue:extra"])
    assert_metric('.queue.latency.quantile', value=10, tags=["queue:extra", "quantile:0.9"])
