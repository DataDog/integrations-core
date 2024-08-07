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
    def _default_collection_interval(self) -> int:
        '''
        Returns the default interval in seconds at which to collect database backup metrics.
        '''
        return 5 * 60  # 5 minutes

    @property
    def collection_interval(self) -> int:
        '''
        Returns the interval in seconds at which to collect database backup metrics.
        Note: The database backup metrics query can be expensive, so it is recommended to set a higher interval.
        '''
        return int(self.instance_config.get('database_backup_metrics_interval', self._default_collection_interval))

    @property
    def queries(self):
        # make a copy of the query to avoid modifying the original
        # in case different instances have different collection intervals
        query = DATABASE_BACKUP_METRICS_QUERY.copy()
        query['collection_interval'] = self.collection_interval
        return [query]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"engine_edition={self.engine_edition}, "
            f"collection_interval={self.collection_interval})"
        )
