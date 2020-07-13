# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import decimal
import json
from collections import defaultdict

import mmh3
import psycopg2
import psycopg2.extras
import time
from datadog import statsd
from datadog_checks.base import AgentCheck
import socket
from datadog_checks.base.utils.db.sql import compute_sql_signature, compute_exec_plan_signature

from contextlib import closing

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


class EventEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(EventEncoder, self).default(o)


# TODO: As a future optimization, the `query` column should be cached on first request
# and not requested again until agent restart or pg_stats reset. This is to avoid
# hitting disk every poll period. This is fine when the query is run every 15s,
# but not when it is run every 100ms for instance. Full queries can be quite large.
STATEMENTS_QUERY = """
SELECT {cols}
  FROM {pg_stat_statements_function} as pg_stat_statements 
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
  WHERE pg_database.datname = %s
  AND query != '<insufficient privilege>'
ORDER BY (pg_stat_statements.total_time / NULLIF(pg_stat_statements.calls, 0)) DESC;
"""


# Required columns for the check to run
PG_STAT_STATEMENTS_REQUIRED_COLUMNS = frozenset({
    'calls',
    'query',
    'total_time',
    'rows',
})


# Count columns to be converted to metrics
PG_STAT_STATEMENTS_METRIC_COLUMNS = {
    'calls': ('pg_stat_statements.calls', 'postgresql.queries.count', AgentCheck.count),
    'total_time': ('pg_stat_statements.total_time', 'postgresql.queries.time', AgentCheck.count),
    'rows': ('pg_stat_statements.rows', 'postgresql.queries.rows', AgentCheck.count),
    'shared_blks_hit': ('pg_stat_statements.shared_blks_hit', 'postgresql.queries.shared_blks_hit', AgentCheck.count),
    'shared_blks_read': ('pg_stat_statements.shared_blks_read', 'postgresql.queries.shared_blks_read', AgentCheck.count),
    'shared_blks_dirtied': ('pg_stat_statements.shared_blks_dirtied', 'postgresql.queries.shared_blks_dirtied', AgentCheck.count),
    'shared_blks_written': ('pg_stat_statements.shared_blks_written', 'postgresql.queries.shared_blks_written', AgentCheck.count),
    'local_blks_hit': ('pg_stat_statements.local_blks_hit', 'postgresql.queries.local_blks_hit', AgentCheck.count),
    'local_blks_read': ('pg_stat_statements.local_blks_read', 'postgresql.queries.local_blks_read', AgentCheck.count),
    'local_blks_dirtied': ('pg_stat_statements.local_blks_dirtied', 'postgresql.queries.local_blks_dirtied', AgentCheck.count),
    'local_blks_written': ('pg_stat_statements.local_blks_written', 'postgresql.queries.local_blks_written', AgentCheck.count),
    'temp_blks_read': ('pg_stat_statements.temp_blks_read', 'postgresql.queries.temp_blks_read', AgentCheck.count),
    'temp_blks_written': ('pg_stat_statements.temp_blks_written', 'postgresql.queries.temp_blks_written', AgentCheck.count),
}


# Columns to apply as tags
PG_STAT_STATEMENTS_TAG_COLUMNS = {
    'datname': ('pg_database.datname', 'db'),
    'rolname': ('pg_roles.rolname', 'user'),
    'query': ('pg_stat_statements.query', 'query'),
}


# Transformation functions to apply to each column before submission
PG_STAT_STATEMENTS_TRANSFORM = {
    # obfuscate then truncate the query to 200 chars
    'query': lambda q: datadog_agent.obfuscate_sql(q)[:200],
}

VALID_EXPLAIN_STATEMENTS = frozenset({
    'select',
    'table',
    'delete',
    'insert',
    'replace',
    'update',
})

# keys from pg_stat_activity to include along with each (sample & execution plan)
pg_stat_activity_sample_keys = [
    'query_start',
    'datname',
    'usesysid',
    'application_name',
    'client_addr',
    'client_port',
    'wait_event_type',
    'wait_event',
    'state',
]


class PgStatementsMixin(object):
    """
    Mixin for collecting telemetry on executed statements.
    """

    def __init__(self, *args, **kwargs):
        # Cache results of monotonic pg_stat_statements to compare to previous collection
        self._statements_cache = {}

        # Available columns will be queried once and cached as the source of truth.
        self.__pg_stat_statements_columns = None
        self._activity_last_query_start = None

    def _execute_query(self, cursor, query, params=None, log_func=None):
        raise NotImplementedError('Check must implement _execute_query()')

    def _lazy_connect_database(self, dbname):
        raise NotImplementedError('Check must implement _lazy_connect_database()')

    @property
    def _pg_stat_statements_columns(self):
        """
        Lazy-loaded list of the columns available under the `pg_stat_statements` table. This must be done because
        version is not a reliable way to determine the available columns on `pg_stat_statements`. The database
        can be upgraded without upgrading extensions, even when the extension is included by default.
        """
        if self.__pg_stat_statements_columns is not None:
            return self.__pg_stat_statements_columns
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'pg_stat_statements';
            """
        cursor = self.db.cursor()
        columns = self._execute_query(cursor, query)
        self.__pg_stat_statements_columns = frozenset(column[0] for column in columns)
        return self.__pg_stat_statements_columns

    def _collect_statement_metrics(self, instance_tags):
        # Sanity checks
        missing_columns = PG_STAT_STATEMENTS_REQUIRED_COLUMNS - self._pg_stat_statements_columns
        if len(missing_columns) > 0:
            self.log.warning('Unable to collect statement metrics because required fields are unavailable: {}'.format(missing_columns))
            return

        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        columns = []
        for entry in (PG_STAT_STATEMENTS_METRIC_COLUMNS, PG_STAT_STATEMENTS_TAG_COLUMNS):
            for alias, (column, *_) in entry.items():
                # Only include columns which are available on the table
                if alias in self._pg_stat_statements_columns or alias in PG_STAT_STATEMENTS_TAG_COLUMNS:
                    columns.append('{column} AS {alias}'.format(column=column, alias=alias))

        rows = self._execute_query(cursor, STATEMENTS_QUERY.format(
            cols=', '.join(columns),
            pg_stat_statements_function=self.config.pg_stat_statements_function
        ), params=(self.config.dbname,))
        if not rows:
            return
        rows = rows[:self.config.max_query_metrics]

        new_cache = {}
        for row in rows:
            key = (row['rolname'], row['datname'], row['query'])
            new_cache[key] = row
            if key not in self.statement_cache:
                continue
            prev = self.statement_cache[key]

            # pg_stats reset will cause this
            if row['calls'] - prev['calls'] <= 0:
                continue

            try:
                obfuscated_query = datadog_agent.obfuscate_sql(row['query'])
            except Exception as e:
                self.log.warn("failed to obfuscate query '%s': %s", row['query'], e)
                continue

            tags = ['query_signature:' + compute_sql_signature(obfuscated_query)] + instance_tags
            for tag_column, (_, alias) in PG_STAT_STATEMENTS_TAG_COLUMNS.items():
                if tag_column not in self._pg_stat_statements_columns:
                    continue
                value = PG_STAT_STATEMENTS_TRANSFORM.get(tag_column, lambda x: x)(row[tag_column])
                tags.append('{alias}:{value}'.format(alias=alias, value=value))

            for alias, (_, name, fn) in PG_STAT_STATEMENTS_METRIC_COLUMNS.items():
                if alias not in self._pg_stat_statements_columns:
                    continue

                val = row[alias] - prev[alias]

                fn(self, name, val, tags=tags)

        self.statement_cache = new_cache

    def _get_new_pg_stat_activity(self, instance_tags=None):
        start_time = time.time()
        query = """
        SELECT * FROM {pg_stat_activity_function} 
        WHERE datname = %s
        AND coalesce(TRIM(query), '') != ''
        """.format(pg_stat_activity_function=self.config.pg_stat_activity_function)
        self.db.rollback()
        with self.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            if self._activity_last_query_start:
                cursor.execute(query + " AND query_start > %s", (self.config.dbname, self._activity_last_query_start,))
            else:
                cursor.execute(query, (self.config.dbname,))
            rows = cursor.fetchall()

        rows = [r for r in rows if r['query'] and r['datname'] and self.can_explain_statement(r['query'])]
        max_query_start = max(r['query_start'] for r in rows)
        if self._activity_last_query_start is None or max_query_start > self._activity_last_query_start:
            self._activity_last_query_start = max_query_start

        # TODO: once stable, either remove these development metrics or make them configurable in a debug mode
        statsd.histogram("dd.postgres.get_new_pg_stat_activity.time", (time.time() - start_time) * 1000,
                         tags=instance_tags)
        statsd.histogram("dd.postgres.get_new_pg_stat_activity.rows", len(rows), tags=instance_tags)
        statsd.increment("dd.postgres.get_new_pg_stat_activity.total_rows", len(rows), tags=instance_tags)
        return rows

    def can_explain_statement(self, statement):
        # TODO: cleaner query cleaning to strip comments, etc.
        if statement == '<insufficient privilege>':
            self.log.warn("insufficient privilege. cannot collect query. review the setup instructions at (TODO: add documentation link).")
            return False
        if statement.strip().split(' ', 1)[0].lower() not in VALID_EXPLAIN_STATEMENTS:
            return False
        if statement.startswith('SELECT {}'.format(self.config.collect_exec_plan_function)):
            return False
        return True

    def _run_explain(self, statement, instance_tags=None):
        if not self.can_explain_statement(statement):
            return
        with self.db.cursor() as cursor:
            try:
                start_time = time.time()
                cursor.execute("""SELECT {explain_function}($stmt${statement}$stmt$)""".format(
                    explain_function=self.config.collect_exec_plan_function,
                    statement=statement
                ))
                result = cursor.fetchone()
                statsd.histogram("dd.postgres.run_explain.time", (time.time() - start_time) * 1000, tags=instance_tags)
            except psycopg2.errors.UndefinedFunction:
                self.log.warn("failed to collect execution plan due to undefined explain_function: %s. refer to setup documentation (TODO link)", self.config.collect_exec_plan_function)
                return None
            except Exception as e:
                statsd.increment("dd.postgres.run_explain.error")
                self.log.error("failed to collect execution plan for query='%s'. (%s): %s", statement, type(e), e)
                return None
        if not result or len(result) < 1 or len(result[0]) < 1:
            return None
        return result[0][0]

    def _submit_log_events(self, events):
        # TODO: This is a temporary hack to send logs via the Python integrations and requires customers
        # to configure a TCP log on port 10518. THIS CODE SHOULD NOT BE MERGED TO MASTER
        try:
            with closing(socket.create_connection(('localhost', 10518))) as c:
                for e in events:
                    c.sendall((json.dumps(e, cls=EventEncoder, default=str) + '\n').encode())
        except ConnectionRefusedError:
            self.warning('Unable to connect to the logs agent; please see the '
                         'documentation on configuring the logs agent.')
            return

    def _explain_new_pg_stat_activity(self, samples, seen_statements, seen_statement_plan_sigs,
                                      instance_tags):
        start_time = time.time()
        events = []
        for row in samples:
            original_statement = row['query']
            if original_statement in seen_statements:
                continue
            seen_statements.add(original_statement)
            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(original_statement)
                query_signature = compute_sql_signature(obfuscated_statement)
                plan_dict = self._run_explain(original_statement, instance_tags)
                if not plan_dict:
                    continue
                plan = json.dumps(plan_dict)
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)
                plan_signature = compute_exec_plan_signature(normalized_plan)
                statement_plan_sig = (query_signature, plan_signature)
                if statement_plan_sig not in seen_statement_plan_sigs:
                    seen_statement_plan_sigs.add(statement_plan_sig)
                    events.append({
                        'db': {
                            'instance': row['datname'],
                            'statement': obfuscated_statement,
                            'query_signature': query_signature,
                            'plan': plan,
                            'plan_cost': (plan_dict.get('Plan', {}).get('Total Cost', 0.) or 0.),
                            'plan_signature': plan_signature,
                            'debug': {
                                'normalized_plan': normalized_plan,
                                'obfuscated_plan': datadog_agent.obfuscate_sql_exec_plan(plan),
                                'original_statement': original_statement,
                            },
                            'postgres': {k: row[k] for k in pg_stat_activity_sample_keys if k in row},
                        }
                    })
            except Exception:
                statsd.increment("dd.postgres.explain_new_pg_stat_activity.error")
                self.log.exception("failed to explain & process query '%s'", original_statement)
        statsd.histogram("dd.postgres.explain_new_pg_stat_activity.time", (time.time() - start_time) * 1000,
                         tags=instance_tags)
        return events

    def _collect_execution_plans(self, instance_tags):
        start_time = time.time()
        # avoid reprocessing the exact same statement
        seen_statements = set()
        # keep only one sample per unique (query, plan)
        seen_statement_plan_sigs = set()
        while time.time() - start_time < self.config.collect_exec_plan_time_limit:
            if len(seen_statement_plan_sigs) > self.config.collect_exec_plan_event_limit:
                break
            samples = self._get_new_pg_stat_activity(instance_tags=instance_tags)
            events = self._explain_new_pg_stat_activity(samples, seen_statements, seen_statement_plan_sigs,
                                                        instance_tags)
            if events:
                self._submit_log_events(events)
            time.sleep(self.config.collect_exec_plan_sample_sleep)

        self.gauge("dd.postgres.collect_execution_plans.total.time", (time.time() - start_time) * 1000,
                   tags=instance_tags)
        self.gauge("dd.postgres.collect_execution_plans.seen_statements", len(seen_statements), tags=instance_tags)
        self.gauge("dd.postgres.collect_execution_plans.seen_statement_plan_sigs", len(seen_statement_plan_sigs),
                   tags=instance_tags)
