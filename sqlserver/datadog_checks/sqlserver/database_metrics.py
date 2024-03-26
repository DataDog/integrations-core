import copy
import functools
from typing import Callable, List, Optional

from datadog_checks.base.config import is_affirmative
from datadog_checks.sqlserver.const import (
    DEFAULT_INDEX_USAGE_STATS_INTERVAL,
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_MAJOR_VERSION,
)
from datadog_checks.sqlserver.queries import (
    DATABASE_BACKUP_METRICS_QUERY,
    DB_FRAGMENTATION_QUERY,
    INDEX_USAGE_STATS_QUERY,
    MASTER_FILES_METRICS_QUERY,
    OS_TASK_METRICS_QUERY,
    QUERY_AO_FAILOVER_CLUSTER,
    QUERY_AO_FAILOVER_CLUSTER_MEMBER,
    QUERY_FAILOVER_CLUSTER_INSTANCE,
    QUERY_LOG_SHIPPING_PRIMARY,
    QUERY_LOG_SHIPPING_SECONDARY,
    TASK_SCHEDULER_METRICS_QUERY,
    TEMPDB_SPACE_USAGE_QUERY,
    get_query_ao_availability_groups,
    get_query_file_stats,
)
from datadog_checks.sqlserver.utils import is_azure_database, is_azure_sql_database


class SqlserverDatabaseMetricsBase:
    def __init__(self, instance_config, new_query_executor, server_static_info, execute_query_handler=None):
        self.instance_config: dict = instance_config
        self.server_static_info: dict = server_static_info
        self.new_query_executor: Callable = new_query_executor
        self.execute_query_handler: Callable = execute_query_handler

    @property
    def major_version(self):
        return self.server_static_info.get(STATIC_INFO_MAJOR_VERSION)

    @property
    def engine_edition(self):
        return self.server_static_info.get(STATIC_INFO_ENGINE_EDITION)

    @property
    def enabled(self):
        raise NotImplementedError

    @property
    def queries(self):
        raise NotImplementedError

    @property
    def databases(self):
        raise NotImplementedError

    @property
    def query_executors(self):
        executor = self.new_query_executor(self.queries)
        executor.compile_queries()
        return [executor]

    def execute(self):
        if not self.enabled:
            return
        for query_executor in self.query_executors:
            query_executor.execute()


class SqlserverFileStatsMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        if not self.major_version and not is_azure_database(self.engine_edition):
            return False
        return True

    @property
    def queries(self):
        return [get_query_file_stats(self.major_version, self.engine_edition)]


class SqlserverAoMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_ao_metrics', False)):
            return False
        if not self.major_version and not is_azure_database(self.engine_edition):
            return False
        if self.major_version > 2012 or is_azure_database(self.engine_edition):
            return True
        return False

    @property
    def queries(self):
        return [
            get_query_ao_availability_groups(self.major_version),
            QUERY_AO_FAILOVER_CLUSTER,
            QUERY_AO_FAILOVER_CLUSTER_MEMBER,
        ]


class SqlserverFciMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_fci_metrics', False)):
            return False
        if not self.major_version and not is_azure_database(self.engine_edition):
            return False
        if self.major_version > 2012 or self.engine_edition == ENGINE_EDITION_AZURE_MANAGED_INSTANCE:
            return True
        return False

    @property
    def queries(self):
        return [QUERY_FAILOVER_CLUSTER_INSTANCE]


class SqlserverPrimaryLogShippingMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_primary_log_shipping_metrics', False)):
            return False
        return True

    @property
    def queries(self):
        return [QUERY_LOG_SHIPPING_PRIMARY]


class SqlserverSecondaryLogShippingMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_secondary_log_shipping_metrics', False)):
            return False
        return True

    @property
    def queries(self):
        return [QUERY_LOG_SHIPPING_SECONDARY]


class SqlserverTempDBFileSpaceUsageMetrics(SqlserverDatabaseMetricsBase):
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_tempdb_file_space_usage_metrics', True)):
            return False
        if is_azure_sql_database(self.engine_edition):
            return False
        return True

    @property
    def queries(self):
        return [TEMPDB_SPACE_USAGE_QUERY]

    @property
    def query_executors(self):
        executor = self.new_query_executor(
            self.queries,
            executor=functools.partial(self.execute_query_handler, db='tempdb'),
            extra_tags=['db:tempdb', 'database:tempdb'],
        )
        executor.compile_queries()
        return [executor]


class SqlserverIndexUsageMetrics(SqlserverDatabaseMetricsBase):
    def __init__(
        self, instance_config, new_query_executor, server_static_info, execute_query_handler=None, databases=None
    ):
        super(SqlserverIndexUsageMetrics, self).__init__(
            instance_config, new_query_executor, server_static_info, execute_query_handler
        )
        self._databases: Optional[List[str]] = databases

    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_index_usage_metrics', True)):
            return False
        return True

    @property
    def collection_interval(self):
        return int(self.instance_config.get('index_usage_stats_interval', DEFAULT_INDEX_USAGE_STATS_INTERVAL))

    @property
    def queries(self):
        INDEX_USAGE_STATS_QUERY['collection_interval'] = self.collection_interval
        return [INDEX_USAGE_STATS_QUERY]

    @property
    def databases(self):
        databases = self._databases or []
        if is_affirmative(self.instance_config.get('include_index_usage_metrics_tempdb', False)):
            databases = [database for database in databases if database != 'tempdb']
        return databases

    @property
    def query_executors(self):
        executors = []
        for database in self.databases:
            executor = self.new_query_executor(
                self.queries,
                executor=functools.partial(self.execute_query_handler, db=database),
            )
            executor.compile_queries()
            executors.append(executor)
        return executors


class SqlserverDbFragmentationMetrics(SqlserverDatabaseMetricsBase):
    # sys.dm_db_index_physical_stats
    #
    # Returns size and fragmentation information for the data and
    # indexes of the specified table or view in SQL Server.
    #
    # There are reports of this query being very slow for large datasets,
    # so debug query timing are included to help monitor it.
    # https://dba.stackexchange.com/q/76374
    #
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-db-index-physical-stats-transact-sql?view=sql-server-ver15
    def __init__(
        self, instance_config, new_query_executor, server_static_info, execute_query_handler=None, databases=None
    ):
        super(SqlserverDbFragmentationMetrics, self).__init__(
            instance_config, new_query_executor, server_static_info, execute_query_handler
        )
        self._databases: Optional[List[str]] = databases
        self.db_fragmentation_object_names = self.instance_config.get('db_fragmentation_object_names', [])

    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_db_fragmentation_metrics', False)):
            return False
        return True

    @property
    def queries(self):
        if self.db_fragmentation_object_names:
            DB_FRAGMENTATION_QUERY['query'] += " AND OBJECT_NAME(DDIPS.object_id, DDIPS.database_id) IN ({})".format(
                ','.join(["'{}'".format(name) for name in self.db_fragmentation_object_names])
            )
        return [DB_FRAGMENTATION_QUERY]

    @property
    def databases(self):
        return self._databases or []

    @property
    def query_executors(self):
        executors = []
        for database in self.databases:
            queries = copy.deepcopy(self.queries)
            for query in queries:
                query['query'] = query['query'].format(db=database)
            executor = self.new_query_executor(
                queries,
                executor=functools.partial(self.execute_query_handler, db=database),
                extra_tags=['db:{}'.format(database)],
            )
            executor.compile_queries()
            executors.append(executor)
        return executors


class SqlserverMasterFilesMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-master-files-transact-sql
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_master_files_metrics', False)):
            return False
        return True

    @property
    def queries(self):
        return [MASTER_FILES_METRICS_QUERY]


class SqlserverDatabaseBackupMetrics(SqlserverDatabaseMetricsBase):
    # msdb.dbo.backupset
    #
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


class SqlserverTaskSchedulerMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-schedulers-transact-sql
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-tasks-transact-sql
    @property
    def enabled(self):
        if not is_affirmative(self.instance_config.get('include_task_scheduler_metrics', False)):
            return False
        return True

    @property
    def queries(self):
        return [TASK_SCHEDULER_METRICS_QUERY, OS_TASK_METRICS_QUERY]
