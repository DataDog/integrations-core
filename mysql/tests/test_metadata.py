# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import re
import time
from unittest import mock

import pymysql
import pytest
from packaging.version import parse as parse_version

from datadog_checks.mysql import MySql
from datadog_checks.mysql.databases_data import DatabasesData, SubmitData

from . import common
from .common import MYSQL_FLAVOR, MYSQL_REPLICATION, MYSQL_VERSION_PARSED


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
    actual_payload["tables"].sort(key=lambda x: x["name"])
    for table in actual_payload['tables']:
        table['create_time'] = "normalized_value"
        if 'columns' in table:
            table['columns'].sort(key=lambda x: x['name'])
        if 'indexes' in table:
            table['indexes'].sort(key=lambda x: x['name'])
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
                if "subpartitions" in partition and partition["subpartitions"]:
                    for subpartition in partition["subpartitions"]:
                        if subpartition["subpartition_expression"] is not None:
                            subpartition["subpartition_expression"] = (
                                subpartition["subpartition_expression"].replace("`", "").lower().strip()
                            )
    if 'views' in actual_payload:
        actual_payload['views'].sort(key=lambda x: x['name'])
        for view in actual_payload['views']:
            if view['definition'] is not None:
                view['definition'] = "normalized_value"
            view['columns'].sort(key=lambda x: x['name'])
            for column in view['columns']:
                if column['column_type'] == 'int':
                    column['column_type'] = 'int(11)'


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
    assert event['database_instance'] == "stubbed.hostname"
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

    is_maria_db = MYSQL_FLAVOR.lower() == 'mariadb'
    is_percona = MYSQL_FLAVOR.lower() == 'percona'
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
                        "update_action": "NO ACTION",
                        "delete_action": "CASCADE",
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
                                "collation": "A",
                                "nullable": True,
                            },
                            {
                                "name": "District",
                                "collation": "A",
                                "nullable": True,
                            },
                        ],
                        "non_unique": True,
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
                                "collation": "A",
                                "nullable": True,
                            },
                            {
                                "name": "District",
                                "collation": "A",
                                "nullable": True,
                            },
                        ],
                        "non_unique": False,
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
                                "collation": "A",
                                "nullable": False,
                            }
                        ],
                        "non_unique": False,
                    },
                    {
                        "name": "single_column_index",
                        "cardinality": 0,
                        "index_type": "BTREE",
                        "columns": [
                            {
                                "name": "population",
                                "collation": "A",
                                "nullable": False,
                            }
                        ],
                        "non_unique": True,
                    },
                    {
                        "name": "two_columns_index",
                        "index_type": "BTREE",
                        "cardinality": 0,
                        "columns": [
                            {
                                "name": "id",
                                "collation": "A",
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
                                "nullable": True,
                            },
                        ],
                        "non_unique": True,
                    },
                ]
                + (
                    [
                        {
                            "name": "functional_key_part_index",
                            "index_type": "BTREE",
                            "cardinality": 0,
                            "non_unique": True,
                            "expression": "(`population` + 1)",
                        }
                    ]
                    if MYSQL_VERSION_PARSED >= parse_version('8.0.13') and not is_maria_db and not is_percona
                    else []
                ),
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
                        "partition_ordinal_position": 1,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "100",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                    {
                        "name": "p1",
                        "partition_ordinal_position": 2,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "200",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                    {
                        "name": "p2",
                        "partition_ordinal_position": 3,
                        "partition_method": "RANGE",
                        "partition_expression": "id",
                        "partition_description": "300",
                        "table_rows": 0,
                        "data_length": 16384,
                    },
                    {
                        "name": "p3",
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
                                "collation": "A",
                                "nullable": False,
                            }
                        ],
                        "non_unique": False,
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
                        "update_action": "RESTRICT",
                        "delete_action": "SET NULL",
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
                                "collation": "A",
                                "nullable": True,
                            },
                        ],
                        "non_unique": True,
                    }
                ],
            },
        ],
        "views": [
            {
                "name": "restaurant_names",
                "definition": "normalized_value",
                "columns": [
                    {
                        "name": "RestaurantName",
                        "column_type": "varchar(255)",
                        "default": "NULL" if is_maria_db else None,
                        "nullable": True,
                        "ordinal_position": 1,
                        "column_key": "",
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
                ],
            }
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
                                "collation": "A",
                                "nullable": True,
                            },
                        ],
                        "non_unique": False,
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
    table_fragment_found = False
    view_fragment_found = False

    expected_tags = (
        'database_hostname:stubbed.hostname',
        'database_instance:stubbed.hostname',
        'dbms_flavor:{}'.format(common.MYSQL_FLAVOR.lower()),
        'dd.internal.resource:database_instance:stubbed.hostname',
        'port:13306',
        'tag1:value1',
        'tag2:value2',
    )
    if MYSQL_FLAVOR.lower() in ('mysql', 'percona'):
        expected_tags += ("server_uuid:{}".format(mysql_check.server_uuid),)
        if MYSQL_REPLICATION == 'classic':
            expected_tags += ('cluster_uuid:{}'.format(mysql_check.cluster_uuid), 'replication_role:primary')

    for schema_event in (e for e in dbm_metadata if e['kind'] == 'mysql_databases'):
        assert schema_event.get("timestamp") is not None
        assert schema_event["host"] == "stubbed.hostname"
        assert schema_event["agent_version"] == "0.0.0"
        assert schema_event["dbms"] == "mysql"
        assert schema_event.get("collection_interval") is not None
        assert schema_event.get("dbms_version") is not None
        assert schema_event.get("flavor") in ("MariaDB", "MySQL", "Percona")
        assert sorted(schema_event["tags"]) == sorted(expected_tags)
        database_metadata = schema_event['metadata']
        assert len(database_metadata) == 1
        db_name = database_metadata[0]['name']
        if db_name not in databases_to_find:
            continue

        database_fragment = database_metadata[0]
        database_payload = actual_payloads.setdefault(
            db_name, {key: value for key, value in database_fragment.items() if key not in ('tables', 'views')}
        )
        for object_type in ('tables', 'views'):
            if object_type in database_fragment:
                database_payload.setdefault(object_type, []).extend(database_fragment[object_type])

        if db_name == 'datadog_test_schemas' and 'tables' in database_fragment:
            assert 'views' not in database_fragment
            table_fragment_found = True
        if db_name == 'datadog_test_schemas' and 'views' in database_fragment:
            assert 'tables' not in database_fragment
            view_fragment_found = True

    assert len(actual_payloads) == len(expected_data_for_db)
    assert table_fragment_found
    assert view_fragment_found

    for db_name, actual_payload in actual_payloads.items():
        normalize_values(actual_payload)
        normalize_values(expected_data_for_db[db_name])
        assert db_name in databases_to_find
        assert expected_data_for_db[db_name] == actual_payload


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


@pytest.mark.unit
def test_schemas_collection_config(dbm_instance):
    dbm_instance['schemas_collection'] = {"enabled": True, "max_execution_time": 0}
    check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert check._config.schemas_config == {"enabled": True, "max_execution_time": 0}

    dbm_instance.pop('schemas_collection')
    dbm_instance['collect_schemas'] = {"enabled": True, "max_execution_time": 0}
    check = MySql(common.CHECK_NAME, {}, instances=[dbm_instance])
    assert check._config.schemas_config == {"enabled": True, "max_execution_time": 0}


@pytest.mark.unit
def test_submit_data_counts_table_and_view_columns_together():
    submitted_data = []
    submitter = SubmitData(submitted_data.append, {"kind": "mysql_databases"}, mock.MagicMock())
    submitter.store_db_infos([{"name": "test_db"}])

    submitter.store("test_db", [{"name": "table"}], 2)
    submitter.store_views("test_db", [{"name": "view", "definition": None, "columns": []}], 3)

    assert submitter.columns_since_last_submit() == 5

    submitter.submit()
    metadata = json.loads(submitted_data[0])["metadata"][0]
    assert metadata["tables"] == [{"name": "table"}]
    assert metadata["views"] == [{"name": "view", "definition": None, "columns": []}]


@pytest.mark.unit
def test_submit_data_sends_table_and_view_fragments_independently():
    submitted_data = []
    submitter = SubmitData(submitted_data.append, {"kind": "mysql_databases"}, mock.MagicMock())
    submitter.store_db_infos([{"name": "test_db"}])
    column = {
        "name": "id",
        "column_type": "int",
        "default": None,
        "nullable": False,
        "ordinal_position": 1,
        "column_key": "",
        "extra": "",
    }

    submitter.store("test_db", [{"name": "table"}], 1)
    submitter.submit()
    submitter.store_views("test_db", [{"name": "view", "definition": None, "columns": [column]}], 1)
    submitter.submit()

    table_metadata = json.loads(submitted_data[0])["metadata"][0]
    view_metadata = json.loads(submitted_data[1])["metadata"][0]
    assert table_metadata == {"name": "test_db", "tables": [{"name": "table"}]}
    assert view_metadata == {
        "name": "test_db",
        "views": [{"name": "view", "definition": None, "columns": [column]}],
    }
    assert set(view_metadata["views"][0]["columns"][0]) == {
        "name",
        "column_type",
        "default",
        "nullable",
        "ordinal_position",
        "column_key",
        "extra",
    }


@pytest.mark.unit
def test_view_columns_split_payloads_at_the_column_limit():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = DatabasesData({}, check, check._config)
    submitted_data = []
    databases_data.TABLES_CHUNK_SIZE = 1
    databases_data.MAX_COLUMNS_PER_EVENT = 1
    databases_data._data_submitter = SubmitData(submitted_data.append, {"kind": "mysql_databases"}, mock.MagicMock())
    databases_data._data_submitter.store_db_infos([{"name": "test_db"}])
    views = [{"name": "view_{}".format(i), "definition": None, "columns": []} for i in range(3)]

    with (
        mock.patch.object(databases_data, '_get_tables', return_value=[]),
        mock.patch.object(databases_data, '_get_views', return_value=views),
        mock.patch.object(databases_data, '_get_views_data', side_effect=lambda chunk, *_: (1, chunk)),
    ):
        databases_data._fetch_database_data(mock.MagicMock(), time.time(), "test_db")

    payloads = [json.loads(event)["metadata"][0] for event in submitted_data]
    assert [[view["name"] for view in payload["views"]] for payload in payloads] == [
        ["view_0", "view_1"],
        ["view_2"],
    ]


@pytest.mark.unit
def test_view_permission_failure_preserves_table_metadata():
    check = MySql(common.CHECK_NAME, {}, instances=[{'server': 'localhost', 'user': 'datadog'}])
    databases_data = DatabasesData({}, check, check._config)
    submitted_data = []
    databases_data._log = mock.MagicMock()
    databases_data._data_submitter = SubmitData(submitted_data.append, {"kind": "mysql_databases"}, databases_data._log)
    databases_data._data_submitter.store_db_infos([{"name": "test_db"}])

    with (
        mock.patch.object(databases_data, '_get_tables', return_value=[{"name": "table"}]),
        mock.patch.object(databases_data, '_get_tables_data', return_value=(1, [{"name": "table", "columns": []}])),
        mock.patch.object(
            databases_data,
            '_get_views',
            side_effect=pymysql.DatabaseError(
                pymysql.constants.ER.TABLEACCESS_DENIED_ERROR, "SHOW VIEW command denied"
            ),
        ),
    ):
        databases_data._fetch_database_data(mock.MagicMock(), time.time(), "test_db")

    metadata = json.loads(submitted_data[0])["metadata"][0]
    assert metadata == {"name": "test_db", "tables": [{"name": "table", "columns": []}]}
    databases_data._log.warning.assert_called_once()
    assert "SHOW VIEW privilege" in databases_data._log.warning.call_args.args[0]
