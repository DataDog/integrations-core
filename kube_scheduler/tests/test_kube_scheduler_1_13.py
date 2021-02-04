# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.base.checks.kube_leader import ElectionRecordAnnotation
from datadog_checks.kube_scheduler import KubeSchedulerCheck

instance = {'prometheus_url': 'http://localhost:10251/metrics', 'send_histograms_buckets': True}

# Constants
CHECK_NAME = 'kube_scheduler'
NAMESPACE = 'kube_scheduler'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_1.13.3.txt')
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
    # don't forget to update the [testenv] in tox.ini with the 'kube' dependency
    with mock.patch(
        'datadog_checks.kube_scheduler.KubeSchedulerCheck._get_record',
        return_value=ElectionRecordAnnotation(
            '{"holderIdentity":"pod1","leaseDurationSeconds":15,"leaderTransitions":3,'
            + '"acquireTime":"2018-12-19T18:23:24Z","renewTime":"2019-01-02T16:30:07Z"}'
        ),
    ):
        yield


def test_check_metrics_1_13(aggregator, mock_metrics, mock_leader):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.pod_preemption.victims', value=0.0, tags=[])
    assert_metric('.pod_preemption.attempts', value=10.0, tags=[])
    assert_metric('.binding_duration.count', value=0.0, tags=['upper_bound:0.001'])
    assert_metric('.binding_duration.sum', value=0.408376, tags=[])
    assert_metric('.scheduling.scheduling_duration.count', value=15.0, tags=['operation:binding'])
    assert_metric('.scheduling.scheduling_duration.sum', value=0.40872890000000006, tags=['operation:binding'])
    assert_metric('.scheduling.algorithm.predicate_duration.sum', value=0.00278, tags=[])
    assert_metric('.scheduling.e2e_scheduling_duration.count', value=0.0, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.algorithm_duration.count', value=14.0, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.e2e_scheduling_duration.sum', value=0.432862, tags=[])
    assert_metric(
        '.scheduling.scheduling_duration.quantile', value=0.0225032, tags=['operation:binding', 'quantile:0.5']
    )
    assert_metric('.scheduling.algorithm.priority_duration.sum', value=0.000237, tags=[])
    assert_metric('.scheduling.algorithm.priority_duration.count', value=15.0, tags=['upper_bound:0.004'])
    assert_metric('.scheduling.algorithm.preemption_duration.sum', value=0.051777, tags=[])
    assert_metric('.scheduling.algorithm.predicate_duration.count', value=15.0, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.algorithm.preemption_duration.count', value=0.0, tags=['upper_bound:0.001'])
    assert_metric('.schedule_attempts', value=15.0, tags=['result:scheduled'])
    assert_metric('.cache.lookups')
    assert_metric('.volume_scheduling_duration.sum', value=0.0003541, tags=['operation:assume'])
    assert_metric(
        '.client.http.requests_duration.count',
        tags=['url:https://172.17.0.2:6443/%7Bprefix%7D', 'upper_bound:0.001', 'verb:GET'],
    )
    assert_metric(
        '.client.http.requests_duration.sum',
        value=86.3256595999997,
        tags=['url:https://172.17.0.2:6443/%7Bprefix%7D', 'verb:GET'],
    )
    assert_metric('.goroutines')
    assert_metric('.gc_duration_seconds.sum')
    assert_metric('.gc_duration_seconds.count')
    assert_metric('.gc_duration_seconds.quantile')
    assert_metric('.threads')
    assert_metric('.open_fds')
    assert_metric('.max_fds')
    assert_metric('.client.http.requests')
    assert_metric(
        '.volume_scheduling_duration.count', value=15.0, tags=['operation:predicate', 'upper_bound:1024000.0']
    )
    # check historgram transformation from microsecond to second
    assert_metric('.scheduling.algorithm_duration.sum', value=0.006377, tags=[])
    # Leader election mixin
    expected_le_tags = ["record_kind:endpoints", "record_name:kube-scheduler", "record_namespace:kube-system"]
    assert_metric('.leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('.leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(NAMESPACE + ".leader_election.status", tags=expected_le_tags)
    aggregator.assert_all_metrics_covered()
