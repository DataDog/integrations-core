import binascii
import re
import time

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 10
DEFAULT_TX_COLLECTION_INTERVAL = 60
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
        NVARCHAR, TODATETIMEOFFSET(r.start_time, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as query_start,
    sess.login_name as user_name,
    sess.last_request_start_time,
    sess.session_id as id,
    DB_NAME(sess.database_id) as database_name,
    sess.status as session_status,
    text.text as text,
    c.client_tcp_port as client_port,
    c.client_net_address as client_address,
    sess.host_name as host_name,
    r.*
FROM sys.dm_exec_sessions sess
    INNER JOIN sys.dm_exec_connections c
        ON sess.session_id = c.session_id
    INNER JOIN sys.dm_exec_requests r
        ON c.connection_id = r.connection_id
    OUTER APPLY sys.dm_exec_sql_text(c.most_recent_sql_handle) text
WHERE sess.session_id != @@spid
ORDER BY r.start_time ASC
""",
).strip()

# collects activity about open transactions
TX_ACTIVITY_QUERY = re.sub(
    r'\s+',
    ' ',
    """\
SELECT 
    CONVERT(
        NVARCHAR, TODATETIMEOFFSET(CURRENT_TIMESTAMP, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as now,
    CONVERT(
        NVARCHAR, TODATETIMEOFFSET(tat.transaction_begin_time, DATEPART(TZOFFSET, SYSDATETIMEOFFSET())), 126
    ) as transaction_begin_time,
    tst.session_id as id,
    es.original_login_name as user_name,
    es.last_request_start_time,
    DB_NAME(tdt.database_id) as database_name,
    tdt.database_transaction_log_record_count as space_used,
    tat.transaction_state,
    CASE
        WHEN  es.status  = 'sleeping' THEN TXT.text
    END as text,
    es.host_name,
    CASE tat.transaction_type
        WHEN 1 THEN 'Read/Write Transaction'
        WHEN 2 THEN 'Read-Only Transaction'
        WHEN 3 THEN 'System Transaction'
                WHEN 4 THEN 'Distributed Transaction'
                ELSE 'Unknown'
    END as transaction_type 
FROM sys.dm_tran_session_transactions as tst
       INNER JOIN sys.dm_tran_active_transactions as tat
              ON tst.transaction_id = tat.transaction_id
       INNER JOIN sys.dm_tran_database_transactions as tdt
              ON tst.transaction_id = tdt.transaction_id
       INNER JOIN sys.dm_exec_sessions es
              ON tst.session_id = es.session_id
         INNER JOIN sys.dm_exec_connections ec 
               ON tst.session_id = ec.session_id
       CROSS APPLY sys.dm_exec_sql_text(ec.most_recent_sql_handle) TXT
ORDER BY transaction_begin_time ASC
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
    # remove start_time in favor of query_start
    'start_time',
}


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
        # tx collection interval should not be shorter than the main activity col interval
        tx_collection_interval = max(
            self._config.activity_config.get('tx_collection_interval', DEFAULT_TX_COLLECTION_INTERVAL),
            collection_interval,
        )
        if collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL
        if tx_collection_interval <= 0:
            tx_collection_interval = DEFAULT_TX_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        self.tx_collection_interval = tx_collection_interval
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
        # keep track of last time we sent an tx_activity event
        self._time_since_last_tx_activity_event = 0

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
    def _get_activity(self, cursor):
        self.log.debug("collecting sql server activity")
        self.log.debug("Running query [%s]", ACTIVITY_QUERY)
        cursor.execute(ACTIVITY_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_tx_activity(self, cursor):
        # self._time_since_last_tx_activity_event = time.time()
        self.log.debug("collecting sql server transaction activity")
        self.log.debug("Running query [%s]", TX_ACTIVITY_QUERY)
        cursor.execute(TX_ACTIVITY_QUERY)
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.check.histogram(
            "dd.sqlserver.activity.get_tx_activity.tx_rows", len(rows), **self.check.debug_stats_kwargs()
        )
        return rows

    def _normalize_queries_and_filter_rows(self, rows, max_bytes_limit):
        normalized_rows = []
        estimated_size = 0
        for row in rows:
            row = self._obfuscate_and_sanitize_row(row)
            estimated_size += self._get_estimated_row_size_bytes(row)
            if estimated_size > max_bytes_limit:
                # query results are ORDER BY query_start ASC
                # so once we hit the max bytes limit, return
                return normalized_rows
            normalized_rows.append(row)
        return normalized_rows

    def _normalize_tx_queries(self, rows):
        normalized_rows = []
        for row in rows:
            row = self._obfuscate_and_sanitize_row(row)
            normalized_rows.append(row)
        return normalized_rows

    def _obfuscate_and_sanitize_row(self, row):
        if not row['text']:
            return row
        try:
            obfuscated_statement = obfuscate_sql_with_metadata(row['text'], self.check.obfuscator_options)['query']
            row['query_signature'] = compute_sql_signature(obfuscated_statement)
        except Exception as e:
            # obfuscation errors are relatively common so only log them during debugging
            self.log.debug("Failed to obfuscate query: %s", e)
            obfuscated_statement = "ERROR: failed to obfuscate"
        row = self._sanitize_row(row, obfuscated_statement)
        return row

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

    def _create_activity_event(self, active_sessions, active_transactions, active_connections):
        event = {
            "host": self._db_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": self.check.tags,
            "timestamp": time.time() * 1000,
            "sqlserver_activity": active_sessions,
            "sqlserver_tx_activity": active_transactions,
            "sqlserver_connections": active_connections,
        }
        return event

    def _report_tx_activity_event(self):
        # Only send an event if we are configured to do so, and
        # don't report more often than the configured collection interval
        elapsed_s = time.time() - self._time_since_last_tx_activity_event
        if elapsed_s >= self.tx_collection_interval:
            return True
        return False

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
                rows = self._get_activity(cursor)
                normalized_rows = self._normalize_queries_and_filter_rows(rows, MAX_PAYLOAD_BYTES)
                if self._report_tx_activity_event():
                    tx_rows = self._get_tx_activity(cursor)
                    tx_rows = self._normalize_tx_queries(tx_rows)
                event = self._create_activity_event(normalized_rows, tx_rows, connections)
                payload = json.dumps(event, default=default_json_event_encoding)
                if self._report_tx_activity_event():
                    self.log.warning(payload)
                self._check.database_monitoring_query_activity(payload)

        self.check.histogram(
            "dd.sqlserver.activity.collect_activity.payload_size", len(payload), **self.check.debug_stats_kwargs()
        )
