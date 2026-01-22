# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Callable, Optional

import pytest
from packaging.version import parse as parse_version

from datadog_checks.mysql import MySql
from datadog_checks.mysql.schemas import MySqlSchemaCollector
from datadog_checks.mysql.version_utils import MySQLVersion

from . import common
from .common import MYSQL_FLAVOR, MYSQL_VERSION_PARSED

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
        c.is_mariadb = MYSQL_FLAVOR.lower() == 'mariadb'
        c.version = MySQLVersion(version=str(MYSQL_VERSION_PARSED), flavor=MYSQL_FLAVOR, build='')
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

        expected_schemas = {'datadog_test_schemas', 'datadog', 'datadog_test_schemas_second', 'testdb'}
        if MYSQL_FLAVOR.lower() == 'mariadb' and MYSQL_VERSION_PARSED <= parse_version('10.6.0'):
            expected_schemas.add('test')
        assert set(schemas) == expected_schemas


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
        'cities',
        'RestaurantReviews',
        'cities_partitioned',
        'users',
        'Restaurants',
        'ϑings',
        'landmarks',
        'ts',
    }


def test_collect_schemas(dbm_instance, integration_check):
    check = integration_check(dbm_instance)
    collector = MySqlSchemaCollector(check)

    collector.collect_schemas()
