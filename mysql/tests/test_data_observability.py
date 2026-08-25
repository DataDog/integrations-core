# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import calendar
import datetime
import json
import logging
from copy import deepcopy
from unittest.mock import MagicMock, call, patch

import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.data_observability import EVENT_TRACK_TYPE, MAX_RESULT_ROWS
from datadog_checks.mysql.version_utils import MySQLVersion

from . import common

pytestmark = pytest.mark.unit

_BASE_EPOCH = calendar.timegm(datetime.datetime(2026, 1, 1, 0, 49, 0).timetuple())

BASE_QUERY = {
    'monitor_id': 1,
    'dbname': 'test_db',
    'query': 'SELECT count(*) FROM orders',
    'interval_seconds': 60,
    'query_timeout': 30_000,
    'type': 'freshness',
    'entity': {
        'platform': 'aws',
        'account': '123456',
        'database': 'test_db',
        'schema': 'test_db',
        'table': 'orders',
    },
}

MULTI_QUERIES = [
    BASE_QUERY,
    {
        **deepcopy(BASE_QUERY),
        'monitor_id': 2,
        'query': 'SELECT count(*) FROM users',
        'interval_seconds': 120,
        'entity': {**BASE_QUERY['entity'], 'table': 'users'},
    },
]

CRON_QUERY = {
    **deepcopy(BASE_QUERY),
    'monitor_id': 10,
    'query': 'SELECT 1',
    'schedule': '50 * * * *',
    'interval_seconds': 3600,
}


def _make_do_instance(instance_basic, queries=None, config_id='test-config-123'):
    instance = deepcopy(instance_basic)
    instance['data_observability'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 10,
        'config_id': config_id,
        'queries': queries if queries is not None else [deepcopy(BASE_QUERY)],
    }
    return instance


def _make_mock_conn(rows=None, description=None, open=True):
    mock_conn = MagicMock()
    mock_conn.open = open
    timeout_cursor = MagicMock()
    timeout_cursor.fetchone.return_value = (0,)
    query_cursor = MagicMock()
    query_cursor.description = description or [('count',)]
    result_rows = rows if rows is not None else [(42,)]
    query_cursor.fetchmany.side_effect = lambda size: result_rows[:size]
    mock_conn.cursor.side_effect = lambda cursor_class=None: (
        query_cursor if cursor_class is pymysql.cursors.SSCursor else timeout_cursor
    )
    mock_conn.query_cursor = query_cursor
    mock_conn.timeout_cursor = timeout_cursor
    return mock_conn, query_cursor


def _create_check(instance_basic, queries=None, config_id='test-config-123'):
    instance = _make_do_instance(instance_basic, queries=queries, config_id=config_id)
    check = MySql(common.CHECK_NAME, {}, [instance])
    check._resolved_hostname = 'mysql.test'
    check.version = MySQLVersion('8.0.0', 'MySQL', '')
    check.is_mariadb = False
    return check


def _setup_and_run(instance_basic, queries=None, config_id='test-config-123', mock_conn=None):
    if mock_conn is None:
        mock_conn, mock_cursor = _make_mock_conn()
    else:
        mock_cursor = mock_conn.query_cursor
    check = _create_check(instance_basic, queries=queries, config_id=config_id)
    check.data_observability._db = mock_conn
    check.data_observability.run_job()
    return check, mock_conn, mock_cursor


def _get_do_event_calls(mock_epe):
    return [call for call in mock_epe.call_args_list if len(call.args) >= 2 and call.args[1] == EVENT_TRACK_TYPE]


def test_no_queries_does_nothing(aggregator, instance_basic):
    check = _create_check(instance_basic, queries=[])
    check.data_observability._connection_args_provider = MagicMock()

    check.data_observability.run_job()

    check.data_observability._connection_args_provider.assert_not_called()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')


def test_queries_are_sorted_to_minimize_database_and_timeout_changes(instance_basic):
    queries = [
        {
            **deepcopy(BASE_QUERY),
            'monitor_id': 1,
            'dbname': 'warehouse',
            'query': 'SELECT warehouse_30_a',
            'query_timeout': 30_000,
        },
        {
            **deepcopy(BASE_QUERY),
            'monitor_id': 2,
            'dbname': 'analytics',
            'query': 'SELECT analytics_20_a',
            'query_timeout': 20_000,
        },
        {
            **deepcopy(BASE_QUERY),
            'monitor_id': 3,
            'dbname': 'warehouse',
            'query': 'SELECT warehouse_10',
            'query_timeout': 10_000,
        },
        {
            **deepcopy(BASE_QUERY),
            'monitor_id': 4,
            'dbname': 'analytics',
            'query': 'SELECT analytics_20_b',
            'query_timeout': 20_000,
        },
        {
            **deepcopy(BASE_QUERY),
            'monitor_id': 5,
            'dbname': 'warehouse',
            'query': 'SELECT warehouse_30_b',
            'query_timeout': 30_000,
        },
    ]
    check, conn, cursor = _setup_and_run(instance_basic, queries=queries)

    assert check.data_observability._db is conn
    assert [call.args[0] for call in cursor.execute.call_args_list] == [
        'USE `analytics`',
        'SELECT analytics_20_a',
        'SELECT analytics_20_b',
        'USE `warehouse`',
        'SELECT warehouse_10',
        'SELECT warehouse_30_a',
        'SELECT warehouse_30_b',
    ]
    assert conn.timeout_cursor.execute.call_args_list == [
        call('SET SESSION max_execution_time = %s', (20_000,)),
        call('SET SESSION max_execution_time = %s', (10_000,)),
        call('SET SESSION max_execution_time = %s', (30_000,)),
    ]


@pytest.mark.parametrize('dbname', ['bad-name', 'bad`name', 'db.name', 'db name', '', 'db;DROP TABLE users'])
def test_invalid_database_name_is_skipped_without_blocking_valid_query(aggregator, instance_basic, dbname):
    invalid_query = {**deepcopy(BASE_QUERY), 'monitor_id': 2, 'dbname': dbname}
    _, _, cursor = _setup_and_run(instance_basic, queries=[invalid_query, deepcopy(BASE_QUERY)])

    assert [call.args[0] for call in cursor.execute.call_args_list] == [
        'USE `test_db`',
        BASE_QUERY['query'],
    ]
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


@pytest.mark.parametrize('dbname', ['shopist', 'shopist_analytics', 'shopist$raw', 'DB123'])
def test_valid_database_name_is_used(instance_basic, dbname):
    query = {**deepcopy(BASE_QUERY), 'dbname': dbname}
    _, _, cursor = _setup_and_run(instance_basic, queries=[query])

    assert cursor.execute.call_args_list[0].args[0] == f'USE `{dbname}`'


def test_query_failure_database_error(aggregator, instance_basic):
    mock_conn, cursor = _make_mock_conn()
    cursor.execute.side_effect = [None, pymysql.err.ProgrammingError('syntax error')]

    _setup_and_run(instance_basic, mock_conn=mock_conn)

    metrics = aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:error' in metrics[0].tags


def test_connection_failure_propagates(instance_basic):
    check = _create_check(instance_basic)
    check.data_observability._connection_args_provider = MagicMock(
        side_effect=pymysql.err.OperationalError('Connection refused')
    )

    with pytest.raises(pymysql.err.OperationalError, match='Connection refused'):
        check.data_observability.run_job()


def test_interface_error_propagates(instance_basic):
    mock_conn, cursor = _make_mock_conn()
    cursor.execute.side_effect = pymysql.err.InterfaceError('connection closed')
    check = _create_check(instance_basic)
    check.data_observability._db = mock_conn

    with pytest.raises(pymysql.err.InterfaceError, match='connection closed'):
        check.data_observability.run_job()

    assert check.data_observability._db is None
    assert check.data_observability._current_dbname is None
    assert check.data_observability._current_query_timeout_ms is None


def test_closed_connection_propagates_and_cron_query_is_retried(instance_basic, aggregator, monkeypatch):
    current_time = [float(_BASE_EPOCH + 65)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    failed_conn, failed_cursor = _make_mock_conn(open=False)
    failed_cursor.execute.side_effect = pymysql.err.OperationalError('server closed the connection')
    check = _make_cron_check(instance_basic)
    check.data_observability._db = failed_conn

    with pytest.raises(pymysql.err.OperationalError, match='server closed'):
        check.data_observability.run_job()

    assert check.data_observability._db is None

    recovered_conn, recovered_cursor = _make_mock_conn()
    check.data_observability._db = recovered_conn
    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1
    assert [call.args[0] for call in recovered_cursor.execute.call_args_list] == [
        'USE `test_db`',
        CRON_QUERY['query'],
    ]


def test_query_failure_does_not_block_subsequent(aggregator, instance_basic):
    mock_conn, cursor = _make_mock_conn()
    cursor.execute.side_effect = [
        None,
        pymysql.err.ProgrammingError('table not found'),
        None,
        None,
    ]

    _setup_and_run(instance_basic, queries=deepcopy(MULTI_QUERIES), mock_conn=mock_conn)

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 2


@pytest.mark.parametrize(
    'is_mariadb,variable,configured_timeout',
    [
        (False, 'max_execution_time', 30_000),
        (True, 'max_statement_time', 30.0),
    ],
    ids=['mysql', 'mariadb'],
)
def test_query_timeout_is_applied(instance_basic, is_mariadb, variable, configured_timeout):
    mock_conn, _ = _make_mock_conn()
    check = _create_check(instance_basic)
    check.is_mariadb = is_mariadb
    check.data_observability._db = mock_conn

    check.data_observability.run_job()

    assert mock_conn.timeout_cursor.execute.call_args_list == [
        call(f'SET SESSION {variable} = %s', (configured_timeout,)),
    ]


def test_mysql_56_executes_query_without_unsupported_session_timeout(instance_basic):
    mock_conn, cursor = _make_mock_conn()
    check = _create_check(instance_basic)
    check.version = MySQLVersion('5.6.51', 'MySQL', '')
    check.data_observability._db = mock_conn

    check.data_observability.run_job()

    mock_conn.timeout_cursor.execute.assert_not_called()
    assert [call.args[0] for call in cursor.execute.call_args_list] == [
        'USE `test_db`',
        BASE_QUERY['query'],
    ]


def test_non_result_query_is_reported_as_error(aggregator, instance_basic):
    mock_conn, cursor = _make_mock_conn()

    def execute(query):
        if not query.startswith('USE'):
            cursor.description = None

    cursor.execute.side_effect = execute
    _setup_and_run(instance_basic, mock_conn=mock_conn)

    metrics = aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:error' in metrics[0].tags


def test_streaming_result_is_capped_in_emitted_event(instance_basic):
    mock_conn, _ = _make_mock_conn(rows=[(row,) for row in range(MAX_RESULT_ROWS + 1)], description=[('row',)])

    with patch.object(MySql, 'event_platform_event') as mock_epe:
        _, conn, _ = _setup_and_run(instance_basic, mock_conn=mock_conn)

    payload = json.loads(_get_do_event_calls(mock_epe)[0].args[0])
    assert payload['row_count'] == MAX_RESULT_ROWS
    assert len(payload['rows']) == MAX_RESULT_ROWS
    assert payload['rows'][-1] == [MAX_RESULT_ROWS - 1]
    conn.cursor.assert_any_call(pymysql.cursors.SSCursor)


def test_event_payload_structure(instance_basic):
    mock_conn, _ = _make_mock_conn(rows=[(42,)], description=[('count',)])

    with patch.object(MySql, 'event_platform_event') as mock_epe:
        _setup_and_run(instance_basic, mock_conn=mock_conn)

    calls = _get_do_event_calls(mock_epe)
    assert len(calls) == 1
    payload = json.loads(calls[0].args[0])
    assert payload['config_id'] == 'test-config-123'
    assert payload['db_type'] == 'mysql'
    assert payload['db_host'] == 'mysql.test'
    assert payload['db_name'] == 'test_db'
    assert payload['monitor_id'] == 1
    assert payload['status'] == 'success'
    assert payload['columns'] == ['count']
    assert payload['rows'] == [[42]]
    assert payload['row_count'] == 1
    assert payload['error'] is None
    assert payload['entity']['schema'] == 'test_db'


def test_custom_sql_select_fields_in_payload(instance_basic):
    query = deepcopy(BASE_QUERY)
    query['custom_sql_select_fields'] = {'metric_config_id': 42, 'entity_id': 'entity-123'}

    with patch.object(MySql, 'event_platform_event') as mock_epe:
        _setup_and_run(instance_basic, queries=[query])

    payload = json.loads(_get_do_event_calls(mock_epe)[0].args[0])
    assert payload['custom_sql_select_fields'] == {'metric_config_id': 42, 'entity_id': 'entity-123'}


def test_tags_include_monitor_config_and_db_type(aggregator, instance_basic):
    _setup_and_run(instance_basic)

    metric = aggregator.metrics('dd.mysql.data_observability.query_executions')[0]
    assert 'monitor_id:1' in metric.tags
    assert 'config_id:test-config-123' in metric.tags
    assert 'db_type:mysql' in metric.tags
    assert 'status:success' in metric.tags


def test_per_query_interval_tracking(aggregator, instance_basic, monkeypatch):
    current_time = [1_000.0]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _create_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1

    aggregator.reset()
    current_time[0] += BASE_QUERY['interval_seconds'] - 1
    check.data_observability.run_job()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')

    current_time[0] += 1
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_failed_query_updates_last_execution(aggregator, instance_basic):
    mock_conn, cursor = _make_mock_conn()
    cursor.execute.side_effect = [None, pymysql.err.ProgrammingError('syntax error')]
    check = _create_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    assert check.data_observability._last_execution[1] > 0

    aggregator.reset()
    check.data_observability.run_job()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')


def _make_cron_check(instance_basic, queries=None, *, window_seconds=None, monkeypatch=None):
    if window_seconds is not None:
        assert monkeypatch is not None
        monkeypatch.setattr('datadog_checks.mysql.data_observability.CRON_STARTUP_LOOKBACK_SECONDS', window_seconds)
    return _create_check(instance_basic, queries=queries or [deepcopy(CRON_QUERY)])


def test_schedule_query_does_not_fire_before_tick(instance_basic, monkeypatch):
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, cursor = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()

    cursor.execute.assert_not_called()


def test_schedule_query_fires_at_cron_tick(instance_basic, aggregator, monkeypatch):
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    current_time[0] = _BASE_EPOCH + 65
    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_first_poll_exactly_at_cron_tick_fires(instance_basic, aggregator, monkeypatch):
    tick_time = float(_BASE_EPOCH + 60)
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: tick_time)
    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_schedule_takes_precedence_over_interval(instance_basic, aggregator, monkeypatch):
    query = {**deepcopy(CRON_QUERY), 'interval_seconds': 5}
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _create_check(instance_basic, queries=[query])
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    current_time[0] += 10
    check.data_observability.run_job()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')

    current_time[0] = _BASE_EPOCH + 65
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_invalid_cron_filtered_at_init(instance_basic, aggregator, caplog):
    bad = {**deepcopy(CRON_QUERY), 'monitor_id': 20, 'schedule': 'not-a-cron'}
    with caplog.at_level(logging.WARNING):
        check = _create_check(instance_basic, queries=[bad, deepcopy(BASE_QUERY)])

    assert {query.monitor_id for query in check.data_observability._queries} == {1}
    assert any('invalid cron schedule' in record.message for record in caplog.records)

    mock_conn, _ = _make_mock_conn()
    check.data_observability._db = mock_conn
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_missing_schedule_and_interval_filtered_at_init(instance_basic, caplog):
    query = deepcopy(BASE_QUERY)
    query.pop('interval_seconds')
    with caplog.at_level(logging.WARNING):
        check = _create_check(instance_basic, queries=[query])

    assert check.data_observability._queries == ()
    assert any('neither schedule nor positive interval_seconds' in record.message for record in caplog.records)


def test_lateness_metric_for_cron(instance_basic, aggregator, monkeypatch):
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn
    check.data_observability.run_job()
    scheduled_tick = check.data_observability._schedulers[10].next_tick

    current_time[0] = _BASE_EPOCH + 180
    check.data_observability.run_job()

    metric = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')[0]
    assert abs(metric.value - (current_time[0] - scheduled_tick)) < 5
    assert 'mode:cron' in metric.tags


def test_lateness_metric_for_interval(instance_basic, aggregator, monkeypatch):
    current_time = [1000.0]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _create_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    first = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')[0]
    assert first.value == 0
    assert 'mode:interval' in first.tags

    current_time[0] = 1080.0
    aggregator.reset()
    check.data_observability.run_job()
    second = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')[0]
    assert second.value == 20


def test_lateness_clamped_at_zero(instance_basic, aggregator, monkeypatch):
    from datadog_checks.mysql.data_observability import DueQuery

    current_time = [float(_BASE_EPOCH + 65)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn
    query = check._do_config.queries[0]

    with patch.object(
        check.data_observability,
        '_get_due_queries',
        return_value=[DueQuery(query, current_time[0] + 100, 'cron')],
    ):
        check.data_observability.run_job()

    metric = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')[0]
    assert metric.value == 0


@pytest.mark.parametrize(
    'window_seconds,time_offset,expected_fires',
    [(300, 70, 1), (0, 70, 0), (300, 400, 0)],
    ids=['inside-window', 'disabled', 'outside-window'],
)
def test_cron_startup_lookback(instance_basic, aggregator, monkeypatch, window_seconds, time_offset, expected_fires):
    current_time = [float(_BASE_EPOCH + time_offset)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(instance_basic, window_seconds=window_seconds, monkeypatch=monkeypatch)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == expected_fires


def test_cron_startup_lookback_does_not_double_fire(instance_basic, aggregator, monkeypatch):
    current_time = [float(_BASE_EPOCH + 70)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1

    current_time[0] += 10
    aggregator.reset()
    check.data_observability.run_job()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')


def test_failed_cron_query_advances_scheduler(instance_basic, aggregator, monkeypatch):
    current_time = [float(_BASE_EPOCH + 65)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, cursor = _make_mock_conn()
    cursor.execute.side_effect = [None, pymysql.err.ProgrammingError('missing table')]
    check = _make_cron_check(instance_basic)
    check.data_observability._db = mock_conn

    check.data_observability.run_job()
    next_tick = check.data_observability._schedulers[10].next_tick

    aggregator.reset()
    check.data_observability.run_job()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert check.data_observability._schedulers[10].next_tick == next_tick


def test_cron_query_is_retried_after_connection_failure(instance_basic, aggregator, monkeypatch):
    current_time = [float(_BASE_EPOCH + 65)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, cursor = _make_mock_conn()
    check = _make_cron_check(instance_basic)
    check.data_observability._get_db_connection = MagicMock(
        side_effect=[pymysql.err.OperationalError('Connection refused'), mock_conn]
    )

    with pytest.raises(pymysql.err.OperationalError, match='Connection refused'):
        check.data_observability.run_job()
    assert not aggregator.metrics('dd.mysql.data_observability.query_executions')

    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1
    assert [call.args[0] for call in cursor.execute.call_args_list] == ['USE `test_db`', CRON_QUERY['query']]


@pytest.mark.parametrize('collection_interval', [None, -5, 0])
def test_non_positive_collection_interval_uses_default(instance_basic, collection_interval):
    instance = _make_do_instance(instance_basic, queries=[])
    instance['data_observability']['collection_interval'] = collection_interval

    check = MySql(common.CHECK_NAME, {}, [instance])

    assert check.data_observability._rate_limiter.rate_limit_s == pytest.approx(1 / 10)


def test_emit_failure_metric(instance_basic, aggregator, monkeypatch):
    mock_conn, _ = _make_mock_conn()
    check = _create_check(instance_basic)
    check.data_observability._db = mock_conn

    def boom(*args, **kwargs):
        raise json.JSONDecodeError('boom', 'doc', 0)

    monkeypatch.setattr('datadog_checks.mysql.data_observability.json.dumps', boom)
    check.data_observability.run_job()

    failures = aggregator.metrics('dd.mysql.data_observability.emit_failures')
    assert len(failures) == 1
    assert 'exc_class:JSONDecodeError' in failures[0].tags
    assert 'monitor_id:1' in failures[0].tags


def test_cancelled_job_aborts_query_before_execution(instance_basic):
    """Cancelling mid-batch must stop the queries that have not run yet."""
    check = _create_check(instance_basic)
    job = check.data_observability
    conn, cursor = _make_mock_conn()
    job.cancel()

    with pytest.raises(Exception, match='cancelled'):
        job._execute_single_query(conn, job._queries[0])

    cursor.execute.assert_not_called()
