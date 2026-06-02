# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures.thread import ThreadPoolExecutor
from copy import deepcopy

import clickhouse_connect
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.clickhouse import ClickhouseCheck

from .common import CLICKHOUSE_VERSION

UNSUPPORTED_VERSIONS = {'18', '19', '20', '21.8', '22.7'}
NO_VIEW_REFRESHES_VERSIONS = UNSUPPORTED_VERSIONS | {'23.2', '23.8'}


def _is_supported():
    if CLICKHOUSE_VERSION == 'latest':
        return True
    return CLICKHOUSE_VERSION not in UNSUPPORTED_VERSIONS


def _supports_view_refreshes():
    if CLICKHOUSE_VERSION == 'latest':
        return True
    return CLICKHOUSE_VERSION not in NO_VIEW_REFRESHES_VERSIONS


pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(
        not _is_supported(),
        reason='metadata collection requires DBM support (ClickHouse 21.8+)',
    ),
]


@pytest.fixture
def metadata_instance(instance):
    instance['dbm'] = True
    instance['collect_schemas'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 60,
        'max_tables': 5000,
        'max_columns': 1000,
    }
    instance['query_metrics'] = {'enabled': False}
    instance['query_samples'] = {'enabled': False}
    instance['query_completions'] = {'enabled': False}
    instance['query_errors'] = {'enabled': False}
    instance['parts_and_merges'] = {'enabled': False}
    return instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


def _client(instance_config):
    return clickhouse_connect.get_client(
        host=instance_config['server'],
        port=instance_config['port'],
        username=instance_config['username'],
        password=instance_config['password'],
    )


def _catalog_events(aggregator):
    return [e for e in aggregator.get_event_platform_events('dbm-metadata') if e.get('kind') == 'clickhouse_databases']


def _databases(catalog_events):
    out = []
    for ev in catalog_events:
        out.extend(ev.get('metadata') or [])
    return out


def _merged_database(catalog_events, name):
    """Merge every per-row entry for `name` across events into one dict.

    SchemaCollector emits one DatabaseObject per table/view; the same database
    name appears multiple times across chunks. The backend dedupes on its side;
    tests need to do the same to assert on the full set of tables. Tables and
    views share a single `tables` list; views are identified by engine.
    """
    tables: list[dict] = []
    found = False
    for db in _databases(catalog_events):
        if db.get('name') != name:
            continue
        found = True
        tables.extend(db.get('tables') or [])
    if not found:
        return None
    return {'name': name, 'tables': tables}


_find_database = _merged_database


def test_metadata_payload_emitted(aggregator, metadata_instance, dd_run_check):
    client = _client(metadata_instance)
    table = 'dd_md_payload_test'
    try:
        client.command(f'DROP TABLE IF EXISTS default.{table}')
        client.command(f'CREATE TABLE default.{table} (id UInt64, ts DateTime) ENGINE = MergeTree ORDER BY id')

        check = ClickhouseCheck('clickhouse', {}, [metadata_instance])
        check.check_id = 'test-collector-id'
        dd_run_check(check)

        events = _catalog_events(aggregator)
        assert events, 'Expected at least one clickhouse_databases event on dbm-metadata'

        ev = events[-1]
        assert ev['dbms'] == 'clickhouse'
        assert ev['database_instance']
        assert ev['agent_version']
        assert ev['collection_started_at'] > 0
        assert ev['collection_payloads_count'] == 1
        assert ev['collector_id'] == 'test-collector-id'
        assert ev['timestamp'] > 0

        db = _find_database(events, 'default')
        assert db is not None, "Expected the 'default' database to be present in payload"
        assert any(t['name'] == table for t in db['tables']), (
            f'Expected table {table} in catalog payload; got: {[t["name"] for t in db["tables"]]}'
        )
    finally:
        client.command(f'DROP TABLE IF EXISTS default.{table} SYNC')


def test_metadata_columns_collected(aggregator, metadata_instance, dd_run_check):
    client = _client(metadata_instance)
    table = 'dd_md_columns_test'
    try:
        client.command(f'DROP TABLE IF EXISTS default.{table}')
        client.command(
            f'CREATE TABLE default.{table} ('
            'id UInt64, '
            'event_name String, '
            'created_at DateTime DEFAULT now()'
            ') ENGINE = MergeTree ORDER BY id'
        )

        check = ClickhouseCheck('clickhouse', {}, [metadata_instance])
        dd_run_check(check)

        events = _catalog_events(aggregator)
        db = _find_database(events, 'default')
        assert db is not None

        target = next((t for t in db['tables'] if t['name'] == table), None)
        assert target is not None, f'Expected {table} in tables, got {[t["name"] for t in db["tables"]]}'

        col_names = [c['name'] for c in target['columns']]
        assert col_names == ['id', 'event_name', 'created_at'], col_names

        types = {c['name']: c['type'] for c in target['columns']}
        assert types['id'] == 'UInt64'
        assert types['event_name'] == 'String'

        defaults = {c['name']: c['default'] for c in target['columns']}
        assert defaults['created_at'], 'DEFAULT expression should round-trip into payload'
    finally:
        client.command(f'DROP TABLE IF EXISTS default.{table} SYNC')


def test_metadata_materialized_view_with_target(aggregator, metadata_instance, dd_run_check):
    client = _client(metadata_instance)
    src = 'dd_md_mv_src'
    target = 'dd_md_mv_target'
    mv = 'dd_md_mv_view'
    try:
        for obj in (mv, target, src):
            client.command(f'DROP TABLE IF EXISTS default.{obj}')

        client.command(f'CREATE TABLE default.{src} (id UInt64, val UInt64) ENGINE = MergeTree ORDER BY id')
        client.command(f'CREATE TABLE default.{target} (id UInt64, total UInt64) ENGINE = MergeTree ORDER BY id')
        client.command(
            f'CREATE MATERIALIZED VIEW default.{mv} TO default.{target} AS SELECT id, val AS total FROM default.{src}'
        )

        check = ClickhouseCheck('clickhouse', {}, [metadata_instance])
        dd_run_check(check)

        events = _catalog_events(aggregator)
        db = _find_database(events, 'default')
        assert db is not None

        view = next((t for t in db['tables'] if t['name'] == mv), None)
        assert view is not None, f'Expected view {mv} in payload; got: {[t["name"] for t in db["tables"]]}'
        assert view['engine'] == 'MaterializedView'
        assert view['create_query']
        assert f'TO default.{target}' in view['create_query']
        assert f'FROM default.{src}' in view['create_query']
    finally:
        for obj in (mv, target, src):
            client.command(f'DROP TABLE IF EXISTS default.{obj} SYNC')


def test_metadata_skips_system_databases(aggregator, metadata_instance, dd_run_check):
    check = ClickhouseCheck('clickhouse', {}, [metadata_instance])
    dd_run_check(check)

    db_names = {db['name'] for db in _databases(_catalog_events(aggregator))}
    forbidden = {'system', 'INFORMATION_SCHEMA', 'information_schema'}
    leaked = db_names & forbidden
    assert not leaked, f'System databases leaked into payload: {leaked}'


def test_metadata_disabled_emits_no_payload(aggregator, instance, dd_run_check):
    instance_config = deepcopy(instance)
    instance_config['dbm'] = True
    instance_config['collect_schemas'] = {'enabled': False, 'collection_interval': 60}

    check = ClickhouseCheck('clickhouse', {}, [instance_config])
    assert check.metadata is None
    dd_run_check(check)

    assert _catalog_events(aggregator) == [], (
        'Expected no clickhouse_databases payload when collect_schemas is disabled'
    )


def test_metadata_exclude_tables_filter(aggregator, metadata_instance, dd_run_check):
    client = _client(metadata_instance)
    table_keep = 'dd_md_filter_keep'
    table_drop = 'dd_md_filter_drop'
    try:
        for t in (table_keep, table_drop):
            client.command(f'DROP TABLE IF EXISTS default.{t}')
            client.command(f'CREATE TABLE default.{t} (id UInt64) ENGINE = MergeTree ORDER BY id')

        instance = deepcopy(metadata_instance)
        instance['collect_schemas']['exclude_tables'] = [f'^{table_drop}$']

        check = ClickhouseCheck('clickhouse', {}, [instance])
        dd_run_check(check)

        db = _find_database(_catalog_events(aggregator), 'default')
        assert db is not None
        table_names = {t['name'] for t in db['tables']}
        assert table_keep in table_names
        assert table_drop not in table_names
    finally:
        for t in (table_keep, table_drop):
            client.command(f'DROP TABLE IF EXISTS default.{t} SYNC')


def test_metadata_include_tables_filter(aggregator, metadata_instance, dd_run_check):
    client = _client(metadata_instance)
    table_included = 'dd_md_include_target'
    table_other = 'dd_md_include_other'
    try:
        for t in (table_included, table_other):
            client.command(f'DROP TABLE IF EXISTS default.{t}')
            client.command(f'CREATE TABLE default.{t} (id UInt64) ENGINE = MergeTree ORDER BY id')

        instance = deepcopy(metadata_instance)
        instance['collect_schemas']['include_tables'] = [f'^{table_included}$']

        check = ClickhouseCheck('clickhouse', {}, [instance])
        dd_run_check(check)

        db = _find_database(_catalog_events(aggregator), 'default')
        assert db is not None
        table_names = {t['name'] for t in db['tables']}
        assert table_included in table_names
        assert table_other not in table_names
    finally:
        for t in (table_included, table_other):
            client.command(f'DROP TABLE IF EXISTS default.{t} SYNC')


@pytest.mark.skipif(
    not _supports_view_refreshes(),
    reason='system.view_refreshes requires ClickHouse 24.3+',
)
def test_metadata_refreshable_view_status_populated(aggregator, metadata_instance, dd_run_check):
    client = _client(metadata_instance)
    src = 'dd_md_refresh_src'
    target = 'dd_md_refresh_target'
    mv = 'dd_md_refreshable_mv'
    try:
        for obj in (mv, target, src):
            client.command(f'DROP TABLE IF EXISTS default.{obj}')

        client.command(f'CREATE TABLE default.{src} (id UInt64, val UInt64) ENGINE = MergeTree ORDER BY id')
        client.command(f'CREATE TABLE default.{target} (id UInt64, total UInt64) ENGINE = MergeTree ORDER BY id')
        client.command(
            f'CREATE MATERIALIZED VIEW default.{mv} REFRESH EVERY 1 HOUR '
            f'TO default.{target} AS SELECT id, val AS total FROM default.{src}',
            settings={'allow_experimental_refreshable_materialized_view': 1},
        )

        check = ClickhouseCheck('clickhouse', {}, [metadata_instance])
        check.check_id = 'test-collector-id'
        dd_run_check(check)

        events = _catalog_events(aggregator)
        db = _find_database(events, 'default')
        assert db is not None

        view = next((t for t in db['tables'] if t['name'] == mv), None)
        assert view is not None, f'Expected refreshable view {mv} in payload'
        assert view['is_refreshable'] is True
    finally:
        for obj in (mv, target, src):
            client.command(f'DROP TABLE IF EXISTS default.{obj} SYNC')
