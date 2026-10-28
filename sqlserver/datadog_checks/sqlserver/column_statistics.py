# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

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
PAYLOAD_MAX_COLUMNS = 5_000
# The check's command_timeout (10s by default) is too short for the procedure on a large database. This matches the
# Postgres collector's statement timeout.
MAX_QUERY_DURATION_SECONDS = 60
KEY_PREFIX = "dbm-column-statistics-"
# Postgres's default_statistics_target, the most values ANALYZE keeps in most_common_freqs.
MAX_COMMON_VALUES = 100
# Fewer distinct values than this share of the rows are sent as a count, more as a negative share, as ANALYZE does.
N_DISTINCT_SCALING_THRESHOLD = 0.1

# The agent's login can't read statistics itself, since SQL Server treats them as table data. Customers install this
# procedure (tests/sql/column_statistics.sql) in each database; it runs as its owner and returns only the counts in
# each column's histogram, never column values.
COLUMN_STATISTICS_QUERY = "EXEC datadog.column_statistics @max_tables = ?"
# The columns the procedure returns. A procedure installed from an older version of the documentation returns others.
PROCEDURE_COLUMNS = frozenset(
    (
        "schema_name",
        "table_name",
        "column_name",
        "is_nullable",
        "is_unique",
        "rows",
        "rows_sampled",
        "stats_age",
        "fixed_width",
        "avg_width",
        "steps",
    )
)
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
    Collects column statistics, in the shape the Postgres integration sends from pg_stats. It runs in the metadata job,
    as the Postgres collector does.
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

    def _databases(self, cursor) -> list[str]:
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

    def _collect_database(self, cursor, db_name: str) -> tuple[int, int, int]:
        try:
            cursor.execute(construct_use_statement(db_name))
            cursor.execute(COLUMN_STATISTICS_QUERY, (self._max_tables,))
            names = [str(column[0]).lower() for column in cursor.description]
            if not PROCEDURE_COLUMNS <= set(names):
                raise OutdatedProcedureError(PROCEDURE_OUTDATED_MESSAGE)
            # Each row's packed steps can take kilobytes, so each is derived as it arrives rather than all held at once.
            columns = []
            row = cursor.fetchone()
            while row:
                stats = dict(zip(names, row))
                columns.append(derive_column_statistics(stats, parse_steps(stats["steps"])))
                row = cursor.fetchone()
        except Exception as e:
            self._handle_error(db_name, e)
            return 0, 0, 0
        self._handle_recovery(db_name)

        tables = group_by_table(db_name, columns)
        batch: list[dict] = []
        batch_columns = payloads = 0
        for table in tables:
            batch.append(table)
            batch_columns += len(table["columns"])
            if batch_columns >= PAYLOAD_MAX_COLUMNS:
                self._submit(batch)
                payloads += 1
                batch, batch_columns = [], 0
        if batch:
            self._submit(batch)
            payloads += 1
        return len(tables), len(columns), payloads

    def _handle_error(self, db_name: str, error: Exception) -> None:
        message = str(error)
        for event, markers, fix in SETUP_ERRORS:
            if not any(marker in message for marker in markers):
                continue
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

    def _handle_recovery(self, db_name: str) -> None:
        for event, failing in self._failing_dbs.items():
            if db_name in failing:
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


def parse_steps(steps: str | None) -> list[dict]:
    """Unpack the histogram steps the procedure packs as is_null:equal_rows:range_rows:distinct_range_rows."""
    parsed = []
    for packed in steps.split(",") if steps else []:
        is_null, equal_rows, range_rows, distinct_range_rows = packed.split(":")
        parsed.append(
            {
                "is_null": is_null == "1",
                "equal_rows": float(equal_rows),
                "range_rows": float(range_rows),
                "distinct_range_rows": float(distinct_range_rows),
            }
        )
    return parsed


def derive_column_statistics(column: dict, steps: list[dict]) -> dict:
    """
    Derive a column's statistics, in the shape of pg_stats, from its histogram steps. SQL Server keeps an exact count
    only for the value ending each of its up to 200 steps; the values inside a step only have an average count.
    """
    rows = float(column["rows"])
    value_steps = [step for step in steps if not step["is_null"]]
    n_distinct = float(sum(1 + float(step["distinct_range_rows"]) for step in value_steps))
    null_steps = [step for step in steps if step["is_null"]]
    if not column["is_nullable"]:
        # Sampled histograms don't add up to the rows exactly, which would otherwise look like a few NULLs.
        null_rows = 0.0
    elif null_steps:
        null_rows = sum(float(step["equal_rows"]) for step in null_steps)
    else:
        # Some histograms have no NULL step, so the NULLs are the rows the other steps don't cover. A histogram with
        # no steps at all, as when every value is NULL, covers none of them.
        value_rows = sum(float(step["equal_rows"]) + float(step["range_rows"]) for step in value_steps)
        null_rows = max(rows - value_rows, 0.0)
    null_rows = min(null_rows, rows)

    if column["fixed_width"] is not None:
        avg_width = float(column["fixed_width"])
    elif column["avg_width"] is not None and null_rows < rows:
        # DBCC's average counts NULLs as zero bytes; pg_stats averages over the non-NULL values.
        avg_width = float(column["avg_width"]) * rows / (rows - null_rows)
    else:
        avg_width = 0.0

    if column["is_unique"]:
        # A sampled histogram undercounts a unique column's values. As ANALYZE does when no value repeats, every
        # non-NULL row is a distinct value, and none is common.
        stored_n_distinct = -(1.0 - null_rows / rows)
    elif n_distinct > N_DISTINCT_SCALING_THRESHOLD * rows:
        # A negative n_distinct is a share of the rows, so it scales with the table.
        stored_n_distinct = -min(n_distinct / rows, 1.0)
    else:
        stored_n_distinct = n_distinct

    return {
        "schema_name": column["schema_name"],
        "table_name": column["table_name"],
        "column_name": column["column_name"],
        "stats_age": column["stats_age"],
        "avg_width": round(avg_width),
        "n_distinct": stored_n_distinct,
        "null_frac": null_rows / rows,
        "most_common_freqs": []
        if column["is_unique"]
        else most_common_freqs(value_steps, n_distinct, null_rows / rows, rows, float(column["rows_sampled"] or rows)),
    }


def most_common_freqs(
    value_steps: list[dict], n_distinct: float, null_frac: float, rows: float, rows_sampled: float
) -> list[float]:
    """
    Choose the common values as ANALYZE does for pg_stats, among the values ending a histogram step, and return each
    one's share of all rows, NULLs included, most common first.

    ANALYZE keeps every value it saw more than once when they're all the values there are, or when it read every row.
    Otherwise it keeps only those significantly more common than the values left out would be.
    """
    # Histogram counts are scaled up to the whole table; ANALYZE reasons in counts within its sample.
    sample_ratio = rows_sampled / rows
    repeated = sorted(
        (float(step["equal_rows"]) for step in value_steps if float(step["equal_rows"]) * sample_ratio > 1),
        reverse=True,
    )
    all_values = len(repeated) == len(value_steps) and all(
        float(step["distinct_range_rows"]) == 0 for step in value_steps
    )
    if all_values and len(repeated) <= MAX_COMMON_VALUES:
        kept = repeated
    else:
        kept = repeated[:MAX_COMMON_VALUES]
        if rows_sampled < rows:
            sample_counts = [equal_rows * sample_ratio for equal_rows in kept]
            kept = kept[: significant_common_values(sample_counts, n_distinct, null_frac, rows_sampled, rows)]
    return [equal_rows / rows for equal_rows in kept]


def significant_common_values(
    counts: list[float], n_distinct: float, null_frac: float, sample_rows: float, total_rows: float
) -> int:
    """
    Return how many of the most common values to keep, from their counts in the sample, most common first. A port
    of Postgres's analyze_mcv_list: the least common value is dropped until it's more common than it would be
    estimated to be without the list, by more than twice its sampling error.
    """
    num = len(counts)
    sum_count = sum(counts[: num - 1])
    while num > 0:
        # The selectivity the least common value would be given if it were left out of the list.
        selectivity = min(max(1.0 - sum_count / sample_rows - null_frac, 0.0), 1.0)
        other_distinct = n_distinct - (num - 1)
        if other_distinct > 1:
            selectivity /= other_distinct
        # The value's count in the sample follows a hypergeometric distribution.
        population_count = total_rows * counts[num - 1] / sample_rows
        variance = (
            sample_rows
            * population_count
            * (total_rows - population_count)
            * (total_rows - sample_rows)
            / (total_rows * total_rows * (total_rows - 1))
        )
        if counts[num - 1] > selectivity * sample_rows + 2 * math.sqrt(max(variance, 0.0)) + 0.5:
            break
        num -= 1
        if num > 0:
            sum_count -= counts[num - 1]
    return num


def group_by_table(db_name: str, columns: list[dict]) -> list[dict]:
    """
    Group per-column statistics into the per-table entries of the column_statistics payload. A table's stats_age is
    that of its oldest column statistics.
    """
    tables: dict[tuple[str, str], dict] = {}
    for column in columns:
        key = (column["schema_name"], column["table_name"])
        table = tables.get(key)
        if table is None:
            table = tables[key] = {
                "db": db_name,
                "schema": key[0],
                "table": key[1],
                "stats_age": 0,
                "columns": [],
                "version": 1,
            }
        table["stats_age"] = max(table["stats_age"], column["stats_age"])
        table["columns"].append(
            {
                "name": column["column_name"],
                "avg_width": column["avg_width"],
                "n_distinct": column["n_distinct"],
                "null_frac": column["null_frac"],
                "most_common_freqs": column["most_common_freqs"],
            }
        )
    return list(tables.values())
