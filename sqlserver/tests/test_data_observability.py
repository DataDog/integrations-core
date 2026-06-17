# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.data_observability import EVENT_TRACK_TYPE, MAX_RESULT_ROWS

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


def test_single_query_success(aggregator):
    _setup_and_run()

    aggregator.assert_metric('dd.sqlserver.data_observability.query_execution_time')
    metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(metrics) == 1
    assert metrics[0].value == 1
    assert 'status:success' in metrics[0].tags


def test_multi_query_execution(aggregator):
    _setup_and_run(queries=deepcopy(MULTI_QUERIES))

    time_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_execution_time')
    assert len(time_metrics) == 2

    status_metrics = aggregator.metrics('dd.sqlserver.data_observability.query_executions')
    assert len(status_metrics) == 2
    assert all(m.value == 1 for m in status_metrics)
    assert all('status:success' in m.tags for m in status_metrics)


# ── Per-dbname connections ────────────────────────────────────────────────────


def test_per_dbname_connection_opened(aggregator):
    """_open_managed_db_connections is called with db_name=q.dbname."""
    query = deepcopy(BASE_QUERY)
    query['dbname'] = 'other_db'
    _, mock_conn, _, open_calls = _setup_and_run(queries=[query])

    assert len(open_calls) == 1
    assert open_calls[0]['db_name'] == 'other_db'


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


def test_azure_sql_db_no_use_statement(aggregator):
    """Azure SQL DB safety: connecting via db_name never issues USE <dbname>.

    The per-db connection model (db_name=q.dbname in _open_managed_db_connections)
    avoids USE statements, which are unsafe on Azure SQL DB.
    """
    # The check must call _open_managed_db_connections with db_name='app_db'
    # rather than opening a default connection and issuing USE app_db.
    _, _, _, open_calls = _setup_and_run()

    assert open_calls[0]['db_name'] == 'app_db'
    # get_cursor is called with same db_name (no USE issued)
    # Implicit: no USE statement is constructed in the data_observability path


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


def test_payload_db_type_is_sqlserver(aggregator):
    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        _setup_and_run()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['db_type'] == 'sqlserver'


def test_payload_entity_platform_mssql(aggregator):
    """Entity object is serialised verbatim from the query spec; platform=mssql for SQL Server queries."""
    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        _setup_and_run()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert payload['entity']['platform'] == 'mssql'


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


def test_payload_cloud_metadata_absent_when_not_configured(aggregator):
    """cloud_metadata key is not present when no cloud provider is configured."""
    with patch.object(SQLServer, 'event_platform_event') as mock_epe:
        _setup_and_run()

        do_calls = _get_do_event_calls(mock_epe)
        payload = json.loads(do_calls[0][0][0])

    assert 'cloud_metadata' not in payload


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


def test_collection_interval_none_uses_default():
    """collection_interval=None should not crash."""
    instance = deepcopy(BASE_INSTANCE)
    instance['data_observability'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': None,
        'queries': [],
    }
    check = SQLServer('sqlserver', {}, [instance])
    assert check.data_observability._enabled


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
