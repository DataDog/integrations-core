# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time

import psycopg
from psycopg.rows import dict_row

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from .health import PostgresHealthEvent
from .util import payload_pg_version

COLUMN_STATS_QUERY = """\
WITH tables AS (
    SELECT c.oid AS relid, n.nspname AS schemaname, c.relname AS tablename
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND c.relkind = 'r'
    ORDER BY n.nspname, c.relname
    LIMIT {max_tables}
),
column_data AS (
    SELECT
        t.schemaname,
        t.tablename,
        json_build_object(
            'name', s.attname,
            'avg_width', s.avg_width,
            'n_distinct', s.n_distinct,
            'null_frac', s.null_frac
        ) AS col,
        EXTRACT(EPOCH FROM (NOW() - st.last_analyze))::bigint AS last_analyze_age,
        EXTRACT(EPOCH FROM (NOW() - st.last_autoanalyze))::bigint AS last_autoanalyze_age,
        EXTRACT(EPOCH FROM (NOW() - st.last_vacuum))::bigint AS last_vacuum_age,
        EXTRACT(EPOCH FROM (NOW() - st.last_autovacuum))::bigint AS last_autovacuum_age,
        EXTRACT(EPOCH FROM (NOW() - GREATEST(st.last_analyze, st.last_autoanalyze)))::bigint AS stats_age
    FROM datadog.column_stats() s
    JOIN tables t ON t.schemaname = s.schemaname AND t.tablename = s.tablename
    JOIN pg_stat_all_tables st ON st.schemaname = t.schemaname AND st.relname = t.tablename
)
SELECT
    schemaname,
    tablename,
    json_agg(col ORDER BY col->>'name') AS columns,
    (array_agg(last_analyze_age))[1] AS last_analyze_age,
    (array_agg(last_autoanalyze_age))[1] AS last_autoanalyze_age,
    (array_agg(last_vacuum_age))[1] AS last_vacuum_age,
    (array_agg(last_autovacuum_age))[1] AS last_autovacuum_age,
    (array_agg(stats_age))[1] AS stats_age
FROM column_data
GROUP BY schemaname, tablename
ORDER BY schemaname, tablename
"""


PAYLOAD_MAX_COLUMNS = 20_000


class PostgresColumnStatsCollectorConfig:
    def __init__(self):
        self.collection_interval = 14400
        self.max_tables = 500
        self.max_query_duration = 60
        self.include_tables: list[str] = []
        self.exclude_tables: list[str] = []


class PostgresColumnStatsCollector:
    """Collects column statistics from pg_stats via the datadog.column_stats() function."""

    def __init__(self, check: PostgreSql, cancel_event):
        self._check = check
        self._log = check.log
        self._cancel_event = cancel_event
        self._config = PostgresColumnStatsCollectorConfig()
        self._config.collection_interval = check._config.collect_column_stats.collection_interval
        self._config.max_tables = check._config.collect_column_stats.max_tables
        self._config.max_query_duration = int(check._config.collect_column_stats.max_query_duration)
        self._config.include_tables = list(check._config.collect_column_stats.include_tables or [])
        self._config.exclude_tables = list(check._config.collect_column_stats.exclude_tables or [])
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._function_not_found = False
        self._insufficient_privilege = False
        self._reset()

    def _reset(self):
        self._collection_started_at = None
        self._total_tables_count = 0
        self._total_columns_count = 0
        self._payloads_count = 0
        self._queued_tables = []
        self._queued_columns_count = 0

    def _get_compiled_pattern(self, pattern_str: str) -> re.Pattern:
        if pattern_str not in self._compiled_patterns:
            self._compiled_patterns[pattern_str] = re.compile(pattern_str)
        return self._compiled_patterns[pattern_str]

    @property
    def _base_event(self):
        return {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "dbms": "postgres",
            "dbms_version": payload_pg_version(self._check.version),
            "cloud_metadata": self._check.cloud_metadata,
            "dbm_type": "column_stats",
            "collection_interval": self._config.collection_interval,
        }

    def _get_databases(self):
        if self._check.autodiscovery:
            autodiscovery_databases = self._check.autodiscovery.get_items()
            if autodiscovery_databases:
                return list(autodiscovery_databases)
        return [self._check._config.dbname]

    def collect_column_stats(self, tags_no_db: list[str]) -> bool:
        """Collect column statistics across all discovered databases."""
        status = "success"
        try:
            self._collection_started_at = time.time() * 1000

            if self._cancel_event.is_set():
                self._log.debug("Column stats collection cancelled")
                return True

            databases = self._get_databases()
            self._log.debug("Collecting column stats for %d databases", len(databases))

            for db_name in databases:
                if self._cancel_event.is_set():
                    self._log.debug("Column stats collection cancelled")
                    break
                self._collect_for_database(db_name, tags_no_db)

            if self._queued_tables:
                self._flush(tags_no_db)

            self._log.debug(
                "Submitted column stats: %d tables, %d columns, %d payloads across %d databases",
                self._total_tables_count,
                self._total_columns_count,
                self._payloads_count,
                len(databases),
            )
            return True
        except Exception as e:
            status = "error"
            self._log.error("Error collecting column stats: %s", e)
            raise
        finally:
            elapsed = (time.time() * 1000) - self._collection_started_at if self._collection_started_at else 0
            tags = self._check.tags + ["status:" + status]
            self._check.histogram(
                "dd.postgres.column_stats.time",
                elapsed,
                tags=tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.postgres.column_stats.tables_count",
                self._total_tables_count,
                tags=tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.postgres.column_stats.columns_count",
                self._total_columns_count,
                tags=tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.postgres.column_stats.payloads_count",
                self._payloads_count,
                tags=tags,
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._reset()

    def _collect_for_database(self, db_name: str, tags_no_db: list[str]):
        try:
            with self._check.db_pool.get_connection(db_name) as conn:
                with conn.cursor(row_factory=dict_row) as cursor:
                    query = COLUMN_STATS_QUERY.format(
                        max_tables=self._config.max_tables,
                    )
                    cursor.execute(f"SET statement_timeout = '{self._config.max_query_duration}s'")
                    cursor.execute(query)

                    self._handle_recovery()

                    row = cursor.fetchone()
                    while row:
                        table_data = self._map_row(db_name, row)
                        if self._table_matches_filters(table_data['table']):
                            table_data['version'] = 1
                            num_columns = len(table_data['columns'])
                            self._queued_tables.append(table_data)
                            self._queued_columns_count += num_columns
                            self._total_tables_count += 1
                            self._total_columns_count += num_columns
                        row = cursor.fetchone()
                        if self._queued_columns_count >= PAYLOAD_MAX_COLUMNS:
                            self._flush(tags_no_db)

        except psycopg.errors.UndefinedFunction:
            if not self._function_not_found:
                self._function_not_found = True
                self._log.warning(
                    "datadog.column_stats() function not found in database '%s'. "
                    "Please create the function as described in the documentation: "
                    "https://docs.datadoghq.com/database_monitoring/setup_postgres/",
                    db_name,
                )
                self._check.health.submit_health_event(
                    name=PostgresHealthEvent.COLUMN_STATS_FUNCTION_NOT_FOUND,
                    status=HealthStatus.WARNING,
                )
        except psycopg.errors.InsufficientPrivilege:
            if not self._insufficient_privilege:
                self._insufficient_privilege = True
                self._log.warning(
                    "Insufficient privileges to execute datadog.column_stats() in database '%s'. "
                    "Please check the function permissions.",
                    db_name,
                )
                self._check.health.submit_health_event(
                    name=PostgresHealthEvent.COLUMN_STATS_INSUFFICIENT_PRIVILEGE,
                    status=HealthStatus.WARNING,
                )
        except Exception:
            self._log.exception("Error collecting column stats for database '%s'", db_name)

    def _handle_recovery(self):
        if self._function_not_found:
            self._function_not_found = False
            self._log.info("datadog.column_stats() function is now available, resuming collection")
            self._check.health.submit_health_event(
                name=PostgresHealthEvent.COLUMN_STATS_FUNCTION_NOT_FOUND,
                status=HealthStatus.OK,
            )
        if self._insufficient_privilege:
            self._insufficient_privilege = False
            self._log.info("datadog.column_stats() privileges restored, resuming collection")
            self._check.health.submit_health_event(
                name=PostgresHealthEvent.COLUMN_STATS_INSUFFICIENT_PRIVILEGE,
                status=HealthStatus.OK,
            )

    def _map_row(self, db_name: str, row):
        return {
            'db': db_name,
            'schema': row['schemaname'],
            'table': row['tablename'],
            'last_analyze_age': row.get('last_analyze_age'),
            'last_autoanalyze_age': row.get('last_autoanalyze_age'),
            'last_vacuum_age': row.get('last_vacuum_age'),
            'last_autovacuum_age': row.get('last_autovacuum_age'),
            'stats_age': row.get('stats_age'),
            'columns': row.get('columns') or [],
        }

    def _flush(self, tags_no_db: list[str]):
        if self._queued_tables:
            event = self._base_event
            event["tags"] = tags_no_db
            event["timestamp"] = time.time() * 1000
            event["column_stats"] = self._queued_tables
            self._payloads_count += 1
            self._check.database_monitoring_column_stats(json.dumps(event, default=default_json_event_encoding))
            self._queued_tables = []
            self._queued_columns_count = 0

    def _table_matches_filters(self, table_name: str) -> bool:
        if not self._config.include_tables and not self._config.exclude_tables:
            return True

        for pattern in self._config.exclude_tables:
            if self._get_compiled_pattern(pattern).search(table_name):
                return False

        if self._config.include_tables:
            for pattern in self._config.include_tables:
                if self._get_compiled_pattern(pattern).search(table_name):
                    return True
            return False

        return True
