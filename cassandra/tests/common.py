# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = "cassandra"

HERE = get_here()
HOST = get_docker_hostname()


# not all metrics will be available in our E2E environment, specifically:
# TODO:// testing for cassandra nodetool metrics

CASSANDRA_E2E_METRICS = [
    "cassandra.currently_blocked_tasks.count",
    "cassandra.db.droppable_tombstone_ratio",
    "cassandra.dropped.one_minute_rate",
    "cassandra.exceptions.count",
    "cassandra.latency.75th_percentile",
    "cassandra.latency.95th_percentile",
    "cassandra.latency.one_minute_rate",
    "cassandra.load.count",
    "cassandra.pending_tasks",
    "cassandra.total_commit_log_size",
    # JVM Metrics -- At this time, collecting these default metrics cannot be excluded from this test
    "jvm.buffer_pool.direct.capacity",
    "jvm.buffer_pool.direct.count",
    "jvm.buffer_pool.direct.used",
    "jvm.buffer_pool.mapped.capacity",
    "jvm.buffer_pool.mapped.count",
    "jvm.buffer_pool.mapped.used",
    "jvm.cpu_load.process",
    "jvm.cpu_load.system",
    "jvm.gc.eden_size",
    "jvm.gc.old_gen_size",
    "jvm.gc.survivor_size",
    "jvm.heap_memory",
    "jvm.heap_memory_committed",
    "jvm.heap_memory_init",
    "jvm.heap_memory_max",
    "jvm.loaded_classes",
    "jvm.non_heap_memory",
    "jvm.non_heap_memory_committed",
    "jvm.non_heap_memory_init",
    "jvm.non_heap_memory_max",
    "jvm.os.open_file_descriptors",
    "jvm.thread_count",
]
