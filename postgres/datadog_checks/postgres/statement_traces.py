import copy
import re
import time
from typing import Dict, Optional, Tuple

import psycopg2
from cachetools import TTLCache

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.time import get_timestamp

from .statement_samples import DBExplainError
from .util import (
    DatabaseConfigurationError,
    StatementTruncationState,
    get_track_activity_query_size,
    get_truncation_state,
    warning_with_tags,
)

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

PG_STAT_ACTIVITY_TRACE_QUERY = re.sub(
    r'\s+',
    ' ',
    """
    SELECT {current_time_func} {pg_stat_activity_cols} {pg_blocking_func} FROM {pg_stat_activity_view}
    where query like '%traceparent=''%-01''%'
    AND usename != '{user}'
    AND query_start IS NOT NULL
    {extra_filters}
""",
).strip()

EXPLAIN_VALIDATION_QUERY = "SELECT * FROM pg_stat_activity"

DEFAULT_COLLECTION_INTERVAL = 1


class PostgresStatementTraces(DBMAsyncJob):
    """
    Collects statement samples and execution plans.
    """

    def __init__(self, check, config, shutdown_callback):
        collection_interval = float(
            config.statement_traces_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        super(PostgresStatementTraces, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=is_affirmative(config.statement_traces_config.get('run_sync', False)),
            enabled=is_affirmative(config.statement_traces_config.get('enabled', True)),
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg2.errors.DatabaseError,),
            job_name="query-traces",
            shutdown_callback=shutdown_callback,
        )
        self._check = check
        self._config = config
        self._tags_no_db = None
        self._activity_last_query_start = None
        # The value is loaded when connecting to the main database
        self._explain_function = config.statement_traces_config.get(
            'explain_analyze_function', 'datadog.explain_analyze_statement'
        )
        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))
        self._username = self._config.user

        self._collection_strategy_cache = TTLCache(
            maxsize=config.statement_traces_config.get('collection_strategy_cache_maxsize', 1000),
            ttl=config.statement_traces_config.get('collection_strategy_cache_ttl', 300),
        )

        self._explain_errors_cache = TTLCache(
            maxsize=config.statement_traces_config.get('explain_errors_cache_maxsize', 5000),
            # only try to re-explain invalid statements once per day
            ttl=config.statement_traces_config.get('explain_errors_cache_ttl', 24 * 60 * 60),
        )

        self._plan_cache = TTLCache(
            maxsize=config.statement_traces_config.get('plan_cache_maxsize', 20000),
            # only try to re-explain statements once per 5 minutes
            ttl=config.statement_traces_config.get('plan_cache_ttl', 5 * 60),
        )

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

    def _get_new_pg_stat_traced_activity(self, available_activity_columns):
        start_time = time.time()
        extra_filters, params = self._get_extra_filters_and_params(filter_stale_idle_conn=True)
        cur_time_func = ""
        blocking_func = ""
        query = PG_STAT_ACTIVITY_TRACE_QUERY.format(
            current_time_func=cur_time_func,
            pg_stat_activity_cols=', '.join(available_activity_columns),
            pg_blocking_func=blocking_func,
            pg_stat_activity_view=self._config.pg_stat_activity_view,
            user=self._username,
            extra_filters=extra_filters,
        )
        with self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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

    def _get_available_activity_columns(self, all_expected_columns):
        with self._check._get_db(self._config.dbname).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(
                "select * from {pg_stat_activity_view} LIMIT 0".format(
                    pg_stat_activity_view=self._config.pg_stat_activity_view
                )
            )
            all_columns = set([i[0] for i in cursor.description])
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
            if not row['datname']:
                continue
            query = row['query']
            if not query:
                continue
            if query == '<insufficient privilege>':
                insufficient_privilege_count += 1
                continue
            if self._activity_last_query_start is None or row['query_start'] > self._activity_last_query_start:
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
                "dd.postgres.statement_traces.error",
                insufficient_privilege_count,
                tags=self._tags + ["error:insufficient-privilege"] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
        return normalized_rows

    def _normalize_row(self, row):
        normalized_row = dict(copy.copy(row))
        obfuscated_query = None
        try:
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
                "dd.postgres.statement_traces.error",
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
        self._collect_statement_traces()

    def _collect_statement_traces(self):
        start_time = time.time()
        pg_activity_cols = self._get_pg_stat_activity_cols_cached(PG_STAT_ACTIVITY_COLS)
        rows = self._get_new_pg_stat_traced_activity(pg_activity_cols)
        rows = self._filter_and_normalize_statement_rows(rows)
        event_traces = self._collect_plans(rows)
        submitted_count = 0
        for e in event_traces:
            self._check.database_monitoring_query_sample(json.dumps(e, default=default_json_event_encoding))
            submitted_count += 1

        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            "dd.postgres.collect_statement_traces.time",
            elapsed_ms,
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.count(
            "dd.postgres.collect_statement_traces.events_submitted.count",
            submitted_count,
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_traces.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_traces.explained_statements_cache.len",
            len(self._explained_statements_ratelimiter),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.postgres.collect_statement_traces.explain_errors_cache.len",
            len(self._explain_errors_cache),
            tags=self._tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    def _can_explain_statement(self, obfuscated_statement):
        if obfuscated_statement.startswith('SELECT {}'.format(self._explain_function)):
            return False
        if obfuscated_statement.startswith('autovacuum:'):
            return False
        if obfuscated_statement.split(' ', 1)[0].lower() not in SUPPORTED_EXPLAIN_STATEMENTS:
            return False
        return True

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

    def _run_explain(self, dbname, statement, obfuscated_statement):
        start_time = time.time()
        with self._check._get_db(dbname).cursor() as cursor:
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

    def _run_and_track_explain(self, dbname, statement, obfuscated_statement, query_signature):
        plan_dict, explain_err_code, err_msg = self._run_explain_safe(
            dbname, statement, obfuscated_statement, query_signature
        )
        err_tag = "error:explain-{}".format(explain_err_code.value if explain_err_code else None)
        if err_msg:
            err_tag = err_tag + "-" + err_msg
        self._check.count(
            "dd.postgres.statement_traces.error",
            1,
            tags=self._dbtags(dbname, err_tag) + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )
        return plan_dict, explain_err_code, err_msg

    def _run_explain_safe(self, dbname, statement, obfuscated_statement, query_signature):
        # type: (str, str, str, str) -> Tuple[Optional[Dict], Optional[DBExplainError], Optional[str]]
        if not self._can_explain_statement(obfuscated_statement):
            return None, DBExplainError.no_plans_possible, None

        track_activity_query_size = get_track_activity_query_size(self._check)

        if get_truncation_state(track_activity_query_size, statement) == StatementTruncationState.truncated:
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

        plan = self._plan_cache.get(query_signature)
        if cached_error_response:
            return plan, None, None

        try:
            plan = self._run_explain(dbname, statement, obfuscated_statement)
            self._plan_cache.set(query_signature, plan)
            return plan, None, None
        except psycopg2.errors.UndefinedParameter as e:
            self._log.debug(
                "Unable to collect execution plan, clients using the extended query protocol or prepared statements"
                " can't be explained due to the separation of the parsed query and raw bind parameters: %s",
                repr(e),
            )
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

    def _collect_plan_for_statement(self, row):
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
                    "query_truncated": get_truncation_state(self._get_track_activity_query_size(), row['query']).value,
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
                if row['statement'] is None:
                    continue
                event = self._collect_plan_for_statement(row)
                if event:
                    events.append(event)
            except Exception:
                self._log.exception(
                    "Crashed trying to collect execution plan for statement in dbname=%s", row['datname']
                )
                self._check.count(
                    "dd.postgres.statement_traces.error",
                    1,
                    tags=self._tags + ["error:collect-plan-for-statement-crash"] + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )
        return events

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
