# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from copy import deepcopy
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.data_observability import EVENT_TRACK_TYPE

pytestmark = pytest.mark.unit

BASE_QUERY = {
    'monitor_id': 1,
    'query': 'SELECT count(*) FROM orders',
    'interval_seconds': 60,
    'timeout_seconds': 10,
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
        'query': 'SELECT count(*) FROM users',
        'interval_seconds': 120,
        'timeout_seconds': 5,
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


def _make_mock_conn(rows=None, description=None):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.description = description or [('count',)]
    mock_cursor.fetchmany.return_value = rows if rows is not None else [(42,)]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def _mock_get_main_db(mock_conn):
    """Create a mock _get_main_db that returns a context manager wrapping mock_conn."""
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_ctx)


def _create_check(pg_instance, queries=None, config_id='test-config-123'):
    instance = _make_do_instance(pg_instance, queries=queries, config_id=config_id)
    check = PostgreSql('postgres', {}, [instance])
    return check


def _setup_and_run(pg_instance, queries=None, config_id='test-config-123', mock_conn=None, mock_cursor=None):
    if mock_conn is None:
        mock_conn, mock_cursor = _make_mock_conn()

    check = _create_check(pg_instance, queries=queries, config_id=config_id)
    check._get_main_db = _mock_get_main_db(mock_conn)
    check.data_observability.run_job()
    return check, mock_conn, mock_cursor


def _get_do_event_calls(mock_epe):
    """Filter event_platform_event calls to only do-query-results events."""
    return [c for c in mock_epe.call_args_list if len(c[0]) >= 2 and c[0][1] == EVENT_TRACK_TYPE]


def test_no_queries_does_nothing(aggregator, pg_instance):
    check = _create_check(pg_instance, queries=[])
    mock_get_main_db = MagicMock()
    check._get_main_db = mock_get_main_db

    check.data_observability.run_job()

    mock_get_main_db.assert_not_called()
    assert len(aggregator.metrics('postgresql.data_observability.query_status')) == 0


def test_single_query_success(aggregator, pg_instance):
    _setup_and_run(pg_instance)

    aggregator.assert_metric('postgresql.data_observability.query_execution_time')
    aggregator.assert_metric('postgresql.data_observability.query_status', value=1)


def test_query_failure_database_error(aggregator, pg_instance):
    """DatabaseError (e.g. syntax error) is caught per-query; execution continues."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("syntax error")

    _setup_and_run(pg_instance, mock_conn=mock_conn, mock_cursor=mock_cursor)

    aggregator.assert_metric('postgresql.data_observability.query_status', value=0)


def test_connection_failure_propagates(pg_instance):
    """Connection errors propagate to _job_loop for proper crash detection."""
    check = _create_check(pg_instance)
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(side_effect=psycopg.OperationalError("Connection refused"))
    mock_ctx.__exit__ = MagicMock(return_value=False)
    check._get_main_db = MagicMock(return_value=mock_ctx)

    with pytest.raises(psycopg.OperationalError, match="Connection refused"):
        check.data_observability.run_job()


def test_interface_error_propagates(pg_instance):
    """InterfaceError (broken connection mid-loop) propagates instead of being swallowed per-query."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.InterfaceError("connection closed")

    check = _create_check(pg_instance)
    check._get_main_db = _mock_get_main_db(mock_conn)

    with pytest.raises(psycopg.InterfaceError, match="connection closed"):
        check.data_observability.run_job()


def test_per_query_interval_tracking(aggregator, pg_instance):
    mock_conn, _ = _make_mock_conn()

    check = _create_check(pg_instance)
    check._get_main_db = _mock_get_main_db(mock_conn)

    # First run: query executes
    check.data_observability.run_job()
    assert len(aggregator.metrics('postgresql.data_observability.query_status')) == 1

    # Immediate second run: query skipped (interval not elapsed)
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('postgresql.data_observability.query_status')) == 0

    # Reset _last_execution to force re-run
    aggregator.reset()
    check.data_observability._last_execution = {1: 0.0}
    check.data_observability.run_job()
    assert len(aggregator.metrics('postgresql.data_observability.query_status')) == 1


def test_multi_query_execution(aggregator, pg_instance):
    _setup_and_run(pg_instance, queries=deepcopy(MULTI_QUERIES))

    time_metrics = aggregator.metrics('postgresql.data_observability.query_execution_time')
    assert len(time_metrics) == 2

    status_metrics = aggregator.metrics('postgresql.data_observability.query_status')
    assert len(status_metrics) == 2
    for m in status_metrics:
        assert m.value == 1


def test_event_payload_structure(aggregator, pg_instance):
    mock_conn, _ = _make_mock_conn(rows=[(42,)], description=[('count',)])

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check._get_main_db = _mock_get_main_db(mock_conn)
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
        check._get_main_db = _mock_get_main_db(mock_conn)
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

    status_metrics = aggregator.metrics('postgresql.data_observability.query_status')
    assert len(status_metrics) == 2


def test_custom_sql_select_fields_in_payload(aggregator, pg_instance):
    query = deepcopy(BASE_QUERY)
    query['custom_sql_select_fields'] = {
        'metric_config_id': 42,
        'entity_id': 'ent-abc-123',
    }
    mock_conn, _ = _make_mock_conn()

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance, queries=[query])
        check._get_main_db = _mock_get_main_db(mock_conn)
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
        check._get_main_db = _mock_get_main_db(mock_conn)
        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['columns'] == ['dd_count_failed_queries', 'dd_gauge_latency_ms', 'dd_tag_schema_name']
    assert payload['rows'] == [[500, 0.42, 'public']]


def test_tags_include_monitor_id(aggregator, pg_instance):
    _setup_and_run(pg_instance)

    for metric_name in [
        'postgresql.data_observability.query_execution_time',
        'postgresql.data_observability.query_status',
    ]:
        metrics = aggregator.metrics(metric_name)
        assert len(metrics) == 1
        tags = metrics[0].tags
        assert 'monitor_id:1' in tags
        assert 'config_id:test-config-123' in tags
        assert 'db_type:postgres' in tags


def test_query_with_no_description(aggregator, pg_instance):
    mock_conn, mock_cursor = _make_mock_conn()

    def execute_side_effect(sql, *args, **kwargs):
        mock_cursor.description = None

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        _setup_and_run(pg_instance, mock_conn=mock_conn, mock_cursor=mock_cursor)

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    aggregator.assert_metric('postgresql.data_observability.query_status', value=1)
    assert payload['columns'] == []
    assert payload['rows'] == []
    assert payload['row_count'] == 0


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
    # Should not raise; verifies issue #4 fix
    assert check.data_observability._enabled


def test_failed_query_updates_last_execution(aggregator, pg_instance):
    """A failed query still updates _last_execution so it's not retried until the next interval."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("syntax error")

    check = _create_check(pg_instance)
    check._get_main_db = _mock_get_main_db(mock_conn)

    check.data_observability.run_job()
    assert 1 in check.data_observability._last_execution

    # Immediate re-run should skip the query (interval not elapsed)
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('postgresql.data_observability.query_status')) == 0


def test_error_event_payload(aggregator, pg_instance):
    """When a query fails, the event payload contains error details."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("relation does not exist")

    with patch.object(PostgreSql, 'event_platform_event') as mock_epe:
        check = _create_check(pg_instance)
        check._get_main_db = _mock_get_main_db(mock_conn)
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
