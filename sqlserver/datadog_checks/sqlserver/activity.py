import binascii
import re
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

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

ACTIVITY_QUERY = re.sub(
    r'\s+',
    ' ',
    """\
SELECT
    at.transaction_begin_time,
    at.transaction_type,
    at.transaction_state,
    sess.login_name as user_name,
    sess.session_id as id,
    DB_NAME(sess.database_id) as database_name,
    sess.status as session_status,
    text.text as text,
    c.client_tcp_port as client_port,
    c.client_net_address as client_address,
    sess.host_name as host_name,
    r.*
FROM sys.dm_tran_active_transactions at
    INNER JOIN sys.dm_tran_session_transactions st ON st.transaction_id = at.transaction_id
      LEFT OUTER JOIN sys.dm_exec_sessions sess ON st.session_id = sess.session_id
    LEFT OUTER JOIN sys.dm_exec_connections c
        ON sess.session_id = c.session_id
    LEFT OUTER JOIN sys.dm_exec_requests r
        ON c.connection_id = r.connection_id
        CROSS APPLY sys.dm_exec_sql_text(c.most_recent_sql_handle) text
    WHERE sess.session_id != @@spid
    ORDER BY at.transaction_begin_time ASC
""",
).strip()

dm_exec_requests_exclude_keys = {
    'sql_handle',
    'plan_handle',
    'statement_sql_handle',
    'task_address',
    'page_resource',
    'scheduler_id',
    'context_info',
    # remove status in favor of session_status
    'status',
    # remove session_id in favor of id
    'session_id',
}


def _hash_to_hex(hash):
    return to_native_string(binascii.hexlify(hash))


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
            config_host=check.resolved_hostname,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-activity",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-activity-"
        self._activity_payload_max_bytes = MAX_PAYLOAD_BYTES

    def _close_db_conn(self):
        pass

    def run_job(self):
        self.collect_activity()

    def _get_active_connections(self, cursor):
        self.log.debug("collecting sql server current connections")
        self.log.debug("Running query [%s]", CONNECTIONS_QUERY)
        cursor.execute(CONNECTIONS_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.log.debug("loaded sql server current connections len(rows)=%s", len(rows))
        return rows

    def _get_activity(self, cursor):
        self.log.debug("collecting sql server activity")
        self.log.debug("Running query [%s]", ACTIVITY_QUERY)
        cursor.execute(ACTIVITY_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows

    def _normalize_queries_and_filter_rows(self, rows, max_bytes_limit):
        normalized_rows = []
        estimated_size = 0
        for row in rows:
            try:
                obfuscated_statement = datadog_agent.obfuscate_sql(row['text'])
                row['query_signature'] = compute_sql_signature(obfuscated_statement)
            except Exception as e:
                # obfuscation errors are relatively common so only log them during debugging
                self.log.debug("Failed to obfuscate query: %s", e)
                obfuscated_statement = "ERROR: failed to obfuscate"
            row = self._sanitize_row(row, obfuscated_statement)
            estimated_size += self._get_estimated_row_size_bytes(row)
            if estimated_size > max_bytes_limit:
                # query results are ORDER BY transaction_begin_time ASC
                # so once we hit the max bytes limit, return
                return normalized_rows
            normalized_rows.append(row)
        return normalized_rows

    @staticmethod
    def _sanitize_row(row, obfuscated_statement):
        row = {key: val for key, val in row.items() if key not in dm_exec_requests_exclude_keys and val is not None}
        row['text'] = obfuscated_statement
        if 'query_hash' in row:
            row['query_hash'] = _hash_to_hex(row['query_hash'])
        if 'query_plan_hash' in row:
            row['query_plan_hash'] = _hash_to_hex(row['query_plan_hash'])
        return row

    @staticmethod
    def _get_estimated_row_size_bytes(row):
        return len(str(row))

    def _create_activity_event(self, active_sessions, active_connections):
        event = {
            "host": self._db_hostname,
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

    def _truncate_activity_rows(self, rows, max_bytes):
        pass

    def collect_activity(self):
        """
        Collects all current activity for the SQLServer intance.
        :return:
        """
        start_time = time.time()
        # re-use the check's conn module, but set extra_key=dbm-activity- to ensure we get our own
        # raw connection. adodbapi and pyodbc modules are thread safe, but connections are not.
        with self.check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self.check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                connections = self._get_active_connections(cursor)
                rows = self._get_activity(cursor)
                normalized_rows = self._normalize_queries_and_filter_rows(rows, MAX_PAYLOAD_BYTES)
                event = self._create_activity_event(normalized_rows, connections)
                payload = json.dumps(event, default=default_json_event_encoding)
                self._check.database_monitoring_query_activity(payload)

        elapsed_ms = (time.time() - start_time) * 1000
        self.check.histogram(
            "dd.sqlserver.activity.collect_activity.time",
            elapsed_ms,
            tags=self.check.debug_tags(),
            hostname=self.check.resolved_hostname,
            raw=True,
        )
        self.check.histogram(
            "dd.sqlserver.activity.collect_activity.payload_size",
            len(payload),
            tags=self.check.debug_tags(),
            hostname=self.check.resolved_hostname,
            raw=True,
        )
