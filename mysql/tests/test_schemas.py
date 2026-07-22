# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import json
from unittest import mock

import pytest

from datadog_checks.mysql.schemas import (
    STRATEGY_CHUNKED,
    STRATEGY_SINGLE_QUERY,
    MySqlSchemaCollector,
    MySqlSchemaCollectorConfig,
    group_indexes,
    group_partitions,
    normalize_columns,
    normalize_foreign_keys,
    supports_json_collection,
)
from datadog_checks.mysql.version_utils import MySQLVersion

pytestmark = pytest.mark.unit


def _make_collector(strategy):
    check = mock.MagicMock()
    check.log = mock.MagicMock()
    metadata = mock.MagicMock()
    config = MySqlSchemaCollectorConfig({"collection_strategy": strategy})
    return MySqlSchemaCollector(check, metadata, config)


def test_normalize_columns_matches_legacy_transforms():
    rows = [
        {
            "name": "population",
            "column_type": "int",
            "default": 0,
            "nullable": "NO",
            "ordinal_position": 3,
            "column_key": "MUL",
            "extra": "",
        },
        {
            "name": "id",
            "column_type": "int",
            "default": None,
            "nullable": "YES",
            "ordinal_position": 1,
            "column_key": "PRI",
            "extra": "",
        },
    ]
    columns = normalize_columns(rows)
    # sorted by ordinal_position
    assert [c["name"] for c in columns] == ["id", "population"]
    assert columns[0]["nullable"] is True
    assert columns[0]["default"] is None
    assert columns[1]["nullable"] is False
    # default is stringified when present
    assert columns[1]["default"] == "0"


def test_group_indexes_groups_key_parts_and_functional_expression():
    rows = [
        {
            "name": "two_columns_index",
            "collation": "A",
            "cardinality": None,
            "index_type": "BTREE",
            "seq_in_index": 2,
            "column_name": "name",
            "sub_part": 3,
            "packed": None,
            "nullable": "YES",
            "non_unique": 1,
            "expression": None,
        },
        {
            "name": "two_columns_index",
            "collation": "A",
            "cardinality": None,
            "index_type": "BTREE",
            "seq_in_index": 1,
            "column_name": "id",
            "sub_part": None,
            "packed": None,
            "nullable": "NO",
            "non_unique": 1,
            "expression": None,
        },
        {
            "name": "functional_key_part_index",
            "collation": None,
            "cardinality": 5,
            "index_type": "BTREE",
            "seq_in_index": 1,
            "column_name": None,
            "sub_part": None,
            "packed": None,
            "nullable": "",
            "non_unique": 1,
            "expression": "(`population` + 1)",
        },
    ]
    indexes = {idx["name"]: idx for idx in group_indexes(rows)}

    two_col = indexes["two_columns_index"]
    # cardinality defaults to 0 when NULL; non_unique coerced to bool
    assert two_col["cardinality"] == 0
    assert two_col["non_unique"] is True
    # key parts ordered by seq_in_index
    assert [c["name"] for c in two_col["columns"]] == ["id", "name"]
    assert two_col["columns"][1]["sub_part"] == 3
    assert "columns" not in indexes["functional_key_part_index"]
    assert indexes["functional_key_part_index"]["expression"] == "(`population` + 1)"


def test_group_partitions_sums_subpartition_stats():
    rows = [
        {
            "name": "p0",
            "subpartition_name": "p0sp0",
            "partition_ordinal_position": 1,
            "subpartition_ordinal_position": 1,
            "partition_method": "RANGE",
            "subpartition_method": "HASH",
            "partition_expression": "year(purchased)",
            "subpartition_expression": "TO_DAYS(purchased)",
            "partition_description": "1990",
            "table_rows": 0,
            "data_length": 16384,
        },
        {
            "name": "p0",
            "subpartition_name": "p0sp1",
            "partition_ordinal_position": 1,
            "subpartition_ordinal_position": 2,
            "partition_method": "RANGE",
            "subpartition_method": "HASH",
            "partition_expression": "year(purchased)",
            "subpartition_expression": "TO_DAYS(purchased)",
            "partition_description": "1990",
            "table_rows": 0,
            "data_length": 16384,
        },
    ]
    partitions = group_partitions(rows)
    assert len(partitions) == 1
    p0 = partitions[0]
    # partition data_length is the sum of its subpartitions
    assert p0["data_length"] == 32768
    assert len(p0["subpartitions"]) == 2
    # expressions are stripped and lowercased
    assert p0["subpartitions"][0]["subpartition_expression"] == "to_days(purchased)"


def test_normalize_foreign_keys_passthrough_keeps_table_name():
    rows = [
        {
            "name": "FK_CityId",
            "constraint_schema": "db",
            "table_name": "landmarks",
            "column_names": "city_id",
            "referenced_table_schema": "db",
            "referenced_table_name": "cities",
            "referenced_column_names": "id",
            "update_action": "RESTRICT",
            "delete_action": "SET NULL",
        }
    ]
    assert normalize_foreign_keys(rows) == rows


@pytest.mark.parametrize(
    "is_mariadb,version,expected",
    [
        (False, "5.7.22", True),
        (False, "5.7.21", False),
        (False, "8.0.35", True),
        (True, "10.5.0", True),
        (True, "10.4.30", False),
        (True, "11.4.2", True),
    ],
)
def test_supports_json_collection(is_mariadb, version, expected):
    v = MySQLVersion(version, "MariaDB" if is_mariadb else "MySQL", "unspecified")
    assert supports_json_collection(v, is_mariadb) is expected


def test_supports_json_collection_none_version():
    assert supports_json_collection(None, False) is False


def _single_query_row():
    return {
        "name": "cities",
        "engine": "InnoDB",
        "row_format": "Dynamic",
        "create_time": datetime.datetime(2025, 1, 2, 3, 4, 5),
        "columns_json": json.dumps(
            [
                {
                    "name": "id",
                    "column_type": "int",
                    "default": None,
                    "nullable": "NO",
                    "ordinal_position": 1,
                    "column_key": "PRI",
                    "extra": "",
                }
            ]
        ),
        "indexes_json": json.dumps(
            [
                {
                    "name": "PRIMARY",
                    "collation": "A",
                    "cardinality": 0,
                    "index_type": "BTREE",
                    "seq_in_index": 1,
                    "column_name": "id",
                    "sub_part": None,
                    "packed": None,
                    "nullable": "NO",
                    "non_unique": 0,
                    "expression": None,
                }
            ]
        ),
        "foreign_keys_json": None,
        "partitions_json": None,
    }


def test_map_row_single_query_shapes_payload_and_serializes_datetime():
    collector = _make_collector(STRATEGY_SINGLE_QUERY)
    obj = collector._map_row({"name": "mydb", "default_collation_name": "utf8"}, _single_query_row())

    assert obj["name"] == "mydb"
    assert obj["default_collation_name"] == "utf8"
    assert len(obj["tables"]) == 1
    table = obj["tables"][0]
    assert table["name"] == "cities"
    # datetime create_time is converted to isoformat so the base collector can json.dumps it
    assert table["create_time"] == "2025-01-02T03:04:05"
    assert table["columns"][0]["name"] == "id"
    assert table["indexes"][0]["name"] == "PRIMARY"
    # empty detail keys are omitted
    assert "foreign_keys" not in table
    assert "partitions" not in table


def test_map_row_chunked_matches_single_query():
    single = _make_collector(STRATEGY_SINGLE_QUERY)
    chunked = _make_collector(STRATEGY_CHUNKED)

    single_row = _single_query_row()
    chunked_row = {
        "name": single_row["name"],
        "engine": single_row["engine"],
        "row_format": single_row["row_format"],
        "create_time": single_row["create_time"],
        "_columns": json.loads(single_row["columns_json"]),
        "_indexes": json.loads(single_row["indexes_json"]),
        "_foreign_keys": [],
        "_partitions": [],
    }

    single_table = single._map_row({"name": "mydb"}, single_row)["tables"][0]
    chunked_table = chunked._map_row({"name": "mydb"}, chunked_row)["tables"][0]
    assert single_table == chunked_table


def test_base_event_includes_flavor_and_bare_version():
    collector = _make_collector(STRATEGY_SINGLE_QUERY)
    collector._check.version = MySQLVersion("8.0.35", "MySQL", "log")
    event = collector.base_event
    assert event["flavor"] == "MySQL"
    assert event["dbms_version"] == "8.0.35"
    assert collector.kind == "mysql_databases"
