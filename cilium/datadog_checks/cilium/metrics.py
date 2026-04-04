# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

AGENT_V2_OVERRIDE = {
    "cilium_endpoint_regenerations": "endpoint.regenerations",
    "cilium_policy_import_errors": "policy.import_errors",
}

AGENT_METRICS = {
    # Common Metrics
    "cilium_agent_api_process_time_seconds": "agent.api_process_time.seconds",
    "cilium_agent_bootstrap_seconds": "agent.bootstrap.seconds",
    "cilium_bpf_map_ops_total": "bpf.map_ops.total",
    "cilium_controllers_failing": "controllers.failing.count",
    "cilium_controllers_runs_duration_seconds": "controllers.runs_duration.seconds",
    "cilium_controllers_runs_total": "controllers.runs.total",
    "cilium_datapath_conntrack_gc_duration_seconds": "datapath.conntrack_gc.duration.seconds",
    "cilium_datapath_conntrack_gc_entries": "datapath.conntrack_gc.entries",
    "cilium_datapath_conntrack_gc_key_fallbacks_total": "datapath.conntrack_gc.key_fallbacks.total",
    "cilium_datapath_conntrack_gc_runs_total": "datapath.conntrack_gc.runs.total",
    "cilium_drop_bytes_total": "drop_bytes.total",
    "cilium_drop_count_total": "drop_count.total",
    "cilium_endpoint_regeneration_time_stats_seconds": "endpoint.regeneration_time_stats.seconds",
    "cilium_endpoint_regenerations_total": "endpoint.regenerations.total",
    "cilium_endpoint_state": "endpoint.state",
    "cilium_errors_warnings_total": "errors_warning.total",
    "cilium_forward_bytes_total": "forward_bytes.total",
    "cilium_forward_count_total": "forward_count.total",
    "cilium_fqdn_gc_deletions_total": "fqdn.gc_deletions.total",
    "cilium_ip_addresses": "ip_addresses.count",
    "cilium_ipam_events_total": "ipam.events.total",
    "cilium_k8s_client_api_calls_counter": "k8s_client.api_calls.count",
    "cilium_k8s_client_api_latency_time_seconds": "k8s_client.api_latency_time.seconds",
    "cilium_kubernetes_events_received_total": "kubernetes.events_received.total",
    "cilium_kubernetes_events_total": "kubernetes.events.total",
    "cilium_nodes_all_datapath_validations_total": "nodes.all_datapath_validations.total",
    "cilium_nodes_all_events_received_total": "nodes.all_events_received.total",
    "cilium_nodes_all_num": "nodes.managed.total",
    "cilium_policy_endpoint_enforcement_status": "policy.endpoint_enforcement_status",
    "cilium_policy_max_revision": "policy.max_revision",
    "cilium_policy_regeneration_time_stats_seconds": "policy.regeneration_time_stats.seconds",
    "cilium_policy_regeneration_total": "policy.regeneration.total",
    "cilium_process_cpu_seconds_total": "process.cpu.seconds.total",
    "cilium_process_max_fds": "process.max_fds",
    "cilium_process_open_fds": "process.open_fds",
    "cilium_process_resident_memory_bytes": "process.resident_memory.bytes",
    "cilium_process_start_time_seconds": "process.start_time.seconds",
    "cilium_process_virtual_memory_bytes": "process.virtual_memory.bytes",
    "cilium_process_virtual_memory_max_bytes": "process.virtual_memory.max.bytes",
    "cilium_services_events_total": "services.events.total",
    "cilium_subprocess_start_total": "subprocess.start.total",
    "cilium_triggers_policy_update_call_duration_seconds": "triggers_policy.update_call_duration.seconds",
    "cilium_triggers_policy_update_folds": "triggers_policy.update_folds",
    "cilium_triggers_policy_update_total": "triggers_policy.update.total",
    "cilium_unreachable_health_endpoints": "unreachable.health_endpoints",
    "cilium_unreachable_nodes": "unreachable.nodes",
    "cilium_event_ts": "event_timestamp",
    "cilium_kvstore_operations_duration_seconds": "kvstore.operations_duration.seconds",
    "cilium_kvstore_events_queue_seconds": "kvstore.events_queue.seconds",
    "cilium_kvstore_quorum_errors_total": "kvstore.quorum_errors.total",
    "cilium_policy_implementation_delay": "policy.implementation_delay",
    "cilium_proxy_redirects": "proxy.redirects",
    "cilium_proxy_upstream_reply_seconds": "proxy.upstream_reply.seconds",
    "cilium_policy_l7_total": "policy.l7.total",
    # Cilium <= 1.7
    "cilium_policy_l7_denied_total": "policy.l7_denied.total",
    "cilium_policy_l7_forwarded_total": "policy.l7_forwarded.total",
    "cilium_policy_l7_parse_errors_total": "policy.l7_parse_errors.total",
    "cilium_policy_l7_received_total": "policy.l7_received.total",
    # Cilium <= 1.9
    "cilium_datapath_errors_total": "datapath.errors.total",
    "cilium_endpoint_count": "endpoint.count",
    "cilium_identity_count": "identity.count",
    "cilium_policy_count": "policy.count",
    "cilium_policy_import_errors": "policy.import_errors.count",
    # Cilium >= 1.9
    "cilium_api_limiter_adjustment_factor": "api_limiter.adjustment_factor",
    "cilium_api_limiter_processed_requests_total": "api_limiter.processed_requests.total",
    "cilium_api_limiter_processing_duration_seconds": "api_limiter.processing_duration.seconds",
    "cilium_api_limiter_rate_limit": "api_limiter.rate_limit",
    "cilium_api_limiter_requests_in_flight": "api_limiter.requests_in_flight",
    "cilium_api_limiter_wait_duration_seconds": "api_limiter.wait_duration.seconds",
    # Cilium 1.10+
    "cilium_k8s_client_api_calls_total": "k8s_client.api_calls.count",
    "cilium_identity": "identity.count",
    "cilium_policy": "policy.count",
    "cilium_policy_import_errors_total": "policy.import_errors.count",
    "cilium_bpf_map_pressure": "bpf.map_pressure",
    "cilium_bpf_maps_virtual_memory_max_bytes": "bpf.maps.virtual_memory.max.bytes",
    "cilium_bpf_progs_virtual_memory_max_bytes": "bpf.progs.virtual_memory.max.bytes",
    "cilium_datapath_conntrack_dump_resets_total": "datapath.conntrack_dump.resets.total",
    "cilium_ipcache_errors_total": "ipcache.errors.total",
    "cilium_k8s_event_lag_seconds": "k8s_event.lag.seconds",
    "cilium_k8s_terminating_endpoints_events_total": "k8s_terminating.endpoints_events.total",
    "cilium_proxy_datapath_update_timeout_total": "proxy.datapath.update_timeout.total",
    # Cilium 1.12+
    "cilium_fqdn_active_names": "fqdn.active_names",
    "cilium_fqdn_active_ips": "fqdn.active_ips",
    "cilium_fqdn_alive_zombie_connections": "fqdn.alive_zombie_connections",
    # Cilium 1.14+
    "cilium_endpoint": "endpoint.count",
    "cilium_endpoint_max_ifindex": "endpoint.max_ifindex",
    "cilium_cidrgroup_policies": "cidrgroup.policies",
    "cilium_kvstore_sync_queue_size": "kvstore.sync_queue_size",
    "cilium_kvstore_initial_sync_completed": "kvstore.initial_sync_completed",
    "cilium_k8s_client_rate_limiter_duration_seconds": "k8s_client.rate_limiter_duration.seconds",
    "cilium_policy_change_total": "policy.change.total",
    # Cilium 1.15+
    "cilium_bpf_map_capacity": "bpf.map.capacity",
    "cilium_hive_status": "hive.status",
    "cilium_ipam_capacity": "ipam.capacity",
    "cilium_cidrgroups_referenced": "cidrgroups.referenced",
    "cilium_cidrgroup_translation_time_stats_seconds": "cidrgroup.translation.time.stats.seconds",
    "cilium_k8s_workqueue_adds_total": "k8s.workqueue.adds.total",
    "cilium_k8s_workqueue_depth": "k8s.workqueue.depth",
    "cilium_k8s_workqueue_longest_running_processor_seconds": "k8s.workqueue.longest.running.processor.seconds",
    "cilium_k8s_workqueue_queue_duration_seconds": "k8s.workqueue.queue.duration.seconds",
    "cilium_k8s_workqueue_retries_total": "k8s.workqueue.retries.total",
    "cilium_k8s_workqueue_unfinished_work_seconds": "k8s.workqueue.unfinished.work.seconds",
    "cilium_version": "version",
    # Cilium 1.16+
    "cilium_fqdn_selectors": "fqdn.selectors",
    "cilium_identity_label_sources": "identity.label_sources",
    # Cilium 1.17+ - Endpoint
    "cilium_endpoint_propagation_delay_seconds": "endpoint.propagation_delay.seconds",
    # Cilium 1.17+ - Datapath
    "cilium_datapath_conntrack_gc_interval_seconds": "datapath.conntrack_gc.interval.seconds",
    "cilium_datapath_signals_handled_total": "datapath.signals_handled.total",
    # BPF counts
    "cilium_bpf_maps": "bpf.maps.count",
    "cilium_bpf_progs": "bpf.progs.count",
    # Policy selector cache
    "cilium_policy_selector_cache_selectors": "policy.selector_cache.selectors",
    "cilium_policy_selector_cache_identities": "policy.selector_cache.identities",
    "cilium_policy_selector_cache_operation_duration_seconds": "policy.selector_cache.operation_duration.seconds",
    # Active Connection Tracking (ACT) - see ACT_GAUGE_METRICS for the _total gauges
    "cilium_act_processing_time_seconds": "act.processing_time.seconds",
    "cilium_act_errors": "act.errors",
    # BGP Control Plane (conditional on EnableBGPControlPlane)
    "cilium_bgp_control_plane_session_state": "bgp.control_plane.session_state",
    "cilium_bgp_control_plane_advertised_routes": "bgp.control_plane.advertised_routes",
    "cilium_bgp_control_plane_received_routes": "bgp.control_plane.received_routes",
    # Drift checker
    "cilium_drift_checker_config_delta": "drift_checker.config_delta",
    # Envoy XDS (counter with _count in name; V2 appends .count automatically)
    "cilium_xds_events_count": "xds.events",
    # Disabled by default - NAT GC
    "cilium_datapath_nat_gc_entries": "datapath.nat_gc.entries",
    # Disabled by default - FQDN
    "cilium_fqdn_semaphore_rejected_total": "fqdn.semaphore_rejected.total",
    # Disabled by default - Hive
    "cilium_hive_degraded_status": "hive.degraded_status",
    # Disabled by default - Neighbor (counters with _count in name; V2 appends .count)
    "cilium_neighbor_entry_refresh_count": "neighbor.entry_refresh",
    "cilium_neighbor_nexthop_lookup_count": "neighbor.nexthop_lookup",
    "cilium_neighbor_entry_insert_count": "neighbor.entry_insert",
    "cilium_neighbor_entry_delete_count": "neighbor.entry_delete",
    # Disabled by default - StateDB
    "cilium_statedb_write_txn_duration_seconds": "statedb.write_txn_duration.seconds",
    "cilium_statedb_table_contention_seconds": "statedb.table_contention.seconds",
    "cilium_statedb_table_objects": "statedb.table_objects",
    "cilium_statedb_table_revision": "statedb.table_revision",
    "cilium_statedb_table_delete_trackers": "statedb.table_delete_trackers",
    "cilium_statedb_table_graveyard_objects": "statedb.table_graveyard_objects",
    "cilium_statedb_table_graveyard_low_watermark": "statedb.table_graveyard_low_watermark",
    "cilium_statedb_table_graveyard_cleaning_duration_seconds": "statedb.table_graveyard_cleaning_duration.seconds",
    # Disabled by default - Reconciler
    "cilium_reconciler_count": "reconciler.count",
    "cilium_reconciler_duration_seconds": "reconciler.duration.seconds",
    "cilium_reconciler_errors_total": "reconciler.errors.total",
    "cilium_reconciler_errors_current": "reconciler.errors_current",
    "cilium_reconciler_prune_count": "reconciler.prune_count",
    "cilium_reconciler_prune_errors_total": "reconciler.prune_errors.total",
    "cilium_reconciler_prune_duration_seconds": "reconciler.prune_duration.seconds",
    # Feature metrics - Control Plane
    "cilium_feature_controlplane_ipam": "feature.controlplane.ipam",
    "cilium_feature_controlplane_identity_allocation": "feature.controlplane.identity_allocation",
    "cilium_feature_controlplane_cilium_endpoint_slices_enabled": "feature.controlplane.cilium_endpoint_slices_enabled",
    # Feature metrics - Datapath
    "cilium_feature_datapath_network": "feature.datapath.network",
    "cilium_feature_datapath_chaining_enabled": "feature.datapath.chaining_enabled",
    "cilium_feature_datapath_internet_protocol": "feature.datapath.internet_protocol",
    "cilium_feature_datapath_config": "feature.datapath.config",
    "cilium_feature_datapath_endpoint_routes_enabled": "feature.datapath.endpoint_routes_enabled",
    "cilium_feature_datapath_kernel_version": "feature.datapath.kernel_version",
    # Feature metrics - Network Policies (gauges)
    "cilium_feature_network_policies_host_firewall_enabled": "feature.network_policies.host_firewall_enabled",
    "cilium_feature_network_policies_local_redirect_policy_enabled": "feature.network_policies.local_redirect_policy_enabled",  # noqa: E501
    "cilium_feature_network_policies_mutual_auth_enabled": "feature.network_policies.mutual_auth_enabled",
    "cilium_feature_network_policies_non_defaultdeny_policies_enabled": "feature.network_policies.non_defaultdeny_policies_enabled",  # noqa: E501
    "cilium_feature_network_policies_cidr_policies": "feature.network_policies.cidr_policies",
    # Feature metrics - Network Policies (counters)
    "cilium_feature_network_policies_l3_policies_total": "feature.network_policies.l3_policies.total",
    "cilium_feature_network_policies_host_network_policies_total": "feature.network_policies.host_network_policies.total",  # noqa: E501
    "cilium_feature_network_policies_dns_policies_total": "feature.network_policies.dns_policies.total",
    "cilium_feature_network_policies_fqdn_policies_total": "feature.network_policies.fqdn_policies.total",
    "cilium_feature_network_policies_http_policies_total": "feature.network_policies.http_policies.total",
    "cilium_feature_network_policies_http_header_matches_policies_total": "feature.network_policies.http_header_matches_policies.total",  # noqa: E501
    "cilium_feature_network_policies_other_l7_policies_total": "feature.network_policies.other_l7_policies.total",
    "cilium_feature_network_policies_deny_policies_total": "feature.network_policies.deny_policies.total",
    "cilium_feature_network_policies_ingress_cidr_group_policies_total": "feature.network_policies.ingress_cidr_group_policies.total",  # noqa: E501
    "cilium_feature_network_policies_mutual_auth_policies_total": "feature.network_policies.mutual_auth_policies.total",
    "cilium_feature_network_policies_tls_inspection_policies_total": "feature.network_policies.tls_inspection_policies.total",  # noqa: E501
    "cilium_feature_network_policies_sni_allow_list_policies_total": "feature.network_policies.sni_allow_list_policies.total",  # noqa: E501
    "cilium_feature_network_policies_non_defaultdeny_policies_total": "feature.network_policies.non_defaultdeny_policies.total",  # noqa: E501
    "cilium_feature_network_policies_local_redirect_policies_total": "feature.network_policies.local_redirect_policies.total",  # noqa: E501
    "cilium_feature_network_policies_internal_traffic_policy_services_total": "feature.network_policies.internal_traffic_policy_services.total",  # noqa: E501
    "cilium_feature_network_policies_cilium_network_policies_total": "feature.network_policies.cilium_network_policies.total",  # noqa: E501
    "cilium_feature_network_policies_cilium_clusterwide_network_policies_total": "feature.network_policies.cilium_clusterwide_network_policies.total",  # noqa: E501
    "cilium_feature_network_policies_cilium_envoy_config_total": "feature.network_policies.cilium_envoy_config.total",
    "cilium_feature_network_policies_cilium_clusterwide_envoy_config_total": "feature.network_policies.cilium_clusterwide_envoy_config.total",  # noqa: E501
    # Feature metrics - Advanced Connectivity & LB
    "cilium_feature_adv_connect_and_lb_transparent_encryption": "feature.adv_connect_and_lb.transparent_encryption",
    "cilium_feature_adv_connect_and_lb_kube_proxy_replacement_enabled": "feature.adv_connect_and_lb.kube_proxy_replacement_enabled",  # noqa: E501
    "cilium_feature_adv_connect_and_lb_node_port_configuration": "feature.adv_connect_and_lb.node_port_configuration",
    "cilium_feature_adv_connect_and_lb_bgp_enabled": "feature.adv_connect_and_lb.bgp_enabled",
    "cilium_feature_adv_connect_and_lb_egress_gateway_enabled": "feature.adv_connect_and_lb.egress_gateway_enabled",
    "cilium_feature_adv_connect_and_lb_bandwidth_manager_enabled": "feature.adv_connect_and_lb.bandwidth_manager_enabled",  # noqa: E501
    "cilium_feature_adv_connect_and_lb_sctp_enabled": "feature.adv_connect_and_lb.sctp_enabled",
    "cilium_feature_adv_connect_and_lb_vtep_enabled": "feature.adv_connect_and_lb.vtep_enabled",
    "cilium_feature_adv_connect_and_lb_cilium_envoy_config_enabled": "feature.adv_connect_and_lb.cilium_envoy_config_enabled",  # noqa: E501
    "cilium_feature_adv_connect_and_lb_big_tcp_enabled": "feature.adv_connect_and_lb.big_tcp_enabled",
    "cilium_feature_adv_connect_and_lb_l2_lb_enabled": "feature.adv_connect_and_lb.l2_lb_enabled",
    "cilium_feature_adv_connect_and_lb_l2_pod_announcement_enabled": "feature.adv_connect_and_lb.l2_pod_announcement_enabled",  # noqa: E501
    "cilium_feature_adv_connect_and_lb_envoy_proxy_enabled": "feature.adv_connect_and_lb.envoy_proxy_enabled",
    "cilium_feature_adv_connect_and_lb_cilium_node_config_enabled": "feature.adv_connect_and_lb.cilium_node_config_enabled",  # noqa: E501
    "cilium_feature_adv_connect_and_lb_clustermesh_enabled": "feature.adv_connect_and_lb.clustermesh_enabled",
}

OPERATOR_V2_OVERRIDES = {
    "cilium_operator_process_cpu_seconds_total": "operator.process.cpu.seconds.total",
}

OPERATOR_METRICS = {
    # Common metrics
    "cilium_operator_process_cpu_seconds_total": "operator.process.cpu.seconds",
    "cilium_operator_process_max_fds": "operator.process.max_fds",
    "cilium_operator_process_open_fds": "operator.process.open_fds",
    "cilium_operator_process_resident_memory_bytes": "operator.process.resident_memory.bytes",
    "cilium_operator_process_start_time_seconds": "operator.process.start_time.seconds",
    "cilium_operator_process_virtual_memory_bytes": "operator.process.virtual_memory.bytes",
    "cilium_operator_process_virtual_memory_max_bytes": "operator.process.virtual_memory_max.bytes",
    "cilium_operator_eni_deficit_resolver_duration_seconds": "operator.eni.deficit_resolver.duration.seconds",
    "cilium_operator_eni_deficit_resolver_folds": "operator.eni.deficit_resolver.folds",
    "cilium_operator_eni_deficit_resolver_latency_seconds": "operator.eni.deficit_resolver.latency.seconds",
    "cilium_operator_eni_deficit_resolver_queued_total": "operator.eni.deficit_resolver.queued.total",
    # Cilium <= 1.8
    "cilium_operator_eni_available": "operator.eni.available",
    "cilium_operator_eni_available_ips_per_subnet": "operator.eni.available.ips_per_subnet",
    "cilium_operator_eni_aws_api_duration_seconds": "operator.eni.aws_api_duration.seconds",
    # Cilium <= 1.9
    "cilium_operator_eni_ec2_rate_limit_duration_seconds": "operator.eni_ec2.rate_limit.duration.seconds",
    "cilium_operator_eni_ec2_resync_duration_seconds": "operator.eni.ec2_resync.duration.seconds",
    "cilium_operator_eni_ec2_resync_folds": "operator.eni.ec2_resync.folds",
    "cilium_operator_eni_ec2_resync_latency_seconds": "operator.eni.ec2_resync.latency.seconds",
    "cilium_operator_eni_ec2_resync_queued_total": "operator.eni.ec2_resync.queued.total",
    "cilium_operator_eni_interface_creation_ops": "operator.eni.interface_creation_ops",
    "cilium_operator_eni_ips": "operator.eni.ips.total",
    "cilium_operator_eni_k8s_sync_duration_seconds": "operator.eni.k8s_sync.duration.seconds",
    "cilium_operator_eni_k8s_sync_folds": "operator.eni.k8s_sync.folds",
    "cilium_operator_eni_k8s_sync_latency_seconds": "operator.eni.k8s_sync.latency.seconds",
    "cilium_operator_eni_k8s_sync_queued_total": "operator.eni.k8s_sync.queued.total",
    "cilium_operator_eni_nodes": "operator.eni.nodes.total",
    "cilium_operator_eni_resync_total": "operator.eni.resync.total",
    # Cilium 1.8+
    "cilium_operator_ipam_api_duration_seconds": "operator.ipam.api.duration.seconds",
    "cilium_operator_ipam_api_rate_limit_duration_seconds": "operator.ipam.api.rate_limit.duration.seconds",
    "cilium_operator_ipam_available": "operator.ipam.available",
    "cilium_operator_ipam_available_ips_per_subnet": "operator.ipam.available.ips_per_subnet",
    "cilium_operator_ipam_deficit_resolver_duration_seconds": "operator.ipam.deficit_resolver.duration.seconds",
    "cilium_operator_ipam_deficit_resolver_folds": "operator.ipam.deficit_resolver.folds",
    "cilium_operator_ipam_deficit_resolver_latency_seconds": "operator.ipam.deficit_resolver.latency.seconds",
    "cilium_operator_ipam_deficit_resolver_queued_total": "operator.ipam.deficit_resolver.queued.total",
    "cilium_operator_ipam_ips": "operator.ipam.ips",
    "cilium_operator_ipam_allocation_ops": "operator.ipam.allocation_ops",
    "cilium_operator_ipam_release_ops": "operator.ipam.release_ops",
    "cilium_operator_ipam_interface_creation_ops": "operator.ipam.interface_creation_ops",
    "cilium_operator_ipam_resync_total": "operator.ipam.resync.total",
    "cilium_operator_ipam_k8s_sync_duration_seconds": "operator.ipam.k8s_sync.duration.seconds",
    "cilium_operator_ipam_k8s_sync_folds": "operator.ipam.k8s_sync.folds",
    "cilium_operator_ipam_k8s_sync_latency_seconds": "operator.ipam.k8s_sync.latency.seconds",
    "cilium_operator_ipam_k8s_sync_queued_total": "operator.ipam.k8s_sync.queued.total",
    "cilium_operator_ipam_nodes": "operator.ipam.nodes",
    # Cilium 1.9+
    "cilium_operator_azure_api_duration_seconds": "operator.azure.api.duration.seconds",
    "cilium_operator_azure_api_rate_limit_duration_seconds": "operator.azure.api.rate_limit.duration.seconds",
    "cilium_operator_ec2_api_duration_seconds": "operator.ec2.api.duration.seconds",
    "cilium_operator_ec2_api_rate_limit_duration_seconds": "operator.ec2.api.rate_limit.duration.seconds",
    "cilium_operator_ipam_resync_duration_seconds": "operator.ipam.resync.duration.seconds",
    "cilium_operator_ipam_resync_folds": "operator.ipam.resync.folds",
    "cilium_operator_ipam_resync_latency_seconds": "operator.ipam.resync.latency.seconds",
    "cilium_operator_ipam_resync_queued_total": "operator.ipam.resync.queued.total",
    # Cilium 1.11+
    "cilium_operator_identity_gc_entries": "operator.identity_gc.entries",
    "cilium_operator_identity_gc_runs": "operator.identity_gc.runs",
    "cilium_operator_number_of_ceps_per_ces": "operator.num_ceps_per_ces",
    "cilium_operator_ces_queueing_delay_seconds": "operator.ces.queueing_delay.seconds",
    "cilium_operator_ces_sync_errors_total": "operator.ces.sync_errors.total",
    # Cilium 1.13+
    "cilium_operator_ipam_interface_candidates": "operator.ipam.interface_candidates",
    "cilium_operator_ipam_empty_interface_slots": "operator.ipam.empty_interface_slots",
    "cilium_operator_ipam_ip_allocation_ops": "operator.ipam.ip_allocation_ops",
    # Cilium 1.14+
    "cilium_operator_ces_sync_total": "operator.ces.sync.total",
    "cilium_operator_ipam_allocation_duration_seconds": "operator.ipam.allocation.duration.seconds",
    "cilium_operator_ipam_available_interfaces": "operator.ipam.available_interfaces",
    "cilium_operator_ipam_available_ips": "operator.ipam.available_ips",
    "cilium_operator_ipam_ip_release_ops": "operator.ipam.ip_release_ops",
    "cilium_operator_ipam_needed_ips": "operator.ipam.needed_ips",
    "cilium_operator_ipam_release_duration_seconds": "operator.ipam.release.duration.seconds",
    "cilium_operator_ipam_used_ips": "operator.ipam.used_ips",
    # Cilium 1.15+
    "cilium_hive_status": "operator.hive.status",
    "cilium_operator_errors_warnings_total": "operator.errors.warnings.total",
    "cilium_operator_lbipam_ips_available_total": "operator.lbipam.ips.available.total",
    "cilium_operator_lbipam_ips_used_total": "operator.lbipam.ips.used.total",
    "cilium_operator_lbipam_conflicting_pools_total": "operator.lbipam.conflicting.pools.total",
    "cilium_operator_lbipam_services_matching_total": "operator.lbipam.services.matching.total",
    "cilium_operator_lbipam_services_unsatisfied_total": "operator.lbipam.services.unsatisfied.total",
    # Cilium 1.17+ - Identity GC
    "cilium_operator_identity_gc_latency": "operator.identity_gc.latency",
    # Cilium 1.17+ - Endpoint GC
    "cilium_operator_endpoint_gc_objects": "operator.endpoint_gc.objects",
    # Cilium 1.17+ - BGP Control Plane
    "cilium_operator_bgp_control_plane_reconcile_errors_total": "operator.bgp.control_plane.reconcile_errors.total",
    "cilium_operator_bgp_control_plane_reconcile_run_duration_seconds": "operator.bgp.control_plane.reconcile_run_duration.seconds",  # noqa: E501
    # Cilium 1.17+ - LB IPAM event processing
    "cilium_operator_lbipam_event_processing_time_seconds": "operator.lbipam.event_processing_time.seconds",
    # Cilium 1.17+ - IPAM background sync
    "cilium_operator_ipam_background_sync_duration_seconds": "operator.ipam.background_sync_duration.seconds",
    # Operator k8s workqueue (uses cilium_k8s_workqueue_* prefix on the wire, distinct DD names)
    "cilium_k8s_workqueue_adds_total": "operator.k8s.workqueue.adds.total",
    "cilium_k8s_workqueue_depth": "operator.k8s.workqueue.depth",
    "cilium_k8s_workqueue_longest_running_processor_seconds": "operator.k8s.workqueue.longest_running_processor.seconds",  # noqa: E501
    "cilium_k8s_workqueue_queue_duration_seconds": "operator.k8s.workqueue.queue_duration.seconds",
    "cilium_k8s_workqueue_retries_total": "operator.k8s.workqueue.retries.total",
    "cilium_k8s_workqueue_unfinished_work_seconds": "operator.k8s.workqueue.unfinished_work.seconds",
    "cilium_k8s_workqueue_work_duration_seconds": "operator.k8s.workqueue.work_duration.seconds",
    # Cilium 1.17+ - Operator hive jobs
    "cilium_operator_hive_jobs_runs_total": "operator.hive.jobs_runs.total",
    "cilium_operator_hive_jobs_runs_failed": "operator.hive.jobs_runs_failed",
    "cilium_operator_hive_jobs_oneshot_last_run_duration_seconds": "operator.hive.jobs.oneshot.last_run_duration.seconds",  # noqa: E501
    "cilium_operator_hive_jobs_observer_last_run_duration_seconds": "operator.hive.jobs.observer.last_run_duration.seconds",  # noqa: E501
    "cilium_operator_hive_jobs_observer_run_duration_seconds": "operator.hive.jobs.observer.run_duration.seconds",
    "cilium_operator_hive_jobs_timer_last_run_duration_seconds": "operator.hive.jobs.timer.last_run_duration.seconds",
    "cilium_operator_hive_jobs_timer_run_duration_seconds": "operator.hive.jobs.timer.run_duration.seconds",
    # Operator feature metrics (use cilium_operator_ namespace at runtime)
    "cilium_operator_feature_adv_connect_and_lb_gateway_api_enabled": "operator.feature.adv_connect_and_lb.gateway_api_enabled",  # noqa: E501
    "cilium_operator_feature_adv_connect_and_lb_ingress_controller_enabled": "operator.feature.adv_connect_and_lb.ingress_controller_enabled",  # noqa: E501
    "cilium_operator_feature_adv_connect_and_lb_lb_ipam_enabled": "operator.feature.adv_connect_and_lb.lb_ipam_enabled",
    "cilium_operator_feature_adv_connect_and_lb_l7_aware_traffic_management_enabled": "operator.feature.adv_connect_and_lb.l7_aware_traffic_management_enabled",  # noqa: E501
    "cilium_operator_feature_adv_connect_and_lb_node_ipam_enabled": "operator.feature.adv_connect_and_lb.node_ipam_enabled",  # noqa: E501
    "cilium_operator_feature_controlplane_kubernetes_version": "operator.feature.controlplane.kubernetes_version",
}

AGENT_V2_METRICS = deepcopy(AGENT_METRICS)
AGENT_V2_METRICS.update(AGENT_V2_OVERRIDE)

OPERATOR_V2_METRICS = deepcopy(OPERATOR_METRICS)
OPERATOR_V2_METRICS.update(OPERATOR_V2_OVERRIDES)

# Gauges whose Prometheus name ends with _total. These bypass construct_metrics_config
# because that function strips _total (designed for counters), which would break matching
# for gauges where _total is part of the registered metric name.
ACT_GAUGE_METRICS = [
    {"cilium_act_new_connections_total": {"name": "act.new_connections"}},
    {"cilium_act_active_connections_total": {"name": "act.active_connections"}},
    {"cilium_act_failed_connections_total": {"name": "act.failed_connections"}},
]


def construct_metrics_config(metric_map):
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        if raw_metric_name.endswith("_total"):
            raw_metric_name = raw_metric_name[:-6]
            metric_name = metric_name[:-6]
        elif raw_metric_name.endswith("_counter"):
            raw_metric_name = raw_metric_name[:-8]
            metric_name = metric_name[:-8]

        config = {raw_metric_name: {"name": metric_name}}
        metrics.append(config)

    return metrics
