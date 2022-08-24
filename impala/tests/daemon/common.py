# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub

# E501: line too long (XXX > 120 characters)
# flake8: noqa: E501

TAGS = ['endpoint:http://localhost:25000/metrics_prometheus']

# "value" is only used in unit test
METRICS = [
    {
        "name": "impala.daemon.jvm.gc.count",
        "value": 9,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
]
