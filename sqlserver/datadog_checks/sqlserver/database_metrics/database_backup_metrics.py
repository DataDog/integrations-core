# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.sqlserver.utils import is_azure_sql_database

from .base import SqlserverDatabaseMetricsBase

DATABASE_BACKUP_METRICS_QUERY = {
    "name": "msdb.dbo.backupset",
    "query": """SELECT
        sys.databases.name as db,
        sys.databases.name as database_name,
        count(backup_set_id) as backup_set_id_count
        from msdb.dbo.backupset right outer join sys.databases
        on sys.databases.name = msdb.dbo.backupset.database_name
        group by sys.databases.name
    """,
    "columns": [
        {"name": "db", "type": "tag"},
        {"name": "database", "type": "tag"},
        {"name": "database.backup_count", "type": "gauge"},
    ],
}


class SqlserverDatabaseBackupMetrics(SqlserverDatabaseMetricsBase):
    # msdb.dbo.backupset
    # Contains a row for each backup set. A backup set
    # contains the backup from a single, successful backup operation.
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-tables/backupset-transact-sql?view=sql-server-ver15
    @property
    def enabled(self):
        if is_azure_sql_database(self.engine_edition):
            return False
        return True

    @property
    def queries(self):
        return [DATABASE_BACKUP_METRICS_QUERY]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(" f"enabled={self.enabled}, " f"engine_edition={self.engine_edition}"
