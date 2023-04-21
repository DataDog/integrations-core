# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import binascii
import datetime
import re
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.utils import is_statement_proc

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 10
MAX_PAYLOAD_BYTES = 19e6

CONNECTIONS_QUERY = """\
SELECT
    login_name AS user_name,
    COUNT(session_id) AS connections,
    status,
    DB_NAME(database_id) AS database_name
FROM sys.dm_exec_sessions
    WHERE is_user_process = 1
    GROUP BY login_name, status, DB_NAME(database_id)
"""

# collects active session load on db
ACTIVITY_QUERY = re.sub(
    r'\s+',
    ' ',
    """\
SELECT
    CONVERT(
        NVARCHAR, TODATETIMEOFFSET(CURRENT_TIMESTAMP, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as now,
    CONVERT(
        NVARCHAR, TODATETIMEOFFSET(req.start_time, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as query_start,
    sess.login_name as user_name,
    sess.last_request_start_time as last_request_start_time,
    sess.session_id as id,
    DB_NAME(sess.database_id) as database_name,
    sess.status as session_status,
    req.status as request_status,
    SUBSTRING(qt.text, (req.statement_start_offset / 2) + 1,
    ((CASE req.statement_end_offset
        WHEN -1 THEN DATALENGTH(qt.text)
        ELSE req.statement_end_offset END
            - req.statement_start_offset) / 2) + 1) AS statement_text,
    qt.text,
    c.client_tcp_port as client_port,
    c.client_net_address as client_address,
    sess.host_name as host_name,
    sess.program_name as program_name,
    {exec_request_columns}
FROM sys.dm_exec_sessions sess
    INNER JOIN sys.dm_exec_connections c
        ON sess.session_id = c.session_id
    INNER JOIN sys.dm_exec_requests req
        ON c.connection_id = req.connection_id
    CROSS APPLY sys.dm_exec_sql_text(req.sql_handle) qt
WHERE sess.session_id != @@spid AND sess.status != 'sleeping'
""",
).strip()

# enumeration of the columns we collect
# from sys.dm_exec_requests
DM_EXEC_REQUESTS_COLS = [
    "command",
    "blocking_session_id",
    "wait_type",
    "wait_time",
    "last_wait_type",
    "wait_resource",
    "open_transaction_count",
    "transaction_id",
    "percent_complete",
    "estimated_completion_time",
    "cpu_time",
    "total_elapsed_time",
    "reads",
    "writes",
    "logical_reads",
    "transaction_isolation_level",
    "lock_timeout",
    "deadlock_priority",
    "row_count",
    "query_hash",
    "query_plan_hash",
]


def _hash_to_hex(hash):
    return to_native_string(binascii.hexlify(hash))


def agent_check_getter(self):
    return self.check


class SqlserverActivity(DBMAsyncJob):
    """Collects query metrics and plans"""

    def __init__(self, check):
        self.check = check
        self.log = check.log
        collection_interval = float(check.activity_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL))
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverActivity, self).__init__(
            check,
            run_sync=is_affirmative(check.activity_config.get('run_sync', False)),
            enabled=is_affirmative(check.activity_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=check.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-activity",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-activity-"
        self._activity_payload_max_bytes = MAX_PAYLOAD_BYTES
        self._exec_requests_cols_cached = None

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.collect_activity()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_active_connections(self, cursor):
        self.log.debug("collecting sql server current connections")
        self.log.debug("Running query [%s]", CONNECTIONS_QUERY)
        cursor.execute(CONNECTIONS_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server current connections len(rows)=%s", len(rows))
        return rows

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_activity(self, cursor, exec_request_columns):
        self.log.debug("collecting sql server activity")
        query = ACTIVITY_QUERY.format(
            exec_request_columns=', '.join(['req.{}'.format(r) for r in exec_request_columns])
        )
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows

    def _normalize_queries_and_filter_rows(self, rows, max_bytes_limit):
        normalized_rows = []
        estimated_size = 0
        rows = sorted(rows, key=lambda r: self._get_sort_key(r))
        for row in rows:
            row = self._obfuscate_and_sanitize_row(row)
            estimated_size += self._get_estimated_row_size_bytes(row)
            if estimated_size > max_bytes_limit:
                # query results are pre-sorted
                # so once we hit the max bytes limit, return
                self.check.histogram(
                    "dd.sqlserver.activity.collect_activity.max_bytes.rows_dropped",
                    len(normalized_rows) - len(rows),
                    **self.check.debug_stats_kwargs()
                )
                self.check.warning(
                    "Exceeded the limit of activity rows captured (%s of %s rows included). "
                    "Database load may be under-reported as a result.",
                    len(normalized_rows),
                    len(rows),
                )
                return normalized_rows
            normalized_rows.append(row)
        return normalized_rows

    def _get_exec_requests_cols_cached(self, cursor, expected_cols):
        if self._exec_requests_cols_cached:
            return self._exec_requests_cols_cached

        self._exec_requests_cols_cached = self._get_available_requests_columns(cursor, expected_cols)
        return self._exec_requests_cols_cached

    def _get_available_requests_columns(self, cursor, all_expected_columns):
        cursor.execute("select TOP 0 * from sys.dm_exec_requests")
        all_columns = {i[0] for i in cursor.description}
        available_columns = [c for c in all_expected_columns if c in all_columns]
        missing_columns = set(all_expected_columns) - set(available_columns)
        if missing_columns:
            self._log.debug("missing the following expected columns from sys.dm_exec_requests: %s", missing_columns)
        self._log.debug("found available sys.dm_exec_requests columns: %s", available_columns)
        return available_columns

    @staticmethod
    def _get_sort_key(r):
        return r.get("query_start") or datetime.datetime.now()

    def _obfuscate_and_sanitize_row(self, row):
        row = self._remove_null_vals(row)
        if 'statement_text' not in row:
            return row
        try:
            statement = obfuscate_sql_with_metadata(row['statement_text'], self.check.obfuscator_options)
            procedure_statement = None
            # sqlserver doesn't have a boolean data type so convert integer to boolean
            row['is_proc'], procedure_name = is_statement_proc(row['text'])
            if row['is_proc'] and 'text' in row:
                procedure_statement = obfuscate_sql_with_metadata(row['text'], self.check.obfuscator_options)
            obfuscated_statement = statement['query']
            metadata = statement['metadata']
            row['dd_commands'] = metadata.get('commands', None)
            row['dd_tables'] = metadata.get('tables', None)
            row['dd_comments'] = metadata.get('comments', None)
            row['query_signature'] = compute_sql_signature(obfuscated_statement)
            # procedure_signature is used to link this activity event with
            # its related plan events
            if procedure_statement:
                row['procedure_signature'] = compute_sql_signature(procedure_statement['query'])
            if procedure_name:
                row['procedure_name'] = procedure_name
        except Exception as e:
            if self.check.log_unobfuscated_queries:
                raw_query_text = row['text'] if row.get('is_proc', False) else row['statement_text']
                self.log.warning("Failed to obfuscate query=[%s] | err=[%s]", raw_query_text, e)
            else:
                self.log.debug("Failed to obfuscate query | err=[%s]", e)
            obfuscated_statement = "ERROR: failed to obfuscate"
        row = self._sanitize_row(row, obfuscated_statement)
        return row

    @staticmethod
    def _remove_null_vals(row):
        return {key: val for key, val in row.items() if val is not None}

    @staticmethod
    def _sanitize_row(row, obfuscated_statement):
        # rename the statement_text field to 'text' because that
        # is what our backend is expecting
        row['text'] = obfuscated_statement
        if 'query_hash' in row:
            row['query_hash'] = _hash_to_hex(row['query_hash'])
        if 'query_plan_hash' in row:
            row['query_plan_hash'] = _hash_to_hex(row['query_plan_hash'])
        # remove deobfuscated sql text from event
        if 'statement_text' in row:
            del row['statement_text']
        return row

    @staticmethod
    def _get_estimated_row_size_bytes(row):
        return len(str(row))

    def _create_activity_event(self, active_sessions, active_connections):
        event = {
            "host": self.check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": self.check.tags,
            "timestamp": time.time() * 1000,
            "sqlserver_activity": active_sessions,
            "sqlserver_connections": active_connections,
        }
        return event

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_activity(self):
        """
        Collects all current activity for the SQLServer intance.
        :return:
        """

        # re-use the check's conn module, but set extra_key=dbm-activity- to ensure we get our own
        # raw connection. adodbapi and pyodbc modules are thread safe, but connections are not.
        with self.check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self.check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                connections = self._get_active_connections(cursor)
                request_cols = self._get_exec_requests_cols_cached(cursor, DM_EXEC_REQUESTS_COLS)
                rows = self._get_activity(cursor, request_cols)
                normalized_rows = self._normalize_queries_and_filter_rows(rows, MAX_PAYLOAD_BYTES)
                event = self._create_activity_event(normalized_rows, connections)
                payload = json.dumps(event, default=default_json_event_encoding)
                self._check.database_monitoring_query_activity(payload)

        self.check.histogram(
            "dd.sqlserver.activity.collect_activity.payload_size", len(payload), **self.check.debug_stats_kwargs()
        )
