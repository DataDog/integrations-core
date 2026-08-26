# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from unittest.mock import MagicMock

import mock
import pytest
import requests

from datadog_checks.base.errors import CheckException
from datadog_checks.couch import CouchDb, errors
from datadog_checks.couch.couch import CouchDB1, CouchDB2

from . import common

pytestmark = pytest.mark.unit


def mock_response(status_code=200, json_data=None):
    response = mock.MagicMock(status_code=status_code, content='{}')
    response.json.return_value = {} if json_data is None else json_data
    return response


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "legacy auth config",
            {'user': 'legacy_foo', 'password': 'legacy_bar'},
            {'auth': ('legacy_foo', 'legacy_bar')},
        ),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("timeout", {'timeout': 17}, {'timeout': (17, 17)}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(common.BASIC_CONFIG)
    instance.update(extra_config)
    check = CouchDb(common.CHECK_NAME, {}, instances=[instance])

    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200, content='{}')

        check.check(instance)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)

        r.get.assert_called_with('http://{}:5984/_all_dbs/'.format(common.HOST), **http_wargs)


def test_new_version_system_metrics(load_test_data):
    # Testing the _build_system_metrics method I'm feeding it a json that has a the updated
    # keys that was added in version 3.4 that was causing the check to break. The idea here
    # is that I'm going to give the method the json then assert that it's able to go through
    # it thhorougly by the number of function calls and debug log calls.

    # Mock everything needed for the function to run
    mock_agent_check = MagicMock()
    mock_agent_check.gauge = MagicMock()
    mock_agent_check.log = MagicMock()

    couchdb_check = CouchDB2(mock_agent_check)
    tags = ["test:tag"]

    # The fixture file json is loaded as a fixture in the confest.py file
    couchdb_check._build_system_metrics(load_test_data, tags)

    assert mock_agent_check.gauge.call_count >= 183
    mock_agent_check.log.debug.assert_any_call("Skipping distribution events")


# --- CouchDb ---


def test_get_default_run_check_does_not_emit_service_check(aggregator):
    # Kills the ReplaceTrueWithFalse/AddNot mutants at couch.py:41 (`run_check=False` default).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock_response(json_data={'ok': True})
        result = check.get('http://example/', ['tag:1'])

    assert result == {'ok': True}
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, count=0)


def test_get_run_check_true_emits_ok_service_check(aggregator):
    # Kills the Eq/NotEq mutants comparing status in couch.py:46 (`AgentCheck.OK` service check).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock_response(json_data={'ok': True})
        result = check.get('http://example/', ['tag:1'], run_check=True)

    assert result == {'ok': True}
    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.OK, tags=['tag:1'], count=1)


def test_get_timeout_emits_critical_service_check_and_reraises(aggregator):
    # Kills the ExceptionReplacer mutant at couch.py:54 (`except requests.exceptions.Timeout`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = requests.exceptions.Timeout('boom')
        with pytest.raises(requests.exceptions.Timeout):
            check.get('http://example/', ['tag:1'], run_check=True)

    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=['tag:1'], count=1)


def test_get_http_error_emits_critical_service_check_and_reraises(aggregator):
    # Kills the ExceptionReplacer mutant at couch.py:57 (`except requests.exceptions.HTTPError`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        response = mock_response(status_code=500)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=response)
        r.get.return_value = response
        with pytest.raises(requests.exceptions.HTTPError):
            check.get('http://example/', ['tag:1'], run_check=True)

    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=['tag:1'], count=1)


def test_get_generic_exception_emits_critical_service_check_and_reraises(aggregator):
    # Kills the ExceptionReplacer mutant at couch.py:69 (bare `except Exception`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.side_effect = ValueError('boom')
        with pytest.raises(ValueError):
            check.get('http://example/', ['tag:1'], run_check=True)

    aggregator.assert_service_check(CouchDb.SERVICE_CHECK_NAME, status=CouchDb.CRITICAL, tags=['tag:1'], count=1)


def test_check_sets_version_metadata(datadog_agent):
    # Kills the AddNot/Is_IsNot mutants at couch.py:78 (`if version is not None`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    check.check_id = common.CHECK_ID
    check.get = MagicMock(return_value={'version': '2.3.1'})

    with mock.patch('datadog_checks.couch.couch.CouchDB2') as mock_v2:
        check.check({})

    mock_v2.assert_called_once_with(check)
    datadog_agent.assert_metadata(common.CHECK_ID, {'version.raw': '2.3.1'})


def test_check_wraps_get_failure_in_connection_error():
    # Kills the ExceptionReplacer mutant at couch.py:81 (`raise errors.ConnectionError(...)`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    check.get = MagicMock(side_effect=ValueError('network down'))

    with pytest.raises(errors.ConnectionError):
        check.check({})


def test_check_raises_bad_version_error_when_major_version_zero():
    # Kills the Eq/NotEq/Lt/Gt mutants at couch.py:79 (`if major_version == 0`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    check.get = MagicMock(return_value={'version': '0.11.0'})

    with pytest.raises(errors.BadVersionError):
        check.check({})


def test_check_routes_to_couchdb1_for_major_version_one():
    # Kills the ReplaceComparisonOperator_LtE_GtE/Eq mutants at couch.py:81 (`major_version <= 1`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    check.get = MagicMock(return_value={'version': '1.9.0'})

    with mock.patch('datadog_checks.couch.couch.CouchDB1') as mock_v1, mock.patch(
        'datadog_checks.couch.couch.CouchDB2'
    ) as mock_v2:
        check.check({})

    mock_v1.assert_called_once_with(check)
    mock_v2.assert_not_called()


def test_check_routes_to_couchdb2_for_major_version_two():
    # Kills the ReplaceComparisonOperator_LtE_GtE/NumberReplacer mutants at couch.py:81
    # (`major_version <= 1`) by confirming version 2 does not route to CouchDB1.
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    check.get = MagicMock(return_value={'version': '2.0.0'})

    with mock.patch('datadog_checks.couch.couch.CouchDB1') as mock_v1, mock.patch(
        'datadog_checks.couch.couch.CouchDB2'
    ) as mock_v2:
        check.check({})

    mock_v2.assert_called_once_with(check)
    mock_v1.assert_not_called()


def test_check_reuses_existing_checker_without_reconstructing():
    # Kills the AddNot/Is_IsNot mutants at couch.py:70 (`if self.checker is None`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[common.BASIC_CONFIG])
    check.get = MagicMock(return_value={'version': '2.0.0'})
    check.checker = MagicMock()

    check.check({})

    check.get.assert_not_called()
    check.checker.check.assert_called_once_with()


def test_get_config_tags_dedupes_when_present():
    # Kills the AddNot mutant at couch.py:100 (`return list(set(tags)) if tags else []`).
    check = CouchDb(common.CHECK_NAME, {}, instances=[{'server': 'http://x/', 'tags': ['a', 'a', 'b']}])
    assert sorted(check.get_config_tags()) == ['a', 'b']


def test_get_config_tags_defaults_to_empty_list_when_absent():
    # Kills the AddNot mutant at couch.py:100 for the falsy/empty branch.
    check = CouchDb(common.CHECK_NAME, {}, instances=[{'server': 'http://x/', 'tags': []}])
    assert check.get_config_tags() == []


# --- CouchDB1 ---


def test_couchdb1_create_metric_emits_overall_and_per_db_gauges():
    # Kills the ZeroIterationForLoop mutants at couch.py:117/118/123/124, the AddNot mutant at
    # couch.py:119, the ReplaceAndWithOr mutant at couch.py:125, and the Mod-format mutants at
    # couch.py:120/128.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB1(mock_agent_check)
    data = {
        'stats': {'httpd': {'requests': {'current': 5}, 'ignored': {'current': None}}},
        'databases': {'kennel': {'doc_count': 10, 'disk_size': 20, 'other_field': 30}},
    }

    couchdb_check._create_metric(data, tags=['t:1'])

    assert mock_agent_check.gauge.call_count == 3
    mock_agent_check.gauge.assert_any_call('couchdb.httpd.requests', 5, tags=['t:1'])
    mock_agent_check.gauge.assert_any_call(
        'couchdb.by_db.doc_count', 10, tags=['t:1', 'db:kennel'], device_name='kennel'
    )
    mock_agent_check.gauge.assert_any_call(
        'couchdb.by_db.disk_size', 20, tags=['t:1', 'db:kennel'], device_name='kennel'
    )


def test_couchdb1_check_wires_instance_tag_into_get_data_and_create_metric():
    # Kills the Mod-format mutant at couch.py:133 (`'instance:%s' % server`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.get_server.return_value = 'http://couch.example/'
    mock_agent_check.get_config_tags.return_value = ['env:prod']
    couchdb_check = CouchDB1(mock_agent_check)
    couchdb_check.get_data = MagicMock(return_value={'stats': {}, 'databases': {}})

    couchdb_check.check()

    expected_tags = ['instance:http://couch.example/', 'env:prod']
    couchdb_check.get_data.assert_called_once_with('http://couch.example/', expected_tags)


def test_couchdb1_get_data_raises_check_exception_when_overall_stats_missing():
    # Kills the AddNot/Is_IsNot mutants at couch.py:146 (`if overall_stats is None`) and the
    # Mod-format mutant at couch.py:150.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.get.return_value = None
    couchdb_check = CouchDB1(mock_agent_check)

    with pytest.raises(CheckException, match='No stats could be retrieved from http://server/_stats/'):
        couchdb_check.get_data('http://server/', ['t'])


def test_couchdb1_get_data_excludes_configured_databases():
    # Kills the ReplaceBinaryOperator_Sub_* mutants at couch.py:165 (set difference).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {'db_exclude': ['db2', 'db4']}
    mock_agent_check.MAX_DB = 50

    def fake_get(url, tags, run_check=False):
        if url.endswith('_stats/'):
            return {'stat': 1}
        if url.endswith('_all_dbs/'):
            return ['db1', 'db2', 'db3']
        return {'doc_count': 1}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB1(mock_agent_check)

    result = couchdb_check.get_data('http://server/', ['t'])

    assert set(result['databases'].keys()) == {'db1', 'db3'}


def test_couchdb1_get_data_warns_and_truncates_when_over_max_dbs():
    # Kills the ReplaceComparisonOperator_Gt_Lt/_LtE/_NotEq mutants at couch.py:169.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {'max_dbs_per_check': 1}
    mock_agent_check.MAX_DB = 50

    def fake_get(url, tags, run_check=False):
        if url.endswith('_stats/'):
            return {'stat': 1}
        if url.endswith('_all_dbs/'):
            return ['db1', 'db2']
        return {'doc_count': 1}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB1(mock_agent_check)

    result = couchdb_check.get_data('http://server/', ['t'])

    assert len(result['databases']) == 1
    mock_agent_check.warning.assert_called_once_with('Too many databases, only the first %s will be checked.', 1)


def test_couchdb1_get_data_does_not_warn_when_databases_equal_max():
    # Kills the ReplaceComparisonOperator_Gt_GtE mutant at couch.py:169.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {'max_dbs_per_check': 2}
    mock_agent_check.MAX_DB = 50

    def fake_get(url, tags, run_check=False):
        if url.endswith('_stats/'):
            return {'stat': 1}
        if url.endswith('_all_dbs/'):
            return ['db1', 'db2']
        return {'doc_count': 1}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB1(mock_agent_check)

    result = couchdb_check.get_data('http://server/', ['t'])

    assert len(result['databases']) == 2
    mock_agent_check.warning.assert_not_called()


def test_couchdb1_get_data_excludes_forbidden_and_unauthorized_dbs():
    # Kills the ExceptionReplacer mutant at couch.py:178 and the Eq/AddNot/OrWithAnd mutants at
    # couch.py:180, plus the ReplaceContinueWithBreak mutant at couch.py:189.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.MAX_DB = 50
    response_403 = mock.MagicMock(status_code=403)
    response_401 = mock.MagicMock(status_code=401)

    def fake_get(url, tags, run_check=False):
        if url.endswith('_stats/'):
            return {'stat': 1}
        if url.endswith('_all_dbs/'):
            return ['forbidden_db', 'unauthorized_db']
        if 'forbidden_db' in url:
            raise requests.exceptions.HTTPError(response=response_403)
        raise requests.exceptions.HTTPError(response=response_401)

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB1(mock_agent_check)

    result = couchdb_check.get_data('http://server/', ['t'])

    assert result['databases'] == {}
    assert sorted(couchdb_check.db_exclude['http://server/']) == ['forbidden_db', 'unauthorized_db']
    assert mock_agent_check.warning.call_count == 2


@pytest.mark.parametrize('status_code', [402, 500])
def test_couchdb1_get_data_keeps_other_http_error_statuses_without_excluding(status_code):
    # Kills the boundary comparison mutants (Lt/LtE/Gt/GtE) at couch.py:180 for status codes
    # just below and above the 403/401 thresholds.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.MAX_DB = 50
    response = mock.MagicMock(status_code=status_code)

    def fake_get(url, tags, run_check=False):
        if url.endswith('_stats/'):
            return {'stat': 1}
        if url.endswith('_all_dbs/'):
            return ['flaky_db']
        raise requests.exceptions.HTTPError(response=response)

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB1(mock_agent_check)

    result = couchdb_check.get_data('http://server/', ['t'])

    assert result['databases'] == {'flaky_db': None}
    assert couchdb_check.db_exclude['http://server/'] == []
    mock_agent_check.warning.assert_not_called()


def test_couchdb1_get_data_stores_successful_db_stats():
    # Kills the Is_IsNot/AddNot mutants at couch.py:190 (`if db_stats is not None`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.MAX_DB = 50

    def fake_get(url, tags, run_check=False):
        if url.endswith('_stats/'):
            return {'stat': 1}
        if url.endswith('_all_dbs/'):
            return ['db1']
        return {'doc_count': 7}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB1(mock_agent_check)

    result = couchdb_check.get_data('http://server/', ['t'])

    assert result['databases'] == {'db1': {'doc_count': 7}}


# --- CouchDB2 ---


def test_couchdb2_max_nodes_per_check_default_is_20():
    # Kills the core/NumberReplacer mutants at couch.py:198 (`MAX_NODES_PER_CHECK = 20`).
    assert CouchDB2.MAX_NODES_PER_CHECK == 20


def test_couchdb2_build_metrics_handles_histogram_percentile_and_plain_values():
    # Kills the ZeroIterationForLoop/AddNot/Eq mutants at couch.py:206-214 covering the
    # histogram, percentile, and plain "type" branches of _build_metrics.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    data = {
        'hist_metric': {
            'type': 'histogram',
            'value': {'histogram': [], 'percentile': [[50, 1.5], [99, 9.9]], 'min': 0.1},
        },
        'plain_metric': {'type': 'counter', 'value': 42},
    }

    couchdb_check._build_metrics(data, ['t:1'])

    mock_agent_check.gauge.assert_any_call('couchdb.hist_metric.percentile.50', 1.5, tags=['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.hist_metric.percentile.99', 9.9, tags=['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.hist_metric.min', 0.1, tags=['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.plain_metric', 42, tags=['t:1'])
    assert mock_agent_check.gauge.call_count == 4


def test_couchdb2_build_metrics_recurses_into_nested_dicts_without_type_key():
    # Kills the AddNot mutant at couch.py:207 (`if "type" in value`) by exercising the
    # nested-dict recursion branch when "type" is absent.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    data = {'nested': {'leaf': {'type': 'counter', 'value': 7}}}

    couchdb_check._build_metrics(data, ['t:1'])

    mock_agent_check.gauge.assert_called_once_with('couchdb.nested.leaf', 7, tags=['t:1'])


def test_couchdb2_build_db_metrics_emits_size_and_count_gauges():
    # Kills the ZeroIterationForLoop mutants at couch.py:223/226.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    data = {'sizes': {'file': 100, 'active': 90}, 'doc_del_count': 2, 'doc_count': 30}

    couchdb_check._build_db_metrics(data, ['db:kennel'])

    mock_agent_check.gauge.assert_any_call('couchdb.by_db.file_size', 100, ['db:kennel'])
    mock_agent_check.gauge.assert_any_call('couchdb.by_db.active_size', 90, ['db:kennel'])
    mock_agent_check.gauge.assert_any_call('couchdb.by_db.doc_del_count', 2, ['db:kennel'])
    mock_agent_check.gauge.assert_any_call('couchdb.by_db.doc_count', 30, ['db:kennel'])
    assert mock_agent_check.gauge.call_count == 4


def test_couchdb2_build_dd_metrics_builds_ddtags_and_emits_gauges():
    # Kills the ZeroIterationForLoop mutants at couch.py:235/238.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    info = {
        'name': 'dummy',
        'view_index': {
            'language': 'javascript',
            'sizes': {'file': 5},
            'updates_pending': {'minimum': 1},
            'waiting_clients': 3,
        },
    }

    couchdb_check._build_dd_metrics(info, ['db:kennel'])

    expected_tags = ['db:kennel', 'design_document:dummy', 'language:javascript']
    mock_agent_check.gauge.assert_any_call('couchdb.by_ddoc.file_size', 5, expected_tags)
    mock_agent_check.gauge.assert_any_call('couchdb.by_ddoc.minimum_updates_pending', 1, expected_tags)
    mock_agent_check.gauge.assert_any_call('couchdb.by_ddoc.waiting_clients', 3, expected_tags)
    assert mock_agent_check.gauge.call_count == 3


@pytest.mark.parametrize('missing_key', ['max', 'min', '50', '90'])
def test_couchdb2_build_system_metrics_skips_missing_percentile_keys(missing_key):
    # Kills the AddNot mutants at couch.py:250/252/254/256 (`if 'x' in val`) — a missing key
    # must be skipped, not looked up, which would KeyError under the mutant.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    val = {'max': 1, 'min': 2, '50': 3, '90': 4, '99': 5}
    del val[missing_key]
    data = {'message_queues': {'q': val}}

    couchdb_check._build_system_metrics(data, ['t:1'])

    tags = ['t:1', 'queue:q']
    for key in ['max', 'min', '50', '90', '99']:
        expected_call = mock.call('couchdb.erlang.message_queues.{0}'.format(key), val.get(key), tags)
        if key == missing_key:
            assert expected_call not in mock_agent_check.gauge.call_args_list
        else:
            assert expected_call in mock_agent_check.gauge.call_args_list


def test_couchdb2_build_system_metrics_logs_debug_when_queue_missing_all_keys():
    # Kills the AddNot mutant at couch.py:258 (`if '99' in val`) via the debug-log else branch.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    data = {'message_queues': {'q': {'max': 1}}}

    couchdb_check._build_system_metrics(data, ['t:1'])

    mock_agent_check.log.debug.assert_called_once_with("Queue %s does not have any keys. It will be ignored.", 'q')


def test_couchdb2_build_system_metrics_recurses_for_distribution():
    # Kills the Eq comparison mutant at couch.py:264 (`elif key == "distribution"`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    data = {'distribution': {'node@host': {'inbound': 7}}}

    couchdb_check._build_system_metrics(data, ['t:1'])

    mock_agent_check.gauge.assert_called_once_with(
        'couchdb.erlang.distribution.inbound', 7, ['t:1', 'node:node@host']
    )


def test_couchdb2_build_system_metrics_skips_distribution_events_but_continues_loop():
    # Kills the Eq_Lt/Eq_LtE comparison mutants and the ReplaceContinueWithBreak mutant at
    # couch.py:269/271 by ensuring keys before and after "distribution_events" are still
    # processed via the plain-gauge and nested-dict branches.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    data = {
        'aaa': 3,
        'distribution_events': {'x': 1},
        'nested': {'inner': 5},
        'plain': 9,
    }

    couchdb_check._build_system_metrics(data, ['t:1'])

    mock_agent_check.gauge.assert_any_call('couchdb.erlang.aaa', 3, ['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.erlang.nested.inner', 5, ['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.erlang.plain', 9, ['t:1'])
    assert mock_agent_check.gauge.call_count == 3
    mock_agent_check.log.debug.assert_called_once_with("Skipping distribution events")


def test_couchdb2_build_active_tasks_metrics_covers_all_task_types():
    # Kills the ZeroIterationForLoop/NumberReplacer/Eq/AddNot mutants at couch.py:278-317
    # covering counting, per-type tag/metric construction, the None-coercion for replication
    # metrics, the continuous/one-time ternary, and the count-label remap for
    # database_compaction.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    couchdb_check = CouchDB2(mock_agent_check)
    tasks = [
        {
            'type': 'replication',
            'doc_id': 'd1',
            'source': 's',
            'target': 't',
            'user': 'u',
            'continuous': True,
            'doc_write_failures': None,
            'docs_read': 5,
            'docs_written': 6,
            'missing_revisions_found': 7,
            'revisions_checked': 8,
            'changes_pending': 9,
        },
        {
            'type': 'database_compaction',
            'database': 'shards/80000000-9fffffff/kennel.1525771285',
            'changes_done': 1,
            'progress': 2,
            'total_changes': 3,
        },
        {
            'type': 'indexer',
            'database': 'shards/80000000-9fffffff/kennel.1525771285',
            'design_document': '_design/dummy',
            'changes_done': 4,
            'progress': 5,
            'total_changes': 6,
        },
        {
            'type': 'view_compaction',
            'database': 'shards/80000000-9fffffff/kennel.1525771285',
            'design_document': '_design/dummy',
            'phase': 'stopped',
            'changes_done': 7,
            'progress': 8,
            'total_changes': 9,
        },
        {
            'type': 'view_compaction',
            'database': 'shards/80000000-9fffffff/kennel.1525771285',
            'design_document': '_design/dummy',
            'changes_done': 10,
        },
    ]

    couchdb_check._build_active_tasks_metrics(tasks, ['t:1'])

    replication_tags = ['t:1', 'doc_id:d1', 'source:s', 'target:t', 'user:u', 'type:continuous']
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.replication.doc_write_failures', 0, replication_tags)
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.replication.docs_read', 5, replication_tags)

    compaction_tags = ['t:1', 'database:kennel']
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.db_compaction.changes_done', 1, compaction_tags)

    indexer_tags = ['t:1', 'database:kennel', 'design_document:dummy']
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.indexer.changes_done', 4, indexer_tags)

    view_tags_with_phase = ['t:1', 'database:kennel', 'design_document:dummy', 'phase:stopped']
    mock_agent_check.gauge.assert_any_call(
        'couchdb.active_tasks.view_compaction.changes_done', 7, view_tags_with_phase
    )

    view_tags_no_phase = ['t:1', 'database:kennel', 'design_document:dummy']
    mock_agent_check.gauge.assert_any_call(
        'couchdb.active_tasks.view_compaction.changes_done', 10, view_tags_no_phase
    )
    assert (
        mock.call('couchdb.active_tasks.view_compaction.progress', mock.ANY, view_tags_no_phase)
        not in mock_agent_check.gauge.call_args_list
    )

    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.replication.count', 1, ['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.db_compaction.count', 1, ['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.indexer.count', 1, ['t:1'])
    mock_agent_check.gauge.assert_any_call('couchdb.active_tasks.view_compaction.count', 2, ['t:1'])


def test_couchdb2_get_instance_names_returns_configured_name_without_membership_call():
    # Kills the Is_IsNot/AddNot mutants at couch.py:323 (`if name is None`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {'name': 'couchdb@node1'}
    couchdb_check = CouchDB2(mock_agent_check)

    names = couchdb_check._get_instance_names('http://server/')

    assert names == ['couchdb@node1']
    mock_agent_check.get.assert_not_called()


def test_couchdb2_get_instance_names_fetches_membership_and_applies_max_nodes():
    # Kills the NumberReplacer mutant at couch.py:198 (`MAX_NODES_PER_CHECK`) and the slice
    # boundary logic at couch.py:328.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {'max_nodes_per_check': 2}
    mock_agent_check.get.return_value = {'cluster_nodes': ['n1', 'n2', 'n3']}
    couchdb_check = CouchDB2(mock_agent_check)

    names = couchdb_check._get_instance_names('http://server/')

    assert names == ['n1', 'n2']
    mock_agent_check.get.assert_called_once_with('http://server/_membership', [])


def test_couchdb2_get_dbs_to_scan_returns_empty_list_on_key_error():
    # Kills the ExceptionReplacer mutant at couch.py:334 (`except KeyError: return []`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}

    def fake_get(url, tags):
        if url.endswith('_all_dbs'):
            return ['db1']
        return {}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB2(mock_agent_check)

    assert couchdb_check._get_dbs_to_scan('http://server/', 'node1', ['t']) == []


def test_couchdb2_get_dbs_to_scan_raises_and_logs_when_node_not_found():
    # Kills the ExceptionReplacer mutant at couch.py:339 (`except ValueError: ... raise`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}

    def fake_get(url, tags):
        if url.endswith('_all_dbs'):
            return ['db1']
        return {'cluster_nodes': ['other_node']}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB2(mock_agent_check)

    with pytest.raises(ValueError):
        couchdb_check._get_dbs_to_scan('http://server/', 'missing_node', ['t'])

    mock_agent_check.log.error.assert_called_once_with(
        "Could not find node %r in %r", 'missing_node', ['other_node']
    )


def test_couchdb2_get_dbs_to_scan_slices_databases_by_node_index():
    # Kills the ReplaceBinaryOperator_Div_* mutants at couch.py:343 and the
    # ReplaceBinaryOperator_Add_*/Mul_*/NumberReplacer mutants at couch.py:344.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}

    def fake_get(url, tags):
        if url.endswith('_all_dbs'):
            return ['db0', 'db1', 'db2', 'db3', 'db4']
        return {'cluster_nodes': ['node0', 'node1']}

    mock_agent_check.get.side_effect = fake_get
    couchdb_check = CouchDB2(mock_agent_check)

    assert couchdb_check._get_dbs_to_scan('http://server/', 'node0', ['t']) == ['db0', 'db1', 'db2']
    assert couchdb_check._get_dbs_to_scan('http://server/', 'node1', ['t']) == ['db3', 'db4']


def test_couchdb2_check_skips_db_scan_when_per_db_metrics_disabled():
    # Kills the AddNot/ReplaceTrueWithFalse mutants at couch.py:357
    # (`self.instance.get("enable_per_db_metrics", True)`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {'enable_per_db_metrics': False}
    mock_agent_check.get_config_tags.return_value = []
    mock_agent_check.get_server.return_value = 'http://server/'
    couchdb_check = CouchDB2(mock_agent_check)
    couchdb_check._get_instance_names = MagicMock(return_value=['node0'])
    couchdb_check._get_node_stats = MagicMock(return_value={})
    couchdb_check._get_system_stats = MagicMock(return_value={})
    couchdb_check._get_active_tasks = MagicMock(return_value=[])
    couchdb_check._get_dbs_to_scan = MagicMock()

    couchdb_check.check()

    couchdb_check._get_dbs_to_scan.assert_not_called()


def test_couchdb2_check_filters_databases_and_stops_at_max_dbs_per_check():
    # Kills the Is_IsNot/AddNot/AndWithOr/OrWithAnd mutants at couch.py:362, the Add mutant at
    # couch.py:363, the GtE/AddNot boundary mutants at couch.py:373, and the
    # ReplaceBreakWithContinue mutant at couch.py:374.
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {
        'max_dbs_per_check': 2,
        'db_include': ['db0', 'db1', 'db2', 'db3'],
        'db_exclude': ['db1'],
    }
    mock_agent_check.MAX_DB = 50
    mock_agent_check.get_config_tags.return_value = []
    mock_agent_check.get_server.return_value = 'http://server/'
    couchdb_check = CouchDB2(mock_agent_check)
    couchdb_check._get_instance_names = MagicMock(return_value=['node0'])
    couchdb_check._get_node_stats = MagicMock(return_value={})
    couchdb_check._get_system_stats = MagicMock(return_value={})
    couchdb_check._get_active_tasks = MagicMock(return_value=[])
    couchdb_check._get_dbs_to_scan = MagicMock(return_value=['db0', 'db1', 'db2', 'db3'])

    scanned_urls = []

    def fake_get(url, tags):
        if '_all_docs' in url:
            return {'rows': []}
        scanned_urls.append(url)
        return {'sizes': {}, 'doc_del_count': 0, 'doc_count': 0}

    mock_agent_check.get.side_effect = fake_get

    couchdb_check.check()

    assert scanned_urls == ['http://server/db0', 'http://server/db2']


def test_couchdb2_get_node_stats_requests_with_run_check_true():
    # Kills the ReplaceTrueWithFalse mutant at couch.py:380 (`self.agent_check.get(url, tags, True)`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.get.return_value = {'stat': 1}
    couchdb_check = CouchDB2(mock_agent_check)

    result = couchdb_check._get_node_stats('http://server/', 'node0', ['t'])

    assert result == {'stat': 1}
    mock_agent_check.get.assert_called_once_with('http://server/_node/node0/_stats', ['t'], True)


def test_couchdb2_get_node_stats_raises_when_stats_missing():
    # Kills the Is_IsNot/AddNot mutants at couch.py:383 (`if stats is None`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.get.return_value = None
    couchdb_check = CouchDB2(mock_agent_check)

    with pytest.raises(Exception, match='No stats could be retrieved from http://server/_node/node0/_stats'):
        couchdb_check._get_node_stats('http://server/', 'node0', ['t'])


def test_couchdb2_get_active_tasks_filters_by_node():
    # Kills the Eq comparison mutants at couch.py:401 (`task['node'] == name`).
    mock_agent_check = MagicMock()
    mock_agent_check.instance = {}
    mock_agent_check.get.return_value = [
        {'node': 'node0', 'id': 1},
        {'node': 'node1', 'id': 2},
    ]
    couchdb_check = CouchDB2(mock_agent_check)

    result = couchdb_check._get_active_tasks('http://server/', 'node0', ['t'])

    assert result == [{'node': 'node0', 'id': 1}]
