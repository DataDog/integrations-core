# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.mesos_slave import MesosSlave

from .common import MESOS_SLAVE_VERSION, PARAMETERS


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
        'mesos_cluster:test-cluster',
        'mesos_node:slave',
        'mesos_pid:slave(1)@127.0.0.1:5051',
        'task_name:hello',
    ]
    aggregator.assert_service_check('hello.ok', tags=service_check_tags, count=1, status=check.OK)


def test_metadata(check, instance, datadog_agent):
    check = check({}, instance)
    check.check_id = 'test:123'
    check.check(instance)

    version = MESOS_SLAVE_VERSION.split('-')[0]
    major, minor, patch = version.split('.')

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': version,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


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


additional_tags = ['instance:mytag1']
cluster_name_tag = ['mesos_cluster:test-cluster']
slave_attrs = {'json.return_value': {"master_hostname": "localhost", "frameworks": []}}
master_attrs = {'json.return_value': {"cluster": "test-cluster"}}

state_test_data = [
    (
        'OK for /state',
        [mock.MagicMock(status_code=200, content='{}')],
        ['url:http://hello.com/state'] + additional_tags,
        False,
        AgentCheck.OK,
    ),
    (
        'failing for /state, OK for /state.json',
        [Exception, mock.MagicMock(status_code=200, content='{}')],
        ['url:http://hello.com/state.json'] + additional_tags,
        False,
        AgentCheck.OK,
    ),
    (
        'failing for /state and failing for /state.json',
        [Exception, Exception],
        ['url:http://hello.com/state.json'] + additional_tags,
        True,
        AgentCheck.CRITICAL,
    ),
    (
        'OK for /state, OK for /state-summary',
        [mock.MagicMock(status_code=200, **slave_attrs), mock.MagicMock(status_code=200, **master_attrs)],
        ['url:http://hello.com/state'] + additional_tags + cluster_name_tag,
        False,
        AgentCheck.OK,
    ),
]

stats_test_data = [
    (
        'OK for /stats.json',
        [mock.MagicMock(status_code=200, content='{}')],
        ['url:http://hello.com/stats.json'] + additional_tags,
        False,
        AgentCheck.OK,
    ),
    (
        'Failing for /stats.json',
        [Exception],
        ['url:http://hello.com/stats.json'] + additional_tags,
        True,
        AgentCheck.CRITICAL,
    ),
]


@pytest.mark.parametrize(PARAMETERS, state_test_data)
@pytest.mark.integration
def test_can_connect_service_check_state(
    instance, aggregator, test_case_name, request_mock_effects, expected_tags, expect_exception, expected_status
):
    check = MesosSlave('mesos_slave', {}, [instance])
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = request_mock_effects
        try:
            check._process_state_info('http://hello.com', instance['tasks'], 5050, instance['tags'])
            assert not expect_exception
        except Exception:
            if not expect_exception:
                raise

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)


@pytest.mark.integration
def test_can_connect_service_with_instance_cluster_name(instance, aggregator):
    instance['cluster_name'] = 'test-cluster'
    expected_tags = ['url:http://hello.com/state'] + cluster_name_tag + additional_tags
    expected_status = AgentCheck.OK
    check = MesosSlave('mesos_slave', {}, [instance])
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = [mock.MagicMock(status_code=200, content='{}')]
        try:
            check._process_state_info('http://hello.com', instance['tasks'], 5050, instance['tags'])
            assert not False
        except Exception:
            if not False:
                raise

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)


@pytest.mark.parametrize(PARAMETERS, stats_test_data)
@pytest.mark.integration
def test_can_connect_service_check_stats(
    instance, aggregator, test_case_name, request_mock_effects, expected_tags, expect_exception, expected_status
):
    check = MesosSlave('mesos_slave', {}, [instance])
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = request_mock_effects
        try:
            check._process_stats_info('http://hello.com', instance['tags'])
            assert not expect_exception
        except Exception:
            if not expect_exception:
                raise

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)
