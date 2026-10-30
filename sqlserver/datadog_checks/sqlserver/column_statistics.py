# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import itertools
import time
from typing import TYPE_CHECKING, Any, Iterator

from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.diagnose import SYSTEM_DATABASES
from datadog_checks.sqlserver.health import SqlServerHealthEvent
from datadog_checks.sqlserver.utils import (
    construct_use_statement,
    raise_if_cancelled,
    serialize_database_names,
)

if TYPE_CHECKING:
    from threading import Event

    from datadog_checks.sqlserver import SQLServer

DEFAULT_COLLECTION_INTERVAL = 3600
DEFAULT_MAX_TABLES = 500
# Each table is stored as its own event, which must stay under the intake's 1 MB per message, and each payload under
# its 5 MB per request.
TABLE_MAX_BYTES = 900_000
PAYLOAD_MAX_BYTES = 4_000_000
# The check's command_timeout (10s by default) is too short for the procedure on a large database. This matches the
# Postgres collector's statement timeout.
MAX_QUERY_DURATION_SECONDS = 60
KEY_PREFIX = "dbm-column-statistics-"

# The agent's login can't read statistics itself, since SQL Server treats them as table data. Customers install this
# procedure (tests/sql/column_statistics.sql) in each database; it runs as its owner and returns each column's
# statistics as SQL Server reports them, with only the counts in its histogram, never column values. They're sent with
# SQL Server's names, and the backend derives what it needs from them.
COLUMN_STATISTICS_QUERY = "EXEC datadog.column_statistics @max_tables = ?"
# The columns the procedure returns. A procedure installed from an older version of the documentation returns others.
PROCEDURE_COLUMNS = frozenset(
    (
        "schema_name",
        "table_name",
        "column_name",
        "stats_name",
        "auto_created",
        "user_created",
        "type_name",
        "max_length",
        "is_nullable",
        "is_unique",
        "last_updated",
        "rows",
        "rows_sampled",
        "steps",
        "modification_counter",
        "average_length",
        "histogram",
    )
)
# The sys.dm_db_stats_histogram columns sent for each step, as parallel arrays. Whether a step's range_high_key is NULL
# stands in for the value itself, which is never sent.
HISTOGRAM_FIELDS = ("range_high_key_is_null", "equal_rows", "range_rows", "distinct_range_rows", "average_range_rows")
PROCEDURE_OUTDATED_MESSAGE = "datadog.column_statistics is outdated"

# get_databases() includes every database autodiscovery finds, whatever its state. An offline or inaccessible one,
# such as a non-readable availability group secondary, can't run the procedure.
DATABASES_QUERY = """
DECLARE @databases xml = ?;
SELECT name
FROM sys.databases
WHERE name IN (
        SELECT database_node.value('.', 'nvarchar(128)')
        FROM @databases.nodes('/databases/database') AS d(database_node)
    )
    AND state = 0 AND HAS_DBACCESS(name) = 1;
"""

# Setup problems the customer can fix. pyodbc ends its messages with the native error number, as in "(2812)", which
# holds in any server language; adodbapi only passes the message text through, which is in the server's language.
SETUP_ERRORS = (
    (
        SqlServerHealthEvent.COLUMN_STATISTICS_PROCEDURE_NOT_FOUND,
        ("(2812)", "Could not find stored procedure"),
        "create it as described in the documentation",
    ),
    (
        SqlServerHealthEvent.COLUMN_STATISTICS_INSUFFICIENT_PRIVILEGE,
        ("(229)", "EXECUTE permission was denied"),
        "grant EXECUTE on it to the Agent's user",
    ),
    (
        SqlServerHealthEvent.COLUMN_STATISTICS_PROCEDURE_OUTDATED,
        (PROCEDURE_OUTDATED_MESSAGE,),
        "re-create it as described in the documentation",
    ),
)


class OutdatedProcedureError(Exception):
    pass


def agent_check_getter(self: SqlserverColumnStatisticsCollector) -> SQLServer:
    return self._check


class SqlserverColumnStatisticsCollector:
    """
    Collects each column's statistics as SQL Server reports them. It runs in the metadata job, as the Postgres collector
    does.
    """

    def __init__(self, check: SQLServer, config: SQLServerConfig, cancel_event: Event):
        column_statistics_config = config.column_statistics_config
        self._check = check
        self._log = check.log
        self._cancel_event = cancel_event
        self.collection_interval = column_statistics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        self._max_tables = int(column_statistics_config.get('max_tables', DEFAULT_MAX_TABLES))
        # The databases currently failing each way, so each database's warning is logged once, and the health event
        # goes to warning with the first failing database and back to OK when the last one is fixed.
        self._failing_dbs: dict[SqlServerHealthEvent, set[str]] = {event: set() for event, _, _ in SETUP_ERRORS}
        self._warned_no_databases = False

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect(self) -> None:
        started = time.time()
        tables = columns = payloads = 0
        status = "success"
        try:
            with self._check.connection.open_managed_default_connection(KEY_PREFIX):
                # The driver applies the timeout to cursors created after it's set.
                self._check.connection.set_command_timeout(KEY_PREFIX, MAX_QUERY_DURATION_SECONDS)
                with self._check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
                    for db_name in self._databases(cursor):
                        raise_if_cancelled(self._cancel_event)
                        db_tables, db_columns, db_payloads = self._collect_database(cursor, db_name)
                        tables += db_tables
                        columns += db_columns
                        payloads += db_payloads
        except Exception:
            status = "error"
            raise
        finally:
            tags = self._check.tags + ["status:" + status]
            hostname = self._check.reported_hostname
            self._check.histogram(
                "dd.sqlserver.column_statistics.time",
                (time.time() - started) * 1000,
                tags=tags,
                hostname=hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.sqlserver.column_statistics.tables_count", tables, tags=tags, hostname=hostname, raw=True
            )
            self._check.gauge(
                "dd.sqlserver.column_statistics.columns_count", columns, tags=tags, hostname=hostname, raw=True
            )
            self._check.gauge(
                "dd.sqlserver.column_statistics.payloads_count", payloads, tags=tags, hostname=hostname, raw=True
            )

    def _databases(self, cursor: Any) -> list[str]:
        # The system databases can't usefully hold the procedure: tempdb even loses it on restart.
        db_names = [db_name for db_name in self._check.get_databases() if db_name.lower() not in SYSTEM_DATABASES]
        cursor.execute(DATABASES_QUERY, (serialize_database_names(db_names),))
        usable = {row[0] for row in cursor.fetchall()}
        databases = [db_name for db_name in db_names if db_name in usable]
        # A database that was failing and is now skipped, as when it went offline, no longer needs fixing.
        for db_name in set().union(*self._failing_dbs.values()) - set(databases):
            self._handle_recovery(db_name)
        if not databases and not self._warned_no_databases:
            self._warned_no_databases = True
            self._log.warning(
                "No database to collect column statistics from: they're only collected from online user databases. "
                "Set `database` to one, or enable `database_autodiscovery`."
            )
        return databases

    def _collect_database(self, cursor: Any, db_name: str) -> tuple[int, int, int]:
        tables = columns = payloads = 0
        # Rows come ordered by table, and each table's histograms can take megabytes, so tables are sent as they
        # complete rather than all held at once.
        batch: list[dict] = []
        batch_bytes = 0
        try:
            cursor.execute(construct_use_statement(db_name))
            cursor.execute(COLUMN_STATISTICS_QUERY, (self._max_tables,))
            names = [str(column[0]).lower() for column in cursor.description]
            if not PROCEDURE_COLUMNS <= set(names):
                raise OutdatedProcedureError(PROCEDURE_OUTDATED_MESSAGE)
            for table in read_tables(cursor, names, db_name):
                table_bytes = fit_table(table)
                if batch and batch_bytes + table_bytes > PAYLOAD_MAX_BYTES:
                    self._submit(batch)
                    payloads += 1
                    batch, batch_bytes = [], 0
                batch.append(table)
                batch_bytes += table_bytes
                tables += 1
                columns += len(table["columns"])
        except Exception as e:
            self._handle_error(db_name, e)
        else:
            self._handle_recovery(db_name)
        # Tables are only yielded once all their rows are read, so those read before an error are complete.
        if batch:
            self._submit(batch)
            payloads += 1
        return tables, columns, payloads

    def _handle_error(self, db_name: str, error: Exception) -> None:
        message = str(error)
        for event, markers, fix in SETUP_ERRORS:
            if not any(marker in message for marker in markers):
                continue
            # A database fails one way at a time: a database now failing differently has fixed its earlier problem.
            self._handle_recovery(db_name, still_failing=event)
            failing = self._failing_dbs[event]
            if db_name not in failing:
                if not failing:
                    self._check.health.submit_health_event(name=event, status=HealthStatus.WARNING)
                failing.add(db_name)
                self._log.warning(
                    "Can't run datadog.column_statistics in database '%s' (%s); %s: "
                    "https://docs.datadoghq.com/database_monitoring/setup_sql_server/",
                    db_name,
                    message,
                    fix,
                )
            return
        self._log.exception("Error collecting column statistics for database '%s'", db_name)

    def _handle_recovery(self, db_name: str, still_failing: SqlServerHealthEvent | None = None) -> None:
        for event, failing in self._failing_dbs.items():
            if event != still_failing and db_name in failing:
                failing.remove(db_name)
                if not failing:
                    self._check.health.submit_health_event(name=event, status=HealthStatus.OK)

    def _submit(self, tables: list[dict]) -> None:
        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": self._check.agent_version,
            "ddsource": self._check.dbms,
            "dbms": self._check.dbms,
            "dbms_version": self._check.dbms_version,
            "cloud_metadata": self._check.cloud_metadata,
            "dbm_type": "column_statistics",
            "collection_interval": self.collection_interval,
            "tags": self._check.tag_manager.get_tags(include_internal=False, include_db=False),
            "timestamp": time.time() * 1000,
            "column_statistics": tables,
        }
        self._check.database_monitoring_column_statistics(json.dumps(event, default=default_json_event_encoding))


def read_tables(cursor: Any, names: list[str], db_name: str) -> Iterator[dict]:
    """Read the procedure's rows, one per column ordered by table, into the column_statistics payload's tables."""
    rows = (dict(zip(names, row)) for row in iter(cursor.fetchone, None))
    for (schema, table), columns in itertools.groupby(
        rows, key=lambda stats: (stats["schema_name"], stats["table_name"])
    ):
        yield {
            "version": 1,
            "db": db_name,
            "schema": schema,
            "table": table,
            "columns": [column_statistics(stats) for stats in columns],
        }


def column_statistics(stats: dict) -> dict:
    """A column's entry in the payload, from its row in the procedure's results."""
    return {
        "column_name": stats["column_name"],
        "stats_name": stats["stats_name"],
        "auto_created": bool(stats["auto_created"]),
        "user_created": bool(stats["user_created"]),
        "type_name": stats["type_name"],
        "max_length": int(stats["max_length"]),
        "is_nullable": bool(stats["is_nullable"]),
        "is_unique": bool(stats["is_unique"]),
        # ISO 8601 with the server's offset, as the procedure formats it.
        "last_updated": stats["last_updated"],
        "rows": int(stats["rows"]),
        "rows_sampled": int(stats["rows_sampled"]),
        "steps": int(stats["steps"]),
        "modification_counter": int(stats["modification_counter"]),
        "average_length": None if stats["average_length"] is None else float(stats["average_length"]),
        "histogram": parse_histogram(stats["histogram"]),
    }


def parse_histogram(packed: str | None) -> dict[str, list]:
    """
    Unpack the histogram steps the procedure packs as
    range_high_key_is_null:equal_rows:range_rows:distinct_range_rows:average_range_rows into parallel arrays.
    """
    histogram: dict[str, list] = {field: [] for field in HISTOGRAM_FIELDS}
    for step in packed.split(",") if packed else []:
        is_null, *counts = step.split(":")
        histogram["range_high_key_is_null"].append(is_null == "1")
        for field, count in zip(HISTOGRAM_FIELDS[1:], counts):
            histogram[field].append(float(count))
    return histogram


def fit_table(table: dict) -> int:
    """
    Return the size of a table's JSON, first setting its largest histograms to None in place if it's over
    TABLE_MAX_BYTES. A column without its histogram still has its other statistics.
    """
    size = len(json.dumps(table, default=default_json_event_encoding))
    if size <= TABLE_MAX_BYTES:
        return size
    by_steps = sorted(table["columns"], key=lambda column: len(column["histogram"]["equal_rows"]), reverse=True)
    for column in by_steps:
        if size <= TABLE_MAX_BYTES:
            break
        size -= len(json.dumps(column["histogram"])) - len("null")
        column["histogram"] = None
    return size
