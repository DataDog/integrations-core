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
    AG.name AS availability_group,
    AG.failure_condition_level,
    AG.health_check_timeout,
    AG.automated_backup_preference_desc,
    AG.required_synchronized_secondaries_to_commit,
    AR.replica_server_name,
    AR.availability_mode_desc,
    AR.failover_mode_desc,
    AR.session_timeout,
    AR.primary_role_allow_connections_desc,
    AR.secondary_role_allow_connections_desc,
    AR.create_date AS replica_create_date,
    AR.modify_date AS replica_modified_date,
    ADC.database_name,
    DRS.database_id,
    DRS.is_primary_replica,
    DRS.synchronization_state_desc,
    DRS.database_state_desc,
    DRS.is_suspended,
    DRS.suspend_reason,
    DRS.recovery_lsn,
    DRS.truncation_lsn,
    DRS.last_received_time,
    DRS.last_hardened_time,
    DRS.log_send_queue_size,
    DRS.log_send_rate,
    DRS.redo_queue_size,
    DRS.redo_rate,
    DRS.filestream_send_rate,
    DRS.low_water_mark_for_ghosts,
    DRS.secondary_lag_seconds
FROM
    sys.availability_groups AS AG
    JOIN sys.availability_replicas AS AR ON AG.group_id = AR.group_id
    JOIN sys.availability_databases_cluster AS ADC ON AG.group_id = ADC.group_id
    JOIN sys.dm_hadr_database_replica_states AS DRS ON AG.group_id = DRS.group_id
        AND ADC.group_database_id = DRS.group_database_id
        AND AR.replica_id = DRS.replica_id
    -- We prioritize these queues because it indicates where data loss could potentially be the greatest
    -- in the event of a failover.
    -- TODO: Maybe make this configurable?
    ORDER BY DRS.log_send_queue_size + DRS.redo_queue_size DESC
""",
).strip()

AG_COLUMNS_TO_METRICS = frozenset(
    {
        "log_send_queue_size",
        "log_send_rate",
        "redo_queue_size",
        "redo_rate",
        "filestream_send_rate",
        "secondary_lag_seconds",
        "required_synchronized_secondaries_to_commit",
        "failure_condition_level",
        "session_timeout",
        "low_water_mark_for_ghosts",
    }
)

FC_QUERY = re.sub(
    r"\s+",
    " ",
    """\
SELECT
    cluster_name,
    quorum_type,
    quorum_type_desc,
    quorum_state,
    quorum_state_desc
FROM sys.dm_hadr_cluster
""",
).strip()

FC_NODES_QUERY = re.sub(
    r"\s+",
    " ",
    """\
SELECT
    NodeName AS node_name,
    status,
    status_description,
    is_current_owner
FROM sys.dm_os_cluster_nodes
""",
).strip()

FC_MEMBERS_QUERY = re.sub(
    r"\s+",
    " ",
    """\
SELECT
    member_name,
    member_type,
    member_type_desc,
    member_state,
    member_state_desc,
    number_of_quorum_votes
FROM sys.dm_hadr_cluster_members
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

        # TODO: Go back and check existing metrics to ensure we don't duplicate metrics
        self._ao_metric_prefix = "sqlserver.ao"
        self._fc_metric_prefix = "sqlserver.fc"
        self._fc_node_metric_prefix = "sqlserver.fc.node"
        self._fc_member_metric_prefix = "sqlserver.fc.member"
        self._fci_metric_prefix = "sqlserver.fci"

        self._cluster_name = None

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
                fc_row = self._get_failover_cluster(cursor)
                fc_node_rows = self._get_failover_cluster_nodes(cursor)
                fc_member_rows = self._get_failover_cluster_members(cursor)
                self._emit_failover_cluster_metrics(fc_row, fc_node_rows, fc_member_rows)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_failover_cluster(self, cursor):
        self.log.debug("Collecting SQL Server Failover Cluster query=[%s]", FC_QUERY)
        cursor.execute(FC_QUERY)
        row = self._construct_row_dicts(cursor)
        if row:
            cluster_name = row[0]['cluster_name']  # Can be an empty string, not null
            self._cluster_name = cluster_name if cluster_name else None
        self.log.debug("Loaded SQL Server Failover Cluster len(rows)=[%s]", len(row))
        return row

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_failover_cluster_nodes(self, cursor):
        self.log.debug("Collecting SQL Server Failover Cluster nodes query=[%s]", FC_NODES_QUERY)
        cursor.execute(FC_NODES_QUERY)
        rows = self._construct_row_dicts(cursor)
        self.log.debug("Loaded SQL Server Failover Cluster nodes len(rows)=[%s]", len(rows))
        return rows

    @tracked_method(agent_check_getter=agent_check_getter)
    def _get_failover_cluster_members(self, cursor):
        self.log.debug("Collecting SQL Server Failover Cluster members query=[%s]", FC_MEMBERS_QUERY)
        cursor.execute(FC_MEMBERS_QUERY)
        rows = self._construct_row_dicts(cursor)
        self.log.debug("Loaded SQL Server Failover Cluster members len(rows)=[%s]", len(rows))
        return rows

    def _emit_failover_cluster_metrics(self, fc_row, fc_node_rows, fc_member_rows):
        cluster_name_tag = ["cluster_name:{}".format(self._cluster_name)]
        for row in fc_row:
            self.check.gauge(
                "{}.quorum_type".format(self._fc_metric_prefix),
                row.get("quorum_type"),
                **self.check.debug_stats_kwargs(
                    tags=cluster_name_tag + ["quorum_type_desc:{}".format(row.get("quorum_type_desc"))]
                )
            )
            self.check.gauge(
                "{}.quorum_state".format(self._fc_metric_prefix),
                row.get("quorum_state"),
                **self.check.debug_stats_kwargs(
                    tags=cluster_name_tag + ["quorum_state_desc:{}".format(row.get("quorum_state_desc"))],
                )
            )
        for row in fc_node_rows:
            node_tags = cluster_name_tag + ["node_name:{}".format(row.get("node_name"))]
            self.check.gauge(
                "{}.status".format(self._fc_node_metric_prefix),
                row.get("status"),
                **self.check.debug_stats_kwargs(
                    tags=node_tags + ["status_description:{}".format(row.get("status_description"))],
                )
            )
            self.check.gauge(
                "{}.is_current_owner".format(self._fc_node_metric_prefix),
                row.get("is_current_owner"),
                **self.check.debug_stats_kwargs(tags=node_tags)
            )
        for row in fc_member_rows:
            member_tags = cluster_name_tag + ["member_name:{}".format(row.get("member_name"))]
            self.check.gauge(
                "{}.type".format(self._fc_member_metric_prefix),
                row.get("member_type"),
                **self.check.debug_stats_kwargs(
                    tags=member_tags + ["member_type_desc:{}".format(row.get("member_type_desc"))]
                )
            )
            self.check.gauge(
                "{}.state".format(self._fc_member_metric_prefix),
                row.get("member_state"),
                **self.check.debug_stats_kwargs(
                    tags=member_tags + ["member_state_desc:{}".format(row.get("member_state_desc"))]
                )
            )
            self.check.gauge(
                "{}.number_of_quorum_votes".format(self._fc_member_metric_prefix),
                row.get("number_of_quorum_votes"),
                **self.check.debug_stats_kwargs(tags=member_tags)
            )

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
