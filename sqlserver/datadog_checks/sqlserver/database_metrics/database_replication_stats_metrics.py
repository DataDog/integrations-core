# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

DATABASE_REPLICATION_STATS_METRICS_QUERY = {
    "name": "sys.dm_hadr_database_replica_states",
    "query": """SELECT
        resource_group_id,
        name,
        replica_server_name,
        synchronization_state_desc,
        synchronization_state
        from sys.dm_hadr_database_replica_states as dhdrs
        inner join sys.availability_groups as ag
        on ag.group_id = dhdrs.group_id
        inner join sys.availability_replicas as ar
        on dhdrs.replica_id = ar.replica_id
    """.strip(),
    "columns": [
        {"name": "availability_group", "type": "tag"},
        {"name": "availability_group_name", "type": "tag"},
        {"name": "replica_server_name", "type": "tag"},
        {"name": "synchronization_state_desc", "type": "tag"},
        {"name": "ao.replica_sync_state", "type": "gauge"},
    ],
}


class SqlserverDatabaseReplicationStatsMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-hadr-database-replica-states-transact-sql?view=sql-server-ver15
    @property
    def include_ao_metrics(self) -> bool:
        return self.config.database_metrics_config["ao_metrics"]["enabled"]

    @property
    def availability_group(self):
        return self.config.database_metrics_config["ao_metrics"]["availability_group"]

    @property
    def only_emit_local(self):
        return self.config.database_metrics_config["ao_metrics"]["only_emit_local"]

    @property
    def enabled(self):
        if not self.include_ao_metrics:
            return False
        return True

    @property
    def queries(self):
        query = DATABASE_REPLICATION_STATS_METRICS_QUERY.copy()
        if self.availability_group or self.only_emit_local:
            where_clauses = []
            if self.availability_group:
                where_clauses.append(f"resource_group_id = '{self.availability_group}'")
            if self.only_emit_local:
                where_clauses.append("is_local = 1")
            query['query'] += f" where {' and '.join(where_clauses)}"
        return [query]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_ao_metrics={self.include_ao_metrics}, "
            f"availability_group={self.availability_group}, "
            f"only_emit_local={self.only_emit_local})"
        )
