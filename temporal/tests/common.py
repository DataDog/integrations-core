# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub


def get_e2e_metric_type(metric_type):
    if metric_type == AggregatorStub.MONOTONIC_COUNT:
        return AggregatorStub.COUNT

    return metric_type


TAGS = ["endpoint:http://localhost:8000/metrics"]


METRICS = [
    {
        "name": "acquire_shards.count",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["operation:ShardController", "service_name:history"],
    },
]
