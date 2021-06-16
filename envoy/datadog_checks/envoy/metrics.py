# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .utils import make_metric_tree

METRIC_PREFIX = 'envoy.'

# fmt: off
METRICS = {
    'stats.overflow': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'server.uptime': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.memory_allocated': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.memory_heap_size': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.live': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.parent_connections': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.total_connections': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.version': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.days_until_first_cert_expiring': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.concurrency': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.debug_assertion_failures': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'server.hot_restart_epoch': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.state': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'server.watchdog_mega_miss': {
        'tags': (
            ('thread_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'server.watchdog_miss': {
        'tags': (
            ('thread_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'filesystem.write_buffered': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'filesystem.write_completed': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'filesystem.flushed_by_timer': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'filesystem.reopen_failed': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'filesystem.write_total_buffered': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'runtime.load_error': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'runtime.override_dir_not_exists': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'runtime.override_dir_exists': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'runtime.load_success': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'runtime.num_keys': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'runtime.admin_overrides_active': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'runtime.deprecated_feature_use': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'runtime.num_layers': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'control_plane.connected_state': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'control_plane.pending_requests': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'control_plane.rate_limit_enforced': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cds.config_reload': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cds.update_attempt': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cds.update_success': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cds.update_failure': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cds.update_rejected': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cds.update_time': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster_manager.cds.version': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster_manager.cds.control_plane.connected_state': {
        'tags': (
            (),
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster_manager.cds.control_plane.pending_requests': {
        'tags': (
            (),
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster_manager.cds.control_plane.rate_limit_enforced': {
        'tags': (
            (),
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.no_route': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.no_cluster': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rq_redirect': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rq_direct_response': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rq_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_1xx': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_2xx': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_3xx': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_4xx': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_5xx': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_retry': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_retry_limit_exceeded': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_retry_overflow': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_retry_success': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_time': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'histogram',
    },
    'vhost.vcluster.upstream_rq_timeout': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'vhost.vcluster.upstream_rq_total': {
        'tags': (
            ('virtual_host_name', ),
            ('virtual_envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ratelimit.ok': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ratelimit.error': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ratelimit.over_limit': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.ip_tagging.hit': {
        'tags': (
            ('stat_prefix', ),
            ('tag_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.ip_tagging.no_hit': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.ip_tagging.total': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.grpc.success': {
        'tags': (
            ('envoy_cluster', ),
            ('grpc_service', 'grpc_method', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.grpc.failure': {
        'tags': (
            ('envoy_cluster', ),
            ('grpc_service', 'grpc_method', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.grpc.total': {
        'tags': (
            ('envoy_cluster', ),
            ('grpc_service', 'grpc_method', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.dynamodb.operation.upstream_rq_total': {
        'tags': (
            ('stat_prefix', ),
            (),
            ('operation_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.dynamodb.operation.upstream_rq_time': {
        'tags': (
            ('stat_prefix', ),
            (),
            ('operation_name', ),
            (),
        ),
        'method': 'histogram',
    },
    'http.dynamodb.table.upstream_rq_total': {
        'tags': (
            ('stat_prefix', ),
            (),
            ('table_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.dynamodb.table.upstream_rq_time': {
        'tags': (
            ('stat_prefix', ),
            (),
            ('table_name', ),
            (),
        ),
        'method': 'histogram',
    },
    'http.dynamodb.error': {
        'tags': (
            ('stat_prefix', ),
            (),
            ('table_name', 'error_type', ),
        ),
        'method': 'monotonic_count',
    },
    'http.dynamodb.error.BatchFailureUnprocessedKeys': {
        'tags': (
            ('stat_prefix', ),
            (),
            ('table_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.buffer.rq_timeout': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rds.config_reload': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rds.update_attempt': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rds.update_success': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rds.update_failure': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rds.update_rejected': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rds.update_time': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.rds.version': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.rds.control_plane.connected_state': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'http.rds.control_plane.pending_requests': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'http.rds.control_plane.rate_limit_enforced': {
        'tags': (
            ('stat_prefix', ),
            ('route_config_name', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.downstream_cx_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.downstream_cx_no_route': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.downstream_cx_tx_bytes_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.downstream_cx_tx_bytes_buffered': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'tcp.downstream_cx_rx_bytes_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.downstream_cx_rx_bytes_buffered': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'tcp.downstream_flow_control_paused_reading_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.downstream_flow_control_resumed_reading_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.idle_timeout': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.max_downstream_connection_duration': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.upstream_flush_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'tcp.upstream_flush_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'auth.clientssl.update_success': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'auth.clientssl.update_failure': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'auth.clientssl.auth_no_ssl': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'auth.clientssl.auth_ip_white_list': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'auth.clientssl.auth_digest_match': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'auth.clientssl.auth_digest_no_match': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'auth.clientssl.total_principals': {
        'tags': (
            (),
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'ratelimit.total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'ratelimit.error': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'ratelimit.over_limit': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'ratelimit.ok': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'ratelimit.cx_closed': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'ratelimit.active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'redis.downstream_cx_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'redis.downstream_cx_protocol_error': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.downstream_cx_rx_bytes_buffered': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'redis.downstream_cx_rx_bytes_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.downstream_cx_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.downstream_cx_tx_bytes_buffered': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'redis.downstream_cx_tx_bytes_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.downstream_cx_drain_close': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.downstream_rq_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'redis.downstream_rq_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.splitter.invalid_request': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.splitter.unsupported_command': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.command.total': {
        'tags': (
            ('stat_prefix', ),
            ('command', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.command.success': {
        'tags': (
            ('stat_prefix', ),
            ('command', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.command.error': {
        'tags': (
            ('stat_prefix', ),
            ('command', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'redis.command.latency': {
        'tags': (
            ('stat_prefix', ),
            ('command', ),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.decoding_error': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.delay_injected': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_get_more': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_insert': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_kill_cursors': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_tailable_cursor': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_no_cursor_timeout': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_await_data': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_exhaust': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_no_max_time': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_scatter_get': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_multi_get': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_query_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'mongo.op_reply': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_reply_cursor_not_found': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_reply_query_failure': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.op_reply_valid_cursor': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.cx_destroy_local_with_active_rq': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.cx_destroy_remote_with_active_rq': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.cx_drain_close': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.cmd.total': {
        'tags': (
            ('stat_prefix', ),
            ('cmd', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.cmd.reply_num_docs': {
        'tags': (
            ('stat_prefix', ),
            ('cmd', ),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.cmd.reply_size': {
        'tags': (
            ('stat_prefix', ),
            ('cmd', ),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.cmd.reply_time_ms': {
        'tags': (
            ('stat_prefix', ),
            ('cmd', ),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.collection.query.total': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.collection.query.scatter_get': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.collection.query.multi_get': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.collection.query.reply_num_docs': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.collection.query.reply_size': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.collection.query.reply_time_ms': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.collection.callsite.query.total': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            ('callsite', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.collection.callsite.query.scatter_get': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            ('callsite', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.collection.callsite.query.multi_get': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            ('callsite', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'mongo.collection.callsite.query.reply_num_docs': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            ('callsite', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.collection.callsite.query.reply_size': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            ('callsite', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'mongo.collection.callsite.query.reply_time_ms': {
        'tags': (
            ('stat_prefix', ),
            ('collection', ),
            ('callsite', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'listener.downstream_cx_total': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.downstream_cx_destroy': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.downstream_cx_active': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'gauge',
    },
    'listener.downstream_cx_length_ms': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'histogram',
    },
    'listener.downstream_pre_cx_active': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'gauge',
    },
    'listener.downstream_pre_cx_timeout': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.server_ssl_socket_factory.downstream_context_secrets_not_ready': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.server_ssl_socket_factory.ssl_context_update_by_sds': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.connection_error': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.handshake': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.session_reused': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.no_certificate': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.fail_no_sni_match': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.fail_verify_no_cert': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.fail_verify_error': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.fail_verify_san': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.fail_verify_cert_hash': {
        'tags': (
            ('address', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.ciphers': {
        'tags': (
            ('address', ),
            (),
            ('cipher', ),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.versions': {
        'tags': (
            ('address', ),
            (),
            ('version', ),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.curves': {
        'tags': (
            ('address', ),
            (),
            ('curve', ),
        ),
        'method': 'monotonic_count',
    },
    'listener.ssl.sigalgs': {
        'tags': (
            ('address', ),
            (),
            ('sigalg', ),
        ),
        'method': 'monotonic_count',
    },
    'listener.no_filter_chain_match': {
        'tags': (
            ('address', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.listener_added': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.listener_modified': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.listener_removed': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.listener_create_success': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.listener_create_failure': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.total_listeners_warming': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.total_listeners_active': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.total_listeners_draining': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.lds.config_reload': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.lds.update_attempt': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.lds.update_success': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.lds.update_failure': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.lds.update_rejected': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener_manager.lds.update_time': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.lds.version': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.lds.control_plane.connected_state': {
        'tags': (
            (),
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.lds.control_plane.pending_requests': {
        'tags': (
            (),
            (),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'listener_manager.lds.control_plane.rate_limit_enforced': {
        'tags': (
            (),
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_ssl_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_http1_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_websocket_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_http2_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_http3_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_destroy': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_destroy_remote': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_destroy_local': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_destroy_active_rq': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_destroy_local_active_rq': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_destroy_remote_active_rq': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_ssl_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_http1_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_websocket_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_http2_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_http3_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_protocol_error': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_length_ms': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'histogram',
    },
    'http.downstream_cx_rx_bytes_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_rx_bytes_buffered': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_tx_bytes_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_tx_bytes_buffered': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_cx_drain_close': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_cx_idle_timeout': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_flow_control_paused_reading_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_flow_control_resumed_reading_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_http1_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_http2_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_http3_total': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_active': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'gauge',
    },
    'http.downstream_rq_response_before_rq_complete': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_rx_reset': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_tx_reset': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_non_relative_path': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_too_large': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_1xx': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_2xx': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_3xx': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_4xx': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_5xx': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_ws_on_non_ws_route': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.downstream_rq_time': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'histogram',
    },
    'http.rs_too_large': {
        'tags': (
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.user_agent.downstream_cx_total': {
        'tags': (
            ('stat_prefix', ),
            ('user_agent', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.user_agent.downstream_cx_destroy_remote_active_rq': {
        'tags': (
            ('stat_prefix', ),
            ('user_agent', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.user_agent.downstream_rq_total': {
        'tags': (
            ('stat_prefix', ),
            ('user_agent', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.http.downstream_rq_1xx': {
        'tags': (
            ('address', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.http.downstream_rq_2xx': {
        'tags': (
            ('address', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.http.downstream_rq_3xx': {
        'tags': (
            ('address', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.http.downstream_rq_4xx': {
        'tags': (
            ('address', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.http.downstream_rq_5xx': {
        'tags': (
            ('address', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'listener.http.downstream_rq_completed': {
        'tags': (
            ('address', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http2.rx_reset': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http2.tx_reset': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http2.header_overflow': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http2.trailers': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http2.headers_cb_no_stream': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http2.too_many_header_frames': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.tracing.random_sampling': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.tracing.service_forced': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.tracing.client_enabled': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.tracing.not_traceable': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.tracing.health_check': {
        'tags': (
            ('stat_prefix', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cluster_added': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cluster_modified': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.cluster_removed': {
        'tags': (
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster_manager.active_clusters': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster_manager.warming_clusters': {
        'tags': (
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.assignment_stale': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.assignment_timeout_received': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_active': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.upstream_cx_http1_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_http2_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_http3_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_connect_fail': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_connect_timeout': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_connect_attempts_exceeded': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_overflow': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_connect_ms': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.upstream_cx_length_ms': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.upstream_cx_destroy': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_destroy_local': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_destroy_remote': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_destroy_with_active_rq': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_destroy_local_with_active_rq': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_destroy_remote_with_active_rq': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_close_notify': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_rx_bytes_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_rx_bytes_buffered': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.upstream_cx_tx_bytes_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_tx_bytes_buffered': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.upstream_cx_protocol_error': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_max_requests': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_none_healthy': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_cx_idle_timeout': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count'
    },
    'cluster.upstream_cx_pool_overflow': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count'
    },
    'cluster.upstream_rq_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_active': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.upstream_rq_pending_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_pending_overflow': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_pending_failure_eject': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_pending_active': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.upstream_rq_cancelled': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_maintenance_mode': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_max_duration_reached': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_timeout': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_per_try_timeout': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_rx_reset': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_tx_reset': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_retry': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_retry_success': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_retry_overflow': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.client_ssl_socket_factory.ssl_context_update_by_sds': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.client_ssl_socket_factory.upstream_context_secrets_not_ready': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.connection_error': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.handshake': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.session_reused': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.no_certificate': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.fail_no_sni_match': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.fail_verify_no_cert': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.fail_verify_error': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.fail_verify_san': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.fail_verify_cert_hash': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.ciphers': {
        'tags': (
            ('envoy_cluster', ),
            (),
            ('cipher', ),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.curves': {
        'tags': (
            ('envoy_cluster', ),
            (),
            ('curve', ),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.sigalgs': {
        'tags': (
            ('envoy_cluster', ),
            (),
            ('sigalg', ),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ssl.versions': {
        'tags': (
            ('envoy_cluster', ),
            (),
            ('version', ),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_flow_control_paused_reading_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_flow_control_resumed_reading_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_flow_control_backed_up_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_flow_control_drained_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_internal_redirect_failed_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count'
    },
    'cluster.upstream_internal_redirect_succeeded_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count'
    },
    'cluster.membership_change': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.membership_degraded': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.membership_excluded': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.membership_healthy': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.membership_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.retry_or_shadow_abandoned': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.config_reload': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.update_attempt': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.update_success': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.update_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.update_empty': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.update_no_rebuild': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.version': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.max_host_weight': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.bind_errors': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.original_dst_host_invalid': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.attempt': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.success': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.passive_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.network_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.verify_cluster': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.health_check.healthy': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.outlier_detection.ejections_enforced_total': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_active': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.outlier_detection.ejections_overflow': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_consecutive_5xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_consecutive_5xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_success_rate': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_success_rate': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_consecutive_gateway_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_consecutive_gateway_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_consecutive_local_origin_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_consecutive_local_origin_failure': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_local_origin_success_rate': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_local_origin_success_rate': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_failure_percentage': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_failure_percentage': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_enforced_failure_percentage_local_origin': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.outlier_detection.ejections_detected_failure_percentage_local_origin': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.circuit_breakers.cx_open': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.cx_pool_open': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.rq_open': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.rq_pending_open': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.rq_retry_open': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.remaining_cx': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.remaining_pending': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.remaining_rq': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.circuit_breakers.remaining_retries': {
        'tags': (
            ('envoy_cluster', ),
            ('priority', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.upstream_rq_completed': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_1xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_2xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_3xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_4xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_5xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.upstream_rq_time': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.canary.upstream_rq_completed': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.canary.upstream_rq_1xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.canary.upstream_rq_2xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.canary.upstream_rq_3xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.canary.upstream_rq_4xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.canary.upstream_rq_5xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.canary.upstream_rq_time': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.internal.upstream_rq_completed': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.internal.upstream_rq_1xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.internal.upstream_rq_2xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.internal.upstream_rq_3xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.internal.upstream_rq_4xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.internal.upstream_rq_5xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.internal.upstream_rq_time': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.external.upstream_rq_completed': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.external.upstream_rq_1xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.external.upstream_rq_2xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.external.upstream_rq_3xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.external.upstream_rq_4xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.external.upstream_rq_5xx': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.external.upstream_rq_time': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.zone.upstream_rq_1xx': {
        'tags': (
            ('envoy_cluster', ),
            ('from_zone', 'to_zone', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.zone.upstream_rq_2xx': {
        'tags': (
            ('envoy_cluster', ),
            ('from_zone', 'to_zone', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.zone.upstream_rq_3xx': {
        'tags': (
            ('envoy_cluster', ),
            ('from_zone', 'to_zone', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.zone.upstream_rq_4xx': {
        'tags': (
            ('envoy_cluster', ),
            ('from_zone', 'to_zone', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.zone.upstream_rq_5xx': {
        'tags': (
            ('envoy_cluster', ),
            ('from_zone', 'to_zone', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.zone.upstream_rq_time': {
        'tags': (
            ('envoy_cluster', ),
            ('from_zone', 'to_zone', ),
            (),
        ),
        'method': 'histogram',
    },
    'cluster.lb_recalculate_zone_structures': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_healthy_panic': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_zone_cluster_too_small': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_zone_routing_all_directly': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_zone_routing_sampled': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_zone_routing_cross_zone': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_local_cluster_not_ok': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_zone_number_differs': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_zone_no_capacity_left': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_subsets_active': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'gauge',
    },
    'cluster.lb_subsets_created': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_subsets_removed': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_subsets_selected': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_subsets_fallback': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.lb_subsets_fallback_panic': {
        'tags': (
            ('envoy_cluster', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http1.dropped_headers_with_underscores': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http1.metadata_not_supported_error': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http1.response_flood': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http1.requests_rejected_with_underscores_in_headers': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.header_overflow': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.headers_cb_no_stream': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.inbound_empty_frames_flood': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.inbound_priority_frames_flood': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.inbound_window_update_frames_flood': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.outbound_control_flood': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.outbound_flood': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.rx_messaging_error': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.rx_reset': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.too_many_header_frames': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.trailers': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.http2.tx_reset': {
        'tags': (
            ('envoy_cluster', ),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'sds.key_rotation_failed': {
        'tags': (
            ('envoy_secret', ),
            (),
        ),
        'method': 'monotonic_count',
    },
}
# fmt: on

METRIC_TREE = make_metric_tree(METRICS)
