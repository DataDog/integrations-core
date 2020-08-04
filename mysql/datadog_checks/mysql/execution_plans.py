import json
import time
from contextlib import closing

import pymysql

import datadog_agent
import pymysql
from datadog import statsd
from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.statement_metrics import is_dbm_enabled
from datadog_checks.base.utils.db.sql import compute_sql_signature, compute_exec_plan_signature, submit_exec_plan_events

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

from datadog_checks.base.utils.db.statement_metrics import is_dbm_enabled
from datadog_checks.base.utils.db.utils import ConstantRateLimiter, ExpiringCache

VALID_EXPLAIN_STATEMENTS = frozenset({
    'select',
    'table',
    'delete',
    'insert',
    'replace',
    'update',
})

# default sampling settings for events_statements_* tables
# rate limit is in samples/second
# {table -> rate-limit}
DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS = {
    'events_statements_history_long': 0,
    'events_statements_history': 1,
    'events_statements_current': 10,
}


class ExecutionPlansMixin(object):
    """
    Mixin for collecting execution plans from query samples.
    """

    def __init__(self, *args, **kwargs):
        # checkpoint at zero so we pull the whole history table on the first run
        self._checkpoint = 0
        self._expiring_cache = ExpiringCache()

    def _get_events_statements_by_digest(self, db, events_statements_table, row_limit):
        start = time.time()

        # Select the most recent events with a bias towards events which have higher wait times
        query = """
            SELECT current_schema AS current_schema,
                   sql_text AS sql_text,
                   IFNULL(digest_text, sql_text) AS digest_text,
                   timer_start AS timer_start,
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
            """.format(events_statements_table)

        with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
            params = ('statement/%', 'EXPLAIN %', self._checkpoint, row_limit)
            self.log.debug("running query. " + query, *params)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                self.log.debug("no statements found in performance_schema.%s", events_statements_table)
                return rows
            self._checkpoint = max(r['timer_start'] for r in rows)
            cursor.execute('SET @@SESSION.sql_notes = 0')
            statsd.increment("dd.mysql.events_statements_by_digest.rows", len(rows))
            statsd.timing("dd.mysql.events_statements_by_digest.time", (time.time() - start) * 1000)
            return rows

    def _collect_plans_for_statements(self, db, rows, seen_statement_plan_sigs, instance_tags):
        events = []
        num_truncated = 0

        for row in rows:
            if not row or not all(row):
                self.log.debug('Row was unexpectedly truncated or events_statements_history_long table is not enabled')
                continue
            schema = row['current_schema']
            sql_text = row['sql_text']
            digest_text = row['digest_text']
            duration_ns = row['max_timer_wait_ns']

            if not sql_text:
                continue

            # The SQL_TEXT column will store 1024 chars by default. Plans cannot be captured on truncated
            # queries, so the `performance_schema_max_sql_text_length` variable must be raised.
            if sql_text[-3:] == '...':
                num_truncated += 1
                continue

            with closing(db.cursor()) as cursor:
                # TODO: run these asynchronously / do some benchmarking to optimize
                plan = self._run_explain(cursor, sql_text, schema, instance_tags)
                if not plan:
                    continue
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True) if plan else None
                obfuscated_statement = datadog_agent.obfuscate_sql(sql_text)
                query_signature = compute_sql_signature(obfuscated_statement)
                plan_signature = compute_exec_plan_signature(normalized_plan)
                statement_plan_sig = (query_signature, plan_signature)
                if statement_plan_sig not in seen_statement_plan_sigs:
                    seen_statement_plan_sigs.add(statement_plan_sig)
                    events.append({
                        'duration': duration_ns,
                        'db': {
                            'instance': schema,
                            'statement': obfuscated_statement,
                            'query_signature': compute_sql_signature(obfuscated_statement),
                            'plan': plan,
                            'plan_cost': self._parse_execution_plan_cost(plan),
                            'plan_signature': plan_signature,
                            'debug': {
                                'normalized_plan': normalized_plan,
                                'obfuscated_plan': datadog_agent.obfuscate_sql_exec_plan(plan),
                                'digest_text': digest_text,
                            },
                            'mysql': {
                                'lock_time': row['lock_time_ns'],
                                'rows_affected': row['rows_affected'],
                                'rows_sent': row['rows_sent'],
                                'rows_examined': row['rows_examined'],
                                'select_full_join': row['select_full_join'],
                                'select_full_range_join': row['select_full_range_join'],
                                'select_range': row['select_range'],
                                'select_range_check': row['select_range_check'],
                                'select_scan': row['select_scan'],
                                'sort_merge_passes': row['sort_merge_passes'],
                                'sort_range': row['sort_range'],
                                'sort_rows': row['sort_rows'],
                                'sort_scan': row['sort_scan'],
                                'no_index_used': row['no_index_used'],
                                'no_good_index_used': row['no_good_index_used'],
                            }
                        }
                    })

        if num_truncated > 0:
            self.log.warning(
                'Unable to collect %d/%d execution plans due to truncated SQL text. Consider raising '
                '`performance_schema_max_sql_text_length` to capture these queries.',
                num_truncated,
                num_truncated + len(events)
            )

        return events

    def _get_enabled_performance_schema_consumers(self, db):
        with closing(db.cursor()) as cursor:
            cursor.execute("SELECT name from performance_schema.setup_consumers WHERE enabled = 'YES'")
            enabled_consumers = set([r[0] for r in cursor.fetchall()])
            self.log.debug("loaded enabled consumers: %s", enabled_consumers)
            return enabled_consumers

    def _performance_schema_enable_consumer(self, db, name):
        query = """UPDATE performance_schema.setup_consumers SET enabled = 'YES' WHERE name = %s"""
        with closing(db.cursor()) as cursor:
            try:
                cursor.execute(query, name)
                self.log.debug('successfully enabled performance_schema consumer %s', name)
                return True
            except pymysql.err.DatabaseError as e:
                if e.args[0] == 1290:
                    # --read-only mode failure is expected so log at debug level
                    self.log.debug('failed to enable performance_schema consumer %s: %s', name, e)
                    return False
                self.log.warning('failed to enable performance_schema consumer %s: %s', name, e)
        return False

    def _get_plan_collection_strategy(self, db, options, min_collection_interval):
        """
        Decides on the plan collection strategy:
        - which events_statement_history-* table are we using
        - how long should the rate and time limits be
        :return: (table, rate_limit, time_limit)
        """
        cached_strategy = self._expiring_cache.get("plan_collection_strategy")
        if cached_strategy:
            self.log.debug("using cached plan_collection_strategy: %s", cached_strategy)
            return cached_strategy

        auto_enable = is_affirmative(options.get('auto_enable_events_statements_consumers', False))
        enabled_consumers = self._get_enabled_performance_schema_consumers(db)

        # unless a specific table is configured, we try all of the events_statements tables in descending order of
        # preference
        preferred_tables = ['events_statements_history_long', 'events_statements_history', 'events_statements_current']
        events_statements_table = options.get('events_statements_table', None)
        if events_statements_table and events_statements_table not in DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS:
            self.log.warning("invalid events_statements_table: %s. must be one of %s", events_statements_table,
                             ', '.join(DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS.keys()))
            events_statements_table = None
        if events_statements_table:
            preferred_tables = [events_statements_table]

        # default time limit is small enough (1ms) so that the check will run only once
        chosen_table = None
        collect_exec_plans_time_limit = options.get('collect_exec_plans_time_limit', 1 / 1000)
        collect_exec_plans_rate_limit = options.get('collect_exec_plans_rate_limit', -1)

        for table in preferred_tables:
            if table not in enabled_consumers:
                if not auto_enable:
                    self.log.debug("performance_schema consumer for table %s not enabled")
                    continue
                success = self._performance_schema_enable_consumer(db, table)
                if not success:
                    continue
                self.log.debug("successfully enabled performance_schema consumer")

            rows = self._get_events_statements_by_digest(db, table, 1)
            if not rows:
                self.log.debug("no statements found in %s", table)
                continue

            if collect_exec_plans_rate_limit < 0:
                collect_exec_plans_rate_limit = DEFAULT_EVENTS_STATEMENTS_RATE_LIMITS[table]
            if collect_exec_plans_time_limit < 1 and table != 'events_statements_history_long':
                # all other tables require sampling multiple times during a single check run, so set the time limit
                # to run for most of the check run, leaving one second free to ensure it doesn't go over
                collect_exec_plans_time_limit = max(1, min_collection_interval - 1)

            chosen_table = table
            break

        strategy = (
            chosen_table,
            collect_exec_plans_time_limit,
            collect_exec_plans_rate_limit
        )

        if chosen_table:
            # cache only successful strategies, 10 minute expiry
            # 10 minutes is short enough that we'll reflect updates "relatively quickly"
            # i.e., an aurora replica becomes a master (or vice versa)
            self.log.debug("found plan collection strategy. chosen_table=%s, time_limit=%s, rate_limit=%s",
                           chosen_table, collect_exec_plans_time_limit, collect_exec_plans_rate_limit)
            self._expiring_cache.set("plan_collection_strategy", strategy, 10 * 60)
        else:
            self.log.warning(
                "no valid performance_schema.events_statements table found. cannot collect execution plans.")

        return strategy

    def _collect_execution_plans(self, db, tags, options, min_collection_interval):
        if not (is_dbm_enabled() and is_affirmative(options.get('collect_execution_plans', True))):
            self.log.debug("skipping execution plan collection. not enabled.")
            return
        (
            events_statements_table,
            collect_exec_plans_time_limit,
            collect_exec_plans_rate_limit
        ) = self._get_plan_collection_strategy(db, options, min_collection_interval)

        if not events_statements_table:
            return

        instance_tags = list(set(self.service_check_tags + tags))
        rate_limiter = ConstantRateLimiter(collect_exec_plans_rate_limit)
        start_time = time.time()
        # avoid reprocessing the exact same statements
        seen_digests = set()
        # ingest only one sample per unique (query, plan) per run
        seen_statement_plan_sigs = set()
        while time.time() - start_time < collect_exec_plans_time_limit:
            rate_limiter.sleep()
            rows = self._get_events_statements_by_digest(db, events_statements_table,
                                                         options.get('events_statements_row_limit', 5000))
            events = self._collect_plans_for_statements(db, rows, seen_statement_plan_sigs, instance_tags)
            if events:
                submit_exec_plan_events(events, instance_tags, "mysql")

        statsd.gauge("dd.mysql.collect_execution_plans.total.time", (time.time() - start_time) * 1000,
                     tags=instance_tags)
        statsd.gauge("dd.mysql.collect_execution_plans.seen_statements", len(seen_digests), tags=instance_tags)
        statsd.gauge("dd.mysql.collect_execution_plans.seen_statement_plan_sigs", len(seen_statement_plan_sigs),
                     tags=instance_tags)

    def _run_explain(self, cursor, statement, schema, instance_tags):
        # TODO: cleaner query cleaning to strip comments, etc.
        if statement.strip().split(' ', 1)[0].lower() not in VALID_EXPLAIN_STATEMENTS:
            return

        try:
            start_time = time.time()
            if schema is not None:
                cursor.execute('USE `{}`'.format(schema))
            cursor.execute('EXPLAIN FORMAT=json {statement}'.format(statement=statement))
            statsd.timing("dd.mysql.run_explain.time", (time.time() - start_time) * 1000, tags=instance_tags)
        except (pymysql.err.InternalError, pymysql.err.ProgrammingError) as e:
            if len(e.args) != 2:
                raise
            if e.args[0] in (1046,):
                self.log.warning('Failed to collect EXPLAIN due to a permissions error: %s, Statement: %s', e.args,
                                 statement)
                return None
            elif e.args[0] == 1064:
                self.log.warning('Programming error when collecting EXPLAIN: %s, Statement: %s', e.args, statement)
                return None
            else:
                raise

        return cursor.fetchone()[0]

    @staticmethod
    def _parse_execution_plan_cost(execution_plan):
        """
        Parses the total cost from the execution plan, if set. If not set, returns cost of 0.
        """
        cost = json.loads(execution_plan).get('query_block', {}).get('cost_info', {}).get('query_cost', 0.)
        return float(cost or 0.)
