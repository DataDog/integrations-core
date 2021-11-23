# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

METRIC_MAP = {
    'envoy_cluster_assignment_stale': 'cluster.assignment_stale',
    'envoy_cluster_assignment_timeout_received': 'cluster.assignment_timeout_received',
    'envoy_cluster_bind_errors': 'cluster.bind_errors',
    'envoy_cluster_default_total_match_count': 'cluster.default_total_match', # Not sure if default is custom
    'envoy_cluster_http2_dropped_headers_with_underscores': 'cluster.http2.dropped_headers_with_underscores', # New for http2
    'envoy_cluster_http2_header_overflow': 'cluster.http2.header_overflow',
    'envoy_cluster_http2_headers_cb_no_stream': 'cluster.http2.headers_cb_no_stream',
    'envoy_cluster_http2_inbound_empty_frames_flood': 'cluster.http2.inbound_empty_frames_flood',
    'envoy_cluster_http2_inbound_priority_frames_flood': 'cluster.http2.inbound_priority_frames_flood',
    'envoy_cluster_http2_inbound_window_update_frames_flood': 'cluster.http2.inbound_window_update_frames_flood',
    'envoy_cluster_http2_keepalive_timeout': 'cluster.http2.keepalive_timeout', # New
    'envoy_cluster_http2_metadata_empty_frames': 'cluster.http2.metadata_empty_frames', # New
    'envoy_cluster_http2_outbound_control_flood': 'cluster.http2.outbound_control_flood',
    'envoy_cluster_http2_outbound_flood': 'cluster.http2.outbound_flood',
    'envoy_cluster_http2_requests_rejected_with_underscores_in_headers': 'cluster.http2.requests_rejected_with_underscores_in_headers', # New for http2
    'envoy_cluster_http2_rx_messaging_error': 'cluster.http2.rx_messaging_error',
    'envoy_cluster_http2_rx_reset': 'cluster.http2.rx_reset',
    'envoy_cluster_http2_trailers': 'cluster.http2.trailers',
    'envoy_cluster_http2_tx_flush_timeout': 'cluster.http2.tx_flush_timeout', # New
    'envoy_cluster_http2_tx_reset': 'cluster.http2.tx_reset',
    'envoy_cluster_internal_upstream_rq': 'cluster.internal.upstream_rq', # New? I don't see one without addl suffix
    'envoy_cluster_internal_upstream_rq_completed': 'cluster.internal.upstream_rq_completed',
    'envoy_cluster_internal_upstream_rq_xx': 'cluster.internal.upstream_rq_xx', # Looks like tagged by 1,2,3,4 (replacing 1xx,2xx...)
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
    'envoy_cluster_upstream_cx_destroy_local_with_active_rq':  'cluster.upstream_cx_destroy_local_with_active_rq',
    'envoy_cluster_upstream_cx_destroy_remote': 'cluster.upstream_cx_destroy_remote',
    'envoy_cluster_upstream_cx_destroy_remote_with_active_rq': 'cluster.upstream_cx_destroy_with_active_rq',
    'envoy_cluster_upstream_cx_destroy_with_active_rq': 'cluster.upstream_cx_destroy_with_active_rq',
    'envoy_cluster_upstream_cx_http1_total': 'cluster.upstream_cx_http1_total',
    'envoy_cluster_upstream_cx_http2_total': 'cluster.upstream_cx_http2_total',
    'envoy_cluster_upstream_cx_http3_total': 'cluster.upstream_cx_http3_total',
    'envoy_cluster_upstream_cx_idle_timeout': 'cluster.upstream_cx_idle_timeout',
    'envoy_cluster_upstream_cx_max_requests': 'cluster.upstream_cx_max_requests',
    'envoy_cluster_upstream_cx_none_healthy': 'cluster.upstream_cx_none_healthy',
    'envoy_cluster_upstream_cx_overflow': 'cluster.upstream_cx_overflow',
    'envoy_cluster_upstream_cx_pool_overflow': 'cluster.upstream_cx_pool_overflow',
    'envoy_cluster_upstream_cx_protocol_error': 'cluster.upstream_cx_protocol_error',
    'envoy_cluster_upstream_cx_rx_bytes_total': 'cluster.upstream_cx_rx_bytes_total',
    'envoy_cluster_upstream_cx_total': 'cluster.upstream_cx_total',
    'envoy_cluster_upstream_cx_tx_bytes_total': 'cluster.upstream_cx_tx_bytes_total',
    'envoy_cluster_upstream_flow_control_backed_up_total': 'cluster.upstream_flow_control_backed_up_total',
    'envoy_cluster_upstream_flow_control_drained_total': 'cluster.upstream_flow_control_drained_total',
    'envoy_cluster_upstream_flow_control_paused_reading_total': 'cluster.upstream_flow_control_paused_reading_total',
    'envoy_cluster_upstream_flow_control_resumed_reading_total': 'cluster.upstream_flow_control_resumed_reading_total',
    'envoy_cluster_upstream_internal_redirect_failed_total': 'cluster.upstream_internal_redirect_failed_total',
    'envoy_cluster_upstream_internal_redirect_succeeded_total': 'cluster.upstream_internal_redirect_succeeded_total',
    'envoy_cluster_upstream_rq': 'cluster.upstream_rq', # New? I don't see one without addl suffix
    'envoy_cluster_upstream_rq_cancelled': 'cluster.upstream_rq_cancelled',
    'envoy_cluster_upstream_rq_completed': 'cluster.upstream_rq_completed',
    'envoy_cluster_upstream_rq_maintenance_mode': 'cluster.upstream_rq_maintenance_mode',
    'envoy_cluster_upstream_rq_max_duration_reached': 'cluster.upstream_rq_max_duration_reached',
    'envoy_cluster_upstream_rq_pending_failure_eject': 'cluster.upstream_rq_pending_failure_eject',
    'envoy_cluster_upstream_rq_pending_overflow': 'cluster.upstream_rq_pending_overflow',
    'envoy_cluster_upstream_rq_pending_total': 'cluster.upstream_rq_pending_total',
    'envoy_cluster_upstream_rq_per_try_timeout': 'cluster.upstream_rq_per_try_timeout',
    'envoy_cluster_upstream_rq_retry': 'cluster.upstream_rq_retry',
    'envoy_cluster_upstream_rq_retry_backoff_exponential': 'cluster.upstream_rq_retry_backoff_exponential', # New
    'envoy_cluster_upstream_rq_retry_backoff_ratelimited': 'cluster.upstream_rq_retry_backoff_ratelimited', # New
    'envoy_cluster_upstream_rq_retry_limit_exceeded': 'cluster.upstream_rq_retry_limit_exceeded', # New
    'envoy_cluster_upstream_rq_retry_overflow': 'cluster.upstream_rq_retry_overflow',
    'envoy_cluster_upstream_rq_retry_success': 'cluster.upstream_rq_retry_success',
    'envoy_cluster_upstream_rq_rx_reset': 'cluster.upstream_rq_rx_reset',
    'envoy_cluster_upstream_rq_timeout': 'cluster.upstream_rq_timeout',
    'envoy_cluster_upstream_rq_total': 'cluster.upstream_rq_total',
    'envoy_cluster_upstream_rq_tx_reset': 'cluster.upstream_rq_tx_reset',
    'envoy_cluster_upstream_rq_xx': 'cluster.upstream_rq_xx', # Newish (replacing 1xx,2xx...)
    'envoy_cluster_manager_cds_control_plane_rate_limit_enforced': 'cluster_manager.cds.control_plane.rate_limit_enforced',
    'envoy_cluster_manager_cds_init_fetch_timeout': 'cluster_manager.cds.init_fetch_timeout', # New
    'envoy_cluster_manager_cds_update_attempt': 'cluster_manager.cds.update_attempt',
    'envoy_cluster_manager_cds_update_failure': 'cluster_manager.cds.update_failure',
    'envoy_cluster_manager_cds_update_rejected': 'cluster_manager.cds.update_rejected',
    'envoy_cluster_manager_cds_update_success': 'cluster_manager.cds.update_success',
    'envoy_cluster_manager_cluster_added': 'cluster_manager.cluster_added',
    'envoy_cluster_manager_cluster_modified': 'cluster_manager.cluster_modified',
    'envoy_cluster_manager_cluster_removed': 'cluster_manager.cluster_removed',
    'envoy_cluster_manager_cluster_updated': 'cluster_manager.cluster_updated', # New
    'envoy_cluster_manager_cluster_updated_via_merge': 'cluster_manager.custer_updated_via_merge', # New
    'envoy_cluster_manager_update_merge_cancelled': 'cluster_manager.update_merge_cancelled', # New
    'envoy_cluster_manager_update_out_of_merge_window': 'cluster_manager.update_out_of_merge_window', # New
    'envoy_filesystem_flushed_by_timer': 'filesystem.flushed_by_timer',
    'envoy_filesystem_reopen_failed': 'filesystem.reopen_failed',
    'envoy_filesystem_write_buffered': 'filesystem.write_buffered',
    'envoy_filesystem_write_completed': 'filesystem.write_completed',
    'envoy_filesystem_write_failed':  'filesystem.write_failed', # New
    'envoy_http_downstream_cx_delayed_close_timeout': 'http.downstream_cx_delayed_close_timeout', # New
    'envoy_http_downstream_cx_destroy': 'http.downstream_cx_destroy',
    'envoy_http_downstream_cx_destroy_active_rq': 'http.downstream_cx_destroy_active_rq',
    'envoy_http_downstream_cx_destroy_local': 'http.downstream_cx_destroy_local',
    'envoy_http_downstream_cx_destroy_local_active_rq': 'http.downstream_cx_destroy_local_active_rq',
    'envoy_http_downstream_cx_destroy_remote': 'http.downstream_cx_destroy_remote',
    'envoy_http_downstream_cx_destroy_remote_active_rq': 'http.downstream_cx_destroy_remote_active_rq',
    'envoy_http_downstream_cx_drain_close': 'http.downstream_cx_drain_close',
    'envoy_http_downstream_cx_http1_total': 'http.downstream_cx_http1_total',
    'envoy_http_downstream_cx_http2_total': 'http.downstream_cx_http2_total',
    'envoy_http_downstream_cx_http3_total': 'http.downstream_cx_http3_total',
    'envoy_http_downstream_cx_idle_timeout': 'http.downstream_cx_idle_timeout',
    'envoy_http_downstream_cx_max_duration_reached': 'http.downstream_cx_max_duration_reached', # New
    'envoy_http_downstream_cx_overload_disable_keepalive': 'http.downstream_cx_overload_disable_keepalive', # New
    'envoy_http_downstream_cx_protocol_error': 'http.downstream_cx_protocol_error',
    'envoy_http_downstream_cx_rx_bytes_total': 'http.downstream_cx_rx_bytes_total',
    'envoy_http_downstream_cx_ssl_total': 'http.downstream_cx_ssl_total',
    'envoy_http_downstream_cx_total': 'http.downstream_cx_total',
    'envoy_http_downstream_cx_tx_bytes_total': 'http.downstream_cx_tx_bytes_total',
    'envoy_http_downstream_cx_upgrades_total': 'http.downstream_cx_upgrades_total', # New
    'envoy_http_downstream_flow_control_paused_reading_total': 'http.downstream_flow_control_paused_reading_total',
    'envoy_http_downstream_flow_control_resumed_reading_total': 'http.downstream_flow_control_resumed_reading_total',
    'envoy_http_downstream_rq_completed': 'http.downstream_rq_completed', # New
    'envoy_http_downstream_rq_failed_path_normalization': 'http.downstream_rq_failed_path_normalization', # New
    'envoy_http_downstream_rq_header_timeout': 'http.downstream_rq_header_timeout', # New
    'envoy_http_downstream_rq_http1_total': 'http.downstream_rq_http1_total',
    'envoy_http_downstream_rq_http2_total': 'http.downstream_rq_http2_total',
    'envoy_http_downstream_rq_http3_total': 'http.downstream_rq_http3_total',
    'envoy_http_downstream_rq_idle_timeout': 'http.downstream_rq_idle_timeout', # New
    'envoy_http_downstream_rq_max_duration_reached': 'http.downstream_rq_max_duration_reached', # New
    'envoy_http_downstream_rq_non_relative_path': 'http.downstream_rq_non_relative_path',
    'envoy_http_downstream_rq_overload_close': 'http.downstream_rq_overload_close', # New
    'envoy_http_downstream_rq_redirected_with_normalized_path': 'http.downstream_rq_redirected_with_normalized_path', # New
    'envoy_http_downstream_rq_response_before_rq_complete': 'http.downstream_rq_response_before_rq_complete',
    'envoy_http_downstream_rq_rx_reset': 'http.downstream_rq_rx_reset',
    'envoy_http_downstream_rq_timeout': 'http.downstream_rq_timeout', # New
    'envoy_http_downstream_rq_too_large': 'http.downstream_rq_too_large',
    'envoy_http_downstream_rq_total': 'http.downstream_rq_total',
    'envoy_http_downstream_rq_tx_reset': 'http.downstream_rq_tx_reset',
    'envoy_http_downstream_rq_ws_on_non_ws_route': 'http.downstream_rq_ws_on_non_ws_route',
    'envoy_http_downstream_rq_xx': 'http.downstream_rq_xx', # Looks like tagged by 1,2,3,4 (replacing 1xx,2xx...)
    'envoy_http_no_cluster': 'http.no_cluster',
    'envoy_http_no_route': 'http.no_route',
    'envoy_http_passthrough_internal_redirect_bad_location': 'http.passthrough_internal_redirect_bad_location', # New
    'envoy_http_passthrough_internal_redirect_no_route': 'http.passthrough_internal_redirect_no_route', # New
    'envoy_http_passthrough_internal_redirect_predicate': 'http.passthrough_internal_redirect_predicate', # New
    'envoy_http_passthrough_internal_redirect_too_many_redirects': 'http.passthrough_internal_redirect_too_many_redirects', # New
    'envoy_http_passthrough_internal_redirect_unsafe_scheme': 'http.passthrough_internal_redirect_unsafe_scheme', # New
    'envoy_http_rq_direct_response': 'http.rq_direct_response',
    'envoy_http_rq_redirect': 'http.rq_redirect',
    'envoy_http_rq_reset_after_downstream_response_started': 'http.rq_reset_after_downstream_response_started', # New
    'envoy_http_rq_total': 'http.rq_total',
    'envoy_http_rs_too_large': 'http.rs_too_large',
    'envoy_http_tracing_client_enabled': 'http.tracing.client_enabled',
    'envoy_http_tracing_health_check': 'http.tracing.health_check',
    'envoy_http_tracing_not_traceable': 'http.tracing.not_traceable',
    'envoy_http_tracing_random_sampling': 'http.tracing.random_sampling',
    'envoy_http_tracing_service_forced': 'http.tracing.service_forced',
    'envoy_http1_dropped_headers_with_underscores': 'cluster.http1.dropped_headers_with_underscores',
    'envoy_http1_metadata_not_supported_error': 'cluster.http1.metadata_not_supported_error',
    'envoy_http1_requests_rejected_with_underscores_in_headers': 'cluster.http1.requests_rejected_with_underscores_in_headers',
    'envoy_http1_response_flood': 'cluster.http1.response_flood',
    'envoy_listener_admin_downstream_cx_destroy': 'listener.admin.downstream_cx_destroy', # New
    'envoy_listener_admin_downstream_cx_overflow': 'listener.admin.downstream_cx_overflow', # New
    'envoy_listener_admin_downstream_cx_overload_reject': 'listener.admin.downstream_cx_overload_reject', # New
    'envoy_listener_admin_downstream_cx_total': 'listener.admin.downstream_cx_total', # New
    'envoy_listener_admin_downstream_global_cx_overflow': 'listener.admin.downstream_global_cx_overflow', # New
    'envoy_listener_admin_downstream_pre_cx_timeout': 'listener.admin.downstream_pre_cx_timeout', # New
    'envoy_listener_admin_http_downstream_rq_completed': 'listener.admin.http.downstream_rq_completed', # New
    'envoy_listener_admin_http_downstream_rq_xx': 'listener.admin.http.downstream_rq_xx',  # Looks like tagged by 1,2,3,4 (replacing 1xx,2xx...)
    'envoy_listener_admin_main_thread_downstream_cx_total': 'listener.admin.main_thread.downstream_cx_total', # New, admin/main_thread
    'envoy_listener_admin_no_filter_chain_match': 'listener.admin.no_filter_chain_match', # New
    'envoy_listener_downstream_cx_destroy': 'listener.downstream_cx_destroy',
    'envoy_listener_downstream_cx_overflow': 'listener.downstream_cx_overflow', # New
    'envoy_listener_downstream_cx_overload_reject': 'listener.downstream_cx_overload_reject', # New
    'envoy_listener_downstream_cx_total': 'listener.downstream_cx_total',
    'envoy_listener_downstream_global_cx_overflow': 'listener.downstream_global_cx_overflow', # New
    'envoy_listener_downstream_pre_cx_timeout': 'listener.downstream_pre_cx_timeout',
    'envoy_listener_http_downstream_rq_completed': 'listener.http.downstream_rq_completed',
    'envoy_listener_http_downstream_rq_xx': 'listener.http.downstream_rq_xx',  # Looks like tagged by 1,2,3,4 (replacing 1xx,2xx...)
    'envoy_listener_no_filter_chain_match': 'listener.no_filter_chain_match',
    'envoy_listener_worker_0_downstream_cx_total': 'listener.worker_0_downstream_cx_total', # New, unsure if by nodes. Should we remap these to labels/user_agent?
    'envoy_listener_worker_1_downstream_cx_total': 'listener.worker_1_downstream_cx_total', # New
    'envoy_listener_worker_2_downstream_cx_total': 'listener.worker_2_downstream_cx_total', # New
    'envoy_listener_worker_3_downstream_cx_total': 'listener.worker_3_downstream_cx_total', # New
    'envoy_listener_manager_lds_control_plane_rate_limit_enforced': 'listener_manager.lds.control_plane.rate_limit_enforced',
    'envoy_listener_manager_lds_init_fetch_timeout': 'listener_manager.lds.init_fetch_timeout', # New
    'envoy_listener_manager_lds_update_attempt': 'listener_manager.lds.update_attempt',
    'envoy_listener_manager_lds_update_failure': 'listener_manager.lds.update_failure',
    'envoy_listener_manager_lds_update_rejected': 'listener_manager.lds.update_rejected',
    'envoy_listener_manager_lds_update_success': 'listener_manager.lds.update_success',
    'envoy_listener_manager_listener_added': 'listener_manager.listener_added',
    'envoy_listener_manager_listener_create_failure': 'listener_manager.listener_create_failure',
    'envoy_listener_manager_listener_create_success': 'listener_manager.listener_create_success',
    'envoy_listener_manager_listener_in_place_updated': 'listener_manager.listener_in_place_updated', # New
    'envoy_listener_manager_listener_modified': 'listener_manager.listener_modified',
    'envoy_listener_manager_listener_removed': 'listener_manager.listener_removed',
    'envoy_listener_manager_listener_stopped': 'listener_manager.listener_stopped',
    'envoy_runtime_deprecated_feature_use': 'runtime.deprecated_feature_use',
    'envoy_runtime_load_error': 'runtime.load_error',
    'envoy_runtime_load_success': 'runtime.load_success',
    'envoy_runtime_override_dir_exists': 'runtime.override_dir_exists',
    'envoy_runtime_override_dir_not_exists': 'runtime.override_dir_not_exists',
    'envoy_server_debug_assertion_failures': 'server.debug_assertion_failures',
    'envoy_server_dynamic_unknown_fields': 'server.dynamic_unknown_fields', # New
    'envoy_server_envoy_bug_failures': 'server.envoy_bug_failure', # New
    'envoy_server_static_unknown_fields': 'server.static_unknown_fields', # New
    'envoy_vhost_vcluster_upstream_rq_retry': 'vhost.vcluster.upstream_rq_retry',
    'envoy_vhost_vcluster_upstream_rq_retry_limit_exceeded': 'vhost.vcluster.upstream_rq_retry_limit_exceeded',
    'envoy_vhost_vcluster_upstream_rq_retry_overflow': 'vhost.vcluster.upstream_rq_retry_overflow',
    'envoy_vhost_vcluster_upstream_rq_retry_success': 'vhost.vcluster.upstream_rq_retry_success',
    'envoy_vhost_vcluster_upstream_rq_timeout': 'vhost.vcluster.upstream_rq_timeout',
    'envoy_vhost_vcluster_upstream_rq_total': 'vhost.vcluster.upstream_rq_total',
    'envoy_cluster_http2_pending_send_bytes': 'cluster.http2.pending_send_bytes', # New
    'envoy_cluster_http2_streams_active': 'cluster.http2.streams_active', # New
    'envoy_cluster_lb_subsets_active': 'cluster.lb_subsets_active',
    'envoy_cluster_max_host_weight': 'cluster.max_host_weight',
    'envoy_cluster_membership_degraded': 'cluster.membership_degraded',
    'envoy_cluster_membership_excluded': 'cluster.membership_excluded',
    'envoy_cluster_membership_healthy': 'cluster.membership_healthy',
    'envoy_cluster_membership_total': 'cluster.membership_total',
    'envoy_cluster_version': 'cluster.version',
    'envoy_cluster_upstream_cx_active': 'cluster.upstream_cx_active',
    'envoy_cluster_upstream_cx_rx_bytes_buffered': 'cluster.upstream_cx_rx_bytes_buffered',
    'envoy_cluster_upstream_cx_tx_bytes_buffered': 'cluster.upstream_cx_tx_bytes_total',
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
    'envoy_http_downstream_cx_upgrades_active': 'http.downstream_cx_upgrades_active', # New
    'envoy_http_downstream_rq_active': 'http.downstream_rq_active',
    'envoy_listener_admin_downstream_cx_active': 'listener.admin.downstream_cx_active',  # Admin prefix?
    'envoy_listener_admin_downstream_pre_cx_active': 'listener.admin.downstream_pre_cx_active',
    'envoy_listener_downstream_cx_active': 'listener.downstream_cx_active',
    'envoy_listener_downstream_pre_cx_active': 'listener.downstream_pre_cx_active',
    'envoy_listener_manager_lds_control_plane_connected_state':'listener_manager.lds.control_plane.connected_state',
    'envoy_listener_manager_lds_control_plane_pending_requests': 'listener_manager.lds.control_plane.pending_requests',
    'envoy_listener_manager_lds_update_time': 'listener_manager.lds.update_time',
    'envoy_listener_manager_lds_version': 'listener_manager.lds.version',
    'envoy_listener_manager_total_filter_chains_draining': 'listener_manager.total_filter_chains_draining', # New
    'envoy_listener_manager_total_listeners_active': 'listener_manager.total_listeners_active',
    'envoy_listener_manager_total_listeners_draining': 'listener_manager.total_listeners_draining',
    'envoy_listener_manager_total_listeners_warming': 'listener_manager.total_listeners_warming',
    'envoy_listener_manager_workers_started':  'listener_manager.workers_started', # New
    'envoy_runtime_admin_overrides_active': 'runtime.admin_overrides_active',
    'envoy_runtime_deprecated_feature_seen_since_process_start': 'runtime.deprecated_feature_seen_since_process_start', # New
    'envoy_runtime_num_keys': 'runtime.num_keys',
    'envoy_runtime_num_layers': 'runtime.num_layers',
    'envoy_server_compilation_settings_fips_mode': 'server.compilation_settings_fips_mode', # New
    'envoy_server_concurrency': 'server.concurrency',
    'envoy_server_days_until_first_cert_expiring': 'server.days_until_first_cert_expiring',
    'envoy_server_hot_restart_epoch': 'server.hot_restart_epoch',
    'envoy_server_hot_restart_generation': 'server.hot_restart_generation',
    'envoy_server_live': 'server.live',
    'envoy_server_memory_allocated': 'server.memory_allocated',
    'envoy_server_memory_heap_size': 'server.memory_heap_size',
    'envoy_server_memory_physical_size': 'server.memory_physical_size', # New
    'envoy_server_parent_connections': 'server.parent_connections',
    'envoy_server_seconds_until_first_ocsp_response_expiring': 'server.seconds_until_first_ocsp_response_expiring', # New
    'envoy_server_state': 'server.state',
    'envoy_server_stats_recent_lookups': 'server.stats_recent_lookups',
    'envoy_server_total_connections': 'server.total_connections',
    'envoy_server_uptime': 'server.uptime',
    'envoy_server_version': 'server.version',
    'envoy_wasm_remote_load_cache_entries': 'wasm.remote_load_cache_entries',  # New
    'envoy_wasm_envoy_wasm_runtime_null_active': 'wasm.envoy_wasm.runtime_null_active',  # New
    'envoy_wasm_remote_load_fetch_successes': 'wasm.remote_load_fetch_successes',  # New
    'envoy_wasm_remote_load_fetch_failures': 'wasm.remote_load_fetch_failures',  # New
    'envoy_wasm_remote_load_cache_negative_hits': 'wasm.remote_load_cache_negative_hits',  # New
    'envoy_wasm_remote_load_cache_misses': 'wasm.remote_load_cache_misses',  # New
    'envoy_wasm_remote_load_cache_hits': 'wasm.remote_load_cache_hits',  # New
    'envoy_wasm_envoy_wasm_runtime_null_created': 'wasm.envoy_wasm.runtime_null_created',  # New
    'envoy_metric_cache_count': 'metric_cache_count',  # New
    'envoy_server_dropped_stat_flushes': 'server.dropped_stat_flushes',  # New
    'envoy_cluster_upstream_rq_200': 'cluster.upstream_rq_200',  # New
    'envoy_cluster_http2_stream_refused_errors': 'cluster.http2.stream_refused_errors',  # New
    'envoy_cluster_internal_upstream_rq_200': 'cluster.internal.upstream_rq_200',  # New
    # THE FOLLOWING ARE HISTOGRAMS
    'envoy_cluster_upstream_cx_connect_ms': 'cluster.upstream_cx_connect_ms',
    'envoy_cluster_upstream_cx_length_ms': 'cluster.upstream_cx_length_ms',
    'envoy_cluster_manager_cds_update_duration': 'cluster_manager.cds.update_duration', # New
    'envoy_http_downstream_cx_length_ms': 'listener.downstream_cx_length_ms',
    'envoy_http_downstream_rq_time': 'http.downstream_rq_time',
    'envoy_listener_admin_downstream_cx_length_ms': 'listener.admin.downstream_cx_length_ms', # Admin is new
    'envoy_listener_downstream_cx_length_ms': 'listener.downstream_cx_length_ms',
    'envoy_listener_manager_lds_update_duration': 'listener_manager.lds.update_duration', # New
    'envoy_server_initialization_time_ms': 'server.initialization_time_ms', # New
}

LABEL_MAP = {
    'cluster_name': 'envoy_cluster',
    'envoy_http_conn_manager_prefix': 'stat_prefix', # tracing
    'envoy_listener_address': 'address', # listener
    'envoy_virtual_cluster': 'virtual_envoy_cluster', # vhost
    'envoy_virtual_host': 'virtual_host_name', # vhost
}


class EnvoyCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'envoy'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)


    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': LABEL_MAP,
        }


# Transform to thread_name tag
    # watchdog metrics should have label name extracted `thread_name`?
    # 'envoy_main_thread_watchdog_mega_miss': 'watchdog_mega_miss',  # envoy.watchdog_mega_miss vs envoy.server.watchdog_mega_miss
    # 'envoy_main_thread_watchdog_miss': 'watchdog_miss',
    # 'envoy_server_main_thread_watchdog_mega_miss': 'server.watchdog_mega_miss', # thread_name:main_thread
    # 'envoy_server_main_thread_watchdog_miss': 'server.watchdog_miss', # thread_name:main_thread
    # TYPE envoy_server_worker_0_watchdog_mega_miss counter
    # TYPE envoy_server_worker_0_watchdog_miss counter
    # TYPE envoy_server_worker_1_watchdog_mega_miss counter
    # TYPE envoy_server_worker_1_watchdog_miss counter
    # TYPE envoy_server_worker_2_watchdog_mega_miss counter
    # TYPE envoy_server_worker_2_watchdog_miss counter
    # TYPE envoy_server_worker_3_watchdog_mega_miss counter
    # TYPE envoy_server_worker_3_watchdog_miss counter
    # TYPE envoy_workers_watchdog_mega_miss counter
    # TYPE envoy_workers_watchdog_miss counter
    # 'envoy_listener_admin_main_thread_downstream_cx_active': 'listener.admin.main_thread.downstream_cx_active', # Admin/main-thread
    # What to do with the worker_<num>
    # TYPE envoy_listener_worker_0_downstream_cx_active gauge
    # TYPE envoy_listener_worker_1_downstream_cx_active gauge
    # TYPE envoy_listener_worker_2_downstream_cx_active gauge
    # TYPE envoy_listener_worker_3_downstream_cx_active gauge


# Looks like cluster_name
#     'envoy_cluster_zone_us_central1_c__upstream_rq': 'cluster.'
#     envoy_cluster_zone_us_central1_c__upstream_rq_200
# envoy_cluster_zone_us_central1_c__upstream_rq_completed


    # These should be tagged by `priority`
    # # cluster.circuit_breakers have no default name match or priority label, priority can be default or high?
    # # int result for stats endpoint
    # # TYPE envoy_cluster_circuit_breakers_high_cx_open gauge
    # # TYPE envoy_cluster_circuit_breakers_high_cx_pool_open gauge
    # # TYPE envoy_cluster_circuit_breakers_high_rq_open gauge
    # # TYPE envoy_cluster_circuit_breakers_high_rq_pending_open gauge
    # # TYPE envoy_cluster_circuit_breakers_high_rq_retry_open gauge
    # 'envoy_cluster_circuit_breakers_default_cx_open': 'cluster.circuit_breakers.cx_open',
    # 'envoy_cluster_circuit_breakers_default_cx_pool_open': 'cluster.circuit_breakers.cx_pool_open',
    # 'envoy_cluster_circuit_breakers_default_rq_open':  'cluster.circuit_breakers.rq_open',
    # 'envoy_cluster_circuit_breakers_default_rq_pending_open': 'cluster.circuit_breakers.rq_pending_open',
    # 'envoy_cluster_circuit_breakers_default_rq_retry_open': 'cluster.circuit_breakers.rq_retry_open',