# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import copy
import time

import psycopg2
import psycopg2.extras

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import default_json_event_encoding, resolve_db_host
from datadog_checks.base.utils.serialization import json

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

STATEMENTS_QUERY = """
SELECT {cols}
  FROM {pg_stat_statements_view} as pg_stat_statements
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
  WHERE query != '<insufficient privilege>'
  {filters}
  LIMIT {limit}
"""

PG_STAT_STATEMENTS_COLUMN_QUERY = 'SELECT * FROM {pg_stat_statements_view}'

DEFAULT_STATEMENTS_LIMIT = 10000

# Required columns for the check to run
PG_STAT_STATEMENTS_REQUIRED_COLUMNS = frozenset({'calls', 'query', 'rows'})

PG_NON_MONOTONIC_COLUMNS = frozenset(
    {
        'rolname',
        'query',
        'datname',
        'queryid',
        'query_signature',
    }
)

PG_COLUMN_BLOCK_LIST = frozenset(
    {
        'oid',
        'stddev_time',
        'min_time',
        'max_time',
        'mean_time',
        'stddev_exec_time',
        'total_plan_time',
        'min_exec_time',
        'max_exec_time',
        'mean_exec_time',
    }
)


class PostgresStatementMetrics(object):
    """Collects telemetry for SQL statements"""

    def __init__(self, check, config):
        self._check = check
        self._config = config
        self._db_hostname = None
        self._log = get_check_logger()
        self._state = StatementMetrics()
        self._stat_column_cache = set()

    def _execute_query(self, cursor, query, params=()):
        try:
            self._log.debug("Running query [%s] %s", query, params)
            cursor.execute(query, params)
            return cursor.fetchall()
        except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
            self._log.warning('Statement-level metrics are unavailable: %s', e)
            return []

    def _get_pg_stat_statements_columns(self, db):
        """
        Load the list of the columns available under the `pg_stat_statements` table. This must be queried because
        version is not a reliable way to determine the available columns on `pg_stat_statements`. The database can
        be upgraded without upgrading extensions, even when the extension is included by default.
        """
        if len(self._stat_column_cache) == 0:
            stat_column_query = PG_STAT_STATEMENTS_COLUMN_QUERY.format(
                pg_stat_statements_view=self._config.pg_stat_statements_view
            )
            stat_column_cursor = db.cursor()
            self._execute_query(stat_column_cursor, stat_column_query, params=(self._config.dbname,))
            if not stat_column_cursor.description:
                self._log.exception("Failed to query pg stat statement columns")
            self._stat_column_cache = set([desc[0] for desc in stat_column_cursor.description])

        # Querying over '*' with limit 0 allows fetching only the column names from the cursor without data
        statements_query = STATEMENTS_QUERY.format(
            cols='*', pg_stat_statements_view=self._config.pg_stat_statements_view, limit=0, filters=""
        )
        statements_cursor = db.cursor()
        self._execute_query(statements_cursor, statements_query, params=(self._config.dbname,))
        if not statements_cursor.description:
            return None
        return [desc[0] for desc in statements_cursor.description if desc[0] not in PG_COLUMN_BLOCK_LIST]

    def _db_hostname_cached(self):
        if self._db_hostname:
            return self._db_hostname
        self._db_hostname = resolve_db_host(self._config.host)
        return self._db_hostname

    def collect_per_statement_metrics(self, db, db_version, tags):
        try:
            rows = self._collect_metrics_rows(db)
            if not rows:
                return
            postgres_version = '{major}.{minor}.{patch}'.format(
                major=db_version.major, minor=db_version.minor, patch=db_version.patch
            )
            payload = {
                'host': self._db_hostname_cached(),
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._config.min_collection_interval,
                'tags': tags,
                'postgres_rows': rows,
                'postgres_version': postgres_version,
            }
            self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        except Exception:
            db.rollback()
            self._log.exception('Unable to collect statement metrics due to an error')
            return []

    def _load_pg_stat_statements(self, db):
        available_columns = set(self._get_pg_stat_statements_columns(db))
        missing_columns = PG_STAT_STATEMENTS_REQUIRED_COLUMNS - available_columns
        if len(missing_columns) > 0:
            self._log.warning(
                'Unable to collect statement metrics because required fields are unavailable: %s',
                ', '.join(list(missing_columns)),
            )
            return []

        params = ()
        filters = ""
        if self._config.dbstrict:
            filters = "AND pg_database.datname = %s"
            params = (self._config.dbname,)
        return self._execute_query(
            db.cursor(cursor_factory=psycopg2.extras.DictCursor),
            STATEMENTS_QUERY.format(
                cols=', '.join(available_columns),
                pg_stat_statements_view=self._config.pg_stat_statements_view,
                filters=filters,
                limit=DEFAULT_STATEMENTS_LIMIT,
            ),
            params=params,
        )

    def _collect_metrics_rows(self, db):
        rows = self._load_pg_stat_statements(db)

        def row_keyfunc(row):
            return (row['query_signature'], row['datname'], row['rolname'])

        rows = self._normalize_queries(rows)
        if len(rows) == 0:
            return None

        available_columns = set(rows[0].keys()).intersection(self._stat_column_cache)
        metric_columns = available_columns.difference(PG_NON_MONOTONIC_COLUMNS)
        rows = self._state.compute_derivative_rows(rows, metric_columns, key=row_keyfunc)
        self._check.gauge('dd.postgres.queries.query_rows_raw', len(rows))

        return rows

    def _normalize_queries(self, rows):
        normalized_rows = []
        for row in rows:
            normalized_row = dict(copy.copy(row))
            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
            except Exception as e:
                # obfuscation errors are relatively common so only log them during debugging
                self._log.debug("Failed to obfuscate query '%s': %s", row['query'], e)
                continue

            normalized_row['query'] = obfuscated_statement
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_statement)
            normalized_rows.append(normalized_row)

        return normalized_rows
