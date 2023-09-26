# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.kube_leader import ElectionRecordAnnotation
from datadog_checks.kube_controller_manager import KubeControllerManagerCheck

instance = {
    'prometheus_url': 'http://localhost:10252/metrics',
    'extra_queues': ['extra'],
    'extra_limiters': ['extra_controller'],
    'ignore_deprecated': False,
}

instance2 = {
    'prometheus_url': 'http://localhost:10252/metrics',
    'extra_queues': ['extra'],
    'extra_limiters': ['extra_controller'],
    'ignore_deprecated': True,
}

# Constants
CHECK_NAME = 'kube_controller_manager'
NAMESPACE = 'kube_controller_manager'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


@pytest.fixture()
def mock_leader():
    # Inject a fake object in the leader-election monitoring logic
    with mock.patch(
        'datadog_checks.kube_controller_manager.KubeControllerManagerCheck._get_record',
        return_value=ElectionRecordAnnotation(
            "endpoints",
            '{"holderIdentity":"pod1","leaseDurationSeconds":15,"leaderTransitions":3,'
            + '"acquireTime":"2018-12-19T18:23:24Z","renewTime":"2019-01-02T16:30:07Z"}',
        ),
    ):
        yield


def test_check_metrics_with_deprecated(aggregator, mock_metrics, mock_leader):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    generic_check_metrics(aggregator, True)


def test_check_metrics_without_deprecated(aggregator, mock_metrics, mock_leader):
    c = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])
    c.check(instance2)

    generic_check_metrics(aggregator, False)


def generic_check_metrics(aggregator, check_deprecated):
    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.goroutines')
    assert_metric('.threads')
    assert_metric('.open_fds')
    assert_metric('.client.http.requests')
    assert_metric('.max_fds')

    assert_metric('.nodes.evictions', metric_type=aggregator.MONOTONIC_COUNT, value=1, tags=["zone:test"])
    assert_metric('.nodes.evictions', metric_type=aggregator.MONOTONIC_COUNT, value=3, tags=["zone:test-total"])
    assert_metric('.nodes.count', value=5, tags=["zone:test"])
    assert_metric('.nodes.unhealthy', value=1, tags=["zone:test"])

    assert_metric('.rate_limiter.use', value=1, tags=["limiter:job_controller"])
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:daemon_controller"])

    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=238.0, tags=["queue:replicaset"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=29, tags=["queue:service"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=1283, tags=["queue:deployment"])

    if check_deprecated:
        assert_metric('.queue.work_duration.sum', value=2124279, tags=["queue:replicaset"])
        assert_metric('.queue.work_duration.count', value=238, tags=["queue:replicaset"])
        assert_metric('.queue.work_duration.quantile', value=144, tags=["queue:replicaset", "quantile:0.5"])

        assert_metric('.queue.latency.sum', value=1953629, tags=["queue:deployment"])
        assert_metric('.queue.latency.count', value=1454, tags=["queue:deployment"])
        assert_metric('.queue.latency.quantile', value=15195, tags=["queue:deployment", "quantile:0.9"])

    # Extra name from the instance
    assert_metric('.rate_limiter.use', value=0, tags=["limiter:extra_controller"])
    assert_metric('.queue.adds', metric_type=aggregator.MONOTONIC_COUNT, value=99.0, tags=["queue:daemonset"])
    assert_metric('.queue.depth', metric_type=aggregator.GAUGE, value=0, tags=["queue:daemonset"])
    assert_metric('.queue.retries', metric_type=aggregator.MONOTONIC_COUNT, value=4, tags=["queue:daemonset"])

    # Metrics from 1.14
    assert_metric('.queue.work_longest_duration', value=2, tags=["queue:daemonset"])
    assert_metric('.queue.work_unfinished_duration', value=1, tags=["queue:daemonset"])
    assert_metric('.queue.process_duration.count', value=51.0, tags=["queue:daemonset", "upper_bound:0.001"])
    assert_metric('.queue.process_duration.sum', value=0.7717836519999999, tags=["queue:daemonset"])
    assert_metric('.queue.queue_duration.count', value=99.0, tags=["queue:daemonset", "upper_bound:none"])
    assert_metric('.queue.queue_duration.sum', value=0.3633380879999999, tags=["queue:daemonset"])

    # Metrics from 1.26
    assert_metric('.job_controller.terminated_pods_tracking_finalizer', value=6, tags=["event:add"])
    assert_metric('.job_controller.terminated_pods_tracking_finalizer', value=6, tags=["event:delete"])

    # Leader election mixin
    expected_le_tags = ["record_kind:endpoints", "record_name:kube-controller-manager", "record_namespace:kube-system"]
    assert_metric('.leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('.leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(NAMESPACE + ".leader_election.status", tags=expected_le_tags)

    aggregator.assert_all_metrics_covered()


def test_service_check_ok(monkeypatch):
    instance = {'prometheus_url': 'http://localhost:10252/metrics'}
    instance_tags = []

    check = KubeControllerManagerCheck(CHECK_NAME, {}, [instance])

    monkeypatch.setattr(check, 'service_check', mock.Mock())

    calls = [
        mock.call('kube_controller_manager.up', AgentCheck.OK, tags=instance_tags),
        mock.call('kube_controller_manager.up', AgentCheck.CRITICAL, tags=instance_tags, message='health check failed'),
    ]

    # successful health check
    with mock.patch("requests.get", return_value=mock.MagicMock(status_code=200)):
        check._perform_service_check(instance)

    # failed health check
    raise_error = mock.Mock()
    raise_error.side_effect = requests.HTTPError('health check failed')
    with mock.patch("requests.get", return_value=mock.MagicMock(raise_for_status=raise_error)):
        check._perform_service_check(instance)

    check.service_check.assert_has_calls(calls)
