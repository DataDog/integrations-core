import datetime
import decimal
import time
from contextlib import closing
from enum import Enum
from typing import Dict, List

import pymysql

from datadog_checks.base import is_affirmative, to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, obfuscate_sql_with_metadata
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

ACTIVITY_QUERY = """\
SELECT
    stmt.TIMER_START AS stmt_timer_start,
    stmt.TIMER_END AS stmt_timer_end,
    stmt.LOCK_TIME,
    stmt.CURRENT_SCHEMA,
    thread.PROCESSLIST_INFO AS SQL_TEXT,
    IF (PROCESSLIST_STATE ='User sleep',' User sleep', (
      IF (waits_statement.EVENT_ID = waits_statement.END_EVENT_ID, 'CPU',
         COALESCE(waits_wait.EVENT_NAME, waits_statement.EVENT_NAME))
    )) AS wait_event,
    waits_statement.TIMER_START AS wait_timer_start,
    waits_statement.TIMER_END AS wait_timer_end,
    thread.thread_id,
    thread.PROCESSLIST_ID,
    thread.PROCESSLIST_USER,
    thread.PROCESSLIST_HOST,
    thread.PROCESSLIST_DB,
    thread.PROCESSLIST_COMMAND,
    thread.PROCESSLIST_STATE,
    socket.IP,
    socket.PORT
FROM
    performance_schema.threads AS thread
    LEFT JOIN performance_schema.events_statements_current AS stmt
        ON stmt.THREAD_ID = thread.THREAD_ID and stmt.NESTING_EVENT_LEVEL = 0
    -- MySQL can potentially have two wait events for a given thread, so we pull both out and favor the one with 'WAIT'
    LEFT JOIN performance_schema.events_waits_current AS waits_wait
        ON waits_wait.thread_id = thread.thread_id AND waits_wait.NESTING_EVENT_TYPE = 'WAIT'
    LEFT JOIN performance_schema.events_waits_current AS waits_statement
        ON waits_statement.thread_id = thread.thread_id AND waits_statement.NESTING_EVENT_TYPE = 'STATEMENT'
    LEFT JOIN performance_schema.socket_instances AS socket
        ON thread.THREAD_ID = socket.THREAD_ID
WHERE
    thread.PROCESSLIST_STATE IS NOT NULL
    AND thread.PROCESSLIST_COMMAND != 'Sleep'
    AND thread.PROCESSLIST_COMMAND != 'Daemon'
    AND thread.PROCESSLIST_ID != CONNECTION_ID()
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
        self._config = config
        self._log = check.log

        self._connection_args = connection_args
        self._db = None
        self._db_version = None
        self._obfuscator_options = to_native_string(json.dumps(self._config.obfuscator_options))

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
            payload = json.dumps(event, default=self._json_event_encoding)
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
        return row.get('event_timer_start') or int(round(time.time() * 1e12))

    def _obfuscate_and_sanitize_row(self, row):
        # type: (Dict[str]) -> Dict[str]
        row = self._sanitize_row(row)
        if 'SQL_TEXT' not in row:
            return row
        try:
            self._finalize_row(row, obfuscate_sql_with_metadata(row['SQL_TEXT'], self._obfuscator_options))
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
        if version == MySQLVersion.VERSION_80 or version == MySQLVersion.VERSION_57:
            return ACTIVITY_QUERY
        raise Exception('Active sessions is not supported for this version=[{}]'.format(version))

    @staticmethod
    def _json_event_encoding(o):
        # We have a similar event encoder in the base check, but to iterate quickly,
        # we create a custom one here that parses differently and handles types unique to MySQL rows.
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        if isinstance(o, datetime.timedelta):
            return int(o.total_seconds())
        raise TypeError

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
