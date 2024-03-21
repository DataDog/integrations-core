# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import binascii
import datetime
import re
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.config import SQLServerConfig
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.utils import extract_sql_comments_and_procedure_name

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
    SUBSTRING(qt.text, 1, {proc_char_limit}) as text,
    c.client_tcp_port as client_port,
    c.client_net_address as client_address,
    sess.host_name as host_name,
    sess.program_name as program_name,
    sess.is_user_process as is_user_process,
    {exec_request_columns}
FROM sys.dm_exec_sessions sess
    INNER JOIN sys.dm_exec_connections c
        ON sess.session_id = c.session_id
    INNER JOIN sys.dm_exec_requests req
        ON c.connection_id = req.connection_id
    CROSS APPLY sys.dm_exec_sql_text(req.sql_handle) qt
WHERE
    sess.session_id != @@spid AND
    sess.status != 'sleeping'
""",
).strip()

# Turns out sys.dm_exec_requests does not contain idle sessions.
# Inner joining dm_exec_sessions with dm_exec_requests will not return any idle blocking sessions.
# This prevent us reusing the same ACTIVITY_QUERY for regular activities and idle blocking sessions.
# The query below is used for idle sessions and does not join with dm_exec_requests.
# The last query execution on the connection is fetched from dm_exec_connections.most_recent_sql_handle.
IDLE_BLOCKING_SESSIONS_QUERY = re.sub(
    r'\s+',
    ' ',
    """\
SELECT
    CONVERT(
        NVARCHAR, TODATETIMEOFFSET(CURRENT_TIMESTAMP, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as now,
    sess.login_name as user_name,
    sess.last_request_start_time as last_request_start_time,
    sess.session_id as id,
    DB_NAME(sess.database_id) as database_name,
    sess.status as session_status,
    lqt.text as statement_text,
    SUBSTRING(lqt.text, 1, {proc_char_limit}) as text,
    c.client_tcp_port as client_port,
    c.client_net_address as client_address,
    sess.host_name as host_name,
    sess.program_name as program_name,
    sess.is_user_process as is_user_process
FROM sys.dm_exec_sessions sess
    INNER JOIN sys.dm_exec_connections c
        ON sess.session_id = c.session_id
    CROSS APPLY sys.dm_exec_sql_text(c.most_recent_sql_handle) lqt
WHERE sess.status = 'sleeping'
    AND sess.session_id IN ({blocking_session_ids})
    AND c.session_id IN ({blocking_session_ids})
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


def _hash_to_hex(hash) -> str:
    return binascii.hexlify(hash).decode("utf-8")


def agent_check_getter(self):
    return self._check


class SqlserverActivity(DBMAsyncJob):
    """Collects query metrics and plans"""

    def __init__(self, check, config: SQLServerConfig):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self.log = check.log
        self._config = config
        collection_interval = float(
            self._config.activity_config.get('collection_interval', DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverActivity, self).__init__(
            check,
            run_sync=is_affirmative(self._config.activity_config.get('run_sync', False)),
            enabled=is_affirmative(self._config.activity_config.get('enabled', True)),
            expected_db_exceptions=(),
            min_collection_interval=self._config.min_collection_interval,
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
    def _get_idle_blocking_sessions(self, cursor, blocking_session_ids):
        # The IDLE_BLOCKING_SESSIONS_QUERY contains minimum information on idle blocker
        query = IDLE_BLOCKING_SESSIONS_QUERY.format(
            blocking_session_ids=",".join(map(str, blocking_session_ids)),
            proc_char_limit=self._config.stored_procedure_characters_limit,
        )
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_activity(self, cursor, exec_request_columns):
        self.log.debug("collecting sql server activity")
        query = ACTIVITY_QUERY.format(
            exec_request_columns=', '.join(['req.{}'.format(r) for r in exec_request_columns]),
            proc_char_limit=self._config.stored_procedure_characters_limit,
        )
        self.log.debug("Running query [%s]", query)
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        # construct set of unique session ids
        session_ids = {r['id'] for r in rows}
        # construct set of blocking session ids
        blocking_session_ids = {r['blocking_session_id'] for r in rows if r['blocking_session_id']}
        # if there are blocking sessions and some of the session(s) are not captured in the activity query
        idle_blocking_session_ids = blocking_session_ids - session_ids
        if idle_blocking_session_ids:
            idle_blocking_sessions = self._get_idle_blocking_sessions(cursor, idle_blocking_session_ids)
            rows.extend(idle_blocking_sessions)
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
                self._check.histogram(
                    "dd.sqlserver.activity.collect_activity.max_bytes.rows_dropped",
                    len(normalized_rows) - len(rows),
                    **self._check.debug_stats_kwargs(),
                )
                self._check.warning(
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
            self._log.info("missing the following expected columns from sys.dm_exec_requests: %s", missing_columns)
        self._log.debug("found available sys.dm_exec_requests columns: %s", available_columns)
        return available_columns

    @staticmethod
    def _get_sort_key(r):
        return r.get("query_start") or datetime.datetime.now().isoformat()

    def _obfuscate_and_sanitize_row(self, row):
        row = self._remove_null_vals(row)
        if 'statement_text' not in row:
            return self._sanitize_row(row)
        try:
            statement = obfuscate_sql_with_metadata(
                row['statement_text'], self._config.obfuscator_options, replace_null_character=True
            )
            # sqlserver doesn't have a boolean data type so convert integer to boolean
            comments, row['is_proc'], procedure_name = extract_sql_comments_and_procedure_name(row['text'])
            if row['is_proc'] and 'text' in row:
                try:
                    procedure_statement = obfuscate_sql_with_metadata(
                        row['text'], self._config.obfuscator_options, replace_null_character=True
                    )
                    row['procedure_signature'] = compute_sql_signature(procedure_statement['query'])
                except Exception as e:
                    row['procedure_signature'] = '__procedure_obfuscation_error__'
                    # if we fail to obfuscate the procedure text,
                    # we should not mark query statement as failed to obfuscate
                    if self._config.log_unobfuscated_queries:
                        self.log.warning("Failed to obfuscate stored procedure=[%s] | err=[%s]", repr(row['text']), e)
                    else:
                        self.log.debug("Failed to obfuscate stored procedure | err=[%s]", e)
            obfuscated_statement = statement['query']
            metadata = statement['metadata']
            row['dd_commands'] = metadata.get('commands', None)
            row['dd_tables'] = metadata.get('tables', None)
            row['dd_comments'] = comments
            row['query_signature'] = compute_sql_signature(obfuscated_statement)
            if procedure_name:
                row['procedure_name'] = procedure_name
        except Exception as e:
            if self._config.log_unobfuscated_queries:
                self.log.warning("Failed to obfuscate query=[%s] | err=[%s]", repr(row['statement_text']), e)
            else:
                self.log.debug("Failed to obfuscate query | err=[%s]", e)
            obfuscated_statement = "ERROR: failed to obfuscate"
        row = self._sanitize_row(row, obfuscated_statement)
        return row

    @staticmethod
    def _remove_null_vals(row):
        return {key: val for key, val in row.items() if val is not None}

    @staticmethod
    def _sanitize_row(row, obfuscated_statement=None):
        # rename the statement_text field to 'text' because that
        # is what our backend is expecting
        if obfuscated_statement:
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
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time.time() * 1000,
            'sqlserver_version': self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            'sqlserver_engine_edition': self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
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
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                connections = self._get_active_connections(cursor)
                request_cols = self._get_exec_requests_cols_cached(cursor, DM_EXEC_REQUESTS_COLS)
                rows = self._get_activity(cursor, request_cols)
                normalized_rows = self._normalize_queries_and_filter_rows(rows, MAX_PAYLOAD_BYTES)
                event = self._create_activity_event(normalized_rows, connections)
                payload = json.dumps(event, default=default_json_event_encoding)
                self._check.database_monitoring_query_activity(payload)

        self._check.histogram(
            "dd.sqlserver.activity.collect_activity.payload_size", len(payload), **self._check.debug_stats_kwargs()
        )
