# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck


class CrioCheck(OpenMetricsBaseCheck):
    """
    Collect CRI-O runtime metrics in OpenMetrics format
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(CrioCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                "crio": {
                    'prometheus_url': 'http://localhost:9090/metrics',
                    'namespace': 'crio',
                    'metrics': [
                        {'container_runtime_crio_operations': 'operations.count'},
                        {'container_runtime_crio_operations_latency_microseconds': 'operations.latency'},
                        {'process_cpu_seconds_total': 'cpu.time'},
                        {'process_resident_memory_bytes': 'mem.resident'},
                        {'process_virtual_memory_bytes': 'mem.virtual'},
                    ],
                    'send_histograms_buckets': True,
                }
            },
            default_namespace="crio",
        )
