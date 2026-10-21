# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientReadTimeoutError
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

    for v in check.TASK_METRICS.values():
        aggregator.assert_metric(v[0])
    for v in metrics.values():
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
STATE_URL = 'http://hello.com/state'
LEGACY_STATE_URL = 'http://hello.com/state.json'
STATS_URL = 'http://hello.com/stats.json'
# The check only emits the OK service check for a non-empty payload, and iterates frameworks for the configured tasks.
STATE_RESPONSE = FakeHTTPResponse(json_result={'frameworks': []})
SLAVE_STATE_RESPONSE = FakeHTTPResponse(json_result={"master_hostname": "localhost", "frameworks": []})
MASTER_STATE_RESPONSE = FakeHTTPResponse(json_result={"cluster": "test-cluster"})
STATS_RESPONSE = FakeHTTPResponse(json_result={'slave/tasks_failed': 0})

state_test_data = [
    (
        'OK for /state',
        [(STATE_URL, STATE_RESPONSE)],
        ['url:http://hello.com/state'] + additional_tags,
        False,
        AgentCheck.OK,
    ),
    (
        'failing for /state, OK for /state.json',
        [(STATE_URL, Exception('boom')), (LEGACY_STATE_URL, STATE_RESPONSE)],
        ['url:http://hello.com/state.json'] + additional_tags,
        False,
        AgentCheck.OK,
    ),
    (
        'failing for /state and failing for /state.json',
        [(STATE_URL, Exception('boom')), (LEGACY_STATE_URL, Exception('boom'))],
        ['url:http://hello.com/state.json'] + additional_tags,
        True,
        AgentCheck.CRITICAL,
    ),
    (
        'OK for /state, OK for /state-summary',
        [(STATE_URL, SLAVE_STATE_RESPONSE), ('http://localhost:5050/state-summary', MASTER_STATE_RESPONSE)],
        ['url:http://hello.com/state'] + additional_tags + cluster_name_tag,
        False,
        AgentCheck.OK,
    ),
]

stats_test_data = [
    (
        'OK for /stats.json',
        [(STATS_URL, STATS_RESPONSE)],
        ['url:http://hello.com/stats.json'] + additional_tags,
        False,
        AgentCheck.OK,
    ),
    (
        'Failing for /stats.json',
        [(STATS_URL, Exception('boom'))],
        ['url:http://hello.com/stats.json'] + additional_tags,
        True,
        AgentCheck.CRITICAL,
    ),
]


@pytest.mark.parametrize(PARAMETERS, state_test_data)
@pytest.mark.integration
def test_can_connect_service_check_state(
    instance,
    aggregator,
    fake_http,
    test_case_name,
    responses,
    expected_tags,
    expect_exception,
    expected_status,
):
    check = MesosSlave('mesos_slave', {}, [instance])
    for url, response in responses:
        fake_http.register_response('GET', url, response)
    try:
        check._process_state_info('http://hello.com', instance['tasks'], 5050, instance['tags'])
        assert not expect_exception
    except Exception:
        if not expect_exception:
            raise

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)


@pytest.mark.integration
def test_can_connect_service_with_instance_cluster_name(instance, aggregator, fake_http):
    instance['cluster_name'] = 'test-cluster'
    expected_tags = ['url:http://hello.com/state'] + cluster_name_tag + additional_tags
    expected_status = AgentCheck.OK
    check = MesosSlave('mesos_slave', {}, [instance])
    fake_http.register_response('GET', STATE_URL, STATE_RESPONSE)
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
    instance,
    aggregator,
    fake_http,
    test_case_name,
    responses,
    expected_tags,
    expect_exception,
    expected_status,
):
    check = MesosSlave('mesos_slave', {}, [instance])
    for url, response in responses:
        fake_http.register_response('GET', url, response)
    try:
        check._process_stats_info('http://hello.com', instance['tags'])
        assert not expect_exception
    except Exception:
        if not expect_exception:
            raise

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)


@pytest.mark.parametrize(
    ('error', 'expected_warning'),
    [
        pytest.param(HTTPClientReadTimeoutError('read timed out'), 'Timeout for', id='timeout'),
        pytest.param(HTTPClientConnectionError('connection refused'), "Couldn't connect to URL", id='connection error'),
    ],
)
def test_get_json_warns_by_failure_kind_and_propagates(instance, fake_http, error, expected_warning):
    """A timeout is reported as a timeout, and anything else as a connection failure.

    Both arms re-raise, because the callers turn the exception into the can_connect service check, and a
    swallowed failure would report the slave as healthy.
    """
    check = MesosSlave('mesos_slave', {}, [instance])
    fake_http.register_response('GET', STATE_URL, error)

    with pytest.raises(type(error)):
        check._get_json('http://hello.com/state')

    assert any(expected_warning in warning for warning in check.warnings)
