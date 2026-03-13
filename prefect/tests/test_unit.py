from datetime import datetime, timezone
from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.prefect import PrefectCheck
from datadog_checks.prefect.check import Event, PrefectFilterMetrics
from tests.helpers import MockDatetime

WP1_TAGS = ["work_pool_id:wp-1", "work_pool_name:default-pool", "work_pool_type:process"]
WP2_TAGS = ["work_pool_id:wp-2", "work_pool_name:paused-pool", "work_pool_type:docker"]
WP3_TAGS = ["work_pool_id:wp-3", "work_pool_name:not-ready-pool", "work_pool_type:kubernetes"]

WP1_WORKER_TAGS = ["work_pool_id:wp-1", "work_pool_name:default-pool", "worker_id:w-3", "worker_name:worker-3"]
WP2_WORKER_TAGS = ["work_pool_id:wp-2", "work_pool_name:paused-pool", "worker_id:w-6", "worker_name:worker-6"]
WP3_WORKER_TAGS = ["work_pool_id:wp-3", "work_pool_name:not-ready-pool", "worker_id:w-8", "worker_name:worker-8"]

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
    "deployment_name:deployment-1",
    "flow_id:f-1",
]

TAGS_F2 = [
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_id:wq-2",
    "work_queue_name:paused-queue",
    "deployment_id:d-2",
    "deployment_name:deployment-2",
    "flow_id:f-2",
]

TAGS_F3 = [
    "work_pool_id:wp-3",
    "work_pool_name:not-ready-pool",
    "work_queue_id:wq-4",
    "work_queue_name:not-ready-queue",
    "deployment_id:d-3",
    "deployment_name:deployment-3",
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
    ("prefect.server.ready", 1.0, [], "ready", 1),
    ("prefect.server.health", 1.0, [], "health", 1),
    # --- work pool metrics ---
    ("prefect.server.work_pool.is_ready", 1, WP1_TAGS, "wp1-is_ready", 1),
    ("prefect.server.work_pool.is_paused", 0, WP1_TAGS, "wp1-is_paused", 1),
    ("prefect.server.work_pool.is_ready", 0, WP2_TAGS, "wp2-is_ready", 1),
    ("prefect.server.work_pool.is_not_ready", 0, WP2_TAGS, "wp2-is_not_ready", 1),
    ("prefect.server.work_pool.is_paused", 1, WP2_TAGS, "wp2-is_paused", 1),
    ("prefect.server.work_pool.is_ready", 0, WP3_TAGS, "wp3-is_ready", 1),
    ("prefect.server.work_pool.is_not_ready", 1, WP3_TAGS, "wp3-is_not_ready", 1),
    ("prefect.server.work_pool.is_paused", 0, WP3_TAGS, "wp3-is_paused", 1),
    # --- worker metrics ---
    ("prefect.server.work_pool.worker.is_online", 1, WP1_WORKER_TAGS, "wp1-worker-is_online", 1),
    ("prefect.server.work_pool.worker.is_online", 0, WP2_WORKER_TAGS, "wp2-worker-is_online", 1),
    ("prefect.server.work_pool.worker.is_online", 0, WP3_WORKER_TAGS, "wp3-worker-is_online", 1),
    ("prefect.server.work_pool.worker.heartbeat_age_seconds", 55.0, WP1_WORKER_TAGS, "wp1-worker-heartbeat_age", 1),
    ("prefect.server.work_pool.worker.heartbeat_age_seconds", 56.544, WP2_WORKER_TAGS, "wp2-worker-heartbeat_age", 1),
    ("prefect.server.work_pool.worker.heartbeat_age_seconds", 0.0, WP3_WORKER_TAGS, "wp3-worker-heartbeat_age", 1),
    # --- work queue basic metrics ---
    ("prefect.server.work_queue.is_ready", 1.0, WQ1_TAGS, "wq1-is_ready", 1),
    ("prefect.server.work_queue.is_not_ready", 0.0, WQ1_TAGS, "wq1-is_not_ready", 1),
    ("prefect.server.work_queue.is_paused", 0.0, WQ1_TAGS, "wq1-is_paused", 1),
    ("prefect.server.work_queue.last_polled_age_seconds", 50.0, WQ1_STATUS_TAGS, "wq1-last_polled", 1),
    ("prefect.server.work_queue.is_ready", 0.0, WQ2_TAGS, "wq2-is_ready", 1),
    ("prefect.server.work_queue.is_not_ready", 0.0, WQ2_TAGS, "wq2-is_not_ready", 1),
    ("prefect.server.work_queue.is_paused", 1.0, WQ2_TAGS, "wq2-is_paused", 1),
    ("prefect.server.work_queue.last_polled_age_seconds", 52.0, WQ2_STATUS_TAGS, "wq2-last_polled", 1),
    ("prefect.server.work_queue.is_ready", 0.0, WQ4_TAGS, "wq4-is_ready", 1),
    ("prefect.server.work_queue.is_not_ready", 1.0, WQ4_TAGS, "wq4-is_not_ready", 1),
    ("prefect.server.work_queue.is_paused", 0.0, WQ4_TAGS, "wq4-is_paused", 1),
    ("prefect.server.work_queue.last_polled_age_seconds", 5.877, WQ4_STATUS_TAGS, "wq4-last_polled", 1),
    ("prefect.server.work_queue.concurrency.in_use", 0.2, WQ1_STATUS_TAGS, "wq1-concurrency_in_use", 1),
    # --- work queue backlog metrics ---
    ("prefect.server.work_queue.backlog.age", 110.0, WQ1_STATUS_TAGS, "wq1-backlog-age", 1),
    ("prefect.server.work_queue.backlog.age", 31.889, WQ2_STATUS_TAGS, "wq2-backlog-age", 1),
    ("prefect.server.work_queue.backlog.age", 0.0, WQ4_STATUS_TAGS, "wq4-backlog-age", 1),
    ("prefect.server.work_queue.backlog.size", 2.0, WQ1_STATUS_TAGS, "wq1-backlog-size", 1),
    ("prefect.server.work_queue.backlog.size", 2.0, WQ2_STATUS_TAGS, "wq2-backlog-size", 1),
    ("prefect.server.work_queue.backlog.size", 0.0, WQ4_STATUS_TAGS, "wq4-backlog-size", 1),
    # --- deployment metrics ---
    (
        "prefect.server.deployment.is_ready",
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
        "prefect.server.deployment.is_ready",
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
    ("prefect.server.flow_runs.pending", 2.0, TAGS_F2, "flow_runs-pending-f2", 1),
    ("prefect.server.flow_runs.scheduled", 1.0, TAGS_F1, "flow_runs-scheduled-f1", 1),
    ("prefect.server.flow_runs.failed.count", 1.0, TAGS_F1, "flow_runs-failed-count-f1", 1),
    ("prefect.server.flow_runs.cancelled.count", 0.0, TAGS_F2, "flow_runs-cancelled-count-f2", 1),
    ("prefect.server.flow_runs.crashed.count", 1.0, TAGS_F1, "flow_runs-crashed-count-f1", 1),
    ("prefect.server.flow_runs.running", 1.0, TAGS_F3, "flow_runs-running-count-f3", 1),
    ("prefect.server.flow_runs.paused", 0.0, TAGS_F1, "flow_runs-paused-f1", 1),
    ("prefect.server.flow_runs.completed.count", 2.0, TAGS_F2, "flow_runs-completed-count-f2", 1),
    ("prefect.server.flow_runs.throughput", 6.0, TAGS_F2, "flow_runs-throughput-f2", 1),
    ("prefect.server.flow_runs.late_start.count", 2.0, TAGS_F2, "flow_runs-late_start-f2", 1),
    ("prefect.server.flow_runs.execution_duration", 10.123, TAGS_F1, "flow_runs-execution-duration-f1", 1),
    ("prefect.server.flow_runs.queue_wait_duration", 5.333, TAGS_F3, "flow_runs-queue-wait-f3", 1),
    ("prefect.server.flow_runs.retry_gaps_duration", 5, TAGS_F1, "flow_runs-retry-gaps-f1", 1),
    # --- task run state counts ---
    ("prefect.server.task_runs.pending", 1.0, TAGS_TR1, "task_runs-pending-tr1", 1),
    ("prefect.server.task_runs.paused", 1.0, TAGS_TR8, "task_runs-paused-tr8", 1),
    ("prefect.server.task_runs.crashed.count", 1.0, TAGS_TR7, "task_runs-crashed-count-tr7", 1),
    ("prefect.server.task_runs.cancelled.count", 2.0, TAGS_TR9, "task_runs-cancelled-count-tr9", 1),
    ("prefect.server.task_runs.completed.count", 2.0, TAGS_TR3, "task_runs-completed-count-tr3", 1),
    ("prefect.server.task_runs.failed.count", 0.0, TAGS_TR3, "task_runs-failed-count-tr3", 1),
    ("prefect.server.task_runs.throughput", 5.0, TAGS_TR1, "task_runs-throughput-tr1", 1),
    ("prefect.server.task_runs.running", 1.0, TAGS_TR1, "task_runs-running-count-tr1", 1),
    ("prefect.server.task_runs.late_start.count", 1.0, TAGS_TR1, "task_runs-late_start-tr1", 1),
    # --- task run metrics ---
    ("prefect.server.task_runs.execution_duration", 5.333, TAGS_TR1, "task_runs-execution-duration-tr1", 2),
    ("prefect.server.task_runs.dependency_wait_duration", 2.0, TAGS_TR2, "task_runs-dependency-wait-duration-tr1", 1),
]


pytestmark = [pytest.mark.usefixtures("mock_http_responses"), pytest.mark.unit]


@pytest.fixture()
def ready_check(check: PrefectCheck, dd_run_check: Callable, aggregator, mocker) -> PrefectCheck:
    mocker.patch("datadog_checks.prefect.check.datetime", MockDatetime)
    mocker.patch.object(check, '_get_last_check_time')

    check.last_check_time_iso = "2026-01-20T15:00:00Z"
    check.last_check_time = datetime(2026, 1, 20, 15, 0, 0, tzinfo=timezone.utc)

    dd_run_check(check)

    return check


def test_metrics_as_in_metadata(ready_check: PrefectCheck, aggregator: AggregatorStub):
    histogram_suffixes = ('.avg', '.max', '.median', '.95percentile')
    metadata_metrics = {k: v for k, v in get_metadata_metrics().items() if not k.endswith(histogram_suffixes)}
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_metric_type=False, check_symmetric_inclusion=True
    )


def _assert_tags(
    aggregator: AggregatorStub, metric_name: str, value: float, tags: list[str], base_tags: list[str], count: int
):
    aggregator.assert_metric(metric_name, value=value, tags=base_tags + tags, count=count)


def test_assert_metrics(ready_check: PrefectCheck, aggregator: AggregatorStub):
    base = ready_check.base_tags

    for metric_name, expected_value, tags, mid, count in ALL_METRIC_CASES:
        try:
            _assert_tags(aggregator, metric_name, expected_value, tags, base, count)
        except AssertionError as e:
            raise AssertionError(
                f"Assertion failed for metric id='{mid}', metric='{metric_name}', tags={base + tags}:\n{e}"
            ) from e

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    "msg_text, exact_match, msg_title, event_type, alert_type",
    [
        pytest.param(
            "flow-run went from Late to Pending\n"
            "Resource ID: fr-completed\nResource Name: fr-completed\nRun count: 1\n",
            True,
            "[PREFECT] [flow-run] fr-completed -> Pending",
            "prefect.flow-run.Pending",
            "info",
            id="flow-run-pending",
        ),
        pytest.param(
            "task-run went from Running to Completed\nResource ID: tr-1\nResource Name: task-1\nRun count: 1\n",
            True,
            "[PREFECT] [task-run] task-1 -> Completed",
            "prefect.task-run.Completed",
            "info",
            id="task-run-completed",
        ),
        pytest.param(
            "worker.process ProcessWorker worker-1 with id worker-1 executed-flow-run\n",
            False,
            "[PREFECT] [worker.process] ProcessWorker worker-1 -> executed-flow-run",
            "prefect.worker.executed-flow-run",
            "info",
            id="worker-executed-flow-run",
        ),
        pytest.param(
            "flow-run went from Running to AwaitingRetry\n"
            "Resource ID: fr-retry\n"
            "Resource Name: fr-retry\n"
            "Run count: 1\n"
            "Message: Retry scheduled\n",
            True,
            "[PREFECT] [flow-run] fr-retry -> AwaitingRetry",
            "prefect.flow-run.AwaitingRetry",
            "error",
            id="flow-run-awaiting-retry",
        ),
        pytest.param(
            "work-pool not-ready-pool with id wp-3 not-ready\n",
            False,
            "[PREFECT] [work-pool] not-ready-pool -> not-ready",
            "prefect.work-pool.not-ready",
            "error",
            id="work-pool-not-ready-error",
        ),
    ],
)
def test_events(
    ready_check: PrefectCheck,
    aggregator: AggregatorStub,
    msg_text: str,
    exact_match: bool,
    msg_title: str,
    event_type: str,
    alert_type: str,
):
    aggregator.assert_event(
        msg_text,
        exact_match=exact_match,
        count=1,
        msg_title=msg_title,
        event_type=event_type,
        alert_type=alert_type,
    )


def test_filter_work_pools(filter_metrics):
    """Test work pool filtering with whitelist/blacklist."""
    work_pools = [
        {"id": "pool1", "name": "production-pool"},
        {"id": "pool2", "name": "production-pool-2"},
        {"id": "pool3", "name": "staging-pool"},
        {"id": "pool4", "name": "dev-pool"},
    ]
    filtered_pools = filter_metrics.filter_work_pools(work_pools)
    assert len(filtered_pools) == 2
    assert all(pool["name"] in ["production-pool", "production-pool-2"] for pool in filtered_pools)

    # Verify cache was populated
    assert filter_metrics.work_pool_cache["production-pool"] is True
    assert filter_metrics.work_pool_cache["production-pool-2"] is True
    assert filter_metrics.work_pool_cache["staging-pool"] is False
    assert filter_metrics.work_pool_cache["dev-pool"] is False


def test_filter_work_queues(filter_metrics):
    """Test work queue filtering (depends on work pool cache)."""
    work_queues = [
        {"id": "queue1", "name": "high-priority", "work_pool_name": "production-pool"},
        {"id": "queue2", "name": "low-priority", "work_pool_name": "production-pool"},
        {"id": "queue3", "name": "high-priority-2", "work_pool_name": "staging-pool"},
    ]
    filtered_queues = filter_metrics.filter_work_queues(work_queues)
    assert len(filtered_queues) == 1
    assert filtered_queues[0]["name"] == "high-priority"

    # Verify cache was populated
    assert filter_metrics.work_queue_cache["high-priority"] is True
    assert filter_metrics.work_queue_cache["low-priority"] is False  # Not whitelisted


def test_filter_deployments(filter_metrics):
    """Test deployment filtering (depends on work pool and work queue caches)."""
    deployments = [
        {
            "id": "dep1",
            "name": "api-deployment",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
        },
        {
            "id": "dep2",
            "name": "worker-deployment",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
        },
        {
            "id": "dep3",
            "name": "api-deployment-2",
            "work_pool_name": "staging-pool",
            "work_queue_name": "high-priority-2",
        },
    ]
    filtered_deployments = filter_metrics.filter_deployments(deployments)
    assert len(filtered_deployments) == 1
    assert filtered_deployments[0]["name"] == "api-deployment"

    # Verify cache was populated
    assert filter_metrics.deployment_cache["api-deployment"] is True
    assert filter_metrics.deployment_cache["worker-deployment"] is False  # Not whitelisted

    # Verify fallback mapping was created
    assert filter_metrics.deployment_fallback.mappings["dep1"] == "api-deployment"
    assert filter_metrics.deployment_fallback.mappings["dep2"] == "worker-deployment"
    assert filter_metrics.deployment_fallback.mappings["dep3"] == "api-deployment-2"


def test_filter_flow_runs(filter_metrics):
    """Test flow run filtering (uses deployment_id fallback to check deployment_name)."""
    # First, populate deployment fallback mappings
    filter_metrics.filter_deployments(
        [
            {
                "id": "dep1",
                "name": "api-deployment",
                "work_pool_name": "production-pool",
                "work_queue_name": "high-priority",
            },
            {
                "id": "dep2",
                "name": "worker-deployment",
                "work_pool_name": "production-pool",
                "work_queue_name": "high-priority",
            },
            {
                "id": "dep3",
                "name": "api-deployment-2",
                "work_pool_name": "staging-pool",
                "work_queue_name": "high-priority-2",
            },
        ]
    )

    flow_runs = [
        {
            "id": "fr1",
            "name": "scheduled-flow",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
            "deployment_id": "dep1",  # Maps to "api-deployment" via fallback
        },
        {
            "id": "fr2",
            "name": "manual-flow",
            "work_pool_name": "staging-pool",
            "work_queue_name": "high-priority-2",
            "deployment_id": "dep1",  # Maps to "api-deployment" via fallback
        },
        {
            "id": "fr3",
            "name": "scheduled-flow-2",
            "work_pool_name": "production-pool",
            "work_queue_name": "low-priority",
            "deployment_id": "dep2",  # Maps to "worker-deployment" via fallback (filtered out)
        },
        {
            "id": "fr4",
            "name": "scheduled-flow-3",
            "work_pool_name": "staging-pool",
            "work_queue_name": "high-priority-2",
            "deployment_id": "dep3",  # Maps to "api-deployment-2" via fallback (filtered out)
        },
    ]
    filtered_flow_runs = filter_metrics.filter_flow_runs(flow_runs)
    assert len(filtered_flow_runs) == 1
    assert filtered_flow_runs[0]["name"] == "scheduled-flow"

    # Verify that the flow run to fallback mappings were created properly
    assert filter_metrics.flow_run_to_deployment_fallback.mappings["fr1"] == "api-deployment"
    assert filter_metrics.flow_run_to_deployment_fallback.mappings["fr2"] == "api-deployment"
    assert filter_metrics.flow_run_to_deployment_fallback.mappings["fr3"] == "worker-deployment"

    # Verify work pool and work queue fallback mappings
    assert filter_metrics.flow_run_to_work_pool_fallback.mappings["fr1"] == "production-pool"
    assert filter_metrics.flow_run_to_work_pool_fallback.mappings["fr2"] == "staging-pool"
    assert filter_metrics.flow_run_to_work_pool_fallback.mappings["fr3"] == "production-pool"
    assert filter_metrics.flow_run_to_work_pool_fallback.mappings["fr4"] == "staging-pool"

    assert filter_metrics.flow_run_to_queue_fallback.mappings["fr1"] == "high-priority"
    assert filter_metrics.flow_run_to_queue_fallback.mappings["fr2"] == "high-priority-2"
    assert filter_metrics.flow_run_to_queue_fallback.mappings["fr3"] == "low-priority"
    assert filter_metrics.flow_run_to_queue_fallback.mappings["fr4"] == "high-priority-2"


def test_filter_task_runs(filter_metrics):
    """Test task run filtering (uses flow_run_id fallback to check flow_run_cache)."""
    # First, populate flow run cache and fallback mappings
    filter_metrics.filter_deployments(
        [
            {
                "id": "dep1",
                "name": "api-deployment",
                "work_pool_name": "production-pool",
                "work_queue_name": "high-priority",
            },
            {
                "id": "dep2",
                "name": "worker-deployment",
                "work_pool_name": "production-pool",
                "work_queue_name": "high-priority",
            },
        ]
    )

    flow_runs = [
        {
            "id": "fr1",
            "name": "scheduled-flow",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
            "deployment_id": "dep1",
        },
        {
            "id": "fr2",
            "name": "manual-flow",
            "work_pool_name": "staging-pool",
            "work_queue_name": "high-priority-2",
            "deployment_id": "dep1",
        },
        {
            "id": "fr3",
            "name": "scheduled-flow-2",
            "work_pool_name": "production-pool",
            "work_queue_name": "low-priority",
            "deployment_id": "dep2",
        },
        {
            "id": "fr4",
            "name": "scheduled-flow-3",
            "work_pool_name": "staging-pool",
            "work_queue_name": "high-priority-2",
            "deployment_id": "dep3",
        },
    ]
    filter_metrics.filter_flow_runs(flow_runs)

    task_runs = [
        {"id": "tr1", "flow_run_id": "fr1"},
        {"id": "tr2", "flow_run_id": "fr2"},
        {"id": "tr3", "flow_run_id": "fr3"},
        {"id": "tr4", "flow_run_id": "fr4"},
    ]
    filtered_task_runs = filter_metrics.filter_task_runs(task_runs)
    assert len(filtered_task_runs) == 1
    assert filtered_task_runs[0]["id"] == "tr1"


def test_filter_metrics_no_rules_configured(check):
    """Test that when no filter rules are configured, everything is included."""
    filter_metrics = PrefectFilterMetrics(log=check.log)

    # Test work pools - all should be included
    work_pools = [
        {"id": "pool1", "name": "production-pool"},
        {"id": "pool2", "name": "staging-pool"},
        {"id": "pool3", "name": "dev-pool"},
    ]
    filtered_pools = filter_metrics.filter_work_pools(work_pools)
    assert len(filtered_pools) == 3

    # Test work queues - all should be included
    work_queues = [
        {"id": "queue1", "name": "high-priority", "work_pool_name": "production-pool"},
        {"id": "queue2", "name": "low-priority", "work_pool_name": "production-pool"},
    ]
    filtered_queues = filter_metrics.filter_work_queues(work_queues)
    assert len(filtered_queues) == 2

    # Test deployments - all should be included
    deployments = [
        {
            "id": "dep1",
            "name": "api-deployment",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
        },
        {
            "id": "dep2",
            "name": "worker-deployment",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
        },
    ]
    filtered_deployments = filter_metrics.filter_deployments(deployments)
    assert len(filtered_deployments) == 2

    # Test flow runs - all should be included
    filter_metrics.filter_deployments(deployments)  # Populate deployment fallback
    flow_runs = [
        {
            "id": "fr1",
            "name": "scheduled-flow",
            "work_pool_name": "production-pool",
            "work_queue_name": "high-priority",
            "deployment_id": "dep1",
        },
        {
            "id": "fr2",
            "name": "manual-flow",
            "work_pool_name": "staging-pool",
            "work_queue_name": "low-priority",
            "deployment_id": "dep2",
        },
    ]
    filtered_flow_runs = filter_metrics.filter_flow_runs(flow_runs)
    assert len(filtered_flow_runs) == 2

    # Test task runs - all should be included
    filter_metrics.filter_flow_runs(flow_runs)  # Populate flow run cache
    task_runs = [
        {"id": "tr1", "flow_run_id": "fr1"},
        {"id": "tr2", "flow_run_id": "fr2"},
    ]
    filtered_task_runs = filter_metrics.filter_task_runs(task_runs)
    assert len(filtered_task_runs) == 2


@pytest.fixture
def filter_metrics(check):
    """Fixture to initialize PrefectFilterMetrics with standard rules and pre-populated caches."""
    f = PrefectFilterMetrics(
        log=check.log,
        work_pool_names={"include": ["^production-"], "exclude": ["^staging-"]},
        work_queue_names={"include": ["^high-"]},
        deployment_names={"include": ["^api-"], "exclude": ["^worker-"]},
        event_names={
            "include": [r"^prefect\.flow-run\.", r"^prefect\.task-run\."],
            "exclude": [r"^prefect\.flow-run\.Failed"],
        },
    )

    # Pre-populate caches
    f.filter_work_pools([{"id": "wp1", "name": "production-pool"}])
    f.filter_work_pools([{"id": "wp2", "name": "staging-pool"}])
    f.filter_work_queues(
        [
            {"id": "wq1", "name": "high-priority", "work_pool_name": "production-pool"},
            {"id": "wq2", "name": "low-priority", "work_pool_name": "production-pool"},
        ]
    )
    f.filter_deployments(
        [
            {
                "id": "dep1",
                "name": "api-deployment",
                "work_pool_name": "production-pool",
                "work_queue_name": "high-priority",
            },
            {
                "id": "dep2",
                "name": "worker-deployment",
                "work_pool_name": "production-pool",
                "work_queue_name": "high-priority",
            },
        ]
    )
    return f


@pytest.mark.parametrize(
    "event_data, expected_included, description",
    [
        # 1. Basic event type filtering
        ({"id": "e1", "event": "prefect.flow-run.Completed"}, True, "Included event type"),
        ({"id": "e3", "event": "prefect.flow-run.Failed"}, False, "Excluded event type (failed)"),
        # 2. Work Pool filtering
        (
            {
                "id": "e4",
                "event": "prefect.flow-run.Completed",
                "related": [{"role": "work-pool", "id": "prefect.work-pool.wp1", "name": "production-pool"}],
            },
            True,
            "Included work pool",
        ),
        (
            {
                "id": "e5",
                "event": "prefect.flow-run.Completed",
                "related": [{"role": "work-pool", "id": "prefect.work-pool.wp2", "name": "staging-pool"}],
            },
            False,
            "Excluded work pool",
        ),
        # 3. Work Queue filtering
        (
            {
                "id": "e6",
                "event": "prefect.flow-run.Completed",
                "related": [
                    {"role": "work-pool", "id": "prefect.work-pool.wp1", "name": "production-pool"},
                    {"role": "work-queue", "id": "prefect.work-queue.wq1", "name": "high-priority"},
                ],
            },
            True,
            "Included work queue",
        ),
        (
            {
                "id": "e7",
                "event": "prefect.flow-run.Completed",
                "related": [
                    {"role": "work-pool", "id": "prefect.work-pool.wp1", "name": "production-pool"},
                    {"role": "work-queue", "id": "prefect.work-queue.wq2", "name": "low-priority"},
                ],
            },
            False,
            "Excluded work queue",
        ),
        # 4. Deployment filtering
        (
            {
                "id": "e8",
                "event": "prefect.flow-run.Completed",
                "related": [
                    {"role": "work-pool", "id": "prefect.work-pool.wp1", "name": "production-pool"},
                    {"role": "work-queue", "id": "prefect.work-queue.wq1", "name": "high-priority"},
                    {"role": "deployment", "id": "prefect.deployment.dep1", "name": "api-deployment"},
                ],
            },
            True,
            "Included deployment",
        ),
        (
            {
                "id": "e9",
                "event": "prefect.flow-run.Completed",
                "related": [
                    {"role": "work-pool", "id": "prefect.work-pool.wp1", "name": "production-pool"},
                    {"role": "work-queue", "id": "prefect.work-queue.wq1", "name": "high-priority"},
                    {"role": "deployment", "id": "prefect.deployment.dep2", "name": "worker-deployment"},
                ],
            },
            False,
            "Excluded deployment",
        ),
    ],
)
def test_filter_events(filter_metrics, event_data, expected_included, description):
    payload = {
        "occurred": "2026-01-20T15:00:00.000000Z",
        "id": event_data["id"],
        "event": event_data["event"],
        "resource": {"prefect.resource.id": f"prefect.flow-run.{event_data['id']}"},
    }

    if "related" in event_data:
        payload["related"] = [
            {
                "prefect.resource.role": r["role"],
                "prefect.resource.id": r["id"],
                "prefect.resource.name": r["name"],
            }
            for r in event_data["related"]
        ]

    event = Event(payload)

    assert filter_metrics.is_event_included(event) is expected_included
