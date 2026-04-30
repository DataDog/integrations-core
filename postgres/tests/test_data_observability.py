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

# ---------------------------------------------------------------------------
# Cron schedule / lateness helpers
# ---------------------------------------------------------------------------
# A "frozen" epoch that sits between two hourly boundaries:
#   xx:49:00  (previous hour + 49 min)
#   xx:50:00  (next cron tick for "50 * * * *")
#   xx:51:00  (tick for "51 * * * *")
#
# We use an absolute epoch so croniter's calendar arithmetic stays stable.
# 2026-01-01 00:49:00 UTC  →  1751331940  (approx; exact value computed below)
import calendar
import datetime

_BASE_EPOCH = calendar.timegm(datetime.datetime(2026, 1, 1, 0, 49, 0).timetuple())  # 00:49:00 UTC

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


def _make_cron_check(pg_instance, queries=None, fake_time=None):
    """Create a check with a cron-scheduled query, optionally monkeypatching time.time."""
    if queries is None:
        queries = [deepcopy(CRON_QUERY)]
    check = _create_check(pg_instance, queries=queries)
    return check


def test_schedule_query_does_not_fire_before_tick(pg_instance, monkeypatch):
    """A cron query registered before its first tick must NOT fire on the first run_job call."""
    # Clock is at 00:49:00 — first tick for "50 * * * *" is 00:50:00, still 60s away.
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

    # First run: registers first future tick (00:50:00 is already past, so next is 01:50:00)
    check.data_observability.run_job()
    # At this point next_run should be set (but nothing fired yet — it's first sight)
    mid = CRON_QUERY['monitor_id']
    first_next_run = check.data_observability._next_run[mid]

    # Second run: now we're past the registered next_run (which was set to 00:50:00)
    # Actually at 00:50:05 the first sight records 00:50:00 as next and skips. Let me re-check.
    # At 00:50:05 > 00:49:00 = _BASE_EPOCH, so first sight computes next_run = 00:50:00 (already past).
    # Wait — croniter(schedule, now).get_next() returns the first tick AFTER `now`.
    # At now=00:50:05, get_next("50 * * * *") = 01:50:00 (the next tick after 00:50:05).
    # So first call: next_run = 01:50:00 → skip (no fire).
    # Advance to 01:50:05:
    current_time[0] = _BASE_EPOCH + 3665  # ~01:50:05
    check.data_observability.run_job()

    second_next_run = check.data_observability._next_run[mid]
    # After firing at 01:50:05, next_run should advance to 02:50:00
    assert second_next_run > first_next_run
    # Should be approximately 1 hour later
    assert second_next_run - first_next_run >= 3600 - 10


def test_schedule_takes_precedence_over_interval_seconds(pg_instance, aggregator, monkeypatch):
    """When both schedule and interval_seconds are set, schedule wins."""
    query = deepcopy(CRON_QUERY)
    query['interval_seconds'] = 5  # Very short interval — should be ignored

    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _create_check(pg_instance, queries=[query])
    check.db_pool = _mock_db_pool(mock_conn)

    # First call at 00:49:00: registers cron next_run (00:50:00), does NOT fire despite interval=5 passing.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Advance 10s (interval would have fired, but cron tick not reached yet).
    current_time[0] = _BASE_EPOCH + 10  # 00:49:10 — past 5s interval, but not yet :50
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 0

    # Now advance past 00:50:00
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.postgres.data_observability.query_executions')) == 1


def test_schedule_invalid_skipped(pg_instance, aggregator, monkeypatch):
    """A query with an invalid cron string is skipped; other queries in the list still run."""
    bad_query = {
        **deepcopy(CRON_QUERY),
        'monitor_id': 20,
        'schedule': 'not-a-cron',
    }
    good_query = deepcopy(BASE_QUERY)  # interval-based query, monitor_id=1

    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _create_check(pg_instance, queries=[bad_query, good_query])
    check.db_pool = _mock_db_pool(mock_conn)

    check.data_observability.run_job()

    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    monitor_ids_run = {int(t.split(':')[1]) for m in metrics for t in m.tags if t.startswith('monitor_id:')}
    # bad_query (id=20) must NOT have run; good_query (id=1) must have run
    assert 20 not in monitor_ids_run
    assert 1 in monitor_ids_run

    # Warning should be recorded in _invalid_warned, not repeated on next run
    check.data_observability.run_job()
    assert 20 in check.data_observability._invalid_warned


def test_neither_set_skipped(pg_instance, aggregator):
    """A query with no schedule and no positive interval_seconds is skipped."""
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
    mock_conn, _ = _make_mock_conn()
    check = _create_check(pg_instance, queries=[query])
    check.db_pool = _mock_db_pool(mock_conn)
    check.data_observability.run_job()

    metrics = aggregator.metrics('dd.postgres.data_observability.query_executions')
    monitor_ids_run = {int(t.split(':')[1]) for m in metrics for t in m.tags if t.startswith('monitor_id:')}
    assert 30 not in monitor_ids_run
    assert 30 in check.data_observability._invalid_warned


# ---------------------------------------------------------------------------
# Lateness metric tests
# ---------------------------------------------------------------------------


def test_lateness_metric_emitted_for_cron(pg_instance, aggregator, monkeypatch):
    """Cron query fired late emits a positive lateness gauge with mode:cron tag."""
    # next_run will be at 00:50:00; fire at 00:52:00 → 120s lateness
    tick_time = float(_BASE_EPOCH + 60)  # 00:50:00 exactly
    fire_time = float(_BASE_EPOCH + 180)  # 00:52:00

    call_count = [0]

    def fake_clock():
        call_count[0] += 1
        # First call: _get_due_queries registration at tick_time
        # The sequence is complex; just use a simpler two-phase approach:
        # Use monkeypatch to control time directly via a mutable list.
        return current_time[0]

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
    """Interval query emits lateness gauge with mode:interval tag."""
    # Use a large base time so that `now - last_run(0.0) >= interval_seconds(60)` is True.
    # At t=1000 with last_run=0.0: 1000 - 0 = 1000 >= 60 → due.
    # First fire: last_run is 0.0 (never run) → scheduled = now → lateness = 0.
    current_time = [1000.0]
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    query = deepcopy(BASE_QUERY)  # monitor_id=1, interval_seconds=60

    check = _create_check(pg_instance, queries=[query])
    check.db_pool = _mock_db_pool(mock_conn)

    # First fire at t=1000: last_run=0 (never run), so scheduled=now → lateness=0.
    check.data_observability.run_job()
    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert lateness_metrics[0].value == 0.0
    assert 'mode:interval' in lateness_metrics[0].tags

    # After first fire, last_run = 1000.0.
    # Second fire at t=1080 (20s late: scheduled = 1000 + 60 = 1060, fired at 1080)
    current_time[0] = 1080.0
    aggregator.reset()
    check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.postgres.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    m = lateness_metrics[0]
    assert 'mode:interval' in m.tags
    # scheduled = last_run(1000) + interval(60) = 1060; fire at 1080 → lateness = 20
    assert abs(m.value - 20.0) < 1.0


def test_lateness_clamped_at_zero(pg_instance, aggregator, monkeypatch):
    """If scheduled_fire_time is in the future at fire time (clock skew), lateness is clamped to 0."""
    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 — cron tick 00:50:00 in the past
    monkeypatch.setattr('datadog_checks.postgres.data_observability.time.time', lambda: current_time[0])

    mock_conn, _ = _make_mock_conn()
    check = _make_cron_check(pg_instance)
    check.db_pool = _mock_db_pool(mock_conn)

    # First call: registers next_run = 01:50:00 (future)
    check.data_observability.run_job()
    mid = CRON_QUERY['monitor_id']
    next_run = check.data_observability._next_run[mid]

    # Manually set next_run to a value slightly in the future to simulate skew
    # (i.e., scheduled_fire_time > now_at_fire_start)
    check.data_observability._next_run[mid] = current_time[0] + 1000.0

    # Force it to look "due" by setting now past that point but making now_at_fire_start < scheduled
    # We achieve this by having _get_due_queries return a past-tick but then fire_start < scheduled_tick.
    # Simpler approach: directly manipulate state so the query is seen as due with scheduled > fire_start.
    # Set next_run to a past value so it's due:
    past_tick = current_time[0] - 5.0
    check.data_observability._next_run[mid] = past_tick
    # But shift time so now_at_fire_start < past_tick (synthetic skew):
    # Actually, just verify the clamp: if scheduled_fire_time > now_at_fire_start, value = 0.
    # We construct this by running at a time just after next_run but having time.time()
    # return a value LESS than next_run for now_at_fire_start — achieved by decrementing after due check.
    # The cleanest way: patch _get_due_queries directly.
    skewed_scheduled = current_time[0] + 100.0  # scheduled in the future
    with patch.object(
        check.data_observability, '_get_due_queries', return_value=[(check.data_observability._do_config.queries[0], skewed_scheduled)]
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

    # First run: registers both next_run values (A→00:50:00, B→00:51:00), fires nothing.
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

    # Simulate: A took 2m30s → clock is now 00:52:35. B's tick (00:51:00) has passed.
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
