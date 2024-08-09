# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRICS_MAP = {
    "process_cpu_seconds": "process.cpu_seconds",  # counter
    "process_max_fds": "process.max_fds",  # gauge
    "process_open_fds": "process.open_fds",  # gauge
    "process_resident_memory_bytes": "process.resident_memory_bytes",  # gauge
    "process_start_time_seconds": "process.start_time_seconds",  # gauge
    "process_virtual_memory_bytes": "process.virtual_memory_bytes",  # gauge
    "process_virtual_memory_max_bytes": "process.virtual_memory_max_bytes",  # gauge
    "promhttp_metric_handler_requests_in_flight": "promhttp.metric_handler_requests_in_flight",  # gauge
    "promhttp_metric_handler_requests": "promhttp.metric_handler_requests",  # counter
    "rest_client_rate_limiter_duration_seconds": "rest.client_rate_limiter_duration_seconds",  # histogram
    "rest_client_request_latency_seconds": "rest.client_request_latency_seconds",  # histogram
    "rest_client_requests": "rest.client_requests",  # counter
}
