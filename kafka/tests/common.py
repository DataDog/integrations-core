# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here

CHECK_NAME = 'kafka'

HERE = get_here()


KAFKA_E2E_METRICS = [
    "jvm.thread_count",
    "jvm.heap_memory_max",
    "kafka.request.fetch_follower.time.99percentile",
    "kafka.request.metadata.time.avg",
]
