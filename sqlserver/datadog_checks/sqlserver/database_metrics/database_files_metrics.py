# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import functools

from datadog_checks.sqlserver.utils import is_azure_sql_database, serialize_database_names

from .base import SqlserverDatabaseMetricsBase

DATABASE_FILES_QUERY = """SELECT
        DB_NAME() AS db,
        DB_NAME() AS database_name,
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
    """

DATABASE_FILES_METRICS_QUERY = {
    "name": "sys.database_files",
    "query": DATABASE_FILES_QUERY,
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

DATABASE_FILES_BATCH_QUERY = """SET NOCOUNT ON;
DECLARE @monitored_databases xml = ?;
DECLARE @database sysname;
DECLARE @module nvarchar(776);
DECLARE @statement nvarchar(max) = N'{}';

DECLARE database_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT database_node.value('.', 'sysname')
    FROM @monitored_databases.nodes('/databases/database') AS databases(database_node);

OPEN database_cursor;
FETCH NEXT FROM database_cursor INTO @database;
WHILE @@FETCH_STATUS = 0
BEGIN
    BEGIN TRY
        SET @module = QUOTENAME(@database) + N'.sys.sp_executesql';
        EXEC @module @statement;
    END TRY
    BEGIN CATCH
        -- A database can become unavailable after autodiscovery. Skip it so later databases are still collected.
    END CATCH;
    FETCH NEXT FROM database_cursor INTO @database;
END;
CLOSE database_cursor;
DEALLOCATE database_cursor;
""".format(DATABASE_FILES_QUERY.replace("'", "''"))


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
        if not is_azure_sql_database(self.engine_edition):
            query = dict(DATABASE_FILES_METRICS_QUERY)
            query['query'] = DATABASE_FILES_BATCH_QUERY
            query['params'] = (serialize_database_names(self.databases or []),)
            executor = self.new_query_executor(
                [query], executor=functools.partial(self.execute_query_handler, fetch_multiple_results=True)
            )
            executor.compile_queries()
            return [executor]

        executors = []
        for database in self.databases:
            executor = self.new_query_executor(
                self.queries,
                executor=functools.partial(self.execute_query_handler, db=database),
                track_operation_time=self.track_operation_time,
            )
            executor.compile_queries()
            executors.append(executor)
        return executors
