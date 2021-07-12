# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import copy
import time

import psycopg2
import psycopg2.extras
from cachetools import TTLCache

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, resolve_db_host
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


DEFAULT_COLLECTION_INTERVAL = 10


class PostgresStatementMetrics(DBMAsyncJob):
    """Collects telemetry for SQL statements"""

    def __init__(self, check, config, shutdown_callback):
        collection_interval = float(
            config.statement_metrics_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        super(PostgresStatementMetrics, self).__init__(
            check,
            run_sync=is_affirmative(config.statement_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(config.statement_metrics_config.get('enabled', True)),
            expected_db_exceptions=(psycopg2.errors.DatabaseError,),
            min_collection_interval=config.min_collection_interval,
            config_host=config.host,
            dbms="postgres",
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
            shutdown_callback=shutdown_callback,
        )
        self._config = config
        self._state = StatementMetrics()
        self._stat_column_cache = []
        self._obfuscate_options = json.dumps(
            {'quantize_sql_tables': self._config.obfuscator_options.get('quantize_sql_tables', False)}
        )
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=config.full_statement_text_cache_max_size,
            ttl=60 * 60 / config.full_statement_text_samples_per_hour_per_query,
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

    def _get_pg_stat_statements_columns(self):
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
        cursor = self._check._get_db(self._config.dbname).cursor()
        self._execute_query(cursor, query, params=(self._config.dbname,))
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []
        self._stat_column_cache = col_names
        return col_names

    def _db_hostname_cached(self):
        if self._db_hostname:
            return self._db_hostname
        self._db_hostname = resolve_db_host(self._config.host)
        return self._db_hostname

    def run_job(self):
        self._tags_no_db = [t for t in self._tags if not t.startswith('db:')]
        self.collect_per_statement_metrics()

    def collect_per_statement_metrics(self):
        # exclude the default "db" tag from statement metrics & FQT events because this data is collected from
        # all databases on the host. For metrics the "db" tag is added during ingestion based on which database
        # each query came from.
        try:
            rows = self._collect_metrics_rows()
            if not rows:
                return
            for event in self._rows_to_fqt_events(rows):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
            # truncate query text to the maximum length supported by metrics tags
            for row in rows:
                row['query'] = row['query'][0:200]
            payload = {
                'host': self._db_hostname_cached(),
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._config.min_collection_interval,
                'tags': self._tags_no_db,
                'postgres_rows': rows,
                'postgres_version': 'v{major}.{minor}.{patch}'.format(
                    major=self._check._version.major, minor=self._check._version.minor, patch=self._check._version.patch
                ),
            }
            self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        except Exception:
            self._log.exception('Unable to collect statement metrics due to an error')
            return []

    def _load_pg_stat_statements(self):
        try:
            available_columns = set(self._get_pg_stat_statements_columns())
            missing_columns = PG_STAT_STATEMENTS_REQUIRED_COLUMNS - available_columns
            if len(missing_columns) > 0:
                self._log.warning(
                    'Unable to collect statement metrics because required fields are unavailable: %s',
                    ', '.join(list(missing_columns)),
                )
                self._check.count(
                    "dd.postgres.statement_metrics.error",
                    1,
                    tags=self._tags + ["error:database-missing_pg_stat_statements_required_columns"],
                )
                return []

            query_columns = sorted(list(available_columns & PG_STAT_ALL_DESIRED_COLUMNS))
            params = ()
            filters = ""
            if self._config.dbstrict:
                filters = "AND pg_database.datname = %s"
                params = (self._config.dbname,)
            return self._execute_query(
                self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor),
                STATEMENTS_QUERY.format(
                    cols=', '.join(query_columns),
                    pg_stat_statements_view=self._config.pg_stat_statements_view,
                    filters=filters,
                    limit=DEFAULT_STATEMENTS_LIMIT,
                ),
                params=params,
            )
        except psycopg2.Error as e:
            error_tag = "error:database-{}".format(type(e).__name__)

            if (
                isinstance(e, psycopg2.errors.ObjectNotInPrerequisiteState)
            ) and 'pg_stat_statements must be loaded' in str(e.pgerror):
                error_tag = "error:database-{}-pg_stat_statements_not_enabled".format(type(e).__name__)
                self._log.warning(
                    "Unable to collect statement metrics because pg_stat_statements is not installed "
                    "in this database"
                )
            else:
                self._log.warning("Unable to collect statement metrics because of an error running queries: %s", e)

            self._check.count("dd.postgres.statement_metrics.error", 1, tags=self._tags + [error_tag])

            return []

    def _collect_metrics_rows(self):
        rows = self._load_pg_stat_statements()

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
                obfuscated_statement = datadog_agent.obfuscate_sql(row['query'], self._obfuscate_options)
            except Exception as e:
                # obfuscation errors are relatively common so only log them during debugging
                self._log.debug("Failed to obfuscate query '%s': %s", row['query'], e)
                continue

            normalized_row['query'] = obfuscated_statement
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_statement)
            normalized_rows.append(normalized_row)

        return normalized_rows

    def _rows_to_fqt_events(self, rows):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            row_tags = self._tags_no_db + [
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
