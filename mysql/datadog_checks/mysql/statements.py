# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
from contextlib import closing

import pymysql

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics, apply_row_limits, is_dbm_enabled

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


METRICS = {
    'count': ('mysql.queries.count', AgentCheck.count),
    'errors': ('mysql.queries.errors', AgentCheck.count),
    'time': ('mysql.queries.time', AgentCheck.count),
    'select_scan': ('mysql.queries.select_scan', AgentCheck.count),
    'select_full_join': ('mysql.queries.select_full_join', AgentCheck.count),
    'no_index_used': ('mysql.queries.no_index_used', AgentCheck.count),
    'no_good_index_used': ('mysql.queries.no_good_index_used', AgentCheck.count),
    'lock_time': ('mysql.queries.lock_time', AgentCheck.count),
    'rows_affected': ('mysql.queries.rows_affected', AgentCheck.count),
    'rows_sent': ('mysql.queries.rows_sent', AgentCheck.count),
    'rows_examined': ('mysql.queries.rows_examined', AgentCheck.count),
}


DEFAULT_METRIC_LIMITS = {
    # TODO: Reduce limits after usage patterns are better understood
    'count': (10000, 10000),
    'errors': (10000, 10000),
    'time': (10000, 10000),
    'select_scan': (200, 200),
    'select_full_join': (200, 200),
    'no_index_used': (200, 200),
    'no_good_index_used': (200, 200),
    'lock_time': (200, 200),
    'rows_affected': (500, 500),
    'rows_sent': (500, 500),
    'rows_examined': (500, 500),
}

class MySQLStatementMetrics:
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, instance, log):
        super(MySQLStatementMetrics, self).__init__()
        self.log = log
        self._state = StatementMetrics(self.log)
        self.is_disabled = instance.get('options', {}).get('disable_query_metrics', False)
        self.query_metric_limits = instance.get('options', {}).get('query_metric_limits', DEFAULT_METRIC_LIMITS)
        self.escape_query_commas_hack = instance.get('options', {}).get('escape_query_commas_hack', False)
    
    def get_per_statement_metrics(self, db):
        if self.is_disabled or not is_dbm_enabled():
            return []

        rows = self._query_summary_per_statement(db)
        rows = self._state.compute_derivative_rows(rows, METRICS.keys(), key=lambda row: (row['schema'], row['digest']))
        rows = apply_row_limits(rows, self.query_metric_limits, 'count', True, key=lambda row: (row['schema'], row['digest']))

        metrics = dict()

        for row in rows:
            tags = []
            if row['schema'] is not None:
                tags.append('schema:' + row['schema'])
            obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
            if self.escape_query_commas_hack:
                obfuscated_statement = obfuscated_statement.replace(', ', '，').replace(',', '，')
            tags.append('query:' + obfuscated_statement[:200])
            tags.append('query_signature:' + compute_sql_signature(obfuscated_statement))

            for col, (name, metric_type) in METRICS.items():
                # Merge metrics in cases where the query signature differs from the DB digest
                value = row[col]
                key = '|'.join([name] + sorted(tags))
                if key in metrics:
                    _, prev_value, _, _ = metrics[key]
                    value += prev_value
                metrics[key] = (name, value, metric_type, tags)
        return list(metrics.values())

    def _query_summary_per_statement(self, db):
        """
        Collects per-statement metrics from performance schema. Because the statement sums are
        cumulative, the results of the previous run are stored and subtracted from the current
        values to get the counts for the elapsed period. This is similar to monotonic_count, but
        several fields must be further processed from the delta values.
        """

        sql_statement_summary ="""\
            SELECT `schema_name` as `schema`,
                `digest` as `digest`,
                `digest_text` as `query`,
                `count_star` as `count`,
                `sum_timer_wait` / 1000 as `time`,
                `sum_lock_time` / 1000 as `lock_time`,
                `sum_errors` as `errors`,
                `sum_rows_affected` as `rows_affected`,
                `sum_rows_sent` as `rows_sent`,
                `sum_rows_examined` as `rows_examined`,
                `sum_select_scan` as `select_scan`,
                `sum_select_full_join` as `select_full_join`,
                `sum_no_index_used` as `no_index_used`,
                `sum_no_good_index_used` as `no_good_index_used`
            FROM performance_schema.events_statements_summary_by_digest
            WHERE `digest_text` NOT LIKE 'EXPLAIN %'
            ORDER BY `count_star` DESC
            LIMIT 10000"""

        try:
            with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
                cursor.execute(sql_statement_summary)

                rows = cursor.fetchall()
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("Statement summary metrics are unavailable at this time: %s", e)
            return []
        
        return rows
