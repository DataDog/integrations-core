# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .base import SqlserverDatabaseMetricsBase

OS_SCHEDULERS_METRICS_QUERY = {
    "name": "sys.dm_os_schedulers",
    "query": """SELECT
        scheduler_id,
        parent_node_id,
        current_tasks_count,
        current_workers_count,
        active_workers_count,
        runnable_tasks_count,
        work_queue_count
        from sys.dm_os_schedulers
    """,
    "columns": [
        {"name": "scheduler_id", "type": "tag"},
        {"name": "parent_node_id", "type": "tag"},
        {"name": "scheduler.current_tasks_count", "type": "gauge"},
        {"name": "scheduler.current_workers_count", "type": "gauge"},
        {"name": "scheduler.active_workers_count", "type": "gauge"},
        {"name": "scheduler.runnable_tasks_count", "type": "gauge"},
        {"name": "scheduler.work_queue_count", "type": "gauge"},
    ],
}


class SqlserverOsSchedulersMetrics(SqlserverDatabaseMetricsBase):
    # https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-schedulers-transact-sql
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
        return [OS_SCHEDULERS_METRICS_QUERY]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"enabled={self.enabled}, "
            f"include_task_scheduler_metrics={self.include_task_scheduler_metrics})"
        )
