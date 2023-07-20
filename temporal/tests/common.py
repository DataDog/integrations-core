# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub

TAGS = ["endpoint:http://localhost:8000/metrics"]


# A representative sampling of metrics from the fixture used for unit tests
METRICS = [
    {
        "name": "ack_level.update.count",
        "value": 12,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:TimerQueueProcessor", "service_name:history"],
    },
    {
        "name": "ack_level.update.count",
        "value": 12,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:TransferQueueProcessor", "service_name:history"],
    },
    {
        "name": "ack_level.update.count",
        "value": 12,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:VisibilityQueueProcessor", "service_name:history"],
    },
    {
        "name": "acquire_shards.count",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history"],
    },
    {
        "name": "acquire_shards.latency.bucket",
        "value": 1,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history", "upper_bound:0.001"],
    },
    {
        "name": "acquire_shards.latency.bucket",
        "value": 1,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history", "upper_bound:0.005"],
    },
    {
        "name": "acquire_shards.latency.bucket",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history", "upper_bound:0.1"],
    },
    {
        "name": "acquire_shards.latency.bucket",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history", "upper_bound:1000.0"],
    },
    {
        "name": "acquire_shards.latency.count",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history"],
    },
    {
        "name": "acquire_shards.latency.sum",
        "value": 0.066191125,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history"],
    },
    {
        "name": "loaded_task_queue_count",
        "value": 4,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS
        + [
            "namespace:default",
            "operation:MatchingEngine",
            "queue_type:Normal",
            "service_name:matching",
            "task_type:Activity",
        ],
    },
    {
        "name": "loaded_task_queue_count",
        "value": 2,
        "type": AggregatorStub.GAUGE,
        "tags": TAGS
        + [
            "namespace:default",
            "operation:MatchingEngine",
            "queue_type:Sticky",
            "service_name:matching",
            "task_type:Workflow",
        ],
    },
]
