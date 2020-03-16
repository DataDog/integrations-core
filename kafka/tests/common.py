# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket

from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = "kafka"

HERE = get_here()
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)


"""
Rate type metrics that do not work in our e2e:
    "kafka.consumer.bytes_in",
    "kafka.consumer.kafka_commits",
    "kafka.consumer.messages_in",
    "kafka.consumer.zookeeper_commits",
    "kafka.messages_in.rate",
    "kafka.net.bytes_in.rate",
    "kafka.net.bytes_out.rate",
    "kafka.net.bytes_rejected.rate",
    "kafka.replication.isr_expands.rate",
    "kafka.replication.isr_shrinks.rate",
    "kafka.replication.leader_elections.rate",
    "kafka.replication.unclean_leader_elections.rate",
    "kafka.request.fetch.failed.rate",
    "kafka.request.fetch.failed_per_second",
    "kafka.request.fetch.time.99percentile",
    "kafka.request.fetch.time.avg",
    "kafka.request.produce.failed.rate",
    "kafka.request.produce.failed_per_second",
"""

KAFKA_E2E_METRICS = [
    "kafka.net.processor.avg.idle.pct.rate",
    # Request metrics:
    "kafka.request.channel.queue.size",
    "kafka.request.fetch_consumer.time.99percentile",
    "kafka.request.fetch_consumer.time.avg",
    "kafka.request.fetch_follower.time.99percentile",
    "kafka.request.fetch_follower.time.avg",
    "kafka.request.fetch_request_purgatory.size",
    "kafka.request.handler.avg.idle.pct.rate",
    "kafka.request.metadata.time.99percentile",
    "kafka.request.metadata.time.avg",
    "kafka.request.produce.time.99percentile",
    "kafka.request.produce.time.avg",
    "kafka.request.producer_request_purgatory.size",
    "kafka.request.update_metadata.time.99percentile",
    "kafka.request.update_metadata.time.avg",
    # replication stats:
    "kafka.replication.active_controller_count",
    "kafka.replication.leader_count",
    "kafka.replication.max_lag",
    "kafka.replication.offline_partitions_count",
    "kafka.replication.partition_count",
    "kafka.replication.under_replicated_partitions",
    # JVM metrics:
    "jvm.buffer_pool.direct.capacity",
    "jvm.buffer_pool.direct.count",
    "jvm.buffer_pool.direct.used",
    "jvm.buffer_pool.mapped.capacity",
    "jvm.buffer_pool.mapped.count",
    "jvm.buffer_pool.mapped.used",
    "jvm.cpu_load.process",
    "jvm.cpu_load.system",
    "jvm.gc.cms.count",
    "jvm.gc.eden_size",
    "jvm.gc.old_gen_size",
    "jvm.gc.parnew.time",
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
