# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

AVAILABILITY_REPLICAS_METRICS_QUERY = {
    "name": "sys.availability_replicas",
    "query": """SELECT
        database_name,
        resource_group_id,
        name,
        replica_server_name,
        failover_mode_desc,
        {is_primary_replica},
        failover_mode,
        is_failover_ready
        from sys.availability_replicas as ar
        inner join sys.dm_hadr_database_replica_cluster_states as dhdrcs
        on ar.replica_id = dhdrcs.replica_id
        inner join sys.dm_hadr_database_replica_states as dhdrs
        on ar.replica_id = dhdrs.replica_id
        inner join sys.availability_groups as ag
        on ag.group_id = ar.group_id
    """.strip(),
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "availability_group", "type": "tag"},
        {"name": "availability_group_name", "type": "tag"},
        {"name": "replica_server_name", "type": "tag"},
        {"name": "failover_mode_desc", "type": "tag"},
        {"name": "is_primary_replica", "type": "tag"},
        {"name": "ao.replica_failover_mode", "type": "gauge"},
        {"name": "ao.replica_failover_readiness", "type": "gauge"},
    ],
}


class SqlserverAvailabilityReplicasMetrics(SqlserverDatabaseMetricsBase):
    # sys.availability_replicas (Transact-SQL)
    #
    # Returns a row for each of the availability replicas that belong to any Always On availability group in the WSFC
    # failover cluster. If the local server instance is unable to talk to the WSFC failover cluster, for example because
    # the cluster is down or quorum has been lost, only rows for local availability replicas are returned.
    # These rows will contain only the columns of data that are cached locally in metadata.
    #
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-availability-replicas-transact-sql?view=sql-server-ver15
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
    def ao_database(self):
        return self.config.database_metrics_config["ao_metrics"]["ao_database"]

    @property
    def enabled(self):
        if not self.include_ao_metrics:
            return False
        return True

    @property
    def queries(self):
        query = AVAILABILITY_REPLICAS_METRICS_QUERY.copy()
        if self.availability_group or self.only_emit_local or self.ao_database:
            where_clauses = []
            if self.availability_group:
                where_clauses.append(f"resource_group_id = '{self.availability_group}'")
            if self.only_emit_local:
                where_clauses.append("is_local = 1")
            if self.ao_database:
                where_clauses.append(f"database_name = '{self.ao_database}'")
            query['query'] += f" where {' and '.join(where_clauses)}"
        if self.major_version >= 2014:
            # This column only supported in SQL Server 2014 and later
            is_primary_replica = "is_primary_replica"
        else:
            is_primary_replica = "'unknown' as is_primary_replica"
        query['query'] = query['query'].format(is_primary_replica=is_primary_replica)
        return [query]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_ao_metrics={self.include_ao_metrics}, "
            f"availability_group={self.availability_group}, "
            f"only_emit_local={self.only_emit_local}, "
            f"ao_database={self.ao_database})"
        )
