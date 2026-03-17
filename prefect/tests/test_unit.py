from datetime import datetime, timezone
from typing import Callable, NamedTuple

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.prefect import PrefectCheck

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

NI_WP_TAGS = ["work_pool_id:wp-4", "work_pool_name:not_included_pool", "work_pool_type:process"]
NI_WORKER_TAGS = ["work_pool_id:wp-4", "work_pool_name:not_included_pool", "worker_id:w-9", "worker_name:worker-9"]
NI_WQ_TAGS = [
    "work_queue_id:wq-5",
    "work_queue_name:not-included-queue",
    "work_pool_id:wp-4",
    "work_pool_name:not_included_pool",
    "work_queue_priority:1",
]
NI_DEPLOY_TAGS = [
    "deployment_id:d-5",
    "deployment_name:deployment-5",
    "flow_id:f-5",
    "work_pool_name:not_included_pool",
    "work_pool_id:wp-4",
    "work_queue_name:not-included-queue",
    "work_queue_id:wq-5",
    "is_paused:False",
]
NI_FLOW_TAGS = [
    "work_pool_id:wp-4",
    "work_pool_name:not_included_pool",
    "work_queue_id:wq-5",
    "work_queue_name:not-included-queue",
    "deployment_id:d-5",
    "deployment_name:deployment-5",
    "flow_id:f-5",
]
NI_TASK_TAGS = NI_FLOW_TAGS + ["task_key:task-ni"]

NIQ_WQ_TAGS = [
    "work_queue_id:wq-6",
    "work_queue_name:not_included_queue",
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_priority:2",
]
NIQ_DEPLOY_TAGS = [
    "deployment_id:d-6",
    "deployment_name:deployment-6",
    "flow_id:f-6",
    "work_pool_name:default-pool",
    "work_pool_id:wp-1",
    "work_queue_name:not_included_queue",
    "work_queue_id:wq-6",
    "is_paused:False",
]
NIQ_FLOW_TAGS = [
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_id:wq-6",
    "work_queue_name:not_included_queue",
    "deployment_id:d-6",
    "deployment_name:deployment-6",
    "flow_id:f-6",
]
NIQ_TASK_TAGS = NIQ_FLOW_TAGS + ["task_key:task-niq"]

NID_DEPLOY_TAGS = [
    "deployment_id:d-7",
    "deployment_name:not_included_deployment",
    "flow_id:f-7",
    "work_pool_name:default-pool",
    "work_pool_id:wp-1",
    "work_queue_name:default-queue",
    "work_queue_id:wq-1",
    "is_paused:False",
]
NID_FLOW_TAGS = [
    "work_pool_id:wp-1",
    "work_pool_name:default-pool",
    "work_queue_id:wq-1",
    "work_queue_name:default-queue",
    "deployment_id:d-7",
    "deployment_name:not_included_deployment",
    "flow_id:f-7",
]
NID_TASK_TAGS = NID_FLOW_TAGS + ["task_key:task-nid"]


class MetricCase(NamedTuple):
    name: str
    value: float
    tags: list[str]
    mid: str
    expected_count: int


class ExcludedMetricCase(NamedTuple):
    name: str
    tags: list[str]
    mid: str


class ExcludedEventCase(NamedTuple):
    msg_title: str
    mid: str


NOT_INCLUDED_METRICS = [
    # --- excluded by work_pool_names ---
    ExcludedMetricCase(name="prefect.server.work_pool.is_ready", tags=NI_WP_TAGS, mid="ni-wp-is_ready"),
    ExcludedMetricCase(
        name="prefect.server.work_pool.worker.is_online", tags=NI_WORKER_TAGS, mid="ni-worker-is_online"
    ),
    ExcludedMetricCase(name="prefect.server.work_queue.is_ready", tags=NI_WQ_TAGS, mid="ni-wq-is_ready"),
    ExcludedMetricCase(name="prefect.server.deployment.is_ready", tags=NI_DEPLOY_TAGS, mid="ni-deploy-is_ready"),
    ExcludedMetricCase(
        name="prefect.server.flow_runs.completed.count", tags=NI_FLOW_TAGS, mid="ni-flow_runs-completed"
    ),
    ExcludedMetricCase(
        name="prefect.server.task_runs.completed.count", tags=NI_TASK_TAGS, mid="ni-task_runs-completed"
    ),
    # --- excluded by work_queue_names ---
    ExcludedMetricCase(name="prefect.server.work_queue.is_ready", tags=NIQ_WQ_TAGS, mid="niq-wq-is_ready"),
    ExcludedMetricCase(name="prefect.server.deployment.is_ready", tags=NIQ_DEPLOY_TAGS, mid="niq-deploy-is_ready"),
    ExcludedMetricCase(
        name="prefect.server.flow_runs.completed.count", tags=NIQ_FLOW_TAGS, mid="niq-flow_runs-completed"
    ),
    ExcludedMetricCase(
        name="prefect.server.task_runs.completed.count", tags=NIQ_TASK_TAGS, mid="niq-task_runs-completed"
    ),
    # --- excluded by deployment_names ---
    ExcludedMetricCase(name="prefect.server.deployment.is_ready", tags=NID_DEPLOY_TAGS, mid="nid-deploy-is_ready"),
    ExcludedMetricCase(
        name="prefect.server.flow_runs.completed.count", tags=NID_FLOW_TAGS, mid="nid-flow_runs-completed"
    ),
    ExcludedMetricCase(
        name="prefect.server.task_runs.completed.count", tags=NID_TASK_TAGS, mid="nid-task_runs-completed"
    ),
]

ALL_METRIC_CASES = [
    # --- api status metrics ---
    MetricCase(name="prefect.server.ready", value=1.0, tags=[], mid="ready", expected_count=1),
    MetricCase(name="prefect.server.health", value=1.0, tags=[], mid="health", expected_count=1),
    # --- work pool metrics ---
    MetricCase(name="prefect.server.work_pool.is_ready", value=1, tags=WP1_TAGS, mid="wp1-is_ready", expected_count=1),
    MetricCase(
        name="prefect.server.work_pool.is_paused", value=0, tags=WP1_TAGS, mid="wp1-is_paused", expected_count=1
    ),
    MetricCase(name="prefect.server.work_pool.is_ready", value=0, tags=WP2_TAGS, mid="wp2-is_ready", expected_count=1),
    MetricCase(
        name="prefect.server.work_pool.is_not_ready", value=0, tags=WP2_TAGS, mid="wp2-is_not_ready", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_pool.is_paused", value=1, tags=WP2_TAGS, mid="wp2-is_paused", expected_count=1
    ),
    MetricCase(name="prefect.server.work_pool.is_ready", value=0, tags=WP3_TAGS, mid="wp3-is_ready", expected_count=1),
    MetricCase(
        name="prefect.server.work_pool.is_not_ready", value=1, tags=WP3_TAGS, mid="wp3-is_not_ready", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_pool.is_paused", value=0, tags=WP3_TAGS, mid="wp3-is_paused", expected_count=1
    ),
    # --- worker metrics ---
    MetricCase(
        name="prefect.server.work_pool.worker.is_online",
        value=1,
        tags=WP1_WORKER_TAGS,
        mid="wp1-worker-is_online",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_pool.worker.is_online",
        value=0,
        tags=WP2_WORKER_TAGS,
        mid="wp2-worker-is_online",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_pool.worker.is_online",
        value=0,
        tags=WP3_WORKER_TAGS,
        mid="wp3-worker-is_online",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_pool.worker.heartbeat_age_seconds",
        value=55.0,
        tags=WP1_WORKER_TAGS,
        mid="wp1-worker-heartbeat_age",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_pool.worker.heartbeat_age_seconds",
        value=56.544,
        tags=WP2_WORKER_TAGS,
        mid="wp2-worker-heartbeat_age",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_pool.worker.heartbeat_age_seconds",
        value=0.0,
        tags=WP3_WORKER_TAGS,
        mid="wp3-worker-heartbeat_age",
        expected_count=1,
    ),
    # --- work queue basic metrics ---
    MetricCase(
        name="prefect.server.work_queue.is_ready", value=1.0, tags=WQ1_TAGS, mid="wq1-is_ready", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_queue.is_not_ready",
        value=0.0,
        tags=WQ1_TAGS,
        mid="wq1-is_not_ready",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.is_paused", value=0.0, tags=WQ1_TAGS, mid="wq1-is_paused", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_queue.last_polled_age_seconds",
        value=50.0,
        tags=WQ1_STATUS_TAGS,
        mid="wq1-last_polled",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.is_ready", value=0.0, tags=WQ2_TAGS, mid="wq2-is_ready", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_queue.is_not_ready",
        value=0.0,
        tags=WQ2_TAGS,
        mid="wq2-is_not_ready",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.is_paused", value=1.0, tags=WQ2_TAGS, mid="wq2-is_paused", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_queue.last_polled_age_seconds",
        value=52.0,
        tags=WQ2_STATUS_TAGS,
        mid="wq2-last_polled",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.is_ready", value=0.0, tags=WQ4_TAGS, mid="wq4-is_ready", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_queue.is_not_ready",
        value=1.0,
        tags=WQ4_TAGS,
        mid="wq4-is_not_ready",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.is_paused", value=0.0, tags=WQ4_TAGS, mid="wq4-is_paused", expected_count=1
    ),
    MetricCase(
        name="prefect.server.work_queue.last_polled_age_seconds",
        value=5.877,
        tags=WQ4_STATUS_TAGS,
        mid="wq4-last_polled",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.concurrency.in_use",
        value=0.2,
        tags=WQ1_STATUS_TAGS,
        mid="wq1-concurrency_in_use",
        expected_count=1,
    ),
    # --- work queue backlog metrics ---
    MetricCase(
        name="prefect.server.work_queue.backlog.age",
        value=110.0,
        tags=WQ1_STATUS_TAGS,
        mid="wq1-backlog-age",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.backlog.age",
        value=31.889,
        tags=WQ2_STATUS_TAGS,
        mid="wq2-backlog-age",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.backlog.age",
        value=0.0,
        tags=WQ4_STATUS_TAGS,
        mid="wq4-backlog-age",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.backlog.size",
        value=2.0,
        tags=WQ1_STATUS_TAGS,
        mid="wq1-backlog-size",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.backlog.size",
        value=2.0,
        tags=WQ2_STATUS_TAGS,
        mid="wq2-backlog-size",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.work_queue.backlog.size",
        value=0.0,
        tags=WQ4_STATUS_TAGS,
        mid="wq4-backlog-size",
        expected_count=1,
    ),
    # --- deployment metrics ---
    MetricCase(
        name="prefect.server.deployment.is_ready",
        value=1.0,
        tags=[
            "deployment_id:d-1",
            "deployment_name:deployment-1",
            "flow_id:f-1",
            "work_pool_name:default-pool",
            "work_pool_id:wp-1",
            "work_queue_name:default-queue",
            "work_queue_id:wq-1",
            "is_paused:False",
        ],
        mid="deployment-d1-is_ready",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.deployment.is_ready",
        value=0.0,
        tags=[
            "deployment_id:d-2",
            "deployment_name:deployment-2",
            "flow_id:f-2",
            "work_pool_name:paused-pool",
            "work_pool_id:wp-2",
            "work_queue_name:queue-paused-pool",
            "work_queue_id:wq-3",
            "is_paused:True",
        ],
        mid="deployment-d2-is_not_ready",
        expected_count=1,
    ),
    # --- flow run state counts ---
    MetricCase(
        name="prefect.server.flow_runs.pending", value=2.0, tags=TAGS_F2, mid="flow_runs-pending-f2", expected_count=1
    ),
    MetricCase(
        name="prefect.server.flow_runs.scheduled",
        value=1.0,
        tags=TAGS_F1,
        mid="flow_runs-scheduled-f1",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.failed.count",
        value=1.0,
        tags=TAGS_F1,
        mid="flow_runs-failed-count-f1",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.cancelled.count",
        value=0.0,
        tags=TAGS_F2,
        mid="flow_runs-cancelled-count-f2",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.crashed.count",
        value=1.0,
        tags=TAGS_F1,
        mid="flow_runs-crashed-count-f1",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.running",
        value=1.0,
        tags=TAGS_F3,
        mid="flow_runs-running-count-f3",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.paused", value=0.0, tags=TAGS_F1, mid="flow_runs-paused-f1", expected_count=1
    ),
    MetricCase(
        name="prefect.server.flow_runs.completed.count",
        value=2.0,
        tags=TAGS_F2,
        mid="flow_runs-completed-count-f2",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.throughput",
        value=6.0,
        tags=TAGS_F2,
        mid="flow_runs-throughput-f2",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.late_start.count",
        value=2.0,
        tags=TAGS_F2,
        mid="flow_runs-late_start-f2",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.execution_duration",
        value=10.123,
        tags=TAGS_F1,
        mid="flow_runs-execution-duration-f1",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.queue_wait_duration",
        value=5.333,
        tags=TAGS_F3,
        mid="flow_runs-queue-wait-f3",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.flow_runs.retry_gaps_duration",
        value=5,
        tags=TAGS_F1,
        mid="flow_runs-retry-gaps-f1",
        expected_count=1,
    ),
    # --- task run state counts ---
    MetricCase(
        name="prefect.server.task_runs.pending", value=1.0, tags=TAGS_TR1, mid="task_runs-pending-tr1", expected_count=1
    ),
    MetricCase(
        name="prefect.server.task_runs.paused", value=1.0, tags=TAGS_TR8, mid="task_runs-paused-tr8", expected_count=1
    ),
    MetricCase(
        name="prefect.server.task_runs.crashed.count",
        value=1.0,
        tags=TAGS_TR7,
        mid="task_runs-crashed-count-tr7",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.task_runs.cancelled.count",
        value=2.0,
        tags=TAGS_TR9,
        mid="task_runs-cancelled-count-tr9",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.task_runs.completed.count",
        value=2.0,
        tags=TAGS_TR3,
        mid="task_runs-completed-count-tr3",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.task_runs.failed.count",
        value=0.0,
        tags=TAGS_TR3,
        mid="task_runs-failed-count-tr3",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.task_runs.throughput",
        value=5.0,
        tags=TAGS_TR1,
        mid="task_runs-throughput-tr1",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.task_runs.running",
        value=1.0,
        tags=TAGS_TR1,
        mid="task_runs-running-count-tr1",
        expected_count=1,
    ),
    MetricCase(
        name="prefect.server.task_runs.late_start.count",
        value=1.0,
        tags=TAGS_TR1,
        mid="task_runs-late_start-tr1",
        expected_count=1,
    ),
    # --- task run metrics ---
    MetricCase(
        name="prefect.server.task_runs.execution_duration",
        value=5.333,
        tags=TAGS_TR1,
        mid="task_runs-execution-duration-tr1",
        expected_count=2,
    ),
    MetricCase(
        name="prefect.server.task_runs.dependency_wait_duration",
        value=2.0,
        tags=TAGS_TR2,
        mid="task_runs-dependency-wait-duration-tr1",
        expected_count=1,
    ),
]


NOT_INCLUDED_EVENTS = [
    ExcludedEventCase(msg_title="[PREFECT] [flow-run] fr-ni-completed -> Completed", mid="ni-evt-excluded-pool"),
    ExcludedEventCase(msg_title="[PREFECT] [flow-run] fr-niq-completed -> Completed", mid="niq-evt-excluded-queue"),
    ExcludedEventCase(msg_title="[PREFECT] [flow-run] fr-nid-completed -> Completed", mid="nid-evt-excluded-deploy"),
    ExcludedEventCase(
        msg_title="[PREFECT] [worker.process] ProcessWorker worker-1 -> executed-flow-run",
        mid="ni-evt-excluded-event-name",
    ),
]


class EventCase(NamedTuple):
    msg_text: str
    exact_match: bool
    msg_title: str
    event_type: str
    alert_type: str


pytestmark = [pytest.mark.usefixtures("mock_prefect_client"), pytest.mark.unit]


@pytest.fixture()
def ready_check(check: PrefectCheck, dd_run_check: Callable, aggregator, mocker) -> PrefectCheck:
    mocker.patch(
        "datadog_checks.prefect.check._utcnow", return_value=datetime(2026, 1, 20, 15, 2, 0, tzinfo=timezone.utc)
    )
    mocker.patch.object(check, '_get_last_check_time')

    reset_check_time(check)

    dd_run_check(check)

    return check


def reset_check_time(check: PrefectCheck):
    check.last_check_time_iso = "2026-01-20T15:00:00Z"
    check.last_check_time = datetime(2026, 1, 20, 15, 0, 0, tzinfo=timezone.utc)


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

    for m in ALL_METRIC_CASES:
        try:
            _assert_tags(aggregator, m.name, m.value, m.tags, base, m.expected_count)
        except AssertionError as e:
            raise AssertionError(
                f"Assertion failed for metric id='{m.mid}', metric='{m.name}', tags={base + m.tags}:\n{e}"
            ) from e

    for em in NOT_INCLUDED_METRICS:
        try:
            aggregator.assert_metric(em.name, tags=base + em.tags, count=0)
        except AssertionError as e:
            raise AssertionError(
                f"Excluded metric was emitted: id='{em.mid}', metric='{em.name}', tags={base + em.tags}:\n{e}"
            ) from e

    aggregator.assert_all_metrics_covered()


ALL_EVENT_CASES = [
    EventCase(
        msg_text="flow-run went from Late to Pending\n"
        "Resource ID: fr-completed\nResource Name: fr-completed\nRun count: 1\n",
        exact_match=True,
        msg_title="[PREFECT] [flow-run] fr-completed -> Pending",
        event_type="prefect.flow-run.Pending",
        alert_type="info",
    ),
    EventCase(
        msg_text="task-run went from Running to Completed\nResource ID: tr-1\nResource Name: task-1\nRun count: 1\n",
        exact_match=True,
        msg_title="[PREFECT] [task-run] task-1 -> Completed",
        event_type="prefect.task-run.Completed",
        alert_type="info",
    ),
    EventCase(
        msg_text="flow-run went from Running to AwaitingRetry\n"
        "Resource ID: fr-retry\n"
        "Resource Name: fr-retry\n"
        "Run count: 1\n"
        "Message: Retry scheduled\n",
        exact_match=True,
        msg_title="[PREFECT] [flow-run] fr-retry -> AwaitingRetry",
        event_type="prefect.flow-run.AwaitingRetry",
        alert_type="error",
    ),
    EventCase(
        msg_text="work-pool not-ready-pool with id wp-3 not-ready\n",
        exact_match=False,
        msg_title="[PREFECT] [work-pool] not-ready-pool -> not-ready",
        event_type="prefect.work-pool.not-ready",
        alert_type="error",
    ),
]


def test_events(ready_check: PrefectCheck, aggregator: AggregatorStub):
    for e in ALL_EVENT_CASES:
        try:
            aggregator.assert_event(
                e.msg_text,
                exact_match=e.exact_match,
                count=1,
                msg_title=e.msg_title,
                event_type=e.event_type,
                alert_type=e.alert_type,
            )
        except AssertionError as err:
            raise AssertionError(f"Assertion failed for event msg_title='{e.msg_title}':\n{err}") from err

    for ee in NOT_INCLUDED_EVENTS:
        try:
            aggregator.assert_event(ee.msg_title, msg_title=ee.msg_title, count=0)
        except AssertionError as err:
            raise AssertionError(
                f"Excluded event was emitted: id='{ee.mid}', msg_title='{ee.msg_title}':\n{err}"
            ) from err
