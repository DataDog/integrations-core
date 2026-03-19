# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

WORK_POOL_TAG_KEYS = ["work_pool_id:", "work_pool_name:", "work_pool_type:"]

WORKER_TAG_KEYS = ["work_pool_id:", "worker_id:", "worker_name:", "work_pool_name:"]

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
    "deployment_name:",
    "flow_id:",
]

TASK_RUN_TAG_KEYS = FLOW_RUN_TAG_KEYS + ["task_key:"]

E2E_METRIC_TAGS: dict[str, list[str]] = {
    # --- status metrics (no resource-specific tags) ---
    "prefect.server.health": [],
    "prefect.server.ready": [],
    # --- work pool metrics ---
    "prefect.server.work_pool.is_ready": WORK_POOL_TAG_KEYS,
    "prefect.server.work_pool.is_not_ready": WORK_POOL_TAG_KEYS,
    "prefect.server.work_pool.is_paused": WORK_POOL_TAG_KEYS,
    # --- worker metrics ---
    "prefect.server.work_pool.worker.is_online": WORKER_TAG_KEYS,
    "prefect.server.work_pool.worker.heartbeat_age_seconds": WORKER_TAG_KEYS,
    # --- work queue metrics ---
    "prefect.server.work_queue.is_ready": WORK_QUEUE_TAG_KEYS,
    "prefect.server.work_queue.is_not_ready": WORK_QUEUE_TAG_KEYS,
    "prefect.server.work_queue.is_paused": WORK_QUEUE_TAG_KEYS,
    "prefect.server.work_queue.last_polled_age_seconds": WORK_QUEUE_STATUS_TAG_KEYS,
    "prefect.server.work_queue.backlog.age": WORK_QUEUE_STATUS_TAG_KEYS,
    "prefect.server.work_queue.backlog.size": WORK_QUEUE_STATUS_TAG_KEYS,
    # --- deployment metrics ---
    "prefect.server.deployment.is_ready": DEPLOYMENT_TAG_KEYS,
    # --- flow run metrics ---
    "prefect.server.flow_runs.scheduled": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.pending": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.failed.count": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.cancelled.count": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.crashed.count": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.paused": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.completed.count": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.throughput": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.running": FLOW_RUN_TAG_KEYS,
    "prefect.server.flow_runs.late_start.count": FLOW_RUN_TAG_KEYS,
    # --- task run metrics ---
    "prefect.server.task_runs.pending": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.paused": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.cancelled.count": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.completed.count": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.failed.count": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.crashed.count": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.throughput": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.running": TASK_RUN_TAG_KEYS,
    "prefect.server.task_runs.late_start.count": TASK_RUN_TAG_KEYS,
}


@pytest.mark.e2e
def test_e2e_metrics(dd_agent_check):
    aggregator = dd_agent_check()

    cross_check_metrics = (
        'flow_runs.retry_gaps_duration',
        'task_runs.dependency_wait_duration',
        'flow_runs.queue_wait_duration',
        'work_queue.concurrency.in_use',
        'flow_runs.execution_duration',
        'task_runs.execution_duration',
    )
    all_metadata = get_metadata_metrics()
    metadata_metrics = {k: v for k, v in all_metadata.items() if not any(m in k for m in cross_check_metrics)}
    exclude = [k for k in all_metadata if any(m in k for m in cross_check_metrics)]
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_metric_type=False,
        check_symmetric_inclusion=True,
        exclude=exclude,
    )

    for metric_name, expected_tags in E2E_METRIC_TAGS.items():
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric_name, tag)
