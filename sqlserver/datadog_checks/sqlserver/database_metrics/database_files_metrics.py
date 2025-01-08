# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import functools

from .base import SqlserverDatabaseMetricsBase

DATABASE_FILES_METRICS_QUERY = {
    "name": "sys.database_files",
    "query": """SELECT
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
        name,
        state_desc,
        ISNULL(size, 0) as size,
        ISNULL(CAST(FILEPROPERTY(name, 'SpaceUsed') as int), 0) as space_used,
        state
        FROM sys.database_files
    """,
    "columns": [
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
        executors = []
        for database in self.databases:
            executor = self.new_query_executor(
                self.queries,
                executor=functools.partial(self.execute_query_handler, db=database),
                extra_tags=['db:{}'.format(database), 'database:{}'.format(database)],
            )
            executor.compile_queries()
            executors.append(executor)
        return executors
