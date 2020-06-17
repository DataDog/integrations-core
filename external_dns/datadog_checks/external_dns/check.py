# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck

from .metrics import DEFAULT_METRICS


class ExternalDNSCheck(OpenMetricsBaseCheck):
    """
    Collect ExternalDNS metrics from its Prometheus endpoint
    """

    def __init__(self, name, init_config, instances):
        super(ExternalDNSCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                'external_dns': {
                    'prometheus_url': 'http://localhost:7979/metrics',
                    'namespace': 'external_dns',
                    'metrics': [DEFAULT_METRICS],
                    'send_histograms_buckets': True,
                }
            },
            default_namespace='external_dns',
        )
