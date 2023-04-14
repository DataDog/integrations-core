# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.stubs.aggregator import AggregatorStub

# E501: line too long (XXX > 120 characters)
# ruff: noqa: E501

TAGS = ['endpoint:http://localhost:25000/metrics_prometheus']

# "value" is only used in unit test
METRICS = [
    {
        "name": "impala.daemon.io_mgr_queue.write_io_error_total.count",
        "value": 1,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.quantile",
        "value": 2,
        "tags": TAGS + ["quantile:0.2", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.quantile",
        "value": 3,
        "tags": TAGS + ["quantile:0.5", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.quantile",
        "value": 4,
        "tags": TAGS + ["quantile:0.7", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.quantile",
        "value": 5,
        "tags": TAGS + ["quantile:0.9", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.quantile",
        "value": 6,
        "tags": TAGS + ["quantile:0.95", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.quantile",
        "value": 7,
        "tags": TAGS + ["quantile:0.999", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.sum",
        "value": 9,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_latency.count",
        "value": 8,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.quantile",
        "value": 10,
        "tags": TAGS + ["quantile:0.2", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.quantile",
        "value": 11,
        "tags": TAGS + ["quantile:0.5", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.quantile",
        "value": 12,
        "tags": TAGS + ["quantile:0.7", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.quantile",
        "value": 13,
        "tags": TAGS + ["quantile:0.9", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.quantile",
        "value": 14,
        "tags": TAGS + ["quantile:0.95", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.quantile",
        "value": 15,
        "tags": TAGS + ["quantile:0.999", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.sum",
        "value": 17,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.read_size.count",
        "value": 16,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.quantile",
        "value": 18,
        "tags": TAGS + ["quantile:0.2", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.quantile",
        "value": 19,
        "tags": TAGS + ["quantile:0.5", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.quantile",
        "value": 20,
        "tags": TAGS + ["quantile:0.7", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.quantile",
        "value": 21,
        "tags": TAGS + ["quantile:0.9", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.quantile",
        "value": 22,
        "tags": TAGS + ["quantile:0.95", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.quantile",
        "value": 23,
        "tags": TAGS + ["quantile:0.999", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.sum",
        "value": 25,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_size.count",
        "value": 24,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.quantile",
        "value": 26,
        "tags": TAGS + ["quantile:0.2", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.quantile",
        "value": 27,
        "tags": TAGS + ["quantile:0.5", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.quantile",
        "value": 28,
        "tags": TAGS + ["quantile:0.7", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.quantile",
        "value": 29,
        "tags": TAGS + ["quantile:0.9", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.quantile",
        "value": 30,
        "tags": TAGS + ["quantile:0.95", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.quantile",
        "value": 31,
        "tags": TAGS + ["quantile:0.999", "id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.sum",
        "value": 33,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.io_mgr_queue.write_latency.count",
        "value": 32,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.num_final_scavenges_total.count",
        "value": 11,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.num_scavenges_total.count",
        "value": 1,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.clean_page_hits_total.count",
        "value": 14,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.system_alloc_time_total.count",
        "value": 13,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.local_arena_free_buffer_hits_total.count",
        "value": 15,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.numa_arena_free_buffer_hits_total.count",
        "value": 12,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.direct_alloc_count_total.count",
        "value": 2,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
        "value": 3,
        "tags": TAGS + ["quantile:0.2", "id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
        "value": 4,
        "tags": TAGS + ["quantile:0.5", "id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
        "value": 5,
        "tags": TAGS + ["quantile:0.7", "id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
        "value": 6,
        "tags": TAGS + ["quantile:0.9", "id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
        "value": 7,
        "tags": TAGS + ["quantile:0.95", "id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
        "value": 8,
        "tags": TAGS + ["quantile:0.999", "id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.sum",
        "value": 10,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    {
        "name": "impala.daemon.buffer_pool.arena.allocated_buffer_sizes.count",
        "value": 9,
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["id:0"],
    },
    # jvm
    {
        "name": "impala.daemon.jvm.code_cache.committed_usage",
        "value": 6488064,
    },
    {
        "name": "impala.daemon.jvm.code_cache.current_usage",
        "value": 5889216,
    },
    {
        "name": "impala.daemon.jvm.code_cache.init_usage",
        "value": 2555904,
    },
    {
        "name": "impala.daemon.jvm.code_cache.max_usage",
        "value": 251658240,
    },
    {
        "name": "impala.daemon.jvm.code_cache.peak_committed_usage",
        "value": 6488064,
    },
    {
        "name": "impala.daemon.jvm.code_cache.peak_current_usage",
        "value": 6428224,
    },
    {
        "name": "impala.daemon.jvm.code_cache.peak_init_usage",
        "value": 2555904,
    },
    {
        "name": "impala.daemon.jvm.code_cache.peak_max_usage",
        "value": 251658240,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.committed_usage",
        "value": 3407872,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.current_usage",
        "value": 3247272,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.init_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.max_usage",
        "value": 1073741824,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.peak_committed_usage",
        "value": 3407872,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.peak_current_usage",
        "value": 3247272,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.compressed_class_space.peak_max_usage",
        "value": 1073741824,
    },
    {
        "name": "impala.daemon.jvm.gc.count",
        "value": 9,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.jvm.gc.num_info_threshold_exceeded.count",
        "value": 0,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.jvm.gc.num_warn_threshold_exceeded.count",
        "value": 0,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.jvm.gc.time_millis.count",
        "value": 0.132,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.jvm.gc.total_extra_sleep_time_millis.count",
        "value": 1.657,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.jvm.heap.committed_usage",
        "value": 116916224,
    },
    {
        "name": "impala.daemon.jvm.heap.current_usage",
        "value": 43646624,
    },
    {
        "name": "impala.daemon.jvm.heap.init_usage",
        "value": 132120576,
    },
    {
        "name": "impala.daemon.jvm.heap.max_usage",
        "value": 954728448,
    },
    {
        "name": "impala.daemon.jvm.heap.peak_committed_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.heap.peak_current_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.heap.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.heap.peak_max_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.metaspace.committed_usage",
        "value": 31457280,
    },
    {
        "name": "impala.daemon.jvm.metaspace.current_usage",
        "value": 30702328,
    },
    {
        "name": "impala.daemon.jvm.metaspace.init_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.metaspace.max_usage",
        "value": -1.0,
    },
    {
        "name": "impala.daemon.jvm.metaspace.peak_committed_usage",
        "value": 31457280,
    },
    {
        "name": "impala.daemon.jvm.metaspace.peak_current_usage",
        "value": 30702328,
    },
    {
        "name": "impala.daemon.jvm.metaspace.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.metaspace.peak_max_usage",
        "value": -1,
    },
    {
        "name": "impala.daemon.jvm.non_heap.committed_usage",
        "value": 41353216,
    },
    {
        "name": "impala.daemon.jvm.non_heap.current_usage",
        "value": 39838816,
    },
    {
        "name": "impala.daemon.jvm.non_heap.init_usage",
        "value": 2555904,
    },
    {
        "name": "impala.daemon.jvm.non_heap.max_usage",
        "value": -1,
    },
    {
        "name": "impala.daemon.jvm.non_heap.peak_committed_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.non_heap.peak_current_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.non_heap.peak_init_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.non_heap.peak_max_usage",
        "value": 0,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.committed_usage",
        "value": 45088768,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.current_usage",
        "value": 28727992,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.init_usage",
        "value": 33554432,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.max_usage",
        "value": 339214336,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.peak_committed_usage",
        "value": 45088768,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.peak_current_usage",
        "value": 33554432,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.peak_init_usage",
        "value": 33554432,
    },
    {
        "name": "impala.daemon.jvm.ps_eden_space.peak_max_usage",
        "value": 347078656,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.committed_usage",
        "value": 62914560,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.current_usage",
        "value": 7488432,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.init_usage",
        "value": 88080384,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.max_usage",
        "value": 716177408,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.peak_committed_usage",
        "value": 88080384,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.peak_current_usage",
        "value": 7488432,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.peak_init_usage",
        "value": 88080384,
    },
    {
        "name": "impala.daemon.jvm.ps_old_gen.peak_max_usage",
        "value": 716177408,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.committed_usage",
        "value": 8912896,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.current_usage",
        "value": 7430200,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.init_usage",
        "value": 5242880,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.max_usage",
        "value": 8912896,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.peak_committed_usage",
        "value": 9437184,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.peak_current_usage",
        "value": 7430200,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.peak_init_usage",
        "value": 5242880,
    },
    {
        "name": "impala.daemon.jvm.ps_survivor_space.peak_max_usage",
        "value": 9437184,
    },
    {
        "name": "impala.daemon.jvm.total_committed_usage",
        "value": 158269440,
    },
    {
        "name": "impala.daemon.jvm.total_current_usage",
        "value": 83485440,
    },
    {
        "name": "impala.daemon.jvm.total_init_usage",
        "value": 129433600,
    },
    {
        "name": "impala.daemon.jvm.total_max_usage",
        "value": 2389704703,
    },
    {
        "name": "impala.daemon.jvm.total_peak_committed_usage",
        "value": 183959552,
    },
    {
        "name": "impala.daemon.jvm.total_peak_current_usage",
        "value": 88850888,
    },
    {
        "name": "impala.daemon.jvm.total_peak_init_usage",
        "value": 129433600,
    },
    {
        "name": "impala.daemon.jvm.total_peak_max_usage",
        "value": 2398093311,
    },
    # tcmalloc
    {
        "name": "impala.daemon.tcmalloc.in_use",
        "value": 84816816,
    },
    {
        "name": "impala.daemon.tcmalloc.pageheap.free",
        "value": 0,
    },
    {
        "name": "impala.daemon.tcmalloc.pageheap.unmapped",
        "value": 3989504,
    },
    {
        "name": "impala.daemon.tcmalloc.physical_reserved",
        "value": 96542720,
    },
    {
        "name": "impala.daemon.tcmalloc.total_reserved",
        "value": 100802560,
    },
    # thrift_server_beeswax.frontend
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.quantile",
        "value": 11,
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.quantile",
        "value": 12,
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.quantile",
        "value": 13,
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.quantile",
        "value": 14,
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.quantile",
        "value": 15,
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.quantile",
        "value": 16,
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.sum",
        "value": 18,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_time.count",
        "value": 17,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.quantile",
        "value": 3,
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.quantile",
        "value": 4,
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.quantile",
        "value": 5,
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.quantile",
        "value": 6,
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.quantile",
        "value": 7,
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.quantile",
        "value": 8,
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.sum",
        "value": 10,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.svc_thread_wait_time.count",
        "value": 9,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connection_setup_queue_size",
        "value": 2,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.connections_in_use",
        "value": 19,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.timedout_cnxn_requests",
        "value": 51,
    },
    {
        "name": "impala.daemon.thrift_server.beeswax.frontend.total_connections.count",
        "value": 20,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    # thrift_server_hiveserver2.frontend
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.quantile",
        "value": 81,
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.quantile",
        "value": 82,
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.quantile",
        "value": 83,
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.quantile",
        "value": 84,
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.quantile",
        "value": 85,
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.quantile",
        "value": 86,
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.sum",
        "value": 88,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_time.count",
        "value": 87,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.quantile",
        "value": 92,
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.quantile",
        "value": 93,
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.quantile",
        "value": 94,
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.quantile",
        "value": 95,
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.quantile",
        "value": 96,
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.quantile",
        "value": 97,
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.sum",
        "value": 99,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time.count",
        "value": 98,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connection_setup_queue_size",
        "value": 90,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.connections_in_use",
        "value": 89,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.timedout_cnxn_requests",
        "value": 91,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.frontend.total_connections.count",
        "value": 80,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    # thrift_server_hiveserver2.frontend_frontend
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.quantile",
        "value": 60,
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.quantile",
        "value": 61,
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.quantile",
        "value": 62,
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.quantile",
        "value": 63,
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.quantile",
        "value": 64,
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.quantile",
        "value": 65,
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.sum",
        "value": 67,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time.count",
        "value": 66,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.quantile",
        "value": 52,
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.quantile",
        "value": 53,
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.quantile",
        "value": 54,
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.quantile",
        "value": 55,
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.quantile",
        "value": 56,
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.quantile",
        "value": 57,
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.sum",
        "value": 59,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time.count",
        "value": 58,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connection_setup_queue_size",
        "value": 60,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.connections_in_use",
        "value": 68,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.timedout_cnxn_requests",
        "value": 100,
    },
    {
        "name": "impala.daemon.thrift_server.hiveserver2.http_frontend.total_connections.count",
        "value": 50,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    # io_mgr
    {
        "name": "impala.daemon.io_mgr.bytes_read.count",
        "value": 1000,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.bytes_written.count",
        "value": 1001,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.cached_bytes_read.count",
        "value": 1002,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.cached_file_handles.hit",
        "value": 1003,
    },
    {
        "name": "impala.daemon.io_mgr.cached_file_handles.hit_ratio_total.count",
        "value": 1004,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.cached_file_handles.miss",
        "value": 1005,
    },
    {
        "name": "impala.daemon.io_mgr.cached_file_handles.reopened.count",
        "value": 1006,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.local_bytes_read.count",
        "value": 1007,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.num_cached_file_handles",
        "value": 1008,
    },
    {
        "name": "impala.daemon.io_mgr.num_file_handles_outstanding",
        "value": 1009,
    },
    {
        "name": "impala.daemon.io_mgr.num_open_files",
        "value": 1010,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.dropped.count",
        "value": 1011,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.dropped_entries.count",
        "value": 1012,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.hit_bytes.count",
        "value": 1013,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.hit.count",
        "value": 1014,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.instant_evictions.count",
        "value": 1015,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.miss_bytes.count",
        "value": 1016,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.miss.count",
        "value": 1017,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.num_entries",
        "value": 1018,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.num_writes.count",
        "value": 1019,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.io_mgr.remote_data_cache.total",
        "value": 1020,
    },
    {
        "name": "impala.daemon.io_mgr.short_circuit.read.count",
        "value": 1021,
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.admission_controller.executor_group_num_queries_executing_default",
    },
    {
        "name": "impala.daemon.admission_controller.total_dequeue_failed_coordinator_limited.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.buffer_pool.clean_page_bytes",
    },
    {
        "name": "impala.daemon.buffer_pool.clean_pages",
    },
    {
        "name": "impala.daemon.buffer_pool.clean_pages_limit",
    },
    {
        "name": "impala.daemon.buffer_pool.free_buffer",
    },
    {
        "name": "impala.daemon.buffer_pool.free_buffers",
    },
    {
        "name": "impala.daemon.buffer_pool.limit",
    },
    {
        "name": "impala.daemon.buffer_pool.reserved",
    },
    {
        "name": "impala.daemon.buffer_pool.system_allocated",
    },
    {
        "name": "impala.daemon.buffer_pool.unused_reservation",
    },
    {
        "name": "impala.daemon.catalog_cache.average_load_time",
    },
    {
        "name": "impala.daemon.catalog_cache.eviction.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.hit.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.hit_rate",
    },
    {
        "name": "impala.daemon.catalog_cache.load.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.load_exception.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.load_exception_rate",
    },
    {
        "name": "impala.daemon.catalog_cache.load_success.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.miss.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.miss_rate",
    },
    {
        "name": "impala.daemon.catalog_cache.request.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog_cache.total_load_time.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.catalog.catalog_object_version_lower_bound",
    },
    {
        "name": "impala.daemon.catalog.curr_topic",
    },
    {
        "name": "impala.daemon.catalog.curr_version",
    },
    {
        "name": "impala.daemon.catalog.num_databases",
    },
    {
        "name": "impala.daemon.catalog.num_tables",
    },
    {
        "name": "impala.daemon.catalog.server_client_cache.clients_in_use",
    },
    {
        "name": "impala.daemon.catalog.server_client_cache.total_clients",
    },
    {
        "name": "impala.daemon.cluster_membership.backends.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.cluster_membership.executor_groups.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.cluster_membership.executor_groups_total_healthy.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.external_data_source_class_cache.hits.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.external_data_source_class_cache.misses.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.mem_tracker.process.bytes_freed_by_last_gc",
    },
    {
        "name": "impala.daemon.mem_tracker.process.bytes_over_limit",
    },
    {
        "name": "impala.daemon.mem_tracker.process.limit",
    },
    {
        "name": "impala.daemon.mem_tracker.process.num_gcs.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.memory.mapped",
    },
    {
        "name": "impala.daemon.memory.rss",
    },
    {
        "name": "impala.daemon.memory.total_used",
    },
    {
        "name": "impala.daemon.request_pool_service_resolve_pool_duration.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.senders_blocked_on_recvr_creation",
    },
    {
        "name": "impala.daemon.num_queries_executed.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.num_queries_executing",
    },
    {
        "name": "impala.daemon.ddl_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.ddl_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.ddl_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.ddl_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.ddl_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.ddl_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.ddl_durations_ms.sum",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.ddl_durations_ms.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.hedged_read_ops.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.hedged_read_ops.win.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.num_files_open_for_insert",
    },
    {
        "name": "impala.daemon.num_fragments.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.num_fragments_in_flight",
    },
    {
        "name": "impala.daemon.num_open_beeswax_sessions",
    },
    {
        "name": "impala.daemon.num_open_hiveserver2_sessions",
    },
    {
        "name": "impala.daemon.num_queries.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.num_queries_expired.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.num_queries_registered",
    },
    {
        "name": "impala.daemon.num_queries_spilled.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.num_sessions_expired.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.query_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.2"],
    },
    {
        "name": "impala.daemon.query_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.5"],
    },
    {
        "name": "impala.daemon.query_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.7"],
    },
    {
        "name": "impala.daemon.query_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.9"],
    },
    {
        "name": "impala.daemon.query_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.95"],
    },
    {
        "name": "impala.daemon.query_durations_ms.quantile",
        "tags": TAGS + ["quantile:0.999"],
    },
    {
        "name": "impala.daemon.query_durations_ms.sum",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.query_durations_ms.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.resultset_cache.total_bytes",
    },
    {
        "name": "impala.daemon.resultset_cache.total_num_rows",
    },
    {
        "name": "impala.daemon.scan_ranges_num_missing_volume_id.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.scan_ranges.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.simple_scheduler.assignments.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.simple_scheduler.local_assignments.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.statestore_subscriber.heartbeat_interval_time.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.statestore_subscriber.last_recovery_duration",
    },
    {
        "name": "impala.daemon.statestore_subscriber.num_connection_failures.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.statestore_subscriber.statestore_client_cache.clients_in_use",
    },
    {
        "name": "impala.daemon.statestore_subscriber.statestore_client_cache.total_clients",
    },
    {
        "name": "impala.daemon.statestore_subscriber.topic.update_duration.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.statestore_subscriber.topic.update_interval_time.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.thread_manager.running_threads",
    },
    {
        "name": "impala.daemon.thread_manager.total_threads_created",
    },
    {
        "name": "impala.daemon.tmp_file_mgr.active_scratch_dirs",
    },
    {
        "name": "impala.daemon.tmp_file_mgr.scratch_space_bytes_used",
    },
    {
        "name": "impala.daemon.tmp_file_mgr.scratch_space_bytes_used_dir_0",
    },
    {
        "name": "impala.daemon.tmp_file_mgr.scratch_space_bytes_used_high_water_mark",
    },
    {
        "name": "impala.daemon.total_senders_blocked_on_recvr_creation.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.total_senders_timedout_waiting_for_recvr_creation.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
    },
    {
        "name": "impala.daemon.rpcs_queue_overflow.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["daemon_service:control_service"],
    },
    {
        "name": "impala.daemon.rpcs_queue_overflow.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["daemon_service:data_stream_service"],
    },
    {
        "name": "impala.daemon.mem_tracker.process.current_usage",
        "tags": TAGS + ["daemon_service:control_service"],
    },
    {
        "name": "impala.daemon.mem_tracker.process.current_usage",
        "tags": TAGS + ["daemon_service:data_stream_service"],
    },
    {
        "name": "impala.daemon.mem_tracker.process.peak_usage",
        "tags": TAGS + ["daemon_service:control_service"],
    },
    {
        "name": "impala.daemon.mem_tracker.process.peak_usage",
        "tags": TAGS + ["daemon_service:data_stream_service"],
    },
    {
        "name": "impala.daemon.statestore_subscriber.processing_time.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["topic:catalog_update"],
    },
    {
        "name": "impala.daemon.statestore_subscriber.processing_time.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["topic:impala_membership"],
    },
    {
        "name": "impala.daemon.statestore_subscriber.processing_time.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["topic:impala_request_queue"],
    },
    {
        "name": "impala.daemon.statestore_subscriber.update_interval.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["topic:catalog_update"],
    },
    {
        "name": "impala.daemon.statestore_subscriber.update_interval.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["topic:impala_membership"],
    },
    {
        "name": "impala.daemon.statestore_subscriber.update_interval.count",
        "type": AggregatorStub.MONOTONIC_COUNT,
        "tags": TAGS + ["topic:impala_request_queue"],
    },
]
