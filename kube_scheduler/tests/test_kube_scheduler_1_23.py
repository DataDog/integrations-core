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
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics_1.23.6.txt')
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
            "endpoints",
            '{"holderIdentity":"pod1","leaseDurationSeconds":15,"leaderTransitions":3,'
            + '"acquireTime":"2018-12-19T18:23:24Z","renewTime":"2019-01-02T16:30:07Z"}',
        ),
    ):
        yield


def test_check_metrics_1_23(aggregator, mock_metrics, mock_leader):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.pod_preemption.attempts', value=3.0, tags=[])

    assert_metric('.scheduling.algorithm_duration.count', value=7, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.algorithm_duration.sum', value=0.002138012)

    assert_metric('.scheduling.e2e_scheduling_duration.sum', value=0.000195006)
    assert_metric(
        '.scheduling.e2e_scheduling_duration.count',
        value=7.0,
        tags=['profile:default-scheduler', 'result:scheduled', 'upper_bound:none'],
    )
    assert_metric(
        '.scheduling.e2e_scheduling_duration.count',
        value=3.0,
        tags=['profile:default-scheduler', 'result:unschedulable', 'upper_bound:none'],
    )

    assert_metric('.schedule_attempts', value=7.0, tags=['profile:default-scheduler', 'result:scheduled'])
    assert_metric('.schedule_attempts', value=3.0, tags=['profile:default-scheduler', 'result:unschedulable'])

    assert_metric('.scheduling.attempt_duration.sum', value=0.000195006, tags=[])
    assert_metric(
        '.scheduling.attempt_duration.count',
        value=7.0,
        tags=['profile:default-scheduler', 'result:scheduled', 'upper_bound:none'],
    )
    assert_metric(
        '.scheduling.attempt_duration.count',
        value=3.0,
        tags=['profile:default-scheduler', 'result:unschedulable', 'upper_bound:none'],
    )

    assert_metric('.scheduling.pod.scheduling_duration.sum', value=0.056623216, tags=['attempts:1'])
    assert_metric('.scheduling.pod.scheduling_duration.sum', value=20.781201637, tags=['attempts:2'])
    assert_metric('.scheduling.pod.scheduling_duration.count', value=4.0, tags=['attempts:1', 'upper_bound:none'])
    assert_metric('.scheduling.pod.scheduling_duration.count', value=3.0, tags=['attempts:2', 'upper_bound:none'])

    assert_metric('.scheduling.pod.scheduling_attempts.sum', value=10.0)
    assert_metric('.scheduling.pod.scheduling_attempts.count', value=7.0)

    assert_metric(
        '.client.http.requests_duration.count',
        tags=['url:https://172.18.0.2:6443/apis/events.k8s.io/v1', 'upper_bound:0.001', 'verb:GET'],
    )
    assert_metric(
        '.client.http.requests_duration.sum',
        value=0.022055548,
        tags=['url:https://172.18.0.2:6443/apis/events.k8s.io/v1', 'verb:GET'],
    )

    assert_metric(
        '.pod_preemption.victims.sum',
        value=2.0,
        tags=[],
    )

    assert_metric(
        '.pod_preemption.victims.count',
        value=2.0,
        tags=[],
    )

    assert_metric('.pending_pods', value=1.0, tags=['queue:active'])
    assert_metric('.pending_pods', value=2.0, tags=['queue:backoff'])
    assert_metric('.pending_pods', value=3.0, tags=['queue:unschedulable'])

    assert_metric('.queue.incoming_pods', value=7.0, tags=['event:PodAdd', 'queue:active'])
    assert_metric('.queue.incoming_pods', value=3.0, tags=['event:NodeTaintChange', 'queue:active'])
    assert_metric('.queue.incoming_pods', value=3.0, tags=['event:ScheduleAttemptFailure', 'queue:unschedulable'])

    assert_metric('.goroutines')
    assert_metric('.gc_duration_seconds.sum')
    assert_metric('.gc_duration_seconds.count')
    assert_metric('.gc_duration_seconds.quantile')
    assert_metric('.threads')
    assert_metric('.open_fds')
    assert_metric('.max_fds')
    assert_metric('.client.http.requests')

    expected_le_tags = ["record_kind:endpoints", "record_name:kube-scheduler", "record_namespace:kube-system"]
    assert_metric('.leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('.leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(NAMESPACE + ".leader_election.status", tags=expected_le_tags)

    aggregator.assert_all_metrics_covered()
