# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable, Optional
import pytest

from datadog_checks.mysql.schemas import MySqlSchemaCollector
from datadog_checks.mysql import MySql
from . import common

# from datadog_checks.postgres.version_utils import VersionUtils

# from .common import POSTGRES_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(instance_basic):
    instance_basic['dbm'] = True
    instance_basic['min_collection_interval'] = 0.1
    instance_basic['query_samples'] = {'enabled': False}
    instance_basic['query_activity'] = {'enabled': False}
    instance_basic['query_metrics'] = {'enabled': False}
    instance_basic['collect_resources'] = {'enabled': False, 'run_sync': True}
    instance_basic['collect_settings'] = {'enabled': False, 'run_sync': True}
    instance_basic['collect_schemas'] = {'enabled': True, 'run_sync': True}
    return instance_basic

@pytest.fixture(scope="function")
def integration_check() -> Callable[[dict, Optional[dict]], MySql]:
    checks = []

    def _check(instance: dict, init_config: dict = None):
        nonlocal checks
        c = MySql(common.CHECK_NAME, init_config or {}, [instance])
        checks.append(c)
        return c

    yield _check

    for c in checks:
        c.cancel()


def test_get_cursor(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = MySqlSchemaCollector(check)

    with collector._get_cursor('datadog_test') as cursor:
        assert cursor is not None
        schemas = []
        for row in cursor:
            schemas.append(row['schema_name'])

        assert set(schemas) == {'datadog', 'hstore', 'public', 'public2'}


def test_tables(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = MySqlSchemaCollector(check)

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
    collector = MySqlSchemaCollector(check)

    collector.collect_schemas()
