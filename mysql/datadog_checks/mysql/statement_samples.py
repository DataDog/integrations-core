import re
import time
from contextlib import closing
from enum import Enum

import pymysql
from cachetools import TTLCache

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, RateLimitingTTLCache, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

SUPPORTED_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update', 'with'})

# unless a specific table is configured, we try all of the events_statements tables in descending order of
# preference
EVENTS_STATEMENTS_PREFERRED_TABLES = [
    'events_statements_history_long',
    'events_statements_current',
    # events_statements_history is the lowest in preference because it keeps the history only as long as the thread
    # exists, which means if an application uses only short-lived connections that execute a single query then we
    # won't be able to catch any samples of it. By querying events_statements_current we at least guarantee we'll
    # be able to catch queries from short-lived connections.
    'events_statements_history',
]

# default sampling settings for events_statements_* tables
# collection interval is in seconds
# {table -> interval}
DEFAULT_EVENTS_STATEMENTS_COLLECTION_INTERVAL = {
    'events_statements_history_long': 10,
    'events_statements_history': 10,
    'events_statements_current': 1,
}

# columns from events_statements_summary tables which correspond to attributes common to all databases and are
# therefore stored under other standard keys
EVENTS_STATEMENTS_SAMPLE_EXCLUDE_KEYS = {
    # gets obfuscated
    'sql_text',
    # stored as "instance"
    'current_schema',
    # used for signature
    'digest_text',
    'timer_end_time_s',
    'max_timer_wait_ns',
    'timer_start',
    # included as network.client.ip
    'processlist_host',
}

CREATE_TEMP_TABLE = re.sub(
    r'\s+',
    ' ',
    """
    CREATE TEMPORARY TABLE {temp_table} SELECT
        current_schema,
        sql_text,
        digest,
        digest_text,
        timer_start,
        timer_end,
        timer_wait,
        lock_time,
        rows_affected,
        rows_sent,
        rows_examined,
        select_full_join,
        select_full_range_join,
        select_range,
        select_range_check,
        select_scan,
        sort_merge_passes,
        sort_range,
        sort_rows,
        sort_scan,
        no_index_used,
        no_good_index_used,
        event_name,
        thread_id
     FROM {statements_table}
        WHERE sql_text IS NOT NULL
        AND event_name like 'statement/%%'
        AND digest_text is NOT NULL
        AND digest_text NOT LIKE 'EXPLAIN %%'
        AND timer_start > %s
    LIMIT %s
""",
).strip()

# neither window functions nor this variable-based window function emulation can be used directly on performance_schema
# tables due to some underlying issue regarding how the performance_schema storage engine works (for some reason
# many of the rows end up making it past the WHERE clause when they should have been filtered out)
SUB_SELECT_EVENTS_NUMBERED = re.sub(
    r'\s+',
    ' ',
    """
    (SELECT
        *,
        @row_num := IF(@current_digest = digest, @row_num + 1, 1) AS row_num,
        @current_digest := digest
    FROM {statements_table}
    ORDER BY digest, timer_wait)
""",
).strip()

SUB_SELECT_EVENTS_WINDOW = re.sub(
    r'\s+',
    ' ',
    """
    (SELECT
        *,
        row_number() over (partition by digest order by timer_wait desc) as row_num
    FROM {statements_table})
""",
).strip()

STARTUP_TIME_SUBQUERY = re.sub(
    r'\s+',
    ' ',
    """
    (SELECT UNIX_TIMESTAMP()-VARIABLE_VALUE
    FROM {global_status_table}
    WHERE VARIABLE_NAME='UPTIME')
""",
).strip()

EVENTS_STATEMENTS_QUERY = re.sub(
    r'\s+',
    ' ',
    """
    SELECT
        current_schema,
        sql_text,
        digest,
        digest_text,
        timer_start,
        @startup_time_s+timer_end*1e-12 as timer_end_time_s,
        timer_wait / 1000 AS timer_wait_ns,
        lock_time / 1000 AS lock_time_ns,
        rows_affected,
        rows_sent,
        rows_examined,
        select_full_join,
        select_full_range_join,
        select_range,
        select_range_check,
        select_scan,
        sort_merge_passes,
        sort_range,
        sort_rows,
        sort_scan,
        no_index_used,
        no_good_index_used,
        processlist_user,
        processlist_host,
        processlist_db
    FROM {statements_numbered} as E
    LEFT JOIN performance_schema.threads as T
        ON E.thread_id = T.thread_id
    WHERE sql_text IS NOT NULL
        AND timer_start > %s
        AND row_num = 1
    ORDER BY timer_wait DESC
    LIMIT %s
""",
).strip()

ENABLED_STATEMENTS_CONSUMERS_QUERY = re.sub(
    r'\s+',
    ' ',
    """
    SELECT name
    FROM performance_schema.setup_consumers
    WHERE enabled = 'YES'
    AND name LIKE 'events_statements_%'
""",
).strip()

PYMYSQL_NON_RETRYABLE_ERRORS = frozenset(
    {
        1044,  # access denied on database
        1046,  # no permission on statement
        1049,  # unknown database
        1305,  # procedure does not exist
        1370,  # no execute on procedure
    }
)


class StatementTruncationState(Enum):
    """
    Denotes the various possible states of a statement's truncation
    """

    truncated = 'truncated'
    not_truncated = 'not_truncated'


class DBExplainError(Enum):
    """
    Denotes the various reasons a query may not have an explain statement.
    """

    # database error i.e connection error
    database_error = 'database_error'

    # this could be the result of a missing EXPLAIN function
    invalid_schema = 'invalid_schema'

    # some statements cannot be explained i.e AUTOVACUUM
    no_plans_possible = 'no_plans_possible'

    # unable to collect an exec plan with the strategy 'PROCEDURE' without a default schema
    procedure_strategy_requires_default_schema = 'procedure_strategy_requires_default_schema'

    # agent may not have access to the default schema
    use_schema_error = 'use_schema_error'

    # a truncated query can't be explained
    query_truncated = 'query_truncated'


class MySQLStatementSamples(DBMAsyncJob):
    """
    Collects statement samples and execution plans.
    """

    def __init__(self, check, config, connection_args):
        collection_interval = float(config.statement_metrics_config.get('collection_interval', 1))
        if collection_interval <= 0:
            collection_interval = 1
        super(MySQLStatementSamples, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=is_affirmative(config.statement_samples_config.get('run_sync', False)),
            enabled=is_affirmative(config.statement_samples_config.get('enabled', True)),
            min_collection_interval=config.min_collection_interval,
            config_host=config.host,
            dbms="mysql",
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            job_name="statement-samples",
            shutdown_callback=self._close_db_conn,
        )
        self._config = config
        self._version_processed = False
        self._connection_args = connection_args
        # checkpoint at zero so we pull the whole history table on the first run
        self._checkpoint = 0
        self._last_check_run = 0
        self._db = None
        self._configured_collection_interval = self._config.statement_samples_config.get('collection_interval', -1)
        self._events_statements_row_limit = self._config.statement_samples_config.get(
            'events_statements_row_limit', 5000
        )
        self._explain_procedure = self._config.statement_samples_config.get('explain_procedure', 'explain_statement')
        self._fully_qualified_explain_procedure = self._config.statement_samples_config.get(
            'fully_qualified_explain_procedure', 'datadog.explain_statement'
        )
        self._events_statements_temp_table = self._config.statement_samples_config.get(
            'events_statements_temp_table_name', 'datadog.temp_events'
        )
        self._events_statements_enable_procedure = self._config.statement_samples_config.get(
            'events_statements_enable_procedure', 'datadog.enable_events_statements_consumers'
        )
        self._preferred_events_statements_tables = EVENTS_STATEMENTS_PREFERRED_TABLES
        self._has_window_functions = False
        events_statements_table = self._config.statement_samples_config.get('events_statements_table', None)
        if events_statements_table:
            if events_statements_table in DEFAULT_EVENTS_STATEMENTS_COLLECTION_INTERVAL:
                self._log.debug("Configured preferred events_statements_table: %s", events_statements_table)
                self._preferred_events_statements_tables = [events_statements_table]
            else:
                self._log.warning(
                    "Invalid events_statements_table: %s. Must be one of %s. Falling back to trying all tables.",
                    events_statements_table,
                    ', '.join(DEFAULT_EVENTS_STATEMENTS_COLLECTION_INTERVAL.keys()),
                )
        self._explain_strategies = {
            'PROCEDURE': self._run_explain_procedure,
            'FQ_PROCEDURE': self._run_fully_qualified_explain_procedure,
            'STATEMENT': self._run_explain,
        }
        self._preferred_explain_strategies = ['PROCEDURE', 'FQ_PROCEDURE', 'STATEMENT']
        self._obfuscate_options = to_native_string(
            json.dumps({'quantize_sql_tables': self._config.obfuscator_options.get('quantize_sql_tables', False)})
        )
        self._init_caches()

    def _init_caches(self):
        self._collection_strategy_cache = TTLCache(
            maxsize=self._config.statement_samples_config.get('collection_strategy_cache_maxsize', 1000),
            ttl=self._config.statement_samples_config.get('collection_strategy_cache_ttl', 300),
        )

        # explained_statements_cache: limit how often we try to re-explain the same query
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=self._config.statement_samples_config.get('explained_queries_cache_maxsize', 5000),
            ttl=60 * 60 / self._config.statement_samples_config.get('explained_queries_per_hour_per_query', 60),
        )

        # seen_samples_cache: limit the ingestion rate per (query_signature, plan_signature)
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            # assuming ~100 bytes per entry (query & plan signature, key hash, 4 pointers (ordered dict), expiry time)
            # total size: 10k * 100 = 1 Mb
            maxsize=self._config.statement_samples_config.get('seen_samples_cache_maxsize', 10000),
            ttl=60 * 60 / self._config.statement_samples_config.get('samples_per_hour_per_query', 15),
        )

    def _read_version_info(self):
        if not self._version_processed and self._check.version:
            self._has_window_functions = self._check.version.version_compatible((8, 0, 0))
            if self._check.version.flavor == "MariaDB" or not self._check.version.version_compatible((5, 7, 0)):
                self._global_status_table = "information_schema.global_status"
            else:
                self._global_status_table = "performance_schema.global_status"
            self._version_processed = True

    def _get_db_connection(self):
        """
        lazy reconnect db
        pymysql connections are not thread safe so we can't reuse the same connection from the main check
        :return:
        """
        if not self._db:
            self._db = pymysql.connect(**self._connection_args)
        return self._db

    def _close_db_conn(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                self._log.debug("Failed to close db connection", exc_info=1)
            finally:
                self._db = None

    def _cursor_run(self, cursor, query, params=None, obfuscated_params=None):
        """
        Run and log the query. If provided, obfuscated params are logged in place of the regular params.
        """
        self._log.debug("Running query [%s] %s", query, obfuscated_params if obfuscated_params else params)
        cursor.execute(query, params)

    def _get_new_events_statements(self, events_statements_table, row_limit):
        # Select the most recent events with a bias towards events which have higher wait times
        start = time.time()
        drop_temp_table_query = "DROP TEMPORARY TABLE IF EXISTS {}".format(self._events_statements_temp_table)
        params = (self._checkpoint, row_limit)
        with closing(self._get_db_connection().cursor(pymysql.cursors.DictCursor)) as cursor:
            # silence expected warnings to avoid spam
            cursor.execute('SET @@SESSION.sql_notes = 0')
            try:
                self._cursor_run(cursor, drop_temp_table_query)
                self._cursor_run(
                    cursor,
                    CREATE_TEMP_TABLE.format(
                        temp_table=self._events_statements_temp_table,
                        statements_table="performance_schema." + events_statements_table,
                    ),
                    params,
                )
            except pymysql.err.DatabaseError as e:
                self._check.count(
                    "dd.mysql.query_samples.error",
                    1,
                    tags=self._tags + ["error:create-temp-table-{}".format(type(e))] + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )
                raise
            if self._has_window_functions:
                sub_select = SUB_SELECT_EVENTS_WINDOW
            else:
                self._cursor_run(cursor, "set @row_num = 0")
                self._cursor_run(cursor, "set @current_digest = ''")
                sub_select = SUB_SELECT_EVENTS_NUMBERED
            self._cursor_run(
                cursor,
                "set @startup_time_s = {}".format(
                    STARTUP_TIME_SUBQUERY.format(global_status_table=self._global_status_table)
                ),
            )
            self._cursor_run(
                cursor,
                EVENTS_STATEMENTS_QUERY.format(
                    statements_numbered=sub_select.format(statements_table=self._events_statements_temp_table)
                ),
                params,
            )
            rows = cursor.fetchall()
            self._cursor_run(cursor, drop_temp_table_query)
            tags = (
                self._tags
                + ["events_statements_table:{}".format(events_statements_table)]
                + self._check._get_debug_tags()
            )
            self._check.histogram(
                "dd.mysql.get_new_events_statements.time",
                (time.time() - start) * 1000,
                tags=tags,
                hostname=self._check.resolved_hostname,
            )
            self._check.histogram(
                "dd.mysql.get_new_events_statements.rows", len(rows), tags=tags, hostname=self._check.resolved_hostname
            )
            self._log.debug("Read %s rows from %s", len(rows), events_statements_table)
            return rows

    def _filter_valid_statement_rows(self, rows):
        num_sent = 0

        for row in rows:
            if not row or not all(row):
                self._log.debug('Row was unexpectedly truncated or the events_statements table is not enabled')
                continue
            sql_text = row['sql_text']
            if not sql_text:
                continue
            yield row
            # only save the checkpoint for rows that we have successfully processed
            # else rows that we ignore can push the checkpoint forward causing us to miss some on the next run
            if row['timer_start'] > self._checkpoint:
                self._checkpoint = row['timer_start']
            num_sent += 1

    def _collect_plan_for_statement(self, row):
        # Plans have several important signatures to tag events with:
        # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
        # - `resource_hash` - hash computed off the raw sql text to match apm resources
        # - `query_signature` - hash computed from the digest text to match query metrics

        try:
            obfuscated_statement = datadog_agent.obfuscate_sql(row['sql_text'], self._obfuscate_options)
            obfuscated_digest_text = datadog_agent.obfuscate_sql(row['digest_text'], self._obfuscate_options)
        except Exception:
            # do not log the raw sql_text to avoid leaking sensitive data into logs. digest_text is safe as parameters
            # are obfuscated by the database
            self._log.debug("Failed to obfuscate statement: %s", row['digest_text'])
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=self._tags + ["error:sql-obfuscate"] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            return None

        apm_resource_hash = compute_sql_signature(obfuscated_statement)
        query_signature = compute_sql_signature(obfuscated_digest_text)

        query_cache_key = (row['current_schema'], query_signature)
        if not self._explained_statements_ratelimiter.acquire(query_cache_key):
            return None

        plan, explain_errors = None, None
        truncated = self._get_truncation_state(row['sql_text'])
        if truncated == StatementTruncationState.truncated:
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=self._tags
                + ["error:explain-{}".format(DBExplainError.query_truncated)]
                + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            explain_errors = [
                (
                    None,
                    DBExplainError.query_truncated,
                    'truncated length: {}'.format(len(row['sql_text'])),
                )
            ]
        else:
            with closing(self._get_db_connection().cursor()) as cursor:
                try:
                    plan, explain_errors = self._explain_statement(
                        cursor, row['sql_text'], row['current_schema'], obfuscated_statement
                    )
                except Exception as e:
                    self._check.count(
                        "dd.mysql.query_samples.error",
                        1,
                        tags=self._tags + ["error:explain-{}".format(type(e))] + self._check._get_debug_tags(),
                        hostname=self._check.resolved_hostname,
                    )
                    self._log.exception("Failed to explain statement: %s", obfuscated_statement)

        collection_errors = []
        if explain_errors:
            for strategy, explain_err_code, explain_err in explain_errors:
                collection_errors.append(
                    {
                        'strategy': strategy if strategy else None,
                        'code': explain_err_code.value if explain_err_code else None,
                        'message': explain_err if explain_err else None,
                    }
                )

        normalized_plan, obfuscated_plan, plan_signature = None, None, None
        if plan:
            normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True) if plan else None
            obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
            plan_signature = compute_exec_plan_signature(normalized_plan)

        query_plan_cache_key = (query_cache_key, plan_signature)
        if self._seen_samples_ratelimiter.acquire(query_plan_cache_key):
            return {
                "timestamp": row["timer_end_time_s"] * 1000,
                "host": self._check.resolved_hostname,
                "ddsource": "mysql",
                "ddtags": self._tags_str,
                "duration": row['timer_wait_ns'],
                "network": {
                    "client": {
                        "ip": row.get('processlist_host', None),
                    }
                },
                "db": {
                    "instance": row['current_schema'],
                    "plan": {
                        "definition": obfuscated_plan,
                        "signature": plan_signature,
                        "collection_errors": collection_errors if collection_errors else None,
                    },
                    "query_signature": query_signature,
                    "resource_hash": apm_resource_hash,
                    "statement": obfuscated_statement,
                    "query_truncated": truncated.value,
                },
                'mysql': {k: v for k, v in row.items() if k not in EVENTS_STATEMENTS_SAMPLE_EXCLUDE_KEYS},
            }

    def _collect_plans_for_statements(self, rows):
        for row in rows:
            try:
                event = self._collect_plan_for_statement(row)
                if event:
                    yield event
            except Exception:
                self._log.debug("Failed to collect plan for statement", exc_info=1)

    def _get_enabled_performance_schema_consumers(self):
        """
        Returns the list of available performance schema consumers
        I.e. (events_statements_current, events_statements_history)
        :return:
        """
        with closing(self._get_db_connection().cursor()) as cursor:
            self._cursor_run(cursor, ENABLED_STATEMENTS_CONSUMERS_QUERY)
            return set([r[0] for r in cursor.fetchall()])

    def _enable_events_statements_consumers(self):
        """
        Enable events statements consumers
        :return:
        """
        try:
            with closing(self._get_db_connection().cursor()) as cursor:
                self._cursor_run(cursor, 'CALL {}()'.format(self._events_statements_enable_procedure))
        except pymysql.err.DatabaseError as e:
            self._log.debug(
                "failed to enable events_statements consumers using procedure=%s: %s",
                self._events_statements_enable_procedure,
                e,
            )

    def _get_sample_collection_strategy(self):
        """
        Decides on the plan collection strategy:
        - which events_statement_history-* table are we using
        - how long should the rate and time limits be
        :return: (table, rate_limit)
        """
        cached_strategy = self._collection_strategy_cache.get("plan_collection_strategy")
        if cached_strategy:
            self._log.debug("Using cached plan_collection_strategy: %s", cached_strategy)
            return cached_strategy

        enabled_consumers = self._get_enabled_performance_schema_consumers()
        if len(enabled_consumers) < 3:
            self._enable_events_statements_consumers()
            enabled_consumers = self._get_enabled_performance_schema_consumers()

        if not enabled_consumers:
            self._log.warning(
                "Cannot collect statement samples as there are no enabled performance_schema.events_statements_* "
                "consumers. Enable performance_schema and at least one events_statements consumer in order to collect "
                "statement samples."
            )
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=self._tags + ["error:no-enabled-events-statements-consumers"] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            return None, None
        self._log.debug("Found enabled performance_schema statements consumers: %s", enabled_consumers)

        events_statements_table = None
        for table in self._preferred_events_statements_tables:
            if table not in enabled_consumers:
                continue
            rows = self._get_new_events_statements(table, 1)
            if not rows:
                self._log.debug("No statements found in %s table. checking next one.", table)
                continue
            events_statements_table = table
            break
        if not events_statements_table:
            self._log.warning(
                "Cannot collect statement samples as all enabled events_statements_consumers %s are empty.",
                enabled_consumers,
            )
            return None, None

        collection_interval = self._configured_collection_interval
        if collection_interval < 0:
            collection_interval = DEFAULT_EVENTS_STATEMENTS_COLLECTION_INTERVAL[events_statements_table]

        # cache only successful strategies
        # should be short enough that we'll reflect updates relatively quickly
        # i.e., an aurora replica becomes a master (or vice versa).
        strategy = (events_statements_table, collection_interval)
        self._log.debug(
            "Chose plan collection strategy: events_statements_table=%s, collection_interval=%s",
            events_statements_table,
            collection_interval,
        )
        self._collection_strategy_cache["plan_collection_strategy"] = strategy
        return strategy

    def run_job(self):
        self._collect_statement_samples()

    def _collect_statement_samples(self):
        self._read_version_info()
        self._log.debug("collecting statement samples")
        events_statements_table, collection_interval = self._get_sample_collection_strategy()
        if not events_statements_table:
            return
        self._set_rate_limit(1.0 / collection_interval)

        start_time = time.time()

        rows = self._get_new_events_statements(events_statements_table, self._events_statements_row_limit)
        rows = self._filter_valid_statement_rows(rows)
        events = self._collect_plans_for_statements(rows)
        submitted_count = 0
        tags = (
            self._tags + ["events_statements_table:{}".format(events_statements_table)] + self._check._get_debug_tags()
        )
        for e in events:
            self._check.database_monitoring_query_sample(json.dumps(e, default=default_json_event_encoding))
            submitted_count += 1
        self._check.histogram(
            "dd.mysql.collect_statement_samples.time",
            (time.time() - start_time) * 1000,
            tags=tags,
            hostname=self._check.resolved_hostname,
        )
        self._check.count(
            "dd.mysql.collect_statement_samples.events_submitted.count",
            submitted_count,
            tags=tags,
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.mysql.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=tags,
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.mysql.collect_statement_samples.explained_statements_cache.len",
            len(self._explained_statements_ratelimiter),
            tags=tags,
            hostname=self._check.resolved_hostname,
        )
        self._check.gauge(
            "dd.mysql.collect_statement_samples.collection_strategy_cache.len",
            len(self._collection_strategy_cache),
            tags=tags,
            hostname=self._check.resolved_hostname,
        )

    def _explain_statement(self, cursor, statement, schema, obfuscated_statement):
        """
        Tries the available methods used to explain a statement for the given schema. If a non-retryable
        error occurs (such as a permissions error), then statements executed under the schema will be
        disallowed in future attempts.
        returns: An execution plan, otherwise it returns a list of tuples containing: (strategy, error code, error)
        rtype: Optional[Dict], List[Tuple[Optional[str], Optional[DBExplainError], Optional[Exception]]]
        """
        start_time = time.time()
        strategy_cache_key = 'explain_strategy:%s' % schema
        tags = self._tags + ["schema:{}".format(schema)] + self._check._get_debug_tags()

        self._log.debug('explaining statement. schema=%s, statement="%s"', schema, statement)

        if not self._can_explain(obfuscated_statement):
            self._log.debug('Skipping statement which cannot be explained: %s', obfuscated_statement)
            return None, [(None, DBExplainError.no_plans_possible, None)]

        cached_strategy = self._collection_strategy_cache.get(strategy_cache_key)
        if cached_strategy:
            _, explain_err_code, _ = cached_strategy[0]  # (strategy, explain_err_code, explain_err)
            if explain_err_code:
                self._log.debug('Skipping statement due to cached collection failure: %s', obfuscated_statement)
                return None, None

        try:
            # If there was a default schema when this query was run, then switch to it before trying to collect
            # the execution plan. This is necessary when the statement uses non-fully qualified tables
            # e.g. `select * from mytable` instead of `select * from myschema.mytable`
            if schema:
                self._cursor_run(cursor, 'USE `{}`'.format(schema))
        except pymysql.err.DatabaseError as e:
            if len(e.args) != 2:
                raise
            explain_errors = [(None, DBExplainError.use_schema_error, '{}'.format(type(e)))]
            if e.args[0] in PYMYSQL_NON_RETRYABLE_ERRORS:
                self._collection_strategy_cache[strategy_cache_key] = explain_errors
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=tags + ["error:explain-use-schema-{}".format(type(e))],
                hostname=self._check.resolved_hostname,
            )
            self._log.debug(
                'Failed to collect execution plan because schema could not be accessed. error=%s, schema=%s, '
                'statement="%s"',
                e.args,
                schema,
                obfuscated_statement,
            )
            return None, explain_errors

        # Use a cached strategy for the schema, if any, or try each strategy to collect plans
        strategies = list(self._preferred_explain_strategies)
        cached_strategy = self._collection_strategy_cache.get(strategy_cache_key)
        if cached_strategy:
            strategy, _, _ = cached_strategy[0]  # (strategy, explain_err_code, explain_err)
            strategies.remove(strategy)
            strategies.insert(0, strategy)

        explain_errors = []
        for strategy in strategies:
            try:
                if not schema and strategy == "PROCEDURE":
                    explain_errors.append((strategy, DBExplainError.procedure_strategy_requires_default_schema, None))
                    self._log.debug(
                        'skipping PROCEDURE strategy as there is no default schema for this statement="%s"',
                        obfuscated_statement,
                    )
                    continue
                plan = self._explain_strategies[strategy](cursor, statement, obfuscated_statement)
                if plan:
                    self._collection_strategy_cache[strategy_cache_key] = [(strategy, None, None)]
                    self._log.debug(
                        'Successfully collected execution plan. strategy=%s, schema=%s, statement="%s"',
                        strategy,
                        schema,
                        obfuscated_statement,
                    )
                    self._check.histogram(
                        "dd.mysql.run_explain.time",
                        (time.time() - start_time) * 1000,
                        tags=self._tags + ["strategy:{}".format(strategy)],
                        hostname=self._check.resolved_hostname,
                    )
                    return plan, None
            except pymysql.err.DatabaseError as e:
                if len(e.args) != 2:
                    raise
                # we don't cache failed plan collection failures for specific queries because some queries in a schema
                # can fail while others succeed. The failed collection will be cached for the specific query
                # so we won't try to explain it again for the cache duration there.
                explain_errors.append((strategy, DBExplainError.database_error, '{}'.format(type(e))))
                self._check.count(
                    "dd.mysql.query_samples.error",
                    1,
                    tags=tags + ["error:explain-attempt-{}-{}".format(strategy, type(e))],
                    hostname=self._check.resolved_hostname,
                )
                self._log.debug(
                    'Failed to collect execution plan. error=%s, strategy=%s, schema=%s, statement="%s"',
                    e.args,
                    strategy,
                    schema,
                    obfuscated_statement,
                )
                continue
        return None, explain_errors

    def _run_explain(self, cursor, statement, obfuscated_statement):
        """
        Run the explain using the EXPLAIN statement
        """
        self._log.debug("running query [EXPLAIN FORMAT=json %s]", obfuscated_statement)
        cursor.execute('EXPLAIN FORMAT=json {}'.format(statement))
        return cursor.fetchone()[0]

    def _run_explain_procedure(self, cursor, statement, obfuscated_statement):
        """
        Run the explain by calling the stored procedure if available.
        """
        self._cursor_run(cursor, 'CALL {}(%s)'.format(self._explain_procedure), statement, obfuscated_statement)
        return cursor.fetchone()[0]

    def _run_fully_qualified_explain_procedure(self, cursor, statement, obfuscated_statement):
        """
        Run the explain by calling the fully qualified stored procedure if available.
        """
        self._cursor_run(
            cursor, 'CALL {}(%s)'.format(self._fully_qualified_explain_procedure), statement, obfuscated_statement
        )
        return cursor.fetchone()[0]

    @staticmethod
    def _can_explain(obfuscated_statement):
        return obfuscated_statement.split(' ', 1)[0].lower() in SUPPORTED_EXPLAIN_STATEMENTS

    @staticmethod
    def _get_truncation_state(statement):
        # Mysql adds 3 dots at the end of truncated statements so we use this to check if
        # a statement is truncated
        truncated = statement[-3:] == '...'
        return StatementTruncationState.truncated if truncated else StatementTruncationState.not_truncated
