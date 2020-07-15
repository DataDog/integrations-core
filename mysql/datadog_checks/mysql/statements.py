# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from contextlib import closing

import pymysql

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


class MySQLStatementMetrics:
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, instance):
        self.statement_cache = dict()

        dbm_enabled = is_affirmative(datadog_agent.get_config('deep_database_monitoring'))
        self.enabled = dbm_enabled and not instance.get('options', {}).get('disable_query_metrics', False)
        self.max_query_metrics = int(instance.get('options', {}).get('max_query_metrics', 500))
        self.max_query_metrics_sort = int(instance.get('options', {}).get('max_query_metrics_sort', 100))
        self.escape_query_commas_hack = instance.get('options', {}).get('escape_query_commas_hack', False)
    
    def get_per_statement_metrics(self, db):
        if not self.enabled:
            return []

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
        rows = self._query_summary_per_statement(db)
        rows = self._compute_derivative_rows(rows, METRICS.keys(), key=lambda row: (row['schema'], row['digest']))
        rows = self._apply_row_limit(rows, 'count', True, METRICS.keys(), self.max_query_metrics, 
                                     top_k=self.max_query_metrics_sort, bottom_k=self.max_query_metrics_sort)

        metrics = dict()
        for row in rows:
            for col, (name, metric_type) in METRICS.items():
                tags = []
                if row['schema'] is not None:
                    tags.append('schema:' + row['schema'])
                obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
                if self.escape_query_commas_hack:
                    obfuscated_statement = obfuscated_statement.replace(', ', '，').replace(',', '，')
                tags.append('query:' + obfuscated_statement[:200])
                tags.append('query_signature:' + compute_sql_signature(obfuscated_statement))

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

    def _compute_derivative_rows(self, rows, metrics, key):
        """
        Given a list of rows, compute the derivative from the previous run for each row
        using the `key` function.
        """
        result = []
        new_cache = {}
        for row in rows:
            row_key = key(row)
            new_cache[row_key] = row
            prev = self.statement_cache.get(row_key)
            if prev is None:
                continue
            if any([row[k] - prev[k] < 0 for k in metrics]):
                # The table was truncated or stats reset; begin tracking again from this point
                continue
            result.append({k: row[k] - prev[k] if k in metrics else row[k] 
                           for k in row})

        self.statement_cache = new_cache
        return result

    @staticmethod
    def _apply_row_limit(rows, metric, metric_descending, secondary_metrics, limit, top_k, bottom_k):
        """
        Limits the number of rows while trying to ensure coverage across metrics. To ensure coverage of each 
        available metric when sorted, this function selects the top K and bottom K rows of each metric targeted. 
        However the resulting row count can be lower or higher than the target limit; in these cases, the
        primary metric will be used to truncate or fill rows which are below or above the query metric limit.

        The primary metric assumes ascending or descending are the most "interesting" values. For instance the
        'count' metric is more valuable descending since the most frequent queries should be kept over the less
        frequent queries.
        """
        if len(rows) < limit or len(rows) == 0:
            return rows

        limited = dict()
        row_key = lambda row: '|'.join([str(item[1]) for item in sorted(row.items(), key=lambda x: x[0])])
        for m in secondary_metrics:
            sorted_rows = sorted(rows, key=lambda row: row[m])
            top = sorted_rows[0:top_k]
            bottom = sorted_rows[bottom_k:]

            for row in top + bottom:
                key = row_key(row)
                limited[key] = row

        # Once the top and bottom of secondary metrics are all accounted for, 
        # fill the list by primary metric (if necessary) or truncate by primary metric (if necessary)
        if len(limited) < limit:
            for row in sorted(rows, key=lambda row: row[metric], reverse=metric_descending):
                key = row_key(row)
                limited[row] = row
                if len(limited) == limit:
                    break
            return list(limited.values())
        else:
            limited = list(limited.values())
            limited.sort(key=lambda row: row[metric], reverse=metric_descending)
            return limited[:limit]
