# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest

from datadog_checks.base.checks.kube_leader import ElectionRecordAnnotation
from datadog_checks.kube_scheduler import KubeSchedulerCheck

from .common import HERE

# Constants
CHECK_NAME = 'kube_scheduler'


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(HERE, 'fixtures', 'metrics_1.29.0.txt')
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


def test_check_metrics_1_29(aggregator, mock_metrics, mock_leader, instance):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric("{}.{}".format(CHECK_NAME, name), **kwargs)

    assert_metric('pod_preemption.attempts', value=3.0, tags=[])

    assert_metric('scheduling.algorithm_duration.count', value=7, tags=['upper_bound:0.001'])
    assert_metric('scheduling.algorithm_duration.sum', value=0.0009387479999999999)

    assert_metric('schedule_attempts', value=7.0, tags=['profile:default-scheduler', 'result:scheduled'])
    assert_metric('schedule_attempts', value=3.0, tags=['profile:default-scheduler', 'result:unschedulable'])

    assert_metric('scheduling.attempt_duration.sum', value=0.00046745799999999997, tags=[])
    assert_metric(
        'scheduling.attempt_duration.count',
        value=7.0,
        tags=['profile:default-scheduler', 'result:scheduled', 'upper_bound:none'],
    )
    assert_metric(
        'scheduling.attempt_duration.count',
        value=3.0,
        tags=['profile:default-scheduler', 'result:unschedulable', 'upper_bound:none'],
    )

    assert_metric('scheduling.pod.scheduling_duration.sum', value=0.020339625, tags=['attempts:1'])
    assert_metric('scheduling.pod.scheduling_duration.sum', value=3.902187669, tags=['attempts:2'])
    assert_metric('scheduling.pod.scheduling_duration.count', value=4.0, tags=['attempts:1', 'upper_bound:none'])
    assert_metric('scheduling.pod.scheduling_duration.count', value=3.0, tags=['attempts:2', 'upper_bound:none'])

    assert_metric('scheduling.pod.scheduling_attempts.sum', value=10.0)
    assert_metric('scheduling.pod.scheduling_attempts.count', value=7.0)

    assert_metric(
        'client.http.requests_duration.count',
        tags=['host:172.18.0.2:6443', 'upper_bound:8.0', 'verb:GET'],
    )
    assert_metric(
        'client.http.requests_duration.sum',
        value=19.906190381000048,
        tags=['host:172.18.0.2:6443', 'verb:GET'],
    )

    assert_metric(
        'pod_preemption.victims.sum',
        value=0.0,
        tags=[],
    )

    assert_metric(
        'pod_preemption.victims.count',
        value=0.0,
        tags=[],
    )

    assert_metric('pending_pods', value=0.0, tags=['queue:active'])
    assert_metric('pending_pods', value=0.0, tags=['queue:backoff'])
    assert_metric('pending_pods', value=0.0, tags=['queue:unschedulable'])

    assert_metric('queue.incoming_pods', value=7.0, tags=['event:PodAdd', 'queue:active'])
    assert_metric('queue.incoming_pods', value=3.0, tags=['event:NodeTaintChange', 'queue:active'])
    assert_metric('queue.incoming_pods', value=3.0, tags=['event:ScheduleAttemptFailure', 'queue:unschedulable'])

    assert_metric('goroutines')
    assert_metric('gc_duration_seconds.sum')
    assert_metric('gc_duration_seconds.count')
    assert_metric('gc_duration_seconds.quantile')
    assert_metric('threads')
    assert_metric('open_fds')
    assert_metric('max_fds')
    assert_metric('client.http.requests')

    expected_le_tags = ["record_kind:endpoints", "record_name:kube-scheduler", "record_namespace:kube-system"]
    assert_metric('leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(CHECK_NAME + ".leader_election.status", tags=expected_le_tags)

    assert_metric('goroutine_by_scheduling_operation', value=0, tags=['operation:Filter'])
    assert_metric('goroutine_by_scheduling_operation', value=0, tags=['operation:binding'])

    aggregator.assert_all_metrics_covered()
