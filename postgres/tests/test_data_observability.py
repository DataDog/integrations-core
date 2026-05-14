# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import calendar
import datetime
import json
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.data_observability import EVENT_TRACK_TYPE

# Fixed epoch (2026-01-01 00:49:00 UTC) chosen to sit 1 minute before the ":50" cron tick used in tests.
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

    # Reset last_execution to force re-run
    aggregator.reset()
    check.data_observability._last_execution[1] = 0.0
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
    """A failed query still updates last_execution so it's not retried until the next interval."""
    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("syntax error")

    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    check.data_observability.run_job()
    assert 1 in check.data_observability._last_execution
    assert check.data_observability._last_execution[1] > 0

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


def test_query_with_no_description(aggregator, pg_instance):
    """Non-SELECT queries (cursor.description is None) trigger the inner-raised ProgrammingError path
    and surface 'result set' in the error payload."""
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
    """Each query in a multi-query batch routes its own dbname to get_connection and its payload."""
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


# ---------------------------------------------------------------------------
# Cron schedule tests
# ---------------------------------------------------------------------------

CRON_QUERY = {
    'monitor_id': 10,
    'dbname': 'test_db',
    'query': 'SELECT 1',
    'schedule': '50 * * * *',  # every hour at :50
    'type': 'freshness',
    'entity': {
        'platform': 'aws',
        'account': '123456',
        'database': 'test_db',
        'schema': 'public',
        'table': 'orders',
    },
}


def _make_cron_check(pg_instance, queries=None):
    if queries is None:
        queries = [deepcopy(CRON_QUERY)]
    return _create_check(pg_instance, queries=queries)


def test_schedule_query_does_not_fire_before_tick(pg_instance, monkeypatch):
    """First-sight cron registers next_run without firing.

    Clock sits at 00:49:00, 59 minutes after the previous :50 tick — well
    outside the 300s lookback window — so first-sight recovery does not
    fire either. The next tick (00:50:00) is still 60s in the future.
    """
    current_time = [float(_BASE_EPOCH)]  # 00:49:00
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    mock_conn.cursor.assert_not_called()


def test_schedule_query_fires_at_cron_tick(pg_instance, aggregator, monkeypatch):
    """A cron query fires after its first tick has passed."""
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    # First call: registers next_run (tick at 00:50:00) but does NOT fire.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Advance past 00:50:00
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1


def test_schedule_advances_after_run(pg_instance, monkeypatch):
    """After a cron fire, _next_run is advanced to the NEXT future tick (not the same tick)."""
    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 — already past the tick
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    # First run at 00:50:05: registers next_run = 01:50:00 (croniter.get_next is strictly after now); no fire.
    check.data_observability.run_job()
    mid = CRON_QUERY['monitor_id']
    first_next_run = check.data_observability._next_run[mid]

    current_time[0] = _BASE_EPOCH + 3665  # ~01:50:05
    check.data_observability.run_job()

    second_next_run = check.data_observability._next_run[mid]
    # After firing at 01:50:05, next_run should advance to 02:50:00
    assert second_next_run > first_next_run
    # Should be approximately 1 hour later
    assert second_next_run - first_next_run >= 3600 - 10


def test_schedule_takes_precedence_over_interval_seconds(pg_instance, aggregator, monkeypatch):
    query = deepcopy(CRON_QUERY)
    query['interval_seconds'] = 5  # Very short interval — should be ignored.

    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _create_check(pg_instance, queries=[query])
    check.db_pool = _mock_db_pool(mock_conn)

    # First call at 00:49:00: registers cron next_run (00:50:00), does NOT fire despite interval=5 passing.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Advance 10s (interval would have fired, but cron tick not reached yet).
    current_time[0] = _BASE_EPOCH + 10  # 00:49:10 — past 5s interval, but not yet :50.
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Now advance past 00:50:00.
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1


def test_invalid_cron_schedule_filtered_at_init(pg_instance, aggregator, caplog):
    """A query with an unparseable cron string is dropped at construction; siblings still run."""
    import logging

    bad = {**deepcopy(CRON_QUERY), 'monitor_id': 20, 'schedule': 'not-a-cron'}
    good = deepcopy(BASE_QUERY)  # interval-based, monitor_id=1

    mock_conn, _ = _make_mock_conn()
    with caplog.at_level(logging.WARNING):
        check = _create_check(pg_instance, queries=[bad, good])
    assert {q.monitor_id for q in check.data_observability._queries} == {1}
    assert any('invalid cron schedule' in r.message and "'not-a-cron'" in r.message for r in caplog.records)

    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()
    monitor_ids_run = {
        int(t.split(':')[1])
        for m in aggregator.metrics('dd.postgres.data_observability.query_executions')
        for t in m.tags
        if t.startswith('monitor_id:')
    }
    assert monitor_ids_run == {1}


def test_query_without_schedule_or_positive_interval_filtered_at_init(pg_instance, caplog):
    """A query with neither schedule nor a positive interval_seconds is dropped at construction."""
    import logging

    query = {
        'monitor_id': 30,
        'dbname': 'test_db',
        'query': 'SELECT 1',
        'type': 'freshness',
        'entity': {
            'platform': 'aws',
            'account': '123456',
            'database': 'test_db',
            'schema': 'public',
            'table': 'foo',
        },
    }
    with caplog.at_level(logging.WARNING):
        check = _create_check(pg_instance, queries=[query])
    assert check.data_observability._queries == ()
    assert any('neither schedule nor positive interval_seconds' in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Lateness metric tests
# ---------------------------------------------------------------------------


def test_lateness_metric_emitted_for_cron(pg_instance, aggregator, monkeypatch):
    """Cron query fired late emits a positive lateness gauge with mode:cron tag."""
    # next_run will be at 00:50:00; fire at 00:52:00 -> 120s lateness.
    fire_time = float(_BASE_EPOCH + 180)  # 00:52:00
    current_time = [float(_BASE_EPOCH)]  # 00:49:00 — before the tick
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    # Step 1: Register next_run (00:50:00)
    check.data_observability.run_job()
    mid = CRON_QUERY['monitor_id']
    scheduled_tick = check.data_observability._next_run[mid]

    # Step 2: Advance to 00:52:00 — 2 minutes late
    current_time[0] = fire_time
    aggregator.reset()
    check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    m = lateness_metrics[0]
    assert m.value >= 0.0
    assert 'mode:cron' in m.tags
    assert f'monitor_id:{mid}' in m.tags
    # Lateness should be fire_time - scheduled_tick ≈ 120s (within 5s tolerance for real-time drift)
    expected_lateness = fire_time - scheduled_tick
    assert abs(m.value - expected_lateness) < 5.0


def test_lateness_metric_emitted_for_interval(pg_instance, aggregator, monkeypatch):
    """Interval query emits lateness gauge with mode:interval tag.

    First fire is lazy-seeded to scheduled = now so lateness is 0; second
    fire after a delay exposes the configured interval as positive lateness.
    """
    current_time = [1000.0]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    query = deepcopy(BASE_QUERY)  # monitor_id=1, interval_seconds=60

    check = _create_check(pg_instance, queries=[query])
    check.db_pool = _mock_db_pool(mock_conn)

    # First fire at t=1000: lazy-seeded last_execution = 940, so scheduled = now -> lateness = 0.
    check.data_observability.run_job()
    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert lateness_metrics[0].value == 0.0
    assert 'mode:interval' in lateness_metrics[0].tags

    # After first fire, last_execution = 1000.0.
    # Second fire at t=1080 (20s late: scheduled = 1000 + 60 = 1060, fired at 1080).
    current_time[0] = 1080.0
    aggregator.reset()
    check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    m = lateness_metrics[0]
    assert 'mode:interval' in m.tags
    # scheduled = last_run(1000) + interval(60) = 1060; fire at 1080 -> lateness = 20.
    assert abs(m.value - 20.0) < 1.0


def test_lateness_clamped_at_zero(pg_instance, aggregator, monkeypatch):
    """If scheduled_fire_time is in the future at fire time (clock skew), lateness is clamped to 0."""
    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 — cron tick 00:50:00 in the past
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    # Patch _get_due_queries to return a scheduled_fire_time in the future of fire_start
    # (synthetic clock-skew scenario). Lateness must clamp to 0 rather than go negative.
    from datadog_checks.postgres.data_observability import DueQuery

    skewed_scheduled = current_time[0] + 100.0
    q = check.data_observability._do_config.queries[0]
    with patch.object(
        check.data_observability,
        '_get_due_queries',
        return_value=[DueQuery(q, skewed_scheduled, "cron")],
    ):
        aggregator.reset()
        check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert lateness_metrics[0].value == 0.0


def test_starved_query_eventually_fires(pg_instance, aggregator, monkeypatch):
    """Query B fires within the same hour even when Query A blocks run_job for >1 minute."""
    # Two cron queries: A at :50, B at :51 (both hourly).
    query_a = {
        **deepcopy(CRON_QUERY),
        'monitor_id': 50,
        'schedule': '50 * * * *',
    }
    query_b = {
        **deepcopy(CRON_QUERY),
        'monitor_id': 51,
        'schedule': '51 * * * *',
    }

    current_time = [float(_BASE_EPOCH)]  # 00:49:00
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _create_check(pg_instance, queries=[query_a, query_b])
    check.db_pool = _mock_db_pool(mock_conn)

    # First run: registers both next_run values (A -> 00:50:00, B -> 00:51:00), fires nothing.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Simulate: clock moves to 00:50:05 — A is due, B is not yet.
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()

    exec_metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    a_ran = any('monitor_id:50' in m.tags for m in exec_metrics)
    b_ran = any('monitor_id:51' in m.tags for m in exec_metrics)
    assert a_ran, "Query A should have fired at 00:50:05"
    assert not b_ran, "Query B should not yet have fired at 00:50:05"

    # Simulate: A took 2m30s -> clock is now 00:52:35. B's tick (00:51:00) has passed.
    current_time[0] = _BASE_EPOCH + 215  # 00:52:35
    aggregator.reset()
    check.data_observability.run_job()

    exec_metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    b_ran_now = any('monitor_id:51' in m.tags for m in exec_metrics)
    assert b_ran_now, "Query B should fire at 00:52:35 (late, but same hour)"

    # B's lateness should be positive (fired ~1m35s after its :51 tick)
    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    b_lateness = [m for m in lateness_metrics if 'monitor_id:51' in m.tags]
    assert len(b_lateness) == 1
    assert b_lateness[0].value > 0.0


# ---------------------------------------------------------------------------
# Cron startup lookback window (recovery of fires lost across check restarts)
# ---------------------------------------------------------------------------


def _make_cron_lookback_check(pg_instance, queries=None, *, monkeypatch=None, window_seconds=None):
    if window_seconds is not None:
        assert monkeypatch is not None, "monkeypatch is required when overriding window_seconds"
        monkeypatch.setattr(
            'datadog_checks.postgres.data_observability.CRON_STARTUP_LOOKBACK_SECONDS',
            window_seconds,
        )
    instance = _make_do_instance(pg_instance, queries=queries or [deepcopy(CRON_QUERY)])
    return PostgreSql('postgres', {}, [instance])


def test_cron_startup_lookback_recovers_missed_fire(pg_instance, aggregator, monkeypatch):
    """A first-sight cron query whose previous tick falls within the lookback window fires immediately."""
    # 00:50:10 — 10s after the 00:50 tick, well inside the default 300s lookback window.
    current_time = [float(_BASE_EPOCH + 70)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_lookback_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(metrics) == 1
    assert any('monitor_id:10' in m.tags for m in metrics)


def test_cron_startup_lookback_disabled_skips_recovery(pg_instance, aggregator, monkeypatch):
    """CRON_STARTUP_LOOKBACK_SECONDS=0 disables first-sight recovery."""
    current_time = [float(_BASE_EPOCH + 70)]  # same scenario as recovery test
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_lookback_check(pg_instance, monkeypatch=monkeypatch, window_seconds=0)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0


def test_cron_startup_lookback_outside_window_skips(pg_instance, aggregator, monkeypatch):
    """A pod starting well past the lookback window does not over-fire."""
    # 00:55:40 — 340s after the 00:50 tick, beyond the default 300s lookback.
    current_time = [float(_BASE_EPOCH + 400)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_lookback_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0


def test_cron_startup_lookback_lateness_reflects_age_of_tick(pg_instance, aggregator, monkeypatch):
    """Recovered fires emit a lateness gauge equal to (now - prev_tick)."""
    # 00:50:30 — 30s after the 00:50 tick.
    current_time = [float(_BASE_EPOCH + 90)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_lookback_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert 25.0 <= lateness_metrics[0].value <= 35.0
    assert 'mode:cron' in lateness_metrics[0].tags


def test_cron_startup_lookback_default_is_300_seconds():
    """The startup lookback window is 5 minutes; pin it so a regression is loud."""
    from datadog_checks.postgres.data_observability import CRON_STARTUP_LOOKBACK_SECONDS

    assert CRON_STARTUP_LOOKBACK_SECONDS == 300


def test_cron_startup_lookback_does_not_double_fire(pg_instance, aggregator, monkeypatch):
    """A startup-recovery fire must not re-fire the same tick on the next run_job() call."""
    current_time = [float(_BASE_EPOCH + 70)]  # 00:50:10 — inside the default 300s lookback
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_lookback_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1

    # Advance a few seconds (still well before the next 01:50 tick); a second run must not re-fire.
    current_time[0] = _BASE_EPOCH + 80
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0


# ---------------------------------------------------------------------------
# State reconciliation, mode caching, and error-path tests
# ---------------------------------------------------------------------------


def test_failed_cron_query_advances_next_run(pg_instance, aggregator, monkeypatch):
    """A failing cron query still advances next_run, so it does not hot-loop on the same tick."""
    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 -- already past the 00:50 tick
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, mock_cursor = _make_mock_conn()
    mock_cursor.execute.side_effect = psycopg.errors.ProgrammingError("relation does not exist")

    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)
    # First run: registers next_run (01:50:00) without firing.
    check.data_observability.run_job()
    mid = CRON_QUERY['monitor_id']
    registered = check.data_observability._next_run[mid]

    # Jump past the next tick and let the failing query fire.
    current_time[0] = _BASE_EPOCH + 3665  # ~01:50:05
    aggregator.reset()
    check.data_observability.run_job()
    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:error' in metrics[0].tags

    # next_run must have advanced past the just-fired tick; otherwise the very next
    # tick would re-fire the same tick in a tight loop.
    advanced = check.data_observability._next_run[mid]
    assert advanced > registered
    assert advanced >= current_time[0]


def test_cron_startup_lookback_boundary_strict_less_than(pg_instance, aggregator, monkeypatch):
    """At exactly the catch-up window since prev_tick, recovery does NOT fire (strict <)."""
    # prev_tick = 00:50:00; window = 60s; clock = 00:51:00 means (now - prev_tick) == 60.
    current_time = [float(_BASE_EPOCH + 120)]  # 00:51:00 exactly
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_lookback_check(pg_instance, monkeypatch=monkeypatch, window_seconds=60)
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # 1 second earlier: (now - prev_tick) == 59 < 60, recovery fires.
    check2 = _make_cron_lookback_check(pg_instance, monkeypatch=monkeypatch, window_seconds=60)
    check2.db_pool = _mock_db_pool(mock_conn)
    current_time[0] = float(_BASE_EPOCH + 119)
    aggregator.reset()
    check2.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1


def test_emit_failures_metric_on_emit_path_exception(pg_instance, aggregator, monkeypatch):
    """A broken emit path produces an emit_failures count tagged with exc_class."""
    mock_conn, _ = _make_mock_conn()
    check = _create_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    def boom(*args, **kwargs):
        raise json.JSONDecodeError("boom", "doc", 0)

    monkeypatch.setattr('datadog_checks.postgres.data_observability.json.dumps', boom)
    check.data_observability.run_job()

    failures = aggregator.metrics('dd.postgres.data_observability.emit_failures')
    assert len(failures) == 1
    assert any(t.startswith('exc_class:JSONDecodeError') for t in failures[0].tags)
    assert 'monitor_id:1' in failures[0].tags
