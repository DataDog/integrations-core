# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.data_observability import EVENT_TRACK_TYPE

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
        'schema': 'public',
        'table': 'orders',
    },
}

MULTI_QUERIES = [
    BASE_QUERY,
    {
        'monitor_id': 2,
        'dbname': 'test_db',
        'query': 'SELECT count(*) FROM users',
        'interval_seconds': 120,
        'type': 'freshness',
        'entity': {
            'platform': 'aws',
            'account': '123456',
            'database': 'test_db',
            'schema': 'public',
            'table': 'users',
        },
    },
]


def _make_do_instance(pg_instance, queries=None, config_id='test-config-123'):
    instance = deepcopy(pg_instance)
    instance['data_observability'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 10,
        'config_id': config_id,
        'queries': queries if queries is not None else [deepcopy(BASE_QUERY)],
    }
    return instance


def _make_mock_conn(rows=None, description=None, broken=False):
    mock_conn = MagicMock()
    mock_conn.broken = broken
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.description = description or [('count',)]
    mock_cursor.fetchmany.return_value = rows if rows is not None else [(42,)]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def _mock_db_pool(mock_conn):
    """Create a mock db_pool whose get_connection returns a context manager wrapping mock_conn."""
    mock_pool = MagicMock()

    @contextmanager
    def get_connection(dbname=None):
        yield mock_conn

    mock_pool.get_connection = MagicMock(side_effect=get_connection)
    return mock_pool


def _create_check(pg_instance, queries=None, config_id='test-config-123'):
    instance = _make_do_instance(pg_instance, queries=queries, config_id=config_id)
    check = PostgreSql('postgres', {}, [instance])
    return check


def _setup_and_run(pg_instance, queries=None, config_id='test-config-123', mock_conn=None, mock_cursor=None):
    if mock_conn is None:
        mock_conn, mock_cursor = _make_mock_conn()

    check = _create_check(pg_instance, queries=queries, config_id=config_id)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()
    return check, mock_conn, mock_cursor


def _get_do_event_calls(mock_epe):
    """Filter event_platform_event calls to only do-query-results events."""
    return [c for c in mock_epe.call_args_list if len(c[0]) >= 2 and c[0][1] == EVENT_TRACK_TYPE]


def test_no_queries_does_nothing(aggregator, pg_instance):
    check = _create_check(pg_instance, queries=[])
    mock_pool = MagicMock()
    check.db_pool = mock_pool

    check.data_observability.run_job()

    mock_pool.get_connection.assert_not_called()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0


def test_single_query_success(aggregator, pg_instance):
    _setup_and_run(pg_instance)

    aggregator.assert_metric('dd.postgres.data_observability.query_execution_time')
    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(metrics) == 1
    assert metrics[0].value == 1
    assert 'status:success' in metrics[0].tags


def test_query_failure_database_error(aggregator, pg_instance):
    """DatabaseError (e.g. syntax error) is caught per-query; execution continues."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("syntax error")

    _setup_and_run(pg_instance, mock_conn=mock_conn, mock_cursor=mock_cursor)

    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(metrics) == 1
    assert metrics[0].value == 1
    assert 'status:error' in metrics[0].tags


def test_connection_failure_propagates(pg_instance):
    """Connection errors propagate to _job_loop for proper crash detection."""
    check = _create_check(pg_instance)
    mock_pool = MagicMock()
    mock_pool.get_connection = MagicMock(side_effect=psycopg.OperationalError("Connection refused"))
    check.db_pool = mock_pool

    with pytest.raises(psycopg.OperationalError, match="Connection refused"):
        check.data_observability.run_job()


def test_interface_error_propagates(pg_instance):
    """InterfaceError (broken connection mid-loop) propagates instead of being swallowed per-query."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.InterfaceError("connection closed")

    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    with pytest.raises(psycopg.InterfaceError, match="connection closed"):
        check.data_observability.run_job()


def test_operational_error_with_broken_conn_propagates(pg_instance):
    """OperationalError on a broken connection re-raises instead of being caught per-query."""
    mock_conn, mock_cursor = _make_mock_conn(broken=True)
    mock_cursor.execute.side_effect = psycopg.OperationalError("server closed the connection")

    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    with pytest.raises(psycopg.OperationalError, match="server closed"):
        check.data_observability.run_job()


def test_per_query_interval_tracking(aggregator, pg_instance):
    mock_conn, _ = _make_mock_conn()

    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    # First run: query executes
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1

    # Immediate second run: query skipped (interval not elapsed)
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Reset _last_execution to force re-run
    aggregator.reset()
    check.data_observability._last_execution = {1: 0.0}
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1


def test_multi_query_execution(aggregator, pg_instance):
    _setup_and_run(pg_instance, queries=deepcopy(MULTI_QUERIES))

    time_metrics = aggregator.metrics('dd.postgres.data_observability.query_execution_time')
    assert len(time_metrics) == 2

    status_metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert all(m.value == 1 for m in status_metrics)
    assert all('status:success' in m.tags for m in status_metrics)


def test_event_payload_structure(aggregator, pg_instance):
    mock_conn, _ = _make_mock_conn(rows=[(42,)], description=[('count',)])

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        assert len(do_calls) == 1
        raw_event = do_calls[0][0][0]
        event_type = do_calls[0][0][1]
        payload = json.loads(raw_event)

    assert event_type == EVENT_TRACK_TYPE
    assert payload['config_id'] == 'test-config-123'
    assert payload['db_type'] == 'postgres'
    assert payload['monitor_id'] == 1
    assert payload['status'] == 'success'
    assert payload['columns'] == ['count']
    assert payload['rows'] == [[42]]
    assert payload['row_count'] == 1
    assert payload['error'] is None
    assert 'duration_s' in payload
    assert 'timestamp' in payload
    assert 'db_host' in payload
    assert 'db_port' in payload
    assert 'db_name' in payload


def test_entity_schema_alias(aggregator, pg_instance):
    mock_conn, _ = _make_mock_conn()

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['entity']['schema'] == 'public'
    assert 'schema_' not in payload['entity']


def test_query_failure_does_not_block_subsequent(aggregator, pg_instance):
    """First query raises DatabaseError, second query still runs."""
    mock_conn, mock_cursor = _make_mock_conn()
    call_count = 0

    def execute_side_effect(sql, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise psycopg.errors.ProgrammingError("table not found")

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    _setup_and_run(pg_instance, queries=deepcopy(MULTI_QUERIES), mock_conn=mock_conn, mock_cursor=mock_cursor)

    status_metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(status_metrics) == 2


def test_no_description_does_not_block_subsequent(aggregator, pg_instance):
    """First query returns None description (non-SELECT), second query still runs."""
    mock_conn, mock_cursor = _make_mock_conn()
    call_count = 0

    def execute_side_effect(sql, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_cursor.description = None if call_count == 1 else [('count',)]

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    _setup_and_run(pg_instance, queries=deepcopy(MULTI_QUERIES), mock_conn=mock_conn, mock_cursor=mock_cursor)

    status_metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert 'status:error' in status_metrics[0].tags
    assert 'status:success' in status_metrics[1].tags


def test_custom_sql_select_fields_in_payload(aggregator, pg_instance):
    query = deepcopy(BASE_QUERY)
    query['custom_sql_select_fields'] = {
        'metric_config_id': 42,
        'entity_id': 'ent-abc-123',
    }
    mock_conn, _ = _make_mock_conn()

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance, queries=[query])
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    custom = payload['custom_sql_select_fields']
    assert custom['metric_config_id'] == 42
    assert custom['entity_id'] == 'ent-abc-123'


def test_dd_column_names_in_payload(aggregator, pg_instance):
    dd_cols = [('dd_count_failed_queries',), ('dd_gauge_latency_ms',), ('dd_tag_schema_name',)]
    mock_conn, _ = _make_mock_conn(rows=[(500, 0.42, 'public')], description=dd_cols)

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['columns'] == ['dd_count_failed_queries', 'dd_gauge_latency_ms', 'dd_tag_schema_name']
    assert payload['rows'] == [[500, 0.42, 'public']]


def test_tags_include_monitor_id(aggregator, pg_instance):
    _setup_and_run(pg_instance)

    time_metrics = aggregator.metrics('dd.postgres.data_observability.query_execution_time')
    assert len(time_metrics) == 1
    assert 'monitor_id:1' in time_metrics[0].tags
    assert 'config_id:test-config-123' in time_metrics[0].tags
    assert 'db_type:postgres' in time_metrics[0].tags

    exec_metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(exec_metrics) == 1
    assert 'monitor_id:1' in exec_metrics[0].tags
    assert 'config_id:test-config-123' in exec_metrics[0].tags
    assert 'db_type:postgres' in exec_metrics[0].tags
    assert 'status:success' in exec_metrics[0].tags


def test_query_with_no_description(aggregator, pg_instance):
    """Non-SELECT queries (cursor.description is None) are caught per-query and emit an error result."""
    mock_conn, mock_cursor = _make_mock_conn()

    def execute_side_effect(sql, *args, **kwargs):
        mock_cursor.description = None

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['status'] == 'error'
    assert 'result set' in payload['error']
    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:error' in metrics[0].tags


def test_collection_interval_none_uses_default(pg_instance):
    """collection_interval=None should not crash, uses default."""
    instance = deepcopy(pg_instance)
    instance['data_observability'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': None,
        'queries': [],
    }
    check = PostgreSql('postgres', {}, [instance])
    assert check.data_observability._enabled


def test_failed_query_updates_last_execution(aggregator, pg_instance):
    """A failed query still updates _last_execution so it's not retried until the next interval."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("syntax error")

    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    check.data_observability.run_job()
    assert 1 in check.data_observability._last_execution

    # Immediate re-run should skip the query (interval not elapsed)
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0


def test_error_event_payload(aggregator, pg_instance):
    """When a query fails, the event payload contains error details."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("relation does not exist")

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        assert len(do_calls) == 1
        payload = json.loads(do_calls[0][0][0])

    assert payload['status'] == 'error'
    assert 'relation does not exist' in payload['error']
    assert payload['columns'] == []
    assert payload['rows'] == []
    assert payload['row_count'] == 0
    assert payload['monitor_id'] == 1
    assert 'duration_s' in payload


def test_fetchmany_called_with_max_rows(pg_instance):
    """fetchmany is called with MAX_RESULT_ROWS to cap memory usage."""
    from datadog_checks.postgres.data_observability import MAX_RESULT_ROWS

    mock_conn, mock_cursor = _make_mock_conn()

    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    mock_cursor.fetchmany.assert_called_once_with(MAX_RESULT_ROWS)


# --- Per-query dbname tests ---


def test_per_query_dbname_used_for_connection(aggregator, pg_instance):
    """db_pool.get_connection is called with the query's dbname."""
    query = deepcopy(BASE_QUERY)
    query['dbname'] = 'other_db'
    mock_conn, _ = _make_mock_conn()

    check = _create_check(pg_instance, queries=[query])
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    check.db_pool.get_connection.assert_called_once_with('other_db')


def test_per_query_dbname_in_event_payload(aggregator, pg_instance):
    """The event payload db_name reflects the query's dbname."""
    query = deepcopy(BASE_QUERY)
    query['dbname'] = 'analytics_db'
    mock_conn, _ = _make_mock_conn()

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance, queries=[query])
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['db_name'] == 'analytics_db'


def test_multi_query_different_dbnames(aggregator, pg_instance):
    """Multiple queries with different dbnames each connect to the correct database."""
    queries = [
        {**deepcopy(BASE_QUERY), 'dbname': 'db_one'},
        {**deepcopy(MULTI_QUERIES[1]), 'dbname': 'db_two'},
    ]
    mock_conn, _ = _make_mock_conn()

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance, queries=queries)
        check.db_pool = _mock_db_pool(mock_conn)
        check.data_observability.run_job()

        calls = check.db_pool.get_connection.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == 'db_one'
        assert calls[1][0][0] == 'db_two'

        do_calls = _get_do_event_calls(mock_epe)
        payload_1 = json.loads(do_calls[0][0][0])
        payload_2 = json.loads(do_calls[1][0][0])

    assert payload_1['db_name'] == 'db_one'
    assert payload_2['db_name'] == 'db_two'
