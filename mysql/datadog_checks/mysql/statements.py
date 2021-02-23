# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
from contextlib import closing
from typing import Any, Callable, Dict, List, Tuple

import pymysql

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.sql import compute_sql_signature, normalize_query_tag
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics, apply_row_limits

from .config import MySQLConfig

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


PyMysqlRow = Dict[str, Any]
Row = Dict[str, Any]
RowKey = Tuple[Any]
RowKeyFunction = Callable[[PyMysqlRow], RowKey]
Metric = Tuple[str, int, List[str]]


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

# These limits define the top K and bottom K unique query rows for each metric. For each check run the
# max metrics sent will be sum of all numbers below (in practice, much less due to overlap in rows).
DEFAULT_STATEMENT_METRIC_LIMITS = {
    'count': (400, 0),
    'errors': (100, 0),
    'time': (400, 0),
    'select_scan': (50, 0),
    'select_full_join': (50, 0),
    'no_index_used': (50, 0),
    'no_good_index_used': (50, 0),
    'lock_time': (50, 0),
    'rows_affected': (100, 0),
    'rows_sent': (100, 0),
    'rows_examined': (100, 0),
    # Synthetic column limits
    'avg_time': (400, 0),
    'rows_sent_ratio': (0, 50),
}


def generate_synthetic_rows(rows):
    # type: (List[PyMysqlRow]) -> List[PyMysqlRow]
    """
    Given a list of rows, generate a new list of rows with "synthetic" column values derived from
    the existing row values.
    """
    synthetic_rows = []
    for row in rows:
        new = copy.copy(row)
        new['avg_time'] = float(new['time']) / new['count'] if new['count'] > 0 else 0
        new['rows_sent_ratio'] = float(new['rows_sent']) / new['rows_examined'] if new['rows_examined'] > 0 else 0

        synthetic_rows.append(new)

    return synthetic_rows


class MySQLStatementMetrics(object):
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, config):
        # type: (MySQLConfig) -> None
        self.config = config
        self.log = get_check_logger()
        self._state = StatementMetrics()

    def collect_per_statement_metrics(self, db):
        # type: (pymysql.connections.Connection) -> List[Metric]
        try:
            return self._collect_per_statement_metrics(db)
        except Exception:
            self.log.exception('Unable to collect statement metrics due to an error')
            return []

    def _collect_per_statement_metrics(self, db):
        # type: (pymysql.connections.Connection) -> List[Metric]
        metrics = []  # type: List[Metric]

        def keyfunc(row):
            return (row['schema'], row['digest'])

        monotonic_rows = self._query_summary_per_statement(db)
        monotonic_rows = self._merge_duplicate_rows(monotonic_rows, key=keyfunc)
        rows = self._state.compute_derivative_rows(monotonic_rows, STATEMENT_METRICS.keys(), key=keyfunc)
        metrics.append(('dd.mysql.queries.query_rows_raw', len(rows), []))

        rows = generate_synthetic_rows(rows)
        rows = apply_row_limits(
            rows,
            self.config.statement_metric_limits or DEFAULT_STATEMENT_METRIC_LIMITS,
            tiebreaker_metric='count',
            tiebreaker_reverse=True,
            key=keyfunc,
        )
        metrics.append(('dd.mysql.queries.query_rows_limited', len(rows), []))

        for row in rows:
            tags = []
            tags.append('digest:' + row['digest'])
            if row['schema'] is not None:
                tags.append('schema:' + row['schema'])

            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(row['query'])
            except Exception as e:
                self.log.warning("Failed to obfuscate query '%s': %s", row['query'], e)
                continue
            tags.append('query_signature:' + compute_sql_signature(obfuscated_statement))
            tags.append('query:' + normalize_query_tag(obfuscated_statement).strip())

            for col, name in STATEMENT_METRICS.items():
                value = row[col]
                metrics.append((name, value, tags))

        return metrics

    @staticmethod
    def _merge_duplicate_rows(rows, key):
        # type: (List[PyMysqlRow], RowKeyFunction) -> List[PyMysqlRow]
        """
        Merges the metrics from duplicate rows because the (schema, digest) identifier may not be
        unique, see: https://bugs.mysql.com/bug.php?id=79533
        """
        merged = {}  # type: Dict[RowKey, PyMysqlRow]

        for row in rows:
            k = key(row)
            if k in merged:
                for m in STATEMENT_METRICS:
                    merged[k][m] += row[m]
            else:
                merged[k] = copy.copy(row)

        return list(merged.values())

    def _query_summary_per_statement(self, db):
        # type: (pymysql.connections.Connection) -> List[PyMysqlRow]
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

        rows = []  # type: List[PyMysqlRow]

        try:
            with closing(db.cursor(pymysql.cursors.DictCursor)) as cursor:
                cursor.execute(sql_statement_summary)

                rows = cursor.fetchall() or []  # type: ignore
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.log.warning("Statement summary metrics are unavailable at this time: %s", e)

        return rows
