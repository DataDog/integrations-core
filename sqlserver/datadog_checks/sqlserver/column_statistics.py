# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.health import SqlServerHealthEvent
from datadog_checks.sqlserver.utils import construct_use_statement, execute_query, raise_if_cancelled

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer

DEFAULT_COLLECTION_INTERVAL = 3600
DEFAULT_MAX_TABLES = 500
PAYLOAD_MAX_COLUMNS = 5_000
# The check's command_timeout (10s by default) is too short for the procedure on a large database. This matches the
# Postgres collector's statement timeout.
MAX_QUERY_DURATION_SECONDS = 60
KEY_PREFIX = "dbm-column-statistics-"

# The agent's login can't read statistics itself, since SQL Server treats them as table data. Customers install this
# procedure in each database; it runs as its owner and returns only counts and frequencies, never column values.
COLUMN_STATISTICS_QUERY = "EXEC datadog.column_statistics @max_tables = ?"

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
)


def agent_check_getter(self: SqlserverColumnStatisticsCollector) -> SQLServer:
    return self._check


class SqlserverColumnStatisticsCollector(DBMAsyncJob):
    """Collects column statistics, in the shape the Postgres integration sends from pg_stats."""

    def __init__(self, check: SQLServer, config: SQLServerConfig):
        column_statistics_config = config.column_statistics_config
        self.collection_interval = column_statistics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        self._max_tables = int(column_statistics_config.get('max_tables', DEFAULT_MAX_TABLES))
        # The databases currently failing each way, so each warning and health event fires once and recovery is
        # reported when the last one is fixed.
        self._failing_dbs: dict[SqlServerHealthEvent, set[str]] = {event: set() for event, _, _ in SETUP_ERRORS}
        super().__init__(
            check,
            run_sync=is_affirmative(column_statistics_config.get('run_sync', False)),
            enabled=is_affirmative(column_statistics_config.get('enabled', False)),
            expected_db_exceptions=(),
            min_collection_interval=config.min_collection_interval,
            dbms=check.dbms,
            rate_limit=1 / float(self.collection_interval),
            job_name="column-statistics",
        )

    def shutdown(self) -> None:
        self._check = None

    def run_job(self) -> None:
        self.collect()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect(self) -> None:
        started = time.time()
        tables = columns = 0
        status = "success"
        try:
            with self._check.connection.open_managed_default_connection(KEY_PREFIX):
                # The driver applies the timeout to cursors created after it's set.
                self._check.connection.set_command_timeout(KEY_PREFIX, MAX_QUERY_DURATION_SECONDS)
                with self._check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
                    for db_name in self._check.get_databases():
                        raise_if_cancelled(self._cancel_event)
                        db_tables, db_columns = self._collect_database(cursor, db_name)
                        tables += db_tables
                        columns += db_columns
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

    def _collect_database(self, cursor, db_name: str) -> tuple[int, int]:
        try:
            cursor.execute(construct_use_statement(db_name))
            rows = execute_query(COLUMN_STATISTICS_QUERY, cursor, parameters=(self._max_tables,))
        except Exception as e:
            self._handle_error(db_name, e)
            return 0, 0
        self._handle_recovery(db_name)

        tables = group_by_table(db_name, rows)
        batch: list[dict] = []
        batch_columns = 0
        for table in tables:
            batch.append(table)
            batch_columns += len(table["columns"])
            if batch_columns >= PAYLOAD_MAX_COLUMNS:
                self._submit(batch)
                batch, batch_columns = [], 0
        if batch:
            self._submit(batch)
        return len(tables), len(rows)

    def _handle_error(self, db_name: str, error: Exception) -> None:
        message = str(error)
        for event, markers, fix in SETUP_ERRORS:
            if not any(marker in message for marker in markers):
                continue
            if db_name not in self._failing_dbs[event]:
                self._failing_dbs[event].add(db_name)
                self._log.warning(
                    "Can't run datadog.column_statistics in database '%s' (%s); %s: "
                    "https://docs.datadoghq.com/database_monitoring/setup_sql_server/",
                    db_name,
                    message,
                    fix,
                )
                self._check.health.submit_health_event(name=event, status=HealthStatus.WARNING)
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


def group_by_table(db_name: str, rows: list[dict]) -> list[dict]:
    """
    Group the procedure's per-column rows into the per-table entries of the column_statistics payload. A table's
    stats_age is that of its oldest column statistics.
    """
    tables: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["schema_name"], row["table_name"])
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
        table["stats_age"] = max(table["stats_age"], row["stats_age"])
        freqs = row["most_common_freqs"]
        table["columns"].append(
            {
                "name": row["column_name"],
                "avg_width": round(row["avg_width"] or 0),
                "n_distinct": float(row["n_distinct"] or 0),
                "null_frac": float(row["null_frac"] or 0),
                "most_common_freqs": [float(f) for f in freqs.split(",")] if freqs else [],
            }
        )
    return list(tables.values())
