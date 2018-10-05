# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException


DEFAULT_METRICS = {
    'coredns_dns_response_size_bytes': 'response_size.bytes',
    'coredns_cache_hits_total': 'cache_hits_count',
    'coredns_cache_misses_total': 'cache_misses_count',
    'coredns_dns_request_count_total': 'request_count',
    'coredns_dns_request_duration_seconds': 'request_duration.seconds',
    'coredns_dns_request_size_bytes': 'request_size.bytes',
    'coredns_dns_request_type_count_total': 'request_type_count',
    'coredns_dns_response_rcode_count_total': 'response_code_count',
    'coredns_proxy_request_count_total': 'proxy_request_count',
    'coredns_proxy_request_duration_seconds': 'proxy_request_duration.seconds',
    'coredns_cache_size': 'cache_size.count',
}


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

    def __init__(self, name, init_config, agentConfig, instances=None):

        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(CoreDNSCheck, self).__init__(name, init_config, agentConfig, instances=generic_instances)

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
            raise CheckException("Unable to find prometheus endpoint in config file.")

        metrics = [DEFAULT_METRICS, GO_METRICS]
        metrics.extend(instance.get('metrics', []))

        instance.update({
            'prometheus_url': endpoint,
            'namespace': 'coredns',
            'metrics': metrics,
        })

        return instance
