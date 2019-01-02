# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import mock

from datadog_checks.base.checks.kube_leader import ElectionRecord

from datadog_checks.kube_controller_manager import KubeControllerManagerCheck

instance = {
    'prometheus_url': 'http://localhost:10252/metrics',
    'extra_queues': ['extra'],
    'extra_limiters': ['extra_controller'],
    'tags': ['te:st']
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


@pytest.fixture()
def mock_leader():
    # Inject a fake object in the leader-election monitoring logic
    mocked = mock.patch(
        'datadog_checks.kube_controller_manager.KubeControllerManagerCheck._get_record',
        return_value=ElectionRecord(
            '{"holderIdentity":"pod1","leaseDurationSeconds":15,"leaderTransitions":3,' +
            '"acquireTime":"2018-12-19T18:23:24Z","renewTime":"2019-01-02T16:30:07Z"}'
        ),
    )
    yield mocked.start()
    mocked.stop()

def test_check_metrics(aggregator, mock_metrics, mock_leader):
    c = KubeControllerManagerCheck(CHECK_NAME, None, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.goroutines')
    assert_metric('.threads')
    assert_metric('.open_fds')

    assert_metric('.nodes.evictions', metric_type=aggregator.MONOTONIC_COUNT, value=33, tags=["zone:test", "te:st"])
    assert_metric('.nodes.count', value=5, tags=["zone:test", "te:st"])
    assert_metric('.nodes.unhealthy', value=1, tags=["zone:test", "te:st"])

    assert_metric('.rate_limiter.use', value=1, tags=["limiter:job_controller", "te:st"])
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:daemon_controller", "te:st"])

    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=29, tags=["queue:replicaset", "te:st"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=3, tags=["queue:service", "te:st"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=13, tags=["queue:deployment", "te:st"])

    assert_metric('.queue.work_duration.sum', value=255667, tags=["queue:replicaset", "te:st"])
    assert_metric('.queue.work_duration.count', value=29, tags=["queue:replicaset", "te:st"])
    assert_metric('.queue.work_duration.quantile', value=110, tags=["queue:replicaset", "quantile:0.5", "te:st"])

    assert_metric('.queue.latency.sum', value=423889, tags=["queue:deployment", "te:st"])
    assert_metric('.queue.latency.count', value=29, tags=["queue:deployment", "te:st"])
    assert_metric('.queue.latency.quantile', value=1005, tags=["queue:deployment", "quantile:0.9", "te:st"])

    # Extra name from the instance
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:extra_controller", "te:st"])
    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=13, tags=["queue:extra", "te:st"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=2, tags=["queue:extra", "te:st"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=55, tags=["queue:extra", "te:st"])
    assert_metric('.queue.work_duration.sum', value=45171, tags=["queue:extra", "te:st"])
    assert_metric('.queue.work_duration.count', value=13, tags=["queue:extra", "te:st"])
    assert_metric('.queue.work_duration.quantile', value=6, tags=["queue:extra", "quantile:0.5", "te:st"])
    assert_metric('.queue.latency.sum', value=9309, tags=["queue:extra", "te:st"])
    assert_metric('.queue.latency.count', value=13, tags=["queue:extra", "te:st"])
    assert_metric('.queue.latency.quantile', value=10, tags=["queue:extra", "quantile:0.9", "te:st"])

    # Leader election mixin
    expected_le_tags = [
        "record_kind:endpoints",
        "record_name:kube-controller-manager",
        "record_namespace:kube-system",
        "te:st",
    ]

    assert_metric('.leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('.leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(NAMESPACE + ".leader_election.status", tags=expected_le_tags)
