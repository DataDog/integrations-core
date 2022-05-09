import re

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method

# try:
#     import datadog_agent
# except ImportError:
#     from ..stubs import datadog_agent


AG_QUERY = re.sub(
    r"\s+",
    " ",
    """\
SELECT
    AG.group_id AS availability_group_id,
    AG.name AS availability_group,
    AG.failure_condition_level,
    AG.automated_backup_preference,
    AG.required_synchronized_secondaries_to_commit,
    AR.replica_server_name,
    AR.availability_mode,
    AR.failover_mode,
    AR.session_timeout,
    AR.primary_role_allow_connections,
    AR.secondary_role_allow_connections,
    AR.create_date AS replica_create_date,
    AR.modify_date AS replica_modified_date,
    ADC.database_name,
    DRS.database_id,
    DRS.is_primary_replica,
    DRS.synchronization_state,
    DRS.database_state,
    DRS.is_suspended,
    DRS.suspend_reason,
    DRS.recovery_lsn,
    DRS.truncation_lsn,
    DRS.last_received_time,
    DRS.last_hardened_time
FROM
    sys.availability_groups AS AG
    JOIN sys.availability_replicas AS AR ON AG.group_id = AR.group_id
    JOIN sys.availability_databases_cluster AS ADC ON AG.group_id = ADC.group_id
    JOIN sys.dm_hadr_database_replica_states AS DRS ON AG.group_id = DRS.group_id
        AND ADC.group_database_id = DRS.group_database_id
        AND AR.replica_id = DRS.replica_id
    -- We prioritize these rows because it indicates where data loss could potentially be the greatest
    -- in the event of a failover.
    ORDER BY DRS.log_send_queue_size + DRS.redo_queue_size DESC
""",
).strip()


def agent_check_getter(self):
    return self.check


class SqlserverAlwaysOn(DBMAsyncJob):

    DEFAULT_COLLECTION_INTERVAL = 10
    MAX_PAYLOAD_BYTES = 19e6

    def __init__(self, check):
        self.check = check
        self.log = check.log
        collection_interval = float(
            check.alwayson_config.get("collection_interval", SqlserverAlwaysOn.DEFAULT_COLLECTION_INTERVAL)
        )
        if collection_interval <= 0:
            collection_interval = SqlserverAlwaysOn.DEFAULT_COLLECTION_INTERVAL
        self.collection_interval = collection_interval
        super(SqlserverAlwaysOn, self).__init__(
            check,
            run_sync=is_affirmative(check.alwayson_config.get("run_sync", False)),
            enabled=is_affirmative(check.alwayson_config.get("enabled", True)),
            expected_db_exceptions=(),
            min_collection_interval=check.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(collection_interval),
            job_name="query-alwayson",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = "dbm-alwayson-"
        self._alwayson_payload_max_bytes = SqlserverAlwaysOn.MAX_PAYLOAD_BYTES
        self._exec_requests_cols_cached = None

    def _close_db_conn(self):
        pass

    def run_job(self):
        self._collect_alwayson()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_alwayson(self):
        # re-use the check's conn module, but set extra_key=dbm-alwayson- to ensure we get our own
        # raw connection. adodbapi and pyodbc modules are thread safe, but connections are not.
        with self.check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self.check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                self._get_availability_groups(cursor)
                # TODO...

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_availability_groups(self, cursor):
        self.log.debug("Collecting SQL Server availability groups query=[%s]", AG_QUERY)
        cursor.execute(AG_QUERY)
        rows = self._construct_row_dicts(cursor)
        self.log.debug("Loaded SQL Server availability groups len(rows)=[%s]", len(rows))
        return rows

    @staticmethod
    def _construct_row_dicts(cursor):
        columns = [i[0] for i in cursor.description]
        # construct row dicts manually as there's no DictCursor for pyodbc
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
