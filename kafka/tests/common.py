# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import socket

import pytest
from datadog_checks.dev import get_docker_hostname, get_here

CHECK_NAME = "kafka"

HERE = get_here()
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)

COMPOSE_FILE = os.getenv('COMPOSE_FILE', 'docker-compose.yml')
IS_KRAFT = COMPOSE_FILE == 'kraft.yml'

kraft = pytest.mark.skipif(not IS_KRAFT, reason='Test only valid for KRaft mode')
not_kraft = pytest.mark.skipif(IS_KRAFT, reason='Test only valid for ZooKeeper mode')


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

KAFKA_COMMON_E2E_METRICS = [
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
    # Replication stats:
    "kafka.replication.active_controller_count",
    "kafka.replication.leader_count",
    "kafka.replication.offline_partitions_count",
    "kafka.replication.partition_count",
    "kafka.replication.under_replicated_partitions",
    "kafka.replication.under_min_isr_partition_count",
    # Rates:
    "kafka.messages_in.rate",
    "kafka.net.bytes_in.rate",
    "kafka.net.bytes_out.rate",
    "kafka.net.bytes_rejected.rate",
    "kafka.replication.isr_expands.rate",
    "kafka.replication.isr_shrinks.rate",
    "kafka.request.fetch.failed.rate",
    "kafka.request.produce.failed.rate",
    # Session:
    "kafka.session.fetch.count",
    "kafka.session.fetch.eviction",
    # Listeners:
    "kafka.server.socket.connection_count",
    # Replication max lag:
    "kafka.replication.max_lag",
    # Controller:
    "kafka.controller.fenced_broker_count",
    "kafka.controller.active_broker_count",
    # Broker:
    "kafka.broker.start_time",
]

KAFKA_ZK_E2E_METRICS = [
    "kafka.session.zookeeper.disconnect.rate",
    "kafka.session.zookeeper.expire.rate",
    "kafka.session.zookeeper.readonly.rate",
    "kafka.session.zookeeper.sync.rate",
    "kafka.replication.leader_elections.rate",
    "kafka.replication.unclean_leader_elections.rate",
    "kafka.request.update_metadata.time.99percentile",
    "kafka.request.update_metadata.time.avg",
]

KAFKA_KRAFT_E2E_METRICS = [
    # Raft quorum:
    "kafka.kraft.current_leader",
    "kafka.kraft.current_vote",
    "kafka.kraft.current_epoch",
    "kafka.kraft.high_watermark",
    "kafka.kraft.log_end_offset",
    "kafka.kraft.log_end_epoch",
    "kafka.kraft.append_records_rate",
    "kafka.kraft.fetch_records_rate",
    "kafka.kraft.commit_latency_avg",
    "kafka.kraft.commit_latency_max",
    "kafka.kraft.poll_idle_ratio_avg",
    "kafka.kraft.unknown_voter_connections",
    # Broker metadata:
    "kafka.kraft.broker_metadata.last_applied_record_offset",
    "kafka.kraft.broker_metadata.last_applied_record_timestamp",
    "kafka.kraft.broker_metadata.last_applied_record_lag_ms",
    "kafka.kraft.broker_metadata.metadata_load_error_count",
    "kafka.kraft.broker_metadata.metadata_apply_error_count",
    # MetadataLoader:
    "kafka.kraft.metadata_loader.current_metadata_version",
    "kafka.kraft.metadata_loader.current_controller_id",
    "kafka.kraft.metadata_loader.handle_load_snapshot_count",
    # SnapshotEmitter:
    "kafka.kraft.snapshot_emitter.latest_snapshot_generated_age_ms",
    "kafka.kraft.snapshot_emitter.latest_snapshot_generated_bytes",
    # Log flush:
    "kafka.log.flush_rate.rate",
    # Election latency (may be NaN in single-node clusters):
    "kafka.kraft.election_latency_avg",
    "kafka.kraft.election_latency_max",
]

OPTIONAL_KRAFT_E2E_METRICS = {
    "kafka.kraft.election_latency_avg",
    "kafka.kraft.election_latency_max",
}
