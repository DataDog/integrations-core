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
def _patch_query(collector, table_rows=None):
    """Mocks the DBM client for the combined tables+columns CTE query."""
    table_rows = table_rows or []

    @contextlib.contextmanager
    def fake_stream(query, *args, **kwargs):
        yield iter(table_rows)

    mock_client = mock.MagicMock()
    mock_client.query_rows_stream.side_effect = fake_stream

    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        yield mock_client


def _capture_payloads(check):
    captured: list[dict] = []
    check.database_monitoring_metadata = lambda raw: captured.append(json.loads(raw))
    check.gauge = lambda *a, **kw: None
    return captured


def _run_collect(check, table_rows=None):
    captured = _capture_payloads(check)
    with _patch_query(check.metadata._schema_collector, table_rows):
        check.metadata._schema_collector.collect_schemas()
    return captured


@contextlib.contextmanager
def _capture_all_queries(collector):
    """Records every SQL string sent through the DBM client."""
    seen: list[str] = []

    def fake_client_query(query, *args, **kwargs):
        seen.append(query)
        return _make_query_result([])

    @contextlib.contextmanager
    def fake_stream(query, *args, **kwargs):
        seen.append(query)
        yield iter([])

    mock_client = mock.MagicMock()
    mock_client.query.side_effect = fake_client_query
    mock_client.query_rows_stream.side_effect = fake_stream

    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        yield seen


@contextlib.contextmanager
def _capture_query_params(collector):
    """Records (query, parameters) for each query_rows_stream call."""
    calls: list[tuple[str, dict]] = []

    @contextlib.contextmanager
    def fake_stream(query, *args, **kwargs):
        calls.append((query, kwargs.get('parameters') or {}))
        yield iter([])

    mock_client = mock.MagicMock()
    mock_client.query_rows_stream.side_effect = fake_stream

    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        yield calls


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
    )
    assert len(payloads) == 1
    p = payloads[0]
    assert p['kind'] == 'clickhouse_databases'
    assert p['dbms'] == 'clickhouse'
    assert p['collection_payloads_count'] == 1
    assert p['collection_started_at'] > 0
    assert 'host' in p
    assert 'collector_id' in p


def test_collect_payload_tables_list_includes_views(check):
    payloads = _run_collect(
        check,
        table_rows=[
            _table_row(name='events'),
            _view_row(
                name='events_mv',
                create_query=(
                    'CREATE MATERIALIZED VIEW default.events_mv'
                    ' REFRESH EVERY 1 HOUR TO default.events_target'
                    ' AS SELECT * FROM default.events'
                ),
            ),
        ],
    )
    dbs = payloads[0]['metadata']
    # Tables and views share a single `tables` list; views are identified by engine.
    items = {t['name']: t for db in dbs for t in db['tables']}
    assert 'events' in items
    assert 'events_mv' in items
    assert items['events_mv']['engine'] == 'MaterializedView'
    assert items['events_mv']['is_refreshable'] is True


@pytest.mark.parametrize('engine', ['View', 'LiveView', 'WindowView'])
def test_collect_view_engines_appear_in_tables_list(check, engine):
    payloads = _run_collect(check, table_rows=[_view_row(name='some_view', engine=engine)])
    dbs = payloads[0]['metadata']
    items = [t for db in dbs for t in db['tables']]
    assert [t['name'] for t in items] == ['some_view']
    assert items[0]['engine'] == engine


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


def test_collect_marks_view_refreshable_based_on_create_query(check):
    payloads = _run_collect(
        check,
        table_rows=[
            _view_row(
                name='refreshable_mv',
                create_query=(
                    'CREATE MATERIALIZED VIEW default.refreshable_mv'
                    ' REFRESH EVERY 1 HOUR TO default.target'
                    ' AS SELECT * FROM default.src'
                ),
            ),
            _view_row(
                name='vanilla_view',
                engine='View',
                create_query='CREATE VIEW default.vanilla_view AS SELECT 1',
            ),
        ],
    )
    by_name = {t['name']: t for db in payloads[0]['metadata'] for t in db['tables']}
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
    view = next(t for db in dbs for t in db['tables'] if t['name'] == 'events_mv')
    assert [c['name'] for c in table['columns']] == ['id']
    assert [c['name'] for c in view['columns']] == ['count']


def test_collect_chunks_when_payload_chunk_size_exceeded(check):
    check.metadata._schema_collector._config.payload_chunk_size = 5
    rows = [_table_row(name=f'big_{i}') for i in range(12)]

    payloads = _run_collect(check, table_rows=rows)

    assert len(payloads) >= 2
    emitted_total = sum(len(db['tables']) for p in payloads for db in p['metadata'])
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


def test_build_match_clauses_empty_returns_empty_string():
    assert _build_match_clauses('database', (), (), 'db') == ('', {})


def test_build_match_clauses_excludes_only():
    out, params = _build_match_clauses('database', (), ('tmp_.*', 'shadow_.*'), 'db')
    assert "AND NOT match(database, {db_exclude_0:String})" in out
    assert "AND NOT match(database, {db_exclude_1:String})" in out
    assert params == {'db_exclude_0': 'tmp_.*', 'db_exclude_1': 'shadow_.*'}


def test_build_match_clauses_includes_become_or_disjunction():
    out, params = _build_match_clauses('name', ('events.*', 'orders.*'), (), 'table')
    assert "AND (match(name, {table_include_0:String}) OR match(name, {table_include_1:String}))" in out
    assert params == {'table_include_0': 'events.*', 'table_include_1': 'orders.*'}


def test_build_match_clauses_single_include_pattern():
    out, params = _build_match_clauses('name', ('only_one.*',), (), 'table')
    assert "AND (match(name, {table_include_0:String}))" in out
    assert " OR " not in out
    assert params == {'table_include_0': 'only_one.*'}


def test_build_match_clauses_excludes_appear_before_includes():
    out, _ = _build_match_clauses('database', ('keep_.*',), ('drop_.*',), 'db')
    exclude_idx = out.find("AND NOT match(database, {db_exclude_0:String})")
    include_idx = out.find("AND (match(database, {db_include_0:String}))")
    assert exclude_idx >= 0 and include_idx >= 0
    assert exclude_idx < include_idx


def test_build_match_clauses_combines_includes_and_excludes():
    out, params = _build_match_clauses('database', ('keep_.*',), ('drop_.*',), 'db')
    assert "AND NOT match(database, {db_exclude_0:String})" in out
    assert "AND (match(database, {db_include_0:String}))" in out
    assert params == {'db_exclude_0': 'drop_.*', 'db_include_0': 'keep_.*'}


def test_build_match_clauses_passes_pattern_verbatim_as_parameter():
    # SQL-injection guard: a pattern containing a quote is bound as a parameter
    # value, not escaped/interpolated into the SQL text.
    out, params = _build_match_clauses('database', (), ("o'reilly_.*",), 'db')
    assert out == "AND NOT match(database, {db_exclude_0:String})"
    assert params == {'db_exclude_0': "o'reilly_.*"}


def test_database_filters_appear_in_combined_query(collect_schemas_instance):
    collect_schemas_instance['collect_schemas']['exclude_databases'] = ['tmp_.*']
    collect_schemas_instance['collect_schemas']['include_databases'] = ['keep_.*']
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_query_params(check.metadata._schema_collector) as calls:
        check.metadata._schema_collector.collect_schemas()

    combined_query, params = next((q, p) for q, p in calls if 'FROM system.tables' in q)
    assert "AND NOT match(database, {db_exclude_0:String})" in combined_query
    assert "AND (match(database, {db_include_0:String}))" in combined_query
    assert params['db_exclude_0'] == 'tmp_.*'
    assert params['db_include_0'] == 'keep_.*'


def test_table_filters_appear_in_combined_query(collect_schemas_instance):
    collect_schemas_instance['collect_schemas']['include_tables'] = ['events.*']
    collect_schemas_instance['collect_schemas']['exclude_tables'] = ['tmp_.*']
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_query_params(check.metadata._schema_collector) as calls:
        check.metadata._schema_collector.collect_schemas()

    combined_query, params = next((q, p) for q, p in calls if 'FROM system.tables' in q)
    assert "AND NOT match(name, {table_exclude_0:String})" in combined_query
    assert "AND (match(name, {table_include_0:String}))" in combined_query
    assert params['table_exclude_0'] == 'tmp_.*'
    assert params['table_include_0'] == 'events.*'


def test_all_cluster_fanout_queries_dedupe_replica_rows(check):
    """Every query that hits a system table needs LIMIT 1 BY to prevent replica fan-out duplicates."""
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    combined_query = next(q for q in seen_queries if 'FROM system.tables' in q)

    assert 'LIMIT 1 BY (database, name)' in combined_query
    assert 'LIMIT 1 BY (database, table, name)' in combined_query


def test_system_databases_excluded_from_all_queries(collect_schemas_instance):
    """All cluster-wide queries hard-exclude ClickHouse's internal databases."""
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    _capture_payloads(check)
    with _capture_all_queries(check.metadata._schema_collector) as seen_queries:
        check.metadata._schema_collector.collect_schemas()

    for kw in ('system.tables', 'system.columns'):
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


def test_max_execution_time_set_on_client(collector):
    _capture_payloads(collector._check)
    with _patch_query(collector) as mock_client:
        collector.collect_schemas()

    mock_client.set_client_setting.assert_called_once_with('max_execution_time', collector._config.max_query_duration)


def test_main_query_failure_closes_client(collector):
    # The base class catches per-DB errors and continues; the caller (run_job) catches
    # any remaining exception. What matters is that the client is properly closed.
    mock_client = mock.MagicMock()
    mock_client.query_rows_stream.return_value.__enter__.side_effect = Exception("main query failed")

    _capture_payloads(collector._check)
    with mock.patch.object(collector._check, 'create_dbm_client', return_value=mock_client):
        collector.collect_schemas()

    mock_client.close.assert_called_once()
    assert collector._db_client is None


def test_payload_chunking(check, collector):
    # Set a small chunk size so 7 tables produce 3 separate payloads.
    collector._config.payload_chunk_size = 3
    table_rows = [_table_row(name=f'tbl_{i}') for i in range(7)]
    captured = _run_collect(check, table_rows=table_rows)

    # Three payloads: rows 0-2, rows 3-5, row 6
    assert len(captured) == 3

    # Only the last payload carries collection_payloads_count (snapshot marker)
    assert 'collection_payloads_count' not in captured[0]
    assert 'collection_payloads_count' not in captured[1]
    assert captured[2]['collection_payloads_count'] == 3

    # Non-final chunks hold exactly chunk_size rows; final chunk holds the remainder
    assert len(captured[0]['metadata']) == 3
    assert len(captured[1]['metadata']) == 3
    assert len(captured[2]['metadata']) == 1

    # Every table appears exactly once across all payloads
    all_names = [
        entry['tables'][0]['name'] for payload in captured for entry in payload['metadata'] if entry.get('tables')
    ]
    assert sorted(all_names) == sorted(f'tbl_{i}' for i in range(7))

    # Schema kind is correct on every payload
    assert all(p['kind'] == 'clickhouse_databases' for p in captured)


def test_cancel_event_aborts_before_query(collector):
    cancel_event = threading.Event()
    collector._cancel_event = cancel_event
    cancel_event.set()

    with pytest.raises(Exception, match="cancelled"):
        collector._check_cancelled()
