# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


INSTANCE = {"teleport_url": "http://127.0.0.1", "diag_port": "3000"}

BAD_HOSTNAME_INSTANCE = {"teleport_url": "https://invalid-hostname"}

COMMON_METRICS = [
    "common.process.state",
    "common.certificate_mismatch.count",
    "common.rx.count",
    "common.server_interactive_sessions_total",
    "common.teleport.build_info",
    "common.teleport.cache_events.count",
    "common.teleport.cache_stale_events.count",
    "common.tx.count",
]

PROXY_METRICS = [
    "proxy.failed_connect_to_node_attempts.count",
    "proxy.failed_login_attempts.count",
    "proxy.grpc.client.started.count",
    "proxy.grpc.client.handled.count",
    "proxy.grpc.client.msg_received.count",
    "proxy.grpc.client.msg_sent.count",
    "proxy.connection_limit_exceeded.count",
    "proxy.peer_client.dial_error.count",
    "proxy.peer_server.connections",
    "proxy.peer_client.rpc",
    "proxy.peer_client.rpc.count",
    "proxy.peer_client.rpc_duration_seconds.bucket",
    "proxy.peer_client.rpc_duration_seconds.count",
    "proxy.peer_client.rpc_duration_seconds.sum",
    "proxy.peer_client.message_sent_size.bucket",
    "proxy.peer_client.message_sent_size.count",
    "proxy.peer_client.message_sent_size.sum",
    "proxy.peer_client.message_received_size.bucket",
    "proxy.peer_client.message_received_size.count",
    "proxy.peer_client.message_received_size.sum",
    "proxy.peer_server.rpc",
    "proxy.peer_server.rpc_duration_seconds.bucket",
    "proxy.peer_server.rpc_duration_seconds.count",
    "proxy.peer_server.rpc_duration_seconds.sum",
    "proxy.peer_server.message_sent_size.bucket",
    "proxy.peer_server.message_sent_size.count",
    "proxy.peer_server.message_sent_size.sum",
    "proxy.peer_server.message_received_size.bucket",
    "proxy.peer_server.message_received_size.count",
    "proxy.peer_server.message_received_size.sum",
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
    "auth.grpc.server.handled.count",
    "auth.grpc.server.msg_received.count",
    "auth.grpc.server.msg_sent.count",
    "auth.grpc.server.started.count",
    "auth.cluster_name_not_found.count",
    "auth.user.login.count",
    "auth.migrations",
]


AUTH_AUDIT_LOG_METRICS = [
    "auth.audit_log.failed_disk_monitoring.count",
    "auth.audit_log.failed_emit_events.count",
    "auth.audit_log.emit_events.count",
    "auth.audit_log.parquetlog.batch_processing_seconds.bucket",
    "auth.audit_log.parquetlog.batch_processing_seconds.count",
    "auth.audit_log.parquetlog.batch_processing_seconds.sum",
    "auth.audit_log.parquetlog.s3_flush_seconds.bucket",
    "auth.audit_log.parquetlog.s3_flush_seconds.count",
    "auth.audit_log.parquetlog.s3_flush_seconds.sum",
    "auth.audit_log.parquetlog.delete_events_seconds.bucket",
    "auth.audit_log.parquetlog.delete_events_seconds.count",
    "auth.audit_log.parquetlog.delete_events_seconds.sum",
    "auth.audit_log.parquetlog.batch_size.bucket",
    "auth.audit_log.parquetlog.batch_size.count",
    "auth.audit_log.parquetlog.batch_size.sum",
    "auth.audit_log.parquetlog.batch_count.count",
    "auth.audit_log.parquetlog.errors_from_collect_count.count",
]

AUTH_BACKEND_S3_METRICS = [
    "auth.backend.s3.requests.count",
    "auth.backend.s3.requests_seconds.bucket",
    "auth.backend.s3.requests_seconds.count",
    "auth.backend.s3.requests_seconds.sum",
]

AUTH_BACKEND_CACHE_METRICS = [
    "auth.backend.cache.backend_batch_read_requests.count",
    "auth.backend.cache.backend_batch_read_seconds.bucket",
    "auth.backend.cache.backend_batch_read_seconds.count",
    "auth.backend.cache.backend_batch_read_seconds.sum",
    "auth.backend.cache.backend_batch_write_requests.count",
    "auth.backend.cache.backend_batch_write_seconds.bucket",
    "auth.backend.cache.backend_batch_write_seconds.count",
    "auth.backend.cache.backend_batch_write_seconds.sum",
    "auth.backend.cache.backend_read_requests.count",
    "auth.backend.cache.backend_read_seconds.bucket",
    "auth.backend.cache.backend_read_seconds.count",
    "auth.backend.cache.backend_read_seconds.sum",
    "auth.backend.cache.backend_requests.count",
    "auth.backend.cache.backend_write_requests.count",
    "auth.backend.cache.backend_write_seconds.bucket",
    "auth.backend.cache.backend_write_seconds.count",
    "auth.backend.cache.backend_write_seconds.sum",
    "auth.backend.cache.watcher.event_sizes.count",
    "auth.backend.cache.watcher.event_sizes.sum",
    "auth.backend.cache.watcher.events.bucket",
    "auth.backend.cache.watcher.events.count",
    "auth.backend.cache.watcher.events.sum",
]

AUTH_BACKEND_DYNAMO_METRICS = [
    "auth.backend.dynamo.requests.count",
    "auth.backend.dynamo.requests_seconds.bucket",
    "auth.backend.dynamo.requests_seconds.count",
    "auth.backend.dynamo.requests_seconds.sum",
]

AUTH_BACKEND_FIRESTORE_METRICS = [
    "auth.backend.firestore.events.backend_batch_read_requests.count",
    "auth.backend.firestore.events.backend_batch_read_seconds.bucket",
    "auth.backend.firestore.events.backend_batch_read_seconds.count",
    "auth.backend.firestore.events.backend_batch_read_seconds.sum",
    "auth.backend.firestore.events.backend_batch_write_requests.count",
    "auth.backend.firestore.events.backend_batch_write_seconds.bucket",
    "auth.backend.firestore.events.backend_batch_write_seconds.count",
    "auth.backend.firestore.events.backend_batch_write_seconds.sum",
    "auth.backend.firestore.events.backend_write_requests.count",
    "auth.backend.firestore.events.backend_write_seconds.bucket",
    "auth.backend.firestore.events.backend_write_seconds.count",
    "auth.backend.firestore.events.backend_write_seconds.sum",
]

AUTH_BACKEND_GCP_GCS_METRICS = [
    "auth.backend.gcs.event_storage.downloads_seconds.bucket",
    "auth.backend.gcs.event_storage.downloads_seconds.count",
    "auth.backend.gcs.event_storage.downloads_seconds.sum",
    "auth.backend.gcs.event_storage.downloads.count",
    "auth.backend.gcs.event_storage.uploads_seconds.bucket",
    "auth.backend.gcs.event_storage.uploads_seconds.count",
    "auth.backend.gcs.event_storage.uploads_seconds.sum",
    "auth.backend.gcs.event_storage.uploads.count",
]

AUTH_BACKEND_ETCD_METRICS = [
    "auth.backend.etcd.backend_batch_read_requests.count",
    "auth.backend.etcd.backend_batch_read_seconds.bucket",
    "auth.backend.etcd.backend_batch_read_seconds.count",
    "auth.backend.etcd.backend_batch_read_seconds.sum",
    "auth.backend.etcd.backend_read_requests.count",
    "auth.backend.etcd.backend_read_seconds.bucket",
    "auth.backend.etcd.backend_read_seconds.count",
    "auth.backend.etcd.backend_read_seconds.sum",
    "auth.backend.etcd.backend_tx_requests.count",
    "auth.backend.etcd.backend_tx_seconds.bucket",
    "auth.backend.etcd.backend_tx_seconds.count",
    "auth.backend.etcd.backend_tx_seconds.sum",
    "auth.backend.etcd.backend_write_requests.count",
    "auth.backend.etcd.backend_write_seconds.bucket",
    "auth.backend.etcd.backend_write_seconds.count",
    "auth.backend.etcd.backend_write_seconds.sum",
    "auth.backend.etcd.teleport_etcd_events.count",
    "auth.backend.etcd.teleport_etcd_event_backpressure.count",
]

SSH_METRICS = [
    "ssh.user.max_concurrent_sessions_hit.count",
]
