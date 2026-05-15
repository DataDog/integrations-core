# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.kube_leader import ElectionRecordAnnotation
from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.kube_scheduler import KubeSchedulerCheck

from .common import make_mock_metrics

instance = {'prometheus_url': 'http://localhost:10251/metrics', 'send_histograms_buckets': True}

# Constants
CHECK_NAME = 'kube_scheduler'
NAMESPACE = 'kube_scheduler'


@pytest.fixture()
def mock_metrics(mock_openmetrics_http):
    return make_mock_metrics(mock_openmetrics_http, 'metrics_1.14.0.txt')


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


def test_check_metrics_1_14(aggregator, mock_metrics, mock_leader):
    c = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    def assert_metric(name, **kwargs):
        # Wrapper to keep assertions < 120 chars
        aggregator.assert_metric(NAMESPACE + name, **kwargs)

    assert_metric('.pod_preemption.victims', value=0.0, tags=[])
    assert_metric('.pod_preemption.attempts', value=6.0, tags=[])
    assert_metric('.binding_duration.count', value=0.0, tags=['upper_bound:0.001'])
    assert_metric('.binding_duration.sum', value=0.16221686500000002, tags=[])
    assert_metric('.scheduling.scheduling_duration.count', value=14.0, tags=['operation:binding'])
    assert_metric('.scheduling.scheduling_duration.sum', value=0.16236949099999998, tags=['operation:binding'])
    assert_metric('.scheduling.algorithm.predicate_duration.sum', value=0.001379, tags=[])
    assert_metric('.scheduling.e2e_scheduling_duration.count', value=0.0, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.algorithm_duration.count', value=14.0, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.e2e_scheduling_duration.sum', value=0.166793941, tags=[])
    assert_metric(
        '.scheduling.scheduling_duration.quantile', value=0.01050672, tags=['operation:binding', 'quantile:0.5']
    )
    assert_metric('.scheduling.algorithm.priority_duration.sum', value=0.0, tags=[])
    assert_metric('.scheduling.algorithm.priority_duration.count', value=14.0, tags=['upper_bound:0.004'])
    assert_metric('.scheduling.algorithm.preemption_duration.sum', value=0.05524, tags=[])
    assert_metric('.scheduling.algorithm.predicate_duration.count', value=14.0, tags=['upper_bound:0.001'])
    assert_metric('.scheduling.algorithm.preemption_duration.count', value=0.0, tags=['upper_bound:0.001'])
    assert_metric('.schedule_attempts', value=14.0, tags=['result:scheduled'])
    assert_metric('.volume_scheduling_duration.sum', value=3.3576e-05, tags=['operation:assume'])
    assert_metric('.volume_scheduling_duration.count', value=14.0, tags=['upper_bound:1000.0', 'operation:assume'])
    assert_metric(
        '.client.http.requests_duration.count',
        tags=['url:https://172.17.0.2:6443/%7Bprefix%7D', 'upper_bound:0.001', 'verb:GET'],
    )
    assert_metric(
        '.client.http.requests_duration.sum',
        value=24.374537649,
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
    # check historgram transformation from microsecond to second
    assert_metric('.scheduling.algorithm_duration.sum', value=0.0018508010000000002, tags=[])
    # Leader election mixin
    expected_le_tags = ["record_kind:endpoints", "record_name:kube-scheduler", "record_namespace:kube-system"]
    assert_metric('.leader_election.transitions', value=3, tags=expected_le_tags)
    assert_metric('.leader_election.lease_duration', value=15, tags=expected_le_tags)
    aggregator.assert_service_check(NAMESPACE + ".leader_election.status", tags=expected_le_tags)
    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'side_effect, expected_status, expected_message',
    [
        (None, AgentCheck.OK, None),
        (requests.HTTPError('health check failed'), AgentCheck.CRITICAL, 'health check failed'),
    ],
    ids=['ok', 'http_error'],
)
def test_service_check(monkeypatch, mock_openmetrics_http, side_effect, expected_status, expected_message):
    instance = {'prometheus_url': 'http://localhost:10251/metrics'}
    # mock_openmetrics_http satisfies detect_sli_endpoint during __init__
    # the service-check path under test is driven by the seeded _http_handlers below
    mock_openmetrics_http.get.return_value = MockHTTPResponse(status_code=200)

    check = KubeSchedulerCheck(CHECK_NAME, {}, [instance])
    monkeypatch.setattr(check, 'service_check', mock.Mock())

    healthcheck_url = 'http://localhost:10251/healthz'
    handler = mock.MagicMock()
    handler.get.return_value.raise_for_status = mock.Mock(side_effect=side_effect)
    check._http_handlers[healthcheck_url] = handler

    check._perform_service_check(instance)

    if expected_message is None:
        check.service_check.assert_called_with('kube_scheduler.up', expected_status, tags=[])
    else:
        check.service_check.assert_called_with('kube_scheduler.up', expected_status, tags=[], message=expected_message)
