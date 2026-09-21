# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientTimeoutError
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

    for v in check.FRAMEWORK_METRICS.values():
        aggregator.assert_metric(v[0])
    for v in metrics.values():
        aggregator.assert_metric(v[0])
    for v in check.ROLE_RESOURCES_METRICS.values():
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
    'test_case_name, request_outcomes, expected_status, expected_tags, expected_exception',
    [
        (
            'OK case for /state endpoint',
            [FakeHTTPResponse(json_result={})],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state'],
            None,
        ),
        (
            'OK case with failing /state due to bad status and fallback on /state.json',
            [FakeHTTPResponse(status_code=500), FakeHTTPResponse(json_result={})],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state.json'],
            None,
        ),
        (
            'OK case with failing /state due to Timeout and fallback on /state.json',
            [HTTPClientTimeoutError("timeout"), FakeHTTPResponse(json_result={})],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state.json'],
            None,
        ),
        (
            'OK case with failing /state due to Exception and fallback on /state.json',
            [Exception("unexpected error"), FakeHTTPResponse(json_result={})],
            AgentCheck.OK,
            ['my:tag', 'url:http://hello.com/state.json'],
            None,
        ),
        (
            'NOK case with failing /state and /state.json due to timeout',
            [HTTPClientTimeoutError("timeout"), HTTPClientTimeoutError("timeout")],
            AgentCheck.CRITICAL,
            ['my:tag', 'url:http://hello.com/state.json'],
            CheckException,
        ),
        (
            'NOK case with failing /state and /state.json with bad status',
            [FakeHTTPResponse(status_code=500), FakeHTTPResponse(status_code=500)],
            AgentCheck.CRITICAL,
            ['my:tag', 'url:http://hello.com/state.json'],
            CheckException,
        ),
        (
            'OK case with non-leader master on /state',
            [
                FakeHTTPResponse(status_code=401, history=[FakeHTTPResponse(status_code=307)]),
                FakeHTTPResponse(status_code=500),
            ],
            AgentCheck.UNKNOWN,
            ['my:tag', 'url:http://hello.com/state.json'],
            None,
        ),
        (
            'OK case with non-leader master on /state.json',
            [
                FakeHTTPResponse(status_code=500),
                FakeHTTPResponse(status_code=401, history=[FakeHTTPResponse(status_code=307)]),
            ],
            AgentCheck.UNKNOWN,
            ['my:tag', 'url:http://hello.com/state.json'],
            None,
        ),
    ],
)
@pytest.mark.integration
def test_can_connect_service_check(
    instance,
    aggregator,
    fake_http,
    test_case_name,
    request_outcomes,
    expected_status,
    expected_tags,
    expected_exception,
):
    check = MesosMaster('mesos_master', {}, [instance])

    urls = ['http://hello.com/state', 'http://hello.com/state.json']
    for url, outcome in zip(urls, request_outcomes):
        fake_http.register_response('GET', url, outcome)

    if expected_exception is not None:
        with pytest.raises(expected_exception):
            check._get_master_state('http://hello.com', ['my:tag'])
    else:
        check._get_master_state('http://hello.com', ['my:tag'])

    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=expected_status, tags=expected_tags)
    fake_http.assert_all_responses_consumed()


def test_timeout_service_check_preserves_timeout_context(instance, aggregator, fake_http):
    check = MesosMaster('mesos_master', {}, [instance])
    fake_http.register_response('GET', 'http://hello.com/state', HTTPClientTimeoutError('timeout'))
    fake_http.register_response('GET', 'http://hello.com/state.json', HTTPClientTimeoutError('timeout'))

    with pytest.raises(CheckException):
        check._get_master_state('http://hello.com', ['my:tag'])

    service_check = aggregator.service_checks('mesos_master.can_connect')[0]
    assert 'seconds timeout when hitting http://hello.com/state.json' in service_check.message
