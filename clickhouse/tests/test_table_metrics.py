# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
from unittest import mock

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.table_metrics import ClickhouseTableMetrics

pytestmark = pytest.mark.unit


def _table_size_row(database='default', name='events', total_rows=1000, total_bytes=2048):
    return (database, name, total_rows, total_bytes)


def _view_refresh_row(
    database='mydb',
    view='mv_orders',
    host='replica-1',
    status='Scheduled',
    exception='',
    last_time=1700000000,
    next_time=1700003600,
    written_rows=500,
    written_bytes=4096,
):
    return (database, view, host, status, exception, last_time, next_time, written_rows, written_bytes)


@pytest.fixture
def schema_metrics_instance():
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'schema_metrics': {'enabled': True, 'collection_interval': 60, 'run_sync': True},
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check(schema_metrics_instance):
    return ClickhouseCheck('clickhouse', {}, [schema_metrics_instance])


@contextlib.contextmanager
def _patch_query(job, table_rows=None):
    table_rows = table_rows or []
    with (
        mock.patch.object(job, '_execute_query', side_effect=lambda q: table_rows),
        mock.patch.object(job._check, 'execute_query_raw', return_value=[]),
    ):
        yield


def test_initialization(check):
    assert isinstance(check.table_metrics, ClickhouseTableMetrics)
    assert check.table_metrics._collection_interval == 60


def test_default_disabled_when_dbm_on():
    check = ClickhouseCheck('clickhouse', {}, [{'server': 'localhost', 'dbm': True}])
    assert check.table_metrics is None


def test_disabled_when_dbm_off():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': False, 'schema_metrics': {'enabled': True}}],
    )
    assert check.table_metrics is None


def test_disabled_when_explicitly_opted_out():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'schema_metrics': {'enabled': False}}],
    )
    assert check.table_metrics is None


@pytest.mark.parametrize('bad_value', [None, 0, -1])
def test_init_falls_back_when_collection_interval_is_invalid(bad_value):
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'schema_metrics': {'enabled': True, 'collection_interval': bad_value},
            }
        ],
    )
    assert check.table_metrics is not None
    assert check.table_metrics._collection_interval == 60


def test_run_job_emits_table_size_gauges(check):
    job = check.table_metrics
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    with _patch_query(job, table_rows=[_table_size_row(name='events', total_rows=1000, total_bytes=2048)]):
        job.run_job()

    by_name = {n: (v, t) for n, v, t in emitted}
    assert by_name['table.rows'][0] == 1000
    assert by_name['table.bytes'][0] == 2048
    tags = by_name['table.rows'][1]
    assert 'db:default' in tags
    assert 'table:events' in tags


def test_run_job_uses_table_database_not_connection_db(check):
    # A table in a non-connection database must be tagged with its own `db:` only —
    # not the instance's `db:default` base tag (which would double-tag the series).
    job = check.table_metrics
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    with _patch_query(job, table_rows=[_table_size_row(database='dd_test', name='orders')]):
        job.run_job()

    tags = next(t for n, _, t in emitted if n == 'table.rows')
    db_tags = [t for t in tags if t.startswith('db:')]
    assert db_tags == ['db:dd_test'], db_tags
    assert 'table:orders' in tags


def test_run_job_table_sizes_query_dedupes_via_limit_by(check):
    # Dedup across clusterAllReplicas replica rows is handled in SQL via
    # LIMIT 1 BY database, name — not in Python.
    job = check.table_metrics
    captured = []

    with mock.patch.object(job, '_execute_query', side_effect=lambda q: captured.append(q) or []):
        with mock.patch.object(job._check, 'execute_query_raw', return_value=[]):
            job.run_job()

    assert len(captured) == 1
    assert 'LIMIT 1 BY database, name' in captured[0]


def test_cancel_closes_db_client(check):
    job = check.table_metrics
    fake_client = mock.MagicMock()
    job._db_client = fake_client

    job.cancel()

    assert job._db_client is None
    fake_client.close.assert_called_once()


def test_routes_through_cluster_all_replicas_in_single_endpoint_mode(schema_metrics_instance):
    schema_metrics_instance['single_endpoint_mode'] = True
    check = ClickhouseCheck('clickhouse', {}, [schema_metrics_instance])
    dbm_queries = []
    raw_queries = []

    check.gauge = lambda *a, **kw: None
    with (
        mock.patch.object(check.table_metrics, '_execute_query', side_effect=lambda q: dbm_queries.append(q) or []),
        mock.patch.object(check, 'execute_query_raw', side_effect=lambda q: raw_queries.append(q) or []),
    ):
        check.table_metrics.run_job()

    assert any("clusterAllReplicas('default', system.tables)" in q for q in dbm_queries)
    assert any("clusterAllReplicas('default', system.view_refreshes)" in q for q in raw_queries)


# --- View refresh metric tests ---


def _patch_view_refresh_query(check, rows):
    return mock.patch.object(check, 'execute_query_raw', return_value=rows)


def test_collect_view_refresh_emits_gauges(check):
    job = check.table_metrics
    gauges = []
    check.gauge = lambda name, value, tags=None: gauges.append((name, value, tags))

    row = _view_refresh_row(status='Scheduled', written_rows=500, written_bytes=4096)
    with _patch_view_refresh_query(check, [row]):
        job._collect_view_refresh_metrics()

    by_name = {n: (v, t) for n, v, t in gauges}
    assert by_name['view.refresh.status'][0] == AgentCheck.OK
    assert 'db:mydb' in by_name['view.refresh.status'][1]
    assert 'view:mv_orders' in by_name['view.refresh.status'][1]
    assert 'host:replica-1' in by_name['view.refresh.status'][1]
    assert 'clickhouse_node:replica-1' in by_name['view.refresh.status'][1]
    assert by_name['view.refresh.rows'][0] == 500
    assert by_name['view.refresh.bytes'][0] == 4096


def test_collect_view_refresh_error_status_emits_critical_gauge(check):
    job = check.table_metrics
    gauges = []
    check.gauge = lambda name, value, tags=None: gauges.append((name, value, tags))

    row = _view_refresh_row(status='Error', exception='Timeout exceeded\nmore detail')
    with _patch_view_refresh_query(check, [row]):
        job._collect_view_refresh_metrics()

    status_gauge = next(v for n, v, _ in gauges if n == 'view.refresh.status')
    assert status_gauge == AgentCheck.CRITICAL


def test_collect_view_refresh_unknown_status_emits_unknown_gauge(check):
    job = check.table_metrics
    gauges = []
    check.gauge = lambda name, value, tags=None: gauges.append((name, value, tags))

    with _patch_view_refresh_query(check, [_view_refresh_row(status='SomeFutureStatus')]):
        job._collect_view_refresh_metrics()

    status_gauge = next(v for n, v, _ in gauges if n == 'view.refresh.status')
    assert status_gauge == AgentCheck.UNKNOWN


def test_collect_view_refresh_drops_instance_db_tag(check):
    job = check.table_metrics
    emitted_tags = []
    check.gauge = lambda name, value, tags=None: emitted_tags.append(tags)

    with _patch_view_refresh_query(check, [_view_refresh_row(database='analytics')]):
        job._collect_view_refresh_metrics()

    db_tags = [t for tags in emitted_tags for t in tags if t.startswith('db:')]
    assert all(t == 'db:analytics' for t in db_tags), db_tags


def test_collect_view_refresh_skips_when_flag_set(check):
    job = check.table_metrics
    job._view_refreshes_skip = True

    with mock.patch.object(check, 'execute_query_raw') as mock_query:
        job._collect_view_refresh_metrics()

    mock_query.assert_not_called()


def test_handle_view_refreshes_unknown_table_sets_skip_and_logs_once(check):
    job = check.table_metrics
    with mock.patch.object(job._log, 'info') as mock_log:
        job._handle_view_refreshes_error(Exception("DB::Exception: Unknown table system.view_refreshes"))
        job._handle_view_refreshes_error(Exception("DB::Exception: Unknown table system.view_refreshes"))

    assert job._view_refreshes_skip is True
    mock_log.assert_called_once()


def test_handle_view_refreshes_permission_denied_sets_skip_and_logs_once(check):
    job = check.table_metrics
    with mock.patch.object(job._log, 'warning') as mock_log:
        job._handle_view_refreshes_error(Exception("Not enough privileges"))
        job._handle_view_refreshes_error(Exception("Not enough privileges"))

    assert job._view_refreshes_skip is True
    mock_log.assert_called_once()
    assert 'Restart the agent' in mock_log.call_args[0][0]


def test_handle_view_refreshes_unexpected_error_does_not_set_skip(check):
    job = check.table_metrics
    with mock.patch.object(job._log, 'exception'):
        job._handle_view_refreshes_error(Exception("some random error"))

    assert job._view_refreshes_skip is False
