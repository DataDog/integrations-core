import json
from contextlib import closing

import pymysql

import datadog_agent
from datadog_checks.base import is_affirmative

from datadog_checks.base.utils.db.sql import compute_sql_signature, compute_exec_plan_signature


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
        # TODO: Make this a configurable limit
        self.query_limit = 500
        self._checkpoint = None
    
    def _submit_log_events(self, *args, **kwargs):
        raise NotImplementedError('Must implement method _submit_log_events')

    def _enable_performance_schema_consumers(self, db):
        query = """UPDATE performance_schema.setup_consumers SET enabled = 'YES' WHERE name = 'events_statements_history_long'"""
        with closing(db.cursor()) as cursor:
            try:
                cursor.execute(query)
            except pymysql.err.OperationalError as e:
                if e.args[0] == 1142:
                    self.log.error('Unable to create performance_schema consumers: %s', e.args[1])
                else:
                    raise
            else:
                self.log.info('Successfully enabled events_statements_history_long consumers')

    def _collect_execution_plans(self, db, tags, options):
        auto_enable_eshl = is_affirmative(options.get('auto_enable_events_statements_history_long', False))
        if not is_affirmative(options.get('collect_execution_plans', False)):
            return False

        tags = list(set(self.service_check_tags + tags))
        if self._checkpoint is None:
            with closing(db.cursor()) as cursor:
                cursor.execute('SELECT MAX(timer_start) FROM performance_schema.events_statements_history_long')
                result = cursor.fetchone()
            if not result or not all(result):
                self.log.warn('Unable to fetch from performance_schema.events_statements_history_long')
                if auto_enable_eshl:
                    self._enable_performance_schema_consumers(db)
                return False
            self._checkpoint = result[0]
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
              FROM performance_schema.events_statements_history_long
             WHERE sql_text IS NOT NULL
               AND event_name like %s
               AND digest_text NOT LIKE %s
               AND timer_start > %s
          GROUP BY digest
          ORDER BY timer_wait DESC
              LIMIT %s
            """

        with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
            cursor.execute(query, ('statement/%', 'EXPLAIN %', self._checkpoint, self.query_limit))
            rows = cursor.fetchall()

        events = []
        for row in rows:
            if not row or not all(row):
                self.log.debug('Row was unexpectedly truncated or events_statements_history_long table is not enabled')
                continue
            schema = row['current_schema']
            sql_text = row['sql_text']
            digest_text = row['digest_text']
            self._checkpoint = max(row['timer_start'], self._checkpoint)
            duration_ns = row['max_timer_wait_ns']

            if not sql_text:
                continue

            # The SQL_TEXT column will store 1024 chars by default. Plans cannot be captured on truncated
            # queries, so the `performance_schema_max_sql_text_length` variable must be raised.
            if sql_text[-3:] == '...':
                self.log.warning(
                    'Unable to collect plan for query due to truncated SQL text. Consider raising the '
                    '`performance_schema_max_sql_text_length` to capture this query.')
                continue

            with closing(db.cursor()) as cursor:
                cursor.execute('SET sql_notes = 0')
                # TODO: run these asynchronously / do some benchmarking to optimize
                plan = self._run_explain(cursor, sql_text, schema)
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True) if plan else None
                obfuscated_statement = datadog_agent.obfuscate_sql(sql_text)
                if plan:
                    events.append({
                        'duration': duration_ns,
                        'db': {
                            'instance': schema,
                            'statement': obfuscated_statement,
                            'query_signature': compute_sql_signature(obfuscated_statement),
                            'plan': plan,
                            'plan_cost': self._parse_execution_plan_cost(plan),
                            'plan_signature': compute_exec_plan_signature(normalized_plan),
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

        self._submit_log_events(events)

    def _run_explain(self, cursor, statement, schema):
        # TODO: cleaner query cleaning to strip comments, etc.
        if statement.strip().split(' ', 1)[0].lower() not in VALID_EXPLAIN_STATEMENTS:
            return

        try:
            if schema is not None:
                cursor.execute('USE `{}`'.format(schema))
            cursor.execute('EXPLAIN FORMAT=json {statement}'.format(statement=statement))
        except (pymysql.err.InternalError, pymysql.err.ProgrammingError) as e:
            if len(e.args) != 2:
                raise
            if e.args[0] in (1046,):
                self.log.warning('Failed to collect EXPLAIN due to a permissions error: %s', (e.args,))
                return None
            elif e.args[0] == 1064:
                self.log.error('Programming error when collecting EXPLAIN: %s', (e.args,))
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
