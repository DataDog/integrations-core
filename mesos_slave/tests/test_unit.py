# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple
from copy import deepcopy

import mock
import pytest
import requests
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.mesos_slave import MesosSlave


def test_fixtures(check, instance, aggregator):
    check = check({}, instance)
    check.check(instance)
    metrics = {}
    for d in (
        check.SLAVE_TASKS_METRICS,
        check.SYSTEM_METRICS,
        check.SLAVE_RESOURCE_METRICS,
        check.SLAVE_EXECUTORS_METRICS,
        check.STATS_METRICS,
    ):
        metrics.update(d)

    for _, v in iteritems(check.TASK_METRICS):
        aggregator.assert_metric(v[0])
    for _, v in iteritems(metrics):
        aggregator.assert_metric(v[0])

    service_check_tags = [
        'instance:mytag1',
        'mesos_cluster:test',
        'mesos_node:slave',
        'mesos_pid:slave(1)@127.0.0.1:5051',
        'task_name:hello',
    ]
    aggregator.assert_service_check('hello.ok', tags=service_check_tags, count=1, status=check.OK)


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
    'test_case, extra_config, expected_http_kwargs',
    [
        ("legacy disable_ssl_validation config True", {'disable_ssl_validation': True}, {'verify': False}),
        ("legacy disable_ssl_validation config False", {'disable_ssl_validation': False}, {'verify': True}),
        ("legacy disable_ssl_validation config default", {}, {'verify': True}),
    ],
)
def test_config(check, instance, test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(instance)
    instance.update(extra_config)

    check = check({}, instance)
    check.check(instance)

    actual = {k: v for k, v in check.http.options.items() if k in expected_http_kwargs}

    assert actual == expected_http_kwargs


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
    ],
)
@pytest.mark.integration
def test_can_connect_service_check(
    instance, aggregator, test_case_name, request_mock_side_effects, expected_status, expected_tags, expect_exception
):
    check = MesosSlave('mesos_slave', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = request_mock_side_effects

        try:
            check._get_state('http://hello.com', ['my:tag'])
            exception_raised = False
        except CheckException:
            exception_raised = True

        assert expect_exception == exception_raised

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)
