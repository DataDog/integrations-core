# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
import datetime
import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Iterator

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig
from datadog_checks.mysql.cursor import CommenterDictCursor, CommenterSSDictCursor
from datadog_checks.mysql.queries import (
    SQL_COLUMNS,
    SQL_DATABASES,
    SQL_FOREIGN_KEYS,
    SQL_PARTITION,
    SQL_TABLES,
    get_indexes_query,
    get_schema_json_query,
)
from datadog_checks.mysql.util import get_list_chunks

if TYPE_CHECKING:
    from datadog_checks.mysql import MySql
    from datadog_checks.mysql.metadata import MySQLMetadata

# JSON aggregation (JSON_ARRAYAGG / JSON_OBJECT grouped) is required for the single-query strategy.
# It is available on MySQL >= 5.7.22 and MariaDB >= 10.5.0. Older versions fall back to the legacy
# collector (see metadata.py).
MYSQL_MIN_JSON_VERSION = (5, 7, 22)
MARIADB_MIN_JSON_VERSION = (10, 5, 0)

DEFAULT_SCHEMAS_COLLECTION_INTERVAL = 600
DEFAULT_MAX_EXECUTION_TIME = 60
# Number of tables to request detail for per round trip in the chunked strategy.
TABLES_CHUNK_SIZE = 500
# Number of tables (rows) to buffer before flushing a metadata payload.
DEFAULT_PAYLOAD_CHUNK_SIZE = 500

# Collection strategies for the v2 collector. Both produce byte-identical payloads; they differ
# only in how table detail is fetched, so the benchmark harness can compare them.
STRATEGY_SINGLE_QUERY = "single_query"  # shape A: one JSON-aggregation query per database
STRATEGY_CHUNKED = "chunked"  # shape B: stream the table list, fetch detail per chunk


def supports_json_collection(version, is_mariadb: bool) -> bool:
    """Return True when the server supports the JSON functions the v2 collector relies on."""
    if version is None:
        return False
    if is_mariadb:
        return version.version_compatible(MARIADB_MIN_JSON_VERSION)
    return version.version_compatible(MYSQL_MIN_JSON_VERSION)


def _as_list(value: Any) -> list:
    """Coerce a JSON_ARRAYAGG result into a list of dicts.

    pymysql may hand back JSON columns either already decoded (list) or as a raw ``str``/``bytes``
    payload depending on the driver's type conversion. ``NULL`` (no matching rows) becomes ``[]``.
    """
    if value is None:
        return []
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        value = json.loads(value)
    return value or []


def _to_bool(value: Any) -> bool:
    """Reproduce v1's nullable handling: the 'YES'/'NO' string becomes a bool."""
    return str(value).lower() == "yes"


def _json_safe_create_time(value: Any) -> Any:
    """Match v1, which serializes create_time through default_json_event_encoding (isoformat).

    The base collector's json.dumps has no custom encoder, so datetimes must be converted here.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def normalize_columns(rows: list[dict]) -> list[dict]:
    """Build the per-table columns list, matching the legacy collector field-for-field."""
    columns = []
    for row in sorted(rows, key=lambda r: r.get("ordinal_position") or 0):
        default = row.get("default")
        columns.append(
            {
                "name": row.get("name"),
                "column_type": row.get("column_type"),
                "default": str(default) if default is not None else None,
                "nullable": _to_bool(row.get("nullable")),
                "ordinal_position": row.get("ordinal_position"),
                "column_key": row.get("column_key"),
                "extra": row.get("extra"),
            }
        )
    return columns


def group_indexes(rows: list[dict]) -> list[dict]:
    """Group flat index key-part rows into per-index dicts, matching the legacy collector.

    Each input row is one key part; rows are grouped by index name and key parts are ordered by
    ``seq_in_index`` (JSON_ARRAYAGG does not preserve order).
    """
    by_index: dict[str, dict] = {}
    order: list[str] = []
    for row in sorted(rows, key=lambda r: (str(r.get("name")), r.get("seq_in_index") or 0)):
        index_name = str(row.get("name"))
        index_data = by_index.get(index_name)
        if index_data is None:
            cardinality = row.get("cardinality")
            index_data = {
                "name": index_name,
                # in-memory table BTREE indexes have no cardinality, so default to 0
                # https://bugs.mysql.com/bug.php?id=58520
                "cardinality": int(cardinality) if cardinality is not None else 0,
                "index_type": str(row.get("index_type")),
                "non_unique": bool(row.get("non_unique")),
            }
            by_index[index_name] = index_data
            order.append(index_name)

        if row.get("expression"):
            index_data["expression"] = str(row.get("expression"))

        if row.get("column_name"):
            column = {"name": row.get("column_name"), "nullable": _to_bool(row.get("nullable"))}
            if row.get("sub_part"):
                column["sub_part"] = int(row["sub_part"])
            if row.get("collation"):
                column["collation"] = str(row["collation"])
            if row.get("packed"):
                column["packed"] = str(row["packed"])
            index_data.setdefault("columns", []).append(column)

    return [by_index[name] for name in order]


def normalize_foreign_keys(rows: list[dict]) -> list[dict]:
    """Foreign keys are already grouped (one row per constraint); pass them through as dicts."""
    return [dict(row) for row in rows]


def group_partitions(rows: list[dict]) -> list[dict]:
    """Group flat partition/subpartition rows into per-partition dicts, matching the legacy collector.

    ``table_rows`` and ``data_length`` are summed across a partition's subpartition rows.
    """
    partitions: dict[str, dict] = {}
    order: list[str] = []
    for row in sorted(
        rows,
        key=lambda r: (r.get("partition_ordinal_position") or 0, r.get("subpartition_ordinal_position") or 0),
    ):
        partition_name = str(row.get("name"))
        partition_data = partitions.get(partition_name)
        if partition_data is None:
            partition_data = {
                "name": partition_name,
                "partition_ordinal_position": int(row.get("partition_ordinal_position")),
                "partition_method": str(row.get("partition_method")),
                "partition_expression": str(row.get("partition_expression")).strip().lower(),
                "partition_description": str(row.get("partition_description")),
                "table_rows": 0,
                "data_length": 0,
            }
            partitions[partition_name] = partition_data
            order.append(partition_name)

        partition_data["table_rows"] += int(row.get("table_rows"))
        partition_data["data_length"] += int(row.get("data_length"))

        if row.get("subpartition_name"):
            partition_data.setdefault("subpartitions", []).append(
                {
                    "name": row.get("subpartition_name"),
                    "subpartition_ordinal_position": int(row.get("subpartition_ordinal_position")),
                    "subpartition_method": str(row.get("subpartition_method")),
                    "subpartition_expression": str(row.get("subpartition_expression")).strip().lower(),
                    "table_rows": int(row.get("table_rows")),
                    "data_length": int(row.get("data_length")),
                }
            )

    return [partitions[name] for name in order]


class MySqlSchemaCollectorConfig(SchemaCollectorConfig):
    def __init__(self, schemas_config: dict):
        super().__init__()
        self.collection_interval = schemas_config.get("collection_interval", DEFAULT_SCHEMAS_COLLECTION_INTERVAL)
        self.payload_chunk_size = schemas_config.get("payload_chunk_size", DEFAULT_PAYLOAD_CHUNK_SIZE)
        # Capped by the collection interval, matching the legacy collector.
        self.max_execution_time = min(
            schemas_config.get("max_execution_time", DEFAULT_MAX_EXECUTION_TIME), self.collection_interval
        )
        self.collection_strategy = schemas_config.get("collection_strategy", STRATEGY_SINGLE_QUERY)


class _ChunkedTableCursor:
    """Adapts the chunked (shape B) generator to the cursor ``fetchone`` interface.

    The base ``SchemaCollector`` drives collection by repeatedly calling ``_get_next(cursor)``; this
    wrapper lets the chunked strategy yield fully-assembled table records the same way the
    single-query strategy yields one DB row per table.
    """

    def __init__(self, rows: Iterator[dict]):
        self._rows = rows

    def fetchone(self):
        return next(self._rows, None)


class MySqlSchemaCollector(SchemaCollector):
    _check: "MySql"
    _config: MySqlSchemaCollectorConfig

    def __init__(self, check: "MySql", metadata: "MySQLMetadata", config: MySqlSchemaCollectorConfig | None = None):
        self._metadata = metadata
        super().__init__(check, config or MySqlSchemaCollectorConfig(check._config.schemas_config))

    @property
    def kind(self) -> str:
        return "mysql_databases"

    @property
    def base_event(self):
        event = super().base_event
        # The MySQL schema payload carries the flavor and uses the bare version string (no build
        # suffix) for dbms_version, matching the legacy collector.
        event["dbms_version"] = self._check.version.version
        event["flavor"] = self._check.version.flavor
        # Match the legacy collector, which tags with the async job's DBM tags (service check tags
        # unioned with the check tags, e.g. including `port:`) rather than the bare check tags.
        if getattr(self._metadata, "_tags", None):
            event["tags"] = self._metadata._tags
        return event

    def _get_databases(self) -> list[dict]:
        with self._metadata.get_db_connection().cursor(CommenterDictCursor) as cursor:
            cursor.execute(SQL_DATABASES)
            return [dict(row) for row in cursor.fetchall()]

    @contextlib.contextmanager
    def _get_cursor(self, database_name: str):
        if self._config.collection_strategy == STRATEGY_CHUNKED:
            yield _ChunkedTableCursor(self._iter_chunked_tables(database_name))
            return

        query = get_schema_json_query(
            self._check.version,
            self._check.is_mariadb,
            max_execution_time_ms=int(self._config.max_execution_time * 1000),
        )
        params = [database_name] * 5
        if self._check.is_mariadb and self._config.max_execution_time and self._config.max_execution_time > 0:
            # MariaDB has no MAX_EXECUTION_TIME optimizer hint; wrap the statement instead.
            query = "SET STATEMENT max_statement_time={} FOR {}".format(self._config.max_execution_time, query)
        # SSCursor streams rows one at a time, keeping integration memory to roughly one table's
        # worth of already-aggregated metadata plus the payload chunk buffer.
        with self._metadata.get_db_connection().cursor(CommenterSSDictCursor) as cursor:
            cursor.execute(query, params)
            yield cursor

    def _get_next(self, cursor):
        return cursor.fetchone()

    def _map_row(self, database: dict, cursor_row: dict) -> dict:
        object = super()._map_row(database, cursor_row)
        if self._config.collection_strategy == STRATEGY_CHUNKED:
            table = self._build_table(
                cursor_row,
                cursor_row.get("_columns") or [],
                cursor_row.get("_indexes") or [],
                cursor_row.get("_foreign_keys") or [],
                cursor_row.get("_partitions") or [],
            )
        else:
            table = self._build_table(
                cursor_row,
                _as_list(cursor_row.get("columns_json")),
                _as_list(cursor_row.get("indexes_json")),
                _as_list(cursor_row.get("foreign_keys_json")),
                _as_list(cursor_row.get("partitions_json")),
            )
        object["tables"] = [table]
        return object

    def _build_table(
        self,
        table_row: dict,
        columns_flat: list[dict],
        indexes_flat: list[dict],
        foreign_keys_flat: list[dict],
        partitions_flat: list[dict],
    ) -> dict:
        table = {
            "name": table_row.get("name"),
            "engine": table_row.get("engine"),
            "row_format": table_row.get("row_format"),
            "create_time": _json_safe_create_time(table_row.get("create_time")),
        }
        # Only attach detail keys when present, matching the legacy collector's setdefault behavior.
        columns = normalize_columns(columns_flat)
        if columns:
            table["columns"] = columns
        indexes = group_indexes(indexes_flat)
        if indexes:
            table["indexes"] = indexes
        foreign_keys = normalize_foreign_keys(foreign_keys_flat)
        if foreign_keys:
            table["foreign_keys"] = foreign_keys
        partitions = group_partitions(partitions_flat)
        if partitions:
            table["partitions"] = partitions
        return table

    def _iter_chunked_tables(self, database_name: str) -> Iterator[dict]:
        """Shape B: stream the table list, then fetch detail one chunk of tables at a time.

        Yields intermediate records shaped like ``{name, engine, row_format, create_time, _columns,
        _indexes, _foreign_keys, _partitions}`` where the ``_*`` values are flat detail rows that
        ``_build_table`` normalizes identically to the single-query strategy.
        """
        conn = self._metadata.get_db_connection()
        with conn.cursor(CommenterDictCursor) as cursor:
            cursor.execute(SQL_TABLES, database_name)
            tables = [dict(row) for row in cursor.fetchall()]

        for tables_chunk in get_list_chunks(tables, TABLES_CHUNK_SIZE):
            table_names = [str(table["name"]) for table in tables_chunk]
            placeholders = ",".join(["%s"] * len(table_names))
            params = [database_name] + table_names

            columns_by_table = self._fetch_grouped(SQL_COLUMNS.format(placeholders), params)
            indexes_by_table = self._fetch_grouped(
                get_indexes_query(self._check.version, self._check.is_mariadb, placeholders), params
            )
            foreign_keys_by_table = self._fetch_grouped(SQL_FOREIGN_KEYS.format(placeholders), params)
            partitions_by_table = self._fetch_grouped(SQL_PARTITION.format(placeholders), params)

            for table in tables_chunk:
                name = table["name"]
                yield {
                    "name": name,
                    "engine": table.get("engine"),
                    "row_format": table.get("row_format"),
                    "create_time": table.get("create_time"),
                    "_columns": columns_by_table.get(name, []),
                    "_indexes": indexes_by_table.get(name, []),
                    "_foreign_keys": foreign_keys_by_table.get(name, []),
                    "_partitions": partitions_by_table.get(name, []),
                }

    def _fetch_grouped(self, query: str, params: list) -> dict[Any, list[dict]]:
        """Run a detail query and group its rows by table_name (which is dropped from index/column
        rows to match the single-query JSON output; foreign-key rows keep it, as in v1)."""
        grouped: dict[Any, list[dict]] = defaultdict(list)
        with self._metadata.get_db_connection().cursor(CommenterDictCursor) as cursor:
            cursor.execute(query, params)
            for row in cursor.fetchall():
                grouped[row["table_name"]].append(dict(row))
        return grouped
