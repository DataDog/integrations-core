# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
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

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.config_models import InstanceConfig

from .util import payload_pg_version


COLUMN_STATS_QUERY = """\
WITH changed AS (
    SELECT c.oid AS relid, n.nspname AS schemaname, c.relname AS tablename
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_stat_all_tables s ON s.relid = c.oid
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND c.relkind = 'r'
      AND GREATEST(s.last_analyze, s.last_autoanalyze) > NOW() - INTERVAL '{collection_interval} seconds'
    ORDER BY GREATEST(s.last_analyze, s.last_autoanalyze) DESC NULLS LAST
    LIMIT {max_tables}
)
SELECT
    ch.schemaname,
    ch.tablename,
    s.attname,
    s.n_distinct,
    s.avg_width,
    s.null_frac,
    EXTRACT(EPOCH FROM (NOW() - st.last_analyze))::bigint AS last_analyze_age,
    EXTRACT(EPOCH FROM (NOW() - st.last_autoanalyze))::bigint AS last_autoanalyze_age,
    EXTRACT(EPOCH FROM (NOW() - st.last_vacuum))::bigint AS last_vacuum_age,
    EXTRACT(EPOCH FROM (NOW() - st.last_autovacuum))::bigint AS last_autovacuum_age,
    EXTRACT(EPOCH FROM (NOW() - GREATEST(st.last_analyze, st.last_autoanalyze)))::bigint AS stats_age
FROM datadog.column_stats() s
JOIN changed ch ON ch.schemaname = s.schemaname AND ch.tablename = s.tablename
JOIN pg_stat_all_tables st ON st.schemaname = ch.schemaname AND st.relname = ch.tablename
ORDER BY ch.schemaname, ch.tablename, s.attname
"""


def agent_check_getter(self):
    return self._check


class ColumnStatsCollector(DBMAsyncJob):
    """
    Collects column statistics from pg_stats via the datadog.column_stats() function.
    Results are grouped by table and submitted as column_stats events.
    """

    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self.collection_interval = config.collect_column_stats.collection_interval
        self.max_tables = config.collect_column_stats.max_tables
        self.include_tables = list(config.collect_column_stats.include_tables or [])
        self.exclude_tables = list(config.collect_column_stats.exclude_tables or [])
        self._compiled_patterns = {}

        super(ColumnStatsCollector, self).__init__(
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
        self._tags_no_db = None
        self.tags = None

    def _get_compiled_pattern(self, pattern_str):
        if pattern_str not in self._compiled_patterns:
            self._compiled_patterns[pattern_str] = re.compile(pattern_str)
        return self._compiled_patterns[pattern_str]

    def run_job(self):
        self.tags = [t for t in self._tags if not t.startswith("dd.internal")]
        self._tags_no_db = [t for t in self.tags if not t.startswith("db:")]
        self.collect_column_stats()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_column_stats(self):
        """Collect column statistics and submit as events."""
        rows = self._query_column_stats()
        if not rows:
            self._log.debug("No column stats rows returned")
            return

        # Group rows by (schema, table)
        tables = {}
        for row in rows:
            key = (row['schemaname'], row['tablename'])
            if key not in tables:
                tables[key] = {
                    'schema': row['schemaname'],
                    'table': row['tablename'],
                    'last_analyze_age': row.get('last_analyze_age'),
                    'last_autoanalyze_age': row.get('last_autoanalyze_age'),
                    'last_vacuum_age': row.get('last_vacuum_age'),
                    'last_autovacuum_age': row.get('last_autovacuum_age'),
                    'stats_age': row.get('stats_age'),
                    'columns': [],
                }
            tables[key]['columns'].append({
                'name': row['attname'],
                'avg_width': row.get('avg_width', 0),
                'n_distinct': row.get('n_distinct', 0),
                'null_frac': row.get('null_frac', 0),
            })

        # Apply include/exclude filters
        filtered_tables = self._apply_table_filters(tables)

        # Build column_stats list with version
        column_stats = []
        for table_data in filtered_tables.values():
            table_data['version'] = 1
            column_stats.append(table_data)

        if not column_stats:
            self._log.debug("No column stats after filtering")
            return

        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "dbms": "postgres",
            "dbms_version": payload_pg_version(self._check.version),
            "tags": self._tags_no_db,
            "cloud_metadata": self._check.cloud_metadata,
            "timestamp": time.time() * 1000,
            "dbm_type": "column_stats",
            "collection_interval": self.collection_interval,
            "column_stats": column_stats,
        }
        self._check.database_monitoring_column_stats(
            json.dumps(event, default=default_json_event_encoding)
        )
        self._log.debug("Submitted column stats event with %d tables", len(column_stats))

    def _query_column_stats(self):
        """Execute column stats query and return rows."""
        if self._cancel_event.is_set():
            self._log.debug("Column stats collection cancelled")
            return []
        try:
            with self._check._get_main_db() as conn:
                with conn.cursor(row_factory=dict_row) as cursor:
                    query = COLUMN_STATS_QUERY.format(
                        collection_interval=int(self.collection_interval),
                        max_tables=self.max_tables,
                    )
                    self._log.debug("Running column stats query")
                    cursor.execute(query)
                    return cursor.fetchall()
        except psycopg.errors.UndefinedFunction:
            self._log.warning(
                "datadog.column_stats() function not found. "
                "Please create the function as described in the documentation: "
                "https://docs.datadoghq.com/database_monitoring/setup_postgres/"
            )
            return []
        except psycopg.errors.InsufficientPrivilege:
            self._log.warning(
                "Insufficient privileges to execute datadog.column_stats(). "
                "Please check the function permissions."
            )
            return []

    def _apply_table_filters(self, tables):
        """Apply include/exclude regex filters to tables."""
        if not self.include_tables and not self.exclude_tables:
            return tables

        filtered = {}
        for key, table_data in tables.items():
            table_name = table_data['table']

            # Check exclude patterns first
            excluded = False
            for pattern in self.exclude_tables:
                if self._get_compiled_pattern(pattern).search(table_name):
                    excluded = True
                    break

            if excluded:
                continue

            # Check include patterns (if any specified, table must match at least one)
            if self.include_tables:
                included = False
                for pattern in self.include_tables:
                    if self._get_compiled_pattern(pattern).search(table_name):
                        included = True
                        break
                if not included:
                    continue

            filtered[key] = table_data

        return filtered
