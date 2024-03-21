# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time
from contextlib import closing
from operator import attrgetter
from typing import Any, Callable, Dict, List, Tuple

import pymysql
from cachetools import TTLCache

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mysql.cursor import CommenterDictCursor

from .util import DatabaseConfigurationError, connect_with_autocommit, warning_with_tags

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


class MySQLStatementMetrics(DBMAsyncJob):
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, check, config, connection_args):
        # (MySql, MySQLConfig) -> None
        collection_interval = float(config.statement_metrics_config.get('collection_interval', 10))
        if collection_interval <= 0:
            collection_interval = 10
        super(MySQLStatementMetrics, self).__init__(
            check,
            rate_limit=1 / float(collection_interval),
            run_sync=is_affirmative(config.statement_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(config.statement_metrics_config.get('enabled', True)),
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            min_collection_interval=config.min_collection_interval,
            dbms="mysql",
            job_name="statement-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self._check = check
        self._metric_collection_interval = collection_interval
        self._connection_args = connection_args
        self._db = None
        self._config = config
        self.log = get_check_logger()
        self._state = StatementMetrics()
        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self._config.full_statement_text_cache_max_size,
            ttl=60 * 60 / self._config.full_statement_text_samples_per_hour_per_query,
        )  # type: TTLCache

    def _get_db_connection(self):
        """
        lazy reconnect db
        pymysql connections are not thread safe so we can't reuse the same connection from the main check
        :return:
        """
        if not self._db:
            self._db = connect_with_autocommit(**self._connection_args)
        return self._db

    def _close_db_conn(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                self._log.debug("Failed to close db connection", exc_info=1)
            finally:
                self._db = None

    def run_job(self):
        self.collect_per_statement_metrics()

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def collect_per_statement_metrics(self):
        # Detect a database misconfiguration by checking if the performance schema is enabled since mysql
        # just returns no rows without errors if the performance schema is disabled
        if self._check.performance_schema_enabled is None:
            self.log.debug('Waiting for performance schema availability to be determined by the check, skipping run.')
            return
        if self._check.performance_schema_enabled is False:
            self._check.record_warning(
                DatabaseConfigurationError.performance_schema_not_enabled,
                warning_with_tags(
                    'Unable to collect statement metrics because the performance schema is disabled. '
                    'See https://docs.datadoghq.com/database_monitoring/setup_mysql/'
                    'troubleshooting#%s for more details',
                    DatabaseConfigurationError.performance_schema_not_enabled.value,
                    code=DatabaseConfigurationError.performance_schema_not_enabled.value,
                    host=self._check.resolved_hostname,
                ),
            )
            return

        rows = self._collect_per_statement_metrics()
        if not rows:
            return
        # Omit internal tags for dbm payloads since those are only relevant to metrics processed directly
        # by the agent
        tags = [t for t in self._tags if not t.startswith('dd.internal')]
        for event in self._rows_to_fqt_events(rows, tags):
            self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
        payload = {
            'host': self._check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'mysql_version': self._check.version.version + '+' + self._check.version.build,
            'mysql_flavor': self._check.version.flavor,
            "ddagenthostname": self._check.agent_hostname,
            'ddagentversion': datadog_agent.get_version(),
            'min_collection_interval': self._metric_collection_interval,
            'tags': tags,
            'cloud_metadata': self._config.cloud_metadata,
            'mysql_rows': rows,
        }
        self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        self._check.count(
            "dd.mysql.collect_per_statement_metrics.rows",
            len(rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    def _collect_per_statement_metrics(self):
        # type: () -> List[PyMysqlRow]
        monotonic_rows = self._query_summary_per_statement()
        monotonic_rows = self._normalize_queries(monotonic_rows)
        rows = self._state.compute_derivative_rows(monotonic_rows, METRICS_COLUMNS, key=_row_key)
        return rows

    def _query_summary_per_statement(self):
        # type: () -> List[PyMysqlRow]
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
            WHERE `digest_text` NOT LIKE 'EXPLAIN %' OR `digest_text` IS NULL
            ORDER BY `count_star` DESC
            LIMIT 10000"""

        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute(sql_statement_summary)

            rows = cursor.fetchall() or []  # type: ignore

        return rows

    def _normalize_queries(self, rows):
        normalized_rows = []
        for row in rows:
            normalized_row = dict(copy.copy(row))
            try:
                statement = obfuscate_sql_with_metadata(row['digest_text'], self._obfuscate_options)
                obfuscated_statement = statement['query'] if row['digest_text'] is not None else None
            except Exception as e:
                self.log.warning("Failed to obfuscate query=[%s] | err=[%s]", row['digest_text'], e)
                continue

            normalized_row['digest_text'] = obfuscated_statement
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_statement)
            metadata = statement['metadata']
            normalized_row['dd_tables'] = metadata.get('tables', None)
            normalized_row['dd_commands'] = metadata.get('commands', None)
            normalized_row['dd_comments'] = metadata.get('comments', None)
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
                "host": self._check.resolved_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "mysql",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                "db": {
                    "instance": row['schema_name'],
                    "query_signature": row['query_signature'],
                    "statement": row['digest_text'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                        "comments": row['dd_comments'],
                    },
                },
                "mysql": {"schema": row["schema_name"]},
            }
