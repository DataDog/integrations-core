# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy


def metric_with_type(name, type):
    return {"name": name, "type": type}


def gauge(name):
    return metric_with_type(name, "gauge")


# https://vertx.io/docs/vertx-micrometer-metrics/java/#_vert_x_core_tools_metrics
VERTX_METRICS_MAP = {
    "vertx_http_client_active_connections": "vertx.http_client.active_connections",
    "vertx_http_client_active_requests": "vertx.http_client.active_requests",
    "vertx_http_client_active_ws_connections": "vertx.http_client.active_ws_connections",
    "vertx_http_client_bytes_read": "vertx.http_client.bytes_read",
    "vertx_http_client_bytes_written": "vertx.http_client.bytes_written",
    "vertx_http_client_errors": "vertx.http_client.errors",
    "vertx_http_client_queue_pending": "vertx.http_client.queue_pending",
    "vertx_http_client_queue_time_seconds": "vertx.http_client.queue_time_seconds",
    "vertx_http_client_queue_time_seconds_max": "vertx.http_client.queue_time_seconds.max",
    "vertx_http_client_request_bytes": "vertx.http_client.request_bytes",
    "vertx_http_client_request_bytes_max": "vertx.http_client.request_bytes.max",
    "vertx_http_client_requests": "vertx.http_client.requests",
    "vertx_http_client_response_bytes": "vertx.http_client.response_bytes",
    "vertx_http_client_response_bytes_max": "vertx.http_client.response_bytes.max",
    "vertx_http_client_response_time_seconds": "vertx.http_client.response_time_seconds",
    "vertx_http_client_response_time_seconds_max": "vertx.http_client.response_time_seconds.max",
    "vertx_http_client_responses": "vertx.http_client.responses",
    "vertx_http_server_active_connections": "vertx.http_server.active_connections",
    "vertx_http_server_active_requests": "vertx.http_server.active_requests",
    "vertx_http_server_active_ws_connections": "vertx.http_server.active_ws_connections",
    "vertx_http_server_bytes_read": "vertx.http_server.bytes_read",
    "vertx_http_server_bytes_written": "vertx.http_server.bytes_written",
    "vertx_http_server_errors": "vertx.http_server.errors",
    "vertx_http_server_request_bytes": "vertx.http_server.request_bytes",
    "vertx_http_server_request_bytes_max": "vertx.http_server.request_bytes.max",
    "vertx_http_server_request_resets": "vertx.http_server.request_resets",
    "vertx_http_server_requests": "vertx.http_server.requests",
    "vertx_http_server_response_bytes": "vertx.http_server.response_bytes",
    "vertx_http_server_response_bytes_max": "vertx.http_server.response_bytes.max",
    "vertx_http_server_response_time_seconds": "vertx.http_server.response_time_seconds",
    "vertx_http_server_response_time_seconds_max": "vertx.http_server.response_time_seconds.max",
    "vertx_pool_completed": "vertx.pool.completed",
    "vertx_pool_in_use": "vertx.pool.in_use",
    "vertx_pool_queue_pending": "vertx.pool.queue_pending",
    "vertx_pool_queue_time_seconds": "vertx.pool.queue_time_seconds",
    "vertx_pool_queue_time_seconds_max": "vertx.pool.queue_time_seconds.max",
    "vertx_pool_ratio": "vertx.pool.ratio",
    "vertx_pool_usage_seconds": "vertx.pool.usage_seconds",
    "vertx_pool_usage_seconds_max": "vertx.pool.usage_seconds.max",
}

COMMON_METRICS_MAP = {
    "jvm_buffer_count_buffers": "jvm.buffer.count_buffers",
    "jvm_buffer_memory_used_bytes": "jvm.buffer.memory_used_bytes",
    "jvm_buffer_total_capacity_bytes": "jvm.buffer.total_capacity_bytes",
    "jvm_classes_loaded_classes": "jvm.classes.loaded_classes",
    "jvm_classes_unloaded_classes": "jvm.classes.unloaded_classes",
    "jvm_gc_live_data_size_bytes": "jvm.gc.live_data_size_bytes",
    "jvm_gc_max_data_size_bytes": "jvm.gc.max_data_size_bytes",
    "jvm_gc_memory_allocated_bytes": "jvm.gc.memory_allocated_bytes",
    "jvm_gc_memory_promoted_bytes": "jvm.gc.memory_promoted_bytes",
    "jvm_gc_pause_seconds": "jvm.gc.pause_seconds",
    "jvm_gc_pause_seconds_max": "jvm.gc.pause_seconds.max",
    "jvm_memory_committed_bytes": "jvm.memory.committed_bytes",
    "jvm_memory_max_bytes": "jvm.memory.max_bytes",
    "jvm_memory_used_bytes": "jvm.memory.used_bytes",
    "jvm_threads_daemon_threads": "jvm.threads.daemon_threads",
    "jvm_threads_live_threads": "jvm.threads.live_threads",
    "jvm_threads_peak_threads": "jvm.threads.peak_threads",
    "jvm_threads_states_threads": "jvm.threads.states_threads",
    "process_cpu_usage": "process.cpu_usage",
    "strimzi_reconciliations": "reconciliations",
    "strimzi_reconciliations_duration_seconds": "reconciliations.duration_seconds",
    "strimzi_reconciliations_duration_seconds_max": "reconciliations.duration_seconds.max",
    "strimzi_reconciliations_failed": "reconciliations.failed",
    "strimzi_reconciliations_locked": "reconciliations.locked",
    "strimzi_reconciliations_periodical": "reconciliations.periodical",
    "strimzi_reconciliations_successful": "reconciliations.successful",
    "strimzi_resource_state": "resource.state",
    "strimzi_resources": "resources",
    "strimzi_resources_paused": "resources.paused",
    "system_cpu_count": gauge("system.cpu_count"),
    "system_cpu_usage": "system.cpu_usage",
    "system_load_average_1m": "system.load_average_1m",
}

CLUSTER_OPERATOR_METRICS_MAP = {
    "strimzi_reconciliations_already_enqueued": "reconciliations.already_enqueued",
}
CLUSTER_OPERATOR_METRICS_MAP.update(COMMON_METRICS_MAP)
CLUSTER_OPERATOR_METRICS_MAP.update(VERTX_METRICS_MAP)

TOPIC_OPERATOR_METRICS_MAP = copy.deepcopy(COMMON_METRICS_MAP)
TOPIC_OPERATOR_METRICS_MAP.update(VERTX_METRICS_MAP)

USER_OPERATOR_METRICS_MAP = copy.deepcopy(COMMON_METRICS_MAP)
