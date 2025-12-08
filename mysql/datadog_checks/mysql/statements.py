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
from datadog_checks.base.utils.db.utils import DBMAsyncJob, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mysql.cursor import CommenterDictCursor

from .util import DatabaseConfigurationError, ManagedAuthConnectionMixin, warning_with_tags

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

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


class MySQLStatementMetrics(ManagedAuthConnectionMixin, DBMAsyncJob):
    """
    MySQLStatementMetrics collects database metrics per normalized MySQL statement
    """

    def __init__(self, check, config, connection_args_provider, uses_managed_auth=False):
        # (MySql, MySQLConfig, Callable, bool) -> None
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
        self._collect_prepared_statements = None
        self._metric_collection_interval = collection_interval
        self._connection_args_provider = connection_args_provider
        self._uses_managed_auth = uses_managed_auth
        self._db_created_at = 0
        self._db = None
        self._config = config
        self.log = get_check_logger()
        self._state = StatementMetrics()
        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))
        # last_seen: the last query execution time seen by the check
        # This is used to limit the queries to fetch from the performance schema to only the new ones
        self._last_seen = '1970-01-01'
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self._config.full_statement_text_cache_max_size,
            ttl=60 * 60 / self._config.full_statement_text_samples_per_hour_per_query,
        )  # type: TTLCache

        # statement_rows: cache of all rows for each digest, keyed by (schema_name, query_signature)
        # This is used to cache the metrics for queries that have the same query_signature but different digests
        self._statement_rows = TTLCache(
            maxsize=self._config.statement_rows_cache_max_size,
            ttl=self._config.statement_rows_cache_ttl,
        )

    def _close_db_conn(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                self._log.debug("Failed to close db connection", exc_info=1)
            finally:
                self._db = None

    def run_job(self):
        start = time.time()
        self._statement_rows.expire()
        self.collect_per_statement_metrics()
        self._check.gauge(
            "dd.mysql.statement_metrics.collect_metrics.elapsed_ms",
            (time.time() - start) * 1000,
            tags=self._check.tag_manager.get_tags() + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def collect_per_statement_metrics(self):
        # Detect a database misconfiguration by checking if the performance schema is enabled since mysql
        # just returns no rows without errors if the performance schema is disabled
        if self._check.global_variables.performance_schema_enabled is False:
            self._check.record_warning(
                DatabaseConfigurationError.performance_schema_not_enabled,
                warning_with_tags(
                    'Unable to collect statement metrics because the performance schema is disabled. '
                    'See https://docs.datadoghq.com/database_monitoring/setup_mysql/'
                    'troubleshooting#%s for more details',
                    DatabaseConfigurationError.performance_schema_not_enabled.value,
                    code=DatabaseConfigurationError.performance_schema_not_enabled.value,
                    host=self._check.reported_hostname,
                ),
            )
            return

        # Omit internal tags for dbm payloads since those are only relevant to metrics processed directly
        # by the agent
        tags = [t for t in self._tags if not t.startswith('dd.internal')]

        rows = self._collect_per_statement_metrics(tags)
        if not rows:
            # No rows to process, can skip the rest of the payload generation and avoid an empty payload
            return
        for event in self._rows_to_fqt_events(rows, tags):
            self._check.database_monitoring_query_sample(event)
        payload = {
            'host': self._check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'mysql_version': self._check.version.version + '+' + self._check.version.build,
            'mysql_flavor': self._check.version.flavor,
            'ddagentversion': datadog_agent.get_version(),
            'min_collection_interval': self._metric_collection_interval,
            'tags': tags,
            'cloud_metadata': self._config.cloud_metadata,
            'service': self._config.service,
            'mysql_rows': rows,
        }
        self._check.database_monitoring_query_metrics(payload)
        self._check.gauge(
            "dd.mysql.collect_per_statement_metrics.rows",
            len(rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
        )

    def _collect_per_statement_metrics(self, tags):
        # type: (List[str]) -> List[PyMysqlRow]

        self._get_statement_count(tags)

        monotonic_rows = self._query_summary_per_statement()
        self._check.gauge(
            "dd.mysql.statement_metrics.query_rows",
            len(monotonic_rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

        monotonic_rows = self._filter_query_rows(monotonic_rows)
        monotonic_rows = self._normalize_queries(monotonic_rows)
        monotonic_rows = self._add_associated_rows(monotonic_rows)
        rows = self._state.compute_derivative_rows(monotonic_rows, METRICS_COLUMNS, key=_row_key)
        return rows

    def _get_statement_count(self, tags):
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute("SELECT count(*) AS count from performance_schema.events_statements_summary_by_digest")

            rows = cursor.fetchall() or []  # type: ignore
            if rows:
                self._check.gauge(
                    "dd.mysql.statement_metrics.events_statements_summary_by_digest.total_rows",
                    rows[0]['count'],
                    tags=tags + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )

    def _query_summary_per_statement(self):
        # type: () -> List[PyMysqlRow]
        """
        Collects per-statement metrics from performance schema. Because the statement sums are
        cumulative, the results of the previous run are stored and subtracted from the current
        values to get the counts for the elapsed period. This is similar to monotonic_count, but
        several fields must be further processed from the delta values.
        """
        only_query_recent_statements = self._config.statement_metrics_config.get('only_query_recent_statements', False)
        # Since `performance_schema.prepared_statements_instances` doesn't have a last_seen column,
        # we only collect prepared statements if we're not querying recent statements
        collect_prepared_statements = not only_query_recent_statements and self.collect_prepared_statements

        condition = (
            "WHERE `last_seen` >= %s"
            if only_query_recent_statements
            else "WHERE `digest_text` NOT LIKE 'EXPLAIN %' OR `digest_text` IS NULL"
        )

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
                   `sum_no_good_index_used`,
                   `last_seen`
            FROM performance_schema.events_statements_summary_by_digest
            {}
            """.format(condition)

        if collect_prepared_statements:
            # Every prepared statement object has a row in `performance_schema.prepared_statements_instances`.
            # Group by `schema_name` and `digest_text` to get the totals for each statement.
            prepared_sql_statement_summary = """\
                SELECT  `owner_object_schema` AS `schema_name`,
                        NULL AS `digest`,
                        `sql_text` AS `digest_text`,
                        sum(`count_execute`) AS `count_star`,
                        sum(`sum_timer_execute`) AS `sum_timer_wait`,
                        sum(`sum_lock_time`) AS `sum_lock_time`,
                        sum(`sum_errors`) AS `sum_errors`,
                        sum(`sum_rows_affected`) AS `sum_rows_affected`,
                        sum(`sum_rows_sent`) AS `sum_rows_sent`,
                        sum(`sum_rows_examined`) AS `sum_rows_examined`,
                        sum(`sum_select_scan`) AS `sum_select_scan`,
                        sum(`sum_select_full_join`) AS `sum_select_full_join`,
                        sum(`sum_no_index_used`) AS `sum_no_index_used`,
                        sum(`sum_no_good_index_used`) AS `sum_no_good_index_used`,
                        NOW() AS `last_seen`
                FROM performance_schema.prepared_statements_instances
                WHERE `sql_text` NOT LIKE 'EXPLAIN %' OR `sql_text` IS NULL
                GROUP BY `owner_object_schema`, `sql_text`
                """

            sql_statement_summary = f"""\
                {sql_statement_summary}
                UNION ALL
                {prepared_sql_statement_summary}
                """
        if not only_query_recent_statements:
            sql_statement_summary = f"""\
                {sql_statement_summary}
                ORDER BY `count_star` DESC
                LIMIT 10000
                """

        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            args = [self._last_seen] if only_query_recent_statements else None
            cursor.execute(sql_statement_summary, args)

            rows = cursor.fetchall() or []  # type: ignore

        if rows:
            self._last_seen = max(row['last_seen'] for row in rows)

        return rows

    def _filter_query_rows(self, rows):
        # type: (List[PyMysqlRow]) -> List[PyMysqlRow]
        """
        Filter out rows that are EXPLAIN statements
        """
        return [
            row for row in rows if row['digest_text'] is None or not row['digest_text'].lower().startswith('explain')
        ]

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

    def _add_associated_rows(self, rows):
        """
        If two or more statements with different digests have the same query_signature, they are considered the same
        Because only one digest statement may be updated, we cache all the rows for each digest,
        update with any new rows and then return all the rows for all the query_signatures.

        We return all rows to guard against the case where a signature wasn't collected on the immediately previous run
        but was present on runs before that.
        """
        for row in rows:
            key = (row['schema_name'], row['query_signature'])
            digest_rows = self._statement_rows.get(key, {})
            digest_rows[row['digest']] = row
            self._statement_rows[key] = digest_rows

        return [row for statement_row in self._statement_rows.values() for row in statement_row.values()]

    def _rows_to_fqt_events(self, rows, tags):
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            row_tags = tags + ["schema:{}".format(row['schema_name'])] if row['schema_name'] else tags
            yield {
                "timestamp": time.time() * 1000,
                "host": self._check.reported_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "mysql",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                'service': self._config.service,
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

    @property
    def collect_prepared_statements(self):
        if self._collect_prepared_statements is None:
            # prepared_statements_instances table was added to MariaDB 10.5.2
            if self._check.is_mariadb and self._check.version.version_compatible((10, 5, 2)) is False:
                self._collect_prepared_statements = False
            # prepared_statements_instances table was added to MySQL 5.7.4
            elif self._check.version.version_compatible((5, 7, 4)) is False:
                self._collect_prepared_statements = False
            else:
                self._collect_prepared_statements = self._config.statement_metrics_config.get(
                    'collect_prepared_statements', True
                )
        return self._collect_prepared_statements
