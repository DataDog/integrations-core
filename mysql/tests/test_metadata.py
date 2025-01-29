# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from os import environ

import pytest
from packaging.version import parse as parse_version

from datadog_checks.mysql import MySql

from . import common
from .common import MYSQL_VERSION_PARSED
from .utils import deep_compare


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
    actual_payload["default_character_set_name"] = "normalized_value"
    actual_payload["default_collation_name"] = "normalized_value"
    for table in actual_payload['tables']:
        table['create_time'] = "normalized_value"
        if 'foreign_keys' in table:
            for f_key in table['foreign_keys']:
                f_key["referenced_column_names"] = sort_names_split_by_coma(f_key["referenced_column_names"])
        if 'columns' in table:
            for column in table['columns']:
                if column['column_type'] == 'int':
                    # 11 is omitted in certain versions
                    # if its not 11 i.e. not default we keep it
                    column['column_type'] = 'int(11)'
        if 'partitions' in table:
            for partition in table['partitions']:
                if partition["partition_expression"] is not None:
                    partition["partition_expression"] = (
                        partition["partition_expression"].replace("`", "").lower().strip()
                    )
                if partition["subpartitions"] is not None:
                    for subpartition in partition["subpartitions"]:
                        if subpartition["subpartition_expression"] is not None:
                            subpartition["subpartition_expression"] = (
                                subpartition["subpartition_expression"].replace("`", "").lower().strip()
                            )


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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collect_schemas(aggregator, dd_run_check, dbm_instance):
    databases_to_find = ['datadog_test_schemas', 'datadog_test_schemas_second']

    is_maria_db = environ.get('MYSQL_FLAVOR') == 'mariadb'
    exp_datadog_test_schemas = {
        "name": "datadog_test_schemas",
        "default_character_set_name": "normalized_value",
        "default_collation_name": "normalized_value",
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
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 1,
                        "column_key": "MUL",
                        "extra": "",
                    },
                    {
                        "name": "District",
                        "column_type": "varchar(255)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 2,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "Review",
                        "column_type": "text",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 3,
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
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "RestaurantName",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": True,
                            },
                            {
                                "name": "District",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": True,
                            },
                        ],
                        "non_unique": True,
                        "expression": None,
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
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 1,
                        "column_key": "MUL",
                        "extra": "",
                    },
                    {
                        "name": "District",
                        "column_type": "varchar(100)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 2,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "Cuisine",
                        "column_type": "varchar(100)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 3,
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "indexes": [
                    {
                        "name": "UC_RestaurantNameDistrict",
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "RestaurantName",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": True,
                            },
                            {
                                "name": "District",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": True,
                            },
                        ],
                        "non_unique": False,
                        "expression": None,
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
                        "ordinal_position": 1,
                        "column_key": "PRI",
                        "extra": "",
                    },
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 2,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "population",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": False,
                        "ordinal_position": 3,
                        "column_key": "MUL",
                        "extra": "",
                    },
                ],
                "indexes": [
                    {
                        "name": "PRIMARY",
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "id",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": False,
                            }
                        ],
                        "non_unique": False,
                        "expression": None,
                    },
                    {
                        "name": "single_column_index",
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "population",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": False,
                            }
                        ],
                        "non_unique": True,
                        "expression": None,
                    },
                    {
                        "name": "two_columns_index",
                        "index_type": "BTREE",
                        "cardinality": 0,
                        "columns": [
                            {
                                "name": "id",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": False,
                            },
                            {
                                "name": "name",
                                "sub_part": 3,
                                "collation": (
                                    'D'
                                    if (
                                        (MYSQL_VERSION_PARSED >= parse_version('8.0') and not is_maria_db)
                                        or (MYSQL_VERSION_PARSED >= parse_version('10.8') and is_maria_db)
                                    )
                                    else 'A'
                                ),
                                "packed": None,
                                "nullable": True,
                            },
                        ],
                        "non_unique": True,
                        "expression": None,
                    },
                    *(
                        [
                            {
                                "name": "functional_key_part_index",
                                "index_type": "BTREE",
                                "cardinality": 0,
                                "columns": [],
                                "non_unique": True,
                                "expression": "(`population` + 1)",
                            }
                        ]
                        if MYSQL_VERSION_PARSED >= parse_version('8.0.13') and not is_maria_db
                        else []
                    ),
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
                        "ordinal_position": 1,
                        "column_key": "PRI",
                        "extra": "",
                    },
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 2,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "population",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": False,
                        "ordinal_position": 3,
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "partitions": [
                    {
                        "name": "p0",
                        "subpartitions": [],
                        "partition_ordinal_position": 1,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "100",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                    {
                        "name": "p1",
                        "subpartitions": [],
                        "partition_ordinal_position": 2,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "200",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                    {
                        "name": "p2",
                        "subpartitions": [],
                        "partition_ordinal_position": 3,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "300",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                    {
                        "name": "p3",
                        "subpartitions": [],
                        "partition_ordinal_position": 4,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "MAXVALUE",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                ],
                "indexes": [
                    {
                        "name": "PRIMARY",
                        "cardinality": 4 if is_maria_db else 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "id",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": False,
                            }
                        ],
                        "non_unique": False,
                        "expression": None,
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
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 1,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "city_id",
                        "column_type": "int(11)",
                        "default": "0",
                        "nullable": True,
                        "ordinal_position": 2,
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
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "city_id",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": True,
                            },
                        ],
                        "non_unique": True,
                        "expression": None,
                    }
                ],
            },
        ],
    }
    exp_datadog_test_schemas_second = {
        "name": "datadog_test_schemas_second",
        "default_character_set_name": "normalized_value",
        "default_collation_name": "normalized_value",
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
                        "ordinal_position": 1,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "name",
                        "column_type": "varchar(255)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 2,
                        "column_key": "UNI",
                        "extra": "",
                    },
                ],
                "indexes": [
                    {
                        "name": "thingsindex",
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "name",
                                "sub_part": None,
                                "collation": "A",
                                "packed": None,
                                "nullable": True,
                            },
                        ],
                        "non_unique": False,
                        "expression": None,
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
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 1,
                        "column_key": "",
                        "extra": "",
                    },
                    {
                        "name": "purchased",
                        "column_type": "date",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 2,
                        "column_key": "",
                        "extra": "",
                    },
                ],
                "partitions": [
                    {
                        "name": "p0",
                        "subpartitions": [
                            {
                                "name": "p0sp0",
                                "subpartition_ordinal_position": 1,
                                "subpartition_method": "HASH",
                                "subpartition_expression": "to_days(purchased)",
                                "table_rows": 0,
                                "data_length": 16384,
                            },
                            {
                                "name": "p0sp1",
                                "subpartition_ordinal_position": 2,
                                "subpartition_method": "HASH",
                                "subpartition_expression": "to_days(purchased)",
                                "table_rows": 0,
                                "data_length": 16384,
                            },
                        ],
                        "partition_ordinal_position": 1,
                        "partition_method": "RANGE",
                        "partition_expression": "year(purchased)",
                        "partition_description": "1990",
                        "table_rows": 0,
                        "data_length": 32768,
                    },
                    {
                        "name": "p1",
                        "subpartitions": [
                            {
                                "name": "p1sp0",
                                "subpartition_ordinal_position": 1,
                                "subpartition_method": "HASH",
                                "subpartition_expression": "to_days(purchased)",
                                "table_rows": 0,
                                "data_length": 16384,
                            },
                            {
                                "name": "p1sp1",
                                "subpartition_ordinal_position": 2,
                                "subpartition_method": "HASH",
                                "subpartition_expression": "to_days(purchased)",
                                "table_rows": 0,
                                "data_length": 16384,
                            },
                        ],
                        "partition_ordinal_position": 2,
                        "partition_method": "RANGE",
                        "partition_expression": "year(purchased)",
                        "partition_description": "2000",
                        "table_rows": 0,
                        "data_length": 32768,
                    },
                    {
                        "name": "p2",
                        "subpartitions": [
                            {
                                "name": "p2sp0",
                                "subpartition_ordinal_position": 1,
                                "subpartition_method": "HASH",
                                "subpartition_expression": "to_days(purchased)",
                                "table_rows": 0,
                                "data_length": 16384,
                            },
                            {
                                "name": "p2sp1",
                                "subpartition_ordinal_position": 2,
                                "subpartition_method": "HASH",
                                "subpartition_expression": "to_days(purchased)",
                                "table_rows": 0,
                                "data_length": 16384,
                            },
                        ],
                        "partition_ordinal_position": 3,
                        "partition_method": "RANGE",
                        "partition_expression": "year(purchased)",
                        "partition_description": "MAXVALUE",
                        "table_rows": 0,
                        "data_length": 32768,
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
            'database_hostname:stubbed.hostname',
            'dbms_flavor:{}'.format(common.MYSQL_FLAVOR.lower()),
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

    assert len(actual_payloads) == len(expected_data_for_db)

    for db_name, actual_payload in actual_payloads.items():
        normalize_values(actual_payload)
        assert db_name in databases_to_find
        assert deep_compare(expected_data_for_db[db_name], actual_payload)


@pytest.mark.integration
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
