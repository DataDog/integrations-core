# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://github.com/Kong/kong-plugin-prometheus/blob/1.2.0/kong/plugins/prometheus/exporter.lua
METRIC_MAP = {
    'kong_bandwidth': 'bandwidth',
    'kong_datastore_reachable': {
        'name': 'datastore.reachable',
        'type': 'service_check',
        'status_map': {'0': 'CRITICAL', '1': 'OK'},
    },
    'kong_http_consumer_status': 'http.consumer.status',
    'kong_http_status': 'http.status',
    'kong_latency': 'latency',
    'kong_memory_lua_shared_dict_bytes': 'memory.lua.shared_dict.bytes',
    'kong_memory_lua_shared_dict_total_bytes': 'memory.lua.shared_dict.total_bytes',
    'kong_nginx_http_current_connections': 'nginx.http.current_connections',
    'kong_nginx_stream_current_connections': 'nginx.stream.current_connections',
    'kong_stream_status': 'stream.status',
}
