# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postgres.schemas import PostgresSchemaCollector

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
    assert 'postgres' in databases
    assert 'dogs' in databases
    assert 'dogs_23' in databases
    assert 'nope' not in databases


def test_databases_filters(dbm_instance, integration_check):
    dbm_instance['collect_schemas']['exclude_databases'] = ['^dogs$', 'dogs_2(\\d)+']
    check = integration_check(dbm_instance)
    collector = PostgresSchemaCollector(check)

    databases = collector._get_databases()
    assert 'postgres' in databases
    assert 'dogs' not in databases
    assert 'dogs_23' not in databases
    assert 'dogs_34' in databases
    assert 'nope' not in databases


@pytest.mark.parametrize("version", ["9", "10"])
def test_get_cursor(dbm_instance, integration_check, version):
    check = integration_check(dbm_instance)
    check.version = version
    collector = PostgresSchemaCollector(check)

    with collector._get_cursor('datadog_test') as cursor:
        assert cursor is not None
        schemas = []
        for row in cursor:
            schemas.append(row['schema_name'])

        assert set(schemas) == {'datadog', 'hstore', 'public', 'public2', 'rdsadmin_test'}


@pytest.mark.parametrize("version", ["9", "10"])
def test_schemas_filters(dbm_instance, integration_check, version):
    dbm_instance['collect_schemas']['exclude_schemas'] = ['public', 'rdsadmin_test']
    check = integration_check(dbm_instance)
    check.version = version
    collector = PostgresSchemaCollector(check)

    with collector._get_cursor('datadog_test') as cursor:
        assert cursor is not None
        schemas = []
        for row in cursor:
            schemas.append(row['schema_name'])

        assert set(schemas) == {'datadog', 'hstore'}


@pytest.mark.parametrize("version", ["9", "10"])
def test_tables(dbm_instance, integration_check, version):
    check = integration_check(dbm_instance)
    check.version = version
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
        'rds_admin_misc',
        'sample_foreign_d73a8c',
    }
