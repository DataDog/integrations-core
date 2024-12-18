# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


INSTANCE = {"teleport_url": "http://127.0.0.1", "diag_port": "3000"}

BAD_HOSTNAME_INSTANCE = {"teleport_url": "https://invalid-hostname"}

COMMON_METRICS = [
    "common.process_state",
    "common.certificate_mismatch.count",
    "common.rx.count",
    "common.server_interactive_sessions_total",
    "common.teleport_build_info",
    "common.teleport_cache_events.count",
    "common.teleport_cache_stale_events.count",
    "common.tx.count",
]

PROXY_METRICS = [
    "proxy.failed_connect_to_node_attempts.count",
    "proxy.failed_login_attempts.count",
    "proxy.grpc_client_started.count",
    "proxy.grpc_client_handled.count",
    "proxy.grpc_client_msg_received.count",
    "proxy.grpc_client_msg_sent.count",
    "proxy.connection_limit_exceeded.count",
    "proxy.peer_client_dial_error.count",
    "proxy.peer_server_connections",
    "proxy.peer_client_rpc",
    "proxy.peer_client_rpc.count",
    "proxy.peer_client_rpc_duration_seconds.bucket",
    "proxy.peer_client_rpc_duration_seconds.count",
    "proxy.peer_client_rpc_duration_seconds.sum",
    "proxy.peer_client_message_sent_size.bucket",
    "proxy.peer_client_message_sent_size.count",
    "proxy.peer_client_message_sent_size.sum",
    "proxy.peer_client_message_received_size.bucket",
    "proxy.peer_client_message_received_size.count",
    "proxy.peer_client_message_received_size.sum",
    "proxy.peer_server_rpc",
    "proxy.peer_server_rpc_duration_seconds.bucket",
    "proxy.peer_server_rpc_duration_seconds.count",
    "proxy.peer_server_rpc_duration_seconds.sum",
    "proxy.peer_server_message_sent_size.bucket",
    "proxy.peer_server_message_sent_size.count",
    "proxy.peer_server_message_sent_size.sum",
    "proxy.peer_server_message_received_size.bucket",
    "proxy.peer_server_message_received_size.count",
    "proxy.peer_server_message_received_size.sum",
    "proxy.ssh_sessions_total",
    "proxy.missing_ssh_tunnels",
    "proxy.remote_clusters",
    "proxy.teleport_connect_to_node_attempts.count",
    "proxy.teleport_reverse_tunnels_connected",
    "proxy.trusted_clusters",
    "proxy.teleport_proxy_db_connection_setup_time_seconds.bucket",
    "proxy.teleport_proxy_db_connection_setup_time_seconds.count",
    "proxy.teleport_proxy_db_connection_setup_time_seconds.sum",
    "proxy.teleport_proxy_db_connection_dial_attempts.count",
    "proxy.teleport_proxy_db_connection_dial_failures.count",
    "proxy.teleport_proxy_db_attempted_servers_total.bucket",
    "proxy.teleport_proxy_db_attempted_servers_total.count",
    "proxy.teleport_proxy_db_attempted_servers_total.sum",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds.bucket",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds.count",
    "proxy.teleport_proxy_db_connection_tls_config_time_seconds.sum",
    "proxy.teleport_proxy_db_active_connections_total",
]


AUTH_METRICS = [
    "auth.generate_requests_throttled.count",
    "auth.generate_requests.count",
    "auth.generate_seconds.bucket",
    "auth.generate_seconds.count",
    "auth.generate_seconds.sum",
    "auth.grpc_server_handled.count",
    "auth.grpc_server_msg_received.count",
    "auth.grpc_server_msg_sent.count",
    "auth.grpc_server_started.count",
    "auth.cluster_name_not_found.count",
    "auth.user_login.count",
    "auth.migrations",
]


AUTH_AUDIT_LOG_METRICS = [
    "auth.audit_log.failed_disk_monitoring.count",
    "auth.audit_log.failed_emit_events.count",
    "auth.audit_log.emit_events.count",
    "auth.audit_log.parquetlog_batch_processing_seconds.bucket",
    "auth.audit_log.parquetlog_batch_processing_seconds.count",
    "auth.audit_log.parquetlog_batch_processing_seconds.sum",
    "auth.audit_log.parquetlog_s3_flush_seconds.bucket",
    "auth.audit_log.parquetlog_s3_flush_seconds.count",
    "auth.audit_log.parquetlog_s3_flush_seconds.sum",
    "auth.audit_log.parquetlog_delete_events_seconds.bucket",
    "auth.audit_log.parquetlog_delete_events_seconds.count",
    "auth.audit_log.parquetlog_delete_events_seconds.sum",
    "auth.audit_log.parquetlog_batch_size.bucket",
    "auth.audit_log.parquetlog_batch_size.count",
    "auth.audit_log.parquetlog_batch_size.sum",
    "auth.audit_log.parquetlog_batch_count.count",
    "auth.audit_log.parquetlog_errors_from_collect_count.count",
]

AUTH_BACKEND_S3_METRICS = [
    "auth.backend.s3_requests.count",
    "auth.backend.s3_requests_seconds.bucket",
    "auth.backend.s3_requests_seconds.count",
    "auth.backend.s3_requests_seconds.sum",
]

AUTH_BACKEND_CACHE_METRICS = [
    "auth.cache.backend_batch_read_requests.count",
    "auth.cache.backend_batch_read_seconds.bucket",
    "auth.cache.backend_batch_read_seconds.count",
    "auth.cache.backend_batch_read_seconds.sum",
    "auth.cache.backend_batch_write_requests.count",
    "auth.cache.backend_batch_write_seconds.bucket",
    "auth.cache.backend_batch_write_seconds.count",
    "auth.cache.backend_batch_write_seconds.sum",
    "auth.cache.backend_read_requests.count",
    "auth.cache.backend_read_seconds.bucket",
    "auth.cache.backend_read_seconds.count",
    "auth.cache.backend_read_seconds.sum",
    "auth.cache.backend_requests.count",
    "auth.cache.backend_write_requests.count",
    "auth.cache.backend_write_seconds.bucket",
    "auth.cache.backend_write_seconds.count",
    "auth.cache.backend_write_seconds.sum",
    "auth.cache.watcher_event_sizes.count",
    "auth.cache.watcher_event_sizes.sum",
    "auth.cache.watcher_events.bucket",
    "auth.cache.watcher_events.count",
    "auth.cache.watcher_events.sum",
]

AUTH_BACKEND_DYNAMO_METRICS = [
    "auth.backend.dynamo_requests.count",
    "auth.backend.dynamo_requests_seconds.bucket",
    "auth.backend.dynamo_requests_seconds.count",
    "auth.backend.dynamo_requests_seconds.sum",
]

AUTH_BACKEND_FIRESTORE_METRICS = [
    "auth.backend.firestore_events_backend_batch_read_requests.count",
    "auth.backend.firestore_events_backend_batch_read_seconds.bucket",
    "auth.backend.firestore_events_backend_batch_read_seconds.count",
    "auth.backend.firestore_events_backend_batch_read_seconds.sum",
    "auth.backend.firestore_events_backend_batch_write_requests.count",
    "auth.backend.firestore_events_backend_batch_write_seconds.bucket",
    "auth.backend.firestore_events_backend_batch_write_seconds.count",
    "auth.backend.firestore_events_backend_batch_write_seconds.sum",
    "auth.backend.firestore_events_backend_write_requests.count",
    "auth.backend.firestore_events_backend_write_seconds.bucket",
    "auth.backend.firestore_events_backend_write_seconds.count",
    "auth.backend.firestore_events_backend_write_seconds.sum",
]

AUTH_BACKEND_GCP_GCS_METRICS = [
    "auth.backend.gcs_event_storage_downloads_seconds.bucket",
    "auth.backend.gcs_event_storage_downloads_seconds.count",
    "auth.backend.gcs_event_storage_downloads_seconds.sum",
    "auth.backend.gcs_event_storage_downloads.count",
    "auth.backend.gcs_event_storage_uploads_seconds.bucket",
    "auth.backend.gcs_event_storage_uploads_seconds.count",
    "auth.backend.gcs_event_storage_uploads_seconds.sum",
    "auth.backend.gcs_event_storage_uploads.count",
]

AUTH_BACKEND_ETCD_METRICS = [
    "auth.backend.etcd_backend_batch_read_requests.count",
    "auth.backend.etcd_backend_batch_read_seconds.bucket",
    "auth.backend.etcd_backend_batch_read_seconds.count",
    "auth.backend.etcd_backend_batch_read_seconds.sum",
    "auth.backend.etcd_backend_read_requests.count",
    "auth.backend.etcd_backend_read_seconds.bucket",
    "auth.backend.etcd_backend_read_seconds.count",
    "auth.backend.etcd_backend_read_seconds.sum",
    "auth.backend.etcd_backend_tx_requests.count",
    "auth.backend.etcd_backend_tx_seconds.bucket",
    "auth.backend.etcd_backend_tx_seconds.count",
    "auth.backend.etcd_backend_tx_seconds.sum",
    "auth.backend.etcd_backend_write_requests.count",
    "auth.backend.etcd_backend_write_seconds.bucket",
    "auth.backend.etcd_backend_write_seconds.count",
    "auth.backend.etcd_backend_write_seconds.sum",
    "auth.backend.etcd_teleport_etcd_events.count",
    "auth.backend.etcd_teleport_etcd_event_backpressure.count",
]

SSH_METRICS = [
    "ssh.user_max_concurrent_sessions_hit.count",
]

KUBERNETES_METRICS = [
    "kubernetes.client_in_flight_requests",
    "kubernetes.client_requests.count",
    "kubernetes.client_tls_duration_seconds.bucket",
    "kubernetes.client_tls_duration_seconds.count",
    "kubernetes.client_tls_duration_seconds.sum",
    "kubernetes.client_got_conn_duration_seconds.bucket",
    "kubernetes.client_got_conn_duration_seconds.count",
    "kubernetes.client_got_conn_duration_seconds.sum",
    "kubernetes.client_first_byte_response_duration_seconds.bucket",
    "kubernetes.client_first_byte_response_duration_seconds.count",
    "kubernetes.client_first_byte_response_duration_seconds.sum",
    "kubernetes.client_request_duration_seconds.bucket",
    "kubernetes.client_request_duration_seconds.count",
    "kubernetes.client_request_duration_seconds.sum",
    "kubernetes.server_in_flight_requests",
    "kubernetes.server_api_requests.count",
    "kubernetes.server_request_duration_seconds.bucket",
    "kubernetes.server_request_duration_seconds.count",
    "kubernetes.server_request_duration_seconds.sum",
    "kubernetes.server_response_size_bytes.bucket",
    "kubernetes.server_response_size_bytes.count",
    "kubernetes.server_response_size_bytes.sum",
    "kubernetes.server_exec_in_flight_sessions",
    "kubernetes.server_exec_sessions.count",
    "kubernetes.server_portforward_in_flight_sessions",
    "kubernetes.server_portforward_sessions.count",
    "kubernetes.server_join_in_flight_sessions",
    "kubernetes.server_join_sessions.count",
]

DATABASE_METRICS = [
    "db.messages_from_client.count",
    "db.messages_from_server.count",
    "db.method_call_count.count",
    "db.method_call_latency_seconds.bucket",
    "db.method_call_latency_seconds.count",
    "db.method_call_latency_seconds.sum",
    "db.initialized_connections.count",
    "db.active_connections_total",
    "db.connection_durations_seconds.bucket",
    "db.connection_durations_seconds.count",
    "db.connection_durations_seconds.sum",
    "db.connection_setup_time_seconds.bucket",
    "db.connection_setup_time_seconds.count",
    "db.connection_setup_time_seconds.sum",
    "db.errors.count",
]

BPF_METRICS = [
    "bpf.lost_command_events.count",
    "bpf.lost_disk_events.count",
    "bpf.lost_network_events.count",
]

PROMETHEUS_METRICS = [
    "prom.http_metric_handler_requests_in_flight",
    "prom.http_metric_handler_requests.count",
]
