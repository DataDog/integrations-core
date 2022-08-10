# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://boundary-git-new-metrics-doc-hashicorp.vercel.app/docs/operations/metrics
METRIC_MAP = {
    'boundary_build_info': {'name': 'version', 'type': 'metadata', 'label': 'version'},
    'boundary_cluster_client_grpc_request_duration_seconds': 'cluster.client.grpc.request_duration_seconds',
    'boundary_controller_api_http_request_duration_seconds': 'controller.api.http.request_duration_seconds',
    'boundary_controller_api_http_request_size_bytes': 'controller.api.http.request_size_bytes',
    'boundary_controller_api_http_response_size_bytes': 'controller.api.http.response_size_bytes',
    'boundary_controller_cluster_grpc_request_duration_seconds': 'controller.cluster.grpc.request_duration_seconds',
    'boundary_worker_proxy_http_write_header_duration_seconds': 'worker.proxy.http.write_header_duration_seconds',
    'boundary_worker_proxy_websocket_active_connections': 'worker.proxy.websocket.active_connections',
    'boundary_worker_proxy_websocket_received_bytes': 'worker.proxy.websocket.received_bytes',
    'boundary_worker_proxy_websocket_sent_bytes': 'worker.proxy.websocket.sent_bytes',
}
