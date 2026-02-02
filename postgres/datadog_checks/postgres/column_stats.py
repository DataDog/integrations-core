# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

import psycopg
from psycopg.rows import dict_row

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.health import HealthEvent, HealthStatus
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.config_models import InstanceConfig

from .util import payload_pg_version

# Query to collect column statistics from datadog.column_stats() function
COLUMN_STATS_QUERY = """
SELECT
    schemaname,
    tablename,
    attname,
    avg_width,
    n_distinct,
    null_frac
FROM datadog.column_stats()
ORDER BY schemaname, tablename, attname
"""

# Query to check if the column_stats function exists
CHECK_FUNCTION_EXISTS_QUERY = """
SELECT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'datadog'
    AND p.proname = 'column_stats'
)
"""


def agent_check_getter(self):
    return self._check


class PostgresColumnStatsCollector(DBMAsyncJob):
    """
    Collects column statistics from pg_stats via the datadog.column_stats() function.
    """

    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self.collection_interval = config.collect_column_stats.collection_interval
        self.max_tables = config.collect_column_stats.max_tables
        self.include_tables = config.collect_column_stats.include_tables or []
        self.exclude_tables = config.collect_column_stats.exclude_tables or []

        super(PostgresColumnStatsCollector, self).__init__(
            check,
            rate_limit=1 / float(self.collection_interval),
            run_sync=config.collect_column_stats.run_sync,
            enabled=config.collect_column_stats.enabled,
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="column-stats",
        )
        self._check = check
        self._config = config
        self.db_pool = self._check.db_pool
        self._compiled_patterns_cache: dict[str, re.Pattern] = {}
        self._tags_no_db: list[str] | None = None
        self.tags: list[str] | None = None
        self._function_exists: bool | None = None
        self._function_check_time: float = 0
        self._function_check_interval: float = 3600  # Re-check function existence every hour

    def _get_compiled_pattern(self, pattern_str: str) -> re.Pattern:
        """Get a compiled regex pattern from cache, compiling it if not already cached."""
        if pattern_str not in self._compiled_patterns_cache:
            self._compiled_patterns_cache[pattern_str] = re.compile(pattern_str)
        return self._compiled_patterns_cache[pattern_str]

    def _should_include_table(self, schema: str, table: str) -> bool:
        """Check if a table should be included based on include/exclude patterns."""
        full_name = f"{schema}.{table}"

        # Check exclude patterns first
        for pattern in self.exclude_tables:
            compiled = self._get_compiled_pattern(pattern)
            if compiled.search(full_name) or compiled.search(table):
                return False

        # If include patterns are specified, table must match at least one
        if self.include_tables:
            for pattern in self.include_tables:
                compiled = self._get_compiled_pattern(pattern)
                if compiled.search(full_name) or compiled.search(table):
                    return True
            return False

        return True

    def _check_function_exists(self) -> bool:
        """Check if the datadog.column_stats() function exists."""
        current_time = time.time()

        # Use cached result if within check interval
        if self._function_exists is not None and (current_time - self._function_check_time) < self._function_check_interval:
            return self._function_exists

        try:
            with self._check._get_main_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(CHECK_FUNCTION_EXISTS_QUERY)
                    result = cursor.fetchone()
                    self._function_exists = result[0] if result else False
                    self._function_check_time = current_time
                    return self._function_exists
        except Exception as e:
            self._log.warning("Failed to check if column_stats function exists: %s", e)
            return False

    def _emit_function_missing_health_event(self):
        """Emit a health event indicating the column_stats function is missing."""
        self._check.health.submit_health_event(
            name=HealthEvent.INITIALIZATION,
            status=HealthStatus.WARNING,
            cooldown_time=60 * 60 * 6,  # 6 hours
            data={
                "job_name": "column-stats",
                "message": "The datadog.column_stats() function does not exist. "
                           "Please create the function to enable column statistics collection.",
            },
        )

    def run_job(self):
        # Do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith("dd.internal")]
        self._tags_no_db = [t for t in self.tags if not t.startswith("db:")]
        self._collect_column_stats()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_column_stats(self):
        """Collect and submit column statistics."""
        if self._cancel_event.is_set():
            return

        # Check if the function exists
        if not self._check_function_exists():
            self._log.debug("datadog.column_stats() function does not exist, skipping collection")
            self._emit_function_missing_health_event()
            return

        try:
            column_stats = self._query_column_stats()
            if column_stats:
                self._submit_column_stats_events(column_stats)
        except Exception as e:
            self._log.error("Failed to collect column statistics: %s", e)
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def _query_column_stats(self) -> dict[tuple[str, str], list[dict]]:
        """
        Query column statistics from the database.
        Returns a dict mapping (schema, table) to list of column stats.
        """
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")

        stats_by_table: dict[tuple[str, str], list[dict]] = {}
        tables_seen: set[tuple[str, str]] = set()

        with self._check._get_main_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(COLUMN_STATS_QUERY)
                rows = cursor.fetchall()

                for row in rows:
                    schema = row['schemaname']
                    table = row['tablename']
                    key = (schema, table)

                    # Check if we've hit the table limit
                    if key not in tables_seen:
                        if len(tables_seen) >= self.max_tables:
                            self._log.debug(
                                "Reached max_tables limit (%d), skipping remaining tables",
                                self.max_tables,
                            )
                            break
                        tables_seen.add(key)

                    # Apply include/exclude filters
                    if not self._should_include_table(schema, table):
                        continue

                    if key not in stats_by_table:
                        stats_by_table[key] = []

                    stats_by_table[key].append({
                        'name': row['attname'],
                        'avg_width': row['avg_width'],
                        'n_distinct': row['n_distinct'],
                        'null_frac': row['null_frac'],
                    })

        self._log.debug(
            "Collected column statistics for %d tables (%d total columns)",
            len(stats_by_table),
            sum(len(cols) for cols in stats_by_table.values()),
        )
        return stats_by_table

    @tracked_method(agent_check_getter=agent_check_getter)
    def _submit_column_stats_events(self, stats_by_table: dict[tuple[str, str], list[dict]]):
        """Submit column statistics events, one per table."""
        for (schema, table), columns in stats_by_table.items():
            if self._cancel_event.is_set():
                self._log.debug("Job loop cancelled. Aborting event submission.")
                return

            event = {
                "host": self._check.reported_hostname,
                "database_instance": self._check.database_identifier,
                "agent_version": datadog_agent.get_version(),
                "dbms": "postgres",
                "dbm_type": "column_stats",
                "collection_interval": self.collection_interval,
                "dbms_version": payload_pg_version(self._check.version),
                "tags": self._tags_no_db,
                "timestamp": time.time() * 1000,
                "cloud_metadata": self._check.cloud_metadata,
                "version": 1,
                "schema": schema,
                "table": table,
                "columns": columns,
            }
            self._check.database_monitoring_column_stats(
                json.dumps(event, default=default_json_event_encoding)
            )

        self._log.debug("Submitted column statistics for %d tables", len(stats_by_table))
