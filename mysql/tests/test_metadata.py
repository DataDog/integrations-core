# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

import pytest
from deepdiff import DeepDiff

from datadog_checks.mysql import MySql

from . import common


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['query_samples'] = {'enabled': False}
    instance_complex['query_metrics'] = {'enabled': False}
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    return instance_complex


def sort_names_split_by_coma(names):
    names_arr = names.split(',')
    sorted_columns = sorted(names_arr)
    return ','.join(sorted_columns)


def normalize_values(actual_payload):
    for table in actual_payload['tables']:
        table['create_time'] = "normalized_value"
        if 'foreign_keys' in table:
            for f_key in table['foreign_keys']:
                f_key["referenced_column_names"] = sort_names_split_by_coma(f_key["referenced_column_names"])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_mysql_settings(aggregator, dbm_instance, dd_run_check):
    # test to make sure we continue to support the old key
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    dd_run_check(mysql_check)
    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    event = next((e for e in dbm_metadata if e['kind'] == 'mysql_variables'), None)
    assert event is not None
    assert event['host'] == "stubbed.hostname"
    assert event['dbms'] == "mysql"
    assert len(event["metadata"]) > 0


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metadata_collection_interval_and_enabled(dbm_instance):

    dbm_instance['schemas_collection'] = {"enabled": True, "collection_interval": 101}
    dbm_instance['collect_settings'] = {"enabled": False, "collection_interval": 100}

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert mysql_check._mysql_metadata.enabled
    assert mysql_check._mysql_metadata.collection_interval == 101
    dbm_instance['schemas_collection'] = {"enabled": False, "collection_interval": 101}
    dbm_instance['collect_settings'] = {"enabled": True, "collection_interval": 102}

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert mysql_check._mysql_metadata.enabled
    assert mysql_check._mysql_metadata.collection_interval == 102

    dbm_instance['schemas_collection'] = {"enabled": True, "collection_interval": 101}
    dbm_instance['collect_settings'] = {"enabled": True, "collection_interval": 102}

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert mysql_check._mysql_metadata.enabled
    assert mysql_check._mysql_metadata.collection_interval == 101
    dbm_instance['schemas_collection'] = {"enabled": False}
    dbm_instance['collect_settings'] = {"enabled": False}
    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert not mysql_check._mysql_metadata.enabled

import pdb
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_schemas(aggregator, dd_run_check, dbm_instance):
    databases_to_find = ['datadog_test_schemas', 'datadog_test_schemas_second']

    exp_datadog_test_schemas = {
        "name": "datadog_test_schemas",
        "default_character_set_name": "latin1",
        "default_collation_name": "latin1_swedish_ci",
        "tables": [
            {
                "name": "RestaurantReviews",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "RestaurantName",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "1",
                        "column_key": "MUL",
                        "extra": "",
                    },
                    {
                        "name": "District",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "Review",
                        "column_type": "text",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "3",
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "foreign_keys": [
                    {
                        "name": "FK_RestaurantNameDistrict",
                        "constraint_schema": "datadog_test_schemas",
                        "table_name": "RestaurantReviews",
                        "column_names": "RestaurantName,District",
                        "referenced_table_schema": "datadog_test_schemas",
                        "referenced_table_name": "Restaurants",
                        "referenced_column_names": "District,RestaurantName",
                    }
                ],
                "indexes": [
                    {
                        "name": "FK_RestaurantNameDistrict",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1,2",
                        "columns": "RestaurantName,District",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "true,true",
                        "non_uniques": "1,1",
                    }
                ],
            },
            {
                "name": "Restaurants",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "RestaurantName",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "1",
                        "column_key": "MUL",
                        "extra": "",
                    },
                    {
                        "name": "District",
                        "column_type": "varchar(100)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "Cuisine",
                        "column_type": "varchar(100)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "3",
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "indexes": [
                    {
                        "name": "UC_RestaurantNameDistrict",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1,2",
                        "columns": "RestaurantName,District",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "true,true",
                        "non_uniques": "0,0",
                    }
                ],
            },
            {
                "name": "cities",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "id",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": False,
                        "ordinal_position": "1",
                        "column_key": "PRI",
                        "extra": "",
                    },
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "population",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": False,
                        "ordinal_position": "3",
                        "column_key": "MUL",
                        "extra": "",
                    },
                ],
                "indexes": [
                    {
                        "name": "PRIMARY",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1",
                        "columns": "id",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "false",
                        "non_uniques": "0",
                    },
                    {
                        "name": "single_column_index",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1",
                        "columns": "population",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "false",
                        "non_uniques": "1",
                    },
                    {
                        "name": "two_columns_index",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1,2",
                        "columns": "id,name",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "false,true",
                        "non_uniques": "1,1",
                    },
                ],
            },
            {
                "name": "cities_partitioned",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "id",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": False,
                        "ordinal_position": "1",
                        "column_key": "PRI",
                        "extra": "",
                    },
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "population",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": False,
                        "ordinal_position": "3",
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "partitions": [
                    {
                        "name": "p0",
                        "subpartition_name": "None",
                        "partition_ordinal_position": "1",
                        "subpartition_ordinal_position": "None",
                        "partition_method": "RANGE",
                        "subpartition_method": "None",
                        "partition_expression": "id",
                        "subpartition_expression": "None",
                        "partition_description": "100",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p1",
                        "subpartition_name": "None",
                        "partition_ordinal_position": "2",
                        "subpartition_ordinal_position": "None",
                        "partition_method": "RANGE",
                        "subpartition_method": "None",
                        "partition_expression": "id",
                        "subpartition_expression": "None",
                        "partition_description": "200",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p2",
                        "subpartition_name": "None",
                        "partition_ordinal_position": "3",
                        "subpartition_ordinal_position": "None",
                        "partition_method": "RANGE",
                        "subpartition_method": "None",
                        "partition_expression": "id",
                        "subpartition_expression": "None",
                        "partition_description": "300",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p3",
                        "subpartition_name": "None",
                        "partition_ordinal_position": "4",
                        "subpartition_ordinal_position": "None",
                        "partition_method": "RANGE",
                        "subpartition_method": "None",
                        "partition_expression": "id",
                        "subpartition_expression": "None",
                        "partition_description": "MAXVALUE",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                ],
                "indexes": [
                    {
                        "name": "PRIMARY",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1",
                        "columns": "id",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "false",
                        "non_uniques": "0",
                    }
                ],
            },
            {
                "name": "landmarks",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "1",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "city_id",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "MUL",
                        "extra": "",
                    },
                ],
                "foreign_keys": [
                    {
                        "name": "FK_CityId",
                        "constraint_schema": "datadog_test_schemas",
                        "table_name": "landmarks",
                        "column_names": "city_id",
                        "referenced_table_schema": "datadog_test_schemas",
                        "referenced_table_name": "cities",
                        "referenced_column_names": "id",
                    }
                ],
                "indexes": [
                    {
                        "name": "FK_CityId",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1",
                        "columns": "city_id",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "true",
                        "non_uniques": "1",
                    }
                ],
            },
        ],
    }
    exp_datadog_test_schemas_second = {
        "name": "datadog_test_schemas_second",
        "default_character_set_name": "latin1",
        "default_collation_name": "latin1_swedish_ci",
        "tables": [
            {
                "name": "ϑings",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "id",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": True,
                        "ordinal_position": "1",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "UNI",
                        "extra": "",
                    },
                ],
                "indexes": [
                    {
                        "name": "thingsindex",
                        "collation": "A",
                        "index_type": "BTREE",
                        "seq_in_index": "1",
                        "columns": "name",
                        "sub_parts": "None",
                        "packed": "None",
                        "nullables": "true",
                        "non_uniques": "0",
                    }
                ],
            },
            {
                "name": "ts",
                "engine": "InnoDB",
                "row_format": "Dynamic",
                "create_time": "normalized_value",
                "columns": [
                    {
                        "name": "id",
                        "column_type": "int(11)",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "1",
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "purchased",
                        "column_type": "date",
                        "default": "None",
                        "nullable": True,
                        "ordinal_position": "2",
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "partitions": [
                    {
                        "name": "p0",
                        "subpartition_name": "p0sp0",
                        "partition_ordinal_position": "1",
                        "subpartition_ordinal_position": "1",
                        "partition_method": "RANGE",
                        "subpartition_method": "HASH",
                        "partition_expression": " YEAR(purchased)",
                        "subpartition_expression": " TO_DAYS(purchased)",
                        "partition_description": "1990",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p0",
                        "subpartition_name": "p0sp1",
                        "partition_ordinal_position": "1",
                        "subpartition_ordinal_position": "2",
                        "partition_method": "RANGE",
                        "subpartition_method": "HASH",
                        "partition_expression": " YEAR(purchased)",
                        "subpartition_expression": " TO_DAYS(purchased)",
                        "partition_description": "1990",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p1",
                        "subpartition_name": "p1sp0",
                        "partition_ordinal_position": "2",
                        "subpartition_ordinal_position": "1",
                        "partition_method": "RANGE",
                        "subpartition_method": "HASH",
                        "partition_expression": " YEAR(purchased)",
                        "subpartition_expression": " TO_DAYS(purchased)",
                        "partition_description": "2000",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p1",
                        "subpartition_name": "p1sp1",
                        "partition_ordinal_position": "2",
                        "subpartition_ordinal_position": "2",
                        "partition_method": "RANGE",
                        "subpartition_method": "HASH",
                        "partition_expression": " YEAR(purchased)",
                        "subpartition_expression": " TO_DAYS(purchased)",
                        "partition_description": "2000",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p2",
                        "subpartition_name": "p2sp0",
                        "partition_ordinal_position": "3",
                        "subpartition_ordinal_position": "1",
                        "partition_method": "RANGE",
                        "subpartition_method": "HASH",
                        "partition_expression": " YEAR(purchased)",
                        "subpartition_expression": " TO_DAYS(purchased)",
                        "partition_description": "MAXVALUE",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                    {
                        "name": "p2",
                        "subpartition_name": "p2sp1",
                        "partition_ordinal_position": "3",
                        "subpartition_ordinal_position": "2",
                        "partition_method": "RANGE",
                        "subpartition_method": "HASH",
                        "partition_expression": " YEAR(purchased)",
                        "subpartition_expression": " TO_DAYS(purchased)",
                        "partition_description": "MAXVALUE",
                        "table_rows": "0",
                        "data_length": "16384",
                        "max_data_length": "None",
                        "index_length": "0",
                        "data_free": "0",
                        "partition_comment": "",
                        "tablespace_name": "None",
                    },
                ],
            },
        ],
    }

    expected_data_for_db = {
        'datadog_test_schemas': exp_datadog_test_schemas,
        'datadog_test_schemas_second': exp_datadog_test_schemas_second,
    }

    dbm_instance['schemas_collection'] = {"enabled": True}

    mysql_check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    dd_run_check(mysql_check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")

    actual_payloads = {}

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'mysql_databases'):
        assert schema_event.get("timestamp") is not None
        assert schema_event["host"] == "stubbed.hostname"
        assert schema_event["agent_version"] == "0.0.0"
        assert schema_event["dbms"] == "mysql"
        assert schema_event.get("collection_interval") is not None
        assert schema_event.get("dbms_version") is not None
        assert (schema_event.get("flavor") == "MariaDB") or (schema_event.get("flavor") == "MySQL")
        assert sorted(schema_event["tags"]) == [
            'dd.internal.resource:database_instance:stubbed.hostname',
            'port:13306',
            'tag1:value1',
            'tag2:value2',
        ]
        database_metadata = schema_event['metadata']
        assert len(database_metadata) == 1
        db_name = database_metadata[0]['name']
        if db_name not in databases_to_find:
            continue

        if db_name in actual_payloads:
            actual_payloads[db_name]['schemas'] = actual_payloads[db_name]['schemas'] + database_metadata[0]['schemas']
        else:
            actual_payloads[db_name] = database_metadata[0]
    pdb.set_trace()
    assert len(actual_payloads) == len(expected_data_for_db)

    for db_name, actual_payload in actual_payloads.items():

        normalize_values(actual_payload)

        assert db_name in databases_to_find

        difference = DeepDiff(expected_data_for_db[db_name], actual_payload, ignore_order=True)

        if difference:
            raise AssertionError(Exception("found the following diffs: " + str(difference)))


def test_schemas_collection_truncated(aggregator, dd_run_check, dbm_instance):

    dbm_instance['dbm'] = True
    dbm_instance['schemas_collection'] = {"enabled": True, "max_execution_time": 0}
    expected_pattern = r"^Truncated after fetching \d+ columns, elapsed time is \d+(\.\d+)?s, database is .*"
    check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    dd_run_check(check)

    dbm_metadata = aggregator.get_event_platform_events("dbm-metadata")
    found = False
    for schema_event in (e for e in dbm_metadata if e['kind'] == 'mysql_databases'):
        if "collection_errors" in schema_event:
            if schema_event["collection_errors"][0]["error_type"] == "truncated" and re.fullmatch(
                expected_pattern, schema_event["collection_errors"][0]["message"]
            ):
                found = True
    assert found
