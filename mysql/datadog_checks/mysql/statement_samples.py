import json
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import closing

import pymysql
import time
from cachetools import TTLCache
from datadog import statsd
from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature, \
    submit_statement_sample_events
from datadog_checks.base.utils.db.utils import ConstantRateLimiter, ExpiringCache

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

VALID_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update'})

# default sampling settings for events_statements_* tables
# rate limit is in samples/second
# {table -> rate-limit}
DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS = {
    'events_statements_history_long': 1 / 10,
    'events_statements_history': 1,
    'events_statements_current': 10,
}

mysql_statement_sample_keys = [
    'lock_time',
    'rows_affected',
    'rows_sent',
    'rows_examined',
    'select_full_join',
    'select_full_range_join',
    'select_range',
    'select_range_check',
    'select_scan',
    'sort_merge_passes',
    'sort_range',
    'sort_rows',
    'sort_scan',
    'no_index_used',
    'no_good_index_used',
]

# columns from events_statements_summary tables which correspond to attributes common to all databases and are
# therefore stored under other standard keys
events_statements_sample_exclude_keys = {
    # gets obfuscated
    'sql_text',
    # stored as "instance"
    'current_schema',
    # used for signature
    'digest_text',
    'timer_end_time_s',
    'max_timer_wait_ns',
    'timer_start'
}


class MySQLStatementSamples(object):
    executor = ThreadPoolExecutor()

    """
    Mixin for collecting statement samples from query samples. Where defined, the user will attempt
    to use the stored procedure `explain_statement` which allows collection of statement samples
    using the permissions of the procedure definer.
    """

    def __init__(self, config, connection_args):
        # checkpoint at zero so we pull the whole history table on the first run
        self._config = config
        self._connection_args = connection_args
        self._checkpoint = 0
        self._log = get_check_logger()
        self._last_check_run = None
        self._db = None
        self._tags = None
        self._tags_str = None
        self._service = "mysql"
        self._collection_loop_future = None
        self._rate_limiter = ConstantRateLimiter(1)
        self._collection_strategy_cache = TTLCache(maxsize=1000, ttl=600)
        self._seen_statements_cache = TTLCache(maxsize=1000, ttl=60)
        self._seen_statements_plan_sigs_cache = TTLCache(maxsize=1000, ttl=60)

    def run_sampler(self, tags):
        """
        start the sampler thread if not already running
        :param tags:
        :return:
        """
        self._tags = tags
        self._tags_str = ','.join(tags)
        for t in self._tags:
            if t.startswith('service:'):
                self._service = t[len('service:'):]
        self._last_check_run = time.time()
        if self._collection_loop_future is None or not self._collection_loop_future.running():
            # if it was 'not running' it could have crashed
            self._log.info("starting mysql statement sampler")
            self._collection_loop_future = MySQLStatementSamples.executor.submit(self.collection_loop)
        else:
            self._log.debug("mysql statement sampler already running")

    def collection_loop(self):
        try:
            # reconnect at the start of each connection loop
            # if the connection fails for whatever reason the loop will exit and be restarted on the next check run
            # pymysql connections are not thread safe so we can't reuse the same connection from the main check
            # in this thread
            self._db = pymysql.connect(**self._connection_args)
            self._log.info("started mysql statement sampler collection loop")
            while True:
                # if the instance check has stopped running for any reason then the collection loop must shut down
                # this is to ensure that we have only one collection_loop running per check instance
                if self._last_check_run and time.time() - self._last_check_run > self._config.min_collection_interval \
                        * 2:
                    self._log.info("stopping mysql statement sampler collection loop due to check inactivity")
                    break

                self._rate_limiter.sleep()

                events_statements_table, collect_exec_plans_rate_limit = self._get_sample_collection_strategy()
                if not events_statements_table:
                    continue

                if self._rate_limiter.rate_limit_s is None or self._rate_limiter.rate_limit_s != \
                        collect_exec_plans_rate_limit:
                    # TODO: should this be (queries collected/s) or (collection loop runs/s)?
                    self._rate_limiter = ConstantRateLimiter(collect_exec_plans_rate_limit)

                self.collect_statement_samples(events_statements_table)
        except Exception:
            self._log.exception("mysql statement sampler collection loop failure")

    def _get_events_statements_by_digest(self, events_statements_table, row_limit):
        start = time.time()

        # Select the most recent events with a bias towards events which have higher wait times
        query = """
            SELECT current_schema AS current_schema,
                   sql_text,
                   IFNULL(digest_text, sql_text) AS digest_text,
                   timer_start,
                   UNIX_TIMESTAMP()-(select VARIABLE_VALUE from information_schema.global_status
                            where VARIABLE_NAME='UPTIME')+timer_end*1e-12 as timer_end_time_s,
                   MAX(timer_wait) / 1000 AS max_timer_wait_ns,
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
                   no_good_index_used
              FROM performance_schema.{}
             WHERE sql_text IS NOT NULL
               AND event_name like %s
               AND digest_text NOT LIKE %s
               AND timer_start > %s
          GROUP BY digest
          ORDER BY timer_wait DESC
              LIMIT %s
            """.format(
            events_statements_table
        )

        with closing(self._db.cursor(pymysql.cursors.DictCursor)) as cursor:
            params = ('statement/%', 'EXPLAIN %', self._checkpoint, row_limit)
            self._log.debug("running query: " + query, *params)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                self._log.debug("no statements found in performance_schema.%s", events_statements_table)
                return rows
            self._checkpoint = max(r['timer_start'] for r in rows)
            cursor.execute('SET @@SESSION.sql_notes = 0')
            tags = ["table:%s".format(events_statements_table)] + self._tags
            statsd.increment("dd.mysql.events_statements_by_digest.rows", len(rows), tags=tags)
            statsd.timing("dd.mysql.events_statements_by_digest.time", (time.time() - start) * 1000, tags=tags)
            return rows

    def _collect_plans_for_statements(self, rows):
        num_sent = 0
        num_truncated = 0
        for row in rows:
            if not row or not all(row):
                self._log.debug('Row was unexpectedly truncated or events_statements_history_long table is not enabled')
                continue

            sql_text = row['sql_text']
            if not sql_text:
                continue

            # TODO: ingest these anyway without plans
            # The SQL_TEXT column will store 1024 chars by default. Plans cannot be captured on truncated
            # queries, so the `performance_schema_max_sql_text_length` variable must be raised.
            if sql_text[-3:] == '...':
                num_truncated += 1
                continue

            # Plans have several important signatures to tag events with:
            # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
            # - `resource_hash` - hash computed off the raw sql text to match apm resources
            # - `query_signature` - hash computed from the digest text to match query metrics
            # TODO: add configurable ratelimiting for explains/s
            plan = self._attempt_explain_safe(sql_text, row['current_schema'])
            if plan:
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True) if plan else None
                obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
                plan_signature = compute_exec_plan_signature(normalized_plan)
                plan_cost = self._parse_execution_plan_cost(plan)
            else:
                normalized_plan, obfuscated_plan, plan_signature, plan_cost = None, None, None, None

            obfuscated_statement = datadog_agent.obfuscate_sql(sql_text)
            query_signature = compute_sql_signature(datadog_agent.obfuscate_sql(row['digest_text']))
            apm_resource_hash = compute_sql_signature(obfuscated_statement)
            statement_plan_sig = (query_signature, plan_signature)

            if statement_plan_sig not in self._seen_statements_cache:
                self._seen_statements_cache[statement_plan_sig] = True
                yield {
                    "timestamp": row["timer_end_time_s"] * 1000,
                    # TODO: if "localhost" then use agent hostname instead
                    "host": self._config.host,
                    "service": self._service,
                    "ddsource": "mysql",
                    "ddtags": self._tags_str,
                    "duration": row['max_timer_wait_ns'],
                    # Missing for now
                    # "network": {
                    #     "client": {
                    #         "ip": "10.10.10.10",
                    #         "port": 5432
                    #     }
                    # },
                    "db": {
                        "instance": row['current_schema'],
                        "plan": {
                            "definition": obfuscated_plan,
                            "cost": plan_cost,
                            "signature": plan_signature
                        },
                        "query_signature": query_signature,
                        "resource_hash": apm_resource_hash,
                        "statement": obfuscated_statement
                    },
                    'mysql': {k: v for k, v in row.items() if k not in events_statements_sample_exclude_keys},
                }
                num_sent += 1
                # TODO: add debug

        if num_truncated > 0:
            self._log.debug(
                'Unable to collect %d/%d statement samples due to truncated SQL text. Consider raising '
                '`performance_schema_max_sql_text_length` to capture these queries.',
                num_truncated,
                num_truncated + num_sent,
            )

    def _get_enabled_performance_schema_consumers(self):
        """
        Returns the list of available performance schema consumers
        I.e. (events_statements_current, events_statements_history)
        :return:
        """
        with closing(self._db.cursor()) as cursor:
            cursor.execute("SELECT name from performance_schema.setup_consumers WHERE enabled = 'YES'")
            enabled_consumers = set([r[0] for r in cursor.fetchall()])
            self._log.debug("loaded enabled consumers: %s", enabled_consumers)
            return enabled_consumers

    def _performance_schema_enable_consumer(self, name):
        query = """UPDATE performance_schema.setup_consumers SET enabled = 'YES' WHERE name = %s"""
        with closing(self._db.cursor()) as cursor:
            try:
                cursor.execute(query, name)
                self._log.debug('successfully enabled performance_schema consumer %s', name)
                return True
            except pymysql.err.DatabaseError as e:
                if e.args[0] == 1290:
                    # --read-only mode failure is expected so log at debug level
                    self._log.debug('failed to enable performance_schema consumer %s: %s', name, e)
                    return False
                self._log.debug('failed to enable performance_schema consumer %s: %s', name, e)
        return False

    def _get_sample_collection_strategy(self):
        """
        Decides on the plan collection strategy:
        - which events_statement_history-* table are we using
        - how long should the rate and time limits be
        :return: (table, rate_limit)
        """
        cached_strategy = self._collection_strategy_cache.get("plan_collection_strategy")
        if cached_strategy:
            self._log.debug("using cached plan_collection_strategy: %s", cached_strategy)
            return cached_strategy

        auto_enable = is_affirmative(self._config.options.get('auto_enable_events_statements_consumers', False))
        enabled_consumers = self._get_enabled_performance_schema_consumers()

        # unless a specific table is configured, we try all of the events_statements tables in descending order of
        # preference
        preferred_tables = ['events_statements_history_long', 'events_statements_history', 'events_statements_current']

        # optional user override
        events_statements_table = self._config.options.get('events_statements_table', None)
        if events_statements_table:
            if events_statements_table in DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS:
                preferred_tables = [events_statements_table]
            else:
                self._log.warning(
                    "invalid events_statements_table: %s. must be one of %s",
                    events_statements_table,
                    ', '.join(DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS.keys()),
                )

        chosen_table = None
        collect_exec_plans_rate_limit = self._config.options.get('collect_exec_plans_rate_limit', -1)

        for table in preferred_tables:
            if table not in enabled_consumers:
                if not auto_enable:
                    self._log.debug("performance_schema consumer for table %s not enabled")
                    continue
                if not self._performance_schema_enable_consumer(table):
                    continue
                self._log.debug("successfully enabled performance_schema consumer")
            rows = self._get_events_statements_by_digest(table, 1)
            if not rows:
                self._log.debug("no statements found in %s", table)
                continue
            if collect_exec_plans_rate_limit < 0:
                collect_exec_plans_rate_limit = DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS[table]
            chosen_table = table
            break

        if not chosen_table:
            self._log.info(
                "no valid performance_schema.events_statements table found. cannot collect statement samples.")
            return None, None

        # cache only successful strategies
        # should be short enough that we'll reflect updates "relatively quickly"
        # i.e., an aurora replica becomes a master (or vice versa).
        strategy = (chosen_table, collect_exec_plans_rate_limit)
        self._log.debug("found plan collection strategy. chosen_table=%s, rate_limit=%s", chosen_table,
                        collect_exec_plans_rate_limit)
        self._collection_strategy_cache["plan_collection_strategy"] = strategy
        return strategy

    def collect_statement_samples(self, events_statements_table):
        start_time = time.time()

        rows = self._get_events_statements_by_digest(
            events_statements_table, self._config.options.get('events_statements_row_limit', 5000)
        )
        events = self._collect_plans_for_statements(rows)
        submit_statement_sample_events(events)

        statsd.gauge("dd.mysql.collect_statement_samples.total.time",
                     (time.time() - start_time) * 1000,
                     tags=self._tags)
        statsd.gauge("dd.mysql.collect_statement_samples.seen_statements",
                     len(self._seen_statements_cache),
                     tags=self._tags)
        statsd.gauge("dd.mysql.collect_statement_samples.seen_statement_plan_sigs",
                     len(self._seen_statements_plan_sigs_cache),
                     tags=self._tags)

    def _attempt_explain_safe(self, sql_text, schema):
        start_time = time.time()
        with closing(self._db.cursor()) as cursor:
            # TODO: run these asynchronously / do some benchmarking to optimize
            try:
                plan = self._attempt_explain(cursor, sql_text, schema)
                statsd.timing("dd.mysql.run_explain.time", (time.time() - start_time) * 1000, tags=self._tags)
                return plan
            except Exception:
                self._log.exception("failed to run explain on query %s", sql_text)

    def _attempt_explain(self, cursor, statement, schema):
        """
        Tries the available methods used to explain a statement for the given schema. If a non-retryable
        error occurs (such as a permissions error), then statements executed under the schema will be
        disallowed in future attempts.
        """
        explain_strategy_none = 'NONE'
        explain_strategy_procedure = 'PROCEDURE'
        explain_strategy_statement = 'STATEMENT'

        fns_by_strategy = {
            explain_strategy_procedure: self._run_explain_procedure,
            explain_strategy_statement: self._run_explain,
        }

        plan = None
        strategy_cache_key = 'explain_strategy:%s' % schema

        # Obfuscate the statement for logging
        obfuscated_statement = datadog_agent.obfuscate_sql(statement)

        if not self._can_explain(statement):
            self._log.debug('Skipping statement which cannot be explained: %s', obfuscated_statement)
            return None

        if self._collection_strategy_cache.get(strategy_cache_key) == explain_strategy_none:
            self._log.debug('Skipping statement due to cached collection failure: %s', obfuscated_statement)
            return None

        exceptions = (pymysql.err.InternalError, pymysql.err.ProgrammingError)
        non_retryable_errors = frozenset(
            {
                1044,  # access denied on database
                1046,  # no permission on statement
                1049,  # unknown database
                1305,  # procedure does not exist
                1370,  # no execute on procedure
            }
        )

        try:
            # Switch to the right schema; this is necessary when the statement uses non-fully qualified tables
            # e.g. `select * from mytable` instead of `select * from myschema.mytable`
            self._use_schema(cursor, schema)
        except exceptions as e:
            if len(e.args) != 2:
                raise
            if e.args[0] in non_retryable_errors:
                self._collection_strategy_cache[strategy_cache_key] = explain_strategy_none
            self._log.debug(
                'Cannot collect execution plan because %s schema could not be accessed: %s, statement: %s',
                schema,
                e.args,
                obfuscated_statement,
            )
            return None

        # Use a cached strategy for the schema, if any, or try each strategy to collect plans
        strategies = list(fns_by_strategy.keys())
        cached = self._collection_strategy_cache.get(strategy_cache_key)
        if cached is not None:
            strategies.remove(cached)
            strategies.insert(0, cached)

        for strategy in strategies:
            fn = fns_by_strategy[strategy]

            try:
                plan = fn(cursor, statement)
            except exceptions as e:
                if len(e.args) != 2:
                    raise
                if e.args[0] in non_retryable_errors:
                    self._collection_strategy_cache[strategy_cache_key] = explain_strategy_none
                self._log.debug(
                    'Failed to collect statement with strategy %s, error: %s, statement: %s',
                    strategy,
                    e.args,
                    obfuscated_statement,
                )
                continue

            if plan:
                self._collection_strategy_cache[strategy_cache_key] = strategy
                break

        if not plan:
            self._log.info(
                'Cannot collect execution plan for statement (enable debug logs to log attempts): %s',
                obfuscated_statement,
            )

        return plan

    def _use_schema(self, cursor, schema):
        """
        Switch to the schema, if specified. Schema may not always be required for a session as long
        as fully-qualified schema and tables are used in the query. These should always be valid for
        running an explain.
        """
        if schema is not None:
            cursor.execute('USE `{}`'.format(schema))

    def _run_explain(self, cursor, statement):
        """
        Run the explain using the EXPLAIN statement
        """
        cursor.execute('EXPLAIN FORMAT=json {statement}'.format(statement=statement))
        return cursor.fetchone()[0]

    def _run_explain_procedure(self, cursor, statement):
        """
        Run the explain by calling the stored procedure `explain_statement` if available.
        """
        cursor.execute('CALL explain_statement(%s)', statement)
        return cursor.fetchone()[0]

    @staticmethod
    def _can_explain(statement):
        # TODO: cleaner query cleaning to strip comments, etc.
        return statement.strip().split(' ', 1)[0].lower() in VALID_EXPLAIN_STATEMENTS

    @staticmethod
    def _parse_execution_plan_cost(execution_plan):
        """
        Parses the total cost from the execution plan, if set. If not set, returns cost of 0.
        """
        cost = json.loads(execution_plan).get('query_block', {}).get('cost_info', {}).get('query_cost', 0.0)
        return float(cost or 0.0)
