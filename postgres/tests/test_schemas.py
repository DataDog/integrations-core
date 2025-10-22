# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.schemas import PostgresSchemaCollector
from datadog_checks.postgres.version_utils import VersionUtils

from .common import POSTGRES_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.1
    pg_instance['query_samples'] = {'enabled': False}
    pg_instance['query_activity'] = {'enabled': False}
    pg_instance['query_metrics'] = {'enabled': False}
    pg_instance['collect_resources'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_settings'] = {'enabled': False, 'run_sync': True}
    pg_instance['collect_schemas'] = {'enabled': True, 'run_sync': True}
    return pg_instance


def test_get_databases(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = PostgresSchemaCollector(check)

    databases = collector._get_databases()
    datbase_names = [database['name'] for database in databases]
    assert 'postgres' in datbase_names
    assert 'dogs' in datbase_names
    assert 'dogs_3' in datbase_names
    assert 'nope' not in datbase_names


def test_databases_filters(dbm_instance, integration_check):
    dbm_instance['collect_schemas']['exclude_databases'] = ['^dogs$', 'dogs_[345]']
    check = integration_check(dbm_instance)
    collector = PostgresSchemaCollector(check)

    databases = collector._get_databases()
    datbase_names = [database['name'] for database in databases]
    assert 'postgres' in datbase_names
    assert 'dogs' not in datbase_names
    assert 'dogs_3' not in datbase_names
    assert 'dogs_9' in datbase_names
    assert 'nope' not in datbase_names


def test_get_cursor(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    check.version = POSTGRES_VERSION
    collector = PostgresSchemaCollector(check)

    with collector._get_cursor('datadog_test') as cursor:
        assert cursor is not None
        schemas = []
        for row in cursor:
            schemas.append(row['schema_name'])

        assert set(schemas) == {'datadog', 'hstore', 'public', 'public2'}


def test_schemas_filters(dbm_instance, integration_check):
    dbm_instance['collect_schemas']['exclude_schemas'] = ['public', 'rdsadmin_test']
    check = integration_check(dbm_instance)
    check.version = POSTGRES_VERSION
    collector = PostgresSchemaCollector(check)

    with collector._get_cursor('datadog_test') as cursor:
        assert cursor is not None
        schemas = []
        for row in cursor:
            schemas.append(row['schema_name'])

        assert set(schemas) == {'datadog', 'hstore'}


def test_tables(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    check.version = POSTGRES_VERSION
    collector = PostgresSchemaCollector(check)

    with collector._get_cursor('datadog_test') as cursor:
        assert cursor is not None
        tables = []
        for row in cursor:
            if row['table_name']:
                tables.append(row['table_name'])

    assert set(tables) == {
        'persons',
        'personsdup1',
        'personsdup2',
        'personsdup3',
        'personsdup4',
        'personsdup5',
        'personsdup6',
        'personsdup7',
        'personsdup8',
        'personsdup9',
        'personsdup10',
        'personsdup11',
        'personsdup12',
        'personsdup13',
        'persons_indexed',
        'pgtable',
        'pg_newtable',
        'cities',
        'sample_foreign_d73a8c',
    }


# def test_columns(dbm_instance, integration_check):
#     check = integration_check(dbm_instance)
#     check.version = POSTGRES_VERSION
#     collector = PostgresSchemaCollector(check)

#     with collector._get_cursor('datadog_test') as cursor:
#         assert cursor is not None
#         # Assert that at least one row has columns
#         assert any(row['columns'] for row in cursor)
#         for row in cursor:
#             if row['columns']:
#                 for column in row['columns']:
#                     assert column['name'] is not None
#                     assert column['data_type'] is not None
#             if row['table_name'] == 'cities':
#                 assert row['columns']
#                 assert row['columns'][0]['name']


# def test_indexes(dbm_instance, integration_check):
#     check = integration_check(dbm_instance)
#     check.version = POSTGRES_VERSION
#     collector = PostgresSchemaCollector(check)

#     with collector._get_cursor('datadog_test') as cursor:
#         assert cursor is not None
#         # Assert that at least one row has indexes
#         assert any(row['indexes'] for row in cursor)
#         for row in cursor:
#             if row['indexes']:
#                 for index in row['indexes']:
#                     assert index['name'] is not None
#                     assert index['definition'] is not None
#             if row['table_name'] == 'cities':
#                 assert row['indexes']
#                 assert row['indexes'][0]['name']


def test_collect_schemas(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    check.version = VersionUtils().parse_version(POSTGRES_VERSION)
    collector = PostgresSchemaCollector(check)

    collector.collect_schemas()
