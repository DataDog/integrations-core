# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub

TAGS = ["endpoint:http://localhost:9249/metrics"]

# A representative sampling of metrics from the fixture used for unit tests.
# These are the namespaced Datadog metric names (i.e. prefix `flink.` is
# added by AggregatorStub.assert_metric below).
METRICS = [
    {
        "name": "jobmanager.Status.JVM.CPU.Load",
        "value": 0.05,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS,
    },
    {
        "name": "jobmanager.Status.JVM.Memory.Heap.Used",
        "value": 123456789.0,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS,
    },
    {
        "name": "jobmanager.numRegisteredTaskManagers",
        "value": 2.0,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS,
    },
    {
        "name": "jobmanager.job.numberOfCompletedCheckpoints",
        "value": 42,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS + ["job_name:wordcount"],
    },
    {
        "name": "taskmanager.Status.JVM.Memory.Heap.Used",
        "value": 87654321.0,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS + ["tm_id:tm-1"],
    },
    {
        "name": "taskmanager.Status.JVM.Threads.Count",
        "value": 64,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS + ["tm_id:tm-1"],
    },
    # Locks in the raw `PerSecond` → DD-side `PerSec` rename so the
    # asymmetry between Flink's emitted name and metadata.csv doesn't
    # silently drop the throughput metric.
    {
        "name": "task.numRecordsOutPerSec",
        "value": 42.5,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS + ["tm_id:tm-1", "job_name:wordcount", "task_name:Source: KafkaSource", "subtask_index:0"],
    },
]
