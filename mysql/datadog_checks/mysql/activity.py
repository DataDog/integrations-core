import time
from contextlib import closing
from enum import Enum
from typing import Dict, List

import pymysql

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

CONNECTIONS_QUERY = """\
SELECT
    PROCESSLIST_USER,
    PROCESSLIST_HOST,
    PROCESSLIST_DB,
    PROCESSLIST_STATE,
    COUNT(PROCESSLIST_USER) AS connections
FROM
    performance_schema.threads
WHERE
    PROCESSLIST_USER IS NOT NULL AND
    PROCESSLIST_STATE IS NOT NULL
    GROUP BY PROCESSLIST_USER, PROCESSLIST_HOST, PROCESSLIST_DB, PROCESSLIST_STATE
"""

SYS_INNODB_LOCK_WAITS_57_COLUMNS = frozenset({'lock_waits.locked_table'})
SYS_INNODB_LOCK_WAITS_80_COLUMNS = frozenset({'lock_waits.locked_table_name', 'lock_waits.locked_table_schema'})

ACTIVITY_QUERY_57_AND_80 = """\
SELECT
    current_events.TIMER_START AS event_timer_start,
    current_events.TIMER_END AS event_timer_end,
    current_events.LOCK_TIME,
    current_events.SQL_TEXT,
    current_events.CURRENT_SCHEMA,
    current_waits.EVENT_NAME AS wait_event,
    current_waits.TIMER_START AS wait_timer_start,
    current_waits.TIMER_END AS wait_timer_end,
    threads.PROCESSLIST_ID,
    threads.PROCESSLIST_USER,
    threads.PROCESSLIST_HOST,
    threads.PROCESSLIST_DB,
    threads.PROCESSLIST_COMMAND,
    threads.PROCESSLIST_STATE,
    socket_instances.IP,
    socket_instances.PORT,
    lock_waits.wait_started,
    lock_waits.wait_age,
    lock_waits.locked_index,
    lock_waits.locked_type,
    lock_waits.blocking_pid,
    lock_waits.blocking_trx_age,
    lock_waits.blocking_trx_rows_locked,
    lock_waits.blocking_trx_rows_modified,
    {lock_wait_columns},
    innodb_trx.trx_started,
    innodb_trx.trx_isolation_level,
    innodb_trx.trx_operation_state
FROM
    performance_schema.events_statements_current AS current_events
    JOIN performance_schema.events_waits_current AS current_waits ON current_events.THREAD_ID = current_waits.THREAD_ID
    JOIN performance_schema.threads AS threads ON current_waits.THREAD_ID = threads.THREAD_ID
    JOIN performance_schema.socket_instances AS socket_instances ON current_waits.THREAD_ID = socket_instances.THREAD_ID
    LEFT JOIN sys.innodb_lock_waits AS lock_waits ON threads.PROCESSLIST_ID = lock_waits.waiting_pid
    LEFT JOIN INFORMATION_SCHEMA.INNODB_TRX AS innodb_trx ON threads.PROCESSLIST_ID = innodb_trx.trx_mysql_thread_id
    WHERE threads.PROCESSLIST_ID != CONNECTION_ID() AND threads.PROCESSLIST_STATE IS NOT NULL
"""


class MySQLVersion(Enum):
    # 8.0
    VERSION_80 = 80
    # 5.7
    VERSION_57 = 57
    # 5.6
    VERSION_56 = 56


def agent_check_getter(self):
    return self._check


class MySQLActivity(DBMAsyncJob):

    DEFAULT_COLLECTION_INTERVAL = 10
    MAX_PAYLOAD_BYTES = 19e6

    def __init__(self, check, config, connection_args):
        self.collection_interval = float(
            config.activity_config.get("collection_interval", MySQLActivity.DEFAULT_COLLECTION_INTERVAL)
        )
        if self.collection_interval <= 0:
            self.collection_interval = MySQLActivity.DEFAULT_COLLECTION_INTERVAL
        super(MySQLActivity, self).__init__(
            check,
            run_sync=is_affirmative(config.activity_config.get("run_sync", False)),
            enabled=is_affirmative(config.activity_config.get("enabled", True)),
            expected_db_exceptions=(),
            min_collection_interval=config.min_collection_interval,
            config_host=config.host,
            dbms="mysql",
            rate_limit=1 / float(self.collection_interval),
            job_name="query-activity",
            shutdown_callback=self._close_db_conn,
        )
        self._check = check
        self._log = check.log

        self._connection_args = connection_args
        self._db = None
        self._db_version = None

    def run_job(self):
        # type: () -> None
        self._check_version()
        self._collect_activity()

    def _check_version(self):
        # type: () -> None
        if self._check.version.version_compatible((8,)):
            self._db_version = MySQLVersion.VERSION_80
        elif self._check.version.version_compatible((5, 7)):
            self._db_version = MySQLVersion.VERSION_57
        elif self._check.version.version_compatible((5, 6)):
            self._db_version = MySQLVersion.VERSION_56

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_activity(self):
        # type: () -> None
        with closing(self._get_db_connection().cursor(pymysql.cursors.DictCursor)) as cursor:
            connections = self._get_active_connections(cursor)
            rows = self._get_activity(cursor)
            if not rows:
                return
            rows = self._normalize_rows(rows)
            event = self._create_activity_event(rows, connections)
            payload = json.dumps(event, default=default_json_event_encoding)
            self._check.database_monitoring_query_activity(payload)
        self._check.histogram(
            "dd.mysql.activity.collect_activity.payload_size",
            len(payload),
            tags=self._tags + self._check._get_debug_tags(),
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_active_connections(self, cursor):
        # type: (pymysql.cursor) -> List[Dict[str]]
        self._log.debug("Running query [%s]", CONNECTIONS_QUERY)
        cursor.execute(CONNECTIONS_QUERY)
        rows = cursor.fetchall()
        self._log.debug("Loaded [%s] current connections", len(rows))
        return rows

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_activity(self, cursor):
        # type: (pymysql.cursor) -> List[Dict[str]]
        query = self._get_query_from_version(self._db_version)
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
            self._log.error('Failed to collect activity, this is likely due to a setup error | err=[%s]', e)
        except Exception as e:
            self._log.error('Failed to collect activity | err=[%s]', e)
        return []

    def _normalize_rows(self, rows):
        # type: (List[Dict[str]]) -> List[Dict[str]]
        rows = sorted(rows, key=lambda r: self._sort_key(r))
        normalized_rows = []
        estimated_size = 0
        for row in rows:
            row = self._obfuscate_and_sanitize_row(row)
            estimated_size += self._get_estimated_row_size_bytes(row)
            if estimated_size > MySQLActivity.MAX_PAYLOAD_BYTES:
                return normalized_rows
            normalized_rows.append(row)
        return normalized_rows

    @staticmethod
    def _sort_key(row):
        # type: (Dict[str]) -> int
        # If an event is produced from an instrument that has TIMED = NO, timing information is not collected,
        # and TIMER_START, TIMER_END, and TIMER_WAIT are all NULL. Time is in picoseconds.
        return row.get('TIMER_START') or int(round(time.time() * 1e12))

    def _obfuscate_and_sanitize_row(self, row):
        # type: (Dict[str]) -> Dict[str]
        row = self._sanitize_row(row)
        if 'SQL_TEXT' not in row:
            return row
        try:
            self._finalize_row(row, obfuscate_sql_with_metadata(row['SQL_TEXT'], self._check.obfuscator_options))
        except Exception as e:
            row['SQL_TEXT'] = 'ERROR: failed to obfuscate'
            self._log.debug("Failed to obfuscate | err=[%s]", e)
        return row

    @staticmethod
    def _sanitize_row(row):
        # type: (Dict[str]) -> Dict[str]
        return {key: val for key, val in row.items() if val is not None}

    @staticmethod
    def _finalize_row(row, statement):
        # type: (Dict[str], Dict[str]) -> None
        obfuscated_statement = statement['query']
        row['SQL_TEXT'] = obfuscated_statement
        row['query_signature'] = compute_sql_signature(obfuscated_statement)

        metadata = statement['metadata']
        row['dd_commands'] = metadata.get('commands', None)
        row['dd_tables'] = metadata.get('tables', None)
        row['dd_comments'] = metadata.get('comments', None)

    @staticmethod
    def _get_estimated_row_size_bytes(row):
        # type: (Dict[str]) -> int
        return len(str(row))

    def _create_activity_event(self, active_sessions, active_connections):
        # type: (List[Dict[str]], List[Dict[str]]) -> Dict[str]
        return {
            "host": self._db_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mysql",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": self._tags,
            "timestamp": time.time() * 1000,
            "mysql_activity": active_sessions,
            "mysql_connections": active_connections,
        }

    @staticmethod
    def _get_query_from_version(version):
        # type: (MySQLVersion) -> str
        if version == MySQLVersion.VERSION_80:
            return ACTIVITY_QUERY_57_AND_80.format(lock_wait_columns=', '.join(SYS_INNODB_LOCK_WAITS_80_COLUMNS))
        elif version == MySQLVersion.VERSION_57:
            return ACTIVITY_QUERY_57_AND_80.format(lock_wait_columns=', '.join(SYS_INNODB_LOCK_WAITS_57_COLUMNS))

    def _get_db_connection(self):
        """
        pymysql connections are not thread safe, so we can't reuse the same connection from the main check.
        """
        if not self._db:
            self._db = pymysql.connect(**self._connection_args)
        return self._db

    def _close_db_conn(self):
        # type: () -> None
        if self._db:
            try:
                self._db.close()
            except Exception as e:
                self._log.debug("Failed to close db connection | err=[%s]", e)
            finally:
                self._db = None
