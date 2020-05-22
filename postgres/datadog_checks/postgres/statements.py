# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mmh3
import psycopg2
import psycopg2.extras

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

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
  FROM pg_stat_statements
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
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
PG_STAT_STATEMENTS_COUNT_COLUMNS = {
    'calls': ('pg_stat_statements.calls', 'postgresql.queries.count', AgentCheck.count),
}


# Columns which are aggregates per-statement and must be divided by count
PG_STAT_STATEMENTS_PER_STATEMENT_COLUMNS = {
    'total_time': ('pg_stat_statements.total_time', 'postgresql.queries.time', AgentCheck.gauge),
    'rows': ('pg_stat_statements.rows', 'postgresql.queries.rows', AgentCheck.gauge),
    'shared_blks_hit': ('pg_stat_statements.shared_blks_hit', 'postgresql.queries.shared_blks_hit', AgentCheck.gauge),
    'shared_blks_read': ('pg_stat_statements.shared_blks_read', 'postgresql.queries.shared_blks_read', AgentCheck.gauge),
    'shared_blks_dirtied': ('pg_stat_statements.shared_blks_dirtied', 'postgresql.queries.shared_blks_dirtied', AgentCheck.gauge),
    'shared_blks_written': ('pg_stat_statements.shared_blks_written', 'postgresql.queries.shared_blks_written', AgentCheck.gauge),
    'local_blks_hit': ('pg_stat_statements.local_blks_hit', 'postgresql.queries.local_blks_hit', AgentCheck.gauge),
    'local_blks_read': ('pg_stat_statements.local_blks_read', 'postgresql.queries.local_blks_read', AgentCheck.gauge),
    'local_blks_dirtied': ('pg_stat_statements.local_blks_dirtied', 'postgresql.queries.local_blks_dirtied', AgentCheck.gauge),
    'local_blks_written': ('pg_stat_statements.local_blks_written', 'postgresql.queries.local_blks_written', AgentCheck.gauge),
    'temp_blks_read': ('pg_stat_statements.temp_blks_read', 'postgresql.queries.temp_blks_read', AgentCheck.gauge),
    'temp_blks_written': ('pg_stat_statements.temp_blks_written', 'postgresql.queries.temp_blks_written', AgentCheck.gauge),
}


# Columns to apply as tags
PG_STAT_STATEMENTS_TAG_COLUMNS = {
    'datname': ('pg_database.datname', 'db'),
    'rolname': ('pg_roles.rolname', 'user'),
    'query': ('pg_stat_statements.query', 'query'),
}


# Transformation functions to apply to each column before submission
PG_STAT_STATEMENTS_TRANSFORM = {
    # Truncate the query to 200 chars
    'query': lambda q: q[:200],
}


# TODO: move this to a shared lib
def compute_sql_signature(query):
    """
    Given a raw SQL query or prepared statement, generate a 64-bit hex signature
    on the normalized query.
    """
    normalized = datadog_agent.obfuscate_sql(query)
    return format(mmh3.hash64(normalized, signed=False)[0], 'x')


class PgStatementsMixin(object):
    """
    Mixin for collecting telemetry on executed statements.
    """

    def __init__(self, *args, **kwargs):
        # Cache results of monotonic pg_stat_statements to compare to previous collection
        self._statements_cache = {}

        # Available columns will be queried once and cached as the source of truth.
        self.__pg_stat_statements_columns = None

        # TODO: Make this a configurable limit
        self.query_limit = 500

    def _execute_query(self, cursor, query, log_func=None):
        raise NotImplementedError('Check must implement _execute_query()')

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
        for entry in (PG_STAT_STATEMENTS_COUNT_COLUMNS, PG_STAT_STATEMENTS_PER_STATEMENT_COLUMNS, PG_STAT_STATEMENTS_TAG_COLUMNS):
            for alias, (column, *_) in entry.items():
                # Only include columns which are available on the table
                if alias in self._pg_stat_statements_columns or alias in PG_STAT_STATEMENTS_TAG_COLUMNS:
                    columns.append('{column} AS {alias}'.format(column=column, alias=alias))

        rows = self._execute_query(cursor, STATEMENTS_QUERY.format(cols=', '.join(columns)))
        if not rows:
            return
        rows = rows[:self.query_limit]

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

            tags = ['query_signature:' + compute_sql_signature(row['query'])] + instance_tags
            for tag_column, (_, alias) in PG_STAT_STATEMENTS_TAG_COLUMNS.items():
                if tag_column not in self._pg_stat_statements_columns:
                    continue
                value = PG_STAT_STATEMENTS_TRANSFORM.get(tag_column, lambda x: x)(row[tag_column])
                tags.append('{alias}:{value}'.format(alias=alias, value=value))

            for alias, (_, name, fn) in list(PG_STAT_STATEMENTS_COUNT_COLUMNS.items()) + list(PG_STAT_STATEMENTS_PER_STATEMENT_COLUMNS.items()):
                if alias not in self._pg_stat_statements_columns:
                    continue

                if alias in PG_STAT_STATEMENTS_PER_STATEMENT_COLUMNS:
                    val = (row[alias] - prev[alias]) / (row['calls'] - prev['calls'])
                else:
                    val = row[alias] - prev[alias]

                fn(self, name, val, tags=tags)

        self.statement_cache = new_cache
