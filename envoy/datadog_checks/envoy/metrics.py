# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .utils import make_metric_tree, modify_metrics_dict

METRIC_PREFIX = 'envoy.'

PROMETHEUS_METRICS_MAP = {
    'envoy_cluster_assignment_stale': 'cluster.assignment_stale',
    'envoy_cluster_assignment_timeout_received': 'cluster.assignment_timeout_received',
    'envoy_cluster_bind_errors': 'cluster.bind_errors',
    'envoy_cluster_default_total_match_count': 'cluster.default_total_match',
    'envoy_cluster_ext_authz_ok': 'cluster.ext_authz.ok',
    'envoy_cluster_ext_authz_error': 'cluster.ext_authz.error',
    'envoy_cluster_ext_authz_denied': 'cluster.ext_authz.denied',
    'envoy_cluster_ext_authz_disabled': 'cluster.ext_authz.disabled',
    'envoy_cluster_ext_authz_failure_mode_allowed': 'cluster.ext_authz.failure_mode_allowed',
    'envoy_cluster_external_upstream_rq': 'cluster.external.upstream_rq',
    'envoy_cluster_external_upstream_rq_completed': 'cluster.external.upstream_rq_completed',
    'envoy_cluster_external_upstream_rq_xx': 'cluster.external.upstream_rq_xx',
    'envoy_cluster_external_upstream_rq_time': 'cluster.external.upstream_rq_time',
    'envoy_cluster_http2_dropped_headers_with_underscores': 'cluster.http2.dropped_headers_with_underscores',
    'envoy_cluster_http2_header_overflow': 'cluster.http2.header_overflow',
    'envoy_cluster_http2_headers_cb_no_stream': 'cluster.http2.headers_cb_no_stream',
    'envoy_cluster_http2_inbound_empty_frames_flood': 'cluster.http2.inbound_empty_frames_flood',
    'envoy_cluster_http2_inbound_priority_frames_flood': 'cluster.http2.inbound_priority_frames_flood',
    'envoy_cluster_http2_inbound_window_update_frames_flood': 'cluster.http2.inbound_window_update_frames_flood',
    'envoy_cluster_http2_keepalive_timeout': 'cluster.http2.keepalive_timeout',
    'envoy_cluster_http2_metadata_empty_frames': 'cluster.http2.metadata_empty_frames',
    'envoy_cluster_http2_outbound_control_flood': 'cluster.http2.outbound_control_flood',
    'envoy_cluster_http2_outbound_flood': 'cluster.http2.outbound_flood',
    'envoy_cluster_http2_requests_rejected_with_underscores_in_headers': (
        'cluster.http2.requests_rejected_with_underscores_in_headers'
    ),
    'envoy_cluster_http2_rx_messaging_error': 'cluster.http2.rx_messaging_error',
    'envoy_cluster_http2_rx_reset': 'cluster.http2.rx_reset',
    'envoy_cluster_http2_trailers': 'cluster.http2.trailers',
    'envoy_cluster_http2_tx_flush_timeout': 'cluster.http2.tx_flush_timeout',
    'envoy_cluster_http2_tx_reset': 'cluster.http2.tx_reset',
    'envoy_cluster_internal_upstream_rq': 'cluster.internal.upstream_rq',
    'envoy_cluster_internal_upstream_rq_completed': 'cluster.internal.upstream_rq_completed',
    'envoy_cluster_internal_upstream_rq_xx': 'cluster.internal.upstream_rq_xx',
    'envoy_cluster_lb_healthy_panic': 'cluster.lb_healthy_panic',
    'envoy_cluster_lb_local_cluster_not_ok': 'cluster.lb_local_cluster_not_ok',
    'envoy_cluster_lb_recalculate_zone_structures': 'cluster.lb_recalculate_zone_structures',
    'envoy_cluster_lb_subsets_created': 'cluster.lb_subsets_created',
    'envoy_cluster_lb_subsets_fallback': 'cluster.lb_subsets_fallback',
    'envoy_cluster_lb_subsets_fallback_panic': 'cluster.lb_subsets_fallback_panic',
    'envoy_cluster_lb_subsets_removed': 'cluster.lb_subsets_removed',
    'envoy_cluster_lb_subsets_selected': 'cluster.lb_subsets_selected',
    'envoy_cluster_lb_zone_cluster_too_small': 'cluster.lb_zone_cluster_too_small',
    'envoy_cluster_lb_zone_no_capacity_left': 'cluster.lb_zone_no_capacity_left',
    'envoy_cluster_lb_zone_number_differs': 'cluster.lb_zone_number_differs',
    'envoy_cluster_lb_zone_routing_all_directly': 'cluster.lb_zone_routing_all_directly',
    'envoy_cluster_lb_zone_routing_cross_zone': 'cluster.lb_zone_routing_cross_zone',
    'envoy_cluster_lb_zone_routing_sampled': 'cluster.lb_zone_routing_sampled',
    'envoy_cluster_membership_change': 'cluster.membership_change',
    'envoy_cluster_original_dst_host_invalid': 'cluster.original_dst_host_invalid',
    'envoy_cluster_ratelimit_ok': 'cluster.ratelimit.ok',
    'envoy_cluster_ratelimit_error': 'cluster.ratelimit.error',
    'envoy_cluster_ratelimit_over_limit': 'cluster.ratelimit.over_limit',
    'envoy_cluster_ratelimit_failure_mode_allowed': 'cluster.ratelimit.failure_mode_allowed',
    'envoy_cluster_retry_or_shadow_abandoned': 'cluster.retry_or_shadow_abandoned',
    'envoy_cluster_update_attempt': 'cluster.update_attempt',
    'envoy_cluster_update_empty': 'cluster.update_empty',
    'envoy_cluster_update_failure': 'cluster.update_failure',
    'envoy_cluster_update_no_rebuild': 'cluster.update_no_rebuild',
    'envoy_cluster_update_success': 'cluster.update_success',
    'envoy_cluster_upstream_cx_close_notify': 'cluster.upstream_cx_close_notify',
    'envoy_cluster_upstream_cx_connect_attempts_exceeded': 'cluster.upstream_cx_connect_attempts_exceeded',
    'envoy_cluster_upstream_cx_connect_fail': 'cluster.upstream_cx_connect_fail',
    'envoy_cluster_upstream_cx_connect_timeout': 'cluster.upstream_cx_connect_timeout',
    'envoy_cluster_upstream_cx_destroy': 'cluster.upstream_cx_destroy',
    'envoy_cluster_upstream_cx_destroy_local': 'cluster.upstream_cx_destroy_local',
    'envoy_cluster_upstream_cx_destroy_local_with_active_rq': 'cluster.upstream_cx_destroy_local_with_active_rq',
    'envoy_cluster_upstream_cx_destroy_remote': 'cluster.upstream_cx_destroy_remote',
    'envoy_cluster_upstream_cx_destroy_remote_with_active_rq': 'cluster.upstream_cx_destroy_remote_with_active_rq',
    'envoy_cluster_upstream_cx_destroy_with_active_rq': 'cluster.upstream_cx_destroy_with_active_rq',
    'envoy_cluster_upstream_cx_http1': 'cluster.upstream_cx_http1',
    'envoy_cluster_upstream_cx_http2': 'cluster.upstream_cx_http2',
    'envoy_cluster_upstream_cx_http3': 'cluster.upstream_cx_http3',
    'envoy_cluster_upstream_cx_idle_timeout': 'cluster.upstream_cx_idle_timeout',
    'envoy_cluster_upstream_cx_max_requests': 'cluster.upstream_cx_max_requests',
    'envoy_cluster_upstream_cx_none_healthy': 'cluster.upstream_cx_none_healthy',
    'envoy_cluster_upstream_cx_overflow': 'cluster.upstream_cx_overflow',
    'envoy_cluster_upstream_cx_pool_overflow': 'cluster.upstream_cx_pool_overflow',
    'envoy_cluster_upstream_cx_protocol_error': 'cluster.upstream_cx_protocol_error',
    'envoy_cluster_upstream_cx_rx_bytes': 'cluster.upstream_cx_rx_bytes',
    'envoy_cluster_upstream_cx_tx_bytes': 'cluster.upstream_cx_tx_bytes',
    'envoy_cluster_upstream_cx': 'cluster.upstream_cx',
    'envoy_cluster_upstream_flow_control_backed_up': 'cluster.upstream_flow_control_backed_up',
    'envoy_cluster_upstream_flow_control_drained': 'cluster.upstream_flow_control_drained',
    'envoy_cluster_upstream_flow_control_paused_reading': 'cluster.upstream_flow_control_paused_reading',
    'envoy_cluster_upstream_flow_control_resumed_reading': 'cluster.upstream_flow_control_resumed_reading',
    'envoy_cluster_upstream_internal_redirect_failed': 'cluster.upstream_internal_redirect_failed',
    'envoy_cluster_upstream_internal_redirect_succeeded': 'cluster.upstream_internal_redirect_succeeded',
    'envoy_cluster_upstream_rq': 'cluster.upstream_rq',
    'envoy_cluster_upstream_rq_cancelled': 'cluster.upstream_rq_cancelled',
    'envoy_cluster_upstream_rq_completed': 'cluster.upstream_rq_completed',
    'envoy_cluster_upstream_rq_maintenance_mode': 'cluster.upstream_rq_maintenance_mode',
    'envoy_cluster_upstream_rq_max_duration_reached': 'cluster.upstream_rq_max_duration_reached',
    'envoy_cluster_upstream_rq_pending_failure_eject': 'cluster.upstream_rq_pending_failure_eject',
    'envoy_cluster_upstream_rq_pending_overflow': 'cluster.upstream_rq_pending_overflow',
    'envoy_cluster_upstream_rq_pending': 'cluster.upstream_rq_pending',
    'envoy_cluster_upstream_rq_per_try_timeout': 'cluster.upstream_rq_per_try_timeout',
    'envoy_cluster_upstream_rq_retry': 'cluster.upstream_rq_retry',
    'envoy_cluster_upstream_rq_retry_backoff_exponential': 'cluster.upstream_rq_retry_backoff_exponential',
    'envoy_cluster_upstream_rq_retry_backoff_ratelimited': 'cluster.upstream_rq_retry_backoff_ratelimited',
    'envoy_cluster_upstream_rq_retry_limit_exceeded': 'cluster.upstream_rq_retry_limit_exceeded',
    'envoy_cluster_upstream_rq_retry_overflow': 'cluster.upstream_rq_retry_overflow',
    'envoy_cluster_upstream_rq_retry_success': 'cluster.upstream_rq_retry_success',
    'envoy_cluster_upstream_rq_rx_reset': 'cluster.upstream_rq_rx_reset',
    'envoy_cluster_upstream_rq_time': 'cluster.upstream_rq_time',
    'envoy_cluster_upstream_rq_timeout': 'cluster.upstream_rq_timeout',
    'envoy_cluster_upstream_rq_tx_reset': 'cluster.upstream_rq_tx_reset',
    'envoy_cluster_upstream_rq_xx': 'cluster.upstream_rq_xx',
    'envoy_cluster_manager_cds_control_plane_rate_limit_enforced': (
        'cluster_manager.cds.control_plane.rate_limit_enforced'
    ),
    'envoy_cluster_manager_cds_init_fetch_timeout': 'cluster_manager.cds.init_fetch_timeout',
    'envoy_cluster_manager_cds_update_attempt': 'cluster_manager.cds.update_attempt',
    'envoy_cluster_manager_cds_update_failure': 'cluster_manager.cds.update_failure',
    'envoy_cluster_manager_cds_update_rejected': 'cluster_manager.cds.update_rejected',
    'envoy_cluster_manager_cds_update_success': 'cluster_manager.cds.update_success',
    'envoy_cluster_manager_cluster_added': 'cluster_manager.cluster_added',
    'envoy_cluster_manager_cluster_modified': 'cluster_manager.cluster_modified',
    'envoy_cluster_manager_cluster_removed': 'cluster_manager.cluster_removed',
    'envoy_cluster_manager_cluster_updated': 'cluster_manager.cluster_updated',
    'envoy_cluster_manager_cluster_updated_via_merge': 'cluster_manager.custer_updated_via_merge',
    'envoy_cluster_manager_update_merge_cancelled': 'cluster_manager.update_merge_cancelled',
    'envoy_cluster_manager_update_out_of_merge_window': 'cluster_manager.update_out_of_merge_window',
    'envoy_filesystem_flushed_by_timer': 'filesystem.flushed_by_timer',
    'envoy_filesystem_reopen_failed': 'filesystem.reopen_failed',
    'envoy_filesystem_write_buffered': 'filesystem.write_buffered',
    'envoy_filesystem_write_completed': 'filesystem.write_completed',
    'envoy_filesystem_write_failed': 'filesystem.write_failed',
    'envoy_http_downstream_cx_delayed_close_timeout': 'http.downstream_cx_delayed_close_timeout',
    'envoy_http_downstream_cx_destroy': 'http.downstream_cx_destroy',
    'envoy_http_downstream_cx_destroy_active_rq': 'http.downstream_cx_destroy_active_rq',
    'envoy_http_downstream_cx_destroy_local': 'http.downstream_cx_destroy_local',
    'envoy_http_downstream_cx_destroy_local_active_rq': 'http.downstream_cx_destroy_local_active_rq',
    'envoy_http_downstream_cx_destroy_remote': 'http.downstream_cx_destroy_remote',
    'envoy_http_downstream_cx_destroy_remote_active_rq': 'http.downstream_cx_destroy_remote_active_rq',
    'envoy_http_downstream_cx_drain_close': 'http.downstream_cx_drain_close',
    'envoy_http_downstream_cx_http1': 'http.downstream_cx_http1',
    'envoy_http_downstream_cx_http2': 'http.downstream_cx_http2',
    'envoy_http_downstream_cx_http3': 'http.downstream_cx_http3',
    'envoy_http_downstream_cx_idle_timeout': 'http.downstream_cx_idle_timeout',
    'envoy_http_downstream_cx_max_duration_reached': 'http.downstream_cx_max_duration_reached',
    'envoy_http_downstream_cx_overload_disable_keepalive': 'http.downstream_cx_overload_disable_keepalive',
    'envoy_http_downstream_cx_protocol_error': 'http.downstream_cx_protocol_error',
    'envoy_http_downstream_cx_rx_bytes': 'http.downstream_cx_rx_bytes',
    'envoy_http_downstream_cx_ssl': 'http.downstream_cx_ssl',
    'envoy_http_downstream_cx': 'http.downstream_cx',
    'envoy_http_downstream_cx_tx_bytes': 'http.downstream_cx_tx_bytes',
    'envoy_http_downstream_cx_upgrades': 'http.downstream_cx_upgrades',
    'envoy_http_downstream_flow_control_paused_reading': 'http.downstream_flow_control_paused_reading',
    'envoy_http_downstream_flow_control_resumed_reading': 'http.downstream_flow_control_resumed_reading',
    'envoy_http_downstream_rq_completed': 'http.downstream_rq_completed',
    'envoy_http_downstream_rq_failed_path_normalization': 'http.downstream_rq_failed_path_normalization',
    'envoy_http_downstream_rq_header_timeout': 'http.downstream_rq_header_timeout',
    'envoy_http_downstream_rq_http1': 'http.downstream_rq_http1',
    'envoy_http_downstream_rq_http2': 'http.downstream_rq_http2',
    'envoy_http_downstream_rq_http3': 'http.downstream_rq_http3',
    'envoy_http_downstream_rq_idle_timeout': 'http.downstream_rq_idle_timeout',
    'envoy_http_downstream_rq_max_duration_reached': 'http.downstream_rq_max_duration_reached',
    'envoy_http_downstream_rq_non_relative_path': 'http.downstream_rq_non_relative_path',
    'envoy_http_downstream_rq_overload_close': 'http.downstream_rq_overload_close',
    'envoy_http_downstream_rq_redirected_with_normalized_path': 'http.downstream_rq_redirected_with_normalized_path',
    'envoy_http_downstream_rq_response_before_rq_complete': 'http.downstream_rq_response_before_rq_complete',
    'envoy_http_downstream_rq_rx_reset': 'http.downstream_rq_rx_reset',
    'envoy_http_downstream_rq_timeout': 'http.downstream_rq_timeout',
    'envoy_http_downstream_rq_too_large': 'http.downstream_rq_too_large',
    'envoy_http_downstream_rq': 'http.downstream_rq',
    'envoy_http_downstream_rq_tx_reset': 'http.downstream_rq_tx_reset',
    'envoy_http_downstream_rq_ws_on_non_ws_route': 'http.downstream_rq_ws_on_non_ws_route',
    'envoy_http_downstream_rq_xx': 'http.downstream_rq_xx',
    'envoy_http_no_cluster': 'http.no_cluster',
    'envoy_http_no_route': 'http.no_route',
    'envoy_http_passthrough_internal_redirect_bad_location': 'http.passthrough_internal_redirect_bad_location',
    'envoy_http_passthrough_internal_redirect_no_route': 'http.passthrough_internal_redirect_no_route',
    'envoy_http_passthrough_internal_redirect_predicate': 'http.passthrough_internal_redirect_predicate',
    'envoy_http_passthrough_internal_redirect_too_many_redirects': (
        'http.passthrough_internal_redirect_too_many_redirects'
    ),
    'envoy_http_passthrough_internal_redirect_unsafe_scheme': 'http.passthrough_internal_redirect_unsafe_scheme',
    'envoy_http_rq_direct_response': 'http.rq_direct_response',
    'envoy_http_rq_redirect': 'http.rq_redirect',
    'envoy_http_rq_reset_after_downstream_response_started': 'http.rq_reset_after_downstream_response_started',
    'envoy_http_rq': 'http.rq',
    'envoy_http_rs_too_large': 'http.rs_too_large',
    'envoy_http_tracing_client_enabled': 'http.tracing.client_enabled',
    'envoy_http_tracing_health_check': 'http.tracing.health_check',
    'envoy_http_tracing_not_traceable': 'http.tracing.not_traceable',
    'envoy_http_tracing_random_sampling': 'http.tracing.random_sampling',
    'envoy_http_tracing_service_forced': 'http.tracing.service_forced',
    'envoy_http1_dropped_headers_with_underscores': 'cluster.http1.dropped_headers_with_underscores',
    'envoy_http1_metadata_not_supported_error': 'cluster.http1.metadata_not_supported_error',
    'envoy_http1_requests_rejected_with_underscores_in_headers': (
        'cluster.http1.requests_rejected_with_underscores_in_headers'
    ),
    'envoy_http1_response_flood': 'cluster.http1.response_flood',
    'envoy_listener_admin_downstream_cx_destroy': 'listener.admin.downstream_cx_destroy',
    'envoy_listener_admin_downstream_cx_overflow': 'listener.admin.downstream_cx_overflow',
    'envoy_listener_admin_downstream_cx_overload_reject': 'listener.admin.downstream_cx_overload_reject',
    'envoy_listener_admin_downstream_cx': 'listener.admin.downstream_cx',
    'envoy_listener_admin_downstream_global_cx_overflow': 'listener.admin.downstream_global_cx_overflow',
    'envoy_listener_admin_downstream_pre_cx_timeout': 'listener.admin.downstream_pre_cx_timeout',
    'envoy_listener_admin_http_downstream_rq_completed': 'listener.admin.http.downstream_rq_completed',
    'envoy_listener_admin_http_downstream_rq_xx': 'listener.admin.http.downstream_rq_xx',
    'envoy_listener_admin_no_filter_chain_match': 'listener.admin.no_filter_chain_match',
    'envoy_listener_downstream_cx_destroy': 'listener.downstream_cx_destroy',
    'envoy_listener_downstream_cx_overflow': 'listener.downstream_cx_overflow',
    'envoy_listener_downstream_cx_overload_reject': 'listener.downstream_cx_overload_reject',
    'envoy_listener_downstream_cx': 'listener.downstream_cx',
    'envoy_listener_downstream_global_cx_overflow': 'listener.downstream_global_cx_overflow',
    'envoy_listener_downstream_pre_cx_timeout': 'listener.downstream_pre_cx_timeout',
    'envoy_listener_http_downstream_rq_completed': 'listener.http.downstream_rq_completed',
    'envoy_listener_http_downstream_rq_xx': 'listener.http.downstream_rq_xx',
    'envoy_listener_no_filter_chain_match': 'listener.no_filter_chain_match',
    'envoy_listener_manager_lds_control_plane_rate_limit_enforced': (
        'listener_manager.lds.control_plane.rate_limit_enforced'
    ),
    'envoy_listener_manager_lds_init_fetch_timeout': 'listener_manager.lds.init_fetch_timeout',
    'envoy_listener_manager_lds_update_attempt': 'listener_manager.lds.update_attempt',
    'envoy_listener_manager_lds_update_failure': 'listener_manager.lds.update_failure',
    'envoy_listener_manager_lds_update_rejected': 'listener_manager.lds.update_rejected',
    'envoy_listener_manager_lds_update_success': 'listener_manager.lds.update_success',
    'envoy_listener_manager_listener_added': 'listener_manager.listener_added',
    'envoy_listener_manager_listener_create_failure': 'listener_manager.listener_create_failure',
    'envoy_listener_manager_listener_create_success': 'listener_manager.listener_create_success',
    'envoy_listener_manager_listener_in_place_updated': 'listener_manager.listener_in_place_updated',
    'envoy_listener_manager_listener_modified': 'listener_manager.listener_modified',
    'envoy_listener_manager_listener_removed': 'listener_manager.listener_removed',
    'envoy_listener_manager_listener_stopped': 'listener_manager.listener_stopped',
    'envoy_runtime_deprecated_feature_use': 'runtime.deprecated_feature_use',
    'envoy_runtime_load_error': 'runtime.load_error',
    'envoy_runtime_load_success': 'runtime.load_success',
    'envoy_runtime_override_dir_exists': 'runtime.override_dir_exists',
    'envoy_runtime_override_dir_not_exists': 'runtime.override_dir_not_exists',
    'envoy_server_debug_assertion_failures': 'server.debug_assertion_failures',
    'envoy_server_dynamic_unknown_fields': 'server.dynamic_unknown_fields',
    'envoy_server_envoy_bug_failures': 'server.envoy_bug_failure',
    'envoy_server_static_unknown_fields': 'server.static_unknown_fields',
    'envoy_vhost_vcluster_upstream_rq_retry': 'vhost.vcluster.upstream_rq_retry',
    'envoy_vhost_vcluster_upstream_rq_retry_limit_exceeded': 'vhost.vcluster.upstream_rq_retry_limit_exceeded',
    'envoy_vhost_vcluster_upstream_rq_retry_overflow': 'vhost.vcluster.upstream_rq_retry_overflow',
    'envoy_vhost_vcluster_upstream_rq_retry_success': 'vhost.vcluster.upstream_rq_retry_success',
    'envoy_vhost_vcluster_upstream_rq_timeout': 'vhost.vcluster.upstream_rq_timeout',
    'envoy_vhost_vcluster_upstream_rq': 'vhost.vcluster.upstream_rq',
    'envoy_cluster_http2_pending_send_bytes': 'cluster.http2.pending_send_bytes',
    'envoy_cluster_http2_streams_active': 'cluster.http2.streams_active',
    'envoy_cluster_lb_subsets_active': 'cluster.lb_subsets_active',
    'envoy_cluster_max_host_weight': 'cluster.max_host_weight',
    'envoy_cluster_membership_degraded': 'cluster.membership_degraded',
    'envoy_cluster_membership_excluded': 'cluster.membership_excluded',
    'envoy_cluster_membership_healthy': 'cluster.membership_healthy',
    'envoy_cluster_membership_total': 'cluster.membership_total',
    'envoy_cluster_version': 'cluster.version',
    'envoy_cluster_upstream_cx_active': 'cluster.upstream_cx_active',
    'envoy_cluster_upstream_cx_rx_bytes_buffered': 'cluster.upstream_cx_rx_bytes_buffered',
    'envoy_cluster_upstream_cx_tx_bytes_buffered': 'cluster.upstream_cx_tx_bytes_buffered',
    'envoy_cluster_upstream_rq_active': 'cluster.upstream_rq_active',
    'envoy_cluster_upstream_rq_pending_active': 'cluster.upstream_rq_pending_active',
    'envoy_cluster_manager_active_clusters': 'cluster_manager.active_clusters',
    'envoy_cluster_manager_cds_control_plane_connected_state': 'cluster_manager.cds.control_plane.connected_state',
    'envoy_cluster_manager_cds_control_plane_pending_requests': 'cluster_manager.cds.control_plane.pending_requests',
    'envoy_cluster_manager_cds_update_time': 'cluster_manager.cds.update_time',
    'envoy_cluster_manager_cds_version': 'cluster_manager.cds.version',
    'envoy_cluster_manager_warming_clusters': 'cluster_manager.warming_clusters',
    'envoy_filesystem_write_total_buffered': 'filesystem.write_total_buffered',
    'envoy_http_downstream_cx_active': 'http.downstream_cx_active',
    'envoy_http_downstream_cx_http1_active': 'http.downstream_cx_http1_active',
    'envoy_http_downstream_cx_http2_active': 'http.downstream_cx_http2_active',
    'envoy_http_downstream_cx_http3_active': 'http.downstream_cx_http3_active',
    'envoy_http_downstream_cx_rx_bytes_buffered': 'http.downstream_cx_rx_bytes_buffered',
    'envoy_http_downstream_cx_ssl_active': 'http.downstream_cx_ssl_active',
    'envoy_http_downstream_cx_tx_bytes_buffered': 'http.downstream_cx_tx_bytes_buffered',
    'envoy_http_downstream_cx_upgrades_active': 'http.downstream_cx_upgrades_active',
    'envoy_http_downstream_rq_active': 'http.downstream_rq_active',
    'envoy_listener_admin_downstream_cx_active': 'listener.admin.downstream_cx_active',
    'envoy_listener_admin_downstream_pre_cx_active': 'listener.admin.downstream_pre_cx_active',
    'envoy_listener_downstream_cx_active': 'listener.downstream_cx_active',
    'envoy_listener_downstream_pre_cx_active': 'listener.downstream_pre_cx_active',
    'envoy_listener_manager_lds_control_plane_connected_state': 'listener_manager.lds.control_plane.connected_state',
    'envoy_listener_manager_lds_control_plane_pending_requests': 'listener_manager.lds.control_plane.pending_requests',
    'envoy_listener_manager_lds_update_time': 'listener_manager.lds.update_time',
    'envoy_listener_manager_lds_version': 'listener_manager.lds.version',
    'envoy_listener_manager_total_filter_chains_draining': 'listener_manager.total_filter_chains_draining',
    'envoy_listener_manager_total_listeners_active': 'listener_manager.total_listeners_active',
    'envoy_listener_manager_total_listeners_draining': 'listener_manager.total_listeners_draining',
    'envoy_listener_manager_total_listeners_warming': 'listener_manager.total_listeners_warming',
    'envoy_listener_manager_workers_started': 'listener_manager.workers_started',
    'envoy_runtime_admin_overrides_active': 'runtime.admin_overrides_active',
    'envoy_runtime_deprecated_feature_seen_since_process_start': 'runtime.deprecated_feature_seen_since_process_start',
    'envoy_runtime_num_keys': 'runtime.num_keys',
    'envoy_runtime_num_layers': 'runtime.num_layers',
    'envoy_server_compilation_settings_fips_mode': 'server.compilation_settings_fips_mode',
    'envoy_server_concurrency': 'server.concurrency',
    'envoy_server_days_until_first_cert_expiring': 'server.days_until_first_cert_expiring',
    'envoy_server_hot_restart_epoch': 'server.hot_restart_epoch',
    'envoy_server_hot_restart_generation': 'server.hot_restart_generation',
    'envoy_server_live': 'server.live',
    'envoy_server_memory_allocated': 'server.memory_allocated',
    'envoy_server_memory_heap_size': 'server.memory_heap_size',
    'envoy_server_memory_physical_size': 'server.memory_physical_size',
    'envoy_server_parent_connections': 'server.parent_connections',
    'envoy_server_seconds_until_first_ocsp_response_expiring': 'server.seconds_until_first_ocsp_response_expiring',
    'envoy_server_state': 'server.state',
    'envoy_server_stats_recent_lookups': 'server.stats_recent_lookups',
    'envoy_server_total_connections': 'server.total_connections',
    'envoy_server_uptime': 'server.uptime',
    'envoy_server_version': 'server.version',
    'envoy_wasm_remote_load_cache_entries': 'wasm.remote_load_cache_entries',
    'envoy_wasm_envoy_wasm_runtime_null_active': 'wasm.envoy_wasm.runtime_null_active',
    'envoy_wasm_remote_load_fetch_successes': 'wasm.remote_load_fetch_successes',
    'envoy_wasm_remote_load_fetch_failures': 'wasm.remote_load_fetch_failures',
    'envoy_wasm_remote_load_cache_negative_hits': 'wasm.remote_load_cache_negative_hits',
    'envoy_wasm_remote_load_cache_misses': 'wasm.remote_load_cache_misses',
    'envoy_wasm_remote_load_cache_hits': 'wasm.remote_load_cache_hits',
    'envoy_wasm_envoy_wasm_runtime_null_created': 'wasm.envoy_wasm.runtime_null_created',
    'envoy_metric_cache_count': 'metric_cache_count',
    'envoy_server_dropped_stat_flushes': 'server.dropped_stat_flushes',
    'envoy_cluster_upstream_rq_200': 'cluster.upstream_rq_200',
    'envoy_cluster_http2_stream_refused_errors': 'cluster.http2.stream_refused_errors',
    'envoy_cluster_internal_upstream_rq_200': 'cluster.internal.upstream_rq_200',
    'envoy_cluster_upstream_cx_connect_ms': 'cluster.upstream_cx_connect_ms',
    'envoy_cluster_upstream_cx_length_ms': 'cluster.upstream_cx_length_ms',
    'envoy_cluster_manager_cds_update_duration': 'cluster_manager.cds.update_duration',
    'envoy_http_downstream_cx_length_ms': 'http.downstream_cx_length_ms',
    'envoy_http_downstream_rq_time': 'http.downstream_rq_time',
    'envoy_listener_admin_downstream_cx_length_ms': 'listener.admin.downstream_cx_length_ms',
    'envoy_listener_downstream_cx_length_ms': 'listener.downstream_cx_length_ms',
    'envoy_listener_manager_lds_update_duration': 'listener_manager.lds.update_duration',
    'envoy_server_initialization_time_ms': 'server.initialization_time_ms',
    'envoy_workers_watchdog_miss': 'workers.watchdog_miss',
    'envoy_workers_watchdog_mega_miss': 'workers.watchdog_mega_miss',
    'envoy_cluster_outlier_detection_ejections_active': 'cluster.outlier_detection.ejections_active',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_overflow': 'cluster.outlier_detection.ejections_overflow',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_consecutive_5xx': 'cluster.outlier_detection.ejections_enforced_consecutive_5xx',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_consecutive_5xx': 'cluster.outlier_detection.ejections_detected_consecutive_5xx',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_success_rate': 'cluster.outlier_detection.ejections_enforced_success_rate',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_success_rate': 'cluster.outlier_detection.ejections_detected_success_rate',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_consecutive_gateway_failure': 'cluster.outlier_detection.ejections_enforced_consecutive_gateway_failure',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_consecutive_gateway_failure': 'cluster.outlier_detection.ejections_detected_consecutive_gateway_failure',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_consecutive_local_origin_failure': 'cluster.outlier_detection.ejections_enforced_consecutive_local_origin_failure',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_consecutive_local_origin_failure': 'cluster.outlier_detection.ejections_detected_consecutive_local_origin_failure',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_local_origin_success_rate': 'cluster.outlier_detection.ejections_enforced_local_origin_success_rate',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_local_origin_success_rate': 'cluster.outlier_detection.ejections_detected_local_origin_success_rate',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_failure_percentage': 'cluster.outlier_detection.ejections_enforced_failure_percentage',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_failure_percentage': 'cluster.outlier_detection.ejections_detected_failure_percentage',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_enforced_failure_percentage_local_origin': 'cluster.outlier_detection.ejections_enforced_failure_percentage_local_origin',  # noqa: E501
    'envoy_cluster_outlier_detection_ejections_detected_failure_percentage_local_origin': 'cluster.outlier_detection.ejections_detected_failure_percentage_local_origin',  # noqa: E501
    'envoy_access_logs_grpc_access_log_logs_dropped': 'access_logs.grpc_access_log.logs_dropped',
    'envoy_access_logs_grpc_access_log_logs_written': 'access_logs.grpc_access_log.logs_written',
    'envoy_tcp_downstream_cx': 'tcp.downstream_cx',
    'envoy_tcp_downstream_cx_no_route': 'tcp.downstream_cx_no_route',
    'envoy_tcp_downstream_cx_tx_bytes': 'tcp.downstream_cx_tx_bytes',
    'envoy_tcp_downstream_cx_tx_bytes_buffered': 'tcp.downstream_cx_tx_bytes_buffered',
    'envoy_tcp_downstream_cx_rx_bytes': 'tcp.downstream_cx_rx_bytes',
    'envoy_tcp_downstream_cx_rx_bytes_buffered': 'tcp.downstream_cx_rx_bytes_buffered',
    'envoy_tcp_downstream_flow_control_paused_reading_': 'tcp.downstream_flow_control_paused_reading',
    'envoy_tcp_downstream_flow_control_resumed_reading': 'tcp.downstream_flow_control_resumed_reading',
    'envoy_tcp_idle_timeout': 'tcp.idle_timeout',
    'envoy_tcp_on_demand_cluster_attempt': 'tcp.on_demand_cluster_attempt',
    'envoy_tcp_on_demand_cluster_missing': 'tcp.on_demand_cluster_missing',
    'envoy_tcp_on_demand_cluster_success': 'tcp.on_demand_cluster_success',
    'envoy_tcp_on_demand_cluster_timeout': 'tcp.on_demand_cluster_timeout',
    'envoy_tcp_upstream_flush': 'tcp.upstream_flush',
    'envoy_tcp_upstream_flush_active': 'tcp.upstream_flush_active',
    'envoy_http_rbac_allowed': 'http.rbac_allowed',
    'envoy_http_rbac_denied': 'http.rbac_denied',
    'envoy_http_rbac_shadow_allowed': 'http.rbac_shadow_allowed',
    'envoy_http_rbac_shadow_denied': 'http.rbac_shadow_denied',
    'envoy_http_local_rate_limit_enabled': 'http.local_rate_limit_enabled',
    'envoy_http_local_rate_limit_enforced': 'http.local_rate_limit_enforced',
    'envoy_http_local_rate_limit_rate_limited': 'http.local_rate_limit_rate_limited',
    'envoy_http_local_rate_limit_ok': 'http.local_rate_limit_ok',
    'envoy_control_plane_connected_state': 'control_plane.connected_state',
    'envoy_listener_server_ssl_socket_factory_ssl_context_update_by_sds': 'listener.server_ssl_socket_factory.ssl_context_update_by_sds',  # noqa: E501
    'envoy_listener_server_ssl_socket_factory_upstream_context_secrets_not_ready': 'listener.server_ssl_socket_factory.upstream_context_secrets_not_ready',  # noqa: E501
    'envoy_listener_server_ssl_socket_factory_downstream_context_secrets_not_ready': 'listener.server_ssl_socket_factory.downstream_context_secrets_not_ready',  # noqa: E501
    'envoy_cluster_client_ssl_socket_factory_ssl_context_update_by_sds': 'cluster.client_ssl_socket_factory.ssl_context_update_by_sds',  # noqa: E501
    'envoy_cluster_client_ssl_socket_factory_upstream_context_secrets_not_ready': 'cluster.client_ssl_socket_factory.upstream_context_secrets_not_ready',  # noqa: E501
    'envoy_cluster_client_ssl_socket_factory_downstream_context_secrets_not_ready': 'cluster.client_ssl_socket_factory.downstream_context_secrets_not_ready',  # noqa: E501
    'envoy_connection_limit_active_connections': 'connection_limit.active_connections',
    'envoy_connection_limit_limited_connections': 'connection_limit.limited_connections',
}

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
    'cluster.ext_authz.ok': {
        'tags': (
            ('envoy_cluster', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ext_authz.error': {
        'tags': (
            ('envoy_cluster', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ext_authz.denied': {
        'tags': (
            ('envoy_cluster', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ext_authz.disabled': {
        'tags': (
            ('envoy_cluster', ),
            ('stat_prefix', ),
            (),
        ),
        'method': 'monotonic_count',
    },
    'cluster.ext_authz.failure_mode_allowed': {
        'tags': (
            ('envoy_cluster', ),
            (),
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
    'cluster.ratelimit.failure_mode_allowed': {
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
    'access_logs.grpc_access_log.logs_dropped': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'access_logs.grpc_access_log.logs_written': {
        'tags': (
            (),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rbac.allowed': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rbac.denied': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rbac.shadow_allowed': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'http.rbac.shadow_denied': {
        'tags': (
            ('stat_prefix',),
            ('shadow_rule_prefix',),
            (),
        ),
        'method': 'monotonic_count',
    },
    # "*." to match at the beginning of raw metric if it doesn't have a standard name
    '*.http_local_rate_limit.enabled': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    '*.http_local_rate_limit.enforced': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    '*.http_local_rate_limit.rate_limited': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    '*.http_local_rate_limit.ok': {
        'tags': (
            ('stat_prefix',),
            (),
            (),
        ),
        'method': 'monotonic_count',
    },
    'connection_limit.active_connections': {
        'tags': (
            ('stat_prefix',),
            (),
        ),
        'method': 'gauge',
    },
    'connection_limit.limited_connections': {
        'tags': (
            ('stat_prefix',),
            (),
        ),
        'method': 'monotonic_count',
    },
}
# fmt: on

MOD_METRICS = modify_metrics_dict(METRICS)
METRIC_TREE = make_metric_tree(METRICS)
