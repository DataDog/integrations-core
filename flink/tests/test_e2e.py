# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.flink import FlinkCheck

pytestmark = [pytest.mark.e2e]

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


def test_e2e_jobmanager_metrics(dd_agent_check, dd_environment):
    aggregator = dd_agent_check(dd_environment, rate=True)
    for metric in EXPECTED_CORE_METRICS:
        aggregator.assert_metric(metric, at_least=1)
    aggregator.assert_service_check('flink.openmetrics.health', FlinkCheck.OK)
