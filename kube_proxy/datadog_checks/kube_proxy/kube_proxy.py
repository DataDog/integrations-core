# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck

class KubeProxyCheck(OpenMetricsBaseCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(KubeProxyCheck, self).__init__(
            name,
            init_config,
            agentConfig,
            instances,
            default_instances={
                "kubeproxy": {
                    'prometheus_url': 'http://localhost:10249/metrics',
                    'namespace': 'kubeproxy',
                    'metrics': [
                        {'kubeproxy_sync_proxy_rules_latency_microseconds': 'sync_rules.latency'},
                        {'process_cpu_seconds_total': 'cpu.time'},
                        {'process_resident_memory_bytes': 'mem.resident'},
                        {'process_virtual_memory_bytes': 'mem.virtual'},
                        {'rest_client_requests_total': 'client.http.requests'}
                    ],
                    'send_histograms_buckets': True
                }
            },
            default_namespace="kubeproxy"
        )
