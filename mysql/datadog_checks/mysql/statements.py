# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time
from contextlib import closing
from typing import Any, Callable, Dict, List, Tuple

import pymysql
from cachetools import TTLCache

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


def _row_key(row):
    """
    :param row: a normalized row from events_statements_summary_by_digest
    :return: a tuple uniquely identifying this row
    """
    return row['schema_name'], row['query_signature']


class MySQLStatementMetrics(object):
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, check, config):
        # (MySql, MySQLConfig) -> None
        self._check = check
        self._config = config
        self._db_hostname = None
        self.log = get_check_logger()
        self._state = StatementMetrics()
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self._config.full_statement_text_cache_max_size,
            ttl=60 * 60 / self._config.full_statement_text_samples_per_hour_per_query,
        )  # type: TTLCache

    def _db_hostname_cached(self):
        if self._db_hostname:
            return self._db_hostname
        self._db_hostname = resolve_db_host(self._config.host)
        return self._db_hostname

    def collect_per_statement_metrics(self, db, tags):
        # type: (pymysql.connections.Connection, List[str]) -> None
        try:
            rows = self._collect_per_statement_metrics(db)
            if not rows:
                return

            for event in self._rows_to_fqt_events(rows, tags):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

            # truncate query text to the maximum length supported by metrics tags
            for row in rows:
                row['digest_text'] = row['digest_text'][0:200]

            payload = {
                'host': self._db_hostname_cached(),
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._config.min_collection_interval,
                'tags': tags,
                'mysql_rows': rows,
            }
            self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        except Exception:
            self.log.exception('Unable to collect statement metrics due to an error')

    def _collect_per_statement_metrics(self, db):
        # type: (pymysql.connections.Connection) -> List[PyMysqlRow]
        monotonic_rows = self._query_summary_per_statement(db)
        monotonic_rows = self._normalize_queries(monotonic_rows)
        rows = self._state.compute_derivative_rows(monotonic_rows, METRICS_COLUMNS, key=_row_key)
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

    def _rows_to_fqt_events(self, rows, tags):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            row_tags = tags + ["schema:{}".format(row['schema_name'])] if row['schema_name'] else tags
            yield {
                "timestamp": time.time() * 1000,
                "host": self._db_hostname_cached(),
                "ddsource": "mysql",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                "db": {
                    "instance": row['schema_name'],
                    "query_signature": row['query_signature'],
                    "statement": row['digest_text'],
                },
                "mysql": {"schema": row["schema_name"]},
            }
