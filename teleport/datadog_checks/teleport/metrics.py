# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

COMMON_METRICS_MAP = {
    "process_state": "common.process.state",
    "certificate_mismatch": "common.certificate_mismatch",
    "rx": "common.rx",
    "server_interactive_sessions_total": "common.server_interactive_sessions_total",
    "teleport_build_info": "common.teleport.build_info",
    "teleport_cache_events": "common.teleport.cache_events",
    "teleport_cache_stale_events": "common.teleport.cache_stale_events",
    "tx": "common.tx",
}

PROXY_METRICS_MAP = {
    "failed_connect_to_node_attempts": "proxy.failed_connect_to_node_attempts",
    "failed_login_attempts": "proxy.failed_login_attempts",
    "grpc_client_started": "proxy.grpc.client.started",
    "grpc_client_handled": "proxy.grpc.client.handled",
    "grpc_client_msg_received": "proxy.grpc.client.msg_received",
    "grpc_client_msg_sent": "proxy.grpc.client.msg_sent",
    "proxy_connection_limit_exceeded": "proxy.connection_limit_exceeded",
    "proxy_peer_client_dial_error": "proxy.peer_client.dial_error",
    "proxy_peer_server_connections": "proxy.peer_server.connections",
    "proxy_peer_client_rpc": {"name": "proxy.peer_client.rpc", "type": "native_dynamic"},
    "proxy_peer_client_rpc_duration_seconds": "proxy.peer_client.rpc_duration_seconds",
    "proxy_peer_client_message_sent_size": "proxy.peer_client.message_sent_size",
    "proxy_peer_client_message_received_size": "proxy.peer_client.message_received_size",
    "proxy_peer_server_rpc": "proxy.peer_server.rpc",
    "proxy_peer_server_rpc_duration_seconds": "proxy.peer_server.rpc_duration_seconds",
    "proxy_peer_server_message_sent_size": "proxy.peer_server.message_sent_size",
    "proxy_peer_server_message_received_size": "proxy.peer_server.message_received_size",
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
    "grpc_server_handled": "auth.grpc.server.handled",
    "grpc_server_msg_received": "auth.grpc.server.msg_received",
    "grpc_server_msg_sent": "auth.grpc.server.msg_sent",
    "grpc_server_started": "auth.grpc.server.started",
    "cluster_name_not_found": "auth.cluster_name_not_found",
    "teleport_connected_resources": "auth.connected.resources",
    "teleport_registered_servers": "auth.registered.servers",
    "teleport_registered_servers_by_install_methods": "auth.registered.servers_by_install_methods",
    "user_login": "auth.user.login",
    "teleport_migrations": "auth.migrations",
    "watcher_event_sizes": "auth.watcher.event_sizes",
    "watcher_events": "auth.watcher.events",
}

AUTH_AUDIT_LOG_METRICS_MAP = {
    "audit_failed_disk_monitoring": "auth.audit_log.failed_disk_monitoring",
    "audit_failed_emit_events": "auth.audit_log.failed_emit_events",
    "audit_percentage_disk_space_used": "auth.audit_log.percentage_disk_space_used",
    "audit_server_open_files": "auth.audit_log.server_open_files",
    "teleport_audit_emit_events": "auth.audit_log.emit_events",
    "teleport_audit_parquetlog_batch_processing_seconds": "auth.audit_log.parquetlog.batch_processing_seconds",
    "teleport_audit_parquetlog_s3_flush_seconds": "auth.audit_log.parquetlog.s3_flush_seconds",
    "teleport_audit_parquetlog_delete_events_seconds": "auth.audit_log.parquetlog.delete_events_seconds",
    "teleport_audit_parquetlog_batch_size": "auth.audit_log.parquetlog.batch_size",
    "teleport_audit_parquetlog_batch_count": "auth.audit_log.parquetlog.batch_count",
    "teleport_audit_parquetlog_last_processed_timestamp": "auth.audit_log.parquetlog.last_processed_timestamp",
    "teleport_audit_parquetlog_age_oldest_processed_message": "auth.audit_log.parquetlog.age_oldest_processed_message",
    "teleport_audit_parquetlog_errors_from_collect_count": "auth.audit_log.parquetlog.errors_from_collect_count",
}

AUTH_BACKEND_S3_METRICS_MAP = {
    "s3_requests": "auth.backend.s3.requests",
    "s3_requests_seconds": "auth.backend.s3.requests_seconds",
}

AUTH_BACKEND_CACHE_METRICS_MAP = {
    "backend_batch_read_requests": "auth.backend.cache.backend_batch_read_requests",
    "backend_batch_read_seconds": "auth.backend.cache.backend_batch_read_seconds",
    "backend_batch_write_requests": "auth.backend.cache.backend_batch_write_requests",
    "backend_batch_write_seconds": "auth.backend.cache.backend_batch_write_seconds",
    "backend_read_requests": "auth.backend.cache.backend_read_requests",
    "backend_read_seconds": "auth.backend.cache.backend_read_seconds",
    "backend_requests": "auth.backend.cache.backend_requests",
    "backend_write_requests": "auth.backend.cache.backend_write_requests",
    "backend_write_seconds": "auth.backend.cache.backend_write_seconds",
    "watcher_event_sizes": "auth.backend.cache.watcher.event_sizes",
    "watcher_events": "auth.backend.cache.watcher.events",
}

AUTH_BACKEND_DYNAMO_METRICS_MAP = {
    "dynamo_requests": "auth.backend.dynamo.requests",
    "dynamo_requests_seconds": "auth.backend.dynamo.requests_seconds",
}

AUTH_BACKEND_FIRESTORE_METRICS_MAP = {
    "firestore_events_backend_batch_read_requests": "auth.backend.firestore.events.backend_batch_read_requests",
    "firestore_events_backend_batch_read_seconds": "auth.backend.firestore.events.backend_batch_read_seconds",
    "firestore_events_backend_batch_write_requests": "auth.backend.firestore.events.backend_batch_write_requests",
    "firestore_events_backend_batch_write_seconds": "auth.backend.firestore.events.backend_batch_write_seconds",
    "firestore_events_backend_read_requests": "auth.backend.firestore.events.backend_read_requests",
    "firestore_events_backend_read_seconds": "auth.backend.firestore.events.backend_read_seconds",
    "firestore_events_backend_requests": "auth.backend.firestore.events.backend_requests",
    "firestore_events_backend_write_requests": "auth.backend.firestore.events.backend_write_requests",
    "firestore_events_backend_write_seconds": "auth.backend.firestore.events.backend_write_seconds",
}

AUTH_GCP_GCS_METRICS_MAP = {
    "gcs_event_storage_downloads_seconds": "auth.backend.gcs.event_storage.downloads_seconds",
    "gcs_event_storage_downloads": "auth.backend.gcs.event_storage.downloads",
    "gcs_event_storage_uploads_seconds": "auth.backend.gcs.event_storage.uploads_seconds",
    "gcs_event_storage_uploads": "auth.backend.gcs.event_storage.uploads",
}

AUTH_ETCD_METRICS_MAP = {
    "etcd_backend_batch_read_requests": "auth.backend.etcd.backend_batch_read_requests",
    "etcd_backend_batch_read_seconds": "auth.backend.etcd.backend_batch_read_seconds",
    "etcd_backend_read_requests": "auth.backend.etcd.backend_read_requests",
    "etcd_backend_read_seconds": "auth.backend.etcd.backend_read_seconds",
    "etcd_backend_tx_requests": "auth.backend.etcd.backend_tx_requests",
    "etcd_backend_tx_seconds": "auth.backend.etcd.backend_tx_seconds",
    "etcd_backend_write_requests": "auth.backend.etcd.backend_write_requests",
    "etcd_backend_write_seconds": "auth.backend.etcd.backend_write_seconds",
    "teleport_etcd_events": "auth.backend.etcd.teleport_etcd_events",
    "teleport_etcd_event_backpressure": "auth.backend.etcd.teleport_etcd_event_backpressure",
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
    "user_max_concurrent_sessions_hit": "ssh.user.max_concurrent_sessions_hit",
}

KUBERNETES_METRICS_MAP = {
    "teleport_kubernetes_client_in_flight_requests": "kubernetes.client.in_flight_requests",
    "teleport_kubernetes_client_requests": "kubernetes.client.requests",
    "teleport_kubernetes_client_tls_duration_seconds": "kubernetes.client.tls_duration_seconds",
    "teleport_kubernetes_client_got_conn_duration_seconds": "kubernetes.client.got_conn_duration_seconds",
    "teleport_kubernetes_client_first_byte_response_duration_seconds": "kubernetes.client.first_byte_response_duration_seconds",  # noqa: E501
    "teleport_kubernetes_client_request_duration_seconds": "kubernetes.client.request_duration_seconds",
    "teleport_kubernetes_server_in_flight_requests": "kubernetes.server.in_flight_requests",
    "teleport_kubernetes_server_api_requests": "kubernetes.server.api_requests",
    "teleport_kubernetes_server_request_duration_seconds": "kubernetes.server.request_duration_seconds",
    "teleport_kubernetes_server_response_size_bytes": "kubernetes.server.response_size_bytes",
    "teleport_kubernetes_server_exec_in_flight_sessions": "kubernetes.server.exec_in_flight_sessions",
    "teleport_kubernetes_server_exec_sessions": "kubernetes.server.exec_sessions",
    "teleport_kubernetes_server_portforward_in_flight_sessions": "kubernetes.server.portforward_in_flight_sessions",  # noqa: E501
    "teleport_kubernetes_server_portforward_sessions": "kubernetes.server.portforward_sessions",
    "teleport_kubernetes_server_join_in_flight_sessions": "kubernetes.server.join_in_flight_sessions",
    "teleport_kubernetes_server_join_sessions": "kubernetes.server.join_sessions",
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

METRIC_MAP = {
    **COMMON_METRICS_MAP,
    **PROXY_METRICS_MAP,
    **AUTH_METRICS_MAP,
    **SSH_METRICS_MAP,
    **KUBERNETES_METRICS_MAP,
    **DATABASE_METRICS_MAP,
}
