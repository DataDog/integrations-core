# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import copy
import time

import psycopg2
import psycopg2.extras
from cachetools import TTLCache

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
  AND query NOT LIKE 'EXPLAIN %%'
  {filters}
  LIMIT {limit}
"""

DEFAULT_STATEMENTS_LIMIT = 10000

# Required columns for the check to run
PG_STAT_STATEMENTS_REQUIRED_COLUMNS = frozenset({'calls', 'query', 'rows'})

PG_STAT_STATEMENTS_METRICS_COLUMNS = frozenset(
    {
        'calls',
        'rows',
        'total_time',
        'total_exec_time',
        'shared_blks_hit',
        'shared_blks_read',
        'shared_blks_dirtied',
        'shared_blks_written',
        'local_blks_hit',
        'local_blks_read',
        'local_blks_dirtied',
        'local_blks_written',
        'temp_blks_read',
        'temp_blks_written',
    }
)

PG_STAT_STATEMENTS_TAG_COLUMNS = frozenset(
    {
        'datname',
        'rolname',
        'query',
    }
)

PG_STAT_STATEMENTS_OPTIONAL_COLUMNS = frozenset({'queryid'})

PG_STAT_ALL_DESIRED_COLUMNS = (
    PG_STAT_STATEMENTS_METRICS_COLUMNS | PG_STAT_STATEMENTS_TAG_COLUMNS | PG_STAT_STATEMENTS_OPTIONAL_COLUMNS
)


def _row_key(row):
    """
    :param row: a normalized row from pg_stat_statements
    :return: a tuple uniquely identifying this row
    """
    return row['query_signature'], row['datname'], row['rolname']


class PostgresStatementMetrics(object):
    """Collects telemetry for SQL statements"""

    def __init__(self, check, config):
        self._check = check
        self._config = config
        self._db_hostname = None
        self._log = get_check_logger()
        self._state = StatementMetrics()
        self._stat_column_cache = []
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self._config.full_statement_text_cache_max_size,
            ttl=60 * 60 / self._config.full_statement_text_samples_per_hour_per_query,
        )

    def _execute_query(self, cursor, query, params=()):
        try:
            self._log.debug("Running query [%s] %s", query, params)
            cursor.execute(query, params)
            return cursor.fetchall()
        except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
            # A failed query could've derived from incorrect columns within the cache. It's a rare edge case,
            # but the next time the query is run, it will retrieve the correct columns.
            self._stat_column_cache = []
            self._log.warning('Statement-level metrics are unavailable: %s', e)
            return []

    def _get_pg_stat_statements_columns(self, db):
        """
        Load the list of the columns available under the `pg_stat_statements` table. This must be queried because
        version is not a reliable way to determine the available columns on `pg_stat_statements`. The database can
        be upgraded without upgrading extensions, even when the extension is included by default.
        """
        if self._stat_column_cache:
            return self._stat_column_cache

        # Querying over '*' with limit 0 allows fetching only the column names from the cursor without data
        query = STATEMENTS_QUERY.format(
            cols='*', pg_stat_statements_view=self._config.pg_stat_statements_view, limit=0, filters=""
        )
        cursor = db.cursor()
        self._execute_query(cursor, query, params=(self._config.dbname,))
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []
        self._stat_column_cache = col_names
        return col_names

    def _db_hostname_cached(self):
        if self._db_hostname:
            return self._db_hostname
        self._db_hostname = resolve_db_host(self._config.host)
        return self._db_hostname

    def collect_per_statement_metrics(self, db, db_version, tags):
        # exclude the default "db" tag from statement metrics & FQT events because this data is collected from
        # all databases on the host. For metrics the "db" tag is added during ingestion based on which database
        # each query came from.
        tags = [t for t in tags if not t.startswith("db:")]
        try:
            rows = self._collect_metrics_rows(db)
            if not rows:
                return
            for event in self._rows_to_fqt_events(rows, tags):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
            # truncate query text to the maximum length supported by metrics tags
            for row in rows:
                row['query'] = row['query'][0:200]
            payload = {
                'host': self._db_hostname_cached(),
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._config.min_collection_interval,
                'tags': tags,
                'postgres_rows': rows,
                'postgres_version': 'v{major}.{minor}.{patch}'.format(
                    major=db_version.major, minor=db_version.minor, patch=db_version.patch
                ),
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

        query_columns = sorted(list(available_columns & PG_STAT_ALL_DESIRED_COLUMNS))
        params = ()
        filters = ""
        if self._config.dbstrict:
            filters = "AND pg_database.datname = %s"
            params = (self._config.dbname,)
        return self._execute_query(
            db.cursor(cursor_factory=psycopg2.extras.DictCursor),
            STATEMENTS_QUERY.format(
                cols=', '.join(query_columns),
                pg_stat_statements_view=self._config.pg_stat_statements_view,
                filters=filters,
                limit=DEFAULT_STATEMENTS_LIMIT,
            ),
            params=params,
        )

    def _collect_metrics_rows(self, db):
        rows = self._load_pg_stat_statements(db)

        rows = self._normalize_queries(rows)
        if not rows:
            return []

        available_columns = set(rows[0].keys())
        metric_columns = available_columns & PG_STAT_STATEMENTS_METRICS_COLUMNS
        rows = self._state.compute_derivative_rows(rows, metric_columns, key=_row_key)
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

    def _rows_to_fqt_events(self, rows, tags):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            row_tags = tags + [
                "db:{}".format(row['datname']),
                "rolname:{}".format(row['rolname']),
            ]
            yield {
                "timestamp": time.time() * 1000,
                "host": self._db_hostname_cached(),
                "ddsource": "postgres",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                "db": {
                    "instance": row['datname'],
                    "query_signature": row['query_signature'],
                    "statement": row['query'],
                },
                "postgres": {
                    "datname": row["datname"],
                    "rolname": row["rolname"],
                },
            }
