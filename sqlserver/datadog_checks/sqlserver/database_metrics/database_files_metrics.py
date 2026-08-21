# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sqlserver.utils import serialize_database_names

from .base import SqlserverDatabaseMetricsBase

DATABASE_FILES_METRICS_QUERY = {
    "name": "sys.database_files",
    "query": """DECLARE @monitored_databases xml = ?;
    WITH monitored_databases AS (
        SELECT database_node.value('.', 'nvarchar(128)') AS name
        FROM @monitored_databases.nodes('/databases/database') AS databases(database_node)
    )
    SELECT
        monitored_databases.name as db,
        monitored_databases.name as database_name,
        file_id,
        CASE type
            WHEN 0 THEN 'data'
            WHEN 1 THEN 'transaction_log'
            WHEN 2 THEN 'filestream'
            WHEN 3 THEN 'unknown'
            WHEN 4 THEN 'full_text'
            ELSE 'other'
        END AS file_type,
        physical_name,
        sys.master_files.name,
        sys.master_files.state_desc,
        ISNULL(size, 0) as size,
        ISNULL(CAST(FILEPROPERTY(sys.master_files.name, 'SpaceUsed') as int), 0) as space_used,
        sys.master_files.state
        FROM monitored_databases
        INNER JOIN sys.databases ON sys.databases.name = monitored_databases.name
        INNER JOIN sys.master_files ON sys.master_files.database_id = sys.databases.database_id
    """,
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "database", "type": "tag"},
        {"name": "file_id", "type": "tag"},
        {"name": "file_type", "type": "tag"},
        {"name": "file_location", "type": "tag"},
        {"name": "file_name", "type": "tag"},
        {"name": "database_files_state_desc", "type": "tag"},
        {"name": "size", "type": "source"},
        {"name": "space_used", "type": "source"},
        {"name": "database.files.state", "type": "gauge"},
    ],
    "extras": [
        # size/space_used are in pages, 1 page = 8 KB. Calculated after the query to avoid int overflow
        {"name": "database.files.size", "expression": "size*8", "submit_type": "gauge"},
        {"name": "database.files.space_used", "expression": "space_used*8", "submit_type": "gauge"},
    ],
}


class SqlserverDatabaseFilesMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-database-files-transact-sql
    @property
    def include_database_files_metrics(self) -> bool:
        return self.config.database_metrics_config["db_files_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_database_files_metrics:
            return False
        return True

    @property
    def queries(self):
        return [DATABASE_FILES_METRICS_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_database_files_metrics={self.include_database_files_metrics})"
        )

    def _build_query_executors(self):
        query = dict(DATABASE_FILES_METRICS_QUERY)
        query['params'] = (serialize_database_names(self.databases or []),)
        executor = self.new_query_executor([query], executor=self.execute_query_handler)
        executor.compile_queries()
        return [executor]
