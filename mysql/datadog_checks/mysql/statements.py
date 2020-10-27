# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import logging
from contextlib import closing

import pymysql

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics, apply_row_limits

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


logger = logging.getLogger(__name__)


STATEMENT_METRICS = {
    'count': 'mysql.queries.count',
    'errors': 'mysql.queries.errors',
    'time': 'mysql.queries.time',
    'select_scan': 'mysql.queries.select_scan',
    'select_full_join': 'mysql.queries.select_full_join',
    'no_index_used': 'mysql.queries.no_index_used',
    'no_good_index_used': 'mysql.queries.no_good_index_used',
    'lock_time': 'mysql.queries.lock_time',
    'rows_affected': 'mysql.queries.rows_affected',
    'rows_sent': 'mysql.queries.rows_sent',
    'rows_examined': 'mysql.queries.rows_examined',
}

DEFAULT_STATEMENT_METRIC_LIMITS = {k: (10000, 10000) for k in STATEMENT_METRICS.keys()}


class MySQLStatementMetrics(object):
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, config):
        self.config = config
        self._state = StatementMetrics()

    def collect_per_statement_metrics(self, db):
        try:
            return self._collect_per_statement_metrics(db)
        except Exception:
            return []
            logger.exception('Unable to collect statement metrics due to an error')

    def _collect_per_statement_metrics(self, db):
        metrics = []

        def keyfunc(row):
            return (row['schema'], row['digest'])

        monotonic_rows = self._query_summary_per_statement(db)
        monotonic_rows = self._merge_duplicate_rows(monotonic_rows, key=keyfunc)
        rows = self._state.compute_derivative_rows(monotonic_rows, STATEMENT_METRICS.keys(), key=keyfunc)
        rows = apply_row_limits(
            rows,
            DEFAULT_STATEMENT_METRIC_LIMITS,
            'count',
            True,
            key=keyfunc,
        )

        for row in rows:
            tags = []
            tags.append('digest:' + row['digest'])
            if row['schema'] is not None:
                tags.append('schema:' + row['schema'])

            # Remove backticks from identifiers as they will be replaced by spaces in obfuscation
            row['query'] = self._normalize_digest_text(row['query'])
            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
            except Exception as e:
                logger.warning("Failed to obfuscate query '%s': %s", row['query'], e)
                continue
            tags.append('query_signature:' + compute_sql_signature(obfuscated_statement))
            tags.append('query:' + self._normalize_query_tag(obfuscated_statement))

            for col, name in STATEMENT_METRICS.items():
                value = row[col]
                metrics.append((name, value, tags))

        return metrics

    @staticmethod
    def _merge_duplicate_rows(rows, key):
        """
        Merges the metrics from duplicate rows because the (schema, digest) identifier may not be
        unique, see: https://bugs.mysql.com/bug.php?id=79533
        """
        merged = {}

        for row in rows:
            k = key(row)
            if k in merged:
                for m in STATEMENT_METRICS:
                    merged[k][m] += row[m]
            else:
                merged[k] = copy.copy(row)

        return list(merged.values())

    def _query_summary_per_statement(self, db):
        """
        Collects per-statement metrics from performance schema. Because the statement sums are
        cumulative, the results of the previous run are stored and subtracted from the current
        values to get the counts for the elapsed period. This is similar to monotonic_count, but
        several fields must be further processed from the delta values.
        """

        sql_statement_summary = """\
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
            logger.warning("Statement summary metrics are unavailable at this time: %s", e)
            return []

        return rows

    @staticmethod
    def _normalize_digest_text(query):
        """
        Cleans the digest query for obfuscation by stripping the backticks from identifiers.
        Digest text like "`schema` . `table`" are normalized to "schema.table" as well.
        """
        return query.replace('` . `', '.').replace('`', '')

    def _normalize_query_tag(self, query):
        """Normalize the query value to be used as a tag"""
        # Truncate to metrics tag limit
        query = query.strip()[:200]
        # Substitute commas in the query with unicode commas. Temp hack to
        # work around the bugs in arbitrary tag values on the backend.
        query = query.replace(', ', '，').replace(',', '，')
        return query
