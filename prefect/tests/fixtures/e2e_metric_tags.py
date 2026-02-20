# Mapping of metric name → required tag key prefixes.
# Each metric must have at least one tag starting with each listed prefix.

WORK_POOL_TAG_KEYS = ["work_pool_id:", "work_pool_name:", "work_pool_type:"]

WORKER_TAG_KEYS = ["work_pool_id:", "worker_id:", "worker_name:"]

WORK_QUEUE_TAG_KEYS = ["work_queue_id:", "work_queue_name:", "work_pool_id:", "work_pool_name:", "work_queue_priority:"]

WORK_QUEUE_STATUS_TAG_KEYS = WORK_QUEUE_TAG_KEYS + ["work_queue_status:"]

DEPLOYMENT_TAG_KEYS = [
    "deployment_id:",
    "deployment_name:",
    "flow_id:",
    "work_pool_name:",
    "work_pool_id:",
    "work_queue_name:",
    "work_queue_id:",
    "is_paused:",
]

FLOW_RUN_TAG_KEYS = [
    "work_pool_id:",
    "work_pool_name:",
    "work_queue_id:",
    "work_queue_name:",
    "deployment_id:",
    "flow_id:",
]

TASK_RUN_TAG_KEYS = FLOW_RUN_TAG_KEYS + ["task_key:"]

E2E_METRIC_TAGS: dict[str, list[str]] = {
    # --- status metrics (no resource-specific tags) ---
    "prefect_server.health": [],
    "prefect_server.ready": [],
    # --- work pool metrics ---
    "prefect_server.work_pool.is_ready": WORK_POOL_TAG_KEYS,
    "prefect_server.work_pool.is_not_ready": WORK_POOL_TAG_KEYS,
    "prefect_server.work_pool.is_paused": WORK_POOL_TAG_KEYS,
    # --- worker metrics ---
    "prefect_server.work_pool.worker.is_online": WORKER_TAG_KEYS,
    "prefect_server.work_pool.worker.heartbeat_age_seconds": WORKER_TAG_KEYS,
    # --- work queue metrics ---
    "prefect_server.work_queue.is_ready": WORK_QUEUE_TAG_KEYS,
    "prefect_server.work_queue.is_not_ready": WORK_QUEUE_TAG_KEYS,
    "prefect_server.work_queue.is_paused": WORK_QUEUE_TAG_KEYS,
    "prefect_server.work_queue.last_polled_age_seconds": WORK_QUEUE_STATUS_TAG_KEYS,
    "prefect_server.work_queue.backlog.age": WORK_QUEUE_STATUS_TAG_KEYS,
    "prefect_server.work_queue.backlog.size": WORK_QUEUE_STATUS_TAG_KEYS,
    # --- deployment metrics ---
    "prefect_server.deployment.is_ready": DEPLOYMENT_TAG_KEYS,
    # --- flow run metrics ---
    "prefect_server.flow_runs.scheduled.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.pending.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.failed.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.cancelled.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.crashed.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.paused.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.completed.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.throughput": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.late_start.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.execution_duration.avg": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.execution_duration.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.execution_duration.max": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.execution_duration.median": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.execution_duration.95percentile": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.queue_wait_duration.avg": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.queue_wait_duration.count": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.queue_wait_duration.max": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.queue_wait_duration.median": FLOW_RUN_TAG_KEYS,
    "prefect_server.flow_runs.queue_wait_duration.95percentile": FLOW_RUN_TAG_KEYS,
    # --- task run metrics ---
    "prefect_server.task_runs.pending.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.paused.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.cancelled.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.completed.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.failed.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.crashed.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.throughput": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.late_start.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.execution_duration.avg": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.execution_duration.count": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.execution_duration.max": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.execution_duration.median": TASK_RUN_TAG_KEYS,
    "prefect_server.task_runs.execution_duration.95percentile": TASK_RUN_TAG_KEYS,
}
