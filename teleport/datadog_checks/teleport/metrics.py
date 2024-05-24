# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

COMMON_METRICS_MAP = {
    "process_state": "common.process_state",
    "certificate_mismatch": "common.certificate_mismatch",
    "rx": "common.rx",
    "server_interactive_sessions_total": "common.server_interactive_sessions_total",
    "teleport_build_info": "common.teleport_build_info",
    "teleport_cache_events": "common.teleport_cache_events",
    "teleport_cache_stale_events": "common.teleport_cache_stale_events",
    "tx": "common.tx",
}

PROXY_METRICS_MAP = {
    "failed_connect_to_node_attempts": "proxy.failed_connect_to_node_attempts",
    "failed_login_attempts": "proxy.failed_login_attempts",
    "grpc_client_started": "proxy.grpc_client_started",
    "grpc_client_handled": "proxy.grpc_client_handled",
    "grpc_client_msg_received": "proxy.grpc_client_msg_received",
    "grpc_client_msg_sent": "proxy.grpc_client_msg_sent",
    "proxy_connection_limit_exceeded": "proxy.connection_limit_exceeded",
    "proxy_peer_client_dial_error": "proxy.peer_client_dial_error",
    "proxy_peer_server_connections": "proxy.peer_server_connections",
    "proxy_peer_client_rpc": {"name": "proxy.peer_client_rpc", "type": "native_dynamic"},
    "proxy_peer_client_rpc_duration_seconds": "proxy.peer_client_rpc_duration_seconds",
    "proxy_peer_client_message_sent_size": "proxy.peer_client_message_sent_size",
    "proxy_peer_client_message_received_size": "proxy.peer_client_message_received_size",
    "proxy_peer_server_rpc": "proxy.peer_server_rpc",
    "proxy_peer_server_rpc_duration_seconds": "proxy.peer_server_rpc_duration_seconds",
    "proxy_peer_server_message_sent_size": "proxy.peer_server_message_sent_size",
    "proxy_peer_server_message_received_size": "proxy.peer_server_message_received_size",
    "proxy_ssh_sessions_total": "proxy.ssh_sessions_total",
    "proxy_missing_ssh_tunnels": "proxy.missing_ssh_tunnels",
    "remote_clusters": "proxy.remote_clusters",
    "teleport_connect_to_node_attempts": "proxy.teleport_connect_to_node_attempts",
    "teleport_reverse_tunnels_connected": "proxy.teleport_reverse_tunnels_connected",
    "trusted_clusters": "proxy.trusted_clusters",
    "teleport_proxy_db_connection_setup_time_seconds": "proxy.teleport_proxy_db_connection_setup_time_seconds",
    "teleport_proxy_db_connection_dial_attempts": "proxy.teleport_proxy_db_connection_dial_attempts",
    "teleport_proxy_db_connection_dial_failures": "proxy.teleport_proxy_db_connection_dial_failures",
    "teleport_proxy_db_attempted_servers_total": "proxy.teleport_proxy_db_attempted_servers_total",
    "teleport_proxy_db_connection_tls_config_time_seconds": "proxy.teleport_proxy_db_connection_tls_config_time_seconds",  # noqa: E501
    "teleport_proxy_db_active_connections_total": "proxy.teleport_proxy_db_active_connections_total",
}

AUTH_SERVICE_METRICS_MAP = {
    "auth_generate_requests_throttled": "auth.generate_requests_throttled",
    "auth_generate_requests": {"name": "auth.generate_requests", "type": "native_dynamic"},
    "auth_generate_seconds": "auth.generate_seconds",
    "grpc_server_handled": "auth.grpc_server_handled",
    "grpc_server_msg_received": "auth.grpc_server_msg_received",
    "grpc_server_msg_sent": "auth.grpc_server_msg_sent",
    "grpc_server_started": "auth.grpc_server_started",
    "cluster_name_not_found": "auth.cluster_name_not_found",
    "teleport_connected_resources": "auth.connected_resources",
    "teleport_registered_servers": "auth.registered_servers",
    "teleport_registered_servers_by_install_methods": "auth.registered_servers_by_install_methods",
    "user_login": "auth.user_login",
    "teleport_migrations": "auth.migrations",
    "watcher_event_sizes": "auth.watcher_event_sizes",
    "watcher_events": "auth.watcher_events",
}

AUTH_AUDIT_LOG_METRICS_MAP = {
    "audit_failed_disk_monitoring": "auth.audit_log.failed_disk_monitoring",
    "audit_failed_emit_events": "auth.audit_log.failed_emit_events",
    "audit_percentage_disk_space_used": "auth.audit_log.percentage_disk_space_used",
    "audit_server_open_files": "auth.audit_log.server_open_files",
    "teleport_audit_emit_events": "auth.audit_log.emit_events",
    "teleport_audit_parquetlog_batch_processing_seconds": "auth.audit_log.parquetlog_batch_processing_seconds",
    "teleport_audit_parquetlog_s3_flush_seconds": "auth.audit_log.parquetlog_s3_flush_seconds",
    "teleport_audit_parquetlog_delete_events_seconds": "auth.audit_log.parquetlog_delete_events_seconds",
    "teleport_audit_parquetlog_batch_size": "auth.audit_log.parquetlog_batch_size",
    "teleport_audit_parquetlog_batch_count": "auth.audit_log.parquetlog_batch_count",
    "teleport_audit_parquetlog_last_processed_timestamp": "auth.audit_log.parquetlog_last_processed_timestamp",
    "teleport_audit_parquetlog_age_oldest_processed_message": "auth.audit_log.parquetlog_age_oldest_processed_message",
    "teleport_audit_parquetlog_errors_from_collect_count": "auth.audit_log.parquetlog_errors_from_collect_count",
}

AUTH_BACKEND_S3_METRICS_MAP = {
    "s3_requests": "auth.backend.s3_requests",
    "s3_requests_seconds": "auth.backend.s3_requests_seconds",
}

AUTH_BACKEND_CACHE_METRICS_MAP = {
    "backend_batch_read_requests": "auth.cache.backend_batch_read_requests",
    "backend_batch_read_seconds": "auth.cache.backend_batch_read_seconds",
    "backend_batch_write_requests": "auth.cache.backend_batch_write_requests",
    "backend_batch_write_seconds": "auth.cache.backend_batch_write_seconds",
    "backend_read_requests": "auth.cache.backend_read_requests",
    "backend_read_seconds": "auth.cache.backend_read_seconds",
    "backend_requests": "auth.cache.backend_requests",
    "backend_write_requests": "auth.cache.backend_write_requests",
    "backend_write_seconds": "auth.cache.backend_write_seconds",
    "watcher_event_sizes": "auth.cache.watcher_event_sizes",
    "watcher_events": "auth.cache.watcher_events",
}

AUTH_BACKEND_DYNAMO_METRICS_MAP = {
    "dynamo_requests": "auth.backend.dynamo_requests",
    "dynamo_requests_seconds": "auth.backend.dynamo_requests_seconds",
}

AUTH_BACKEND_FIRESTORE_METRICS_MAP = {
    "firestore_events_backend_batch_read_requests": "auth.backend.firestore_events_backend_batch_read_requests",
    "firestore_events_backend_batch_read_seconds": "auth.backend.firestore_events_backend_batch_read_seconds",
    "firestore_events_backend_batch_write_requests": "auth.backend.firestore_events_backend_batch_write_requests",
    "firestore_events_backend_batch_write_seconds": "auth.backend.firestore_events_backend_batch_write_seconds",
    "firestore_events_backend_read_requests": "auth.backend.firestore_events_backend_read_requests",
    "firestore_events_backend_read_seconds": "auth.backend.firestore_events_backend_read_seconds",
    "firestore_events_backend_requests": "auth.backend.firestore_events_backend_requests",
    "firestore_events_backend_write_requests": "auth.backend.firestore_events_backend_write_requests",
    "firestore_events_backend_write_seconds": "auth.backend.firestore_events_backend_write_seconds",
}

AUTH_GCP_GCS_METRICS_MAP = {
    "gcs_event_storage_downloads_seconds": "auth.backend.gcs_event_storage_downloads_seconds",
    "gcs_event_storage_downloads": "auth.backend.gcs_event_storage_downloads",
    "gcs_event_storage_uploads_seconds": "auth.backend.gcs_event_storage_uploads_seconds",
    "gcs_event_storage_uploads": "auth.backend.gcs_event_storage_uploads",
}

AUTH_ETCD_METRICS_MAP = {
    "etcd_backend_batch_read_requests": "auth.backend.etcd_backend_batch_read_requests",
    "etcd_backend_batch_read_seconds": "auth.backend.etcd_backend_batch_read_seconds",
    "etcd_backend_read_requests": "auth.backend.etcd_backend_read_requests",
    "etcd_backend_read_seconds": "auth.backend.etcd_backend_read_seconds",
    "etcd_backend_tx_requests": "auth.backend.etcd_backend_tx_requests",
    "etcd_backend_tx_seconds": "auth.backend.etcd_backend_tx_seconds",
    "etcd_backend_write_requests": "auth.backend.etcd_backend_write_requests",
    "etcd_backend_write_seconds": "auth.backend.etcd_backend_write_seconds",
    "teleport_etcd_events": "auth.backend.etcd_teleport_etcd_events",
    "teleport_etcd_event_backpressure": "auth.backend.etcd_teleport_etcd_event_backpressure",
}


AUTH_METRICS_MAP = {
    **AUTH_SERVICE_METRICS_MAP,
    **AUTH_AUDIT_LOG_METRICS_MAP,
    **AUTH_BACKEND_S3_METRICS_MAP,
    **AUTH_BACKEND_CACHE_METRICS_MAP,
    **AUTH_BACKEND_DYNAMO_METRICS_MAP,
    **AUTH_BACKEND_FIRESTORE_METRICS_MAP,
    **AUTH_GCP_GCS_METRICS_MAP,
    **AUTH_ETCD_METRICS_MAP,
}  # noqa: E501

SSH_METRICS_MAP = {
    "user_max_concurrent_sessions_hit": "ssh.user_max_concurrent_sessions_hit",
}

KUBERNETES_METRICS_MAP = {
    "teleport_kubernetes_client_in_flight_requests": "kubernetes.client_in_flight_requests",
    "teleport_kubernetes_client_requests": "kubernetes.client_requests",
    "teleport_kubernetes_client_tls_duration_seconds": "kubernetes.client_tls_duration_seconds",
    "teleport_kubernetes_client_got_conn_duration_seconds": "kubernetes.client_got_conn_duration_seconds",
    "teleport_kubernetes_client_first_byte_response_duration_seconds": "kubernetes.client_first_byte_response_duration_seconds",  # noqa: E501
    "teleport_kubernetes_client_request_duration_seconds": "kubernetes.client_request_duration_seconds",
    "teleport_kubernetes_server_in_flight_requests": "kubernetes.server_in_flight_requests",
    "teleport_kubernetes_server_api_requests": "kubernetes.server_api_requests",
    "teleport_kubernetes_server_request_duration_seconds": "kubernetes.server_request_duration_seconds",
    "teleport_kubernetes_server_response_size_bytes": "kubernetes.server_response_size_bytes",
    "teleport_kubernetes_server_exec_in_flight_sessions": "kubernetes.server_exec_in_flight_sessions",
    "teleport_kubernetes_server_exec_sessions": "kubernetes.server_exec_sessions",
    "teleport_kubernetes_server_portforward_in_flight_sessions": "kubernetes.server_portforward_in_flight_sessions",  # noqa: E501
    "teleport_kubernetes_server_portforward_sessions": "kubernetes.server_portforward_sessions",
    "teleport_kubernetes_server_join_in_flight_sessions": "kubernetes.server_join_in_flight_sessions",
    "teleport_kubernetes_server_join_sessions": "kubernetes.server_join_sessions",
}

DATABASE_METRICS_MAP = {
    "teleport_db_messages_from_client": "db.messages_from_client",
    "teleport_db_messages_from_server": "db.messages_from_server",
    "teleport_db_method_call_count": "db.method_call_count",
    "teleport_db_method_call_latency_seconds": "db.method_call_latency_seconds",
    "teleport_db_initialized_connections": "db.initialized_connections",
    "teleport_db_active_connections_total": "db.active_connections_total",
    "teleport_db_connection_durations_seconds": "db.connection_durations_seconds",
    "teleport_db_connection_setup_time_seconds": "db.connection_setup_time_seconds",
    "teleport_db_errors": "db.errors",
}

BPF_METRICS_MAP = {
    "bpf_lost_command_events": "bpf.lost_command_events",
    "bpf_lost_disk_events": "bpf.lost_disk_events",
    "bpf_lost_network_events": "bpf.lost_network_events",
}

PROMETHEUS_METRICS_MAP = {
    "promhttp_metric_handler_requests_in_flight": "prom.http_metric_handler_requests_in_flight",
    "promhttp_metric_handler_requests": "prom.http_metric_handler_requests",
}


METRIC_MAP = {
    **COMMON_METRICS_MAP,
    **PROXY_METRICS_MAP,
    **AUTH_METRICS_MAP,
    **SSH_METRICS_MAP,
    **KUBERNETES_METRICS_MAP,
    **DATABASE_METRICS_MAP,
    **BPF_METRICS_MAP,
    **PROMETHEUS_METRICS_MAP,
}

METRIC_MAP_BY_SERVICE = {
    **{metric: "teleport" for metric in COMMON_METRICS_MAP.keys()},
    **{metric: "proxy" for metric in PROXY_METRICS_MAP.keys()},
    **{metric: "auth" for metric in AUTH_METRICS_MAP.keys()},
    **{metric: "ssh" for metric in SSH_METRICS_MAP.keys()},
    **{metric: "kubernetes" for metric in KUBERNETES_METRICS_MAP.keys()},
    **{metric: "database" for metric in DATABASE_METRICS_MAP.keys()},
}
