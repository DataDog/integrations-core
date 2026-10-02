# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import json
import threading
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
    supports_single_query_collection,
)
from datadog_checks.mysql.version_utils import MySQLVersion

pytestmark = pytest.mark.unit


def _make_collector(strategy, *, is_mariadb=False, version="8.0.35", config=None):
    check = mock.MagicMock()
    check.log = mock.MagicMock()
    check.is_mariadb = is_mariadb
    check.version = MySQLVersion(version, "MariaDB" if is_mariadb else "MySQL", "unspecified")
    metadata = mock.MagicMock()
    collector = MySqlSchemaCollector(check, metadata, MySqlSchemaCollectorConfig(config or {}))
    collector._strategy = strategy
    return collector


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


def test_group_indexes_reports_full_index_cardinality():
    # Index cardinality is the full-index value (highest seq_in_index), not the leading column's.
    # Rows are supplied out of seq_in_index order to confirm the result is order-independent.
    rows = [
        {
            "name": "composite_index",
            "collation": "A",
            "cardinality": 4947,
            "index_type": "BTREE",
            "seq_in_index": 2,
            "column_name": "amount",
            "sub_part": None,
            "packed": None,
            "nullable": "NO",
            "non_unique": 1,
            "expression": None,
        },
        {
            "name": "composite_index",
            "collation": "A",
            "cardinality": 3158,
            "index_type": "BTREE",
            "seq_in_index": 1,
            "column_name": "ref_id",
            "sub_part": None,
            "packed": None,
            "nullable": "YES",
            "non_unique": 1,
            "expression": None,
        },
    ]
    index = group_indexes(rows)[0]
    assert index["cardinality"] == 4947
    assert [c["name"] for c in index["columns"]] == ["ref_id", "amount"]


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
        # 5.7 has JSON_ARRAYAGG from 5.7.22 but is excluded on cost grounds.
        (False, "5.7.22", False),
        (False, "5.7.44", False),
        (False, "8.0.0", True),
        (False, "8.0.35", True),
        (False, "8.4.0", True),
        (True, "10.5.0", False),
        (True, "10.4.30", False),
        (True, "11.4.2", False),
    ],
)
def test_supports_single_query_collection(is_mariadb, version, expected):
    v = MySQLVersion(version, "MariaDB" if is_mariadb else "MySQL", "unspecified")
    assert supports_single_query_collection(v, is_mariadb) is expected


def test_supports_single_query_collection_none_version():
    assert supports_single_query_collection(None, False) is False


@pytest.mark.parametrize(
    "use_single_query,expected",
    [
        (True, STRATEGY_SINGLE_QUERY),
        (False, STRATEGY_CHUNKED),
    ],
)
def test_use_single_query_opts_out_on_supported_server(use_single_query, expected):
    collector = _make_collector(STRATEGY_CHUNKED, version="8.0.35", config={"use_single_query": use_single_query})

    assert collector._resolve_strategy() == expected


def _run_every_schema_query(collector) -> list[str]:
    """Run the database list, the chunked table list and detail queries, and the single query."""
    db_cursor = collector._metadata.get_db_connection.return_value.cursor.return_value.__enter__.return_value
    db_cursor.fetchall.side_effect = [[{"name": "app"}], [{"name": "t1"}]] + [[]] * 4

    collector._get_databases()
    list(collector._iter_chunked_tables("app"))
    collector._strategy = STRATEGY_SINGLE_QUERY
    with collector._get_cursor("app"):
        pass

    return [call.args[0] for call in db_cursor.execute.call_args_list]


MYSQL_TIMEOUT_HINT = "SELECT /*+ MAX_EXECUTION_TIME(60000) */"
MARIADB_TIMEOUT_PREFIX = "SET STATEMENT max_statement_time=60.0 FOR "


@pytest.mark.parametrize(
    "is_mariadb,version,expected_timeout",
    [
        (False, "5.6.51", None),
        (False, "5.7.7", None),
        (False, "5.7.8", MYSQL_TIMEOUT_HINT),
        (False, "8.0.35", MYSQL_TIMEOUT_HINT),
        (True, "10.11.18", MARIADB_TIMEOUT_PREFIX),
    ],
)
def test_every_schema_query_applies_supported_query_timeout(is_mariadb, version, expected_timeout):
    collector = _make_collector(STRATEGY_CHUNKED, is_mariadb=is_mariadb, version=version)

    queries = _run_every_schema_query(collector)

    assert len(queries) == 7
    for query in queries:
        if expected_timeout == MYSQL_TIMEOUT_HINT:
            assert MYSQL_TIMEOUT_HINT in query
        elif expected_timeout == MARIADB_TIMEOUT_PREFIX:
            assert query.startswith(MARIADB_TIMEOUT_PREFIX)
            assert "MAX_EXECUTION_TIME" not in query
        else:
            assert "MAX_EXECUTION_TIME" not in query
            assert not query.startswith("SET STATEMENT")


@pytest.mark.parametrize("max_execution_time", [0, -1])
def test_non_positive_max_execution_time_disables_query_timeout(max_execution_time):
    collector = _make_collector(STRATEGY_CHUNKED, config={"max_execution_time": max_execution_time})
    cursor = mock.MagicMock()

    assert collector._query_timeout() is None
    assert collector._query_hint() == ""
    collector._execute(cursor, "SELECT 1")
    cursor.execute.assert_called_once_with("SELECT 1", None)


def test_chunked_collection_fetches_connection_once_per_database():
    collector = _make_collector(STRATEGY_CHUNKED, version="5.7.44")
    get_db_connection = collector._metadata.get_db_connection
    db_cursor = get_db_connection.return_value.cursor.return_value.__enter__.return_value
    # The table list, then the four detail queries for each of the two chunks.
    db_cursor.fetchall.side_effect = [[{"name": "t1"}, {"name": "t2"}]] + [[]] * 8

    with mock.patch("datadog_checks.mysql.schemas.TABLES_CHUNK_SIZE", 1):
        tables = list(collector._iter_chunked_tables("app"))

    assert [table["name"] for table in tables] == ["t1", "t2"]
    assert db_cursor.execute.call_count == 9
    get_db_connection.assert_called_once()


def test_chunked_collection_passes_table_names_as_query_parameters():
    """Table names come from the server and must never be interpolated into SQL."""
    collector = _make_collector(STRATEGY_CHUNKED, version="5.7.44")
    table_names = ["normal_table", 'bad"table', "x') UNION SELECT user()#"]
    db_cursor = collector._metadata.get_db_connection.return_value.cursor.return_value.__enter__.return_value
    db_cursor.fetchall.side_effect = [[{"name": name} for name in table_names]] + [[]] * 4

    list(collector._iter_chunked_tables("mydb"))

    # The first query lists the tables; the rest fetch column, index, foreign key, and partition detail.
    detail_calls = db_cursor.execute.call_args_list[1:]
    assert len(detail_calls) == 4
    for call in detail_calls:
        query, params = call.args
        assert params == ["mydb"] + table_names
        assert query.count("%s") == len(params)
        for name in table_names:
            assert name not in query


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
    collector._check.agent_version = "7.70.0"
    event = collector.base_event
    assert event["flavor"] == "MySQL"
    assert event["dbms_version"] == "8.0.35"
    assert event["agent_version"] == "7.70.0"
    assert collector.kind == "mysql_databases"


def _make_collecting_collector(databases):
    """Build a collector that can run `collect_schemas` end to end, where each database has no tables."""
    collector = _make_collector(STRATEGY_SINGLE_QUERY)
    collector._check.reported_hostname = "db-host"
    collector._check.database_identifier = "db-host"
    collector._check.dbms = "mysql"
    collector._check.tags = []
    collector._check.cloud_metadata = {}
    collector._check.agent_version = "7.70.0"
    collector._metadata._tags = None
    db_cursor = collector._metadata.get_db_connection.return_value.cursor.return_value.__enter__.return_value
    db_cursor.fetchall.return_value = databases
    collector._get_cursor = mock.Mock(return_value=mock.MagicMock())
    collector._get_next = mock.Mock(return_value=None)
    return collector


def test_collect_schemas_stops_at_next_database_when_cancelled():
    collector = _make_collecting_collector([{"name": "app"}, {"name": "other"}])
    cancel_event = threading.Event()

    def raise_if_cancelled():
        if cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")

    def cancel_during_collection(database_name):
        cancel_event.set()
        return mock.MagicMock()

    collector._metadata._raise_if_cancelled.side_effect = raise_if_cancelled
    collector._get_cursor.side_effect = cancel_during_collection

    with pytest.raises(Exception, match="cancelled"):
        collector.collect_schemas()

    collector._get_cursor.assert_called_once_with("app")


def test_collect_schemas_names_database_without_tables():
    """The backend sweeps stored tables per reported database, so a database whose tables were
    all dropped has to be named in its payload rather than sent as an empty one."""
    empty = {"name": "empty", "default_character_set_name": "utf8mb4", "default_collation_name": "utf8mb4_bin"}
    app = {"name": "app", "default_character_set_name": "utf8mb4", "default_collation_name": "utf8mb4_bin"}
    collector = _make_collecting_collector([empty, app])
    del collector._get_cursor, collector._get_next
    collector._check.version = MySQLVersion("5.7.44", "MySQL", "unspecified")
    db_cursor = collector._metadata.get_db_connection.return_value.cursor.return_value.__enter__.return_value
    # The database list, the empty table list, then app's table list and its four detail queries.
    db_cursor.fetchall.side_effect = [[empty, app], [], [{"name": "t1"}], [], [], [], []]

    collector.collect_schemas()

    payloads = [json.loads(call.args[0]) for call in collector._check.database_monitoring_metadata.call_args_list]
    assert payloads[0]["metadata"] == [{**empty, "tables": []}]
    assert [(db["name"], [table["name"] for table in db["tables"]]) for db in payloads[1]["metadata"]] == [
        ("app", ["t1"])
    ]
    assert [payload["collection_payloads_count"] for payload in payloads] == [1, 1]


def test_collect_schemas_warns_when_no_tables_are_visible():
    collector = _make_collecting_collector([{"name": "app"}, {"name": "other"}])

    collector.collect_schemas()

    collector._log.warning.assert_called_once()
    assert "REFERENCES" in collector._log.warning.call_args[0][0]
