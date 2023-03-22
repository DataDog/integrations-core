# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import re
import time
from enum import Enum
from typing import Dict, Optional, Tuple  # noqa: F401

import psycopg2
from cachetools import TTLCache
from six import PY2

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool
from datadog_checks.postgres.explain_parameterized_queries import ExplainParameterizedQueries

from .util import DatabaseConfigurationError, warning_with_tags
from .version_utils import V9_6, V10

# according to https://unicodebook.readthedocs.io/unicode_encodings.html, the max supported size of a UTF-8 encoded
# character is 6 bytes
MAX_CHARACTER_SIZE_IN_BYTES = 6

TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE = -1

SUPPORTED_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update', 'with'})

# columns from pg_stat_activity which correspond to attributes common to all databases and are therefore stored in
# under other standard keys
pg_stat_activity_sample_exclude_keys = {
    # we process & obfuscate this separately
    'query',
    # stored separately
    'application_name',
    'datname',
    'usename',
    'client_addr',
    'client_hostname',
    'client_port',
}

# enumeration of the columns we collect
PG_STAT_ACTIVITY_COLS = [
    "datid",
    "datname",
    "pid",
    "usesysid",
    "usename",
    "application_name",
    "client_addr",
    "client_hostname",
    "client_port",
    "backend_start",
    "xact_start",
    "query_start",
    "state_change",
    "wait_event_type",
    "wait_event",
    "state",
    "backend_xid",
    "backend_xmin",
    "query",
    "backend_type",
]

PG_BLOCKING_PIDS_FUNC = ",pg_blocking_pids(pid) as blocking_pids"
CURRENT_TIME_FUNC = "clock_timestamp() as now,"

PG_STAT_ACTIVITY_QUERY = re.sub(
    r'\s+',
    ' ',
    """
    SELECT {current_time_func} {pg_stat_activity_cols} {pg_blocking_func} FROM {pg_stat_activity_view}
    WHERE
        {backend_type_predicate}
        (coalesce(TRIM(query), '') != '' AND pid != pg_backend_pid() AND query_start IS NOT NULL {extra_filters})
""",
).strip()

PG_ACTIVE_CONNECTIONS_QUERY = re.sub(
    r'\s+',
    ' ',
    """
    SELECT application_name, state, usename, datname, count(*) as connections
    FROM {pg_stat_activity_view}
    WHERE pid != pg_backend_pid() AND client_port IS NOT NULL
    {extra_filters}
    GROUP BY application_name, state, usename, datname
""",
).strip()

EXPLAIN_VALIDATION_QUERY = "SELECT * FROM pg_stat_activity"


class StatementTruncationState(Enum):
    """
    Denotes the various possible states of a statement's truncation
    """

    truncated = 'truncated'
    not_truncated = 'not_truncated'
    unknown = 'unknown'


class DBExplainError(Enum):
    """
    Denotes the various reasons a query may not have an explain statement.
    """

    # may be due to a misconfiguration of the database during setup or the Agent is
    # not able to access the required function
    database_error = 'database_error'

    # datatype mismatch occurs when return type is not json, for instance when multiple queries are explained
    datatype_mismatch = 'datatype_mismatch'

    # this could be the result of a missing EXPLAIN function
    invalid_schema = 'invalid_schema'

    # a value retrieved from the EXPLAIN function could be invalid
    invalid_result = 'invalid_result'

    # some statements cannot be explained i.e AUTOVACUUM
    no_plans_possible = 'no_plans_possible'

    # there could be a problem with the EXPLAIN function (missing, invalid permissions, or an incorrect definition)
    failed_function = 'failed_function'

    # a truncated statement can't be explained
    query_truncated = "query_truncated"

    # connection error may be due to a misconfiguration during setup
    connection_error = 'connection_error'

    # clients using the extended query protocol or prepared statements can't be explained due to
    # the separation of the parsed query and raw bind parameters
    parameterized_query = 'parameterized_query'

    # search path may be different when the client executed a query from where we executed it.
    undefined_table = 'undefined_table'

    # the statement was explained with the prepared statement workaround
    explained_with_prepared_statement = 'explained_with_prepared_statement'


DEFAULT_COLLECTION_INTERVAL = 1
DEFAULT_ACTIVITY_COLLECTION_INTERVAL = 10


def agent_check_getter(self):
    return self._check


class PostgresStatementSamples(DBMAsyncJob):
    """
    Collects statement samples and execution plans.
    """

    def __init__(self, check, config, shutdown_callback):
        collection_interval = float(
            config.statement_samples_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL

        self._conn_pool = MultiDatabaseConnectionPool(check._new_connection)

        def shutdown_cb():
            self._conn_pool.close_all_connections()
            return shutdown_callback()

        super(PostgresStatementSamples, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=is_affirmative(config.statement_samples_config.get('run_sync', False)),
            enabled=is_affirmative(config.statement_samples_config.get('enabled', True)),
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg2.errors.DatabaseError,),
            job_name="query-samples",
            shutdown_callback=shutdown_cb,
        )
        self._check = check
        self._config = config
        self._conn_ttl_ms = self._config.idle_connection_timeout
        self._tags_no_db = None
        self._activity_last_query_start = None
        # The value is loaded when connecting to the main database
        self._explain_function = config.statement_samples_config.get('explain_function', 'datadog.explain_statement')
        self._explain_parameterized_queries = ExplainParameterizedQueries(check, config)
        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))

        self._collection_strategy_cache = TTLCache(
            maxsize=config.statement_samples_config.get('collection_strategy_cache_maxsize', 1000),
            ttl=config.statement_samples_config.get('collection_strategy_cache_ttl', 300),
        )

        self._explain_errors_cache = TTLCache(
            maxsize=config.statement_samples_config.get('explain_errors_cache_maxsize', 5000),
            # only try to re-explain invalid statements once per day
            ttl=config.statement_samples_config.get('explain_errors_cache_ttl', 24 * 60 * 60),
        )

        # explained_statements_ratelimiter: limit how often we try to re-explain the same query
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.statement_samples_config.get('explained_queries_cache_maxsize', 5000)),
            ttl=60 * 60 / int(config.statement_samples_config.get('explained_queries_per_hour_per_query', 60)),
        )

        # seen_samples_ratelimiter: limit the ingestion rate per (query_signature, plan_signature)
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            # assuming ~100 bytes per entry (query & plan signature, key hash, 4 pointers (ordered dict), expiry time)
            # total size: 10k * 100 = 1 Mb
            maxsize=int(config.statement_samples_config.get('seen_samples_cache_maxsize', 10000)),
            ttl=60 * 60 / int(config.statement_samples_config.get('samples_per_hour_per_query', 15)),
        )

        self._activity_coll_enabled = is_affirmative(self._config.statement_activity_config.get('enabled', True))
        # activity events cannot be reported more often than regular samples
        self._activity_coll_interval = max(
            self._config.statement_activity_config.get('collection_interval', DEFAULT_ACTIVITY_COLLECTION_INTERVAL),
            collection_interval,
        )
        self._activity_max_rows = self._config.statement_activity_config.get('payload_row_limit', 3500)
        # Keep track of last time we sent an activity event
        self._time_since_last_activity_event = 0
        self._pg_stat_activity_cols = None

    def _dbtags(self, db, *extra_tags):
        """
        Returns the default instance tags with the initial "db" tag replaced with the provided tag
        """
        t = ["db:" + db]
        if extra_tags:
            t.extend(extra_tags)
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_active_connections(self):
        start_time = time.time()
        extra_filters, params = self._get_extra_filters_and_params()
        query = PG_ACTIVE_CONNECTIONS_QUERY.format(
            pg_stat_activity_view=self._config.pg_stat_activity_view, extra_filters=extra_filters
        )
        with self._conn_pool.get_connection(self._config.dbname, ttl_ms=self._conn_ttl_ms).cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            self._log.debug("Running query [%s] %s", query, params)
            cursor.execute(query, params)
            rows = cursor.fetchall()

        self._report_check_hist_metrics(start_time, len(rows), "get_active_connections")
        self._log.debug("Loaded %s rows from %s", len(rows), self._config.pg_stat_activity_view)
        return [dict(row) for row in rows]

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_new_pg_stat_activity(self, available_activity_columns):
        start_time = time.time()
        extra_filters, params = self._get_extra_filters_and_params(filter_stale_idle_conn=True)
        report_activity = self._report_activity_event()
        cur_time_func = ""
        blocking_func = ""
        backend_type_predicate = ""
        if self._check.version.compare(V10) >= 0:
            backend_type_predicate = "backend_type != 'client backend' OR"
        # minimum version for pg_blocking_pids function is v9.6
        # only call pg_blocking_pids as often as we collect activity snapshots
        if self._check.version >= V9_6 and report_activity:
            blocking_func = PG_BLOCKING_PIDS_FUNC
        if report_activity:
            cur_time_func = CURRENT_TIME_FUNC
        query = PG_STAT_ACTIVITY_QUERY.format(
            backend_type_predicate=backend_type_predicate,
            current_time_func=cur_time_func,
            pg_stat_activity_cols=', '.join(available_activity_columns),
            pg_blocking_func=blocking_func,
            pg_stat_activity_view=self._config.pg_stat_activity_view,
            extra_filters=extra_filters,
        )
        with self._conn_pool.get_connection(self._config.dbname, ttl_ms=self._conn_ttl_ms).cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            self._log.debug("Running query [%s] %s", query, params)
            cursor.execute(query, params)
            rows = cursor.fetchall()
        self._report_check_hist_metrics(start_time, len(rows), "get_new_pg_stat_activity")
        self._log.debug("Loaded %s rows from %s", len(rows), self._config.pg_stat_activity_view)
        return rows

    def _get_pg_stat_activity_cols_cached(self, expected_cols):
        if self._pg_stat_activity_cols:
            return self._pg_stat_activity_cols

        self._pg_stat_activity_cols = self._get_available_activity_columns(expected_cols)
        return self._pg_stat_activity_cols

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_available_activity_columns(self, all_expected_columns):
        with self._conn_pool.get_connection(self._config.dbname, ttl_ms=self._conn_ttl_ms).cursor(
            cursor_factory=psycopg2.extras.DictCursor
        ) as cursor:
            cursor.execute(
                "select * from {pg_stat_activity_view} LIMIT 0".format(
                    pg_stat_activity_view=self._config.pg_stat_activity_view
                )
            )
            all_columns = {i[0] for i in cursor.description}
            available_columns = [c for c in all_expected_columns if c in all_columns]
            missing_columns = set(all_expected_columns) - set(available_columns)
            if missing_columns:
                self._log.debug("missing the following expected columns from pg_stat_activity: %s", missing_columns)
            self._log.debug("found available pg_stat_activity columns: %s", available_columns)
        return available_columns

    def _filter_and_normalize_statement_rows(self, rows):
        insufficient_privilege_count = 0
        total_count = 0
        normalized_rows = []
        for row in rows:
            total_count += 1
            if (not row['datname'] or not row['query']) and row.get(
                'backend_type', 'client backend'
            ) == 'client backend':
                continue
            query = row['query']
            if query == '<insufficient privilege>':
                insufficient_privilege_count += 1
                continue
            if self._activity_last_query_start is None or (
                row['query_start'] and row['query_start'] > self._activity_last_query_start
            ):
                self._activity_last_query_start = row['query_start']
            normalized_rows.append(self._normalize_row(row))
        if insufficient_privilege_count > 0:
            self._log.warning(
                "Insufficient privilege for %s/%s queries when collecting from %s.",
                insufficient_privilege_count,
                total_count,
                self._config.pg_stat_activity_view,
            )
            self._check.count(
                "dd.postgres.statement_samples.error",
                insufficient_privilege_count,
                tags=self._tags + ["error:insufficient-privilege"] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
        return normalized_rows

    def _normalize_row(self, row):
        normalized_row = dict(copy.copy(row))
        obfuscated_query = None
        backend_type = normalized_row.get('backend_type', 'client backend')
        try:
            if backend_type != 'client backend':
                obfuscated_query = backend_type
                normalized_row['query_signature'] = compute_sql_signature(backend_type)
            else:
                statement = obfuscate_sql_with_metadata(row['query'], self._obfuscate_options)
                obfuscated_query = statement['query']
                metadata = statement['metadata']
                normalized_row['query_signature'] = compute_sql_signature(obfuscated_query)
                normalized_row['dd_tables'] = metadata.get('tables', None)
                normalized_row['dd_commands'] = metadata.get('commands', None)
                normalized_row['dd_comments'] = metadata.get('comments', None)
        except Exception as e:
            if self._config.log_unobfuscated_queries:
                self._log.warning("Failed to obfuscate query=[%s] | err=[%s]", row['query'], e)
            else:
                self._log.debug("Failed to obfuscate query | err=[%s]", e)
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._dbtags(row['datname'], "error:sql-obfuscate") + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
        normalized_row['statement'] = obfuscated_query
        return normalized_row

    def _get_extra_filters_and_params(self, filter_stale_idle_conn=False):
        extra_filters = ""
        params = ()
        if self._config.dbstrict:
            extra_filters = " AND datname = %s"
            params = params + (self._config.dbname,)
        else:
            extra_filters = " AND " + " AND ".join("datname NOT ILIKE %s" for _ in self._config.ignore_databases)
            params = params + tuple(self._config.ignore_databases)
        if filter_stale_idle_conn and self._activity_last_query_start:
            # do not re-read old idle connections
            extra_filters = extra_filters + " AND NOT (query_start < %s AND state = 'idle')"
            params = params + (self._activity_last_query_start,)
        return extra_filters, params

    def _report_check_hist_metrics(self, start_time, row_len, method_name):
        self._check.histogram(
            "dd.postgres.{}.time".format(method_name),
            (time.time() - start_time) * 1000,
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.histogram(
            "dd.postgres.{}.rows".format(method_name),
            row_len,
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    def run_job(self):
        self._tags_no_db = [t for t in self._tags if not t.startswith('db:')]
        self._collect_statement_samples()
        self._conn_pool.prune_connections()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_statement_samples(self):
        start_time = time.time()
        pg_activity_cols = self._get_pg_stat_activity_cols_cached(PG_STAT_ACTIVITY_COLS)
        rows = self._get_new_pg_stat_activity(pg_activity_cols)
        rows = self._filter_and_normalize_statement_rows(rows)
        event_samples = self._collect_plans(rows)
        submitted_count = 0
        for e in event_samples:
            self._check.database_monitoring_query_sample(json.dumps(e, default=default_json_event_encoding))
            submitted_count += 1

        if self._report_activity_event():
            active_connections = self._get_active_connections()
            activity_event = self._create_activity_event(rows, active_connections)
            self._check.database_monitoring_query_activity(
                json.dumps(activity_event, default=default_json_event_encoding)
            )
            self._check.histogram(
                "dd.postgres.collect_activity_snapshot.time", (time.time() - start_time) * 1000, tags=self._tags
            )
        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            "dd.postgres.collect_statement_samples.time",
            elapsed_ms,
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.count(
            "dd.postgres.collect_statement_samples.events_submitted.count",
            submitted_count,
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.explained_statements_cache.len",
            len(self._explained_statements_ratelimiter),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_samples.explain_errors_cache.len",
            len(self._explain_errors_cache),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    @staticmethod
    def _to_active_session(row, track_activity_query_size):
        if (row.get('backend_type', 'client backend') != 'client backend') or (
            row['state'] is not None and row['state'] != 'idle'
        ):
            active_row = {key: val for key, val in row.items() if val is not None and key != 'query'}
            # Create an active_row, for each session by
            # 1. Removing all null key/value pairs and the original query
            # 2. if row['statement'] is none, replace with ERROR: failed to obfuscate so we can still collect activity
            active_row['query_truncated'] = PostgresStatementSamples._get_truncation_state(
                track_activity_query_size, row['query']
            ).value
            if row['statement'] is None:
                active_row['statement'] = "ERROR: failed to obfuscate"
            return active_row

    def _can_explain_statement(self, obfuscated_statement):
        if obfuscated_statement.startswith('SELECT {}'.format(self._explain_function)):
            return False
        if obfuscated_statement.startswith('autovacuum:'):
            return False
        if obfuscated_statement.split(' ', 1)[0].lower() not in SUPPORTED_EXPLAIN_STATEMENTS:
            return False
        return True

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_db_explain_setup_state(self, dbname):
        # type: (str) -> Tuple[Optional[DBExplainError], Optional[Exception]]
        try:
            self._check._get_db(dbname)
        except psycopg2.OperationalError as e:
            self._log.warning(
                "cannot collect execution plans due to failed DB connection to dbname=%s: %s", dbname, repr(e)
            )
            return DBExplainError.connection_error, e
        except psycopg2.DatabaseError as e:
            self._log.warning(
                "cannot collect execution plans due to a database error in dbname=%s: %s", dbname, repr(e)
            )
            return DBExplainError.database_error, e

        try:
            result = self._run_explain(dbname, EXPLAIN_VALIDATION_QUERY, EXPLAIN_VALIDATION_QUERY)
        except psycopg2.errors.InvalidSchemaName as e:
            self._log.warning("cannot collect execution plans due to invalid schema in dbname=%s: %s", dbname, repr(e))
            self._emit_run_explain_error(dbname, DBExplainError.invalid_schema, e)
            return DBExplainError.invalid_schema, e
        except psycopg2.errors.DatatypeMismatch as e:
            self._emit_run_explain_error(dbname, DBExplainError.datatype_mismatch, e)
            return DBExplainError.datatype_mismatch, e
        except psycopg2.DatabaseError as e:
            # if the schema is valid then it's some problem with the function (missing, or invalid permissions,
            # incorrect definition)
            self._emit_run_explain_error(dbname, DBExplainError.failed_function, e)
            self._check.record_warning(
                DatabaseConfigurationError.undefined_explain_function,
                warning_with_tags(
                    "Unable to collect execution plans in dbname=%s. Check that the function "
                    "%s exists in the database. See "
                    "https://docs.datadoghq.com/database_monitoring/setup_postgres/troubleshooting#%s "
                    "for more details: %s",
                    dbname,
                    self._explain_function,
                    DatabaseConfigurationError.undefined_explain_function.value,
                    str(e),
                    host=self._check.resolved_hostname,
                    dbname=dbname,
                    code=DatabaseConfigurationError.undefined_explain_function.value,
                ),
            )
            return DBExplainError.failed_function, e

        if not result:
            return DBExplainError.invalid_result, None

        return None, None

    def _get_db_explain_setup_state_cached(self, dbname):
        # type: (str) -> Tuple[DBExplainError, Exception]
        strategy_cache = self._collection_strategy_cache.get(dbname)
        if strategy_cache:
            db_explain_error, err = strategy_cache
            self._log.debug("using cached explain_setup_state for DB '%s': %s", dbname, db_explain_error)
            return db_explain_error, err

        db_explain_error, err = self._get_db_explain_setup_state(dbname)
        self._collection_strategy_cache[dbname] = (db_explain_error, err)
        self._log.debug("caching new explain_setup_state for DB '%s': %s", dbname, db_explain_error)

        return db_explain_error, err

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _run_explain(self, dbname, statement, obfuscated_statement):
        start_time = time.time()
        with self._conn_pool.get_connection(dbname, ttl_ms=self._conn_ttl_ms).cursor() as cursor:
            self._log.debug("Running query on dbname=%s: %s(%s)", dbname, self._explain_function, obfuscated_statement)
            cursor.execute(
                """SELECT {explain_function}($stmt${statement}$stmt$)""".format(
                    explain_function=self._explain_function, statement=statement
                )
            )
            result = cursor.fetchone()
            self._check.histogram(
                "dd.postgres.run_explain.time",
                (time.time() - start_time) * 1000,
                tags=self._dbtags(dbname) + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            if not result or len(result) < 1 or len(result[0]) < 1:
                return None
            return result[0][0]

    @tracked_method(agent_check_getter=agent_check_getter)
    def _run_and_track_explain(self, dbname, statement, obfuscated_statement, query_signature):
        plan_dict, explain_err_code, err_msg = self._run_explain_safe(
            dbname, statement, obfuscated_statement, query_signature
        )
        if explain_err_code and explain_err_code != DBExplainError.explained_with_prepared_statement:
            err_tag = "error:explain-{}".format(explain_err_code.value if explain_err_code else None)
            if err_msg:
                err_tag = err_tag + "-" + err_msg
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._dbtags(dbname, err_tag) + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
        return plan_dict, explain_err_code, err_msg

    def _run_explain_safe(self, dbname, statement, obfuscated_statement, query_signature):
        # type: (str, str, str, str) -> Tuple[Optional[Dict], Optional[DBExplainError], Optional[str]]
        if not self._can_explain_statement(obfuscated_statement):
            return None, DBExplainError.no_plans_possible, None

        track_activity_query_size = self._get_track_activity_query_size()

        if self._get_truncation_state(track_activity_query_size, statement) == StatementTruncationState.truncated:
            return (
                None,
                DBExplainError.query_truncated,
                "track_activity_query_size={}".format(track_activity_query_size),
            )

        db_explain_error, err = self._get_db_explain_setup_state_cached(dbname)
        if db_explain_error is not None:
            return None, db_explain_error, '{}'.format(type(err))

        cached_error_response = self._explain_errors_cache.get(query_signature)
        if cached_error_response:
            return cached_error_response

        try:
            return self._run_explain(dbname, statement, obfuscated_statement), None, None
        except psycopg2.errors.UndefinedParameter as e:
            self._log.debug(
                "Unable to collect execution plan, clients using the extended query protocol or prepared statements"
                " can't be explained due to the separation of the parsed query and raw bind parameters: %s",
                repr(e),
            )
            if is_affirmative(self._config.statement_samples_config.get('explain_parameterized_queries', False)):
                plan = self._explain_parameterized_queries.explain_statement(dbname, statement, obfuscated_statement)
                if plan:
                    return plan, DBExplainError.explained_with_prepared_statement, None
            error_response = None, DBExplainError.parameterized_query, '{}'.format(type(e))
            self._explain_errors_cache[query_signature] = error_response
            self._emit_run_explain_error(dbname, DBExplainError.parameterized_query, e)
            return error_response
        except psycopg2.errors.UndefinedTable as e:
            self._log.debug("Failed to collect execution plan: %s", repr(e))
            error_response = None, DBExplainError.undefined_table, '{}'.format(type(e))
            self._explain_errors_cache[query_signature] = error_response
            self._emit_run_explain_error(dbname, DBExplainError.undefined_table, e)
            return error_response
        except psycopg2.errors.DatabaseError as e:
            self._log.debug("Failed to collect execution plan: %s", repr(e))
            error_response = None, DBExplainError.database_error, '{}'.format(type(e))
            self._emit_run_explain_error(dbname, DBExplainError.database_error, e)
            if isinstance(e, psycopg2.errors.ProgrammingError) and not isinstance(
                e, psycopg2.errors.InsufficientPrivilege
            ):
                # ProgrammingError is things like InvalidName, InvalidSchema, SyntaxError
                # we don't want to cache things like permission errors for a very long time because they can be fixed
                # dynamically by the user. the goal here is to cache only those queries which there is no reason to
                # retry
                self._explain_errors_cache[query_signature] = error_response
            return error_response

    def _emit_run_explain_error(self, dbname, err_code, err):
        # type: (str, DBExplainError, Exception) -> None
        self._check.count(
            "dd.postgres.run_explain.error",
            1,
            tags=self._dbtags(dbname, "error:explain-{}-{}".format(err_code.value, type(err)))
            + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_plan_for_statement(self, row):
        # limit the rate of explains done to the database
        cache_key = (row['datname'], row['query_signature'])
        if not self._explained_statements_ratelimiter.acquire(cache_key):
            return None

        # Plans have several important signatures to tag events with. Note that for postgres, the
        # query_signature and resource_hash will be the same value.
        # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
        # - `resource_hash` - hash computed off the raw sql text to match apm resources
        # - `query_signature` - hash computed from the raw sql text to match query metrics
        plan_dict, explain_err_code, err_msg = self._run_and_track_explain(
            row['datname'], row['query'], row['statement'], row['query_signature']
        )
        collection_errors = None
        if explain_err_code:
            collection_errors = [{'code': explain_err_code.value, 'message': err_msg if err_msg else None}]

        plan, normalized_plan, obfuscated_plan, plan_signature = None, None, None, None
        if plan_dict:
            plan = json.dumps(plan_dict)
            # if we're using the orjson implementation then json.dumps returns bytes
            plan = plan.decode('utf-8') if isinstance(plan, bytes) else plan
            try:
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)
                obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
            except Exception as e:
                if self._config.log_unobfuscated_plans:
                    self._log.warning("Failed to obfuscate plan=[%s] | err=[%s]", plan, e)
                raise e

            plan_signature = compute_exec_plan_signature(normalized_plan)

        statement_plan_sig = (row['query_signature'], plan_signature)
        if self._seen_samples_ratelimiter.acquire(statement_plan_sig):
            event = {
                "host": self._check.resolved_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "postgres",
                "ddtags": ",".join(self._dbtags(row['datname'])),
                "timestamp": time.time() * 1000,
                "network": {
                    "client": {
                        "ip": row.get('client_addr', None),
                        "port": row.get('client_port', None),
                        "hostname": row.get('client_hostname', None),
                    }
                },
                "db": {
                    "instance": row.get('datname', None),
                    "plan": {
                        "definition": obfuscated_plan,
                        "signature": plan_signature,
                        "collection_errors": collection_errors,
                    },
                    "query_signature": row['query_signature'],
                    "resource_hash": row['query_signature'],
                    "application": row.get('application_name', None),
                    "user": row['usename'],
                    "statement": row['statement'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                        "comments": row['dd_comments'],
                    },
                    "query_truncated": self._get_truncation_state(
                        self._get_track_activity_query_size(), row['query']
                    ).value,
                },
                'postgres': {k: v for k, v in row.items() if k not in pg_stat_activity_sample_exclude_keys},
            }
            if row['state'] in {'idle', 'idle in transaction'}:
                if row['state_change'] and row['query_start']:
                    event['duration'] = (row['state_change'] - row['query_start']).total_seconds() * 1e9
                    # If the transaction is idle then we have a more specific "end time" than the current time at
                    # which we're collecting this event. According to the postgres docs, all of the timestamps in
                    # pg_stat_activity are `timestamp with time zone` so the timezone should always be present. However,
                    # if there is something wrong and it's missing then we can't use `state_change` for the timestamp
                    # of the event else we risk the timestamp being significantly off and the event getting dropped
                    # during ingestion.
                    if row['state_change'].tzinfo:
                        event['timestamp'] = get_timestamp(row['state_change']) * 1000
            return event
        return None

    def _collect_plans(self, rows):
        events = []
        for row in rows:
            try:
                if row['statement'] is None or row.get('backend_type', 'client backend') != 'client backend':
                    continue
                event = self._collect_plan_for_statement(row)
                if event:
                    events.append(event)
            except Exception:
                self._log.exception(
                    "Crashed trying to collect execution plan for statement in dbname=%s", row['datname']
                )
                self._check.count(
                    "dd.postgres.statement_samples.error",
                    1,
                    tags=self._tags + ["error:collect-plan-for-statement-crash"] + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )
        return events

    def _create_activity_event(self, rows, active_connections):
        self._time_since_last_activity_event = time.time()
        active_sessions = []
        for row in rows:
            active_row = self._to_active_session(row, self._get_track_activity_query_size())
            if active_row:
                active_sessions.append(active_row)
        if len(active_sessions) > self._activity_max_rows:
            active_sessions = self._truncate_activity_rows(active_sessions, self._activity_max_rows)
        event = {
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "postgres",
            "dbm_type": "activity",
            "collection_interval": self._activity_coll_interval,
            "ddtags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "postgres_activity": active_sessions,
            "postgres_connections": active_connections,
        }
        return event

    def _truncate_activity_rows(self, rows, row_limit):
        # sort first one transaction age, and then second on query age
        rows.sort(key=lambda r: (self._sort_key(r), r['query_start']))
        return rows[0:row_limit]

    def _sort_key(self, row):
        # xact_start is not always set in the activity row
        # as we filter out null values first
        if 'xact_start' in row:
            return row['xact_start']
        # otherwise primarily sort on query_start, which will always be set.
        return row['query_start']

    def _report_activity_event(self):
        # Only send an event if we are configured to do so, and
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_activity_event
        if elapsed_s < self._activity_coll_interval or not self._activity_coll_enabled:
            return False
        return True

    def _get_track_activity_query_size(self):
        return int(self._check.pg_settings.get("track_activity_query_size", TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE))

    @staticmethod
    def _get_truncation_state(track_activity_query_size, statement):
        # Only check is a statement is truncated if the value of track_activity_query_size was loaded correctly
        # to avoid confusingly reporting a wrong indicator by using a default that might be wrong for the database
        if track_activity_query_size == TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE:
            return StatementTruncationState.unknown

        # Compare the query length (in bytes to match Postgres) to the configured max query size to determine
        # if the query has been truncated. Note that the length of a truncated statement
        # can be less than the value of 'track_activity_query_size' by MAX_CHARACTER_SIZE_IN_BYTES + 1 because
        # multi-byte characters that fall on the limit are left out. One caveat is that if a statement's length
        # happens to be greater or equal to the threshold below but isn't actually truncated, this
        # would falsely report it as a truncated statement
        statement_bytes = bytes(statement) if PY2 else bytes(statement, "utf-8")
        truncated = len(statement_bytes) >= track_activity_query_size - (MAX_CHARACTER_SIZE_IN_BYTES + 1)
        return StatementTruncationState.truncated if truncated else StatementTruncationState.not_truncated
