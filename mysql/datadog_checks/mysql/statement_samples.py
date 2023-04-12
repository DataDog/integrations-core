# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
import time
from collections import namedtuple
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
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

from .util import DatabaseConfigurationError, StatementTruncationState, get_truncation_state, warning_with_tags


def agent_check_getter(self):
    return self.check


SUPPORTED_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update', 'with'})

EVENTS_STATEMENTS_TABLE = 'events_statements_current'

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

EVENTS_STATEMENTS_CURRENT_QUERY = re.sub(
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
    FROM performance_schema.events_statements_current E
    LEFT JOIN performance_schema.threads as T
        ON E.thread_id = T.thread_id
    WHERE sql_text IS NOT NULL
        AND event_name like 'statement/%%'
        AND digest_text is NOT NULL
        AND digest_text NOT LIKE 'EXPLAIN %%'
        ORDER BY timer_wait DESC
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

PYMYSQL_MISSING_EXPLAIN_STATEMENT_PROC_ERRORS = frozenset(
    {
        pymysql.constants.ER.ACCESS_DENIED_ERROR,
        pymysql.constants.ER.DBACCESS_DENIED_ERROR,
        pymysql.constants.ER.SP_DOES_NOT_EXIST,
        pymysql.constants.ER.PROCACCESS_DENIED_ERROR,
    }
)


class DBExplainErrorCode(Enum):
    """
    Denotes the various reasons a query may not have an explain statement.
    """

    # database error i.e connection error
    database_error = 'database_error'

    # this could be the result of a missing EXPLAIN function
    invalid_schema = 'invalid_schema'

    # some statements cannot be explained i.e AUTOVACUUM
    no_plans_possible = 'no_plans_possible'

    # agent may not have access to the default schema
    use_schema_error = 'use_schema_error'

    # a truncated query can't be explained
    query_truncated = 'query_truncated'


# ExplainState describes the current state of an explain strategy
# If there is no error then the strategy is valid
ExplainState = namedtuple('ExplainState', ['strategy', 'error_code', 'error_message'])

EMPTY_EXPLAIN_STATE = ExplainState(strategy=None, error_code=None, error_message=None)


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
            dbms="mysql",
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            job_name="statement-samples",
            shutdown_callback=self._close_db_conn,
        )
        self._config = config
        self._version_processed = False
        self._connection_args = connection_args
        self._last_check_run = 0
        self._db = None
        self._check = check
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
        self._explain_strategies = {
            'PROCEDURE': self._run_explain_procedure,
            'FQ_PROCEDURE': self._run_fully_qualified_explain_procedure,
            'STATEMENT': self._run_explain,
        }
        self._preferred_explain_strategies = ['PROCEDURE', 'FQ_PROCEDURE', 'STATEMENT']
        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))
        self._init_caches()

    def _init_caches(self):
        self._collection_strategy_cache = TTLCache(
            maxsize=self._config.statement_samples_config.get('collection_strategy_cache_maxsize', 1000),
            ttl=self._config.statement_samples_config.get('collection_strategy_cache_ttl', 300),
        )

        # explained_statements_cache: limit how often we try to re-explain the same query
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=self._config.statement_samples_config.get('explained_queries_cache_maxsize', 5000),
            ttl=45 * 60 / self._config.statement_samples_config.get('explained_queries_per_hour_per_query', 60),
        )

        # explain_error_states_cache. cache {(schema, query_signature) -> [explain_error_state])
        self._explain_error_states_cache = TTLCache(
            maxsize=self._config.statement_samples_config.get('explain_errors_cache_maxsize', 5000),
            # only try to re-explain failed statements once every two hours, so in the worst case the maximum
            # re-explain rate of failed queries is ~ 5000/(2*60*60) = 1/second
            ttl=self._config.statement_samples_config.get('explain_errors_cache_ttl', 2 * 60 * 60),
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

    def _use_schema(self, cursor, schema, explain_state_cache_key):
        """
        Try to use the schema (if provided), caching errors to avoid excessive futile re-attempts
        """
        cached_state = self._collection_strategy_cache.get(explain_state_cache_key, EMPTY_EXPLAIN_STATE)
        if cached_state.error_code:
            return cached_state
        try:
            # If there was a default schema when this query was run, then switch to it before trying to collect
            # the execution plan. This is necessary when the statement uses non-fully qualified tables
            # e.g. `select * from mytable` instead of `select * from myschema.mytable`
            if schema:
                self._cursor_run(cursor, 'USE `{}`'.format(schema))
                return None
        except pymysql.err.DatabaseError as e:
            if len(e.args) != 2:
                raise
            error_state = ExplainState(
                strategy=None,
                error_code=DBExplainErrorCode.use_schema_error,
                error_message=str(type(e)),
            )
            if e.args[0] in PYMYSQL_NON_RETRYABLE_ERRORS:
                self._collection_strategy_cache[explain_state_cache_key] = error_state
            return error_state

    def _cursor_run(self, cursor, query, params=None, obfuscated_params=None, obfuscated_query=None):
        """
        Run and log the query. If provided, obfuscated params are logged in place of the regular params.
        """
        try:
            logged_query = obfuscated_query if obfuscated_query else query
            self._log.debug("Running query [%s] %s", logged_query, obfuscated_params if obfuscated_params else params)
            cursor.execute(query, params)
        except pymysql.DatabaseError as e:
            self._check.count(
                "dd.mysql.db.error",
                1,
                tags=self._tags + ["error:{}".format(type(e))] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            raise

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_new_events_statements_current(self):
        start = time.time()
        with closing(self._get_db_connection().cursor(pymysql.cursors.DictCursor)) as cursor:
            self._cursor_run(
                cursor,
                "set @startup_time_s = {}".format(
                    STARTUP_TIME_SUBQUERY.format(global_status_table=self._global_status_table)
                ),
            )
            self._cursor_run(cursor, EVENTS_STATEMENTS_CURRENT_QUERY)
            rows = cursor.fetchall()
            tags = (
                self._tags
                + ["events_statements_table:{}".format(EVENTS_STATEMENTS_TABLE)]
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
            self._log.debug("Read %s rows from %s", len(rows), EVENTS_STATEMENTS_TABLE)
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
            num_sent += 1

    def _collect_plan_for_statement(self, row):
        # Plans have several important signatures to tag events with:
        # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
        # - `resource_hash` - hash computed off the raw sql text to match apm resources
        # - `query_signature` - hash computed from the digest text to match query metrics
        try:
            statement = obfuscate_sql_with_metadata(row['sql_text'], self._obfuscate_options)
            statement_digest_text = obfuscate_sql_with_metadata(row['digest_text'], self._obfuscate_options)
        except Exception as e:
            # do not log raw sql_text to avoid leaking sensitive data into logs unless log_unobfuscated_queries is set
            # digest_text is safe as parameters are obfuscated by the database
            if self._config.log_unobfuscated_queries:
                self._log.warning("Failed to obfuscate query=[%s] | err=[%s]", row['sql_text'], e)
            else:
                self._log.debug("Failed to obfuscate query=[%s] | err=[%s]", row['digest_text'], e)
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=self._tags + ["error:sql-obfuscate"] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            return None

        obfuscated_statement = statement['query']
        obfuscated_digest_text = statement_digest_text['query']
        apm_resource_hash = compute_sql_signature(obfuscated_statement)
        query_signature = compute_sql_signature(obfuscated_digest_text)

        query_cache_key = (row['current_schema'], query_signature)
        if not self._explained_statements_ratelimiter.acquire(query_cache_key):
            return None

        with closing(self._get_db_connection().cursor()) as cursor:
            plan, error_states = self._explain_statement(
                cursor, row['sql_text'], row['current_schema'], obfuscated_statement, query_signature
            )

        collection_errors = []
        if error_states:
            for state in error_states:
                error_tag = "error:explain-{}-{}".format(state.error_code, state.error_message)
                self._check.count(
                    "dd.mysql.query_samples.error",
                    1,
                    tags=self._tags + [error_tag] + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )
                collection_errors.append(
                    {
                        'strategy': state.strategy,
                        'code': state.error_code.value if state.error_code else None,
                        'message': state.error_message,
                    }
                )

        normalized_plan, obfuscated_plan, plan_signature = None, None, None
        if plan:
            try:
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True) if plan else None
                obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
            except Exception as e:
                if self._config.log_unobfuscated_plans:
                    self._log.warning("Failed to obfuscate plan=[%s] | err=[%s]", plan, e)
                raise e
            plan_signature = compute_exec_plan_signature(normalized_plan)

        query_plan_cache_key = (query_cache_key, plan_signature)
        if self._seen_samples_ratelimiter.acquire(query_plan_cache_key):
            return {
                "timestamp": row["timer_end_time_s"] * 1000,
                "host": self._check.resolved_hostname,
                "ddagentversion": datadog_agent.get_version(),
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
                    "metadata": {
                        "tables": statement['metadata'].get('tables', None),
                        "commands": statement['metadata'].get('commands', None),
                        "comments": statement['metadata'].get('comments', None),
                    },
                    "query_truncated": get_truncation_state(row['sql_text']).value,
                },
                'mysql': {k: v for k, v in row.items() if k not in EVENTS_STATEMENTS_SAMPLE_EXCLUDE_KEYS},
            }

    @tracked_method(agent_check_getter=agent_check_getter)
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
            return {r[0] for r in cursor.fetchall()}

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
        cached_strategy = self._collection_strategy_cache.get("events_statements_strategy")
        if cached_strategy:
            self._log.debug("Using cached events_statements_strategy: %s", cached_strategy)
            return cached_strategy

        enabled_consumers = self._get_enabled_performance_schema_consumers()
        if len(enabled_consumers) < 3:
            self._enable_events_statements_consumers()
            enabled_consumers = self._get_enabled_performance_schema_consumers()

        if not enabled_consumers:
            self._check.record_warning(
                DatabaseConfigurationError.events_statements_consumer_missing,
                warning_with_tags(
                    'Cannot collect statement samples as there are no enabled performance_schema.events_statements_* '
                    'consumers. Enable performance_schema and at least one events_statements consumer in order '
                    'to collect statement samples. See https://docs.datadoghq.com/database_monitoring/setup_mysql/'
                    'troubleshooting/#%s for more details.',
                    DatabaseConfigurationError.events_statements_consumer_missing.value,
                    code=DatabaseConfigurationError.events_statements_consumer_missing.value,
                    host=self._check.resolved_hostname,
                ),
            )
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=self._tags + ["error:no-enabled-events-statements-consumers"] + self._check._get_debug_tags(),
                hostname=self._check.resolved_hostname,
            )
            return None, None
        self._log.debug("Found enabled performance_schema statements consumers: %s", enabled_consumers)

        collection_interval = self._configured_collection_interval
        if collection_interval < 0:
            collection_interval = DEFAULT_EVENTS_STATEMENTS_COLLECTION_INTERVAL[EVENTS_STATEMENTS_TABLE]

        # cache only successful strategies
        # should be short enough that we'll reflect updates relatively quickly
        # i.e., an aurora replica becomes a master (or vice versa).
        strategy = (EVENTS_STATEMENTS_TABLE, collection_interval)
        self._log.debug(
            "Chose plan collection strategy: events_statements_table=%s, collection_interval=%s",
            EVENTS_STATEMENTS_TABLE,
            collection_interval,
        )
        self._collection_strategy_cache["events_statements_strategy"] = strategy
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

        rows = self._get_new_events_statements_current()
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

    def _explain_statement(self, cursor, statement, schema, obfuscated_statement, query_signature):
        """
        Tries the available methods used to explain a statement for the given schema. If a non-retryable
        error occurs (such as a permissions error), then statements executed under the schema will be
        disallowed in future attempts.
        returns: An execution plan, otherwise it returns a list of error ExplainStates
        rtype: Optional[Dict], List[ExplainState]
        """
        if get_truncation_state(statement) == StatementTruncationState.truncated:
            error_state = ExplainState(
                strategy=None,
                error_code=DBExplainErrorCode.query_truncated,
                error_message='truncated length: {}'.format(len(statement)),
            )
            return None, [error_state]

        if not self._can_explain(obfuscated_statement):
            self._log.debug('Skipping statement which cannot be explained: %s', obfuscated_statement)
            error_state = ExplainState(
                strategy=None, error_code=DBExplainErrorCode.no_plans_possible, error_message=None
            )
            return None, [error_state]

        # for caching an ExplainState (whether error or OK) per schema
        explain_state_cache_key = 'explain_state:%s' % schema

        # for caching a list of *error* ExplainStates per query
        query_cache_key = (schema, query_signature)

        start_time = time.time()
        self._log.debug('explaining statement. schema=%s, statement="%s"', schema, obfuscated_statement)
        error_state = self._use_schema(cursor, schema, explain_state_cache_key)
        if error_state:
            self._log.debug(
                'Failed to collect execution plan because schema could not be accessed. schema=%s error=%s: %s',
                schema,
                error_state,
                obfuscated_statement,
            )
            return None, [error_state]

        preferred_strategies = list(self._preferred_explain_strategies)
        explain_state = self._collection_strategy_cache.get(explain_state_cache_key, EMPTY_EXPLAIN_STATE)

        # if we've cached a successful non-error strategy, put it at the front of the list
        if explain_state.strategy and not explain_state.error_code:
            preferred_strategies.remove(explain_state.strategy)
            preferred_strategies.insert(0, explain_state.strategy)

        # if there is a default schema on the connection then the only way we can guarantee collection of plans is
        # by having that same default schema set when invoking the EXPLAIN, which is what we do with the "PROCEDURE"
        # strategy. If there is no default schema then we can collect it from anywhere, typically FQ_PROCEDURE, which
        # is expected to be in the dedicated datadog schema.
        optimal_strategy = "PROCEDURE" if schema else "FQ_PROCEDURE"
        is_optimal_strategy_cached = explain_state.strategy == optimal_strategy and not explain_state.error_code
        if is_optimal_strategy_cached:
            # if the optimal strategy was cached then that means at least one recent query must have been successfully
            # collected from this schema and therefore the schema is probably setup OK.
            # knowing that the schema is setup OK, if we fail to collect an execution plan for a given query then
            # it's likely a problem with that specific query and it's not worth trying it again so we cache those
            # errors for a longer time to avoid excessive futile explain attempts.
            cached_error_states = self._explain_error_states_cache.get(query_cache_key, None)
            if cached_error_states:
                self._log.debug(
                    'Skipping execution plan collection for query due to cached failures %s: %s',
                    cached_error_states,
                    obfuscated_statement,
                )
                return None, cached_error_states

        error_states = []
        for strategy in preferred_strategies:
            if not schema and strategy == "PROCEDURE":
                self._log.debug(
                    'skipping PROCEDURE strategy as there is no default schema for this statement="%s"',
                    obfuscated_statement,
                )
                continue
            try:
                plan = self._explain_strategies[strategy](schema, cursor, statement, obfuscated_statement)
                if plan:
                    self._collection_strategy_cache[explain_state_cache_key] = ExplainState(
                        strategy=strategy, error_code=None, error_message=None
                    )
                    self._log.debug(
                        'Successfully collected execution plan. strategy=%s, schema=%s, statement="%s"',
                        strategy,
                        schema,
                        obfuscated_statement,
                    )
                    self._check.histogram(
                        "dd.mysql.run_explain.time",
                        (time.time() - start_time) * 1000,
                        tags=self._tags + ["strategy:{}".format(strategy)] + self._check._get_debug_tags(),
                        hostname=self._check.resolved_hostname,
                    )
                    return plan, None
            except pymysql.err.DatabaseError as e:
                if len(e.args) != 2:
                    raise
                error_state = ExplainState(
                    strategy=strategy, error_code=DBExplainErrorCode.database_error, error_message=str(type(e))
                )
                error_states.append(error_state)
                self._log.debug(
                    'Failed to collect execution plan. error=%s, strategy=%s, schema=%s, statement="%s"',
                    e.args,
                    strategy,
                    schema,
                    obfuscated_statement,
                )
                continue

        if is_optimal_strategy_cached and error_states:
            self._log.debug(
                'Caching execution plan failure for query to skip future explains %s: %s',
                error_states,
                obfuscated_statement,
            )
            self._explain_error_states_cache[query_cache_key] = error_states

        return None, error_states

    def _run_explain(self, schema, cursor, statement, obfuscated_statement):
        """
        Run the explain using the EXPLAIN statement
        """
        self._cursor_run(
            cursor,
            'EXPLAIN FORMAT=json {}'.format(statement),
            obfuscated_query='EXPLAIN FORMAT=json %s',
            obfuscated_params=obfuscated_statement,
        )
        return cursor.fetchone()[0]

    def _run_explain_procedure(self, schema, cursor, statement, obfuscated_statement):
        """
        Run the explain by calling the stored procedure if available.
        """
        try:
            self._cursor_run(cursor, 'CALL {}(%s)'.format(self._explain_procedure), statement, obfuscated_statement)
            return cursor.fetchone()[0]
        except pymysql.err.DatabaseError as e:
            if e.args[0] in PYMYSQL_MISSING_EXPLAIN_STATEMENT_PROC_ERRORS:
                err_msg = e.args[1] if len(e.args) > 1 else ''
                self._check.record_warning(
                    DatabaseConfigurationError.explain_plan_procedure_missing,
                    warning_with_tags(
                        "Unable to collect explain plans because the procedure '%s' is either undefined or not "
                        "granted access to in schema '%s'. See https://docs.datadoghq.com/database_monitoring/"
                        'setup_mysql/troubleshooting#%s for more details: (%d) %s',
                        self._explain_procedure,
                        schema,
                        DatabaseConfigurationError.explain_plan_procedure_missing.value,
                        e.args[0],
                        str(err_msg),
                        code=DatabaseConfigurationError.explain_plan_procedure_missing.value,
                        host=self._check.resolved_hostname,
                        schema=schema,
                    ),
                )
            raise

    def _run_fully_qualified_explain_procedure(self, schema, cursor, statement, obfuscated_statement):
        """
        Run the explain by calling the fully qualified stored procedure if available.
        """
        try:
            self._cursor_run(
                cursor, 'CALL {}(%s)'.format(self._fully_qualified_explain_procedure), statement, obfuscated_statement
            )
            return cursor.fetchone()[0]
        except pymysql.err.DatabaseError as e:
            if e.args[0] in PYMYSQL_MISSING_EXPLAIN_STATEMENT_PROC_ERRORS:
                err_msg = e.args[1] if len(e.args) > 1 else ''
                self._check.record_warning(
                    DatabaseConfigurationError.explain_plan_fq_procedure_missing,
                    warning_with_tags(
                        "Unable to collect explain plans because the procedure '%s' is either undefined or "
                        'not granted access to. See https://docs.datadoghq.com/database_monitoring/setup_mysql/'
                        'troubleshooting#%s for more details: (%d) %s',
                        self._fully_qualified_explain_procedure,
                        DatabaseConfigurationError.explain_plan_fq_procedure_missing.value,
                        e.args[0],
                        str(err_msg),
                        code=DatabaseConfigurationError.explain_plan_fq_procedure_missing.value,
                        host=self._check.resolved_hostname,
                    ),
                )
            raise

    @staticmethod
    def _can_explain(obfuscated_statement):
        return obfuscated_statement.split(' ', 1)[0].lower() in SUPPORTED_EXPLAIN_STATEMENTS
