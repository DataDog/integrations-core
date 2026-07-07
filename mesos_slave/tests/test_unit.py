# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from copy import deepcopy

import mock
import pytest
from requests.exceptions import Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.mesos_slave import MesosSlave
from datadog_checks.mesos_slave.mesos_slave import DEFAULT_MASTER_PORT

from .common import MESOS_SLAVE_VERSION, PARAMETERS

pytestmark = pytest.mark.unit


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
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
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
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
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
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = request_mock_effects
        try:
            check._process_stats_info('http://hello.com', instance['tags'])
            assert not expect_exception
        except Exception:
            if not expect_exception:
                raise

    aggregator.assert_service_check('mesos_slave.can_connect', count=1, status=expected_status, tags=expected_tags)


def urls_called(mock_get):
    return [call.args[0] for call in mock_get.call_args_list]


def test_default_master_port_is_5050():
    # Kills the core/NumberReplacer mutants at mesos_slave.py:16 (DEFAULT_MASTER_PORT 5050 -> 5051/5049).
    assert DEFAULT_MASTER_PORT == 5050


def test_tls_warning_logged_for_https_url_when_verify_enabled(caplog):
    # Kills core/ReplaceComparisonOperator_Eq_{Gt,GtE,Is} and AddNot mutants at mesos_slave.py:103.
    with caplog.at_level(logging.WARNING):
        MesosSlave('mesos_slave', {}, [{'url': 'https://hello.com', 'tasks': []}])
    assert any('Skipping TLS cert validation' in m for m in caplog.messages)


def test_tls_warning_not_logged_for_http_url(caplog):
    # Kills core/ReplaceComparisonOperator_Eq_{NotEq,Lt,LtE,IsNot} and ReplaceAndWithOr at mesos_slave.py:103.
    with caplog.at_level(logging.WARNING):
        MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    assert not any('Skipping TLS cert validation' in m for m in caplog.messages)


def test_tls_warning_not_logged_for_scheme_greater_than_https(caplog):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at mesos_slave.py:103 ('httpz' >= 'https' is True).
    with caplog.at_level(logging.WARNING):
        MesosSlave('mesos_slave', {}, [{'url': 'httpz://hello.com', 'tasks': []}])
    assert not any('Skipping TLS cert validation' in m for m in caplog.messages)


def test_tls_warning_not_logged_when_ssl_validation_disabled_for_https_url(caplog):
    # Kills the core/AddNot and core/ReplaceAndWithOr mutants at mesos_slave.py:103 (verify=False case).
    with caplog.at_level(logging.WARNING):
        MesosSlave('mesos_slave', {}, [{'url': 'https://hello.com', 'tasks': [], 'disable_ssl_validation': True}])
    assert not any('Skipping TLS cert validation' in m for m in caplog.messages)


def test_read_timeout_only_does_not_override_http_timeout():
    # Kills the core/ReplaceOrWithAnd mutant at mesos_slave.py:105 (read_timeout alone must skip the override).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': [], 'read_timeout': 3}])
    assert check.http.options['timeout'] == (10.0, 3.0)


def test_get_state_metrics_uses_state_endpoint():
    # Kills the core/ReplaceBinaryOperator_Add_* mutants at mesos_slave.py:170,172,173 (url/endpoint/suffix concat).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, **{'json.return_value': {}})
        tags = []
        state_metrics = check._get_state_metrics('http://hello.com', tags)
    assert urls_called(r.get) == ['http://hello.com/state']
    assert tags == ['url:http://hello.com/state']
    assert state_metrics == {}


def test_get_state_metrics_with_suffix_appends_suffix_to_endpoint():
    # Kills the core/ReplaceBinaryOperator_Add_* mutants at mesos_slave.py:172,173 for the suffix concatenation.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, **{'json.return_value': {}})
        tags = []
        check._get_state_metrics('http://hello.com', tags, suffix='-summary')
    assert urls_called(r.get) == ['http://hello.com/state-summary']
    assert tags == ['url:http://hello.com/state-summary']


def test_get_state_metrics_falls_back_to_json_endpoint_on_failure():
    # Kills the core/ExceptionReplacer mutant at mesos_slave.py:174 and the Add mutants at line 176.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = [Exception('boom'), mock.MagicMock(status_code=200, **{'json.return_value': {}})]
        tags = []
        state_metrics = check._get_state_metrics('http://hello.com', tags)
    assert urls_called(r.get) == ['http://hello.com/state', 'http://hello.com/state.json']
    assert tags == ['url:http://hello.com/state.json']
    assert state_metrics == {}


def test_get_stats_metrics_uses_snapshot_endpoint_at_version_boundary():
    # Kills the core/NumberReplacer and ReplaceComparisonOperator_GtE_* mutants at mesos_slave.py:183 (exact boundary).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    check.version = [0, 22, 0]
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, **{'json.return_value': {}})
        tags = []
        check._get_stats_metrics('http://hello.com', tags)
    assert urls_called(r.get) == ['http://hello.com/metrics/snapshot']
    assert tags == ['url:http://hello.com/metrics/snapshot']


def test_get_stats_metrics_uses_legacy_endpoint_below_version_boundary():
    # Kills the core/NumberReplacer and ReplaceComparisonOperator_GtE_* mutants at mesos_slave.py:183 (minor < 22).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    check.version = [0, 21, 99]
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, **{'json.return_value': {}})
        tags = []
        check._get_stats_metrics('http://hello.com', tags)
    assert urls_called(r.get) == ['http://hello.com/stats.json']
    assert tags == ['url:http://hello.com/stats.json']


def test_get_stats_metrics_uses_legacy_endpoint_with_negative_patch():
    # Kills the core/NumberReplacer mutant at mesos_slave.py:183 (last 0 -> -1 in [0,22,0]).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    check.version = [0, 22, -1]
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, **{'json.return_value': {}})
        tags = []
        check._get_stats_metrics('http://hello.com', tags)
    assert urls_called(r.get) == ['http://hello.com/stats.json']


def test_get_stats_metrics_uses_snapshot_endpoint_strictly_above_boundary():
    # Kills the core/ReplaceComparisonOperator_GtE_Eq mutant at mesos_slave.py:183 (version strictly above target).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    check.version = [0, 23, 0]
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, **{'json.return_value': {}})
        tags = []
        check._get_stats_metrics('http://hello.com', tags)
    assert urls_called(r.get) == ['http://hello.com/metrics/snapshot']


def test_get_json_timeout_logs_timeout_specific_warning_and_reraises():
    # Kills the core/ExceptionReplacer mutant at mesos_slave.py:191 (except Timeout).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = Timeout()
        with pytest.raises(Timeout):
            check._get_json('http://hello.com/state')
    assert any('Timeout for' in w for w in check.warnings)


def test_get_json_generic_exception_logs_connection_warning_and_reraises():
    # Kills the core/ExceptionReplacer mutant at mesos_slave.py:194 (except Exception as e).
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = ValueError('boom')
        with pytest.raises(ValueError):
            check._get_json('http://hello.com/state')
    assert any("Couldn't connect to URL" in w for w in check.warnings)


def test_process_state_info_reports_critical_and_reraises_when_state_fetch_fails(aggregator):
    # Kills the core/ExceptionReplacer mutant at mesos_slave.py:143 (except Exception): the
    # CRITICAL service check must be submitted by the handler before the exception is re-raised.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = [Exception, Exception]
        with pytest.raises(Exception):
            check._process_state_info('http://hello.com', [], 5050, ['instance:mytag1'])
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, count=1, status=AgentCheck.CRITICAL)


def test_process_stats_info_reports_critical_and_reraises_when_stats_fetch_fails(aggregator):
    # Kills the core/ExceptionReplacer mutant at mesos_slave.py:164 (except Exception): the
    # CRITICAL service check must be submitted by the handler before the exception is re-raised.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = [Exception]
        with pytest.raises(Exception):
            check._process_stats_info('http://hello.com', ['instance:mytag1'])
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, count=1, status=AgentCheck.CRITICAL)


def test_set_cluster_name_skips_master_lookup_when_cluster_name_already_set():
    # Kills the core/ReplaceAndWithOr mutant at mesos_slave.py:208.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    check.cluster_name = 'existing'
    r = mock.MagicMock()
    tags = []
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        check._set_cluster_name('http://hello.com', 5050, {'master_hostname': 'host'}, tags)
    assert r.get.call_count == 0
    assert tags == ['mesos_cluster:existing']


def make_state_metrics_with_task(state_id, slave_id):
    return {
        'id': state_id,
        'frameworks': [
            {
                'executors': [
                    {
                        'tasks': [
                            {
                                'name': 'hello',
                                'slave_id': slave_id,
                                'state': 'TASK_RUNNING',
                                'resources': {'cpus': 1, 'mem': 1, 'disk': 1},
                            }
                        ]
                    }
                ]
            }
        ],
    }


def test_process_tasks_skips_task_with_lexicographically_smaller_slave_id(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE and Eq_IsNot mutants at mesos_slave.py:221.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    state_metrics = make_state_metrics_with_task(state_id='ZZZ', slave_id='AAA')
    check._process_tasks(['hello'], state_metrics, [])
    aggregator.assert_service_check('hello.ok', count=0)


def test_process_tasks_skips_task_with_lexicographically_larger_slave_id(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at mesos_slave.py:221.
    check = MesosSlave('mesos_slave', {}, [{'url': 'http://hello.com', 'tasks': []}])
    state_metrics = make_state_metrics_with_task(state_id='AAA', slave_id='ZZZ')
    check._process_tasks(['hello'], state_metrics, [])
    aggregator.assert_service_check('hello.ok', count=0)
