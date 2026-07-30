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

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.data_observability import EVENT_TRACK_TYPE, MAX_RESULT_ROWS

# Fixed epoch (2026-01-01 00:49:00 UTC) chosen to sit 1 minute before the ":50" cron tick used in tests.
_BASE_EPOCH = calendar.timegm(datetime.datetime(2026, 1, 1, 0, 49, 0).timetuple())

pytestmark = pytest.mark.unit

BASE_INSTANCE = {
    'host': 'localhost,1433',
    'connector': 'odbc',
    'driver': '{ODBC Driver 18 for SQL Server}',
    'reported_hostname': 'test-host',
}

BASE_QUERY = {
    'monitor_id': 1,
    'dbname': 'app_db',
    'query': 'SELECT count(*) FROM orders',
    'interval_seconds': 60,
    'type': 'freshness',
    'entity': {
        'platform': 'mssql',
        'account': '123456',
        'database': 'app_db',
        'schema': 'dbo',
        'table': 'orders',
    },
}

MULTI_QUERIES = [
    BASE_QUERY,
    {
        'monitor_id': 2,
        'dbname': 'app_db',
        'query': 'SELECT count(*) FROM users',
        'interval_seconds': 120,
        'type': 'freshness',
        'entity': {
            'platform': 'mssql',
            'account': '123456',
            'database': 'app_db',
            'schema': 'dbo',
            'table': 'users',
        },
    },
]


def _make_do_instance(queries=None, config_id='test-config-123', extra=None):
    instance = deepcopy(BASE_INSTANCE)
    instance['data_observability'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 10,
        'config_id': config_id,
        'queries': queries if queries is not None else [deepcopy(BASE_QUERY)],
    }
    if extra:
        instance.update(extra)
    return instance


def _make_mock_cursor(rows=None, description=None):
    mock_cursor = MagicMock()
    mock_cursor.description = description if description is not None else [('count',)]
    mock_cursor.fetchmany.return_value = rows if rows is not None else [(42,)]
    return mock_cursor


def _make_connection_mocks(mock_cursor=None):
    """Return (mock_connection, mock_cursor, ctx_patcher_fn).

    Patches check.connection._open_managed_db_connections as a context manager,
    check.connection.get_cursor to return mock_cursor, and check.connection.close_cursor
    as a no-op. Returns the mocked objects and a callable that applies the patches.
    """
    if mock_cursor is None:
        mock_cursor = _make_mock_cursor()

    # Track open_managed_db_connections calls
    open_calls = []

    @contextmanager
    def fake_open_managed(db_key, db_name=None, key_prefix=None):
        open_calls.append({'db_key': db_key, 'db_name': db_name, 'key_prefix': key_prefix})
        yield

    mock_connection = MagicMock()
    mock_connection._open_managed_db_connections = MagicMock(side_effect=fake_open_managed)
    mock_connection.get_cursor = MagicMock(return_value=mock_cursor)
    mock_connection.close_cursor = MagicMock()
    mock_connection.set_command_timeout = MagicMock()
    mock_connection.get_host_with_port = MagicMock(return_value=BASE_INSTANCE['host'])
    mock_connection.DEFAULT_DB_KEY = 'database'

    return mock_connection, mock_cursor, open_calls


def _create_check(instance):
    check = SQLServer('sqlserver', {}, [instance])
    return check


def _setup_and_run(instance=None, queries=None, mock_cursor=None):
    if instance is None:
        instance = _make_do_instance(queries=queries)
    check = _create_check(instance)
    mock_connection, cursor, open_calls = _make_connection_mocks(mock_cursor)
    check._connection = mock_connection

    check.data_observability.run_job()
    return check, mock_connection, cursor, open_calls


def _get_do_event_calls(mock_epe):
    return [c for c in mock_epe.call_args_list if len(c[0]) >= 2 and c[0][1] == EVENT_TRACK_TYPE]


# ── Basic execution ──────────────────────────────────────────────────────────


def test_no_queries_does_nothing(aggregator):
    instance = _make_do_instance(queries=[])
    check = _create_check(instance)
    mock_connection, _, _ = _make_connection_mocks()
    check._connection = mock_connection

    check.data_observability.run_job()

    mock_connection._open_managed_db_connections.assert_not_called()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0


def test_multi_query_execution(aggregator):
    _setup_and_run(queries=deepcopy(MULTI_QUERIES))

    time_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_execution_time')
    assert len(time_metrics) == 2

    status_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert all(m.value == 1 for m in status_metrics)
    assert all('status:success' in m.tags for m in status_metrics)


# ── Per-dbname connections ────────────────────────────────────────────────────


def test_multiple_queries_different_dbnames(aggregator):
    """Queries to different dbnames open separate connections."""
    queries = [
        {**deepcopy(BASE_QUERY), 'dbname': 'db_one'},
        {**deepcopy(MULTI_QUERIES[1]), 'dbname': 'db_two'},
    ]

    with patch.object(SQLServer, 'event_platform_event'):
        _, _, _, open_calls = _setup_and_run(queries=queries)

    assert len(open_calls) == 2
    assert open_calls[0]['db_name'] == 'db_one'
    assert open_calls[1]['db_name'] == 'db_two'


# ── Error handling ────────────────────────────────────────────────────────────


def test_query_failure_does_not_block_subsequent(aggregator):
    """First query raises pyodbc.Error; second query still runs."""
    import pyodbc

    mock_cursor = _make_mock_cursor()
    call_count = 0

    def execute_side_effect(sql, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise pyodbc.ProgrammingError("table not found")

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    _setup_and_run(queries=deepcopy(MULTI_QUERIES), mock_cursor=mock_cursor)

    # Both queries must emit a metric
    status_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(status_metrics) == 2


def test_no_description_does_not_block_subsequent(aggregator):
    """cursor.description is None (non-SELECT) triggers per-query error; subsequent queries still run."""
    mock_cursor = _make_mock_cursor()
    call_count = 0

    def execute_side_effect(sql, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_cursor.description = None if call_count == 1 else [('count',)]

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    _setup_and_run(queries=deepcopy(MULTI_QUERIES), mock_cursor=mock_cursor)

    status_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert 'status:error' in status_metrics[0].tags
    assert 'status:success' in status_metrics[1].tags


def test_query_with_no_description(aggregator):
    """Non-SELECT queries (cursor.description is None) emit error result."""
    mock_cursor = _make_mock_cursor()

    def execute_side_effect(sql, *args, **kwargs):
        mock_cursor.description = None

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        instance = _make_do_instance()
        check = _create_check(instance)
        mock_connection, _, _ = _make_connection_mocks(mock_cursor)
        check._connection = mock_connection

        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['status'] == 'error'
    assert 'result set' in payload['error']
    metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:error' in metrics[0].tags


def test_connection_failure_does_not_block_other_due_queries(aggregator):
    """A connection failure opening the first due query's db must not abort processing of
    other queries already due in the same pass (they were already ticked/collected before
    the failure)."""
    from datadog_checks.sqlserver.connection_errors import SQLConnectionError

    mock_cursor = _make_mock_cursor()
    instance = _make_do_instance(queries=deepcopy(MULTI_QUERIES))
    check = _create_check(instance)
    mock_connection, _, open_calls = _make_connection_mocks(mock_cursor)

    call_count = 0
    real_side_effect = mock_connection._open_managed_db_connections.side_effect

    @contextmanager
    def flaky_open_managed(db_key, db_name=None, key_prefix=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SQLConnectionError("could not connect")
        with real_side_effect(db_key, db_name=db_name, key_prefix=key_prefix) as ctx:
            yield ctx

    mock_connection._open_managed_db_connections = MagicMock(side_effect=flaky_open_managed)
    check._connection = mock_connection

    check.data_observability.run_job()

    # First query's connection failed, but the second (already-due) query still ran.
    status_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(status_metrics) == 1
    failure_metrics = aggregator.metrics('dd.sqlserver.data_observability.connection_failures')
    assert len(failure_metrics) == 1


def test_connection_failure_retried_on_next_poll(aggregator, monkeypatch):
    """A cron query whose connection attempt fails is retried on the very next run_job()
    call, not stranded until its next scheduled tick.

    Uses a cron query deliberately: CronScheduler.due_ticks() consumes the tick as soon as
    it's reported, so — unlike an interval query, which would naturally still look "due"
    on the next poll regardless of any retry bookkeeping — a cron query only fires again
    here because of the `_pending_retries` mechanism. This protects that mechanism from
    regressing silently.
    """
    from datadog_checks.sqlserver.connection_errors import SQLConnectionError

    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 — past the cron tick, fires immediately
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    mock_cursor = _make_mock_cursor()
    check = _make_cron_check()
    mock_connection, _, _ = _attach_conn(check, mock_cursor)

    call_count = 0
    real_side_effect = mock_connection._open_managed_db_connections.side_effect

    @contextmanager
    def flaky_open_managed(db_key, db_name=None, key_prefix=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SQLConnectionError("could not connect")
        with real_side_effect(db_key, db_name=db_name, key_prefix=key_prefix) as ctx:
            yield ctx

    mock_connection._open_managed_db_connections = MagicMock(side_effect=flaky_open_managed)

    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0

    # No clock movement and no new tick — due_ticks() already consumed this tick, so only
    # the pending-retry queue can cause the query to fire again here.
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 1


def test_error_event_payload(aggregator):
    """Failed query emits an event payload with error details."""
    import pyodbc

    mock_cursor = _make_mock_cursor()
    mock_cursor.execute.side_effect = pyodbc.ProgrammingError("invalid object name")

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        instance = _make_do_instance()
        check = _create_check(instance)
        mock_connection, _, _ = _make_connection_mocks(mock_cursor)
        check._connection = mock_connection

        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        assert len(do_calls) == 1
        payload = json.loads(do_calls[0][0][0])

    assert payload['status'] == 'error'
    assert 'invalid object name' in payload['error']
    assert payload['columns'] == []
    assert payload['rows'] == []
    assert payload['row_count'] == 0
    assert payload['monitor_id'] == 1
    assert 'duration_s' in payload


# ── Scheduling ────────────────────────────────────────────────────────────────


def test_per_query_interval_tracking(aggregator):
    instance = _make_do_instance()
    check = _create_check(instance)
    mock_connection, _, _ = _make_connection_mocks()
    check._connection = mock_connection

    # First run: query executes
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 1

    # Immediate second run: query skipped (interval not elapsed)
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0

    # Reset _last_execution to force re-run
    aggregator.reset()
    check.data_observability._last_execution = {1: 0.0}
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 1


def test_failed_query_updates_last_execution(aggregator):
    """A failed query still updates _last_execution so it is not retried until the next interval."""
    import pyodbc

    mock_cursor = _make_mock_cursor()
    mock_cursor.execute.side_effect = pyodbc.ProgrammingError("syntax error")

    instance = _make_do_instance()
    check = _create_check(instance)
    mock_connection, _, _ = _make_connection_mocks(mock_cursor)
    check._connection = mock_connection

    check.data_observability.run_job()
    assert 1 in check.data_observability._last_execution

    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0


# ── Payload structure ─────────────────────────────────────────────────────────


def test_event_payload_structure(aggregator):
    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        check, _, _, _ = _setup_and_run()

        do_calls = _get_do_event_calls(mock_epe)
        assert len(do_calls) == 1
        raw_event = do_calls[0][0][0]
        event_type = do_calls[0][0][1]
        payload = json.loads(raw_event)

    assert event_type == EVENT_TRACK_TYPE
    assert payload['config_id'] == 'test-config-123'
    assert payload['db_type'] == 'sqlserver'
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
    assert payload['entity']['platform'] == 'mssql'
    assert 'cloud_metadata' not in payload


def test_payload_db_port_honors_separate_port_option(aggregator):
    """When host has no embedded port, db_port must reflect the separately-configured
    `port` option (via Connection.get_host_with_port()) rather than falling back to the
    default 1433.

    Exercises the real `Connection.get_host_with_port` implementation (bound onto the
    mock) against an instance actually configured with a bare host + separate port,
    rather than stubbing the method's return value directly — a stub would pass even if
    `_get_db_port()` ignored the `port` config option entirely.
    """
    from types import MethodType

    from datadog_checks.sqlserver.connection import Connection

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        instance = _make_do_instance(extra={'host': 'myhost', 'port': 1444})
        check = _create_check(instance)
        mock_connection, _, _ = _make_connection_mocks()
        mock_connection.instance = instance
        mock_connection.get_host_with_port = MethodType(Connection.get_host_with_port, mock_connection)
        check._connection = mock_connection

        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['db_port'] == 1444


def test_payload_db_name_reflects_query_dbname(aggregator):
    query = deepcopy(BASE_QUERY)
    query['dbname'] = 'analytics_db'

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        _setup_and_run(queries=[query])

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['db_name'] == 'analytics_db'


def test_payload_cloud_metadata_included(aggregator):
    """cloud_metadata is included in the payload when azure/aws/gcp is configured."""
    instance = _make_do_instance(extra={'azure': {'deployment_type': 'sql_database'}})

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        check = _create_check(instance)
        mock_connection, _, _ = _make_connection_mocks()
        check._connection = mock_connection

        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert 'cloud_metadata' in payload
    assert 'azure' in payload['cloud_metadata']


def test_entity_schema_alias(aggregator):
    """Entity schema field serialises as 'schema' (alias) not 'schema_'."""
    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        _setup_and_run()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['entity']['schema'] == 'dbo'
    assert 'schema_' not in payload['entity']


def test_custom_sql_select_fields_in_payload(aggregator):
    query = deepcopy(BASE_QUERY)
    query['custom_sql_select_fields'] = {
        'metric_config_id': 42,
        'entity_id': 'ent-abc-123',
    }

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        _setup_and_run(queries=[query])

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    custom = payload['custom_sql_select_fields']
    assert custom['metric_config_id'] == 42
    assert custom['entity_id'] == 'ent-abc-123'


def test_tags_include_monitor_id(aggregator):
    _setup_and_run()

    time_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_execution_time')
    assert len(time_metrics) == 1
    assert 'monitor_id:1' in time_metrics[0].tags
    assert 'config_id:test-config-123' in time_metrics[0].tags
    assert 'db_type:sqlserver' in time_metrics[0].tags

    exec_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(exec_metrics) == 1
    assert 'monitor_id:1' in exec_metrics[0].tags
    assert 'status:success' in exec_metrics[0].tags


# ── query_timeout conversion ──────────────────────────────────────────────────


def test_query_timeout_ms_to_seconds_conversion(aggregator):
    """query_timeout in ms is converted to ceiling-seconds before setting on the connection."""
    query = deepcopy(BASE_QUERY)
    query['query_timeout'] = 180_000  # 180 s

    _, mock_conn, _, _ = _setup_and_run(queries=[query])

    mock_conn.set_command_timeout.assert_called_once()
    _, timeout_s, *_ = mock_conn.set_command_timeout.call_args[0]
    assert timeout_s == 180


def test_query_timeout_ceiling(aggregator):
    """Fractional ms values are rounded up (ceil), minimum 1 s."""
    query = deepcopy(BASE_QUERY)
    query['query_timeout'] = 1500  # 1.5 s → ceil → 2 s

    _, mock_conn, _, _ = _setup_and_run(queries=[query])

    _, timeout_s, *_ = mock_conn.set_command_timeout.call_args[0]
    assert timeout_s == 2


def test_query_timeout_minimum_1s(aggregator):
    """Sub-second timeouts are clamped to 1 s minimum."""
    query = deepcopy(BASE_QUERY)
    query['query_timeout'] = 100  # 0.1 s → ceil → 1 s

    _, mock_conn, _, _ = _setup_and_run(queries=[query])

    _, timeout_s, *_ = mock_conn.set_command_timeout.call_args[0]
    assert timeout_s == 1


def test_no_query_timeout_skips_set_command_timeout(aggregator):
    """When query_timeout is not set, set_command_timeout is not called."""
    query = deepcopy(BASE_QUERY)
    # No query_timeout key

    _, mock_conn, _, _ = _setup_and_run(queries=[query])

    mock_conn.set_command_timeout.assert_not_called()


# ── Miscellaneous ─────────────────────────────────────────────────────────────


def test_sql_connection_error_is_expected_db_exception():
    """SQLConnectionError (raised by Connection.open_db_connections on failure) must be
    classified as an expected DB exception so DBMAsyncJob reports it as a database error
    rather than an async-job crash if it ever escapes run_job()."""
    from datadog_checks.sqlserver.connection_errors import SQLConnectionError

    instance = _make_do_instance(queries=[])
    check = _create_check(instance)
    assert SQLConnectionError in check.data_observability._expected_db_exceptions


@pytest.mark.parametrize('collection_interval', [None, -5, 0])
def test_collection_interval_non_positive_uses_default(collection_interval):
    """A missing or non-positive collection_interval (e.g. from a malformed RC config)
    must fall back to the default instead of producing a zero/negative rate limit that
    spins the job loop without sleeping."""
    instance = deepcopy(BASE_INSTANCE)
    instance['data_observability'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': collection_interval,
        'queries': [],
    }
    check = SQLServer('sqlserver', {}, [instance])
    assert check.data_observability._enabled
    assert check.data_observability._rate_limiter.rate_limit_s == pytest.approx(1 / 10)


def test_fetchmany_called_with_max_rows(aggregator):
    """fetchmany is called with MAX_RESULT_ROWS to cap memory usage."""
    mock_cursor = _make_mock_cursor()
    _setup_and_run(mock_cursor=mock_cursor)
    mock_cursor.fetchmany.assert_called_once_with(MAX_RESULT_ROWS)


def test_pyodbc_cursor_description_columns_from_description(aggregator):
    """columns are built from cursor.description (no DictCursor in pyodbc)."""
    description = [('col_a',), ('col_b',), ('col_c',)]
    mock_cursor = _make_mock_cursor(rows=[(1, 2, 3)], description=description)

    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        instance = _make_do_instance()
        check = _create_check(instance)
        mock_connection, _, _ = _make_connection_mocks(mock_cursor)
        check._connection = mock_connection

        check.data_observability.run_job()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['columns'] == ['col_a', 'col_b', 'col_c']
    assert payload['rows'] == [[1, 2, 3]]


# ---------------------------------------------------------------------------
# Cron schedule tests
# ---------------------------------------------------------------------------

CRON_QUERY = {
    'monitor_id': 10,
    'dbname': 'app_db',
    'query': 'SELECT 1',
    'schedule': '50 * * * *',  # every hour at :50
    'interval_seconds': 3600,
    'type': 'freshness',
    'entity': {
        'platform': 'mssql',
        'account': '123456',
        'database': 'app_db',
        'schema': 'dbo',
        'table': 'orders',
    },
}


def _make_cron_check(queries=None, *, window_seconds=None, monkeypatch=None):
    if window_seconds is not None:
        assert monkeypatch is not None, "monkeypatch is required when overriding window_seconds"
        monkeypatch.setattr(
            'datadog_checks.sqlserver.data_observability.CRON_STARTUP_LOOKBACK_SECONDS',
            window_seconds,
        )
    instance = _make_do_instance(queries=queries or [deepcopy(CRON_QUERY)])
    return _create_check(instance)


def _attach_conn(check, mock_cursor=None):
    mock_connection, cursor, open_calls = _make_connection_mocks(mock_cursor)
    check._connection = mock_connection
    return mock_connection, cursor, open_calls


def test_schedule_query_fires_at_cron_tick(aggregator, monkeypatch):
    """A cron query fires after its first tick has passed."""
    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    check = _make_cron_check()
    _attach_conn(check)

    # First call: registers next_run (tick at 00:50:00) but does NOT fire.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0

    # Advance past 00:50:00
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 1


def test_schedule_query_fires_when_first_poll_exactly_at_tick(aggregator, monkeypatch):
    """First poll landing exactly on the cron tick must fire, not skip the cycle."""
    tick_time = float(_BASE_EPOCH + 60)  # 00:50:00 — exactly on the :50 tick
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: tick_time)

    check = _make_cron_check()
    _attach_conn(check)

    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 1


def test_schedule_takes_precedence_over_interval_seconds(aggregator, monkeypatch):
    query = deepcopy(CRON_QUERY)
    query['interval_seconds'] = 5  # Very short interval — should be ignored.

    current_time = [float(_BASE_EPOCH)]
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    check = _make_cron_check(queries=[query])
    _attach_conn(check)

    # First call at 00:49:00: registers cron next_run (00:50:00), does NOT fire despite interval=5 passing.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0

    # Advance 10s (interval would have fired, but cron tick not reached yet).
    current_time[0] = _BASE_EPOCH + 10  # 00:49:10 — past 5s interval, but not yet :50.
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0

    # Now advance past 00:50:00.
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 1


def test_invalid_cron_schedule_filtered_at_init(aggregator, caplog):
    """A query with an unparseable cron string is dropped at construction; siblings still run."""
    import logging

    bad = {**deepcopy(CRON_QUERY), 'monitor_id': 20, 'schedule': 'not-a-cron'}
    good = deepcopy(BASE_QUERY)  # interval-based, monitor_id=1

    instance = _make_do_instance(queries=[bad, good])
    with caplog.at_level(logging.WARNING):
        check = _create_check(instance)
    assert {q.monitor_id for q in check.data_observability._queries} == {1}
    assert any('invalid cron schedule' in r.message and "'not-a-cron'" in r.message for r in caplog.records)

    _attach_conn(check)
    check.data_observability.run_job()
    monitor_ids_run = {
        int(t.split(':')[1])
        for m in aggregator.metrics('dd.sqlserver.data_observability.query_executions')
        for t in m.tags
        if t.startswith('monitor_id:')
    }
    assert monitor_ids_run == {1}


def test_query_without_schedule_or_positive_interval_filtered_at_init(caplog):
    """A query with neither schedule nor a positive interval_seconds is dropped at construction."""
    import logging

    query = {
        'monitor_id': 30,
        'dbname': 'app_db',
        'query': 'SELECT 1',
        'type': 'freshness',
        'entity': {
            'platform': 'mssql',
            'account': '123456',
            'database': 'app_db',
            'schema': 'dbo',
            'table': 'foo',
        },
    }
    instance = _make_do_instance(queries=[query])
    with caplog.at_level(logging.WARNING):
        check = _create_check(instance)
    assert check.data_observability._queries == ()
    assert any('neither schedule nor positive interval_seconds' in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Lateness metric tests
# ---------------------------------------------------------------------------


def test_lateness_metric_emitted_for_cron(aggregator, monkeypatch):
    """Cron query fired late emits a positive lateness gauge with mode:cron tag."""
    # next_run will be at 00:50:00; fire at 00:52:00 -> 120s lateness.
    fire_time = float(_BASE_EPOCH + 180)  # 00:52:00
    current_time = [float(_BASE_EPOCH)]  # 00:49:00 — before the tick
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    check = _make_cron_check()
    _attach_conn(check)

    # Step 1: First poll at 00:49:00 — prev tick is 23:50:00 (>>300s ago), no lookback recovery.
    # Scheduler caches next_tick = 00:50:00.
    check.data_observability.run_job()
    mid = CRON_QUERY['monitor_id']
    scheduled_tick = check.data_observability._schedulers[mid].next_tick

    # Step 2: Advance to 00:52:00 — 2 minutes late
    current_time[0] = fire_time
    aggregator.reset()
    check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    m = lateness_metrics[0]
    assert m.value >= 0.0
    assert 'mode:cron' in m.tags
    assert f'monitor_id:{mid}' in m.tags
    # Lateness should be fire_time - scheduled_tick ≈ 120s (within 5s tolerance for real-time drift)
    expected_lateness = fire_time - scheduled_tick
    assert abs(m.value - expected_lateness) < 5.0


def test_lateness_metric_emitted_for_interval(aggregator, monkeypatch):
    """Interval query emits lateness gauge with mode:interval tag.

    First fire is lazy-seeded to scheduled = now so lateness is 0; second
    fire after a delay exposes the configured interval as positive lateness.
    """
    current_time = [1000.0]
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    query = deepcopy(BASE_QUERY)  # monitor_id=1, interval_seconds=60

    instance = _make_do_instance(queries=[query])
    check = _create_check(instance)
    _attach_conn(check)

    # First fire at t=1000: lazy-seeded last_execution = 940, so scheduled = now -> lateness = 0.
    check.data_observability.run_job()
    lateness_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert lateness_metrics[0].value == 0.0
    assert 'mode:interval' in lateness_metrics[0].tags

    # After first fire, last_execution = 1000.0.
    # Second fire at t=1080 (20s late: scheduled = 1000 + 60 = 1060, fired at 1080).
    current_time[0] = 1080.0
    aggregator.reset()
    check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    m = lateness_metrics[0]
    assert 'mode:interval' in m.tags
    # scheduled = last_run(1000) + interval(60) = 1060; fire at 1080 -> lateness = 20.
    assert abs(m.value - 20.0) < 1.0


def test_lateness_clamped_at_zero(aggregator, monkeypatch):
    """If scheduled_fire_time is in the future at fire time (clock skew), lateness is clamped to 0."""
    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 — cron tick 00:50:00 in the past
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    check = _make_cron_check()
    _attach_conn(check)

    # Patch _get_due_queries to return a scheduled_fire_time in the future of fire_start
    # (synthetic clock-skew scenario). Lateness must clamp to 0 rather than go negative.
    from datadog_checks.sqlserver.data_observability import DueQuery

    skewed_scheduled = current_time[0] + 100.0
    q = check.data_observability._queries[0]
    with patch.object(
        check.data_observability,
        '_get_due_queries',
        return_value=[DueQuery(q, skewed_scheduled, "cron")],
    ):
        aggregator.reset()
        check.data_observability.run_job()

    lateness_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_fire_lateness_seconds')
    assert len(lateness_metrics) == 1
    assert lateness_metrics[0].value == 0.0


def test_starved_query_eventually_fires(aggregator, monkeypatch):
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
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    check = _make_cron_check(queries=[query_a, query_b])
    _attach_conn(check)

    # First run: registers both next_run values (A -> 00:50:00, B -> 00:51:00), fires nothing.
    check.data_observability.run_job()
    assert len(aggregator.metrics('dd.sqlserver.data_observability.query_executions')) == 0

    # Simulate: clock moves to 00:50:05 — A is due, B is not yet.
    current_time[0] = _BASE_EPOCH + 65  # 00:50:05
    aggregator.reset()
    check.data_observability.run_job()

    exec_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    a_ran = any('monitor_id:50' in m.tags for m in exec_metrics)
    b_ran = any('monitor_id:51' in m.tags for m in exec_metrics)
    assert a_ran, "Query A should have fired at 00:50:05"
    assert not b_ran, "Query B should not yet have fired at 00:50:05"

    # Simulate: A took 2m30s -> clock is now 00:52:35. B's tick (00:51:00) has passed.
    current_time[0] = _BASE_EPOCH + 215  # 00:52:35
    aggregator.reset()
    check.data_observability.run_job()

    exec_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    b_ran_now = any('monitor_id:51' in m.tags for m in exec_metrics)
    assert b_ran_now, "Query B should fire at 00:52:35 (late, but same hour)"

    # B's lateness should be positive (fired ~1m35s after its :51 tick)
    lateness_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_fire_lateness_seconds')
    b_lateness = [m for m in lateness_metrics if 'monitor_id:51' in m.tags]
    assert len(b_lateness) == 1
    assert b_lateness[0].value > 0.0


# ---------------------------------------------------------------------------
# Cron startup lookback window (recovery of fires lost across check restarts)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "window_seconds,time_offset,expected_fires",
    [
        (300, 70, 1),  # inside window (10s after tick): fires
        (0, 70, 0),  # disabled: skips
        (300, 400, 0),  # outside window (340s after tick): skips
    ],
    ids=["inside-window", "disabled", "outside-window"],
)
def test_cron_startup_lookback_window_behavior(aggregator, monkeypatch, window_seconds, time_offset, expected_fires):
    """Recovery fires only when window > 0 and (now - prev_tick) <= window."""
    current_time = [float(_BASE_EPOCH + time_offset)]
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    check = _make_cron_check(window_seconds=window_seconds, monkeypatch=monkeypatch)
    _attach_conn(check)
    check.data_observability.run_job()

    metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(metrics) == expected_fires
    if expected_fires:
        assert any('monitor_id:10' in m.tags for m in metrics)


def test_cron_startup_lookback_default_is_300_seconds():
    """The startup lookback window is 5 minutes; pin it so a regression is loud."""
    from datadog_checks.sqlserver.data_observability import CRON_STARTUP_LOOKBACK_SECONDS

    assert CRON_STARTUP_LOOKBACK_SECONDS == 300


# ---------------------------------------------------------------------------
# State reconciliation, mode caching, and error-path tests
# ---------------------------------------------------------------------------


def test_failed_cron_query_advances_next_run(aggregator, monkeypatch):
    """A failing cron query still advances the scheduler, so it does not hot-loop on the same tick."""
    import pyodbc

    current_time = [float(_BASE_EPOCH + 65)]  # 00:50:05 -- already past the 00:50 tick
    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.time.time', lambda: current_time[0])

    mock_cursor = _make_mock_cursor()
    mock_cursor.execute.side_effect = pyodbc.ProgrammingError("invalid object name")

    check = _make_cron_check()
    _attach_conn(check, mock_cursor)
    # First run: lookback recovery fires (5s within 300s window); scheduler caches next_tick = 01:50:00.
    # The query fails; aggregator records an error metric that we discard below.
    check.data_observability.run_job()
    mid = CRON_QUERY['monitor_id']
    registered = check.data_observability._schedulers[mid].next_tick

    # Jump past the next tick and let the failing query fire again.
    current_time[0] = _BASE_EPOCH + 3665  # ~01:50:05
    aggregator.reset()
    check.data_observability.run_job()
    metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(metrics) == 1
    assert 'status:error' in metrics[0].tags

    # next_tick must have advanced past the just-fired tick; otherwise the very next
    # poll would re-fire the same tick in a tight loop.
    advanced = check.data_observability._schedulers[mid].next_tick
    assert advanced > registered
    assert advanced >= current_time[0]


def test_emit_failures_metric_on_emit_path_exception(aggregator, monkeypatch):
    """A broken emit path produces an emit_failures count tagged with exc_class."""
    instance = _make_do_instance()
    check = _create_check(instance)
    _attach_conn(check)

    def boom(*args, **kwargs):
        raise json.JSONDecodeError("boom", "doc", 0)

    monkeypatch.setattr('datadog_checks.sqlserver.data_observability.json.dumps', boom)
    check.data_observability.run_job()

    failures = aggregator.metrics('dd.sqlserver.data_observability.emit_failures')
    assert len(failures) == 1
    assert any(t.startswith('exc_class:JSONDecodeError') for t in failures[0].tags)
    assert 'monitor_id:1' in failures[0].tags
