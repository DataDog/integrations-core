from contextlib import closing

import pymysql

import datadog_agent
from datadog_checks.base import is_affirmative

from .sql import compute_sql_signature


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
            SELECT thread_id, 
                   event_id,
                   current_schema,
                   sql_text,
                   IFNULL(digest_text, sql_text),
                   timer_start,
                   MAX(timer_wait)
              FROM performance_schema.events_statements_history_long
             WHERE sql_text IS NOT NULL
               AND event_name like %s
               AND timer_start > %s
          GROUP BY digest
          ORDER BY timer_wait DESC
              LIMIT %s
            """

        with closing(db.cursor()) as cursor:
            cursor.execute(query, ('statement/%', self._checkpoint, self.query_limit))
            rows = cursor.fetchall()

        events = []
        for row in rows:
            if not row or not all(row):
                self.log.debug('Row was unexpectedly truncated or events_statements_history_long table is not enabled')
                continue
            key = (row[0], row[1])
            schema = row[2]
            sql_text = row[3]
            digest_text = row[4]
            self._checkpoint = max(row[5], self._checkpoint)

            with closing(db.cursor()) as cursor:
                cursor.execute('SET sql_notes = 0')
                # TODO: run these asynchronously / do some benchmarking to optimize
                plan = self._run_explain(cursor, sql_text, schema)
                if plan:
                    events.append({
                        'query': datadog_agent.obfuscate_sql(sql_text),
                        'plan': plan,
                        'query_signature': compute_sql_signature(digest_text)
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
        except pymysql.err.InternalError as e:
            if len(e.args) != 2:
                raise
            if e.args[0] in (1046,):
                self.log.warning('Failed to collect EXPLAIN due to a permissions error: %s', (self.args,))
            elif e.args[0] == 1064:
                self.log.error('Programming error when collecting EXPLAIN: %s', (self.args,))
            else:
                raise

        return cursor.fetchone()[0]
