# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import unicode_literals

import logging
from copy import copy

import pytest
from deepdiff import DeepDiff

from datadog_checks.sqlserver import SQLServer

from .common import CHECK_NAME

try:
    import pyodbc
except ImportError:
    pyodbc = None


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    # set a very small collection interval so the tests go fast
    instance_docker['collect_settings'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 0.1,
    }
    return copy(instance_docker)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    "expected_columns,available_columns",
    [
        [
            ["name", "value"],
            ["name", "value"],
        ],
        [
            ["name", "value", "some_missing_column"],
            ["name", "value"],
        ],
    ],
)
def test_get_available_settings_columns(dbm_instance, expected_columns, available_columns):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-metadata-"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            result_available_columns = check.sql_metadata._get_available_settings_columns(cursor, expected_columns)
            assert result_available_columns == available_columns


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_get_settings_query_cached(dbm_instance, caplog):
    caplog.set_level(logging.DEBUG)
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    check.initialize_connection()
    _conn_key_prefix = "dbm-metadata"
    with check.connection.open_managed_default_connection(key_prefix=_conn_key_prefix):
        with check.connection.get_managed_cursor(key_prefix=_conn_key_prefix) as cursor:
            for _ in range(3):
                query = check.sql_metadata._get_settings_query_cached(cursor)
                assert query, "query should be non-empty"
    times_columns_loaded = 0
    for r in caplog.records:
        if r.message.startswith("found available sys.configurations columns"):
            times_columns_loaded += 1
    assert times_columns_loaded == 1, "columns should have been loaded only once"


def test_sqlserver_collect_settings(aggregator, dd_run_check, dbm_instance):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)
    check.initialize_connection()
    check.check(dbm_instance)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'sqlserver_configs'), None)
    assert event is not None
    assert event['dbms'] == "sqlserver"
    assert event['kind'] == "sqlserver_configs"
    assert len(event["metadata"]) > 0


def test_collect_schemas(aggregator, dd_run_check, dbm_instance):

    databases_to_find = ['datadog_test_schemas', 'datadog_test']
    exp_datadog_test = {
        'id': '6',
        'name': 'datadog_test',
        "collation":"SQL_Latin1_General_CP1_CI_AS",
        'owner': 'dbo',
        'schemas': [
            {
                'name': 'dbo',
                'id': '1',
                'owner_name': 'dbo',
                'tables': [
                    {
                        'id': '885578193',
                        'name': 'ϑings',
                        'columns': [
                            {
                                'name': 'id',
                                'data_type': 'int',
                                'default': '((0))',
                                'nullable': True,
                                'ordinal_position': '1',
                            },
                            {
                                'name': 'name',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '2',
                            },
                        ],
                        'partitions': {'partition_count': 1},
                        'indexes': [
                            {
                                'name': 'thingsindex',
                                'type': 1,
                                'is_unique': False,
                                'is_primary_key': False,
                                'is_unique_constraint': False,
                                'is_disabled': False,
                                'column_names': 'name',
                            }
                        ],
                    }
                ],
            }
        ],
    }
    exp_datadog_test_schemas = {
        'id': '5',
        'name': 'datadog_test_schemas',
        "collation":"SQL_Latin1_General_CP1_CI_AS",
        'owner': 'dbo',
        'schemas': [
            {
                'name': 'test_schema',
                'id': '5',
                'owner_name': 'dbo',
                'tables': [
                    {
                        'id': '885578193',
                        'name': 'cities',
                        'columns': [
                            {
                                'name': 'id',
                                'data_type': 'int',
                                'default': '((0))',
                                'nullable': False,
                                'ordinal_position': '1',
                            },
                            {
                                'name': 'name',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '2',
                            },
                            {
                                'name': 'population',
                                'data_type': 'int',
                                'default': '((0))',
                                'nullable': False,
                                'ordinal_position': '3',
                            },
                        ],
                        'partitions': {'partition_count': 12},
                        'foreign_keys': [
                            {
                                'foreign_key_name': 'FK_CityId',
                                'referencing_table': 'landmarks',
                                'referencing_column': 'city_id',
                                'referenced_table': 'cities',
                                'referenced_column': 'id',
                            }
                        ],
                        'indexes': [
                            {
                                'name': 'PK_Cities',
                                'type': 1,
                                'is_unique': True,
                                'is_primary_key': True,
                                'is_unique_constraint': False,
                                'is_disabled': False,
                                'column_names': 'id',
                            },
                            {
                                'name': 'single_column_index',
                                'type': 2,
                                'is_unique': False,
                                'is_primary_key': False,
                                'is_unique_constraint': False,
                                'is_disabled': False,
                                'column_names': 'population,id',
                            },
                            {
                                'name': 'two_columns_index',
                                'type': 2,
                                'is_unique': False,
                                'is_primary_key': False,
                                'is_unique_constraint': False,
                                'is_disabled': False,
                                'column_names': 'id,name',
                            },
                        ],
                    },
                    {
                        'id': '949578421',
                        'name': 'landmarks',
                        'columns': [
                            {
                                'name': 'name',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '1',
                            },
                            {
                                'name': 'city_id',
                                'data_type': 'int',
                                'default': '((0))',
                                'nullable': True,
                                'ordinal_position': '2',
                            },
                        ],
                        'partitions': {'partition_count': 1},
                    },
                    {
                        'id': '1029578706',
                        'name': 'RestaurantReviews',
                        'columns': [
                            {
                                'name': 'RestaurantName',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '1',
                            },
                            {
                                'name': 'District',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '2',
                            },
                            {
                                'name': 'Review',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '3',
                            },
                        ],
                        'partitions': {'partition_count': 1},
                    },
                    {
                        'id': '997578592',
                        'name': 'Restaurants',
                        'columns': [
                            {
                                'name': 'RestaurantName',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '1',
                            },
                            {
                                'name': 'District',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '2',
                            },
                            {
                                'name': 'Cuisine',
                                'data_type': 'varchar',
                                'default': 'None',
                                'nullable': True,
                                'ordinal_position': '3',
                            },
                        ],
                        'partitions': {'partition_count': 2},
                        'foreign_keys': [
                            {
                                'foreign_key_name': 'FK_RestaurantNameDistrict',
                                'referencing_table': 'RestaurantReviews',
                                'referencing_column': 'RestaurantName,District',
                                'referenced_table': 'Restaurants',
                                'referenced_column': 'RestaurantName,District',
                            }
                        ],
                        'indexes': [
                            {
                                'name': 'UC_RestaurantNameDistrict',
                                'type': 2,
                                'is_unique': True,
                                'is_primary_key': False,
                                'is_unique_constraint': True,
                                'is_disabled': False,
                                'column_names': 'RestaurantName,District',
                            }
                        ],
                    },
                ],
            }
        ],
    }
    expected_data_for_db = {'datadog_test': exp_datadog_test, 'datadog_test_schemas': exp_datadog_test_schemas}

    dbm_instance['database_autodiscovery'] = True
    dbm_instance['autodiscovery_include'] = ['datadog_test_schemas', 'datadog_test']

    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    dd_run_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    actual_payloads = {}

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'sqlserver_databases'):
        assert schema_event.get("timestamp") is not None
        assert schema_event["host"] == "stubbed.hostname" 
        assert schema_event["agent_version"] == "0.0.0"
        assert schema_event["dbms"] == "sqlserver"
        assert schema_event.get("collection_interval") is not None
        assert schema_event.get("dbms_version") is not None

        database_metadata = schema_event['metadata']
        assert len(database_metadata) == 1
        db_name = database_metadata[0]['name']

        if db_name in actual_payloads:
            actual_payloads[db_name]['schemas'] = actual_payloads[db_name]['schemas'] + database_metadata[0]['schemas']
        else:
            actual_payloads[db_name] = database_metadata[0]
    assert len(actual_payloads) == len(expected_data_for_db)

    for db_name, actual_payload in actual_payloads.items():

        assert db_name in databases_to_find

        difference = DeepDiff(actual_payload, expected_data_for_db[db_name], ignore_order=True)

        diff_keys = list(difference.keys())
        # schema data also collects certain built default schemas which are ignored in the test
        if len(diff_keys) > 0 and diff_keys != ['iterable_item_removed']:
            raise AssertionError(Exception("found the following diffs: " + str(difference)))