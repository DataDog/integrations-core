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

_TASK_TAGS = TAGS + ["tm_id:tm-1", "job_name:wordcount", "task_name:Source: KafkaSource", "subtask_index:0"]
_OPERATOR_TAGS = TAGS + ["tm_id:tm-1", "job_name:wordcount", "operator_name:Source", "subtask_index:0"]

# Flink Counters (see metrics.py's COUNTER_METRICS). Flink's Prometheus reporter
# always describes these as `# TYPE ... gauge` in the raw scrape (see
# fixtures/metrics.txt), so asserting MONOTONIC_COUNT here is what actually locks
# in the bug 1 fix -- without the type_override wiring in check.py, these would
# be submitted (and fail this assertion) as GAUGE.
COUNTER_METRICS = [
    {"name": "task.numRecordsIn", "value": 12345.0, "tags": _TASK_TAGS},
    {"name": "task.numRecordsOut", "value": 12345.0, "tags": _TASK_TAGS},
    {"name": "task.numBytesOut", "value": 999999.0, "tags": _TASK_TAGS},
    {"name": "task.numBuffersOut", "value": 500.0, "tags": _TASK_TAGS},
    {"name": "task.numLateRecordsDropped", "value": 3.0, "tags": _TASK_TAGS},
    {"name": "task.Shuffle.Netty.Input.numBytesInLocal", "value": 1000.0, "tags": _TASK_TAGS},
    {"name": "task.Shuffle.Netty.Input.numBytesInRemote", "value": 2000.0, "tags": _TASK_TAGS},
    {"name": "task.Shuffle.Netty.Input.numBuffersInLocal", "value": 10.0, "tags": _TASK_TAGS},
    {"name": "task.Shuffle.Netty.Input.numBuffersInRemote", "value": 20.0, "tags": _TASK_TAGS},
    {"name": "operator.numRecordsIn", "value": 12345.0, "tags": _OPERATOR_TAGS},
    {"name": "operator.numRecordsOut", "value": 6789.0, "tags": _OPERATOR_TAGS},
    {"name": "operator.numLateRecordsDropped", "value": 1.0, "tags": _OPERATOR_TAGS},
    {"name": "operator.numSplitsProcessed", "value": 7.0, "tags": _OPERATOR_TAGS},
    {"name": "operator.commitsSucceeded", "value": 15.0, "tags": _OPERATOR_TAGS},
    {"name": "operator.commitsFailed", "value": 0.0, "tags": _OPERATOR_TAGS},
]
