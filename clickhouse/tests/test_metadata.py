# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import json
import threading
from unittest import mock

import pytest
from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.metadata import ClickhouseMetadata
from datadog_checks.clickhouse.schemas import (
    ClickhouseSchemaCollector,
    _build_match_clauses,
)

pytestmark = pytest.mark.unit


def _column_row(name='id', type_='UInt64', default='', comment='', position=1):
    """Column tuple as returned by groupArrayIf in the combined CTE query."""
    return (name, type_, default, comment, position)


def _table_row(
    database='default',
    name='events',
    engine='MergeTree',
    uuid_str='uuid-1',
    create_query='CREATE TABLE default.events (id UInt64) ENGINE = MergeTree ORDER BY id',
    sorting_key='id',
    partition_key='',
    primary_key='id',
    sampling_key='',
    metadata_modified_at=1700000000,
    columns=None,
):
    return (
        database,
        name,
        engine,
        uuid_str,
        create_query,
        sorting_key,
        partition_key,
        primary_key,
        sampling_key,
        metadata_modified_at,
        columns or [],
    )


def _view_row(
    database='default',
    name='events_mv',
    engine='MaterializedView',
    uuid_str='uuid-2',
    create_query='CREATE MATERIALIZED VIEW default.events_mv TO default.events_target AS SELECT * FROM default.events',
    metadata_modified_at=1700001000,
    columns=None,
):
    return _table_row(
        database=database,
        name=name,
        engine=engine,
        uuid_str=uuid_str,
        create_query=create_query,
        sorting_key='',
        partition_key='',
        primary_key='',
        sampling_key='',
        metadata_modified_at=metadata_modified_at,
        columns=columns,
    )


def _refresh_row(database='default', view='events_mv', exception=''):
    return (database, view, exception)


@pytest.fixture
def collect_schemas_instance():
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'collect_schemas': {
            'enabled': True,
            'collection_interval': 600,
            'max_tables': 5000,
            'max_columns': 1000,
            'run_sync': True,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check(collect_schemas_instance):
    return ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])


@pytest.fixture
def collector(check) -> ClickhouseSchemaCollector:
    return check.metadata._schema_collector


def _make_query_result(rows):
    rows = list(rows)
    result = mock.MagicMock()
    result.result_set = rows
    result.result_rows = rows
    result.column_names = ('c0',)
    result.column_types = ()
    result.summary = {}
    return result


@contextlib.contextmanager
def _patch_query(collector, table_rows=None, refresh_rows=None):
    """Mocks the DBM client for the two cluster-wide queries.

    - view_refreshes goes through client.query() → result_rows
    - combined tables+columns CTE goes through client.query() → result_rows
    """
    table_rows = table_rows or []
    refresh_rows = refresh_rows or []

    def fake_client_query(query, *args, **kwargs):
        if 'view_refreshes' in query:
            return _make_query_result(refresh_rows)
        return _make_query_result(table_rows)

    mock_client = mock.MagicMock()
    mock_client.query.side_effect = fake_client_query

    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        yield mock_client


def _capture_payloads(check):
    captured: list[dict] = []
    check.database_monitoring_metadata = lambda raw: captured.append(json.loads(raw))
    check.gauge = lambda *a, **kw: None
    return captured


def _run_collect(check, table_rows=None, refresh_rows=None):
    captured = _capture_payloads(check)
    with _patch_query(check.metadata._schema_collector, table_rows, refresh_rows):
        check.metadata._schema_collector.collect_schemas()
    return captured


@contextlib.contextmanager
def _capture_all_queries(collector):
    """Records every SQL string sent through the DBM client."""
    seen: list[str] = []

    def fake_client_query(query, *args, **kwargs):
        seen.append(query)
        return _make_query_result([])

    mock_client = mock.MagicMock()
    mock_client.query.side_effect = fake_client_query

    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        yield seen


def test_initialization(check):
    assert isinstance(check.metadata, ClickhouseMetadata)
    assert isinstance(check.metadata._schema_collector, ClickhouseSchemaCollector)
    assert check.metadata._collection_interval == 600
    assert check.metadata._schema_collector._config.max_tables == 5000
    assert check.metadata._schema_collector._config.max_columns == 1000


def test_kind(collector):
    assert collector.kind == 'clickhouse_databases'


def test_init_collection_interval_omitted_uses_default():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'collect_schemas': {'enabled': True}}],
    )
    assert check.metadata is not None
    assert check.metadata._collection_interval == 600


def test_init_max_tables_omitted_uses_default():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'collect_schemas': {'enabled': True}}],
    )
    assert check.metadata._schema_collector._config.max_tables == 300


def test_init_max_query_duration_omitted_uses_default():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'collect_schemas': {'enabled': True}}],
    )
    assert check.metadata._schema_collector._config.max_query_duration == 60


def test_init_filters_omitted_default_to_empty_tuples():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'collect_schemas': {'enabled': True}}],
    )
    cfg = check.metadata._schema_collector._config
    assert cfg.include_databases == ()
    assert cfg.exclude_databases == ()
    assert cfg.include_tables == ()
    assert cfg.exclude_tables == ()


def test_disabled_when_dbm_off():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': False, 'collect_schemas': {'enabled': True, 'collection_interval': 600}}],
    )
    assert check.metadata is None


def test_disabled_by_default_when_dbm_on():
    check = ClickhouseCheck('clickhouse', {}, [{'server': 'localhost', 'dbm': True}])
    assert check.metadata is None


def test_disabled_when_explicitly_opted_out():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'collect_schemas': {'enabled': False, 'collection_interval': 600}}],
    )
    assert check.metadata is None


def test_collect_emits_single_payload_when_small(check):
    payloads = _run_collect(
        check,
        table_rows=[
            _table_row(name='events', columns=[_column_row(name='id')]),
            _view_row(name='events_mv'),
        ],
        refresh_rows=[_refresh_row(view='events_mv')],
    )
    assert len(payloads) == 1
    p = payloads[0]
    assert p['kind'] == 'clickhouse_databases'
    assert p['dbms'] == 'clickhouse'
    assert p['collection_payloads_count'] == 1
    assert p['collection_started_at'] > 0
    assert 'host' in p
    assert 'collector_id' in p


def test_collect_payload_contains_tables_and_views(check):
    payloads = _run_collect(
        check,
        table_rows=[_table_row(name='events'), _view_row(name='events_mv')],
        refresh_rows=[_refresh_row(view='events_mv')],
    )
    dbs = payloads[0]['metadata']
    table_names = {t['name'] for db in dbs for t in db['tables']}
    view_names = {v['name'] for db in dbs for v in db['views']}
    assert 'events' in table_names
    assert 'events_mv' in view_names
    refreshable_view = next(v for db in dbs for v in db['views'] if v['name'] == 'events_mv')
    assert refreshable_view['is_refreshable'] is True


@pytest.mark.parametrize('engine', ['View', 'LiveView', 'WindowView'])
def test_collect_routes_other_view_engines(check, engine):
    payloads = _run_collect(check, table_rows=[_view_row(name='some_view', engine=engine)])
    dbs = payloads[0]['metadata']
    views = [v for db in dbs for v in db['views']]
    assert [v['name'] for v in views] == ['some_view']
    assert views[0]['engine'] == engine


def test_collect_dedupes_replica_rows_via_sql(check):
    payloads = _run_collect(check, table_rows=[_table_row(name='events')])
    dbs = payloads[0]['metadata']
    table_names = [t['name'] for db in dbs for t in db['tables']]
    assert table_names == ['events']


def test_collect_emits_empty_snapshot_marker_when_no_tables(check):
    # An empty run still emits one terminal payload so the backend receives a
    # snapshot marker (collection_payloads_count) and can clear stale state.
    payloads = _run_collect(check, table_rows=[])
    assert len(payloads) == 1
    assert payloads[0]['metadata'] == []
    assert payloads[0]['collection_payloads_count'] == 1


def test_collect_marks_view_refreshable_only_when_refresh_row_present(check):
    payloads = _run_collect(
        check,
        table_rows=[
            _view_row(name='refreshable_mv'),
            _view_row(
                name='vanilla_view',
                engine='View',
                create_query='CREATE VIEW default.vanilla_view AS SELECT 1',
            ),
        ],
        refresh_rows=[_refresh_row(view='refreshable_mv')],
    )
    by_name = {v['name']: v for db in payloads[0]['metadata'] for v in db['views']}
    assert by_name['refreshable_mv']['is_refreshable'] is True
    assert by_name['vanilla_view']['is_refreshable'] is False


def test_collect_columns_attached_to_correct_parent(check):
    payloads = _run_collect(
        check,
        table_rows=[
            _table_row(name='events', columns=[_column_row(name='id')]),
            _view_row(name='events_mv', columns=[_column_row(name='count', type_='UInt64')]),
        ],
    )
    dbs = payloads[0]['metadata']
    table = next(t for db in dbs for t in db['tables'] if t['name'] == 'events')
    view = next(v for db in dbs for v in db['views'] if v['name'] == 'events_mv')
    assert [c['name'] for c in table['columns']] == ['id']
    assert [c['name'] for c in view['columns']] == ['count']


def test_collect_chunks_when_payload_chunk_size_exceeded(check):
    check.metadata._schema_collector._config.payload_chunk_size = 5
    rows = [_table_row(name=f'big_{i}') for i in range(12)]

    payloads = _run_collect(check, table_rows=rows)

    assert len(payloads) >= 2
    emitted_total = sum(len(db['tables']) + len(db['views']) for p in payloads for db in p['metadata'])
    assert emitted_total == 12


def test_collect_collection_payloads_count_only_on_last(check):
    check.metadata._schema_collector._config.payload_chunk_size = 5
    rows = [_table_row(name=f'big_{i}') for i in range(12)]

    payloads = _run_collect(check, table_rows=rows)

    for intermediate in payloads[:-1]:
        assert 'collection_payloads_count' not in intermediate
    assert payloads[-1]['collection_payloads_count'] == len(payloads)


def test_collect_all_chunks_share_collection_started_at(check):
    check.metadata._schema_collector._config.payload_chunk_size = 5
    rows = [_table_row(name=f'big_{i}') for i in range(12)]

    payloads = _run_collect(check, table_rows=rows)

    started_ats = {p['collection_started_at'] for p in payloads}
    assert len(started_ats) == 1


def test_collect_view_refreshes_unknown_table_logs_once(collector):
    collector._log = mock.MagicMock()
    with mock.patch.object(collector, '_execute_query', side_effect=Exception('Unknown table system.view_refreshes')):
        assert collector._collect_view_refreshes('') == []
        assert collector._collect_view_refreshes('') == []
    assert len(collector._log.info.call_args_list) == 1


def test_collect_view_refreshes_permission_denied_logs_once(collector):
    collector._log = mock.MagicMock()
    with mock.patch.object(
        collector, '_execute_query', side_effect=Exception('Not enough privileges to access system.view_refreshes')
    ):
        assert collector._collect_view_refreshes('') == []
        assert collector._collect_view_refreshes('') == []
    assert len(collector._log.warning.call_args_list) == 1


def test_collect_view_refreshes_unexpected_error_logs_exception(collector):
    collector._log = mock.MagicMock()
    with mock.patch.object(collector, '_execute_query', side_effect=Exception('boom')):
        assert collector._collect_view_refreshes('') == []
    collector._log.exception.assert_called_once()


def test_cancel_closes_db_client(check):
    fake_client = mock.MagicMock()
    check.metadata._schema_collector._db_client = fake_client

    check.metadata.cancel()

    assert check.metadata._schema_collector._db_client is None
    fake_client.close.assert_called_once()


def test_combined_query_dedupes_replicas_before_limit(check):
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    combined_query = next(q for q in seen_queries if 'FROM system.tables' in q)
    dedup_idx = combined_query.find('LIMIT 1 BY (database, name)')
    outer_limit_idx = combined_query.find('LIMIT 5000')
    assert dedup_idx >= 0
    assert outer_limit_idx >= 0
    assert dedup_idx < outer_limit_idx


def test_combined_query_joins_columns_and_caps_per_table(check):
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    combined_query = next(q for q in seen_queries if 'FROM system.columns' in q)
    assert '(database, table) IN (' in combined_query
    assert 'FROM system.tables' in combined_query
    assert 'LIMIT 1 BY (database, name)' in combined_query
    assert 'LIMIT 1 BY (database, table, name)' in combined_query
    # limit_columns = max_tables * max_columns = 5000 * 1000
    assert 'LIMIT 5000000' in combined_query
    # per-table cap via groupArrayIf
    assert 'groupArrayIf(1000)' in combined_query


def test_collect_routes_through_cluster_all_replicas_in_single_endpoint_mode(collect_schemas_instance):
    collect_schemas_instance['single_endpoint_mode'] = True
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    joined = '\n'.join(seen_queries)
    assert "clusterAllReplicas('default', system.tables)" in joined
    assert "clusterAllReplicas('default', system.columns)" in joined
    assert "clusterAllReplicas('default', system.view_refreshes)" in joined


def test_build_match_clauses_empty_returns_empty_string():
    assert _build_match_clauses('database', (), ()) == ''


def test_build_match_clauses_excludes_only():
    out = _build_match_clauses('database', (), ('tmp_.*', 'shadow_.*'))
    assert "AND NOT match(database, 'tmp_.*')" in out
    assert "AND NOT match(database, 'shadow_.*')" in out


def test_build_match_clauses_includes_become_or_disjunction():
    out = _build_match_clauses('name', ('events.*', 'orders.*'), ())
    assert "AND (match(name, 'events.*') OR match(name, 'orders.*'))" in out


def test_build_match_clauses_single_include_pattern():
    out = _build_match_clauses('name', ('only_one.*',), ())
    assert "AND (match(name, 'only_one.*'))" in out
    assert " OR " not in out


def test_build_match_clauses_excludes_appear_before_includes():
    out = _build_match_clauses('database', ('keep_.*',), ('drop_.*',))
    exclude_idx = out.find("AND NOT match(database, 'drop_.*')")
    include_idx = out.find("AND (match(database, 'keep_.*'))")
    assert exclude_idx >= 0 and include_idx >= 0
    assert exclude_idx < include_idx


def test_build_match_clauses_combines_includes_and_excludes():
    out = _build_match_clauses('database', ('keep_.*',), ('drop_.*',))
    assert "AND NOT match(database, 'drop_.*')" in out
    assert "AND (match(database, 'keep_.*'))" in out


def test_build_match_clauses_escapes_single_quotes():
    out = _build_match_clauses('database', (), ("o'reilly_.*",))
    assert "AND NOT match(database, 'o''reilly_.*')" in out


def test_database_filters_appear_in_combined_query(collect_schemas_instance):
    collect_schemas_instance['collect_schemas']['exclude_databases'] = ['tmp_.*']
    collect_schemas_instance['collect_schemas']['include_databases'] = ['keep_.*']
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    combined_query = next(q for q in seen_queries if 'FROM system.tables' in q)
    assert "AND NOT match(database, 'tmp_.*')" in combined_query
    assert "AND (match(database, 'keep_.*'))" in combined_query


def test_table_filters_appear_in_combined_query(collect_schemas_instance):
    collect_schemas_instance['collect_schemas']['include_tables'] = ['events.*']
    collect_schemas_instance['collect_schemas']['exclude_tables'] = ['tmp_.*']
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    combined_query = next(q for q in seen_queries if 'FROM system.tables' in q)
    assert "AND NOT match(name, 'tmp_.*')" in combined_query
    assert "AND (match(name, 'events.*'))" in combined_query


def test_all_cluster_fanout_queries_dedupe_replica_rows(check):
    """Every query that hits a system table needs LIMIT 1 BY to prevent replica fan-out duplicates."""
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    refreshes_query = next(q for q in seen_queries if 'system.view_refreshes' in q)
    combined_query = next(q for q in seen_queries if 'FROM system.tables' in q)

    assert 'LIMIT 1 BY (database, view)' in refreshes_query
    assert 'LIMIT 1 BY (database, name)' in combined_query
    assert 'LIMIT 1 BY (database, table, name)' in combined_query


def test_system_databases_excluded_from_all_queries(collect_schemas_instance):
    """All cluster-wide queries hard-exclude ClickHouse's internal databases."""
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    for kw in ('system.tables', 'system.columns', 'system.view_refreshes'):
        q = next(q for q in seen_queries if kw in q)
        assert "database NOT IN (" in q


def test_collect_uses_local_system_tables_in_direct_mode(check):
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    joined = '\n'.join(seen_queries)
    assert 'clusterAllReplicas' not in joined
    assert 'FROM system.tables' in joined
    assert 'FROM system.columns' in joined
    assert 'FROM system.view_refreshes' in joined


def test_max_execution_time_set_on_client(collector):
    _capture_payloads(collector._check)
    with _patch_query(collector) as mock_client:
        collector.collect_schemas()

    mock_client.set_client_setting.assert_called_once_with('max_execution_time', collector._config.max_query_duration)


def test_main_query_failure_closes_client(collector):
    def fake_query(query, *args, **kwargs):
        if 'view_refreshes' in query:
            return _make_query_result([])
        raise Exception("main query failed")

    mock_client = mock.MagicMock()
    mock_client.query.side_effect = fake_query

    _capture_payloads(collector._check)
    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        with pytest.raises(Exception, match="main query failed"):
            collector.collect_schemas()

    mock_client.close.assert_called_once()
    assert collector._db_client is None


def test_cancel_event_aborts_before_query(collector):
    cancel_event = threading.Event()
    collector._cancel_event = cancel_event
    cancel_event.set()

    collector._db_client = mock.MagicMock()

    with pytest.raises(Exception, match="cancelled"):
        collector._execute_query("SELECT 1")

    collector._db_client.query.assert_not_called()
