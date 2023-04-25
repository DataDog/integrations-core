# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.stubs.aggregator import AggregatorStub

STRIMZI_VERSION = os.environ["STRIMZI_VERSION"]
HERE = os.path.abspath(os.path.dirname(__file__))

METRICS = (
    {
        "name": "strimzi.jvm.gc.memory_promoted_bytes.count",
        "value": 1,
    },
)
