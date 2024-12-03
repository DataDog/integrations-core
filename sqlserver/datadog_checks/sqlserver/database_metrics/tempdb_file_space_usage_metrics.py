# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import functools

from datadog_checks.sqlserver.utils import is_azure_sql_database

from .base import SqlserverDatabaseMetricsBase

TEMPDB_SPACE_USAGE_QUERY = {
    "name": "sys.dm_db_file_space_usage",
    "query": """SELECT
        database_id,
        ISNULL(SUM(unallocated_extent_page_count)*1.0/128, 0) as free_space,
        ISNULL(SUM(version_store_reserved_page_count)*1.0/128, 0) as used_space_by_version_store,
        ISNULL(SUM(internal_object_reserved_page_count)*1.0/128, 0) as used_space_by_internal_object,
        ISNULL(SUM(user_object_reserved_page_count)*1.0/128, 0) as used_space_by_user_object,
        ISNULL(SUM(mixed_extent_page_count)*1.0/128, 0) as mixed_extent_space
    FROM sys.dm_db_file_space_usage group by database_id""",
    "columns": [
        {"name": "database_id", "type": "tag"},
        {"name": "tempdb.file_space_usage.free_space", "type": "gauge"},
        {"name": "tempdb.file_space_usage.version_store_space", "type": "gauge"},
        {"name": "tempdb.file_space_usage.internal_object_space", "type": "gauge"},
        {"name": "tempdb.file_space_usage.user_object_space", "type": "gauge"},
        {"name": "tempdb.file_space_usage.mixed_extent_space", "type": "gauge"},
    ],
}


class SqlserverTempDBFileSpaceUsageMetrics(SqlserverDatabaseMetricsBase):
    @property
    def include_tempdb_file_space_usage_metrics(self) -> bool:
        return self.config.database_metrics_config['tempdb_file_space_usage_metrics']['enabled']

    @property
    def enabled(self):
        if not self.include_tempdb_file_space_usage_metrics:
            return False
        if is_azure_sql_database(self.engine_edition):
            return False
        return True

    @property
    def queries(self):
        return [TEMPDB_SPACE_USAGE_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"engine_edition={self.engine_edition}, "
            f"include_tempdb_file_space_usage_metrics={self.include_tempdb_file_space_usage_metrics})"
        )

    def _build_query_executors(self):
        executor = self.new_query_executor(
            self.queries,
            executor=functools.partial(self.execute_query_handler, db='tempdb'),
            extra_tags=['db:tempdb', 'database:tempdb'],
        )
        executor.compile_queries()
        return [executor]
