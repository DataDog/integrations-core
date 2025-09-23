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
Metrics that do not work in our e2e:
    "kafka.consumer.bytes_in",
    "kafka.consumer.kafka_commits",
    "kafka.consumer.messages_in",
    "kafka.consumer.zookeeper_commits",
    "kafka.request.produce.rate",
    "kafka.request.fetch_follower.rate",
    "kafka.request.fetch_consumer.rate",
    "kafka.consumer.fetch_rate",
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
    "kafka.replication.under_min_isr_partition_count",
    # Rates
    "kafka.messages_in.rate",
    "kafka.net.bytes_in.rate",
    "kafka.net.bytes_out.rate",
    "kafka.net.bytes_rejected.rate",
    "kafka.replication.isr_expands.rate",
    "kafka.replication.isr_shrinks.rate",
    "kafka.replication.leader_elections.rate",
    "kafka.replication.unclean_leader_elections.rate",
    "kafka.request.fetch.failed.rate",
    "kafka.request.produce.failed.rate",
    "kafka.session.zookeeper.disconnect.rate",
    "kafka.session.zookeeper.expire.rate",
    "kafka.session.zookeeper.readonly.rate",
    "kafka.session.zookeeper.sync.rate",
    # Session
    "kafka.session.fetch.count",
    "kafka.session.fetch.eviction",
    # Listeners
    "kafka.server.socket.connection_count",
]
