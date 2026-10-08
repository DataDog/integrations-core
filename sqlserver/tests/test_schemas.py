# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from typing import Callable, Optional

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import STATIC_INFO_MAJOR_VERSION, STATIC_INFO_YEAR
from datadog_checks.sqlserver.queries import INDEX_QUERY_PRE_2017
from datadog_checks.sqlserver.schemas import SQLServerSchemaCollector

from . import common

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

SCHEMA_DATABASE = 'datadog_test_schemas'


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['database'] = SCHEMA_DATABASE
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 0.1
    instance_docker['query_samples'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['collect_resources'] = {'enabled': False, 'run_sync': True}
    instance_docker['collect_settings'] = {'enabled': False, 'run_sync': True}
    instance_docker['collect_schemas'] = {'enabled': True, 'run_sync': True}
    return instance_docker


@pytest.fixture(scope="function")
def integration_check() -> Callable[[dict, Optional[dict]], SQLServer]:
    checks = []

    def _check(instance: dict, init_config: dict = None):
        nonlocal checks
        c = SQLServer(common.CHECK_NAME, init_config or {}, [instance])
        c.static_info_cache[STATIC_INFO_MAJOR_VERSION] = common.SQLSERVER_MAJOR_VERSION
        c.static_info_cache[STATIC_INFO_YEAR] = common.SQLSERVER_YEAR
        checks.append(c)
        return c

    yield _check

    for c in checks:
        c.cancel()


def create_schema_collector(check: SQLServer) -> SQLServerSchemaCollector:
    collector = SQLServerSchemaCollector(check)
    collector._get_databases()
    return collector


def test_get_cursor(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = create_schema_collector(check)

    with collector._get_cursor(SCHEMA_DATABASE) as cursor:
        assert cursor is not None
        schemas = []
        rows = cursor.fetchall_dict()
        for row in rows:
            schemas.append(row['schema_name'])

        assert set(schemas) == {
            'test_schema',
        }


def test_tables(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = create_schema_collector(check)

    with collector._get_cursor(SCHEMA_DATABASE) as cursor:
        assert cursor is not None
        tables = []
        rows = cursor.fetchall_dict()
        for row in rows:
            if row['table_name']:
                tables.append(row['table_name'])

    assert set(tables) == {'cities', 'Restaurants', 'RestaurantReviews', 'landmarks', 'index_coverage', 'key_order'}


def test_columns(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = create_schema_collector(check)

    with collector._get_cursor(SCHEMA_DATABASE) as cursor:
        assert cursor is not None
        # Assert that at least one row has columns
        rows = cursor.fetchall_dict()
        assert any(row['columns'] for row in rows)
        for row in rows:
            if row['columns']:
                columns = json.loads(row['columns'])
                for column in columns:
                    assert column['name'] is not None
                    assert column['data_type'] is not None
            if row['table_name'] == 'cities':
                columns = json.loads(row['columns'])
                assert columns[0]['name'] is not None


def test_indexes(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = create_schema_collector(check)

    with collector._get_cursor(SCHEMA_DATABASE) as cursor:
        assert cursor is not None
        # Assert that at least one row has indexes
        rows = cursor.fetchall_dict()
        assert any(row['indexes'] for row in rows)
        for row in rows:
            if row['indexes']:
                indexes = json.loads(row['indexes'])
                for index in indexes:
                    assert index['name'] is not None
                    assert index['type'] is not None
                    assert index['is_unique'] is not None
                    assert index['is_primary_key'] is not None
                    assert index['is_unique_constraint'] is not None
                    assert index['is_disabled'] is not None
                    assert index['column_names'] is not None
                    assert index['key_columns'] is not None
                    assert index['included_columns'] is not None
            if row['table_name'] == 'cities':
                indexes = json.loads(row['indexes'])
                assert indexes[0]['name'] is not None
            if row['table_name'] == 'index_coverage':
                _assert_include_split({index['name']: index for index in json.loads(row['indexes'])})
            if row['table_name'] == 'key_order':
                _assert_key_order({index['name']: index for index in json.loads(row['indexes'])})


def _assert_include_split(indexes):
    # (c) INCLUDE (a, e) and (c, a) INCLUDE (e) share column_names. The INCLUDE list does not.
    assert indexes['ix_include']['key_columns'] == 'c'
    assert indexes['ix_include']['included_columns'] == 'a,e'
    assert indexes['ix_prefix']['key_columns'] == 'c,a'
    assert indexes['ix_prefix']['included_columns'] == 'e'
    # ix_filtered covers only rows WHERE e IS NOT NULL. Unfiltered indexes have no filter_definition.
    assert indexes['ix_filtered']['filter_definition'] == '([e] IS NOT NULL)'
    assert indexes['ix_include'].get('filter_definition') is None


def _assert_key_order(indexes):
    # PRIMARY KEY CLUSTERED (b, a). key_columns follows key order, not table order.
    assert indexes['pk_key_order']['key_columns'] == 'b,a'
    assert indexes['pk_key_order']['included_columns'] == ''
    # (c DESC, a). The suffix is absent from every other fixture.
    assert indexes['ix_desc']['key_columns'] == 'c DESC,a'
    assert indexes['ix_desc']['included_columns'] == ''


def _legacy_indexes(collector, table_row):
    table_id = str(table_row['table_id'])
    collector._pre_2017_cursor.execute(INDEX_QUERY_PRE_2017.replace("schema_tables.table_id", table_id))
    indexes = {}
    for row in collector._pre_2017_cursor.fetchall_dict():
        lowered = {str(key).lower(): value for key, value in row.items()}
        indexes[lowered['name']] = lowered
    return indexes


def test_collect_schemas(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = SQLServerSchemaCollector(check)

    collector.collect_schemas()


# Force pre-2017 behavior for testing that collections don't crash
# Note that this test assumes the pre-2017 tables are still present
def test_collect_schemas_pre_2017(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    check.static_info_cache[STATIC_INFO_MAJOR_VERSION] = 13
    collector = SQLServerSchemaCollector(check)

    collector.collect_schemas()


def test_indexes_pre_2017(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    check.static_info_cache[STATIC_INFO_MAJOR_VERSION] = 13
    collector = create_schema_collector(check)

    with collector._get_cursor(SCHEMA_DATABASE) as cursor:
        assert collector._is_2016_or_earlier
        rows = {row['table_name']: row for row in cursor.fetchall_dict()}
        _assert_include_split(_legacy_indexes(collector, rows['index_coverage']))
        _assert_key_order(_legacy_indexes(collector, rows['key_order']))
