# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.config_models.instance import CollectSchemas
from datadog_checks.clickhouse.metadata import (
    _CREATE_QUERY_MAX_BYTES,
    _CREATE_QUERY_TRUNC_SUFFIX,
    _PAYLOAD_MAX_BYTES,
    ClickhouseMetadata,
    _parse_view_sources,
    _parse_view_target,
    _truncate_ddl,
)

pytestmark = pytest.mark.unit


def _table_row(
    database='default',
    name='events',
    engine='MergeTree',
    uuid_str='uuid-1',
    total_rows=10,
    total_bytes=1024,
    create_query='CREATE TABLE default.events (id UInt64) ENGINE = MergeTree ORDER BY id',
    sorting_key='id',
    partition_key='',
    primary_key='id',
    sampling_key='',
    metadata_modified_at=1700000000,
    as_select='',
):
    return (
        database,
        name,
        engine,
        uuid_str,
        total_rows,
        total_bytes,
        create_query,
        sorting_key,
        partition_key,
        primary_key,
        sampling_key,
        metadata_modified_at,
        as_select,
    )


def _view_row(
    database='default',
    name='events_mv',
    engine='MaterializedView',
    uuid_str='uuid-2',
    create_query=(
        'CREATE MATERIALIZED VIEW default.events_mv TO default.events_target AS SELECT * FROM default.events'
    ),
    as_select='SELECT * FROM default.events',
    metadata_modified_at=1700001000,
):
    return _table_row(
        database=database,
        name=name,
        engine=engine,
        uuid_str=uuid_str,
        total_rows=0,
        total_bytes=0,
        create_query=create_query,
        sorting_key='',
        partition_key='',
        primary_key='',
        sampling_key='',
        metadata_modified_at=metadata_modified_at,
        as_select=as_select,
    )


def _column_row(database='default', table='events', name='id', type_='UInt64', default='', comment='', position=1):
    return (database, table, name, type_, default, comment, position)


def _refresh_row(
    database='default',
    view='events_mv',
    status='Ok',
    last_refresh_time=1700001000,
    next_refresh_time=1700001600,
    exception='',
    written_rows=10,
    written_bytes=512,
):
    return (database, view, status, last_refresh_time, next_refresh_time, exception, written_rows, written_bytes)


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


def test_initialization(check):
    assert isinstance(check.metadata, ClickhouseMetadata)
    assert check.metadata._config.enabled is True
    assert check.metadata._collection_interval == 600
    assert check.metadata._max_tables == 5000
    assert check.metadata._max_columns == 1000


def test_init_none_optional_max_fields_use_defaults(check):
    config = CollectSchemas(enabled=True, collection_interval=600, run_sync=True, max_tables=None, max_columns=None)
    job = ClickhouseMetadata(check, config)
    assert job._max_tables == 300
    assert job._max_columns == 1000


def test_disabled_when_dbm_off():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': False,
                'collect_schemas': {'enabled': True, 'collection_interval': 600},
            }
        ],
    )
    assert check.metadata is None


def test_disabled_by_default_when_dbm_on():
    check = ClickhouseCheck('clickhouse', {}, [{'server': 'localhost', 'dbm': True}])
    assert check.metadata is None


def test_disabled_when_explicitly_opted_out():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'collect_schemas': {'enabled': False, 'collection_interval': 600},
            }
        ],
    )
    assert check.metadata is None


@pytest.mark.parametrize('value', [None, ''])
def test_truncate_ddl_handles_empty(value):
    assert _truncate_ddl(value) == ''


def test_truncate_ddl_under_cap_returns_as_is():
    ddl = 'CREATE TABLE t (id Int64) ENGINE = MergeTree ORDER BY id'
    assert _truncate_ddl(ddl) == ddl


def test_truncate_ddl_over_cap_appends_suffix():
    ddl = 'A' * (_CREATE_QUERY_MAX_BYTES + 100)
    out = _truncate_ddl(ddl)
    assert out.endswith(_CREATE_QUERY_TRUNC_SUFFIX)
    assert len(out.encode('utf-8')) <= _CREATE_QUERY_MAX_BYTES


def test_truncate_ddl_preserves_utf8_boundary():
    ddl = '☃' * (_CREATE_QUERY_MAX_BYTES // 3 + 50)
    out = _truncate_ddl(ddl)
    out.encode('utf-8').decode('utf-8')
    assert out.endswith(_CREATE_QUERY_TRUNC_SUFFIX)


def test_parse_view_sources_extracts_from_clause():
    dbs, tbls = _parse_view_sources('SELECT * FROM default.events', None)
    assert dbs == ['default']
    assert tbls == ['events']


def test_parse_view_sources_supports_quoted_identifiers():
    dbs, tbls = _parse_view_sources('SELECT * FROM "my db"."my table"', None)
    assert dbs == ['my db']
    assert tbls == ['my table']


def test_parse_view_sources_supports_backtick_identifiers():
    dbs, tbls = _parse_view_sources('SELECT * FROM `db`.`tbl`', None)
    assert dbs == ['db']
    assert tbls == ['tbl']


def test_parse_view_sources_handles_join():
    dbs, tbls = _parse_view_sources('SELECT * FROM a.t1 JOIN b.t2 ON t1.id = t2.id', None)
    assert dbs == ['a', 'b']
    assert tbls == ['t1', 't2']


def test_parse_view_sources_dedupes():
    dbs, tbls = _parse_view_sources('SELECT * FROM a.t1 JOIN a.t1 ON 1=1', None)
    assert dbs == ['a']
    assert tbls == ['t1']


def test_parse_view_sources_unqualified_table():
    dbs, tbls = _parse_view_sources('SELECT * FROM events', None)
    assert dbs == ['']
    assert tbls == ['events']


def test_parse_view_sources_falls_back_to_create_query():
    dbs, tbls = _parse_view_sources(None, 'CREATE VIEW v AS SELECT * FROM default.events')
    assert dbs == ['default']
    assert tbls == ['events']


def test_parse_view_sources_empty_returns_empty():
    assert _parse_view_sources(None, None) == ([], [])
    assert _parse_view_sources('', '') == ([], [])


def test_parse_view_target_extracts_db_qualified():
    db, tbl = _parse_view_target('CREATE MATERIALIZED VIEW default.mv TO target_db.target_tbl AS SELECT * FROM x')
    assert db == 'target_db'
    assert tbl == 'target_tbl'


def test_parse_view_target_unqualified_target_table():
    db, tbl = _parse_view_target('CREATE MATERIALIZED VIEW default.mv TO target_tbl AS SELECT 1')
    assert db is None
    assert tbl == 'target_tbl'


def test_parse_view_target_no_to_clause():
    db, tbl = _parse_view_target('CREATE MATERIALIZED VIEW default.mv AS SELECT 1')
    assert db is None
    assert tbl is None


def test_parse_view_target_handles_quoted_identifiers():
    db, tbl = _parse_view_target('CREATE MATERIALIZED VIEW v TO `target db`.`target tbl` AS SELECT 1')
    assert db == 'target db'
    assert tbl == 'target tbl'


def test_parse_view_target_returns_none_for_empty():
    assert _parse_view_target(None) == (None, None)
    assert _parse_view_target('') == (None, None)


def test_columns_by_parent_groups_by_table(check):
    rows = [
        _column_row(table='events', name='id', position=1),
        _column_row(table='events', name='ts', type_='DateTime', position=2),
        _column_row(table='other', name='id', position=1),
    ]
    out = check.metadata._columns_by_parent(rows)
    assert {col['name'] for col in out[('default', 'events')]} == {'id', 'ts'}
    assert {col['name'] for col in out[('default', 'other')]} == {'id'}


def test_columns_by_parent_dedupes_identical_replica_rows(check):
    row = _column_row()
    out = check.metadata._columns_by_parent([row, row, row])
    assert len(out[('default', 'events')]) == 1


def test_columns_by_parent_keeps_distinct_replica_variants(check):
    rows = [
        _column_row(name='id', type_='UInt64'),
        _column_row(name='id', type_='Int64'),
    ]
    out = check.metadata._columns_by_parent(rows)
    assert len(out[('default', 'events')]) == 2


def test_columns_by_parent_respects_max_columns(collect_schemas_instance):
    collect_schemas_instance['collect_schemas']['max_columns'] = 2
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    rows = [_column_row(name=f'c{i}', position=i) for i in range(5)]
    out = check.metadata._columns_by_parent(rows)
    assert len(out[('default', 'events')]) == 2


def test_build_payload_routes_views_and_tables(check):
    payload = check.metadata._build_payload(
        tables_rows=[_table_row(name='events'), _view_row(name='events_mv')],
        columns_rows=[_column_row(table='events'), _column_row(table='events_mv', name='id')],
        refresh_rows=[],
    )
    dbs = payload['metadata']['databases']
    assert len(dbs) == 1
    db = dbs[0]
    assert db['name'] == 'default'
    assert [t['name'] for t in db['tables']] == ['events']
    assert [v['name'] for v in db['views']] == ['events_mv']


def test_build_payload_dedupes_replica_rows(check):
    row = _table_row(name='events')
    payload = check.metadata._build_payload(tables_rows=[row, row, row], columns_rows=[], refresh_rows=[])
    assert len(payload['metadata']['databases'][0]['tables']) == 1


def test_build_payload_empty_returns_none(check):
    assert check.metadata._build_payload([], [], []) is None


def test_build_payload_truncates_large_ddl(check):
    huge = 'CREATE TABLE x AS ' + 'B' * (_CREATE_QUERY_MAX_BYTES + 100)
    payload = check.metadata._build_payload([_table_row(create_query=huge)], [], [])
    ddl = payload['metadata']['databases'][0]['tables'][0]['create_query']
    assert ddl.endswith(_CREATE_QUERY_TRUNC_SUFFIX)
    assert len(ddl.encode('utf-8')) <= _CREATE_QUERY_MAX_BYTES


def test_build_payload_view_includes_target_when_present(check):
    create_q = 'CREATE MATERIALIZED VIEW default.mv TO target_db.target_tbl AS SELECT * FROM default.src'
    payload = check.metadata._build_payload(
        tables_rows=[_view_row(name='mv', create_query=create_q, as_select='SELECT * FROM default.src')],
        columns_rows=[],
        refresh_rows=[],
    )
    view = payload['metadata']['databases'][0]['views'][0]
    assert view['target_database'] == 'target_db'
    assert view['target_table'] == 'target_tbl'
    assert view['source_databases'] == ['default']
    assert view['source_tables'] == ['src']


def test_build_payload_view_omits_target_when_absent(check):
    create_q = 'CREATE VIEW default.v AS SELECT 1'
    payload = check.metadata._build_payload(
        tables_rows=[_view_row(name='v', engine='View', create_query=create_q, as_select='SELECT 1')],
        columns_rows=[],
        refresh_rows=[],
    )
    view = payload['metadata']['databases'][0]['views'][0]
    assert 'target_database' not in view
    assert 'target_table' not in view


def test_build_payload_marks_view_refreshable_only_when_refresh_row_present(check):
    payload = check.metadata._build_payload(
        tables_rows=[
            _view_row(name='refreshable_mv'),
            _view_row(
                name='vanilla_view',
                engine='View',
                create_query='CREATE VIEW default.vanilla_view AS SELECT 1',
                as_select='SELECT 1',
            ),
        ],
        columns_rows=[],
        refresh_rows=[_refresh_row(view='refreshable_mv')],
    )
    by_name = {v['name']: v for v in payload['metadata']['databases'][0]['views']}
    assert by_name['refreshable_mv']['is_refreshable'] is True
    assert by_name['vanilla_view']['is_refreshable'] is False


def test_build_payload_columns_attached_to_correct_parent(check):
    payload = check.metadata._build_payload(
        tables_rows=[_table_row(name='events'), _view_row(name='events_mv')],
        columns_rows=[
            _column_row(table='events', name='id'),
            _column_row(table='events_mv', name='count', type_='UInt64'),
        ],
        refresh_rows=[],
    )
    db = payload['metadata']['databases'][0]
    assert [c['name'] for c in db['tables'][0]['columns']] == ['id']
    assert [c['name'] for c in db['views'][0]['columns']] == ['count']


def test_build_payload_top_level_fields(check):
    check.check_id = 'test-collector-id'
    check.metadata._collection_started_at = 1700000000000
    payload = check.metadata._build_payload([_table_row()], [], [])
    assert payload['kind'] == 'clickhouse_databases'
    assert payload['dbms'] == 'clickhouse'
    assert payload['collection_interval'] == 600
    assert payload['database_instance']
    assert payload['collection_started_at'] == 1700000000000
    assert payload['collection_payloads_count'] == 1
    assert payload['collector_id'] == 'test-collector-id'


def test_build_payload_truncates_when_aggregate_exceeds_payload_cap(check):
    check.metadata._log = mock.MagicMock()
    huge_ddl = 'A' * (_CREATE_QUERY_MAX_BYTES - len(_CREATE_QUERY_TRUNC_SUFFIX) - 1)
    row_count = (_PAYLOAD_MAX_BYTES // _CREATE_QUERY_MAX_BYTES) + 50
    rows = [_table_row(name=f'big_{i}', create_query=huge_ddl) for i in range(row_count)]

    payload = check.metadata._build_payload(rows, [], [])

    emitted = sum(len(d['tables']) + len(d['views']) for d in payload['metadata']['databases'])
    assert 0 < emitted < row_count
    check.metadata._log.warning.assert_called_once()
    warning_args = check.metadata._log.warning.call_args.args
    template, max_bytes_arg, dropped_arg = warning_args[0], warning_args[1], warning_args[2]
    assert '%d bytes' in template
    assert max_bytes_arg == _PAYLOAD_MAX_BYTES
    assert dropped_arg == row_count - emitted


def test_collect_view_refreshes_unknown_table_logs_once(check):
    job = check.metadata
    job._log = mock.MagicMock()
    with mock.patch.object(job, '_execute_query', side_effect=Exception('Unknown table system.view_refreshes')):
        assert job._collect_view_refreshes() == []
        assert job._collect_view_refreshes() == []
    assert len(job._log.info.call_args_list) == 1
    assert job._view_refreshes_unsupported_logged is True


def test_collect_view_refreshes_permission_denied_logs_once(check):
    job = check.metadata
    job._log = mock.MagicMock()
    with mock.patch.object(
        job, '_execute_query', side_effect=Exception('Not enough privileges to access system.view_refreshes')
    ):
        assert job._collect_view_refreshes() == []
        assert job._collect_view_refreshes() == []
    assert len(job._log.warning.call_args_list) == 1
    assert job._view_refreshes_permission_logged is True


def test_collect_view_refreshes_unexpected_error_logs_exception(check):
    job = check.metadata
    job._log = mock.MagicMock()
    with mock.patch.object(job, '_execute_query', side_effect=Exception('boom')):
        assert job._collect_view_refreshes() == []
    job._log.exception.assert_called_once()


def test_emit_metrics_table_gauges(check):
    job = check.metadata
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_metrics([_table_row(name='events', total_rows=1000, total_bytes=2048)], [])

    by_name = {n: (v, t) for n, v, t in emitted}
    assert by_name['table.rows'][0] == 1000
    assert by_name['table.bytes'][0] == 2048
    tags = by_name['table.rows'][1]
    assert 'db:default' in tags
    assert 'table:events' in tags


def test_emit_metrics_view_refresh_gauges(check):
    job = check.metadata
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_metrics(
        [],
        [_refresh_row(status='Ok', last_refresh_time=100, next_refresh_time=700, written_rows=5, written_bytes=50)],
    )

    by_name = {n: (v, t) for n, v, t in emitted}
    assert by_name['view.refresh.last_time'][0] == 100
    assert by_name['view.refresh.next_time'][0] == 700
    assert by_name['view.refresh.rows'][0] == 5
    assert by_name['view.refresh.bytes'][0] == 50
    status_tags = by_name['view.refresh.status'][1]
    assert 'status:Ok' in status_tags
    assert 'view:events_mv' in status_tags


def test_emit_metrics_view_refresh_unknown_status(check):
    job = check.metadata
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    job._emit_metrics([], [_refresh_row(status=None)])

    status_tags = next(t for n, _, t in emitted if n == 'view.refresh.status')
    assert 'status:Unknown' in status_tags


def test_emit_metrics_dedupes_duplicate_table_rows(check):
    job = check.metadata
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    row = _table_row(name='events')
    job._emit_metrics([row, row, row], [])

    rows_emissions = [m for m in emitted if m[0] == 'table.rows']
    assert len(rows_emissions) == 1


def test_collect_and_emit_publishes_payload(check):
    job = check.metadata
    table_row = _table_row(name='events')
    view_row = _view_row(name='events_mv')
    column_row = _column_row(table='events')
    refresh_row = _refresh_row(view='events_mv')

    def fake_query(query):
        if 'view_refreshes' in query:
            return [refresh_row]
        if 'system.columns' in query:
            return [column_row]
        return [table_row, view_row]

    emitted_metadata = []
    check.database_monitoring_metadata = lambda raw: emitted_metadata.append(raw)
    check.gauge = lambda *a, **kw: None

    with mock.patch.object(job, '_execute_query', side_effect=fake_query):
        job._collect_and_emit()

    assert len(emitted_metadata) == 1
    payload = json.loads(emitted_metadata[0])
    assert payload['kind'] == 'clickhouse_databases'
    db = payload['metadata']['databases'][0]
    assert any(t['name'] == 'events' for t in db['tables'])
    view = next(v for v in db['views'] if v['name'] == 'events_mv')
    assert view['is_refreshable'] is True


def test_collect_and_emit_skips_when_tables_query_fails(check):
    job = check.metadata
    emitted_metadata = []
    check.database_monitoring_metadata = lambda raw: emitted_metadata.append(raw)
    check.gauge = lambda *a, **kw: None

    with mock.patch.object(job, '_execute_query', side_effect=Exception('connection refused')):
        job._collect_and_emit()

    assert emitted_metadata == []


def test_collect_and_emit_continues_when_columns_query_fails(check):
    job = check.metadata

    def fake_query(query):
        if 'system.tables' in query:
            return [_table_row(name='events')]
        if 'system.columns' in query:
            raise Exception('columns boom')
        return []

    emitted_metadata = []
    check.database_monitoring_metadata = lambda raw: emitted_metadata.append(raw)
    check.gauge = lambda *a, **kw: None

    with mock.patch.object(job, '_execute_query', side_effect=fake_query):
        job._collect_and_emit()

    assert len(emitted_metadata) == 1
    payload = json.loads(emitted_metadata[0])
    table = payload['metadata']['databases'][0]['tables'][0]
    assert table['columns'] == []


def test_collect_and_emit_routes_through_cluster_all_replicas_in_single_endpoint_mode(
    collect_schemas_instance,
):
    collect_schemas_instance['single_endpoint_mode'] = True
    check = ClickhouseCheck('clickhouse', {}, [collect_schemas_instance])
    seen_queries = []

    def fake_query(query):
        seen_queries.append(query)
        return []

    check.database_monitoring_metadata = lambda raw: None
    check.gauge = lambda *a, **kw: None
    with mock.patch.object(check.metadata, '_execute_query', side_effect=fake_query):
        check.metadata._collect_and_emit()

    joined = '\n'.join(seen_queries)
    assert "clusterAllReplicas('default', system.tables)" in joined
    assert "clusterAllReplicas('default', system.columns)" in joined
    assert "clusterAllReplicas('default', system.view_refreshes)" in joined


def test_collect_and_emit_uses_local_system_tables_in_direct_mode(check):
    seen_queries = []

    def fake_query(query):
        seen_queries.append(query)
        return []

    check.database_monitoring_metadata = lambda raw: None
    check.gauge = lambda *a, **kw: None
    with mock.patch.object(check.metadata, '_execute_query', side_effect=fake_query):
        check.metadata._collect_and_emit()

    joined = '\n'.join(seen_queries)
    assert 'clusterAllReplicas' not in joined
    assert 'FROM system.tables' in joined
    assert 'FROM system.columns' in joined
    assert 'FROM system.view_refreshes' in joined
