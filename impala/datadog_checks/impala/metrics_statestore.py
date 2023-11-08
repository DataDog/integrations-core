# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# E501: line too long (XXX > 120 characters)
# ruff: noqa: E501
from datadog_checks.impala.common import counter, gauge

STATESTORE_METRIC_MAP = {
    "impala_statestore_live_backends": "statestore.live_backends",
    "impala_statestore_total_key_size_bytes": "statestore.total_key_size",
    "impala_statestore_total_value_size_bytes": "statestore.total_value_size",
    "impala_statestore_topic_update_durations_total": counter("statestore.topic_update_durations"),
    "impala_statestore_topic_update_durations_last": gauge("statestore.last_topic_update_durations"),
    "impala_statestore_topic_update_durations_min": gauge("statestore.min_topic_update_durations"),
    "impala_statestore_topic_update_durations_max": gauge("statestore.max_topic_update_durations"),
    "impala_statestore_topic_update_durations_mean": gauge("statestore.mean_topic_update_durations"),
    "impala_statestore_total_topic_size_bytes": "statestore.total_topic_size",
    "impala_statestore_priority_topic_update_durations_total": counter("statestore.priority_topic_update_durations"),
    "impala_statestore_priority_topic_update_durations_last": gauge("statestore.last_priority_topic_update_durations"),
    "impala_statestore_priority_topic_update_durations_min": gauge("statestore.min_priority_topic_update_durations"),
    "impala_statestore_priority_topic_update_durations_max": gauge("statestore.max_priority_topic_update_durations"),
    "impala_statestore_priority_topic_update_durations_mean": gauge("statestore.mean_priority_topic_update_durations"),
    "impala_statestore_heartbeat_durations_total": counter("statestore.heartbeat_durations"),
    "impala_rpc_method_statestore_StatestoreService_RegisterSubscriber_call_duration": "statestore.register_subscriber_call_duration",
    # thrift_server
    "impala_thrift_server_StatestoreService_connection_setup_time": "statestore.thrift_server.connection_setup_time",
    "impala_thrift_server_StatestoreService_svc_thread_wait_time": "statestore.thrift_server.svc_thread_wait_time",
    "impala_thrift_server_StatestoreService_connection_setup_queue_size": "statestore.thrift_server.connection_setup_queue_size",
    "impala_thrift_server_StatestoreService_connections_in_use": "statestore.thrift_server.connections_in_use",
    "impala_thrift_server_StatestoreService_timedout_cnxn_requests": "statestore.thrift_server.timedout_cnxn_requests",
    "impala_thrift_server_StatestoreService_total_connections": "statestore.thrift_server.total_connections",
    # subscriber
    "impala_subscriber_heartbeat_client_cache_clients_in_use": "statestore.subscriber.heartbeat.client_cache.clients_in_use",
    "impala_subscriber_heartbeat_client_cache_total_clients": "statestore.subscriber.heartbeat.client_cache.total_clients",
    "impala_subscriber_update_state_client_cache_clients_in_use": "statestore.subscriber.update_state.client_cache.clients_in_use",
    "impala_subscriber_update_state_client_cache_total_clients": "statestore.subscriber.update_state.client_cache.total_clients",
    # thread_manager
    "impala_thread_manager_total_threads_created": "statestore.thread_manager.total_threads_created",
    "impala_thread_manager_running_threads": "statestore.thread_manager.running_threads",
    # memory
    "impala_memory_rss": "statestore.memory.rss",
    "impala_memory_total_used": "statestore.memory.total_used",
    "impala_memory_mapped_bytes": "statestore.memory.mapped",
    # tcmalloc
    "impala_tcmalloc_physical_bytes_reserved": "statestore.tcmalloc.physical_reserved",
    "impala_tcmalloc_bytes_in_use": "statestore.tcmalloc.in_use",
    "impala_tcmalloc_total_bytes_reserved": "statestore.tcmalloc.total_reserved",
    "impala_tcmalloc_pageheap_free_bytes": "statestore.tcmalloc.pageheap.free",
    "impala_tcmalloc_pageheap_unmapped_bytes": "statestore.tcmalloc.pageheap.unmapped",
}
