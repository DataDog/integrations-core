# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import logging

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.mesos_master import MesosMaster

from . import common

pytestmark = pytest.mark.unit


@contextlib.contextmanager
def mocked_session():
    # RequestsWrapper only creates its requests.Session lazily on the first HTTP call, so patching
    # it here (rather than assigning to check.http.get, which is a read-only slot) is the only way
    # to control the check's HTTP responses without mocking the check's own logic.
    session = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=session):
        yield session


def test_service_check_needed_defaults_to_true():
    # Kills the core/ReplaceTrueWithFalse mutant at mesos_master.py:22 (service_check_needed True -> False).
    assert MesosMaster.service_check_needed is True


def test_disable_ssl_validation_inverts_to_verify_false():
    # Kills the core/ReplaceFalseWithTrue mutant at mesos_master.py:138 (the 'default': False remap entry).
    check = MesosMaster('mesos_master', {}, [{'url': 'https://host', 'disable_ssl_validation': True}])
    assert check.http.options['verify'] is False


def test_ssl_validation_enabled_by_default():
    # Kills the core/ReplaceTrueWithFalse mutant at mesos_master.py:138 (the 'invert': True remap entry).
    check = MesosMaster('mesos_master', {}, [{'url': 'https://host'}])
    assert check.http.options['verify'] is True


@pytest.mark.parametrize(
    'url, disable_ssl_validation, expect_warning',
    [
        ('https://host', True, True),
        ('http://host', True, False),
        ('https://host', False, False),
        ('http://host', False, False),
    ],
)
def test_ssl_warning_only_logged_for_https_with_validation_disabled(
    url, disable_ssl_validation, expect_warning, caplog
):
    # Kills the core/ReplaceAndWithOr and core/ReplaceComparisonOperator_Eq_* mutants at mesos_master.py:146
    # (warning must require both verify=False AND scheme=='https', not either alone or a different scheme match).
    caplog.set_level(logging.WARNING)
    instance = {'url': url, 'disable_ssl_validation': disable_ssl_validation}
    MesosMaster('mesos_master', {}, [instance])
    assert ('Skipping TLS cert validation' in caplog.text) is expect_warning


def test_read_timeout_only_skips_default_timeout_override():
    # Kills the core/ReplaceOrWithAnd mutant at mesos_master.py:148 (the override guard on read/connect timeout).
    check = MesosMaster('mesos_master', {}, [{'url': 'http://host', 'read_timeout': 3}])
    assert check.http.options['timeout'] == (10.0, 3.0)


def test_connect_timeout_only_skips_default_timeout_override():
    # Kills the core/ReplaceOrWithAnd mutant at mesos_master.py:148 (symmetric case for connect_timeout).
    check = MesosMaster('mesos_master', {}, [{'url': 'http://host', 'connect_timeout': 4}])
    assert check.http.options['timeout'] == (4.0, 10.0)


def test_get_json_default_failure_expected_is_false(aggregator):
    # Kills the core/ReplaceFalseWithTrue mutant at mesos_master.py:160 (failure_expected default).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        session.get.return_value = mock.MagicMock(status_code=500, encoding='utf-8')
        with pytest.raises(CheckException):
            check._get_json('http://host/stats.json')

    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=AgentCheck.CRITICAL)


def test_get_json_appends_url_tag_to_existing_tags(aggregator):
    # Kills the core/ReplaceBinaryOperator_Add_* and core/ReplaceBinaryOperator_Mod_* mutants at mesos_master.py:161
    # (list concatenation and the "url:%s" % url interpolation must both be exact).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': True}
        session.get.return_value = response
        check._get_json('http://host/stats.json', tags=['existing:tag'])

    aggregator.assert_service_check(
        'mesos_master.can_connect', count=1, tags=['existing:tag', 'url:http://host/stats.json']
    )


def test_get_json_builds_url_tag_when_no_tags_given(aggregator):
    # Kills the core/AddNot mutant at mesos_master.py:161 (the "if tags else" branch selection).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': True}
        session.get.return_value = response
        check._get_json('http://host/stats.json')

    aggregator.assert_service_check('mesos_master.can_connect', count=1, tags=['url:http://host/stats.json'])


def test_get_json_normalizes_missing_encoding():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at mesos_master.py:168.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding=None)
        response.json.return_value = {}
        session.get.return_value = response
        check._get_json('http://host/stats.json')

        assert response.encoding == 'UTF8'


def test_get_json_preserves_existing_encoding():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot mutant at mesos_master.py:168 (the opposite direction).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='ascii')
        response.json.return_value = {}
        session.get.return_value = response
        check._get_json('http://host/stats.json')

        assert response.encoding == 'ascii'


@pytest.mark.parametrize(
    'status_code, expected_status, expected_message',
    [
        (200, AgentCheck.OK, 'Mesos master instance detected at http://host '),
        (150, AgentCheck.CRITICAL, 'Got 150 when hitting http://host'),
        (404, AgentCheck.CRITICAL, 'Got 404 when hitting http://host'),
    ],
)
def test_make_request_status_code_boundary(status_code, expected_status, expected_message):
    # Kills the core/ReplaceComparisonOperator_NotEq_* and core/AddNot mutants at mesos_master.py:180, and the
    # core/NumberReplacer mutants tampering with the 200 boundary constant.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        session.get.return_value = mock.MagicMock(status_code=status_code)
        _, msg, status = check._make_request('http://host')

    assert status == expected_status
    assert msg == expected_message


def test_make_request_handles_timeout_exception():
    # Kills the core/ExceptionReplacer mutant at mesos_master.py:186 (the requests.exceptions.Timeout handler).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        session.get.side_effect = requests.exceptions.Timeout
        _, msg, status = check._make_request('http://host')

    assert status == AgentCheck.CRITICAL
    assert 'seconds timeout when hitting http://host' in msg


def test_make_request_handles_generic_exception():
    # Kills the core/ExceptionReplacer mutant at mesos_master.py:190 (the catch-all Exception handler).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        session.get.side_effect = RuntimeError('kaboom')
        _, msg, status = check._make_request('http://host')

    assert status == AgentCheck.CRITICAL
    assert msg == 'kaboom'


def test_send_service_check_default_failure_expected_is_false(aggregator):
    # Kills the core/ReplaceFalseWithTrue mutant at mesos_master.py:196 (failure_expected default).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with pytest.raises(CheckException):
        check._send_service_check('http://host', AgentCheck.CRITICAL, tags=['t:1'], message='trouble')

    aggregator.assert_service_check('mesos_master.can_connect', count=1)


@pytest.mark.parametrize(
    'status, failure_expected, expected_raises, expected_count, expected_message',
    [
        (AgentCheck.OK, False, False, 1, ''),
        (AgentCheck.CRITICAL, True, True, 0, None),
        (AgentCheck.WARNING, True, False, 1, 'trouble'),
        (AgentCheck.UNKNOWN, False, False, 1, 'trouble'),
        (AgentCheck.CRITICAL, False, True, 1, 'Cannot connect to mesos. Error: trouble'),
        (AgentCheck.WARNING, False, False, 1, 'trouble'),
        (AgentCheck.UNKNOWN, True, False, 1, 'trouble'),
    ],
)
def test_send_service_check_status_handling(
    status, failure_expected, expected_raises, expected_count, expected_message, aggregator
):
    # Kills the core/ReplaceFalseWithTrue, core/ReplaceComparisonOperator_Is_* (Lt/LtE/Gt/GtE/NotEq/IsNot),
    # core/ReplaceAndWithOr, core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants across
    # mesos_master.py:197-210, by exercising every status/failure_expected combination the branches distinguish.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    if expected_raises:
        with pytest.raises(CheckException):
            check._send_service_check('http://host', status, failure_expected=failure_expected, message='trouble')
    else:
        check._send_service_check('http://host', status, failure_expected=failure_expected, message='trouble')

    aggregator.assert_service_check('mesos_master.can_connect', count=expected_count)
    if expected_count:
        recorded = aggregator.service_checks('mesos_master.can_connect')[-1]
        assert recorded.message == expected_message


def test_send_service_check_resets_flag_after_first_emission(aggregator):
    # Kills the core/ReplaceFalseWithTrue mutant at mesos_master.py:208 (service_check_needed reset after emitting).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    check._send_service_check('http://host', AgentCheck.OK)
    check._send_service_check('http://host', AgentCheck.OK)

    aggregator.assert_service_check('mesos_master.can_connect', count=1)


def test_master_state_found_307_true_when_first_response_is_none():
    # Kills the core/ReplaceComparisonOperator_IsNot_Is and core/AddNot mutants at mesos_master.py:215.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    resp2 = mock.MagicMock(history=[mock.MagicMock(status_code=307)])

    assert check._master_state_found_307(None, resp2) is True


def test_master_state_found_307_true_when_second_response_is_none():
    # Kills the core/ReplaceComparisonOperator_IsNot_Is and core/AddNot mutants at mesos_master.py:217.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    resp1 = mock.MagicMock(history=[mock.MagicMock(status_code=307)])

    assert check._master_state_found_307(resp1, None) is True


def test_master_state_found_307_false_without_redirect_in_history():
    # Kills the core/ZeroIterationForLoop mutant at mesos_master.py:220 and the
    # core/ReplaceFalseWithTrue mutant at mesos_master.py:223 (the default return).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    resp1 = mock.MagicMock(history=[mock.MagicMock(status_code=200), mock.MagicMock(status_code=404)])
    resp2 = mock.MagicMock(history=[])

    assert check._master_state_found_307(resp1, resp2) is False


def test_master_state_found_307_skips_none_entries_in_history():
    # Kills the core/ReplaceAndWithOr and core/AddNot mutants at mesos_master.py:221 (the "r is not None" guard).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    resp1 = mock.MagicMock(history=[None, mock.MagicMock(status_code=307)])
    resp2 = mock.MagicMock(history=[])

    assert check._master_state_found_307(resp1, resp2) is True


def test_master_state_found_307_requires_exact_redirect_code():
    # Kills the core/ReplaceComparisonOperator_Eq_* and core/NumberReplacer mutants at mesos_master.py:221
    # (the literal 307 status code) and the core/ReplaceTrueWithFalse mutant at mesos_master.py:222.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    resp1 = mock.MagicMock(history=[mock.MagicMock(status_code=308)])
    resp2 = mock.MagicMock(history=[])

    assert check._master_state_found_307(resp1, resp2) is False


def test_get_master_state_uses_state_endpoint_when_available(aggregator):
    # Kills the core/ReplaceBinaryOperator_Add_* mutants at mesos_master.py:227 and mesos_master.py:256
    # (the endpoint and tag string concatenations).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': 1}
        session.get.return_value = response

        result = check._get_master_state('http://host', ['t:1'])

        assert result == {'ok': 1}
        assert session.get.call_args.args[0] == 'http://host/state'
    aggregator.assert_service_check('mesos_master.can_connect', count=1, tags=['t:1', 'url:http://host/state'])


def test_get_master_state_falls_back_to_json_endpoint_on_bad_status(aggregator):
    # Kills the core/ReplaceOrWithAnd and core/ReplaceComparisonOperator_NotEq_Eq mutants at mesos_master.py:232,
    # the core/ReplaceBinaryOperator_Add_* mutants at mesos_master.py:234, and the
    # core/ReplaceComparisonOperator_Is_IsNot mutant at mesos_master.py:242.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        bad_response = mock.MagicMock(status_code=500, encoding='utf-8')
        fallback_response = mock.MagicMock(status_code=200, encoding=None)
        fallback_response.json.return_value = {'fallback': True}
        session.get.side_effect = [bad_response, fallback_response]

        result = check._get_master_state('http://host', ['t:1'])

        assert result == {'fallback': True}
        assert fallback_response.encoding == 'UTF8'
        assert session.get.call_args.args[0] == 'http://host/state.json'
    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=AgentCheck.OK)


def test_get_master_state_marks_unknown_on_non_leader_redirect(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_NotEq and core/ReplaceAndWithOr mutants at mesos_master.py:241.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        primary = mock.MagicMock(status_code=401, history=[mock.MagicMock(status_code=307)])
        fallback = mock.MagicMock(status_code=401, history=[], encoding='utf-8')
        fallback.json.return_value = {'should': 'not be used'}
        session.get.side_effect = [primary, fallback]

        result = check._get_master_state('http://host', ['t:1'])

        assert result is None
    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=AgentCheck.UNKNOWN)


def test_get_master_state_preserves_existing_encoding_on_success():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot mutant at mesos_master.py:252.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='ascii')
        response.json.return_value = {}
        session.get.return_value = response

        check._get_master_state('http://host', ['t:1'])

        assert response.encoding == 'ascii'


def test_get_master_stats_uses_new_endpoint_at_version_boundary():
    # Kills the core/ReplaceComparisonOperator_GtE_* and core/NumberReplacer mutants at mesos_master.py:260, and
    # the core/ReplaceBinaryOperator_Add_* mutants at mesos_master.py:261.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    check.version = [0, 22, 0]

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': True}
        session.get.return_value = response

        check._get_master_stats('http://host', ['t:1'])

        assert session.get.call_args.args[0] == 'http://host/metrics/snapshot'


def test_get_master_stats_uses_legacy_endpoint_below_version_boundary():
    # Kills the core/ReplaceComparisonOperator_GtE_* mutants at mesos_master.py:260 (just below the boundary), and
    # the core/ReplaceBinaryOperator_Add_* mutants at mesos_master.py:263.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    check.version = [0, 21, 99]

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': True}
        session.get.return_value = response

        check._get_master_stats('http://host', ['t:1'])

        assert session.get.call_args.args[0] == 'http://host/stats.json'


def test_get_master_roles_uses_new_endpoint_at_version_boundary():
    # Kills the core/ReplaceComparisonOperator_GtE_* and core/NumberReplacer mutants at mesos_master.py:267, and
    # the core/ReplaceBinaryOperator_Add_* mutants at mesos_master.py:268.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    check.version = [1, 8, 0]

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': True}
        session.get.return_value = response

        check._get_master_roles('http://host', ['t:1'])

        assert session.get.call_args.args[0] == 'http://host/roles'


def test_get_master_roles_uses_legacy_endpoint_below_version_boundary():
    # Kills the core/ReplaceComparisonOperator_GtE_* mutants at mesos_master.py:267 (just below the boundary), and
    # the core/ReplaceBinaryOperator_Add_* mutants at mesos_master.py:270.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    check.version = [1, 7, 99]

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'ok': True}
        session.get.return_value = response

        check._get_master_roles('http://host', ['t:1'])

        assert session.get.call_args.args[0] == 'http://host/roles.json'


def test_check_leadership_sets_leader_false_when_state_metrics_unavailable():
    # Kills the core/ReplaceFalseWithTrue mutant at mesos_master.py:275.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        primary = mock.MagicMock(status_code=401, history=[mock.MagicMock(status_code=307)])
        fallback = mock.MagicMock(status_code=401, history=[])
        session.get.side_effect = [primary, fallback]

        result = check._check_leadership('http://host', ['t:1'])

        assert result is None
        assert check.leader is False


def test_check_leadership_sets_leader_true_when_pid_matches_leader():
    # Kills the core/ReplaceComparisonOperator_Eq_* mutants at mesos_master.py:280.
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'version': '1.7.1', 'leader': 'master@a', 'pid': 'master@a'}
        session.get.return_value = response

        check._check_leadership('http://host', ['t:1'])

        assert check.leader is True


def test_check_leadership_sets_leader_false_when_pid_differs_from_leader():
    # Kills the core/ReplaceComparisonOperator_Eq_* mutants at mesos_master.py:280 (the opposite direction).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])

    with mocked_session() as session:
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        response.json.return_value = {'version': '1.7.1', 'leader': 'master@a', 'pid': 'master@b'}
        session.get.return_value = response

        check._check_leadership('http://host', ['t:1'])

        assert check.leader is False


def test_check_full_flow_tags_frameworks_and_resets_service_check_flag(aggregator):
    # Kills the core/AddNot mutant at mesos_master.py:291 (instance_tags None guard), the core/AddNot mutant at
    # mesos_master.py:297 ('cluster' in state_metrics), the core/ExceptionReplacer mutant at mesos_master.py:321
    # (the KeyError guard around missing role resources), and the core/ReplaceTrueWithFalse mutant at
    # mesos_master.py:343 (service_check_needed reset at the end of check()).
    check = MesosMaster('mesos_master', {}, [common.INSTANCE])
    instance = dict(common.INSTANCE, tags=None)

    state = {
        'version': '1.9.0',
        'pid': 'master@127.0.0.1:5050',
        'leader': 'master@127.0.0.1:5050',
        'cluster': 'datadog-test',
        'frameworks': [
            {
                'name': 'marathon',
                'tasks': [{}],
                'used_resources': {'cpus': 1.0, 'mem': 128.0, 'disk': 0.0},
            }
        ],
    }
    roles = {
        'roles': [
            {
                'name': 'role1',
                'frameworks': ['marathon'],
                'weight': 1.0,
                # 'cpus' is deliberately missing to exercise the KeyError guard at mesos_master.py:321.
                'resources': {'mem': 10.0, 'disk': 0.0},
            }
        ]
    }
    stats = {'master/tasks_running': 3, 'system/cpus_total': 4}

    def fake_get(url, **options):
        response = mock.MagicMock(status_code=200, encoding='utf-8')
        if url.endswith('/state'):
            response.json.return_value = state
        elif url.endswith('/roles'):
            response.json.return_value = roles
        elif url.endswith('/metrics/snapshot'):
            response.json.return_value = stats
        return response

    with mocked_session() as session:
        session.get.side_effect = fake_get
        check.check(instance)

    aggregator.assert_metric(
        'mesos.cluster.total_frameworks',
        value=1,
        tags=['mesos_pid:master@127.0.0.1:5050', 'mesos_node:master', 'mesos_cluster:datadog-test'],
    )
    aggregator.assert_metric('mesos.role.mem')
    aggregator.assert_metric('mesos.role.disk')
    assert check.service_check_needed is True
