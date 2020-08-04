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
from datadog_checks.base.utils.db.utils import ConstantRateLimiter

VALID_EXPLAIN_STATEMENTS = frozenset({
    'select',
    'table',
    'delete',
    'insert',
    'replace',
    'update',
})


class ExecutionPlansMixin(object):
    """
    Mixin for collecting execution plans from query samples.
    """

    def __init__(self, *args, **kwargs):
        # checkpoint at zero so we pull the whole history table on the first run
        self._checkpoint = 0
        self._auto_enable_eshl = None

    def _enable_performance_schema_consumers(self, db):
        query = """UPDATE performance_schema.setup_consumers SET enabled = 'YES' WHERE name = 
        'events_statements_history_long'"""
        with closing(db.cursor()) as cursor:
            try:
                cursor.execute(query)
            except pymysql.err.OperationalError as e:
                if e.args[0] == 1142:
                    self.log.error('Unable to create performance_schema consumers: %s', e.args[1])
                else:
                    raise
            except pymysql.err.InternalError as e:
                if e.args[0] == 1290:
                    self.log.warning('Unable to create performance_schema consumers because the instance is read-only')
                    self._auto_enable_eshl = False
                else:
                    raise
            else:
                self.log.info('Successfully enabled events_statements_history_long consumers')

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

    def _collect_execution_plans(self, db, tags, options, min_collection_interval):
        if self._auto_enable_eshl is None:
            self._auto_enable_eshl = is_affirmative(options.get('auto_enable_events_statements_history_long', False))
        if not (is_dbm_enabled() and is_affirmative(options.get('collect_execution_plans', True))):
            return False

        stmt_row_limit = options.get('events_statements_row_limit', 5000)

        events_statements_table = options.get('events_statements_table', 'events_statements_history_long')
        supported_tables = {'events_statements_history_long', 'events_statements_history', 'events_statements_current'}
        if events_statements_table not in supported_tables:
            self.log.warning("invalid 'events_statements_table' config for instance: %s. must be one of %s.",
                             events_statements_table, ', '.join(sorted(supported_tables)))
            events_statements_table = 'events_statements_history_long'
        is_history_long = events_statements_table == 'events_statements_history_long'

        collect_exec_plans_rate_limit = options.get('collect_exec_plans_rate_limit', -1)
        collect_exec_plans_time_limit = options.get('collect_exec_plans_time_limit', -1)
        if collect_exec_plans_rate_limit < 0:
            collect_exec_plans_rate_limit = 0 if is_history_long else 1
        if collect_exec_plans_time_limit < 0:
            # default time limit for history long is 1ms, meaning it'll run only once
            collect_exec_plans_time_limit = 1 / 1000 if is_history_long else max(1, min_collection_interval - 1)
        stmt_sample_rate_limiter = ConstantRateLimiter(collect_exec_plans_rate_limit)

        instance_tags = list(set(self.service_check_tags + tags))

        start_time = time.time()
        # avoid reprocessing the exact same statements
        seen_digests = set()
        # ingest only one sample per unique (query, plan)
        seen_statement_plan_sigs = set()
        while time.time() - start_time < collect_exec_plans_time_limit:
            stmt_sample_rate_limiter.sleep()
            rows = self._get_events_statements_by_digest(db, events_statements_table, stmt_row_limit)
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
