# -------------------------
# tag constants
# -------------------------
WP1_TAGS = ["work_pool_id:wp-1", "work_pool_name:default-pool", "work_pool_type:process"]
WP2_TAGS = ["work_pool_id:wp-2", "work_pool_name:paused-pool", "work_pool_type:docker"]
WP3_TAGS = ["work_pool_id:wp-3", "work_pool_name:not-ready-pool", "work_pool_type:kubernetes"]

WP1_WORKER_TAGS = ["work_pool_id:wp-1", "worker_id:w-3", "worker_name:worker-3"]
WP2_WORKER_TAGS = ["work_pool_id:wp-2", "worker_id:w-6", "worker_name:worker-6"]
WP3_WORKER_TAGS = ["work_pool_id:wp-3", "worker_id:w-8", "worker_name:worker-8"]

WQ1_TAGS = [
    "work_queue_id:wq-1",
    "work_queue_name:default-queue",
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_priority:1",
]
WQ2_TAGS = [
    "work_queue_id:wq-2",
    "work_queue_name:paused-queue",
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_priority:1",
]
WQ4_TAGS = [
    "work_queue_id:wq-4",
    "work_queue_name:not-ready-queue",
    "work_pool_id:wp-3",
    "work_pool_name:not-ready-pool",
    "work_queue_priority:1",
]

WQ1_STATUS_TAGS = WQ1_TAGS + ["work_queue_status:READY"]
WQ2_STATUS_TAGS = WQ2_TAGS + ["work_queue_status:PAUSED"]
WQ4_STATUS_TAGS = WQ4_TAGS + ["work_queue_status:NOT_READY"]

TAGS_F1 = [
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_id:wq-1",
    "work_queue_name:default-queue",
    "deployment_id:d-1",
    "flow_id:f-1",
]

TAGS_F2 = [
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_id:wq-2",
    "work_queue_name:paused-queue",
    "deployment_id:d-2",
    "flow_id:f-2",
]

TAGS_F3 = [
    "work_pool_id:wp-3",
    "work_pool_name:not-ready-pool",
    "work_queue_id:wq-4",
    "work_queue_name:not-ready-queue",
    "deployment_id:d-3",
    "flow_id:f-3",
]

TAGS_TR1 = TAGS_F1 + ["task_key:task-1"]
TAGS_TR2 = TAGS_F1 + ["task_key:task-2"]
TAGS_TR3 = TAGS_F1 + ["task_key:task-3"]
TAGS_TR7 = TAGS_F1 + ["task_key:task-7"]
TAGS_TR8 = TAGS_F1 + ["task_key:task-8"]
TAGS_TR9 = TAGS_F1 + ["task_key:task-9"]


ALL_METRIC_CASES = [
    # --- api status metrics ---
    ("prefect_server.ready", 1.0, [], "ready", 1),
    ("prefect_server.health", 1.0, [], "health", 1),
    # --- work pool metrics ---
    ("prefect_server.work_pool.is_ready", 1, WP1_TAGS, "wp1-is_ready", 1),
    ("prefect_server.work_pool.is_paused", 0, WP1_TAGS, "wp1-is_paused", 1),
    ("prefect_server.work_pool.is_ready", 0, WP2_TAGS, "wp2-is_ready", 1),
    ("prefect_server.work_pool.is_not_ready", 0, WP2_TAGS, "wp2-is_not_ready", 1),
    ("prefect_server.work_pool.is_paused", 1, WP2_TAGS, "wp2-is_paused", 1),
    ("prefect_server.work_pool.is_ready", 0, WP3_TAGS, "wp3-is_ready", 1),
    ("prefect_server.work_pool.is_not_ready", 1, WP3_TAGS, "wp3-is_not_ready", 1),
    ("prefect_server.work_pool.is_paused", 0, WP3_TAGS, "wp3-is_paused", 1),
    # --- worker metrics ---
    ("prefect_server.work_pool.worker.is_online", 1, WP1_WORKER_TAGS, "wp1-worker-is_online", 1),
    ("prefect_server.work_pool.worker.is_online", 0, WP2_WORKER_TAGS, "wp2-worker-is_online", 1),
    ("prefect_server.work_pool.worker.is_online", 0, WP3_WORKER_TAGS, "wp3-worker-is_online", 1),
    ("prefect_server.work_pool.worker.heartbeat_age_seconds", 55.0, WP1_WORKER_TAGS, "wp1-worker-heartbeat_age", 1),
    ("prefect_server.work_pool.worker.heartbeat_age_seconds", 56.544, WP2_WORKER_TAGS, "wp2-worker-heartbeat_age", 1),
    ("prefect_server.work_pool.worker.heartbeat_age_seconds", 0.0, WP3_WORKER_TAGS, "wp3-worker-heartbeat_age", 1),
    # --- work queue basic metrics ---
    ("prefect_server.work_queue.is_ready", 1.0, WQ1_TAGS, "wq1-is_ready", 1),
    ("prefect_server.work_queue.is_not_ready", 0.0, WQ1_TAGS, "wq1-is_not_ready", 1),
    ("prefect_server.work_queue.is_paused", 0.0, WQ1_TAGS, "wq1-is_paused", 1),
    ("prefect_server.work_queue.last_polled_age_seconds", 50.0, WQ1_STATUS_TAGS, "wq1-last_polled", 1),
    ("prefect_server.work_queue.is_ready", 0.0, WQ2_TAGS, "wq2-is_ready", 1),
    ("prefect_server.work_queue.is_not_ready", 0.0, WQ2_TAGS, "wq2-is_not_ready", 1),
    ("prefect_server.work_queue.is_paused", 1.0, WQ2_TAGS, "wq2-is_paused", 1),
    ("prefect_server.work_queue.last_polled_age_seconds", 52.0, WQ2_STATUS_TAGS, "wq2-last_polled", 1),
    ("prefect_server.work_queue.is_ready", 0.0, WQ4_TAGS, "wq4-is_ready", 1),
    ("prefect_server.work_queue.is_not_ready", 1.0, WQ4_TAGS, "wq4-is_not_ready", 1),
    ("prefect_server.work_queue.is_paused", 0.0, WQ4_TAGS, "wq4-is_paused", 1),
    ("prefect_server.work_queue.last_polled_age_seconds", 5.877, WQ4_STATUS_TAGS, "wq4-last_polled", 1),
    # --- work queue backlog metrics ---
    ("prefect_server.work_queue.backlog.age", 110.0, WQ1_STATUS_TAGS, "wq1-backlog-age", 1),
    ("prefect_server.work_queue.backlog.age", 31.889, WQ2_STATUS_TAGS, "wq2-backlog-age", 1),
    ("prefect_server.work_queue.backlog.age", 0.0, WQ4_STATUS_TAGS, "wq4-backlog-age", 1),
    ("prefect_server.work_queue.backlog.size", 2.0, WQ1_STATUS_TAGS, "wq1-backlog-size", 1),
    ("prefect_server.work_queue.backlog.size", 2.0, WQ2_STATUS_TAGS, "wq2-backlog-size", 1),
    ("prefect_server.work_queue.backlog.size", 0.0, WQ4_STATUS_TAGS, "wq4-backlog-size", 1),
    # --- deployment metrics ---
    (
        "prefect_server.deployment.is_ready",
        1.0,
        [
            "deployment_id:d-1",
            "deployment_name:deployment-1",
            "flow_id:f-1",
            "work_pool_name:default-pool",
            "work_pool_id:wp-1",
            "work_queue_name:default-queue",
            "work_queue_id:wq-1",
            "is_paused:False",
        ],
        "deployment-d1-is_ready",
        1,
    ),
    (
        "prefect_server.deployment.is_ready",
        0.0,
        [
            "deployment_id:d-2",
            "deployment_name:deployment-2",
            "flow_id:f-2",
            "work_pool_name:paused-pool",
            "work_pool_id:wp-2",
            "work_queue_name:queue-paused-pool",
            "work_queue_id:wq-3",
            "is_paused:True",
        ],
        "deployment-d2-is_not_ready",
        1,
    ),
    # --- flow run state counts ---
    ("prefect_server.flow_runs.pending.count", 2.0, TAGS_F2, "flow_runs-pending-f2", 1),
    ("prefect_server.flow_runs.scheduled.count", 1.0, TAGS_F1, "flow_runs-scheduled-f1", 1),
    ("prefect_server.flow_runs.failed.count", 1.0, TAGS_F1, "flow_runs-failed-count-f1", 1),
    ("prefect_server.flow_runs.cancelled.count", 0.0, TAGS_F2, "flow_runs-cancelled-count-f2", 1),
    ("prefect_server.flow_runs.crashed.count", 1.0, TAGS_F1, "flow_runs-crashed-count-f1", 1),
    ("prefect_server.flow_runs.paused.count", 0.0, TAGS_F1, "flow_runs-paused-f1", 1),
    ("prefect_server.flow_runs.completed.count", 2.0, TAGS_F2, "flow_runs-completed-count-f2", 1),
    ("prefect_server.flow_runs.throughput", 6.0, TAGS_F2, "flow_runs-throughput-f2", 1),
    ("prefect_server.flow_runs.late_start.count", 2.0, TAGS_F2, "flow_runs-late_start-f2", 1),
    # ("prefect_server.flow_runs.late_start.rate", 2.0 / 6.0, TAGS_F2, "flow_runs-late_start-rate-f2", 1),
    ("prefect_server.flow_runs.execution_duration", 10.123, TAGS_F1, "flow_runs-execution-duration-f1", 1),
    ("prefect_server.flow_runs.queue_wait_duration", 5.333, TAGS_F3, "flow_runs-queue-wait-f3", 1),
    ("prefect_server.flow_runs.retry_gaps_duration", 5, TAGS_F1, "flow_runs-retry-gaps-f1", 1),
    # --- task run state counts ---
    ("prefect_server.task_runs.pending.count", 1.0, TAGS_TR1, "task_runs-pending-tr1", 1),
    ("prefect_server.task_runs.paused.count", 1.0, TAGS_TR8, "task_runs-paused-tr8", 1),
    ("prefect_server.task_runs.crashed.count", 1.0, TAGS_TR7, "task_runs-crashed-count-tr7", 1),
    ("prefect_server.task_runs.cancelled.count", 2.0, TAGS_TR9, "task_runs-cancelled-count-tr9", 1),
    ("prefect_server.task_runs.completed.count", 2.0, TAGS_TR3, "task_runs-completed-count-tr3", 1),
    ("prefect_server.task_runs.failed.count", 0.0, TAGS_TR3, "task_runs-failed-count-tr3", 1),
    ("prefect_server.task_runs.throughput", 4.0, TAGS_TR1, "task_runs-throughput-tr1", 1),
    ("prefect_server.task_runs.late_start.count", 1.0, TAGS_TR1, "task_runs-late_start-tr1", 1),
    # ("prefect_server.task_runs.late_start.rate", 1.0 / 4.0, TAGS_TR1, "task_runs-late_start-rate-tr1", 1),
    # --- task run metrics ---
    ("prefect_server.task_runs.execution_duration", 5.333, TAGS_TR1, "task_runs-execution-duration-tr1", 2),
    ("prefect_server.task_runs.dependency_wait_duration", 2.0, TAGS_TR2, "task_runs-dependency-wait-duration-tr1", 1),
]
