# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.mysql import MySql

from . import common
import pdb

@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['query_samples'] = {'enabled': False}
    instance_complex['query_metrics'] = {'enabled': False}
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return instance_complex


#@pytest.mark.integration
#@pytest.mark.usefixtures('dd_environment')
#def test_collect_mysql_settings(aggregator, dbm_instance, dd_run_check):
    # test to make sure we continue to support the old key
#    pdb.set_trace()
#    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
#    dd_run_check(mysql_check)
#    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
#    event = next((e for e in dbm_metadata if e['kind'] == 'mysql_variables'), None)
#    assert event is not None
#    assert event['host'] == "stubbed.hostname"
#    assert event['dbms'] == "mysql"
#    assert len(event["metadata"]) > 0

@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_schemas(aggregator, dd_run_check, dbm_instance):
    databases_to_find = ['datadog_test_schemas', 'datadog_test_schemas_second']
    exp_datadog_test = {
        'id': 'normalized_value',
        'name': 'datadog_test_schemas_second',
        "collation": "SQL_Latin1_General_CP1_CI_AS",
        'owner': 'dbo',
        'schemas': [
            {
                'name': 'dbo',
                'id': 'normalized_value',
                'owner_name': 'dbo',
                'tables': [
                    {
                        'id': 'normalized_value',
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
        'id': 'normalized_value',
        'name': 'datadog_test_schemas',
        "collation": "SQL_Latin1_General_CP1_CI_AS",
        'owner': 'dbo',
        'schemas': [
            {
                'name': 'test_schema',
                'id': 'normalized_value',
                'owner_name': 'dbo',
                'tables': [
                    {
                        'id': 'normalized_value',
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
                                'column_names': 'id,population',
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
                        'id': 'normalized_value',
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
                        'id': 'normalized_value',
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
                        'id': 'normalized_value',
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
                                'column_names': 'District,RestaurantName',
                            }
                        ],
                    },
                ],
            }
        ],
    }

    #if running_on_windows_ci():
    #    exp_datadog_test['owner'] = 'None'
    #    exp_datadog_test_schemas['owner'] = 'None'

    expected_data_for_db = {
        'datadog_test_schemas_second': exp_datadog_test,
        'datadog_test_schemas': exp_datadog_test_schemas,
    }

    #dbm_instance['database_autodiscovery'] = True
    #dbm_instance['autodiscovery_include'] = ['datadog_test_schemas', 'datadog_test_schemas_second']
    dbm_instance['schemas_collection'] = {"enabled": True}

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    dd_run_check(mysql_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    actual_payloads = {}
    pdb.set_trace()
    for schema_event in (e for e in dbm_metadata if e['kind'] == 'mysql_databases'):
        pdb.set_trace()
        assert schema_event.get("timestamp") is not None
        assert schema_event["host"] == "stubbed.hostname"
        assert schema_event["agent_version"] == "0.0.0"
        assert schema_event["dbms"] == "mysql"
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

        # id's are env dependant
       # normalize_ids(actual_payload)

        # index columns may be in any order
        #normalize_indexes_columns(actual_payload)

        difference = DeepDiff(actual_payload, expected_data_for_db[db_name], ignore_order=True)

        diff_keys = list(difference.keys())
        # schema data also collects certain builtin default schemas which are ignored in the test
        if len(diff_keys) > 0 and diff_keys != ['iterable_item_removed']:
            raise AssertionError(Exception("found the following diffs: " + str(difference)))