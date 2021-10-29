# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

import requests

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck
from datadog_checks.base.utils.http import RequestsWrapper

KUBE_METRICS_SERVER_NAMESPACE = "kube_metrics_server"

COUNTERS = {
    'authenticated_user_requests': 'authenticated_user.requests',
    'metrics_server_kubelet_summary_scrapes_total': 'kubelet_summary_scrapes_total',
    'metrics_server_kubelet_request_total': 'kubelet_summary_scrapes_total',
}

HISTOGRAMS = {
    'metrics_server_manager_tick_duration_seconds': 'manager_tick_duration',
    'metrics_server_scraper_duration_seconds': 'scraper_duration',
}

SUMMARIES = {
    'metrics_server_kubelet_summary_request_duration_seconds': 'kubelet_summary_request_duration',
    'metrics_server_kubelet_request_duration_seconds': 'kubelet_summary_request_duration',
}

GAUGES = {
    'metrics_server_scraper_last_time_seconds': 'scraper_last_time',
    'metrics_server_kubelet_last_request_time_seconds': 'scraper_last_time',
    'process_max_fds': 'process.max_fds',
    'process_open_fds': 'process.open_fds',
}

GO_METRICS = {'go_gc_duration_seconds': 'go.gc_duration_seconds', 'go_goroutines': 'go.goroutines'}

IGNORED_METRICS = [
    # Should be reported via API Server Check
    'http_requests_total',
    'http_request_size_bytes',
    'http_response_size_bytes',
    'http_request_duration_microseconds',
    'apiserver_audit_event_total',
    'apiserver_client_certificate_expiration_seconds',
    'apiserver_current_inflight_requests',
    'apiserver_storage_data_key_generation_failures_total',
    'apiserver_storage_data_key_generation_latencies_microseconds',
    'apiserver_storage_envelope_transformation_cache_misses_total',
    # Should be reported via ETCD Check
    'etcd_helper_cache_entry_count',
    'etcd_helper_cache_hit_count',
    'etcd_helper_cache_miss_count',
    'etcd_request_cache_add_latencies_summary',
    'etcd_request_cache_get_latencies_summary',
    # Should be reported via Golang Check
    'go_memstats_alloc_bytes',
    'go_memstats_alloc_bytes_total',
    'go_memstats_buck_hash_sys_bytes',
    'go_memstats_frees_total',
    'go_memstats_gc_sys_bytes',
    'go_memstats_heap_alloc_bytes',
    'go_memstats_heap_idle_bytes',
    'go_memstats_heap_inuse_bytes',
    'go_memstats_heap_objects',
    'go_memstats_heap_released_bytes_total',
    'go_memstats_heap_sys_bytes',
    'go_memstats_last_gc_time_seconds',
    'go_memstats_lookups_total',
    'go_memstats_mallocs_total',
    'go_memstats_mcache_inuse_bytes',
    'go_memstats_mcache_sys_bytes',
    'go_memstats_mspan_inuse_bytes',
    'go_memstats_mspan_sys_bytes',
    'go_memstats_next_gc_bytes',
    'go_memstats_other_sys_bytes',
    'go_memstats_stack_inuse_bytes',
    'go_memstats_stack_sys_bytes',
    'go_memstats_sys_bytes',
    'process_cpu_seconds_total',
    'process_resident_memory_bytes',
    'process_start_time_seconds',
    'process_virtual_memory_bytes',
]


class KubeMetricsServerCheck(OpenMetricsBaseCheck):
    """
    Collect kube-metrics-server metrics from Prometheus
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubeMetricsServerCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                "kube_metrics_server": {
                    'namespace': KUBE_METRICS_SERVER_NAMESPACE,
                    'metrics': [COUNTERS, HISTOGRAMS, SUMMARIES, GAUGES, GO_METRICS],
                    'ignore_metrics': IGNORED_METRICS,
                }
            },
            default_namespace=KUBE_METRICS_SERVER_NAMESPACE,
        )

        if instances is not None:
            for instance in instances:
                url = instance.get('health_url')
                prometheus_url = instance.get('prometheus_url')

                if url is None and re.search(r'/metrics$', prometheus_url):
                    url = re.sub(r'/metrics$', '/livez', prometheus_url)

                instance['health_url'] = url

    def check(self, instance):
        # Get the configuration for this specific instance
        scraper_config = self.get_scraper_config(instance)
        self.process(scraper_config)

        self._perform_service_check(instance)

    def _perform_service_check(self, instance):
        url = instance.get('health_url')
        if url is None:
            return

        tags = instance.get("tags", [])
        service_check_name = KUBE_METRICS_SERVER_NAMESPACE + '.up'
        http_handler = self._healthcheck_http_handler(instance, url)

        try:
            response = http_handler.get(url)
            response.raise_for_status()
            self.service_check(service_check_name, AgentCheck.OK, tags=tags)
        except requests.exceptions.RequestException as e:
            message = str(e)
            self.service_check(service_check_name, AgentCheck.CRITICAL, message=message, tags=tags)

    def _healthcheck_http_handler(self, instance, endpoint):
        if endpoint in self._http_handlers:
            return self._http_handlers[endpoint]

        config = {}
        config['tls_cert'] = instance.get('ssl_cert', None)
        config['tls_private_key'] = instance.get('ssl_private_key', None)
        config['tls_verify'] = instance.get('ssl_verify', True)
        config['tls_ignore_warning'] = instance.get('ssl_ignore_warning', False)
        config['tls_ca_cert'] = instance.get('ssl_ca_cert', None)

        if config['tls_ca_cert'] is None:
            config['tls_ignore_warning'] = True
            config['tls_verify'] = False

        http_handler = self._http_handlers[endpoint] = RequestsWrapper(
            config, self.init_config, self.HTTP_CONFIG_REMAPPER, self.log
        )

        return http_handler
