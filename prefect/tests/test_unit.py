from datetime import datetime, timezone
from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.prefect import PrefectCheck
from datadog_checks.prefect.event_manager import EventManager
from datadog_checks.prefect.filter_metrics import PrefectFilterMetrics
from tests.helpers import MockDatetime

from .fixtures.metrics import ALL_METRIC_CASES

pytestmark = [pytest.mark.usefixtures("mock_http_responses"), pytest.mark.unit]


@pytest.fixture()
def ready_check(check: PrefectCheck, dd_run_check: Callable, aggregator, mocker) -> PrefectCheck:
    mocker.patch("datadog_checks.prefect.check.datetime", MockDatetime)

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
            "[flow-run] fr-completed -> Pending",
            "prefect.flow-run.Pending",
            "info",
            id="flow-run-pending",
        ),
        pytest.param(
            "task-run went from Running to Completed\nResource ID: tr-1\nResource Name: task-1\nRun count: 1\n",
            True,
            "[task-run] task-1 -> Completed",
            "prefect.task-run.Completed",
            "info",
            id="task-run-completed",
        ),
        pytest.param(
            "worker.process ProcessWorker worker-1 with id worker-1 executed-flow-run\n",
            False,
            "[worker.process] ProcessWorker worker-1 -> executed-flow-run",
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
            "[flow-run] fr-retry -> AwaitingRetry",
            "prefect.flow-run.AwaitingRetry",
            "info",
            id="flow-run-awaiting-retry",
        ),
        pytest.param(
            "work-pool not-ready-pool with id wp-3 not-ready\n",
            False,
            "[work-pool] not-ready-pool -> not-ready",
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


def test_filter_metrics():
    """
    1. Work pool filtering with whitelist/blacklist
    2. Work queue filtering (depends on work pools)
    3. Deployment filtering (depends on work pools and work queues)
    4. Flow run filtering (depends on work pools, work queues, deployments via fallback)
    5. Task run filtering (depends on flow runs via fallback)
    """
    # Create filter instance with all filters configured
    filter_metrics = PrefectFilterMetrics(
        work_pool_names={"include": ["^production-", "^staging-"], "exclude": ["^staging-"]},
        work_queue_names={"include": ["^high-"]},
        deployment_names={"include": ["^api-", "^worker-"], "exclude": ["^worker-"]},
    )

    # 1. Test work pool filtering
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

    # 2. Test work queue filtering (depends on work pool cache)
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

    # 3. Test deployment filtering (depends on work pool and work queue caches)
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

    # 4. Test flow run filtering (uses deployment_id fallback to check deployment_name)
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

    # Verify that the three flow run to fallback mappings were created properly
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

    # 5. Test task run filtering (uses flow_name fallback to check flow_run_cache)
    task_runs = [
        {"id": "tr1", "flow_run_id": "fr1"},
        {"id": "tr2", "flow_run_id": "fr2"},
        {"id": "tr3", "flow_run_id": "fr3"},
        {"id": "tr4", "flow_run_id": "fr4"},
    ]
    filtered_task_runs = filter_metrics.filter_task_runs(task_runs)
    assert len(filtered_task_runs) == 1
    assert filtered_task_runs[0]["id"] == "tr1"


@pytest.fixture
def filter_metrics():
    """Fixture to initialize PrefectFilterMetrics with standard rules and pre-populated caches."""
    f = PrefectFilterMetrics(
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

    event = EventManager(payload)

    assert filter_metrics.is_event_included(event) is expected_included
