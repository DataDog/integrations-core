# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.utils.http import RequestsWrapper

METRICS = {
    'process_cpu_seconds_total': 'cpu.time',
    'process_resident_memory_bytes': 'mem.resident',
    'process_virtual_memory_bytes': 'mem.virtual',
    # Alpha metrics
    'kubeproxy_sync_proxy_rules_duration_seconds': 'sync_proxy.rules.duration',
    'kubeproxy_sync_proxy_rules_endpoint_changes_pending': 'sync_proxy.rules.endpoint_changes.pending',
    'kubeproxy_sync_proxy_rules_endpoint_changes_total': 'sync_proxy.rules.endpoint_changes.total',
    'kubeproxy_sync_proxy_rules_iptables_restore_failures_total': 'sync_proxy.rules.iptables.restore_failures',
    'kubeproxy_sync_proxy_rules_iptables_total': 'sync_proxy.rules.iptables',
    'kubeproxy_sync_proxy_rules_last_queued_timestamp_seconds': 'sync_proxy.rules.last_queued_timestamp',
    'kubeproxy_sync_proxy_rules_last_timestamp_seconds': 'sync_proxy.rules.last_timestamp',
    'kubeproxy_sync_proxy_rules_service_changes_pending': 'sync_proxy.rules.service_changes.pending',
    'kubeproxy_sync_proxy_rules_service_changes_total': 'sync_proxy.rules.service_changes.total',
    'rest_client_exec_plugin_certificate_rotation_age': 'rest.client.exec_plugin.certificate.rotation',
    'rest_client_exec_plugin_ttl_seconds': 'rest.client.exec_plugin.ttl',
    'rest_client_request_duration_seconds': 'rest.client.request.duration',
    'rest_client_requests_total': 'rest.client.requests',
    # Deprecated in 1.14
    'kubeproxy_sync_proxy_rules_latency_microseconds': 'sync_proxy.rules.latency',
}


class KubeProxyCheck(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        if instances is not None:
            for instance in instances:
                url = instance.get('health_url')
                prometheus_url = instance.get('prometheus_url')

                # healthz url uses port 10256 by default
                # https://kubernetes.io/docs/reference/command-line-tools-reference/kube-proxy/
                if url is None and re.search(r':[0-9]+/metrics$', prometheus_url):
                    url = re.sub(r':[0-9]+/metrics$', ':10256/healthz', prometheus_url)

                instance['health_url'] = url

        super(KubeProxyCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                "kubeproxy": {
                    'prometheus_url': 'http://localhost:10249/metrics',
                    'namespace': 'kubeproxy',
                    'metrics': [
                        METRICS,
                    ],
                    'send_histograms_buckets': True,
                }
            },
            default_namespace="kubeproxy",
        )

    def check(self, instance):
        scraper_config = self.get_scraper_config(instance)
        self.process(scraper_config)

        self._perform_service_check(instance)

    def _perform_service_check(self, instance):
        url = instance.get('health_url')
        if url is None:
            return

        tags = instance.get("tags", [])
        service_check_name = 'kubeproxy.up'
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
