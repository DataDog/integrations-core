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
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

from .util import DatabaseConfigurationError, warning_with_tags
from .version_utils import V9_4

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
  {extra_clauses}
"""

# Use pg_stat_statements(false) when available as an optimization to avoid pulling SQL text from disk
PG_STAT_STATEMENTS_COUNT_QUERY = "SELECT COUNT(*) FROM pg_stat_statements(false)"
PG_STAT_STATEMENTS_COUNT_QUERY_LT_9_4 = "SELECT COUNT(*) FROM pg_stat_statements"

# Required columns for the check to run
PG_STAT_STATEMENTS_REQUIRED_COLUMNS = frozenset({'calls', 'query', 'rows'})

PG_STAT_STATEMENTS_TIMING_COLUMNS = frozenset(
    {
        'blk_read_time',
        'blk_write_time',
    }
)

PG_STAT_STATEMENTS_METRICS_COLUMNS = (
    frozenset(
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
    | PG_STAT_STATEMENTS_TIMING_COLUMNS
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


def agent_check_getter(self):
    return self._check


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
            dbms="postgres",
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
            shutdown_callback=shutdown_callback,
        )
        self._check = check
        self._metrics_collection_interval = collection_interval
        self._pg_stat_statements_max_warning_threshold = config.statement_metrics_config.get(
            'pg_stat_statements_max_warning_threshold', 10000
        )
        self._config = config
        self._state = StatementMetrics()
        self._stat_column_cache = []
        self._track_io_timing_cache = None
        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))
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
            raise e

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
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
            cols='*', pg_stat_statements_view=self._config.pg_stat_statements_view, extra_clauses="LIMIT 0", filters=""
        )
        cursor = self._check._get_db(self._config.dbname).cursor()
        self._execute_query(cursor, query, params=(self._config.dbname,))
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []
        self._stat_column_cache = col_names
        return col_names

    def run_job(self):
        self._tags_no_db = [t for t in self._tags if not t.startswith('db:')]
        self.collect_per_statement_metrics()

    def _payload_pg_version(self):
        version = self._check.version
        if not version:
            return ""
        return 'v{major}.{minor}.{patch}'.format(major=version.major, minor=version.minor, patch=version.patch)

    @tracked_method(agent_check_getter=agent_check_getter)
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
            payload = {
                'host': self._check.resolved_hostname,
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._metrics_collection_interval,
                'tags': self._tags_no_db,
                'cloud_metadata': self._config.cloud_metadata,
                'postgres_rows': rows,
                'postgres_version': self._payload_pg_version(),
                'ddagentversion': datadog_agent.get_version(),
                "ddagenthostname": self._check.agent_hostname,
            }
            self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        except Exception:
            self._log.exception('Unable to collect statement metrics due to an error')
            return []

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_pg_stat_statements(self):
        try:
            available_columns = set(self._get_pg_stat_statements_columns())
            missing_columns = PG_STAT_STATEMENTS_REQUIRED_COLUMNS - available_columns
            if len(missing_columns) > 0:
                self._check.warning(
                    warning_with_tags(
                        "Unable to collect statement metrics because required fields are unavailable: %s.",
                        ', '.join(sorted(missing_columns)),
                        host=self._check.resolved_hostname,
                        dbname=self._config.dbname,
                    ),
                )
                self._check.count(
                    "dd.postgres.statement_metrics.error",
                    1,
                    tags=self._tags
                    + [
                        "error:database-missing_pg_stat_statements_required_columns",
                    ]
                    + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )
                return []

            desired_columns = PG_STAT_ALL_DESIRED_COLUMNS

            if self._check.pg_settings.get("track_io_timing") != "on":
                desired_columns -= PG_STAT_STATEMENTS_TIMING_COLUMNS

            pg_stat_statements_max = int(self._check.pg_settings.get("pg_stat_statements.max"))
            if pg_stat_statements_max > self._pg_stat_statements_max_warning_threshold:
                self._check.record_warning(
                    DatabaseConfigurationError.high_pg_stat_statements_max,
                    warning_with_tags(
                        "pg_stat_statements.max is set to %d which is higher than the supported "
                        "value of %d. This can have a negative impact on database and collection of "
                        "query metrics performance. Consider lowering the pg_stat_statements.max value to %d. "
                        "Alternatively, you may acknowledge the potential performance impact by increasing the "
                        "query_metrics.pg_stat_statements_max_warning_threshold to equal or greater than %d to "
                        "silence this warning. "
                        "See https://docs.datadoghq.com/database_monitoring/setup_postgres/"
                        "troubleshooting#%s for more details",
                        pg_stat_statements_max,
                        self._pg_stat_statements_max_warning_threshold,
                        self._pg_stat_statements_max_warning_threshold,
                        self._pg_stat_statements_max_warning_threshold,
                        DatabaseConfigurationError.high_pg_stat_statements_max.value,
                        host=self._check.resolved_hostname,
                        dbname=self._config.dbname,
                        code=DatabaseConfigurationError.high_pg_stat_statements_max.value,
                        value=pg_stat_statements_max,
                        threshold=self._pg_stat_statements_max_warning_threshold,
                    ),
                )

            query_columns = sorted(available_columns & desired_columns)
            params = ()
            filters = ""
            if self._config.dbstrict:
                filters = "AND pg_database.datname = %s"
                params = (self._config.dbname,)
            elif self._config.ignore_databases:
                filters = " AND " + " AND ".join(
                    "pg_database.datname NOT ILIKE %s" for _ in self._config.ignore_databases
                )
                params = params + tuple(self._config.ignore_databases)
            return self._execute_query(
                self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor),
                STATEMENTS_QUERY.format(
                    cols=', '.join(query_columns),
                    pg_stat_statements_view=self._config.pg_stat_statements_view,
                    filters=filters,
                    extra_clauses="",
                ),
                params=params,
            )
        except psycopg2.Error as e:
            error_tag = "error:database-{}".format(type(e).__name__)

            if (
                isinstance(e, psycopg2.errors.ObjectNotInPrerequisiteState)
            ) and 'pg_stat_statements must be loaded' in str(e.pgerror):
                error_tag = "error:database-{}-pg_stat_statements_not_loaded".format(type(e).__name__)
                self._check.record_warning(
                    DatabaseConfigurationError.pg_stat_statements_not_loaded,
                    warning_with_tags(
                        "Unable to collect statement metrics because pg_stat_statements "
                        "extension is not loaded in database '%s'. "
                        "See https://docs.datadoghq.com/database_monitoring/setup_postgres/"
                        "troubleshooting#%s for more details",
                        self._config.dbname,
                        DatabaseConfigurationError.pg_stat_statements_not_loaded.value,
                        host=self._check.resolved_hostname,
                        dbname=self._config.dbname,
                        code=DatabaseConfigurationError.pg_stat_statements_not_loaded.value,
                    ),
                )
            elif isinstance(e, psycopg2.errors.UndefinedTable) and 'pg_stat_statements' in str(e.pgerror):
                error_tag = "error:database-{}-pg_stat_statements_not_created".format(type(e).__name__)
                self._check.record_warning(
                    DatabaseConfigurationError.pg_stat_statements_not_created,
                    warning_with_tags(
                        "Unable to collect statement metrics because pg_stat_statements is not created "
                        "in database '%s'. See https://docs.datadoghq.com/database_monitoring/setup_postgres/"
                        "troubleshooting#%s for more details",
                        self._config.dbname,
                        DatabaseConfigurationError.pg_stat_statements_not_created.value,
                        host=self._check.resolved_hostname,
                        dbname=self._config.dbname,
                        code=DatabaseConfigurationError.pg_stat_statements_not_created.value,
                    ),
                )
            else:
                self._check.warning(
                    warning_with_tags(
                        "Unable to collect statement metrics because of an error running queries "
                        "in database '%s'. See https://docs.datadoghq.com/database_monitoring/troubleshooting for "
                        "help: %s",
                        self._config.dbname,
                        str(e),
                        host=self._check.resolved_hostname,
                        dbname=self._config.dbname,
                    ),
                )

            self._check.count(
                "dd.postgres.statement_metrics.error",
                1,
                tags=self._tags + [error_tag] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )

            return []

    @tracked_method(agent_check_getter=agent_check_getter)
    def _emit_pg_stat_statements_metrics(self):
        query = PG_STAT_STATEMENTS_COUNT_QUERY_LT_9_4 if self._check.version < V9_4 else PG_STAT_STATEMENTS_COUNT_QUERY
        try:
            rows = self._execute_query(
                self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor),
                query,
            )
            count = 0
            if rows:
                count = rows[0][0]
            self._check.gauge(
                "postgresql.pg_stat_statements.max",
                self._check.pg_settings.get("pg_stat_statements.max", 0),
                tags=self._tags,
                hostname=self._check.resolved_hostname,
            )
            self._check.count(
                "postgresql.pg_stat_statements.count",
                count,
                tags=self._tags,
                hostname=self._check.resolved_hostname,
            )
        except psycopg2.Error as e:
            self._log.warning("Failed to query for pg_stat_statements count: %s", e)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_metrics_rows(self):
        self._emit_pg_stat_statements_metrics()
        rows = self._load_pg_stat_statements()

        rows = self._normalize_queries(rows)
        if not rows:
            return []

        available_columns = set(rows[0].keys())
        metric_columns = available_columns & PG_STAT_STATEMENTS_METRICS_COLUMNS
        rows = self._state.compute_derivative_rows(rows, metric_columns, key=_row_key)
        self._check.gauge(
            'dd.postgres.queries.query_rows_raw',
            len(rows),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        return rows

    def _normalize_queries(self, rows):
        normalized_rows = []
        for row in rows:
            normalized_row = dict(copy.copy(row))
            try:
                statement = obfuscate_sql_with_metadata(row['query'], self._obfuscate_options)
            except Exception as e:
                if self._config.log_unobfuscated_queries:
                    self._log.warning("Failed to obfuscate query=[%s] | err=[%s]", row['query'], e)
                else:
                    self._log.debug("Failed to obfuscate query | err=[%s]", e)
                continue

            obfuscated_query = statement['query']
            normalized_row['query'] = obfuscated_query
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_query)
            metadata = statement['metadata']
            normalized_row['dd_tables'] = metadata.get('tables', None)
            normalized_row['dd_commands'] = metadata.get('commands', None)
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
                "host": self._check.resolved_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "postgres",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                "db": {
                    "instance": row['datname'],
                    "query_signature": row['query_signature'],
                    "statement": row['query'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                    },
                },
                "postgres": {
                    "datname": row["datname"],
                    "rolname": row["rolname"],
                },
            }
