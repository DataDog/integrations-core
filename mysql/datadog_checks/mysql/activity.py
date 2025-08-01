# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import decimal
import time
from contextlib import closing
from enum import Enum
from typing import Dict, List  # noqa: F401

import pymysql

from datadog_checks.base import is_affirmative, to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mysql.cursor import CommenterDictCursor

from .util import DatabaseConfigurationError, connect_with_session_variables, get_truncation_state, warning_with_tags

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


ACTIVITY_QUERY = """\
SELECT
    thread_a.thread_id,
    thread_a.processlist_id,
    thread_a.processlist_user,
    thread_a.processlist_host,
    thread_a.processlist_db,
    thread_a.processlist_command,
    thread_a.processlist_state,
    COALESCE(statement.sql_text, thread_a.PROCESSLIST_info) AS sql_text,
    statement.digest_text as digest_text,
    statement.timer_start AS event_timer_start,
    statement.timer_end AS event_timer_end,
    statement.lock_time,
    statement.current_schema,
    waits_a.event_id AS event_id,
    waits_a.end_event_id,
    IF(waits_a.thread_id IS NULL,
        'other',
        COALESCE(
            IF(thread_a.processlist_state = 'User sleep', 'User sleep',
            IF(waits_a.event_id = waits_a.end_event_id, 'CPU', waits_a.event_name)), 'CPU'
        )
    ) AS wait_event,
    waits_a.operation,
    waits_a.timer_start AS wait_timer_start,
    waits_a.timer_end AS wait_timer_end,
    waits_a.object_schema,
    waits_a.object_name,
    waits_a.index_name,
    waits_a.object_type,
    waits_a.source
    {blocking_columns}
FROM
    performance_schema.threads AS thread_a
    LEFT JOIN performance_schema.events_waits_current AS waits_a ON waits_a.thread_id = thread_a.thread_id
    LEFT JOIN performance_schema.events_statements_current AS statement ON statement.thread_id = thread_a.thread_id
    {blocking_joins}
WHERE
    (
        thread_a.processlist_state IS NOT NULL
        AND thread_a.processlist_id != CONNECTION_ID()
        AND thread_a.PROCESSLIST_COMMAND != 'Daemon'
        AND thread_a.processlist_command != 'Sleep'
        AND (waits_a.EVENT_NAME != 'idle' OR waits_a.EVENT_NAME IS NULL)
        AND (waits_a.operation != 'idle' OR waits_a.operation IS NULL)
        -- events_waits_current can have multiple rows per thread, thus we use EVENT_ID to identify the row
        -- we want to use. Additionally, we want the row with the highest EVENT_ID which reflects the most recent wait.
        AND (
            waits_a.event_id = (
            SELECT
                MAX(waits_b.EVENT_ID)
            FROM  performance_schema.events_waits_current AS waits_b
            Where waits_b.thread_id = thread_a.thread_id
        ) OR waits_a.event_id is NULL)
        -- We ignore rows without SQL text because there will be rows for background operations that do not have
        -- SQL text associated with it.
        AND COALESCE(statement.sql_text, thread_a.PROCESSLIST_info) != ''
    )
    {idle_blockers_subquery};
"""

BLOCKING_COLUMNS_MYSQL8 = """\
    ,blocking_thread.thread_id AS blocking_thread_id,
    blocking_thread.processlist_id AS blocking_processlist_id
"""

BLOCKING_JOINS_MYSQL8 = """\
    LEFT JOIN performance_schema.data_lock_waits AS lock_waits ON thread_a.thread_id = lock_waits.requesting_thread_id
    LEFT JOIN performance_schema.threads AS blocking_thread ON lock_waits.blocking_thread_id = blocking_thread.thread_id
"""

IDLE_BLOCKERS_SUBQUERY_MYSQL8 = """\
        OR
        -- Include idle sessions that are blocking others
        thread_a.thread_id IN (
            SELECT blocking_thread_id
            FROM performance_schema.data_lock_waits
        )
"""

BLOCKING_COLUMNS_MYSQL7 = """\
    ,blocking_thread.thread_id AS blocking_thread_id,
    blocking_thread.processlist_id AS blocking_processlist_id
"""

BLOCKING_JOINS_MYSQL7 = """\
    LEFT JOIN information_schema.INNODB_TRX AS trx ON thread_a.processlist_id = trx.trx_mysql_thread_id
    LEFT JOIN information_schema.INNODB_LOCK_WAITS AS lock_waits ON trx.trx_id = lock_waits.requesting_trx_id
    LEFT JOIN information_schema.INNODB_TRX AS blocking_trx ON lock_waits.blocking_trx_id = blocking_trx.trx_id
    LEFT JOIN performance_schema.threads AS blocking_thread
        ON blocking_trx.trx_mysql_thread_id = blocking_thread.processlist_id
"""

IDLE_BLOCKERS_SUBQUERY_MYSQL7 = """\
        OR
        -- Include idle sessions that are blocking others
        thread_a.processlist_id IN (
            SELECT blocking_trx.trx_mysql_thread_id
            FROM information_schema.INNODB_LOCK_WAITS AS lock_waits
            JOIN information_schema.INNODB_TRX AS blocking_trx ON lock_waits.blocking_trx_id = blocking_trx.trx_id
        )
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
            expected_db_exceptions=(pymysql.err.OperationalError, pymysql.err.InternalError),
            min_collection_interval=config.min_collection_interval,
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
        self._activity_query = None

    def run_job(self):
        # type: () -> None
        # Detect a database misconfiguration by checking if `events-waits-current` is enabled.
        if self._check.events_wait_current_enabled is None:
            self._log.debug(
                'Waiting for events_waits_current availability to be determined by the check, skipping run.'
            )
        if self._check.events_wait_current_enabled is False:
            azure_deployment_type = self._config.cloud_metadata.get("azure", {}).get("deployment_type")
            if azure_deployment_type != "flexible_server":
                self._check.record_warning(
                    DatabaseConfigurationError.events_waits_current_not_enabled,
                    warning_with_tags(
                        'Query activity and wait event collection is disabled on this host. To enable it, the setup '
                        'consumer `performance-schema-consumer-events-waits-current` '
                        'must be enabled on the MySQL server. Please refer to the troubleshooting documentation: '
                        'https://docs.datadoghq.com/database_monitoring/setup_mysql/troubleshooting#%s',
                        DatabaseConfigurationError.events_waits_current_not_enabled.value,
                        code=DatabaseConfigurationError.events_waits_current_not_enabled.value,
                        host=self._check.reported_hostname,
                    ),
                )
            return
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
        # do not emit any dd.internal metrics for DBM specific check code
        tags = [t for t in self._tags if not t.startswith('dd.internal')]
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            rows = self._get_activity(cursor)
            rows = self._normalize_rows(rows)
            event = self._create_activity_event(rows, tags)
            payload = json.dumps(event, default=self._json_event_encoding)
            self._check.database_monitoring_query_activity(payload)
            self._check.histogram(
                "dd.mysql.activity.collect_activity.payload_size",
                len(payload),
                tags=tags + self._check._get_debug_tags(),
            )

    def _should_collect_blocking_queries(self):
        # type: () -> bool
        return self._config.activity_config.get("collect_blocking_queries", False)

    def _get_activity_query(self):
        # type: () -> str
        if self._activity_query:
            return self._activity_query
        blocking_columns = ""
        blocking_joins = ""
        idle_blockers_subquery = ""
        if self._should_collect_blocking_queries():
            if self._db_version == MySQLVersion.VERSION_80 and not self._check.is_mariadb:
                blocking_columns = BLOCKING_COLUMNS_MYSQL8
                blocking_joins = BLOCKING_JOINS_MYSQL8
                idle_blockers_subquery = IDLE_BLOCKERS_SUBQUERY_MYSQL8
            else:
                blocking_columns = BLOCKING_COLUMNS_MYSQL7
                blocking_joins = BLOCKING_JOINS_MYSQL7
                idle_blockers_subquery = IDLE_BLOCKERS_SUBQUERY_MYSQL7
        return ACTIVITY_QUERY.format(
            blocking_columns=blocking_columns,
            blocking_joins=blocking_joins,
            idle_blockers_subquery=idle_blockers_subquery,
        )

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_activity(self, cursor):
        # type: (pymysql.cursor) -> List[Dict[str]]
        query = self._get_activity_query()
        self._log.debug("Running activity query [%s]", query)
        cursor.execute(query)
        return cursor.fetchall()

    def _normalize_rows(self, rows):
        # type: (List[Dict[str]]) -> List[Dict[str]]
        rows = sorted(rows, key=lambda r: self._sort_key(r))
        normalized_rows = []
        seen = {}
        second_pass = {}
        estimated_size = 0
        for row in rows:
            if row["thread_id"] in seen:
                # `performance_schema.events_statements_current` can contain previous statements
                # for the same thread. We only want the most recent one.
                if row["event_timer_end"] < seen[row["thread_id"]]["event_timer_start"]:
                    continue
                else:
                    second_pass[row["thread_id"]] = {"event_timer_start": row["event_timer_start"]}
            else:
                seen[row["thread_id"]] = {"event_timer_start": row["event_timer_start"]}
            if row["sql_text"] is not None:
                row["query_truncated"] = get_truncation_state(row["sql_text"]).value
            row = self._obfuscate_and_sanitize_row(row)
            estimated_size += self._get_estimated_row_size_bytes(row)
            if estimated_size > MySQLActivity.MAX_PAYLOAD_BYTES:
                return normalized_rows
            normalized_rows.append(row)
        if second_pass:
            normalized_rows = self._eliminate_duplicate_rows(normalized_rows, second_pass)
        return normalized_rows

    @staticmethod
    def _eliminate_duplicate_rows(rows, second_pass):
        # type: (List[Dict[str]], Dict[str]) -> List[Dict[str]]
        filtered_rows = []
        for row in rows:
            if (
                row["thread_id"] in second_pass
                and row["event_timer_end"] < second_pass[row["thread_id"]]["event_timer_start"]
            ):
                continue
            filtered_rows.append(row)
        return filtered_rows

    @staticmethod
    def _sort_key(row):
        # type: (Dict[str]) -> int
        # value is in picoseconds
        return row.get('event_timer_start') or int(round(time.time() * 1e12))

    def _obfuscate_and_sanitize_row(self, row):
        # type: (Dict[str]) -> Dict[str]
        row = self._sanitize_row(row)
        if "sql_text" not in row:
            return row
        try:
            self._finalize_row(
                row,
                obfuscate_sql_with_metadata(row["sql_text"], self._obfuscator_options),
                obfuscate_sql_with_metadata(row.get("digest_text"), self._obfuscator_options),
            )
        except Exception as e:
            if self._config.log_unobfuscated_queries:
                self._log.warning("Failed to obfuscate query=[%s] | err=[%s]", row["sql_text"], e)
            else:
                self._log.debug("Failed to obfuscate query | err=[%s]", e)
            row["sql_text"] = "ERROR: failed to obfuscate"
        return row

    @staticmethod
    def _sanitize_row(row):
        # type: (Dict[str]) -> Dict[str]
        return {key: val for key, val in row.items() if val is not None}

    @staticmethod
    def _finalize_row(row, statement, digest_statement):
        # type: (Dict[str], Dict[str], Dict[str]) -> None
        row["sql_text"] = statement["query"]
        if digest_statement["query"]:
            # if digest_text is not NULL, use it to compute the query signature
            row["query_signature"] = compute_sql_signature(digest_statement["query"])
        else:
            # fallback to sql_text when digest_text is NULL
            # MySQL < 8.0 sometimes have NULL digest_text even when statements_digest consumer is enabled
            row["query_signature"] = compute_sql_signature(statement["query"])

        metadata = statement["metadata"]
        row["dd_commands"] = metadata.get("commands", None)
        row["dd_tables"] = metadata.get("tables", None)
        row["dd_comments"] = metadata.get("comments", None)

    @staticmethod
    def _get_estimated_row_size_bytes(row):
        # type: (Dict[str]) -> int
        return len(str(row))

    def _create_activity_event(self, active_sessions, tags):
        # type: (List[Dict[str]], List[Dict[str]]) -> Dict[str]
        return {
            "host": self._check.reported_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mysql",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": tags,
            "timestamp": time.time() * 1000,
            "cloud_metadata": self._config.cloud_metadata,
            'service': self._config.service,
            "mysql_activity": active_sessions,
        }

    @staticmethod
    def _json_event_encoding(o):
        # We have a similar event encoder in the base check, but to iterate quickly and support types unique to
        # MySQL, we create a custom one here.
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
            self._db = connect_with_session_variables(**self._connection_args)
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
