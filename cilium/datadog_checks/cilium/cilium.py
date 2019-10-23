# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck, ConfigurationError

AGENT_METRICS = {
    'cilium_agent_api_process_time_seconds': 'agent.api_process_time.seconds',
    'cilium_agent_bootstrap_seconds': 'agent.bootstrap.seconds',
    'cilium_bpf_map_ops_total': 'bpf.map_ops.total',
    'cilium_controllers_failing': 'controllers.failing.count',
    'cilium_controllers_runs_duration_seconds': 'controllers.runs_duration.seconds',
    'cilium_controllers_runs_total': 'controllers.runs.total',
    'cilium_datapath_conntrack_gc_duration_seconds': 'datapath.conntrack_gc.duration.seconds',
    'cilium_datapath_conntrack_gc_entries': 'datapath.conntrack_gc.entries',
    'cilium_datapath_conntrack_gc_key_fallbacks_total': 'datapath.conntrack_gc.key_fallbacks.total',
    'cilium_datapath_conntrack_gc_runs_total': 'datapath.conntrack_gc.runs.total',
    'cilium_datapath_errors_total': 'datapath.errors.total',
    'cilium_drop_bytes_total': 'drop_bytes.total',
    'cilium_drop_count_total': 'drop_count.total',
    'cilium_endpoint_count': 'endpoint.count',
    'cilium_endpoint_regeneration_time_stats_seconds': 'endpoint.regeneration_time_stats.seconds',
    'cilium_endpoint_regenerations': 'endpoint.regenerations.count',
    'cilium_endpoint_state': 'endpoint.state',
    'cilium_errors_warnings_total': 'errors_warning.total',
    'cilium_forward_bytes_total': 'forward_bytes.total',
    'cilium_forward_count_total': 'forward_count.total',
    'cilium_fqdn_gc_deletions_total': 'fqdn.gc_deletions.total',
    'cilium_identity_count': 'identity.count',
    'cilium_ip_addresses': 'ip_addresses.count',
    'cilium_ipam_events_total': 'ipam.events.total',
    'cilium_k8s_client_api_calls_counter': 'k8s_client.api_calls.count',
    'cilium_k8s_client_api_latency_time_seconds': 'k8s_client.api_latency_time.seconds',
    'cilium_kubernetes_events_received_total': 'kubernetes.events_received.total',
    'cilium_kubernetes_events_total': 'kubernetes.events.total',
    'cilium_nodes_all_datapath_validations_total': 'nodes.all_datapath_validations.total',
    'cilium_nodes_all_events_received_total': 'nodes.all_events_received.total',
    'cilium_nodes_all_num': 'nodes.managed.total',
    'cilium_policy_count': 'policy.count',
    'cilium_policy_endpoint_enforcement_status': 'policy.endpoint_enforcement_status', # double check
    'cilium_policy_import_errors': 'policy.import_errors.count',
    'cilium_policy_l7_denied_total': 'policy.l7_denied.total',
    'cilium_policy_l7_forwarded_total': 'policy.l7_forwarded.total',
    'cilium_policy_l7_parse_errors_total': 'policy.l7_parse_errors.total',
    'cilium_policy_l7_received_total': 'policy.l7_received.total',
    'cilium_policy_max_revision': 'policy.max_revision',
    'cilium_policy_regeneration_time_stats_seconds': 'policy.regeneration_time_stats.seconds',
    'cilium_policy_regeneration_total': 'policy.regeneration.total',
    'cilium_process_cpu_seconds_total': 'process.cpu.seconds.total',
    'cilium_process_max_fds': 'process.max_fds',
    'cilium_process_open_fds': 'process.open_fds',
    'cilium_process_resident_memory_bytes': 'process.resident_memory.bytes',
    'cilium_process_start_time_seconds': 'process.start_time.seconds',
    'cilium_process_virtual_memory_bytes': 'process.virtual_memory.bytes',
    'cilium_process_virtual_memory_max_bytes': 'process.virtual_memory.max.bytes',
    'cilium_subprocess_start_total': 'subprocess.start.total',
    'cilium_triggers_policy_update_call_duration_seconds': 'triggers_policy.update_call_duration.seconds',
    'cilium_triggers_policy_update_folds': 'triggers_policy.update_folds',
    'cilium_triggers_policy_update_total': 'triggers_policy.update.total',
    'cilium_unreachable_health_endpoints': 'unreachable.health_endpoints',
    'cilium_unreachable_nodes': 'unreachable.nodes',
    # Metrics unsure if needed
    'cilium_event_ts': 'event_timestamp',
}

OPERATOR_METRICS = {
    'cilium_operator_process_cpu_seconds_total': 'operator.process.cpu.seconds',
    'cilium_operator_process_max_fds': 'operator.process.max_fds',
    'cilium_operator_process_open_fds': 'operator.process.open_fds',
    'cilium_operator_process_resident_memory_bytes': 'operator.process.resident_memory.bytes',
    'cilium_operator_process_start_time_seconds': 'operator.process.start_time.seconds',
    'cilium_operator_process_virtual_memory_bytes': 'operator.process.virtual_memory.bytes',
    'cilium_operator_process_virtual_memory_max_bytes': 'operator.process.virtual_memory_max.bytes',
    # TODO: ENI metrics are not listed
}



class CiliumCheck(OpenMetricsBaseCheck):
    """
    Collect Cilium metrics from Prometheus endpoint
    """

    def __init__(self, name, init_config, instances):
        """
        Set up Cilium instance so it can be used in OpenMetricsBaseCheck
        """
        instance = self.instance
        endpoint = None
        metrics = None
        agent_endpoint = instance.get('agent_endpoint')
        operator_endpoint = instance.get('operator_endpoint')

        # Cannot have both cilium-agent and cilium-operator metrics enabled
        if agent_endpoint and operator_endpoint:
            ConfigurationError("Only one endpoint needs to be specified")

        # Must have at least one endpoint enabled
        if not agent_endpoint and not operator_endpoint:
            ConfigurationError("Must provide at least one endpoint")

        if operator_endpoint:
            endpoint = operator_endpoint
            metrics = [OPERATOR_METRICS]
        else:
            if agent_endpoint:
                endpoint = agent_endpoint
                metrics = [AGENT_METRICS]

        metrics.extend(instance.get('metrics', []))

        instance.update({
            'prometheus_url': endpoint,
            'namespace': 'cilium',
            'metrics': metrics,
            'prometheus_timeout': instance.get('timeout', 10)
        })

        super(CiliumCheck, self).__init__(name, init_config, instance)



        
        
        

        

