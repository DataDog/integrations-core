# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

COUNT_METRICS = {
    "proxy.node.restarts.proxy.restart_count": "node.restarts.proxy.restart_count",
    "proxy.process.http.origin_server_total_request_bytes": "process.http.origin_server_total_request_bytes",
    "proxy.process.http.origin_server_total_response_bytes": "process.http.origin_server_total_response_bytes",
    "proxy.process.user_agent_total_bytes": "process.user_agent_total_bytes",
    "proxy.process.origin_server_total_bytes": "process.origin_server_total_bytes",
    "proxy.process.cache.volume_0.direntries.total": "process.cache.volume_0.direntries.total",
    "proxy.process.cache.volume_0.direntries.used": "process.cache.volume_0.direntries.used",
}

GAUGE_METRICS = {
    "proxy.node.restarts.manager.start_time": "node.restarts.manager.start_time",
    "proxy.node.restarts.proxy.start_time": "node.restarts.proxy.start_time",
    "proxy.node.restarts.proxy.cache_ready_time": "node.restarts.proxy.cache_ready_time",
    "proxy.node.restarts.proxy.stop_time": "node.restarts.proxy.stop_time",
}
