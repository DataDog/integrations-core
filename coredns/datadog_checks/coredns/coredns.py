# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

# Sorted per plugin, all prometheus metrics prior to version 1.7.0 which introduced a major renaming of metrics.
DEFAULT_METRICS = {
    # acl: https://github.com/coredns/coredns/blob/v1.6.9/plugin/acl/
    'coredns_request_block_count_total': 'acl.blocked_requests',
    'coredns_request_allow_count_total': 'acl.allowed_requests',
    # autopath: https://github.com/coredns/coredns/blob/v1.6.9/plugin/autopath/
    'coredns_autopath_success_count_total': 'autopath.success_count',
    # cache: https://github.com/coredns/coredns/tree/v1.6.9/plugin/cache
    'coredns_cache_size': 'cache_size.count',
    'coredns_cache_hits_total': 'cache_hits_count',
    'coredns_cache_misses_total': 'cache_misses_count',
    'coredns_cache_drops_total': 'cache_drops_count',
    'coredns_cache_prefetch_total': 'cache_prefetch_count',
    'coredns_cache_served_stale_total': 'cache_stale_count',
    # dnssec: https://github.com/coredns/coredns/tree/v1.6.9/plugin/dnssec
    'coredns_dnssec_cache_size': 'dnssec.cache_size',
    'coredns_dnssec_cache_hits_total': 'dnssec.cache_hits',
    'coredns_dnssec_cache_misses_total': 'dnssec.cache_misses',
    # forward: https://github.com/coredns/coredns/tree/v1.6.9/plugin/forward
    'coredns_forward_request_duration_seconds': 'forward_request_duration.seconds',
    'coredns_forward_request_count_total': 'forward_request_count',
    'coredns_forward_response_rcode_count_total': 'forward_response_rcode_count',
    'coredns_forward_healthcheck_failure_count_total': 'forward_healthcheck_failure_count',
    'coredns_forward_healthcheck_broken_count_total': 'forward_healthcheck_broken_count',
    'coredns_forward_sockets_open': 'forward_sockets_open',
    'coredns_forward_max_concurrent_reject_count_total': 'forward_max_concurrent_rejects',
    # grpc: https://github.com/coredns/coredns/tree/v1.6.9/plugin/grpc
    'coredns_grpc_request_duration_seconds': 'grpc.request_duration',
    'coredns_grpc_request_count_total': 'grpc.request_count',
    'coredns_grpc_response_rcode_count_total': 'grpc.response_rcode_count',
    # health: https://github.com/coredns/coredns/tree/v1.6.9/plugin/health
    'coredns_health_request_duration_seconds': 'health_request_duration',
    # hosts: https://github.com/coredns/coredns/tree/v1.6.9/plugin/hosts
    'coredns_hosts_entries_count': 'hosts.entries_count',
    'coredns_hosts_reload_timestamp_seconds': 'hosts.reload_timestamp',
    # kubernetes: https://github.com/coredns/coredns/tree/v1.6.9/plugin/kubernetes
    'coredns_kubernetes_dns_programming_duration_seconds': 'kubernetes.dns_programming_duration',
    # metrics: https://github.com/coredns/coredns/tree/v1.6.9/plugin/metrics
    'coredns_build_info': 'build_info',
    'coredns_panic_count_total': 'panic_count.count',
    'coredns_dns_request_count_total': 'request_count',
    'coredns_dns_request_duration_seconds': 'request_duration.seconds',
    'coredns_dns_request_size_bytes': 'request_size.bytes',
    'coredns_dns_request_do_count_total': 'do_request_count',
    'coredns_dns_request_type_count_total': 'request_type_count',
    'coredns_dns_response_size_bytes': 'response_size.bytes',
    'coredns_dns_response_rcode_count_total': 'response_code_count',
    'coredns_plugin_enabled': 'plugin_enabled',
    # reload: https://github.com/coredns/coredns/tree/v1.6.9/plugin/reload
    'coredns_reload_failed_count_total': 'reload.failed_count',
    # template: https://github.com/coredns/coredns/tree/v1.6.9/plugin/template
    'coredns_template_matches_total': 'template.matches_count',
    'coredns_template_template_failures_total': 'template.failures_count',
    'coredns_template_rr_failures_total': 'template.rr_failures_count',
    # proxy (deprecated): https://github.com/coredns/coredns/tree/v1.4.0/plugin/proxy
    'coredns_proxy_request_count_total': 'proxy_request_count',
    'coredns_proxy_request_duration_seconds': 'proxy_request_duration.seconds',
}

# Sorted per plugin, all prometheus metrics after version 1.7.0 which introduced a major renaming of metrics.
NEW_METRICS = {
    # acl: https://github.com/coredns/coredns/blob/v1.7.0/plugin/acl/README.md
    'coredns_acl_blocked_requests_total': 'acl.blocked_requests',
    'coredns_acl_allowed_requests_total': 'acl.allowed_requests',
    # autopath: https://github.com/coredns/coredns/blob/v1.7.0/plugin/autopath/
    'coredns_autopath_success_total': 'autopath.success_count',
    # cache: https://github.com/coredns/coredns/tree/v1.7.0/plugin/cache
    'coredns_cache_entries': 'cache_size.count',
    # dnssec: https://github.com/coredns/coredns/tree/v1.7.0/plugin/dnssec
    'coredns_dnssec_cache_entries': 'dnssec.cache_size',
    # forward: https://github.com/coredns/coredns/tree/v1.7.0/plugin/forward
    'coredns_forward_requests_total': 'forward_request_count',
    'coredns_forward_responses_total': 'forward_response_rcode_count',
    'coredns_forward_healthcheck_failures_total': 'forward_healthcheck_failure_count',
    'coredns_forward_healthcheck_broken_total': 'forward_healthcheck_broken_count',
    'coredns_forward_max_concurrent_rejects_total': 'forward_max_concurrent_rejects',
    # grpc: https://github.com/coredns/coredns/tree/v1.7.0/plugin/grpc
    'coredns_grpc_requests_total': 'grpc.request_count',
    'coredns_grpc_responses_total': 'grpc.response_rcode_count',
    # hosts: https://github.com/coredns/coredns/tree/v1.7.0/plugin/hosts
    'coredns_hosts_entries': 'hosts.entries_count',
    # metrics: https://github.com/coredns/coredns/tree/v1.7.0/plugin/metrics
    'coredns_panics_total': 'panic_count.count',
    'coredns_dns_requests_total': 'request_count',
    'coredns_dns_do_requests_total': 'do_request_count',
    'coredns_dns_responses_total': 'response_code_count',
    'coredns_plugin_enabled': 'plugin_enabled',
    # reload: https://github.com/coredns/coredns/tree/v1.7.0/plugin/reload
    'coredns_reload_failed_total': 'reload.failed_count',
}

DEFAULT_METRICS.update(NEW_METRICS)

GO_METRICS = {
    'go_gc_duration_seconds': 'go.gc_duration_seconds',
    'go_goroutines': 'go.goroutines',
    'go_info': 'go.info',
    'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
    'go_memstats_alloc_bytes_total': 'go.memstats.alloc_bytes_total',
    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash_sys_bytes',
    'go_memstats_frees_total': 'go.memstats.frees_total',
    'go_memstats_gc_cpu_fraction': 'go.memstats.gc_cpu_fraction',
    'go_memstats_gc_sys_bytes': 'go.memstats.gc_sys_bytes',
    'go_memstats_heap_alloc_bytes': 'go.memstats.heap_alloc_bytes',
    'go_memstats_heap_idle_bytes': 'go.memstats.heap_idle_bytes',
    'go_memstats_heap_inuse_bytes': 'go.memstats.heap_inuse_bytes',
    'go_memstats_heap_objects': 'go.memstats.heap_objects',
    'go_memstats_heap_released_bytes': 'go.memstats.heap_released_bytes',
    'go_memstats_heap_sys_bytes': 'go.memstats.heap_sys_bytes',
    'go_memstats_last_gc_time_seconds': 'go.memstats.last_gc_time_seconds',
    'go_memstats_lookups_total': 'go.memstats.lookups_total',
    'go_memstats_mallocs_total': 'go.memstats.mallocs_total',
    'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache_inuse_bytes',
    'go_memstats_mcache_sys_bytes': 'go.memstats.mcache_sys_bytes',
    'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan_inuse_bytes',
    'go_memstats_mspan_sys_bytes': 'go.memstats.mspan_sys_bytes',
    'go_memstats_next_gc_bytes': 'go.memstats.next_gc_bytes',
    'go_memstats_other_sys_bytes': 'go.memstats.other_sys_bytes',
    'go_memstats_stack_inuse_bytes': 'go.memstats.stack_inuse_bytes',
    'go_memstats_stack_sys_bytes': 'go.memstats.stack_sys_bytes',
    'go_memstats_sys_bytes': 'go.memstats.sys_bytes',
    'process_cpu_seconds_total': 'process.cpu_seconds_total',
    'process_max_fds': 'process.max_fds',
    'process_open_fds': 'process.open_fds',
    'process_resident_memory_bytes': 'process.resident_memory_bytes',
    'process_start_time_seconds': 'process.start_time_seconds',
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
}


class CoreDNSCheck(OpenMetricsBaseCheck):
    """
    Collect CoreDNS metrics from its Prometheus endpoint
    """

    def __init__(self, name, init_config, instances=None):

        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(CoreDNSCheck, self).__init__(name, init_config, instances=generic_instances)

    def create_generic_instances(self, instances):
        """
        Transform each CoreDNS instance into a OpenMetricsBaseCheck instance
        """
        generic_instances = []
        for instance in instances:
            transformed_instance = self._create_core_dns_instance(instance)
            generic_instances.append(transformed_instance)

        return generic_instances

    def _create_core_dns_instance(self, instance):
        """
        Set up coredns instance so it can be used in OpenMetricsBaseCheck
        """
        endpoint = instance.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError("Unable to find prometheus endpoint in config file.")

        metrics = [DEFAULT_METRICS, GO_METRICS]
        metrics.extend(instance.get('metrics', []))

        instance.update({'prometheus_url': endpoint, 'namespace': 'coredns', 'metrics': metrics})

        return instance
