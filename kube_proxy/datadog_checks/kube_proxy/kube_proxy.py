# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck

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
