STATUS_METRICS = {
    "ready": "gauge",
    "health": "gauge",
}
WORK_POOL_METRICS = {
    "work_pool.is_ready": "gauge",
    "work_pool.is_not_ready": "gauge",
    "work_pool.is_paused": "gauge",
    "work_pool.worker.is_online": "gauge",
    "work_pool.worker.heartbeat_age_seconds": "gauge",
}

WORK_QUEUE_METRICS = {
    "work_queue.is_ready": "gauge",
    "work_queue.is_not_ready": "gauge",
    "work_queue.is_paused": "gauge",
    "work_queue.last_polled_age_seconds": "gauge",
    "work_queue.backlog.size": "gauge",
    "work_queue.backlog.age": "gauge",
    "work_queue.concurrency.in_use": "gauge",
}

DEPLOYMENT_METRICS = {
    "deployment.is_ready": "gauge",
}

FLOW_RUN_METRICS = {
    "flow_runs.scheduled.count": "gauge",
    "flow_runs.pending.count": "gauge",
    "flow_runs.throughput": "count",
    "flow_runs.failed.count": "count",
    "flow_runs.cancelled.count": "count",
    "flow_runs.crashed.count": "count",
    "flow_runs.running.count": "gauge",
    "flow_runs.paused.count": "gauge",
    "flow_runs.completed.count": "count",
    "flow_runs.execution_duration": "histogram",
    "flow_runs.late_start.count": "count",
    "flow_runs.retry_gaps_duration": "histogram",
    "flow_runs.queue_wait_duration": "histogram",
}

TASK_RUN_METRICS = {
    "task_runs.execution_duration": "histogram",
    "task_runs.dependency_wait_duration": "histogram",
    "task_runs.late_start.count": "count",
    "task_runs.pending.count": "gauge",
    "task_runs.running.count": "gauge",
    "task_runs.throughput": "count",
    "task_runs.paused.count": "gauge",
    "task_runs.completed.count": "count",
    "task_runs.failed.count": "count",
    "task_runs.cancelled.count": "count",
    "task_runs.crashed.count": "count",
}

METRICS_SPEC = {
    **STATUS_METRICS,
    **WORK_POOL_METRICS,
    **WORK_QUEUE_METRICS,
    **DEPLOYMENT_METRICS,
    **FLOW_RUN_METRICS,
    **TASK_RUN_METRICS,
}
