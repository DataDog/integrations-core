# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time
from contextlib import closing
from typing import Any, Callable, Dict, List, Tuple

import pymysql

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import default_json_event_encoding, resolve_db_host
from datadog_checks.base.utils.serialization import json

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


PyMysqlRow = Dict[str, Any]
Row = Dict[str, Any]
RowKey = Tuple[Any]
RowKeyFunction = Callable[[PyMysqlRow], RowKey]
Metric = Tuple[str, int, List[str]]


METRICS_COLUMNS = {
    'count_star',
    'sum_timer_wait',
    'sum_lock_time',
    'sum_errors',
    'sum_rows_affected',
    'sum_rows_sent',
    'sum_rows_examined',
    'sum_select_scan',
    'sum_select_full_join',
    'sum_no_index_used',
    'sum_no_good_index_used',
}

# These limits define the top K and bottom K unique query rows for each metric. For each check run the
# max metrics sent will be sum of all numbers below (in practice, much less due to overlap in rows).
DEFAULT_STATEMENT_METRICS_LIMITS = {
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


class MySQLStatementMetrics(object):
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, check, config):
        # (MySql, MySQLConfig) -> None
        self._check = check
        self._config = config
        self._db_hostname = resolve_db_host(self._config.host)
        self.log = get_check_logger()
        self._state = StatementMetrics()

    def collect_per_statement_metrics(self, db, tags):
        # type: (pymysql.connections.Connection, List[str]) -> None
        try:
            rows = self._collect_per_statement_metrics(db)
            if not rows:
                return
            payload = {
                'host': self._db_hostname,
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._config.min_collection_interval,
                'tags': tags,
                'mysql_rows': rows,
            }
            self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        except Exception:
            self.log.exception('Unable to collect statement metrics due to an error')

    def _collect_per_statement_metrics(self, db):
        # type: (pymysql.connections.Connection) -> List[Metric]
        metrics = []  # type: List[Metric]

        def keyfunc(row):
            return (row['schema_name'], row['query_signature'])

        monotonic_rows = self._query_summary_per_statement(db)
        monotonic_rows = self._normalize_queries(monotonic_rows)
        rows = self._state.compute_derivative_rows(monotonic_rows, METRICS_COLUMNS, key=keyfunc)
        metrics.append(('dd.mysql.queries.query_rows_raw', len(rows), []))

        return rows

    def _query_summary_per_statement(self, db):
        # type: (pymysql.connections.Connection) -> List[PyMysqlRow]
        """
        Collects per-statement metrics from performance schema. Because the statement sums are
        cumulative, the results of the previous run are stored and subtracted from the current
        values to get the counts for the elapsed period. This is similar to monotonic_count, but
        several fields must be further processed from the delta values.
        """

        sql_statement_summary = """\
            SELECT `schema_name`,
                   `digest`,
                   `digest_text`,
                   `count_star`,
                   `sum_timer_wait`,
                   `sum_lock_time`,
                   `sum_errors`,
                   `sum_rows_affected`,
                   `sum_rows_sent`,
                   `sum_rows_examined`,
                   `sum_select_scan`,
                   `sum_select_full_join`,
                   `sum_no_index_used`,
                   `sum_no_good_index_used`
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

    def _normalize_queries(self, rows):
        normalized_rows = []
        for row in rows:
            normalized_row = dict(copy.copy(row))
            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(row['digest_text'])
            except Exception as e:
                self.log.warning("Failed to obfuscate query '%s': %s", row['digest_text'], e)
                continue

            normalized_row['digest_text'] = obfuscated_statement
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_statement)
            normalized_rows.append(normalized_row)

        return normalized_rows
