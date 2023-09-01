# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub

TAGS = ['endpoint:http://localhost:25010/metrics_prometheus']

# "value" is only used in unit test
METRICS = [
    {
        "name": "impala.statestore.live_backends",
        "value": 2,
    },
    {
        "name": "impala.statestore.memory.mapped",
        "value": 544841728,
    },
    {
        "name": "impala.statestore.memory.rss",
        "value": 47427584,
    },
    {
        "name": "impala.statestore.memory.total_used",
        "value": 5316608,
    },
    {
        "name": "impala.statestore.subscriber.heartbeat.client_cache.total_clients",
        "value": 2,
    },
    {
        "name": "impala.statestore.subscriber.heartbeat.client_cache.clients_in_use",
        "value": 0,
    },
    {
        "name": "impala.statestore.subscriber.update_state.client_cache.clients_in_use",
        "value": 12,
    },
    {
        "name": "impala.statestore.subscriber.update_state.client_cache.total_clients",
        "value": 3,
    },
    {
        "name": "impala.statestore.tcmalloc.in_use",
        "value": 3790248,
    },
    {
        "name": "impala.statestore.tcmalloc.pageheap.free",
        "value": 10,
    },
    {
        "name": "impala.statestore.tcmalloc.pageheap.unmapped",
        "value": 974848,
    },
    {
        "name": "impala.statestore.tcmalloc.physical_reserved",
        "value": 5316608,
    },
    {
        "name": "impala.statestore.tcmalloc.total_reserved",
        "value": 6291456,
    },
    {
        "name": "impala.statestore.thread_manager.running_threads",
        "value": 36,
    },
    {
        "name": "impala.statestore.thread_manager.total_threads_created",
        "value": 40,
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_queue_size",
        "value": 4,
    },
    {
        "name": "impala.statestore.thrift_server.connections_in_use",
        "value": 8,
    },
    {
        "name": "impala.statestore.thrift_server.timedout_cnxn_requests",
        "value": 13,
    },
    {
        "name": "impala.statestore.thrift_server.total_connections.count",
        "value": 14,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.total_key_size",
        "value": 71,
    },
    {
        "name": "impala.statestore.total_topic_size",
        "value": 280,
    },
    {
        "name": "impala.statestore.total_value_size",
        "value": 209,
    },
    {
        "name": "impala.statestore.topic_update_durations.count",
        "value": 734,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.last_topic_update_durations",
        "value": 0.001,
    },
    {
        "name": "impala.statestore.min_topic_update_durations",
        "value": 0,
    },
    {
        "name": "impala.statestore.max_topic_update_durations",
        "value": 3.475,
    },
    {
        "name": "impala.statestore.mean_topic_update_durations",
        "value": 0.00629019,
    },
    {
        "name": "impala.statestore.priority_topic_update_durations.count",
        "value": 7161,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.last_priority_topic_update_durations",
        "value": 0.001,
    },
    {
        "name": "impala.statestore.min_priority_topic_update_durations",
        "value": 0,
    },
    {
        "name": "impala.statestore.max_priority_topic_update_durations",
        "value": 0.076,
    },
    {
        "name": "impala.statestore.mean_priority_topic_update_durations",
        "value": 0.00119969,
    },
    {
        "name": "impala.statestore.heartbeat_durations.count",
        "value": 1468,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.sum",
        "value": 20,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.count",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.quantile",
        "value": 1,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.quantile",
        "value": 2,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.quantile",
        "value": 3,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.quantile",
        "value": 4,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.quantile",
        "value": 5,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.statestore.thrift_server.connection_setup_time.quantile",
        "value": 6,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.sum",
        "value": 21,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.count",
        "value": 4,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.quantile",
        "value": 7,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.quantile",
        "value": 8,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.quantile",
        "value": 9,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.quantile",
        "value": 10,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.quantile",
        "value": 11,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.statestore.thrift_server.svc_thread_wait_time.quantile",
        "value": 12,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.count",
        "value": 50,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.sum",
        "value": 0.004,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.quantile",
        "tags": TAGS + ['quantile:0.2'],
        "value": 0.001,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.quantile",
        "tags": TAGS + ['quantile:0.5'],
        "value": 0.002,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.quantile",
        "tags": TAGS + ['quantile:0.7'],
        "value": 0.003,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.quantile",
        "tags": TAGS + ['quantile:0.9'],
        "value": 0.004,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.quantile",
        "tags": TAGS + ['quantile:0.95'],
        "value": 0.005,
    },
    {
        "name": "impala.statestore.register_subscriber_call_duration.quantile",
        "tags": TAGS + ['quantile:0.999'],
        "value": 0.006,
    },
]
