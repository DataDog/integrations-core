# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import psycopg2
import psycopg2.extras

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics, apply_row_limits

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


logger = logging.getLogger(__name__)


STATEMENTS_QUERY = """
SELECT {cols}
  FROM {pg_stat_statements_view} as pg_stat_statements
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
  WHERE pg_database.datname = %s
  AND query != '<insufficient privilege>'
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

# Columns to apply as tags
PG_STAT_STATEMENTS_TAG_COLUMNS = {
    'datname': 'db',
    'rolname': 'user',
    'query': 'query',
}

DEFAULT_METRIC_LIMITS = {k: (10000, 10000) for k in PG_STAT_STATEMENTS_METRIC_COLUMNS.keys()}


class PostgresStatementMetrics(object):
    """Collects telemetry for SQL statements"""

    def __init__(self, config):
        self.config = config
        # Cache results of monotonic pg_stat_statements to compare to previous collection
        self._state = StatementMetrics()

        # Available columns will be queried once and cached as the source of truth.
        self._pg_stat_statements_columns = None
        self._pg_stat_statements_query_columns = None

    def _execute_query(self, cursor, query, params=()):
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
            logger.warning('Statement-level metrics are unavailable: %s', e)
            return []

    def _get_pg_stat_statements_columns(self, db):
        """
        Load the list of the columns available under the `pg_stat_statements` table. This must be queried because
        version is not a reliable way to determine the available columns on `pg_stat_statements`. The database can
        be upgraded without upgrading extensions, even when the extension is included by default.
        """
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'pg_stat_statements';
            """
        columns = self._execute_query(db.cursor(), query)
        return [column[0] for column in columns]

    def collect_per_statement_metrics(self, instance, db, instance_tags):
        try:
            self.__collect_per_statement_metrics(instance, db, instance_tags)
        except Exception:
            db.rollback()
            logger.exception('Unable to collect statement metrics due to an error')

    def __collect_per_statement_metrics(self, instance, db, instance_tags):
        available_columns = self._get_pg_stat_statements_columns(db)
        missing_columns = PG_STAT_STATEMENTS_REQUIRED_COLUMNS - set(available_columns)
        if len(missing_columns) > 0:
            logger.warning(
                'Unable to collect statement metrics because required fields are unavailable: %s',
                ', '.join(list(missing_columns)),
            )
            return

        desired_columns = (
            list(PG_STAT_STATEMENTS_METRIC_COLUMNS.keys())
            + list(PG_STAT_STATEMENTS_OPTIONAL_COLUMNS)
            + list(PG_STAT_STATEMENTS_TAG_COLUMNS.keys())
        )
        query_columns = list(set(desired_columns) & set(available_columns)) + list(PG_STAT_STATEMENTS_TAG_COLUMNS.keys())
        rows = self._execute_query(
            db.cursor(cursor_factory=psycopg2.extras.DictCursor),
            STATEMENTS_QUERY.format(
                cols=', '.join(query_columns),
                pg_stat_statements_view=self.config.pg_stat_statements_view,
            ),
            params=(self.config.dbname,),
        )
        if not rows:
            return

        def row_keyfunc(row):
            # old versions of pg_stat_statements don't have a query ID so fall back to the query string itself
            queryid = row['queryid'] if 'queryid' in row else row['query']
            return (queryid, row['datname'], row['rolname'])

        rows = self._state.compute_derivative_rows(rows, PG_STAT_STATEMENTS_METRIC_COLUMNS.keys(), key=row_keyfunc)
        metric_limits = (
            self.config.statement_metric_limits if self.config.statement_metric_limits else DEFAULT_METRIC_LIMITS
        )
        rows = apply_row_limits(rows, metric_limits, 'calls', True, key=row_keyfunc)

        for row in rows:
            try:
                normalized_query = datadog_agent.obfuscate_sql(row['query'])
                if not normalized_query:
                    logger.warning("Query obfuscation resulted in empty query '%s': %s", row['query'], e)
                    continue
            except Exception as e:
                logger.warning("Failed to obfuscate query '%s': %s", row['query'], e)
                continue

            # The APM resource hash will use the same query signature because the grouped query is close
            # enough to the raw query that they will intersect frequently.
            query_signature = compute_sql_signature(normalized_query)
            tags = ['query_signature:' + query_signature, 'resource_hash:' + query_signature] + instance_tags
            for column, tag_name in PG_STAT_STATEMENTS_TAG_COLUMNS.items():
                if column not in row:
                    continue
                value = row[column]
                if column == 'query':
                    value = self._normalize_query_tag(value)
                tags.append('{tag_name}:{value}'.format(tag_name=tag_name, value=value))

            for column, metric_name in PG_STAT_STATEMENTS_METRIC_COLUMNS.items():
                if column not in row:
                    continue
                value = row[column]
                if column == 'total_time':
                    # convert milliseconds to nanoseconds
                    value = value * 1000000
                instance.count(metric_name, value, tags=tags)

    def _normalize_query_tag(self, query):
        """Normalize the query value to be used as a tag"""
        # Truncate to metrics tag limit
        query = query.strip()[:200]
        if self.config.escape_query_commas_hack:
            # Substitute commas in the query with unicode commas. Temp hack to
            # work around the bugs in arbitrary tag values on the backend.
            query = query.replace(', ', '，').replace(',', '，')
        return query
