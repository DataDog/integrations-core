# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

OS_TASKS_METRICS_QUERY = {
    "name": "sys.dm_os_tasks",
    "query": """select
        scheduler_id,
        SUM(CAST(context_switches_count AS BIGINT)) as context_switches_count,
        SUM(CAST(pending_io_count AS BIGINT)) as pending_io_count,
        SUM(pending_io_byte_count) as pending_io_byte_count,
        AVG(pending_io_byte_average) as pending_io_byte_average
        from sys.dm_os_tasks group by scheduler_id
    """,
    "columns": [
        {"name": "scheduler_id", "type": "tag"},
        {"name": "task.context_switches_count", "type": "gauge"},
        {"name": "task.pending_io_count", "type": "gauge"},
        {"name": "task.pending_io_byte_count", "type": "gauge"},
        {"name": "task.pending_io_byte_average", "type": "gauge"},
    ],
}


class SqlserverOsTasksMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-tasks-transact-sql
    @property
    def include_task_scheduler_metrics(self):
        return self.config.database_metrics_config["task_scheduler_metrics"]["enabled"]

    @property
    def enabled(self):
        if not self.include_task_scheduler_metrics:
            return False
        return True

    @property
    def queries(self):
        return [OS_TASKS_METRICS_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_task_scheduler_metrics={self.include_task_scheduler_metrics})"
        )
