# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
import time
from collections import namedtuple
from contextlib import closing
from enum import Enum
from operator import attrgetter

import pymysql
from cachetools import TTLCache

from datadog_checks.mysql.cursor import CommenterCursor, CommenterDictCursor

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

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

from .util import (
    DatabaseConfigurationError,
    StatementTruncationState,
    connect_with_session_variables,
    get_truncation_state,
    warning_with_tags,
)

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
    'end_event_id',
    'uptime',
    'now',
    'timer_end',
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
        end_event_id,
        timer_start,
        @uptime as uptime,
        unix_timestamp() as now,
        timer_end,
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

UPTIME_SUBQUERY = re.sub(
    r'\s+',
    ' ',
    """
    (SELECT VARIABLE_VALUE
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
    AND name != 'events_statements_cpu'
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

# the max value of unsigned BIGINT type column
BIGINT_MAX = 2**64 - 1


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
            'TIDB_STATEMENT': self._run_explain_tidb,
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
            self._db = connect_with_session_variables(**self._connection_args)
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
                hostname=self._check.reported_hostname,
            )
            raise

    def _get_tidb_statement_samples(self):
        """
        Get statement samples from TiDB's cluster_statements_summary table.

        TiDB doesn't have events_statements_current, but we can use cluster_statements_summary
        with QUERY_SAMPLE_TEXT which contains a sample query for each digest.
        """
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            # TiDB-specific query to get statement samples
            query = """
            SELECT
                SCHEMA_NAME as current_schema,
                QUERY_SAMPLE_TEXT as sql_text,
                DIGEST as digest,
                DIGEST_TEXT as digest_text,
                -- TiDB doesn't have these fields, so we'll use calculated values
                0 as end_event_id,
                unix_timestamp() * 1000000000 - AVG_LATENCY as timer_start,
                0 as uptime,
                unix_timestamp() as now,
                unix_timestamp() * 1000000000 as timer_end,
                AVG_LATENCY as timer_wait_ns,
                0 as lock_time_ns,
                AVG_AFFECTED_ROWS as rows_affected,
                AVG_RESULT_ROWS as rows_sent,
                -- TiDB doesn't track rows_examined separately, use AVG_PROCESSED_KEYS as approximation
                AVG_PROCESSED_KEYS as rows_examined,
                -- TiDB doesn't have these performance counters, set to 0
                0 as select_full_join,
                0 as select_full_range_join,
                0 as select_range,
                0 as select_range_check,
                0 as select_scan,
                0 as sort_merge_passes,
                0 as sort_range,
                0 as sort_rows,
                0 as sort_scan,
                0 as no_index_used,
                0 as no_good_index_used,
                SAMPLE_USER as processlist_user,
                INSTANCE as processlist_host,
                SCHEMA_NAME as processlist_db,
                PLAN as execution_plan
            FROM information_schema.cluster_statements_summary
            WHERE QUERY_SAMPLE_TEXT IS NOT NULL
                AND QUERY_SAMPLE_TEXT != ''
                AND DIGEST_TEXT IS NOT NULL
                AND DIGEST_TEXT NOT LIKE 'EXPLAIN %'
                AND LAST_SEEN > DATE_SUB(NOW(), INTERVAL 1 MINUTE)
            ORDER BY LAST_SEEN DESC
            LIMIT 100
            """
            self._cursor_run(cursor, query)
            return cursor.fetchall()

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def _get_new_events_statements_current(self):
        start = time.time()

        # Check if this is TiDB and use appropriate query
        if self._check._get_is_tidb(self._db):
            rows = self._get_tidb_statement_samples()
        else:
            with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
                self._cursor_run(
                    cursor,
                    "set @uptime = {}".format(UPTIME_SUBQUERY.format(global_status_table=self._global_status_table)),
                )
                self._cursor_run(cursor, EVENTS_STATEMENTS_CURRENT_QUERY)
                rows = cursor.fetchall()

        table_name = (
            "information_schema.cluster_statements_summary"
            if self._check._get_is_tidb(self._db)
            else EVENTS_STATEMENTS_TABLE
        )
        tags = self._tags + ["events_statements_table:{}".format(table_name)] + self._check._get_debug_tags()
        self._check.histogram(
            "dd.mysql.get_new_events_statements.time",
            (time.time() - start) * 1000,
            tags=tags,
            hostname=self._check.reported_hostname,
        )
        self._check.histogram(
            "dd.mysql.get_new_events_statements.rows", len(rows), tags=tags, hostname=self._check.reported_hostname
        )
        self._log.debug("Read %s rows from %s", len(rows), table_name)
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
                hostname=self._check.reported_hostname,
            )
            return None

        obfuscated_statement = statement['query']
        obfuscated_digest_text = statement_digest_text['query']
        apm_resource_hash = compute_sql_signature(obfuscated_statement)
        query_signature = compute_sql_signature(obfuscated_digest_text)

        query_cache_key = (row['current_schema'], query_signature)
        if not self._explained_statements_ratelimiter.acquire(query_cache_key):
            return None

        # For TiDB, check if we already have the execution plan from cluster_statements_summary
        tidb_plan_text = None
        if self._check._get_is_tidb(self._db):
            plan = None
            error_states = []

            # Use text PLAN if available
            if not plan and 'execution_plan' in row and row['execution_plan']:
                # TiDB's PLAN column contains text format, not JSON
                # Store it separately to skip obfuscation later
                tidb_plan_text = row['execution_plan']
                # Handle both string and bytes
                if isinstance(tidb_plan_text, bytes):
                    tidb_plan_text = tidb_plan_text.decode('utf-8')
                # Set plan to a special marker so we know we have a TiDB text plan
                plan = "TIDB_TEXT_PLAN"
                self._log.debug(
                    'Using pre-fetched text execution plan from TiDB cluster_statements_summary for statement: %s',
                    obfuscated_statement,
                )

            # If we couldn't get a plan from TiDB columns, fall through to normal explain
            if not plan:
                with closing(self._get_db_connection().cursor(CommenterCursor)) as cursor:
                    plan, error_states = self._explain_statement(
                        cursor, row['sql_text'], row['current_schema'], obfuscated_statement, query_signature
                    )
        else:
            with closing(self._get_db_connection().cursor(CommenterCursor)) as cursor:
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
                    hostname=self._check.reported_hostname,
                )
                collection_errors.append(
                    {
                        'strategy': state.strategy,
                        'code': state.error_code.value if state.error_code else None,
                        'message': state.error_message,
                    }
                )

        normalized_plan, obfuscated_plan, plan_signature = None, None, None
        tidb_native_plan = None  # Store the native TiDB plan for mysql.execution_plan

        if plan:
            # Special handling for TiDB text plans
            if plan == "TIDB_TEXT_PLAN" and tidb_plan_text:
                # Parse TiDB text plan into JSON format
                tidb_native_plan = self._parse_tidb_text_plan(tidb_plan_text)
                self._log.debug(
                    "TiDB native plan type: %s, content: %s",
                    type(tidb_native_plan),
                    tidb_native_plan[:200] if len(tidb_native_plan) > 200 else tidb_native_plan,
                )
                # Convert to MySQL-compatible format for plan.definition
                mysql_compatible_plan = self._convert_tidb_plan_to_mysql_format(tidb_native_plan)
                self._log.debug(
                    "MySQL-compatible plan type: %s, content: %s",
                    type(mysql_compatible_plan),
                    mysql_compatible_plan[:200] if len(mysql_compatible_plan) > 200 else mysql_compatible_plan,
                )
                normalized_plan = mysql_compatible_plan
                obfuscated_plan = mysql_compatible_plan
                # Create a signature from the MySQL-compatible plan
                plan_signature = compute_sql_signature(mysql_compatible_plan)
            else:
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
            event_timestamp = time.time() * 1000

            if self._has_sampled_since_completion(row, event_timestamp):
                return None

            # For TiDB, update execution_plan with the native JSON format
            if tidb_native_plan:
                # Create a copy of the row to avoid modifying the original
                row = dict(row)
                # Replace the text execution_plan with the native TiDB JSON array
                # Ensure it's a string, not bytes
                if isinstance(tidb_native_plan, bytes):
                    row['execution_plan'] = tidb_native_plan.decode('utf-8')
                else:
                    row['execution_plan'] = tidb_native_plan

            event = {
                "timestamp": event_timestamp,
                "dbm_type": "plan",
                "host": self._check.reported_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "mysql",
                "ddtags": self._tags_str,
                "duration": row['timer_wait_ns'],
                "network": {
                    "client": {
                        "ip": row.get('processlist_host', None),
                    }
                },
                "cloud_metadata": self._config.cloud_metadata,
                'service': self._config.service,
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

            # For TiDB, add the node instance information
            if self._check._get_is_tidb(self._db) and row.get('processlist_host'):
                event['tidb'] = {'node_instance': row['processlist_host']}

            return event

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def _collect_plans_for_statements(self, rows):
        for row in rows:
            try:
                if not row['timer_end']:
                    # If an event is produced from an instrument that has TIMED = NO,
                    # timing information is not collected,
                    # and TIMER_START, TIMER_END, and TIMER_WAIT are all NULL.
                    self._log.debug("Skipping statement with missing timer_end: %s", row)
                    continue
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
        with closing(self._get_db_connection().cursor(CommenterCursor)) as cursor:
            self._cursor_run(cursor, ENABLED_STATEMENTS_CONSUMERS_QUERY)
            return {r[0] for r in cursor.fetchall()}

    def _enable_events_statements_consumers(self):
        """
        Enable events statements consumers
        :return:
        """
        try:
            with closing(self._get_db_connection().cursor(CommenterCursor)) as cursor:
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

        # Check if this is TiDB - it doesn't have performance_schema consumers
        if self._check._get_is_tidb(self._db):
            self._log.debug("TiDB detected, using TiDB statement samples strategy")
            # For TiDB, use TIDB_STATEMENT strategy since it doesn't support FORMAT=json or stored procedures
            self._preferred_explain_strategies = ['TIDB_STATEMENT']
            collection_interval = self._configured_collection_interval
            if collection_interval < 0:
                collection_interval = 10  # Default 10 seconds for TiDB
            strategy = ("information_schema.cluster_statements_summary", collection_interval)
            self._collection_strategy_cache["events_statements_strategy"] = strategy
            return strategy

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
                    host=self._check.reported_hostname,
                ),
            )
            self._check.count(
                "dd.mysql.query_samples.error",
                1,
                tags=self._tags + ["error:no-enabled-events-statements-consumers"] + self._check._get_debug_tags(),
                hostname=self._check.reported_hostname,
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
            hostname=self._check.reported_hostname,
        )
        self._check.count(
            "dd.mysql.collect_statement_samples.events_submitted.count",
            submitted_count,
            tags=tags,
            hostname=self._check.reported_hostname,
        )
        self._check.gauge(
            "dd.mysql.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=tags,
            hostname=self._check.reported_hostname,
        )
        self._check.gauge(
            "dd.mysql.collect_statement_samples.explained_statements_cache.len",
            len(self._explained_statements_ratelimiter),
            tags=tags,
            hostname=self._check.reported_hostname,
        )
        self._check.gauge(
            "dd.mysql.collect_statement_samples.collection_strategy_cache.len",
            len(self._collection_strategy_cache),
            tags=tags,
            hostname=self._check.reported_hostname,
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
            self._log.warning(
                'Failed to collect execution plan. '
                'Check that the `explain_statement` function exists in the schema `%s`. '
                'See '
                'https://docs.datadoghq.com/database_monitoring/setup_mysql/troubleshooting/'
                '#explain-plan-fq-procedure-missing. '
                'error=%s: %s',
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
                        hostname=self._check.reported_hostname,
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

    def _run_explain_tidb(self, schema, cursor, statement, obfuscated_statement):
        """
        Run the explain for TiDB which uses FORMAT=tidb_json instead of FORMAT=json

        TiDB EXPLAIN documentation: https://docs.pingcap.com/tidb/stable/sql-statement-explain/

        Note: TiDB's cluster_statements_summary table stores normalized queries with placeholders (?).
        Since TiDB EXPLAIN doesn't support parameterized queries, we cannot collect execution plans
        when only the parameterized query is available.

        Note: For TiDB, execution plans are primarily retrieved from the PLAN column in
        information_schema.cluster_statements_summary table, which contains pre-collected
        execution plans in text format. The execution statistics are embedded within this
        text plan. This method is used as a fallback when the PLAN column is not available.
        """
        # Check if the statement contains placeholders
        if '?' in statement:
            self._log.debug(
                'Skipping TiDB EXPLAIN for parameterized query (placeholders detected): %s', obfuscated_statement
            )
            # Return None to indicate we cannot collect the plan
            return None

        try:
            cursor.execute('EXPLAIN FORMAT=tidb_json {}'.format(statement))
            return cursor.fetchone()[0]
        except Exception as e:
            # Log with obfuscated statement for security
            self._log.debug('TiDB EXPLAIN failed for statement: %s, error: %s', obfuscated_statement, e)
            raise

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
                        host=self._check.reported_hostname,
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
                        host=self._check.reported_hostname,
                    ),
                )
            raise

    def _has_sampled_since_completion(self, row, event_timestamp):
        # TiDB doesn't have end_event_id, so always return False for TiDB
        if self._check._get_is_tidb(self._db):
            return False

        # If the query has finished end_event_id will be set
        if row['end_event_id']:
            query_end_time = self._calculate_timer_end(row)
            time_diff = abs(event_timestamp - query_end_time)
            window_ms = self._seen_samples_ratelimiter.ttl * 1000
            # When some clients hold a connection open they also hold a server thread open.
            # If the client issues queries infrequently we will sample the same query multiple times
            # since it will still exist in events_statements_current table.
            # This check ensures we only emit an event for a completed query on the first sample check after completion.
            if time_diff > window_ms:
                return True
        return False

    @staticmethod
    def _can_explain(obfuscated_statement):
        return obfuscated_statement.split(' ', 1)[0].lower() in SUPPORTED_EXPLAIN_STATEMENTS

    def _parse_tidb_text_plan(self, plan_text):
        """
        Parse TiDB text execution plan into a structured JSON format.

        TiDB plan format has tab-separated columns:
        id, task, estRows, operator info, actRows, execution info, memory, disk
        """
        try:
            # Handle escaped newlines and tabs if present
            if '\\n' in plan_text or '\\t' in plan_text:
                plan_text = plan_text.replace('\\n', '\n').replace('\\t', '\t')

            lines = plan_text.strip().split('\n')
            if len(lines) < 2:  # Need at least header and one data line
                return json.dumps({"raw_plan": plan_text})

            # Skip the first line (header) and process data lines
            # Parse header to understand column order
            header_line = lines[0]
            headers = header_line.split('\t')
            self._log.debug("TiDB plan headers: %s", headers)
            self._log.debug("TiDB plan header count: %d", len(headers))

            # Based on the user's output showing the data is shifted left by 1,
            # it seems like there might be an extra header column that doesn't have data
            # Or the data has one less column than the headers

            # Build flat array of nodes (TiDB format)
            nodes = []

            for i, line in enumerate(lines[1:]):  # Skip header line
                if not line.strip():
                    continue

                # Split by tabs - TiDB uses tabs to separate columns
                parts = line.split('\t')

                # Debug first data line
                if i == 0:
                    self._log.debug("TiDB plan first data line parts: %s", parts)
                    self._log.debug("TiDB plan parts count: %d, expected: %d", len(parts), len(headers))

                # Based on the output, it seems the data columns are consistently shifted
                # Let's check if we have the expected number of parts
                if len(parts) < 8:
                    self._log.debug("TiDB plan line has only %d columns, expected 8", len(parts))
                    continue

                # Try to detect if there's an empty first column
                # If the first part is empty or just whitespace/tree chars, shift everything
                if not parts[0].strip() or parts[0].strip() in ['', '└', '├', '│']:
                    # Empty first column, shift all indices by 1
                    if len(parts) < 9:
                        self._log.debug("TiDB plan with empty first column has only %d columns, need 9", len(parts))
                        continue
                    id_value = parts[1]
                    task_value = parts[2]
                    estrows_value = parts[3]
                    operator_value = parts[4]
                    actrows_value = parts[5]
                    execution_value = parts[6]
                    memory_value = parts[7]
                    disk_value = parts[8]
                else:
                    # Normal column positions
                    id_value = parts[0]
                    task_value = parts[1]
                    estrows_value = parts[2]
                    operator_value = parts[3]
                    actrows_value = parts[4]
                    execution_value = parts[5]
                    memory_value = parts[6]
                    disk_value = parts[7]

                # Clean up the id field by removing tree prefixes (└─, ├─, spaces) and trailing spaces
                clean_id = id_value.lstrip('└├─ \t').rstrip()

                # Debug output to understand the mapping
                if i == 0:
                    self._log.debug(
                        "TiDB plan mapping - id_value: %s, task_value: %s, estrows_value: %s",
                        id_value,
                        task_value,
                        estrows_value,
                    )

                # Looking at the output, it seems the JSON field order doesn't match our mapping
                # The output shows taskType:"Projection_7" when we set id: clean_id
                # This suggests the fields are being reordered or renamed somewhere
                # Let's create the node with the correct mapping based on the actual output

                # Based on the output pattern, it appears that:
                # What we call 'id' appears as 'taskType' in output
                # What we call 'taskType' appears as 'estRows' in output
                # And so on... everything is shifted

                # Create node object with all values properly trimmed
                node = {
                    'id': clean_id,  # Already cleaned and trimmed
                    'taskType': task_value.strip(),  # Remove all whitespace
                    'estRows': estrows_value.strip(),  # Remove all whitespace
                    'operatorInfo': operator_value.strip() if operator_value.strip() else None,  # camelCase
                    'actRows': actrows_value.strip(),  # Remove all whitespace
                    'executionInfo': execution_value.strip() if execution_value.strip() else None,  # camelCase
                    'memory': memory_value.strip() if memory_value.strip() != 'N/A' else None,
                    'disk': disk_value.strip() if disk_value.strip() != 'N/A' else None,
                }

                # Parse numeric values
                for field in ['estRows', 'actRows']:
                    value = node[field]
                    if value and value != 'N/A':
                        try:
                            # Keep as string with decimal if present (matching TiDB format)
                            if '.' in value:
                                node[field] = value  # Keep as "1.00" format
                            else:
                                node[field] = str(int(value))  # Convert to string integer
                        except ValueError:
                            # Keep as string if can't parse
                            pass
                    elif value == 'N/A':
                        node[field] = "0"

                # Remove empty/None fields to match TiDB's compact format
                node = {k: v for k, v in node.items() if v is not None and v != ''}

                nodes.append(node)

            # Return as flat array matching TiDB's FORMAT=tidb_json output
            return json.dumps(nodes)

        except Exception as e:
            # If parsing fails, return the original text wrapped in JSON
            self._log.debug("Failed to parse TiDB plan to JSON: %s", e)
            return json.dumps({"raw_plan": plan_text, "parse_error": str(e)})

    def _convert_tidb_plan_to_mysql_format(self, tidb_plan_json):
        """
        Convert TiDB plan JSON to MySQL-compatible format.

        TiDB format: [{"id": "Point_Get_1", "taskType": "root", ...}]
        MySQL format: {"query_block": {"select_id": 1, "table": {...}}}
        """
        try:
            # Parse the TiDB plan if it's a string or bytes
            if isinstance(tidb_plan_json, (str, bytes)):
                if isinstance(tidb_plan_json, bytes):
                    tidb_plan_json = tidb_plan_json.decode('utf-8')
                tidb_nodes = json.loads(tidb_plan_json)
            else:
                tidb_nodes = tidb_plan_json

            if not tidb_nodes or not isinstance(tidb_nodes, list):
                self._log.debug("TiDB plan is not a list, returning original: %s", type(tidb_nodes))
                return tidb_plan_json

            # Find the actual data access node (usually the deepest one with table info)
            table_node = None
            root_node = tidb_nodes[0]

            # Search through all nodes to find the one with table information
            for node in tidb_nodes:
                if 'table:' in node.get('operatorInfo', ''):
                    table_node = node
                    break

            # If no table node found, use the last node (deepest in the tree)
            if not table_node:
                table_node = tidb_nodes[-1] if tidb_nodes else root_node
                self._log.debug("No table node found, using last node: %s", table_node.get('id', 'unknown'))

            # Extract table information from the table node
            table_name = None
            access_type = "unknown"
            key_info = None

            # Try to extract table name and access pattern
            operator_info = table_node.get('operatorInfo', '')
            if operator_info:
                # Look for table name patterns
                if 'table:' in operator_info:
                    table_match = operator_info.split('table:')[1].split(',')[0].split()[0]
                    table_name = table_match

                # Determine access type based on operator id
                op_id = table_node.get('id', '')
                if 'Point_Get' in op_id:
                    access_type = 'const'  # MySQL uses 'const' for point lookups
                    # Extract key info if available
                    if 'index:' in operator_info:
                        key_info = operator_info.split('index:')[1].split(',')[0].split()[0]
                    elif (
                        'handle' in operator_info
                        or 'PRIMARY' in operator_info
                        or 'clustered index:PRIMARY' in operator_info
                    ):
                        key_info = 'PRIMARY'
                elif 'IndexRangeScan' in op_id or 'IndexLookUp' in op_id:
                    access_type = 'range'
                    if 'index:' in operator_info:
                        key_info = operator_info.split('index:')[1].split(',')[0].split()[0]
                elif 'TableFullScan' in op_id:
                    access_type = 'ALL'
                elif 'TableRangeScan' in op_id:
                    access_type = 'range'
                elif 'IndexReader' in op_id:
                    access_type = 'index'

            # Build MySQL-compatible structure
            mysql_format = {
                "query_block": {
                    "select_id": 1,
                    "cost_info": {
                        "query_cost": "0.00"  # TiDB doesn't provide cost in the same way
                    },
                }
            }

            # Add table information
            table_info = {
                "table_name": table_name or "unknown",
                "access_type": access_type,
                "rows_examined_per_scan": int(float(table_node.get('estRows', '0'))),
                "rows_produced_per_join": int(float(table_node.get('actRows', '0'))),
            }

            # Add key information if available
            if key_info:
                table_info["key"] = key_info
                table_info["used_key_parts"] = [key_info]

            # Add execution info if available
            if table_node.get('executionInfo'):
                table_info["execution_info"] = table_node['executionInfo']

            # Add operator info as a custom field
            if table_node.get('operatorInfo'):
                table_info["operator_info"] = table_node['operatorInfo']

            mysql_format["query_block"]["table"] = table_info

            # If there are multiple nodes, add them as a custom field
            if len(tidb_nodes) > 1:
                mysql_format["query_block"]["tidb_execution_tree"] = tidb_nodes

            result = json.dumps(mysql_format)
            self._log.debug("Converted TiDB plan to MySQL format successfully, type: %s", type(result))
            return result

        except Exception as e:
            self._log.debug("Failed to convert TiDB plan to MySQL format: %s", e)
            # Return original if conversion fails
            if isinstance(tidb_plan_json, bytes):
                return tidb_plan_json.decode('utf-8')
            return tidb_plan_json

    @staticmethod
    def _calculate_timer_end(row):
        """
        Calculate the timer_end_time_s from the timer_end, now and uptime fields
        """
        # timer_end is in picoseconds and uptime is in seconds
        # timer_end can overflow, so we need to calcuate how many times it overflowed
        timer_end = row['timer_end']
        now = row['now']
        uptime = int(row['uptime'])

        bigint_max_in_seconds = BIGINT_MAX * 1e-12
        # when timer_end is greater than bigint_max_in_seconds, we need to add the difference to the uptime
        seconds_to_add = uptime // bigint_max_in_seconds * bigint_max_in_seconds
        timer_end_time_s = now - uptime + seconds_to_add + timer_end * 1e-12
        return int(timer_end_time_s * 1000)
