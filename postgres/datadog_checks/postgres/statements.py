# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import time

import psycopg2
import psycopg2.extras
from datadog import statsd

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature, compute_sql_signature, submit_exec_plan_events
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics, apply_row_limits
from datadog_checks.base.utils.db.utils import ConstantRateLimiter

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

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
PG_STAT_STATEMENTS_REQUIRED_COLUMNS = frozenset({'calls', 'query', 'total_time', 'rows'})

PG_STAT_STATEMENTS_OPTIONAL_COLUMNS = frozenset({'queryid'})

# Monotonically increasing count columns to be converted to metrics
PG_STAT_STATEMENTS_METRIC_COLUMNS = {
    'calls': 'postgresql.queries.count',
    'total_time': 'postgresql.queries.time',
    'rows': 'postgresql.queries.rows',
    'shared_blks_hit': 'postgresql.queries.shared_blks_hit',
    'shared_blks_read': 'postgresql.queries.shared_blks_read',
    'shared_blks_dirtied': 'postgresql.queries.shared_blks_dirtied',
    'shared_blks_written': 'postgresql.queries.shared_blks_written',
    'local_blks_hit': 'postgresql.queries.local_blks_hit',
    'local_blks_read': 'postgresql.queries.local_blks_read',
    'local_blks_dirtied': 'postgresql.queries.local_blks_dirtied',
    'local_blks_written': 'postgresql.queries.local_blks_written',
    'temp_blks_read': 'postgresql.queries.temp_blks_read',
    'temp_blks_written': 'postgresql.queries.temp_blks_written',
}

DEFAULT_METRIC_LIMITS = {k: (100000, 100000) for k in PG_STAT_STATEMENTS_METRIC_COLUMNS.keys()}

# Columns to apply as tags
PG_STAT_STATEMENTS_TAG_COLUMNS = {
    'datname': 'db',
    'rolname': 'user',
    'query': 'query',
}

VALID_EXPLAIN_STATEMENTS = frozenset({'select', 'table', 'delete', 'insert', 'replace', 'update'})

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
        self._state = StatementMetrics(self.log)

        # Available columns will be queried once and cached as the source of truth.
        self.__pg_stat_statements_columns = None
        self.__pg_stat_statements_query_columns = None
        self._activity_last_query_start = None
        self._activity_sample_rate_limiter = None

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

    @property
    def _pg_stat_statements_query_columns(self):
        """
        Columns to query for with aliases
        Only includes columns that actually exist in the table
        """
        if self.__pg_stat_statements_query_columns is not None:
            return self.__pg_stat_statements_query_columns
        all_columns = list(PG_STAT_STATEMENTS_METRIC_COLUMNS.keys()) + list(PG_STAT_STATEMENTS_OPTIONAL_COLUMNS)
        self.__pg_stat_statements_query_columns = sorted(
            list(set(all_columns) & self._pg_stat_statements_columns) + list(PG_STAT_STATEMENTS_TAG_COLUMNS.keys())
        )
        return self.__pg_stat_statements_query_columns

    def _collect_statement_metrics(self, instance_tags):
        try:
            self.__collect_statement_metrics(instance_tags)
        except:
            self.log.exception('Unable to collect statement metrics due to an error')

    def __collect_statement_metrics(self, instance_tags):
        # Sanity checks
        missing_columns = PG_STAT_STATEMENTS_REQUIRED_COLUMNS - self._pg_stat_statements_columns
        if len(missing_columns) > 0:
            self.log.warning(
                'Unable to collect statement metrics because required fields are unavailable: {}'.format(
                    ', '.join(list(missing_columns))
                )
            )
            return

        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        rows = self._execute_query(
            cursor,
            STATEMENTS_QUERY.format(
                cols=', '.join(self._pg_stat_statements_query_columns),
                pg_stat_statements_function=self.config.pg_stat_statements_function,
            ),
            params=(self.config.dbname,),
        )
        statsd.gauge("dd.postgres.collect_statement_metrics.rows", len(rows), tags=instance_tags)
        if not rows:
            return

        def row_keyfunc(row):
            # old versions of pg_stat_statements don't have a query ID so fall back to the query string itself
            queryid = row['queryid'] if 'queryid' in row else row['query']
            return (queryid, row['datname'], row['rolname'])

        rows = self._state.compute_derivative_rows(rows, PG_STAT_STATEMENTS_METRIC_COLUMNS.keys(), key=row_keyfunc)
        metric_limits = self.config.query_metric_limits if self.config.query_metric_limits else DEFAULT_METRIC_LIMITS
        rows = apply_row_limits(rows, metric_limits, 'calls', True, key=row_keyfunc)

        for row in rows:
            try:
                obfuscated_query = datadog_agent.obfuscate_sql(row['query'])
            except Exception as e:
                self.log.warn("failed to obfuscate query '%s': %s", row['query'], e)
                continue

            # The APM resource hash will use the same query signature because the grouped query is close
            # enough to the raw query that they will intersect frequently.
            query_signature = compute_sql_signature(obfuscated_query)
            apm_resource_hash = query_signature
            tags = ['query_signature:' + query_signature, 'resource_hash:' + apm_resource_hash] + instance_tags
            for column, tag_name in PG_STAT_STATEMENTS_TAG_COLUMNS.items():
                if column not in row:
                    continue
                value = row[column]
                if column == 'query':
                    # truncate to metrics tag limit
                    value = obfuscated_query[:200]
                    if self.config.escape_query_commas_hack:
                        value = value.replace(', ', '，').replace(',', '，')
                tags.append('{tag_name}:{value}'.format(tag_name=tag_name, value=value))

            for column, metric_name in PG_STAT_STATEMENTS_METRIC_COLUMNS.items():
                if column not in row:
                    continue
                value = row[column]
                if column == 'total_time':
                    # convert milliseconds to nanoseconds
                    value = value * 1000000
                self.log.debug("AgentCheck.count(%s, %s, tags=%s)", metric_name, value, tags)
                self.count(metric_name, value, tags=tags)

    def _get_new_pg_stat_activity(self, instance_tags=None):
        start_time = time.time()
        query = """
        SELECT * FROM {pg_stat_activity_function}
        WHERE datname = %s
        AND coalesce(TRIM(query), '') != ''
        """.format(
            pg_stat_activity_function=self.config.pg_stat_activity_function
        )
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
        statsd.histogram(
            "dd.postgres.get_new_pg_stat_activity.time", (time.time() - start_time) * 1000, tags=instance_tags
        )
        statsd.histogram("dd.postgres.get_new_pg_stat_activity.rows", len(rows), tags=instance_tags)
        statsd.increment("dd.postgres.get_new_pg_stat_activity.total_rows", len(rows), tags=instance_tags)
        return rows

    def can_explain_statement(self, statement):
        # TODO: cleaner query cleaning to strip comments, etc.
        if statement == '<insufficient privilege>':
            self.log.warn("Insufficient privilege to collect statement.")
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
                cursor.execute(
                    """SELECT {explain_function}($stmt${statement}$stmt$)""".format(
                        explain_function=self.config.collect_exec_plan_function, statement=statement
                    )
                )
                result = cursor.fetchone()
                statsd.histogram("dd.postgres.run_explain.time", (time.time() - start_time) * 1000, tags=instance_tags)
            except psycopg2.errors.UndefinedFunction:
                self.log.warn(
                    "Failed to collect execution plan due to undefined explain_function: %s.",
                    self.config.collect_exec_plan_function,
                )
                return None
            except Exception as e:
                statsd.increment("dd.postgres.run_explain.error", tags=instance_tags)
                self.log.error("failed to collect execution plan for query='%s'. (%s): %s", statement, type(e), e)
                return None
        if not result or len(result) < 1 or len(result[0]) < 1:
            return None
        return result[0][0]

    def _explain_new_pg_stat_activity(self, samples, seen_statements, seen_statement_plan_sigs, instance_tags):
        start_time = time.time()
        events = []
        for row in samples:
            original_statement = row['query']
            if original_statement in seen_statements:
                continue
            seen_statements.add(original_statement)

            plan_dict = None
            try:
                plan_dict = self._run_explain(original_statement, instance_tags)
            except Exception:
                statsd.increment("dd.postgres.explain_new_pg_stat_activity.error")
                self.log.exception("failed to explain & process query '%s'", original_statement)

            # Plans have several important signatures to tag events with. Note that for postgres, the
            # query_signature and resource_hash will be the same value.
            # - `plan_signature` - hash computed from the normalized JSON plan to group identical plan trees
            # - `resource_hash` - hash computed off the raw sql text to match apm resources
            # - `query_signature` - hash computed from the raw sql text to match query metrics
            if plan_dict:
                plan = json.dumps(plan_dict)
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(plan, normalize=True)
                obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(plan)
                plan_signature = compute_exec_plan_signature(normalized_plan)
                plan_cost = (plan_dict.get('Plan', {}).get('Total Cost', 0.0) or 0.0)
            else:
                plan = None
                normalized_plan = None
                obfuscated_plan = None
                plan_signature = None
                plan_cost = None

            obfuscated_statement = datadog_agent.obfuscate_sql(original_statement)
            query_signature = compute_sql_signature(obfuscated_statement)
            apm_resource_hash = query_signature
            statement_plan_sig = (query_signature, plan_signature)

            if statement_plan_sig not in seen_statement_plan_sigs:
                seen_statement_plan_sigs.add(statement_plan_sig)
                event = {
                    'db': {
                        'instance': row['datname'],
                        'statement': obfuscated_statement,
                        'query_signature': query_signature,
                        'resource_hash': apm_resource_hash,
                        'plan': obfuscated_plan,
                        'plan_cost': plan_cost,
                        'plan_signature': plan_signature,
                        'postgres': {k: row[k] for k in pg_stat_activity_sample_keys if k in row},
                    }
                }
                if self.config.collect_exec_plan_debug:
                    event['db']['debug'] = {
                        'original_plan': plan,
                        'normalized_plan': normalized_plan,
                        'original_statement': original_statement,
                    }
                events.append(event)
        statsd.histogram(
            "dd.postgres.explain_new_pg_stat_activity.time", (time.time() - start_time) * 1000, tags=instance_tags
        )
        return events

    def _collect_execution_plans(self, instance_tags):
        try:
            self.__collect_execution_plans(instance_tags)
        except:
            self.log.exception('Unable to collect execution plans due to an error')

    def __collect_execution_plans(self, instance_tags):
        if not self._activity_sample_rate_limiter:
            self._activity_sample_rate_limiter = ConstantRateLimiter(self.config.collect_exec_plans_rate_limit)

        start_time = time.time()
        # avoid reprocessing the exact same statement
        seen_statements = set()
        # keep only one sample per unique (query, plan)
        seen_statement_plan_sigs = set()
        while time.time() - start_time < self.config.collect_exec_plans_time_limit:
            if len(seen_statement_plan_sigs) > self.config.collect_exec_plans_event_limit:
                break
            self._activity_sample_rate_limiter.sleep()
            samples = self._get_new_pg_stat_activity(instance_tags=instance_tags)
            events = self._explain_new_pg_stat_activity(
                samples, seen_statements, seen_statement_plan_sigs, instance_tags
            )
            if events:
                submit_exec_plan_events(events, instance_tags, "postgres")

        statsd.gauge(
            "dd.postgres.collect_execution_plans.total.time", (time.time() - start_time) * 1000, tags=instance_tags
        )
        statsd.gauge("dd.postgres.collect_execution_plans.seen_statements", len(seen_statements), tags=instance_tags)
        statsd.gauge(
            "dd.postgres.collect_execution_plans.seen_statement_plan_sigs",
            len(seen_statement_plan_sigs),
            tags=instance_tags,
        )
