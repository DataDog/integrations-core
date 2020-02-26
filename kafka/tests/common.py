# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dev import get_here

CHECK_NAME = 'kafka'

HERE = get_here()

# Metrics that do not work in our e2e
# "kafka.net.bytes_out.rate",
# "kafka.net.bytes_in.rate"
# "kafka.net.bytes_rejected.rate"
# "kafka.net.processor.avg.idle.pct.rate"
# "kafka.request.fetch.failed.rate",
# "kafka.request.fetch.failed_per_second",
# "kafka.request.produce.failed_per_second",
# "kafka.request.produce.failed.rate",
# "kafka.request.fetch.time.avg",
# "kafka.request.fetch.time.99percentile",


KAFKA_E2E_METRICS = [
    "jvm.heap_memory_max",
    "jvm.thread_count",
    "kafka.net.handler.avg.idle.pct.rate",
    "kafka.replication.active_controller_count",
    "kafka.replication.leader_count",
    "kafka.replication.max_lag",
    "kafka.replication.offline_partitions_count",
    "kafka.replication.partition_count",
    "kafka.replication.under_replicated_partitions",
    "kafka.request.channel.queue.size",
    "kafka.request.fetch_consumer.time.99percentile",
    "kafka.request.fetch_consumer.time.avg",
    "kafka.request.fetch_follower.time.99percentile",
    "kafka.request.fetch_follower.time.avg",
    "kafka.request.fetch_request_purgatory.size",
    "kafka.request.handler.avg.idle.pct.rate",
    "kafka.request.metadata.time.avg",
    "kafka.request.produce.time.99percentile",
    "kafka.request.produce.time.avg",
    "kafka.request.producer_request_purgatory.size",
    "kafka.request.update_metadata.time.99percentile",
    "kafka.request.update_metadata.time.avg",
]
