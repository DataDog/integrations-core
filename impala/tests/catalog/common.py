# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub

# E501: line too long (XXX > 120 characters)
# ruff: noqa: E501

TAGS = ['endpoint:http://localhost:25020/metrics_prometheus']

# "value" is only used in unit test
METRICS = [
    # tcmalloc
    {
        "name": "impala.catalog.tcmalloc.in_use",
        "value": 48179280,
    },
    {
        "name": "impala.catalog.tcmalloc.pageheap.free",
        "value": 10,
    },
    {
        "name": "impala.catalog.tcmalloc.pageheap.unmapped",
        "value": 14565376,
    },
    {
        "name": "impala.catalog.tcmalloc.physical_reserved",
        "value": 58187776,
    },
    {
        "name": "impala.catalog.tcmalloc.total_reserved",
        "value": 72753152,
    },
    # jvm
    {
        "name": "impala.catalog.jvm.code_cache.committed_usage",
        "value": 6553600,
    },
    {
        "name": "impala.catalog.jvm.code_cache.current_usage",
        "value": 6104000,
    },
    {
        "name": "impala.catalog.jvm.code_cache.init_usage",
        "value": 2555904,
    },
    {
        "name": "impala.catalog.jvm.code_cache.max_usage",
        "value": 251658240,
    },
    {
        "name": "impala.catalog.jvm.code_cache.peak_committed_usage",
        "value": 6553600,
    },
    {
        "name": "impala.catalog.jvm.code_cache.peak_current_usage",
        "value": 6493568,
    },
    {
        "name": "impala.catalog.jvm.code_cache.peak_init_usage",
        "value": 2555904,
    },
    {
        "name": "impala.catalog.jvm.code_cache.peak_max_usage",
        "value": 251658240,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.committed_usage",
        "value": 3145728,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.current_usage",
        "value": 3018288,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.init_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.max_usage",
        "value": 1073741824,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.peak_committed_usage",
        "value": 3145728,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.peak_current_usage",
        "value": 3018288,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.compressed_class_space.peak_max_usage",
        "value": 1073741824,
    },
    {
        "name": "impala.catalog.jvm.gc.count",
        "value": 9,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.jvm.gc.num_info_threshold_exceeded.count",
        "value": 12,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.jvm.gc.num_warn_threshold_exceeded.count",
        "value": 55,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.jvm.gc.time_millis.count",
        "value": 0.126,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.jvm.gc.total_extra_sleep_time_millis.count",
        "value": 1.232,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.jvm.heap.committed_usage",
        "value": 119013376,
    },
    {
        "name": "impala.catalog.jvm.heap.current_usage",
        "value": 29420832,
    },
    {
        "name": "impala.catalog.jvm.heap.init_usage",
        "value": 132120576,
    },
    {
        "name": "impala.catalog.jvm.heap.max_usage",
        "value": 1908932608,
    },
    {
        "name": "impala.catalog.jvm.heap.peak_committed_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.heap.peak_current_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.heap.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.heap.peak_max_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.metaspace.committed_usage",
        "value": 29360128,
    },
    {
        "name": "impala.catalog.jvm.metaspace.current_usage",
        "value": 28849616,
    },
    {
        "name": "impala.catalog.jvm.metaspace.init_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.metaspace.max_usage",
        "value": -1.0,
    },
    {
        "name": "impala.catalog.jvm.metaspace.peak_committed_usage",
        "value": 29360128,
    },
    {
        "name": "impala.catalog.jvm.metaspace.peak_current_usage",
        "value": 28849616,
    },
    {
        "name": "impala.catalog.jvm.metaspace.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.metaspace.peak_max_usage",
        "value": -1,
    },
    {
        "name": "impala.catalog.jvm.non_heap.committed_usage",
        "value": 39059456,
    },
    {
        "name": "impala.catalog.jvm.non_heap.current_usage",
        "value": 37971904,
    },
    {
        "name": "impala.catalog.jvm.non_heap.init_usage",
        "value": 2555904,
    },
    {
        "name": "impala.catalog.jvm.non_heap.max_usage",
        "value": -1,
    },
    {
        "name": "impala.catalog.jvm.non_heap.peak_committed_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.non_heap.peak_current_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.non_heap.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.non_heap.peak_max_usage",
        "value": 0,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.committed_usage",
        "value": 48758784,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.current_usage",
        "value": 14748696,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.init_usage",
        "value": 33554432,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.max_usage",
        "value": 697827328,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.peak_committed_usage",
        "value": 48758784,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.peak_current_usage",
        "value": 33554432,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.peak_init_usage",
        "value": 33554432,
    },
    {
        "name": "impala.catalog.jvm.ps_eden_space.peak_max_usage",
        "value": 705167360,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.committed_usage",
        "value": 61865984,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.current_usage",
        "value": 8830616,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.init_usage",
        "value": 88080384,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.max_usage",
        "value": 1431830528,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.peak_committed_usage",
        "value": 88080384,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.peak_current_usage",
        "value": 8830616,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.peak_init_usage",
        "value": 88080384,
    },
    {
        "name": "impala.catalog.jvm.ps_old_gen.peak_max_usage",
        "value": 1431830528,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.committed_usage",
        "value": 8388608,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.current_usage",
        "value": 5841520,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.init_usage",
        "value": 5242880,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.max_usage",
        "value": 8388608,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.peak_committed_usage",
        "value": 10485760,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.peak_current_usage",
        "value": 5841520,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.peak_init_usage",
        "value": 5242880,
    },
    {
        "name": "impala.catalog.jvm.ps_survivor_space.peak_max_usage",
        "value": 10485760,
    },
    {
        "name": "impala.catalog.jvm.total_committed_usage",
        "value": 158072832,
    },
    {
        "name": "impala.catalog.jvm.total_current_usage",
        "value": 67392736,
    },
    {
        "name": "impala.catalog.jvm.total_init_usage",
        "value": 129433600,
    },
    {
        "name": "impala.catalog.jvm.total_max_usage",
        "value": 3463446527,
    },
    {
        "name": "impala.catalog.jvm.total_peak_committed_usage",
        "value": 186384384,
    },
    {
        "name": "impala.catalog.jvm.total_peak_current_usage",
        "value": 86588040,
    },
    {
        "name": "impala.catalog.jvm.total_peak_init_usage",
        "value": 129433600,
    },
    {
        "name": "impala.catalog.jvm.total_peak_max_usage",
        "value": 3472883711,
    },
    # events_processor
    {
        "name": "impala.catalog.events_processor.events_received_15min_rate",
        "value": 1,
    },
    {
        "name": "impala.catalog.events_processor.events_received.count",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.events_processor.events_received_5min_rate",
        "value": 5,
    },
    {
        "name": "impala.catalog.events_processor.events_received_1min_rate",
        "value": 6,
    },
    {
        "name": "impala.catalog.events_processor.events_skipped.count",
        "value": 4,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.events_processor.last_synced_event_id.count",
        "value": 3,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.events_processor.avg_events_fetch_duration",
        "value": 0.992732,
    },
    {
        "name": "impala.catalog.events_processor.avg_events_process_duration",
        "value": 7,
    },
    # memory
    {
        "name": "impala.catalog.memory.mapped",
        "value": 4081811456,
    },
    {
        "name": "impala.catalog.memory.rss",
        "value": 209494016,
    },
    {
        "name": "impala.catalog.memory.total_used",
        "value": 58187776,
    },
    # thread_manager
    {
        "name": "impala.catalog.thread_manager.running_threads",
        "value": 12,
    },
    {
        "name": "impala.catalog.thread_manager.total_threads_created",
        "value": 13,
    },
    # thrift_server
    {
        "name": "impala.catalog.thrift_server.connection.setup_queue_size",
        "value": 15,
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.count",
        "value": 1,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.sum",
        "value": 0,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.quantile",
        "value": 1,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.quantile",
        "value": 2,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.quantile",
        "value": 3,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.quantile",
        "value": 4,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.quantile",
        "value": 5,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.catalog.thrift_server.connection.setup_time.quantile",
        "value": 6,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.catalog.thrift_server.connections.in_use",
        "value": 1,
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.count",
        "value": 1,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.sum",
        "value": 0,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.quantile",
        "value": 10,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.quantile",
        "value": 11,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.quantile",
        "value": 12,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.quantile",
        "value": 13,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.quantile",
        "value": 14,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.catalog.thrift_server.svc_thread_wait_time.quantile",
        "value": 15,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.catalog.thrift_server.timedout_cnxn_requests",
        "value": 500,
    },
    {
        "name": "impala.catalog.thrift_server.total_connections.count",
        "value": 1000,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    # catalog
    {
        "name": "impala.catalog.partial_fetch_rpc_queue_len",
        "value": 60,
    },
    {
        "name": "impala.catalog.server_topic_processing_time_s_total.count",
        "value": 403,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.count",
        "value": 4,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.sum",
        "value": 0.103,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.quantile",
        "value": 0.001,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.quantile",
        "value": 0.002,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.quantile",
        "value": 0.003,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.quantile",
        "value": 0.004,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.quantile",
        "value": 0.005,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration.quantile",
        "value": 0.006,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.count",
        "value": 803,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.sum",
        "value": 0.289,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.quantile",
        "value": 0.010,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.quantile",
        "value": 0.011,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.quantile",
        "value": 0.012,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.quantile",
        "value": 0.013,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.quantile",
        "value": 0.014,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.heartbeat_call_duration.quantile",
        "value": 0.015,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.count",
        "value": 403,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.sum",
        "value": 0.153,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.quantile",
        "value": 0.020,
        "tags": TAGS + ['quantile:0.2'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.quantile",
        "value": 0.021,
        "tags": TAGS + ['quantile:0.5'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.quantile",
        "value": 0.022,
        "tags": TAGS + ['quantile:0.7'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.quantile",
        "value": 0.023,
        "tags": TAGS + ['quantile:0.9'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.quantile",
        "value": 0.024,
        "tags": TAGS + ['quantile:0.95'],
    },
    {
        "name": "impala.catalog.rpc_method_statestore_subscriber.update_state_call_duration.quantile",
        "value": 0.025,
        "tags": TAGS + ['quantile:0.999'],
    },
    {
        "name": "impala.catalog.statestore_subscriber.heartbeat_interval_time_total.count",
        "value": 803,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.statestore_subscriber.last_recovery_duration",
        "value": 42,
    },
    {
        "name": "impala.catalog.statestore_subscriber.num_connection_failures.count",
        "value": 55,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.statestore_subscriber.statestore_client_cache.clients_in_use",
        "value": 70,
    },
    {
        "name": "impala.catalog.statestore_subscriber.statestore_client_cache.total_clients",
        "value": 1,
    },
    {
        "name": "impala.catalog.statestore_subscriber.processing_time.count",
        "value": 403,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ['topic:catalog_update'],
    },
    {
        "name": "impala.catalog.statestore_subscriber.update_interval.count",
        "value": 402,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ['topic:catalog_update'],
    },
    {
        "name": "impala.catalog.statestore_subscriber.topic_update_duration_total.count",
        "value": 490,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.catalog.statestore_subscriber.topic_update_interval_time_total.count",
        "value": 480,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
]
