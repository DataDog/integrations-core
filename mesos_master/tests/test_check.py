# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.mesos_master import MesosMaster


def test_check(check, instance, aggregator):
    check = check({}, instance)
    check.check(instance)
    metrics = {}
    for d in (
        check.CLUSTER_TASKS_METRICS,
        check.CLUSTER_SLAVES_METRICS,
        check.CLUSTER_RESOURCES_METRICS,
        check.CLUSTER_REGISTRAR_METRICS,
        check.CLUSTER_FRAMEWORK_METRICS,
        check.SYSTEM_METRICS,
        check.STATS_METRICS,
    ):
        metrics.update(d)

    for _, v in iteritems(check.FRAMEWORK_METRICS):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(metrics):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(check.ROLE_RESOURCES_METRICS):
        aggregator.assert_metric(v[0])

    aggregator.assert_metric('mesos.cluster.total_frameworks')
    aggregator.assert_metric('mesos.framework.total_tasks')
    aggregator.assert_metric('mesos.role.frameworks.count')
    aggregator.assert_metric('mesos.role.weight')


def test_default_timeout(check, instance):
    # test default timeout
    check = check({}, instance)
    check.check(instance)

    assert check.http.options['timeout'] == (5, 5)


def test_init_config_old_timeout(check, instance):
    # test init_config timeout
    check = check({'default_timeout': 2}, instance)
    check.check(instance)
    assert check.http.options['timeout'] == (2, 2)


def test_init_config_timeout(check, instance):
    # test init_config timeout
    check = check({'timeout': 7}, instance)
    check.check(instance)

    assert check.http.options['timeout'] == (7, 7)


def test_instance_old_timeout(check, instance):
    # test instance default_timeout
    instance['default_timeout'] = 13
    check = check({'default_timeout': 9}, instance)
    check.check(instance)

    assert check.http.options['timeout'] == (13, 13)


def test_instance_timeout(check, instance):
    # test instance timeout
    instance['timeout'] = 15
    check = check({}, instance)
    check.check(instance)

    assert check.http.options['timeout'] == (15, 15)


@pytest.mark.parametrize(
    'test_case_name, request_mock_side_effects, expected_status, expected_tags, expect_exception',
    [
        (
            'OK case for /state endpoint',
            [mock.MagicMock(status_code=200, content='{}')],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state'],
            False,
        ),
        (
            'OK case with failing /state due to bad status and fallback on /state.json',
            [mock.MagicMock(status_code=500), mock.MagicMock(status_code=200, content='{}')],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state.json'],
            False,
        ),
        (
            'OK case with failing /state due to Timeout and fallback on /state.json',
            [requests.exceptions.Timeout, mock.MagicMock(status_code=200, content='{}')],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state.json'],
            False,
        ),
        (
            'OK case with failing /state due to Exception and fallback on /state.json',
            [Exception, mock.MagicMock(status_code=200, content='{}')],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state.json'],
            False,
        ),
        (
            'NOK case with failing /state and /state.json due to timeout',
            [requests.exceptions.Timeout, requests.exceptions.Timeout],
            AgentCheck.CRITICAL,
            ['my:tag', 'url:http://hello.com/state.json'],
            True,
        ),
        (
            'NOK case with failing /state and /state.json with bad status',
            [mock.MagicMock(status_code=500), mock.MagicMock(status_code=500)],
            AgentCheck.CRITICAL,
            ['my:tag', 'url:http://hello.com/state.json'],
            True,
        ),
        (
            'OK case with non-leader master on /state',
            [
                mock.MagicMock(status_code=401, history=[mock.MagicMock(status_code=307)]),
                mock.MagicMock(content='{}', history=[], status_code=500),
            ],
            AgentCheck.UNKNOWN,
            ['my:tag', 'url:http://hello.com/state.json'],
            False,
        ),
        (
            'OK case with non-leader master on /state.json',
            [
                mock.MagicMock(status_code=500, history=[]),
                mock.MagicMock(content='{}', history=[mock.MagicMock(status_code=307)], status_code=401),
            ],
            AgentCheck.UNKNOWN,
            ['my:tag', 'url:http://hello.com/state.json'],
            False,
        ),
    ],
)
@pytest.mark.integration
def test_can_connect_service_check(
    instance, aggregator, test_case_name, request_mock_side_effects, expected_status, expected_tags, expect_exception
):
    check = MesosMaster('mesos_master', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = request_mock_side_effects

        try:
            check._get_master_state('http://hello.com', ['my:tag'])
            exception_raised = False
        except CheckException:
            exception_raised = True

        assert expect_exception == exception_raised

    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=expected_status, tags=expected_tags)
