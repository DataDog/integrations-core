# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import contextlib
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
    MySqlViewCollector,
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
    collector._tables._strategy = strategy
    return collector


def _make_view_collector(config=None) -> MySqlViewCollector:
    collector = _make_collector(STRATEGY_CHUNKED, config={"collect_views": True, **(config or {})})
    views = collector._object_collectors[-1]
    assert isinstance(views, MySqlViewCollector)
    return views


def _db_cursor(collector):
    return collector._metadata.get_db_connection.return_value.cursor.return_value.__enter__.return_value


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

    assert collector._tables._resolve_strategy() == expected


def _run_every_schema_query(collector) -> list[str]:
    """
    Run the database list, the chunked table list and detail queries, the single query, and the view list and
    column queries.
    """
    tables, views = collector._object_collectors
    db_cursor = _db_cursor(collector)
    db_cursor.fetchall.side_effect = [[{"name": "app"}], [{"name": "t1"}]] + [[]] * 4 + [[{"name": "v1"}], []]

    collector._get_databases()
    list(tables._iter_chunked_tables("app"))
    tables._strategy = STRATEGY_SINGLE_QUERY
    with tables._open_rows(None, {"name": "app"}):
        pass
    with views._open_rows(None, {"name": "app"}) as rows:
        list(rows)

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
    collector = _make_collector(
        STRATEGY_CHUNKED, is_mariadb=is_mariadb, version=version, config={"collect_views": True}
    )

    queries = _run_every_schema_query(collector)

    assert len(queries) == 9
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
        tables = list(collector._tables._iter_chunked_tables("app"))

    assert [table["name"] for table in tables] == ["t1", "t2"]
    assert db_cursor.execute.call_count == 9
    get_db_connection.assert_called_once()


@pytest.mark.parametrize(
    "kind, detail_queries",
    [
        # Column, index, foreign key, and partition detail.
        pytest.param("mysql_databases", 4, id="tables"),
        # Column detail.
        pytest.param("mysql_views", 1, id="views"),
    ],
)
def test_chunked_collection_passes_object_names_as_query_parameters(kind, detail_queries):
    """Table and view names come from the server and must never be interpolated into SQL."""
    collector = _make_collector(STRATEGY_CHUNKED, version="5.7.44", config={"collect_views": True})
    [object_collector] = [c for c in collector._object_collectors if c.kind == kind]
    names = ["normal_name", 'bad"name', "x') UNION SELECT user()#"]
    db_cursor = _db_cursor(collector)
    db_cursor.fetchall.side_effect = [[{"name": name} for name in names]] + [[]] * detail_queries

    with object_collector._open_rows(None, {"name": "mydb"}) as rows:
        list(rows)

    # The first query lists the objects; the rest fetch their detail.
    detail_calls = db_cursor.execute.call_args_list[1:]
    assert len(detail_calls) == detail_queries
    for call in detail_calls:
        query, params = call.args
        assert params == ["mydb"] + names
        assert query.count("%s") == len(params)
        for name in names:
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
    collector = _make_collector(STRATEGY_SINGLE_QUERY)._tables
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
    single = _make_collector(STRATEGY_SINGLE_QUERY)._tables
    chunked = _make_collector(STRATEGY_CHUNKED)._tables

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


@pytest.mark.parametrize("kind", ["mysql_databases", "mysql_views"])
def test_base_event_includes_flavor_and_bare_version(kind):
    collector = _make_collector(STRATEGY_SINGLE_QUERY, config={"collect_views": True})
    [object_collector] = [c for c in collector._object_collectors if c.kind == kind]
    collector._check.version = MySQLVersion("8.0.35", "MySQL", "log")
    collector._check.agent_version = "7.70.0"
    event = object_collector.base_event
    assert event["kind"] == kind
    assert event["flavor"] == "MySQL"
    assert event["dbms_version"] == "8.0.35"
    assert event["agent_version"] == "7.70.0"


@pytest.mark.parametrize(
    "config, expected_kinds",
    [
        pytest.param({}, ["mysql_databases"], id="default"),
        pytest.param({"collect_views": True}, ["mysql_databases", "mysql_views"], id="collect_views"),
    ],
)
def test_collect_views_adds_views_kind(config, expected_kinds):
    assert _make_collector(STRATEGY_CHUNKED, config=config).kinds == expected_kinds


@pytest.mark.parametrize(
    "max_views, expected_limit",
    [
        pytest.param(None, 1000, id="default"),
        pytest.param(5, 5, id="configured"),
        pytest.param(0, 1_000_000, id="zero means no limit"),
    ],
)
def test_view_query_limits_views_per_database(max_views, expected_limit):
    views = _make_view_collector({} if max_views is None else {"max_views": max_views})
    db_cursor = _db_cursor(views)
    db_cursor.fetchall.return_value = []

    with views._open_rows(None, {"name": "mydb"}) as rows:
        list(rows)

    assert db_cursor.execute.call_args.args[1] == ["mydb", expected_limit]


@pytest.mark.parametrize(
    "definition, expected_definition",
    [
        pytest.param("select `id` from `t`", "select `id` from `t`", id="visible"),
        # MySQL returns an empty definition when the user lacks SHOW VIEW.
        pytest.param("", None, id="hidden"),
    ],
)
def test_view_map_row_shapes_payload(definition, expected_definition):
    views = _make_view_collector()
    column = {
        "name": "id",
        "column_type": "int",
        "default": None,
        "nullable": "NO",
        "ordinal_position": 1,
        "column_key": "",
        "extra": "",
    }

    obj = views._map_row(
        {"name": "mydb", "default_collation_name": "utf8"},
        {"name": "v", "definition": definition, "_columns": [column]},
    )

    assert obj == {
        "name": "mydb",
        "default_collation_name": "utf8",
        "tables": [],
        "views": [{"name": "v", "definition": expected_definition, "columns": normalize_columns([column])}],
    }


def _make_collecting_collector(databases):
    """Build a collector that can run `collect_schemas` end to end, where each database has no tables."""
    collector = _make_collector(STRATEGY_SINGLE_QUERY)
    collector._check.reported_hostname = "db-host"
    collector._check.database_identifier = "db-host"
    collector._check.dbms = "mysql"
    collector._check.tags = []
    collector._check.cloud_metadata = {}
    collector._check.agent_version = "7.70.0"
    _db_cursor(collector).fetchall.return_value = databases
    collector._tables._open_rows = mock.Mock(side_effect=lambda session, database: contextlib.nullcontext(iter(())))
    return collector


def test_collect_schemas_stops_at_next_database_when_cancelled():
    collector = _make_collecting_collector([{"name": "app"}, {"name": "other"}])
    cancel_event = threading.Event()

    def raise_if_cancelled():
        if cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")

    def cancel_during_collection(session, database):
        cancel_event.set()
        return contextlib.nullcontext(iter(()))

    collector._metadata._raise_if_cancelled.side_effect = raise_if_cancelled
    collector._tables._open_rows.side_effect = cancel_during_collection

    with pytest.raises(Exception, match="cancelled"):
        collector.collect_schemas()

    collector._tables._open_rows.assert_called_once_with(None, {"name": "app"})


def test_collect_schemas_warns_when_no_tables_are_visible():
    collector = _make_collecting_collector([{"name": "app"}, {"name": "other"}])

    collector.collect_schemas()

    collector._log.warning.assert_called_once()
    assert "REFERENCES" in collector._log.warning.call_args[0][0]
