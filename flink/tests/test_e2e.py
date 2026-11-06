# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_all_discovery_candidates_stable
from datadog_checks.flink import FlinkCheck

pytestmark = [pytest.mark.e2e]

# Flink logs a harmless startup notice ("Hadoop FS is not available ...: NoClassDefFoundError")
# with the vanilla `flink` image. Exclude only that known-benign substring so a real error is
# still caught.
DISCOVERY_STABILITY_LOG_PATTERNS = tuple(
    pattern if pattern != r'error' else r'(?<!NoClassDefFound)error' for pattern in CONTAINER_STABILITY_LOG_PATTERNS
)

# Core metrics that should be present on a freshly-started JobManager,
# regardless of whether any Flink job has been submitted. JVM and cluster
# metrics are reported as soon as the reporter starts.
EXPECTED_CORE_METRICS = [
    "flink.jobmanager.Status.JVM.CPU.Load",
    "flink.jobmanager.Status.JVM.Memory.Heap.Used",
    "flink.jobmanager.Status.JVM.Memory.Heap.Max",
    "flink.jobmanager.Status.JVM.Threads.Count",
    "flink.jobmanager.numRegisteredTaskManagers",
    "flink.jobmanager.numRunningJobs",
    "flink.jobmanager.taskSlotsTotal",
]

# Core metrics that should be present on a freshly-started TaskManager, mirroring
# EXPECTED_CORE_METRICS above but for the other role sharing the same container image.
EXPECTED_TASKMANAGER_CORE_METRICS = [
    "flink.taskmanager.Status.JVM.CPU.Load",
    "flink.taskmanager.Status.JVM.Memory.Heap.Used",
    "flink.taskmanager.Status.JVM.Threads.Count",
]

# Task/operator-scope metrics only exist once a job is running (see the
# StateMachineExample.jar submission in conftest.py's dd_environment). This exercises
# tag extraction (job_name, task_name, operator_name, subtask_index) and metric naming
# against real Flink-emitted data, not the hand-written fixture in tests/fixtures/metrics.txt.
# Counter-vs-gauge submission type (COUNTER_METRICS in metrics.py/check.py) is deliberately
# NOT re-verified here: the real Agent's MonotonicCount sender computes a rate internally
# and the e2e replay JSON reports the result as `gauge` regardless -- no e2e test in this
# repo asserts MONOTONIC_COUNT for exactly that reason. That distinction is the unit test's job.
EXPECTED_TASK_METRICS = [
    "flink.task.numRecordsIn",
    "flink.task.currentInputWatermark",
]
EXPECTED_OPERATOR_METRICS = [
    "flink.operator.numRecordsIn",
    "flink.operator.currentOutputWatermark",
]


def test_e2e_jobmanager_metrics(dd_agent_check, dd_environment):
    aggregator = dd_agent_check(dd_environment, rate=True)
    for metric in EXPECTED_CORE_METRICS:
        aggregator.assert_metric(metric, at_least=1)
    aggregator.assert_service_check('flink.openmetrics.health', FlinkCheck.OK)


def test_e2e_discovery(dd_agent_check_discovery):
    # Both the jobmanager and taskmanager containers share the same `flink` image, so
    # Autodiscovery finds and configures one instance per container. Task/operator-scope
    # metrics are only exposed by the TaskManager's own endpoint (not the JobManager's),
    # so this discovery-based check -- not test_e2e_jobmanager_metrics -- is what can see them.
    aggregator = dd_agent_check_discovery(rate=True, discovery_min_instances=2)

    for metric in EXPECTED_CORE_METRICS:
        aggregator.assert_metric(metric, at_least=1)
    for metric in EXPECTED_TASKMANAGER_CORE_METRICS:
        aggregator.assert_metric(metric, at_least=1)
    for metric in EXPECTED_TASK_METRICS + EXPECTED_OPERATOR_METRICS:
        aggregator.assert_metric(metric, at_least=1)
    aggregator.assert_service_check('flink.openmetrics.health', FlinkCheck.OK)


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(
        dd_agent_check, FlinkCheck, compose_service='jobmanager', log_patterns=DISCOVERY_STABILITY_LOG_PATTERNS
    )
