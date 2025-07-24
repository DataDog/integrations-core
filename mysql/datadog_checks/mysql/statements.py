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

from .util import DatabaseConfigurationError, connect_with_session_variables, warning_with_tags

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

# TiDB statements_summary column mappings to MySQL performance_schema
# Note: This mapping is kept for reference but the normalization function
# handles the mapping directly due to version compatibility issues
TIDB_TO_MYSQL_COLUMN_MAPPINGS = {
    # TiDB column -> MySQL column
    'SCHEMA_NAME': 'schema_name',
    'DIGEST': 'digest',
    'DIGEST_TEXT': 'digest_text',
    'EXEC_COUNT': 'count_star',
    'SUM_LATENCY': 'sum_timer_wait',  # TiDB uses nanoseconds like MySQL
    'SUM_ERRORS': 'sum_errors',
    'SUM_AFFECT_ROWS': 'sum_rows_affected',
    'LAST_SEEN': 'last_seen',
}


def _row_key(row):
    """
    :param row: a normalized row from events_statements_summary_by_digest
    :return: a tuple uniquely identifying this row
    """
    return row['schema_name'], row['query_signature']


def _get_tidb_statement_summary_query(only_query_recent_statements=False, last_seen=None):
    """
    Builds the TiDB equivalent query for statement summary collection.

    Uses information_schema.cluster_statements_summary which provides cluster-wide
    statistics across all TiDB nodes.

    Args:
        only_query_recent_statements: If True, only query statements seen recently
        last_seen: Timestamp for filtering recent statements

    Returns:
        tuple: (query_string, query_args)
    """
    if only_query_recent_statements:
        condition = "WHERE `LAST_SEEN` >= %s"
        args = [last_seen]
    else:
        # TiDB doesn't need to exclude EXPLAIN statements as they're not stored
        condition = """
            ORDER BY `EXEC_COUNT` DESC
            LIMIT 10000
        """
        args = None

    # Use only columns that exist in the TiDB cluster_statements_summary table
    query = f"""\
        SELECT
            `INSTANCE`,
            `SCHEMA_NAME`,
            `DIGEST`,
            `DIGEST_TEXT`,
            `EXEC_COUNT`,
            `SUM_LATENCY`,
            `SUM_ERRORS`,
            `AVG_AFFECTED_ROWS`,
            `LAST_SEEN`,
            `AVG_LATENCY`,
            `MAX_LATENCY`,
            `AVG_MEM`,
            `MAX_MEM`,
            `AVG_RESULT_ROWS`,
            `MAX_RESULT_ROWS`
        FROM information_schema.cluster_statements_summary
        {condition}
    """

    return query, args


def _normalize_tidb_statement_row(row):
    """
    Normalizes a TiDB cluster_statements_summary row to match MySQL performance_schema format.

    Args:
        row: A row from information_schema.cluster_statements_summary

    Returns:
        dict: Normalized row matching MySQL format
    """
    normalized = {}

    # Map available TiDB columns to MySQL columns
    normalized['schema_name'] = row.get('SCHEMA_NAME', '')
    normalized['digest'] = row.get('DIGEST', '')
    normalized['digest_text'] = row.get('DIGEST_TEXT', '')
    normalized['count_star'] = row.get('EXEC_COUNT', 0)
    normalized['sum_timer_wait'] = row.get('SUM_LATENCY', 0)
    normalized['sum_errors'] = row.get('SUM_ERRORS', 0)
    # TiDB has AVG_AFFECTED_ROWS, need to multiply by EXEC_COUNT to get sum
    exec_count = row.get('EXEC_COUNT', 0)
    avg_affected = row.get('AVG_AFFECTED_ROWS', 0)
    normalized['sum_rows_affected'] = int(avg_affected * exec_count) if exec_count > 0 else 0
    normalized['last_seen'] = row.get('LAST_SEEN', '')

    # Use AVG_RESULT_ROWS * EXEC_COUNT as an approximation for sum_rows_sent
    avg_result_rows = row.get('AVG_RESULT_ROWS', 0)
    normalized['sum_rows_sent'] = int(avg_result_rows * exec_count) if exec_count > 0 else 0

    # Set default values for MySQL columns that TiDB doesn't have
    normalized['sum_lock_time'] = 0  # TiDB doesn't track lock time separately
    normalized['sum_rows_examined'] = 0  # Not available in TiDB stats
    normalized['sum_select_scan'] = 0
    normalized['sum_select_full_join'] = 0
    normalized['sum_no_index_used'] = 0
    normalized['sum_no_good_index_used'] = 0

    # Add TiDB-specific metrics as internal fields (prefixed with _)
    normalized['_tidb_instance'] = row.get('INSTANCE', '')
    normalized['_tidb_avg_latency'] = row.get('AVG_LATENCY', 0)
    normalized['_tidb_max_latency'] = row.get('MAX_LATENCY', 0)
    normalized['_tidb_avg_mem'] = row.get('AVG_MEM', 0)
    normalized['_tidb_max_mem'] = row.get('MAX_MEM', 0)

    return normalized


def _is_tidb_statements_summary_available(cursor):
    """
    Check if TiDB cluster_statements_summary table is available and accessible.

    Args:
        cursor: Database cursor

    Returns:
        bool: True if available, False otherwise
    """
    try:
        cursor.execute("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'information_schema'
            AND table_name = 'cluster_statements_summary'
            LIMIT 1
        """)
        return cursor.fetchone() is not None
    except Exception:
        return False


def _collect_tidb_statement_metrics_rows(cursor, only_query_recent_statements=False, last_seen=None):
    """
    Collects statement metrics from TiDB and normalizes them to MySQL format.

    Args:
        cursor: Database cursor
        only_query_recent_statements: If True, only query recent statements
        last_seen: Timestamp for filtering recent statements

    Returns:
        list: Normalized rows matching MySQL performance_schema format
    """
    query, args = _get_tidb_statement_summary_query(only_query_recent_statements, last_seen)

    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)

    rows = cursor.fetchall() or []

    # Normalize rows to match MySQL format
    normalized_rows = []
    for row in rows:
        normalized_row = _normalize_tidb_statement_row(row)
        normalized_rows.append(normalized_row)

    return normalized_rows


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
        # last_seen: the last query execution time seen by the check
        # This is used to limit the queries to fetch from the performance schema to only the new ones
        self._last_seen = '1970-01-01'
        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        # For TiDB, we'll check this lazily on first use to avoid connecting during init
        self._is_tidb_checked = False
        self._samples_per_hour = None
        self._full_statement_text_cache = None

        # statement_rows: cache of all rows for each digest, keyed by (schema_name, query_signature)
        # This is used to cache the metrics for queries that have the same query_signature but different digests
        self._statement_rows = {}  # type: Dict[(str, str), Dict[str, PyMysqlRow]]

    def _get_db_connection(self):
        """
        lazy reconnect db
        pymysql connections are not thread safe so we can't reuse the same connection from the main check
        :return:
        """
        if not self._db:
            self._db = connect_with_session_variables(**self._connection_args)
        return self._db

    def _ensure_fqt_cache_initialized(self):
        """
        Lazily initialize the full statement text cache with appropriate rate limit
        """
        if self._full_statement_text_cache is not None:
            return

        # Check if this is TiDB and set appropriate rate limit
        if not self._is_tidb_checked:
            self._is_tidb_checked = True
            db = self._get_db_connection()
            if self._check._get_is_tidb(db):
                self._samples_per_hour = max(6, self._config.full_statement_text_samples_per_hour_per_query)
                self.log.info(
                    "TiDB: Using enhanced FQT rate limit of %d samples per hour (every %d minutes)",
                    self._samples_per_hour,
                    60 // self._samples_per_hour,
                )
            else:
                self._samples_per_hour = self._config.full_statement_text_samples_per_hour_per_query

        self._full_statement_text_cache = TTLCache(
            maxsize=self._config.full_statement_text_cache_max_size,
            ttl=60 * 60 / self._samples_per_hour,
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
        self.collect_per_statement_metrics()
        self._check.gauge(
            "dd.mysql.statement_metrics.collect_metrics.elapsed_ms",
            (time.time() - start) * 1000,
            tags=self._check.tag_manager.get_tags() + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def collect_per_statement_metrics(self):
        # For TiDB, we don't need performance_schema as it uses information_schema.cluster_statements_summary
        if self._check._get_is_tidb(self._db):
            self.log.debug('TiDB detected, using cluster_statements_summary for statement metrics')
        else:
            # Detect a database misconfiguration by checking if the performance schema is enabled since mysql
            # just returns no rows without errors if the performance schema is disabled
            if self._check.performance_schema_enabled is None:
                self.log.debug(
                    'Waiting for performance schema availability to be determined by the check, skipping run.'
                )
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
            if self._check._get_is_tidb(self._db):
                self.log.debug("TiDB: No rows returned from _collect_per_statement_metrics")
            return

        # Debug logging for TiDB FQT events
        fqt_event_count = 0
        if self._check._get_is_tidb(self._db):
            self.log.debug("TiDB: Generating FQT events for %d rows", len(rows))

        for event in self._rows_to_fqt_events(rows, tags):
            self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
            fqt_event_count += 1

        if self._check._get_is_tidb(self._db):
            self.log.debug("TiDB: Generated %d FQT events (rate-limited from %d rows)", fqt_event_count, len(rows))
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
            'service': self._config.service,
            'mysql_rows': rows,
        }
        self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
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

        # Debug logging for TiDB
        if self._check._get_is_tidb(self._db):
            self.log.debug("TiDB: monotonic_rows count before compute_derivative_rows: %d", len(monotonic_rows))
            if monotonic_rows:
                self.log.debug("TiDB: sample row: %s", monotonic_rows[0])

        rows = self._state.compute_derivative_rows(monotonic_rows, METRICS_COLUMNS, key=_row_key)

        # Debug logging for TiDB
        if self._check._get_is_tidb(self._db):
            self.log.debug("TiDB: rows count after compute_derivative_rows: %d", len(rows))
            if rows:
                self.log.debug("TiDB: sample derivative row: %s", rows[0])

            # For TiDB, if no derivative rows are returned (e.g., first run),
            # use the monotonic rows directly to ensure FQT events are generated
            if not rows and monotonic_rows:
                self.log.debug("TiDB: Using monotonic rows for FQT events on first run")
                # Return monotonic rows with zeroed metric values to generate FQT events
                rows = []
                for row in monotonic_rows:
                    # Create a copy with all metric columns set to 0
                    fqt_row = dict(row)
                    for metric in METRICS_COLUMNS:
                        if metric in fqt_row:
                            fqt_row[metric] = 0
                    rows.append(fqt_row)

        return rows

    def _get_statement_count(self, tags):
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            # Check if this is TiDB
            if self._check._get_is_tidb(self._db):
                # TiDB uses cluster_statements_summary instead
                cursor.execute("SELECT count(*) AS count from information_schema.cluster_statements_summary")
            else:
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
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            # Check if this is TiDB
            if self._check._get_is_tidb(self._db):
                # Use TiDB-specific implementation
                if _is_tidb_statements_summary_available(cursor):
                    rows = _collect_tidb_statement_metrics_rows(
                        cursor, only_query_recent_statements=only_query_recent_statements, last_seen=self._last_seen
                    )
                else:
                    self.log.warning("TiDB statements_summary table not available")
                    return []
            else:
                # Use standard MySQL implementation
                condition = (
                    "WHERE `last_seen` >= %s"
                    if only_query_recent_statements
                    else """WHERE `digest_text` NOT LIKE 'EXPLAIN %' OR `digest_text` IS NULL
                    ORDER BY `count_star` DESC
                    LIMIT 10000"""
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
            if key not in self._statement_rows:
                self._statement_rows[key] = {}
            self._statement_rows[key][row['digest']] = row

        return [row for statement_row in self._statement_rows.values() for row in statement_row.values()]

    def _rows_to_fqt_events(self, rows, tags):
        # Ensure FQT cache is initialized before use
        self._ensure_fqt_cache_initialized()

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
