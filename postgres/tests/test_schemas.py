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
