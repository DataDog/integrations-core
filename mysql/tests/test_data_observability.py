# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import calendar
import datetime
import json
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.data_observability import EVENT_TRACK_TYPE

_BASE_EPOCH = calendar.timegm(datetime.datetime(2026, 1, 1, 0, 49, 0).timetuple())

pytestmark = pytest.mark.unit

BASE_QUERY = {
    'monitor_id': 1,
    'dbname': 'test_db',
    'query': 'SELECT count(*) FROM orders',
    'interval_seconds': 60,
    'type': 'freshness',
    'entity': {
        'platform': 'aws',
        'account': '123456',
        'database': 'test_db',
        'schema': 'test_db',
        'table': 'orders',
    },
}

SECOND_QUERY = {
    'monitor_id': 2,
    'dbname': 'other_db',
    'query': 'SELECT count(*) FROM users',
    'interval_seconds': 120,
    'type': 'freshness',
    'entity': {
        'platform': 'aws',
        'account': '123456',
        'database': 'other_db',
        'schema': 'other_db',
        'table': 'users',
    },
}

CRON_QUERY = {
    'monitor_id': 10,
    'dbname': 'test_db',
    'query': 'SELECT 1',
    'schedule': '50 * * * *',
    'type': 'freshness',
    'entity': {
        'platform': 'aws',
        'account': '123456',
        'database': 'test_db',
        'schema': 'test_db',
        'table': 'orders',
    },
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


def _create_check(instance_basic, queries=None, config_id='test-config-123'):
    return MySql('mysql', {}, [_make_do_instance(instance_basic, queries=queries, config_id=config_id)])


def _make_mock_conn(rows=None, description=None):
    mock_conn = MagicMock()
    mock_conn.open = True
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.description = description or [('count',)]
    mock_cursor.fetchmany.return_value = rows if rows is not None else [(42,)]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def _patch_connection(monkeypatch, mock_conn):
    connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr('datadog_checks.mysql.data_observability.connect_with_session_variables', connect)
    return connect


def _setup_and_run(instance_basic, monkeypatch, queries=None, mock_conn=None):
    if mock_conn is None:
        mock_conn, mock_cursor = _make_mock_conn()
    else:
        mock_cursor = mock_conn.cursor.return_value
    connect = _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic, queries=queries)
    check._data_observability.run_job()
    return check, mock_conn, mock_cursor, connect


def _get_do_event_calls(mock_epe):
    return [c for c in mock_epe.call_args_list if len(c[0]) >= 2 and c[0][1] == EVENT_TRACK_TYPE]


def test_no_queries_does_nothing(instance_basic, monkeypatch, aggregator):
    mock_conn, _ = _make_mock_conn()
    connect = _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic, queries=[])

    check._data_observability.run_job()

    connect.assert_not_called()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 0


def test_single_query_success_uses_database(instance_basic, monkeypatch, aggregator):
    _, _, mock_cursor, _ = _setup_and_run(instance_basic, monkeypatch)

    assert mock_cursor.execute.call_args_list[0][0][0] == 'USE `test_db`'
    assert mock_cursor.execute.call_args_list[1][0][0] == 'SELECT count(*) FROM orders'
    aggregator.assert_metric('dd.mysql.data_observability.query_execution_time')
    metrics = aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:success' in metrics[0].tags


def test_event_payload_structure(instance_basic, monkeypatch):
    mock_conn, _ = _make_mock_conn(rows=[(42,)], description=[('count',)])
    _patch_connection(monkeypatch, mock_conn)

    with patch.object(MySql, 'event_platform_event') as mock_epe:
        check = _create_check(instance_basic)
        check._data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert do_calls[0][0][1] == EVENT_TRACK_TYPE
    assert payload['config_id'] == 'test-config-123'
    assert payload['db_type'] == 'mysql'
    assert payload['db_name'] == 'test_db'
    assert payload['monitor_id'] == 1
    assert payload['status'] == 'success'
    assert payload['columns'] == ['count']
    assert payload['rows'] == [[42]]
    assert payload['row_count'] == 1
    assert payload['entity']['schema'] == 'test_db'
    assert 'schema_' not in payload['entity']


def test_custom_sql_select_fields_in_payload(instance_basic, monkeypatch):
    query = deepcopy(BASE_QUERY)
    query['custom_sql_select_fields'] = {
        'metric_config_id': 42,
        'entity_id': 'ent-abc-123',
    }
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)

    with patch.object(MySql, 'event_platform_event') as mock_epe:
        check = _create_check(instance_basic, queries=[query])
        check._data_observability.run_job()
        payload = json.loads(_get_do_event_calls(mock_epe)[0][0][0])

    assert payload['custom_sql_select_fields'] == {
        'metric_config_id': 42,
        'entity_id': 'ent-abc-123',
    }


def test_tags_include_monitor_id_config_id_and_db_type(instance_basic, monkeypatch, aggregator):
    _setup_and_run(instance_basic, monkeypatch)

    metric = aggregator.metrics('dd.mysql.data_observability.query_executions')[0]
    assert 'monitor_id:1' in metric.tags
    assert 'config_id:test-config-123' in metric.tags
    assert 'db_type:mysql' in metric.tags
    assert 'status:success' in metric.tags


def test_query_failure_does_not_block_subsequent(instance_basic, monkeypatch, aggregator):
    mock_conn, mock_cursor = _make_mock_conn()
    call_count = 0

    def execute_side_effect(sql, *args, **kwargs):
        nonlocal call_count
        if not sql.startswith('USE'):
            call_count += 1
            if call_count == 1:
                raise pymysql.err.ProgrammingError("table not found")

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)
    _setup_and_run(
        instance_basic, monkeypatch, queries=[deepcopy(BASE_QUERY), deepcopy(SECOND_QUERY)], mock_conn=mock_conn
    )

    status_metrics = aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert 'status:error' in status_metrics[0].tags
    assert 'status:success' in status_metrics[1].tags


def test_no_description_does_not_block_subsequent(instance_basic, monkeypatch, aggregator):
    mock_conn, mock_cursor = _make_mock_conn()
    call_count = 0

    def execute_side_effect(sql, *args, **kwargs):
        nonlocal call_count
        if not sql.startswith('USE'):
            call_count += 1
            mock_cursor.description = None if call_count == 1 else [('count',)]

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)
    _setup_and_run(
        instance_basic, monkeypatch, queries=[deepcopy(BASE_QUERY), deepcopy(SECOND_QUERY)], mock_conn=mock_conn
    )

    status_metrics = aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert 'status:error' in status_metrics[0].tags
    assert 'status:success' in status_metrics[1].tags


def test_invalid_dbname_returns_error(instance_basic, monkeypatch, aggregator):
    query = deepcopy(BASE_QUERY)
    query['dbname'] = 'bad-name'
    mock_conn, _ = _make_mock_conn()

    with patch.object(MySql, 'event_platform_event') as mock_epe:
        check, _, _, _ = _setup_and_run(instance_basic, monkeypatch, queries=[query], mock_conn=mock_conn)
        payload = json.loads(_get_do_event_calls(mock_epe)[0][0][0])

    assert payload['status'] == 'error'
    assert "Invalid database name" in payload['error']
    assert 'status:error' in aggregator.metrics('dd.mysql.data_observability.query_executions')[0].tags
    assert check._data_observability._last_execution[1] > 0


def test_connection_failure_propagates(instance_basic, monkeypatch):
    connect = MagicMock(side_effect=pymysql.err.OperationalError("Connection refused"))
    monkeypatch.setattr('datadog_checks.mysql.data_observability.connect_with_session_variables', connect)
    check = _create_check(instance_basic)

    with pytest.raises(pymysql.err.OperationalError, match="Connection refused"):
        check._data_observability.run_job()


def test_broken_connection_error_propagates(instance_basic, monkeypatch):
    mock_conn, mock_cursor = _make_mock_conn()

    def execute_side_effect(sql, *args, **kwargs):
        if not sql.startswith('USE'):
            mock_conn.open = False
            raise pymysql.err.OperationalError("server closed the connection")

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)
    _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic)

    with pytest.raises(pymysql.err.OperationalError, match="server closed"):
        check._data_observability.run_job()


def test_fetchmany_called_with_max_rows(instance_basic, monkeypatch):
    from datadog_checks.mysql.data_observability import MAX_RESULT_ROWS

    _, _, mock_cursor, _ = _setup_and_run(instance_basic, monkeypatch)

    mock_cursor.fetchmany.assert_called_once_with(MAX_RESULT_ROWS)


def test_reuses_open_connection_between_runs(instance_basic, monkeypatch, aggregator):
    mock_conn, _ = _make_mock_conn()
    connect = _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic)

    check._data_observability.run_job()
    check._data_observability._last_execution[1] = 0.0
    aggregator.reset()
    check._data_observability.run_job()

    connect.assert_called_once()


def test_invalid_cron_schedule_filtered_at_init(instance_basic, monkeypatch, aggregator, caplog):
    bad = {**deepcopy(CRON_QUERY), 'monitor_id': 20, 'schedule': 'not-a-cron'}
    good = deepcopy(BASE_QUERY)
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)

    with caplog.at_level('WARNING'):
        check = _create_check(instance_basic, queries=[bad, good])

    assert {q.monitor_id for q in check._data_observability._queries} == {1}
    assert any('invalid cron schedule' in r.message for r in caplog.records)
    check._data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_query_without_schedule_or_positive_interval_filtered_at_init(instance_basic, caplog):
    query = deepcopy(BASE_QUERY)
    query.pop('interval_seconds')

    with caplog.at_level('WARNING'):
        check = _create_check(instance_basic, queries=[query])

    assert check._data_observability._queries == ()
    assert any('neither schedule nor positive interval_seconds' in r.message for r in caplog.records)


def test_schedule_query_fires_at_cron_tick(instance_basic, monkeypatch, aggregator):
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic, queries=[deepcopy(CRON_QUERY)])

    check._data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 0

    current_time[0] = _BASE_EPOCH + 65
    aggregator.reset()
    check._data_observability.run_job()

    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_schedule_takes_precedence_over_interval_seconds(instance_basic, monkeypatch, aggregator):
    query = deepcopy(CRON_QUERY)
    query['interval_seconds'] = 5
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic, queries=[query])

    check._data_observability.run_job()
    current_time[0] = _BASE_EPOCH + 10
    check._data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 0

    current_time[0] = _BASE_EPOCH + 65
    check._data_observability.run_job()
    assert len(aggregator.metrics('dd.mysql.data_observability.query_executions')) == 1


def test_lateness_metric_emitted_for_interval(instance_basic, monkeypatch, aggregator):
    current_time = [1000.0]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic)

    check._data_observability.run_job()
    lateness_metrics = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert lateness_metrics[0].value == 0.0
    assert 'mode:interval' in lateness_metrics[0].tags

    current_time[0] = 1080.0
    aggregator.reset()
    check._data_observability.run_job()
    lateness_metrics = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')
    assert abs(lateness_metrics[0].value - 20.0) < 1.0


def test_cron_startup_lookback_recovers_missed_fire(instance_basic, monkeypatch, aggregator):
    current_time = [float(_BASE_EPOCH + 70)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic, queries=[deepcopy(CRON_QUERY)])

    check._data_observability.run_job()

    metrics = aggregator.metrics('dd.mysql.data_observability.query_executions')
    assert len(metrics) == 1
    lateness_metrics = aggregator.metrics('dd.mysql.data_observability.query_fire_lateness_seconds')
    assert 5.0 <= lateness_metrics[0].value <= 15.0
    assert 'mode:cron' in lateness_metrics[0].tags


def test_failed_cron_query_advances_next_run(instance_basic, monkeypatch, aggregator):
    current_time = [float(_BASE_EPOCH + 65)]
    monkeypatch.setattr('datadog_checks.mysql.data_observability.time.time', lambda: current_time[0])
    mock_conn, mock_cursor = _make_mock_conn()

    def execute_side_effect(sql, *args, **kwargs):
        if not sql.startswith('USE'):
            raise pymysql.err.ProgrammingError("table not found")

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)
    _patch_connection(monkeypatch, mock_conn)
    check = _create_check(instance_basic, queries=[deepcopy(CRON_QUERY)])

    check._data_observability.run_job()
    registered = check._data_observability._next_run[10]
    current_time[0] = _BASE_EPOCH + 3665
    aggregator.reset()
    check._data_observability.run_job()

    assert 'status:error' in aggregator.metrics('dd.mysql.data_observability.query_executions')[0].tags
    assert check._data_observability._next_run[10] > registered


def test_emit_failures_metric_on_emit_path_exception(instance_basic, monkeypatch, aggregator):
    mock_conn, _ = _make_mock_conn()
    _patch_connection(monkeypatch, mock_conn)

    def boom(*args, **kwargs):
        raise json.JSONDecodeError("boom", "doc", 0)

    monkeypatch.setattr('datadog_checks.mysql.data_observability.json.dumps', boom)
    check = _create_check(instance_basic)
    check._data_observability.run_job()

    failures = aggregator.metrics('dd.mysql.data_observability.emit_failures')
    assert len(failures) == 1
    assert 'monitor_id:1' in failures[0].tags
    assert any(t.startswith('exc_class:JSONDecodeError') for t in failures[0].tags)
