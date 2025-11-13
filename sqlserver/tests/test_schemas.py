# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Callable, Optional

import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.schemas import SQLServerSchemaCollector

from . import common

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.fixture
def dbm_instance(instance_docker):
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
        checks.append(c)
        return c

    yield _check

    for c in checks:
        c.cancel()


def test_get_cursor(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = SQLServerSchemaCollector(check)

    with collector._get_cursor('datadog_test_schemas') as cursor:
        assert cursor is not None
        schemas = []
        rows = cursor.fetchall_dict()
        for row in rows:
            schemas.append(row['schema_name'])

        assert set(schemas) == {
            'db_accessadmin',
            'db_denydatawriter',
            'test_schema',
            'db_datawriter',
            'db_ddladmin',
            'db_datareader',
            'db_securityadmin',
            'db_denydatareader',
            'db_backupoperator',
            'dbo',
            'guest',
            'db_owner',
        }


def test_tables(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = SQLServerSchemaCollector(check)

    with collector._get_cursor('datadog_test_schemas') as cursor:
        assert cursor is not None
        tables = []
        rows = cursor.fetchall_dict()
        for row in rows:
            if row['table_name']:
                tables.append(row['table_name'])

    assert set(tables) == {'cities', 'Restaurants', 'RestaurantReviews', 'landmarks'}


def test_columns(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = SQLServerSchemaCollector(check)

    with collector._get_cursor('datadog_test_schemas') as cursor:
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
    collector = SQLServerSchemaCollector(check)

    with collector._get_cursor('datadog_test_schemas') as cursor:
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
            if row['table_name'] == 'cities':
                indexes = json.loads(row['indexes'])
                assert indexes[0]['name'] is not None


def test_collect_schemas(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = SQLServerSchemaCollector(check)

    collector.collect_schemas()
