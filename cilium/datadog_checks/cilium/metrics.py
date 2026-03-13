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
    "cilium_ipcache_events_total": "ipcache.events.total",
    "cilium_k8s_event_lag_seconds": "k8s_event.lag.seconds",
    "cilium_k8s_terminating_endpoints_events_total": "k8s_terminating.endpoints_events.total",
    "cilium_proxy_datapath_update_timeout_total": "proxy.datapath.update_timeout.total",
    # Cilium 1.12+
    "cilium_fqdn_active_names": "fqdn.active_names",
    "cilium_fqdn_active_ips": "fqdn.active_ips",
    "cilium_fqdn_alive_zombie_connections": "fqdn.alive_zombie_connections",
    # Cilium 1.14+
    "cilium_endpoint": "endpoint.count",
    "cilium_cidrgroup_policies": "cidrgroup.policies",
    "cilium_kvstore_sync_queue_size": "kvstore.sync_queue_size",
    "cilium_kvstore_initial_sync_completed": "kvstore.initial_sync_completed",
    "cilium_kvstore_sync_errors_total": "kvstore.sync_errors.total",
    "cilium_k8s_client_rate_limiter_duration_seconds": "k8s_client.rate_limiter_duration.seconds",
    "cilium_policy_change_total": "policy.change.total",
    # Cilium 1.15+
    "cilium_bpf_map_capacity": "bpf.map.capacity",
    "cilium_hive_status": "hive.status",
    "cilium_ipam_capacity": "ipam.capacity",
    "cilium_cidrgroups_referenced": "cidrgroups.referenced",
    "cilium_k8s_workqueue_adds_total": "k8s.workqueue.adds.total",
    "cilium_k8s_workqueue_depth": "k8s.workqueue.depth",
    "cilium_k8s_workqueue_longest_running_processor_seconds": "k8s.workqueue.longest.running.processor.seconds",
    "cilium_k8s_workqueue_queue_duration_seconds": "k8s.workqueue.queue.duration.seconds",
    "cilium_k8s_workqueue_retries_total": "k8s.workqueue.retries.total",
    "cilium_k8s_workqueue_unfinished_work_seconds": "k8s.workqueue.unfinished.work.seconds",
    "cilium_k8s_workqueue_work_duration_seconds": "k8s.workqueue.work_duration.seconds",
    # cilium_version is intentionally excluded from the metrics mapper so that
    # the metadata transformer fires and sets version.major/minor/patch via set_metadata.
    # Cilium 1.16+
    "cilium_fqdn_selectors": "fqdn.selectors",
    "cilium_identity_label_sources": "identity.label_sources",
    # Cilium 1.14-1.18, removed in 1.19
    "cilium_endpoint_max_ifindex": "endpoint.max_ifindex",
    # Cilium 1.15-1.16, removed in 1.17
    "cilium_cidrgroup_translation_time_stats_seconds": "cidrgroup.translation.time.stats.seconds",
    # Cilium <= 1.16, removed in 1.17
    "cilium_triggers_policy_update_call_duration_seconds": "triggers_policy.update_call_duration.seconds",
    "cilium_triggers_policy_update_folds": "triggers_policy.update_folds",
    "cilium_triggers_policy_update_total": "triggers_policy.update.total",
    # ClusterMesh agent metrics
    "cilium_clustermesh_remote_cluster_services": "clustermesh.remote_cluster_services",
    "cilium_clustermesh_remote_cluster_nodes": "clustermesh.remote_cluster_nodes",
    "cilium_clustermesh_remote_clusters": "clustermesh.remote_clusters",
    "cilium_clustermesh_remote_cluster_failures": "clustermesh.remote_cluster_failures",
    "cilium_clustermesh_remote_cluster_last_failure_ts": "clustermesh.remote_cluster_last_failure_ts",
    "cilium_clustermesh_remote_cluster_readiness_status": "clustermesh.remote_cluster_readiness_status",
    "cilium_clustermesh_remote_cluster_cache_revocations": "clustermesh.remote_cluster_cache_revocations",
    # IPsec
    "cilium_ipsec_xfrm_error": "ipsec.xfrm_error",
    "cilium_ipsec_keys": "ipsec.keys",
    "cilium_ipsec_xfrm_states": "ipsec.xfrm_states",
    "cilium_ipsec_xfrm_policies": "ipsec.xfrm_policies",
    # eBPF additions
    "cilium_bpf_syscall_duration_seconds": "bpf.syscall_duration.seconds",
    "cilium_bpf_ratelimit_dropped_total": "bpf.ratelimit_dropped.total",
    # Drop/Forward additions
    "cilium_mtu_error_message_total": "mtu_error_message.total",
    "cilium_fragmented_count_total": "fragmented_count.total",
    # Services
    "cilium_service_implementation_delay": "service.implementation_delay",
    # API limiter
    "cilium_api_limiter_wait_history_duration_seconds": "api_limiter.wait_history_duration.seconds",
    # Policy
    "cilium_policy_incremental_update_duration": "policy.incremental_update_duration",
    # Identity
    "cilium_identity_gc_entries": "identity.gc_entries",
    "cilium_identity_gc_runs": "identity.gc_runs",
    "cilium_identity_gc_latency": "identity.gc_latency",
    # Kubernetes
    "cilium_k8s_cnp_status_completion_seconds": "k8s.cnp_status_completion.seconds",
    # Controllers
    "cilium_controllers_group_runs_total": "controllers.group_runs.total",
    # Endpoint
    "cilium_endpoint_restoration_endpoints": "endpoint.restoration_endpoints",
    "cilium_endpoint_restoration_duration_seconds": "endpoint.restoration_duration.seconds",
    # NAT
    "cilium_nat_endpoint_max_connection": "nat.endpoint_max_connection",
    # Hive Jobs (Cilium 1.17+)
    "cilium_hive_jobs_runs_total": "hive.jobs_runs.total",
    "cilium_hive_jobs_runs_failed": "hive.jobs_runs_failed",
    "cilium_hive_jobs_oneshot_last_run_duration_seconds": "hive.jobs.oneshot.last_run_duration.seconds",
    "cilium_hive_jobs_observer_last_run_duration_seconds": "hive.jobs.observer.last_run_duration.seconds",
    "cilium_hive_jobs_observer_run_duration_seconds": "hive.jobs.observer.run_duration.seconds",
    "cilium_hive_jobs_timer_last_run_duration_seconds": "hive.jobs.timer.last_run_duration.seconds",
    "cilium_hive_jobs_timer_run_duration_seconds": "hive.jobs.timer.run_duration.seconds",
    # Cilium 1.17+
    "cilium_node_health_connectivity_status": "node_health.connectivity.status",
    "cilium_node_health_connectivity_latency_seconds": "node_health.connectivity.latency.seconds",
    "cilium_policy_selector_match_count_max": "policy.selector_match_count_max",
    "cilium_identity_cache_timer_duration": "identity.cache_timer.duration",
    "cilium_identity_cache_timer_trigger_latency": "identity.cache_timer_trigger.latency",
    "cilium_identity_cache_timer_trigger_folds": "identity.cache_timer_trigger.folds",
    # Cilium 1.19+
    "cilium_clustermesh_remote_cluster_endpoints": "clustermesh.remote_cluster_endpoints",
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
    # Note: lbipam metrics had _total suffix in 1.15-1.16; the _total is stripped by construct_metrics_config
    # so the same entries match both old (counter) and new (gauge, renamed without _total in 1.17+) metric names.
    "cilium_hive_status": "operator.hive.status",
    "cilium_operator_errors_warnings_total": "operator.errors.warnings.total",
    "cilium_operator_lbipam_ips_available_total": "operator.lbipam.ips.available.total",
    "cilium_operator_lbipam_ips_used_total": "operator.lbipam.ips.used.total",
    "cilium_operator_lbipam_conflicting_pools_total": "operator.lbipam.conflicting.pools.total",
    "cilium_operator_lbipam_services_matching_total": "operator.lbipam.services.matching.total",
    "cilium_operator_lbipam_services_unsatisfied_total": "operator.lbipam.services.unsatisfied.total",
    # Missing from earlier integrations
    "cilium_operator_controllers_group_runs_total": "operator.controllers.group_runs.total",
    "cilium_operator_number_of_cep_changes_per_ces": "operator.num_cep_changes_per_ces",
    # ClusterMesh operator
    "cilium_operator_clustermesh_remote_clusters": "operator.clustermesh.remote_clusters",
    "cilium_operator_clustermesh_remote_cluster_failures": "operator.clustermesh.remote_cluster_failures",
    "cilium_operator_clustermesh_remote_cluster_last_failure_ts": "operator.clustermesh.remote_cluster_last_failure_ts",
    "cilium_operator_clustermesh_remote_cluster_readiness_status": "operator.clustermesh.remote_cluster_readiness_status",  # noqa: E501
    "cilium_operator_clustermesh_remote_cluster_cache_revocations": "operator.clustermesh.remote_cluster_cache_revocations",  # noqa: E501
    "cilium_operator_clustermesh_remote_cluster_services": "operator.clustermesh.remote_cluster_services",
    "cilium_operator_clustermesh_remote_cluster_service_exports": "operator.clustermesh.remote_cluster_service_exports",
    # MCS-API
    "cilium_operator_mcsapi_serviceexport_info": "operator.mcsapi.serviceexport_info",
    "cilium_operator_mcsapi_serviceexport_status_condition": "operator.mcsapi.serviceexport_status_condition",
    "cilium_operator_mcsapi_serviceimport_info": "operator.mcsapi.serviceimport_info",
    "cilium_operator_mcsapi_serviceimport_status_condition": "operator.mcsapi.serviceimport_status_condition",
    "cilium_operator_mcsapi_serviceimport_status_clusters": "operator.mcsapi.serviceimport_status_clusters",
    # CID controller
    "cilium_operator_cid_controller_work_queue_event_count": "operator.cid_controller.work_queue_event_count",
    "cilium_operator_cid_controller_work_queue_latency": "operator.cid_controller.work_queue_latency",
    # Cilium 1.17+
    "cilium_operator_unmanaged_pods": "operator.unmanaged_pods",
    "cilium_operator_doublewrite_crd_identities": "operator.doublewrite.crd_identities",
    "cilium_operator_doublewrite_kvstore_identities": "operator.doublewrite.kvstore_identities",
    "cilium_operator_doublewrite_crd_only_identities": "operator.doublewrite.crd_only_identities",
    "cilium_operator_doublewrite_kvstore_only_identities": "operator.doublewrite.kvstore_only_identities",
    # Cilium 1.19+ (operator workqueue metrics with cilium_operator_ prefix, replacing bare workqueue_* names)
    "cilium_operator_k8s_workqueue_depth": "operator.k8s.workqueue.depth",
    "cilium_operator_k8s_workqueue_adds_total": "operator.k8s.workqueue.adds.total",
    "cilium_operator_k8s_workqueue_queue_duration_seconds": "operator.k8s.workqueue.queue_duration.seconds",
    "cilium_operator_k8s_workqueue_work_duration_seconds": "operator.k8s.workqueue.work_duration.seconds",
    "cilium_operator_k8s_workqueue_unfinished_work_seconds": "operator.k8s.workqueue.unfinished_work.seconds",
    "cilium_operator_k8s_workqueue_longest_running_processor_seconds": "operator.k8s.workqueue.longest_running_processor.seconds",  # noqa: E501
    "cilium_operator_k8s_workqueue_retries_total": "operator.k8s.workqueue.retries.total",
}

AGENT_V2_METRICS = deepcopy(AGENT_METRICS)
AGENT_V2_METRICS.update(AGENT_V2_OVERRIDE)

OPERATOR_V2_METRICS = deepcopy(OPERATOR_METRICS)
OPERATOR_V2_METRICS.update(OPERATOR_V2_OVERRIDES)


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
