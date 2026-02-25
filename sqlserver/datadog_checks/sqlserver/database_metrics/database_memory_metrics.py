# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

# Exclude internal databases
# 32767: mssqlsystemresource
# 32761: model_msdb
# 32762: model_replicatedmaster
DATABASE_MEMORY_METRICS_QUERY = """
    SELECT
        DB_NAME(database_id) as db,
        COUNT(*) * 8 / 1024.0 as buffer_pool_size_mb,
        SUM(CAST(is_modified AS INT)) * 8 / 1024.0 as dirty_pages_mb
    FROM sys.dm_os_buffer_descriptors WITH (NOLOCK)
    WHERE database_id NOT IN (32767,32761,32762)
    GROUP BY database_id;
"""

DATABASE_MEMORY_METRICS_QUERY_MAPPING = {
    "name": "database_memory_metrics",
    "query": DATABASE_MEMORY_METRICS_QUERY,
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "database.buffer_pool.size", "type": "gauge"},
        {"name": "database.buffer_pool.dirty_pages", "type": "gauge"},
    ],
}


class SqlserverDatabaseMemoryMetrics(SqlserverDatabaseMetricsBase):
    """
    Collects database memory metrics from sys.dm_os_buffer_descriptors.
    This provides insights into buffer pool usage per database.
    """

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect database memory metrics.
        Note: Querying sys.dm_os_buffer_descriptors can be resource intensive on systems with large buffer pools.
        '''
        return self.config.database_metrics_config["db_memory_metrics"].get("collection_interval", 300)

    @property
    def enabled(self) -> bool:
        return self.config.database_metrics_config["db_memory_metrics"]["enabled"]

    @property
    def queries(self):
        query_mapping = DATABASE_MEMORY_METRICS_QUERY_MAPPING.copy()
        query_mapping['collection_interval'] = self.collection_interval
        return [query_mapping]

    @property
    def databases(self):
        """
        This metric runs at instance level since we aggregate across all databases
        in a single query for performance reasons.
        """
        return [None]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled}, collection_interval={self.collection_interval})"
