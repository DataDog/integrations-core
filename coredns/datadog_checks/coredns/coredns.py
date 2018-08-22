# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.prometheus import PrometheusCheck
from datadog_checks.errors import CheckException


class CoreDNSCheck(PrometheusCheck):
    """
    Collect CoreDNS metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(CoreDNSCheck, self).__init__(name, init_config, agentConfig, instances)
        self.NAMESPACE = 'coredns'

        self.metrics_mapper = {
            # Primarily, metrics are emitted by the prometheus plugin: https://coredns.io/plugins/metrics/
            # Note: the count metrics were moved to specific functions
            # below to be submitted as both gauges and monotonic_counts
            'coredns_dns_request_duration_seconds': 'request_duration.seconds',
            'coredns_dns_request_size_bytes': 'request_size.bytes',
            # https://coredns.io/plugins/proxy/
            'coredns_proxy_request_duration_seconds': 'proxy_request_duration.seconds',
            # https://coredns.io/plugins/cache/
            'coredns_cache_size': 'cache_size.count',
        }
        self.ignore_metrics = {
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

    def check(self, instance):
        endpoint = instance.get('prometheus_endpoint')
        if endpoint is None:
            raise CheckException("Unable to find prometheus_endpoint in config file.")

        send_buckets = instance.get('send_histograms_buckets', True)
        # By default we send the buckets.
        if send_buckets is not None and str(send_buckets).lower() == 'false':
            send_buckets = False
        else:
            send_buckets = True

        self.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)

    def submit_as_gauge_and_monotonic_count(self, metric_suffix, message, **kwargs):
        """
        submit a coredns metric both as a gauge (for compatibility) and as a monotonic_count
        """
        metric_name = self.NAMESPACE + metric_suffix
        for metric in message.metric:
            _tags = []
            for label in metric.label:
                _tags.append('{}:{}'.format(label.name, label.value))
            # submit raw metric
            self.gauge(metric_name, metric.counter.value, _tags)
            # submit rate metric
            self.monotonic_count(metric_name + '.count', metric.counter.value, _tags)

    def coredns_dns_response_rcode_count_total(self, message, **kwargs):
        self.submit_as_gauge_and_monotonic_count('.response_code_count', message, **kwargs)

    def coredns_proxy_request_count_total(self, message, **kwargs):
        self.submit_as_gauge_and_monotonic_count('.proxy_request_count', message, **kwargs)

    def coredns_cache_hits_total(self, message, **kwargs):
        self.submit_as_gauge_and_monotonic_count('.cache_hits_count', message, **kwargs)

    def coredns_cache_misses_total(self, message, **kwargs):
        self.submit_as_gauge_and_monotonic_count('.cache_misses_count', message, **kwargs)

    def coredns_dns_request_count_total(self, message, **kwargs):
        self.submit_as_gauge_and_monotonic_count('.request_count', message, **kwargs)

    def coredns_dns_request_type_count_total(self, message, **kwargs):
        self.submit_as_gauge_and_monotonic_count('.request_type_count', message, **kwargs)
