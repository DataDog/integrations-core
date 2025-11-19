# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

AVAILABILITY_GROUPS_METRICS_QUERY = {
    "name": "sys.dm_hadr_availability_group_states",
    "query": """SELECT
        resource_group_id,
        name,
        synchronization_health_desc,
        synchronization_health,
        primary_recovery_health,
        secondary_recovery_health
        from sys.dm_hadr_availability_group_states as dhdrcs
        inner join sys.availability_groups as ag
        on ag.group_id = dhdrcs.group_id
    """.strip(),
    "columns": [
        {"name": "availability_group", "type": "tag"},
        {"name": "availability_group_name", "type": "tag"},
        {"name": "synchronization_health_desc", "type": "tag"},
        {"name": "ao.ag_sync_health", "type": "gauge"},
        {"name": "ao.primary_replica_health", "type": "gauge"},
        {"name": "ao.secondary_replica_health", "type": "gauge"},
    ],
}


class SqlserverAvailabilityGroupsMetrics(SqlserverDatabaseMetricsBase):
    # sys.dm_hadr_availability_group_states
    # Returns a row for each Always On availability group that possesses an availability replica on the local instance
    # of SQL Server. Each row displays the states that define the health of a given availability group.
    #
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-hadr-availability-group-states-transact-sql?view=sql-server-ver15
    @property
    def include_ao_metrics(self) -> bool:
        return self.config.database_metrics_config["ao_metrics"]["enabled"]

    @property
    def availability_group(self):
        return self.config.database_metrics_config["ao_metrics"]["availability_group"]

    @property
    def enabled(self):
        if not self.include_ao_metrics:
            return False
        return True

    @property
    def queries(self):
        query = AVAILABILITY_GROUPS_METRICS_QUERY.copy()
        if self.availability_group:
            query['query'] += f" where resource_group_id = '{self.availability_group}'"
        return [query]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_ao_metrics={self.include_ao_metrics}, "
            f"availability_group={self.availability_group})"
        )
