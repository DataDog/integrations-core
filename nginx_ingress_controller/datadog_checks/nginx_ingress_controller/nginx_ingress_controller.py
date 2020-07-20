# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import is_affirmative
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck

DEFAULT_METRICS = [
    # nginx metrics
    {'nginx_ingress_controller_nginx_process_connections': 'nginx.connections.current'},
    {'nginx_ingress_controller_nginx_process_connections_total': 'nginx.connections.total'},
    {'nginx_ingress_controller_nginx_process_requests_total': 'nginx.requests.total'},
    # nginx process metrics
    {'nginx_ingress_controller_nginx_process_num_procs': 'nginx.process.count'},
    {'nginx_ingress_controller_nginx_process_read_bytes_total': 'nginx.bytes.read'},
    {'nginx_ingress_controller_nginx_process_write_bytes_total': 'nginx.bytes.write'},
    {'nginx_ingress_controller_nginx_process_cpu_seconds_total': 'nginx.cpu.time'},
    {'nginx_ingress_controller_nginx_process_resident_memory_bytes': 'nginx.mem.resident'},
    {'nginx_ingress_controller_nginx_process_virtual_memory_bytes': 'nginx.mem.virtual'},
    # controller metrics
    {'nginx_ingress_controller_success': 'controller.reload.success'},
    {'nginx_ingress_controller_ingress_upstream_latency_seconds': 'controller.upstream.latency'},
    {'nginx_ingress_controller_requests': 'controller.requests'},
    {'process_cpu_seconds_total': 'controller.cpu.time'},
    {'process_resident_memory_bytes': 'controller.mem.resident'},
    {'process_virtual_memory_bytes': 'controller.mem.virtual'},
]

HISTOGRAM_METRICS = [
    {'nginx_ingress_controller_response_duration_seconds': 'controller.response.duration'},
    {'nginx_ingress_controller_request_duration_seconds': 'controller.request.duration'},
]


class NginxIngressControllerCheck(OpenMetricsBaseCheck):
    """
    Collect Nginx Ingress Controller metrics in OpenMetrics format
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        instance = instances[0]

        # Allow for additional metric mappings
        metrics = instance.get('metrics', []) + DEFAULT_METRICS

        if is_affirmative(instance.get('collect_nginx_histograms', False)):
            metrics += HISTOGRAM_METRICS

        super(NginxIngressControllerCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                "nginx_ingress": {
                    'prometheus_url': 'http://localhost:10254/metrics',
                    'namespace': 'nginx_ingress',
                    'metrics': metrics,
                }
            },
            default_namespace="nginx_ingress",
        )
