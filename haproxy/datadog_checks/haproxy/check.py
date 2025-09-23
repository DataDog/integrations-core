# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck, is_affirmative

from .checkv2 import HaproxyCheckV2
from .legacy.haproxy import HAProxyCheckLegacy
from .metrics import METRIC_MAP


class HAProxyCheck(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            return HaproxyCheckV2(name, init_config, instances)
        elif is_affirmative(instance.get('use_prometheus', False)):
            return super(HAProxyCheck, cls).__new__(cls)
        else:
            return HAProxyCheckLegacy(name, init_config, instances)

    def __init__(self, name, init_config, instances):
        super(HAProxyCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                'haproxy': {
                    'prometheus_url': 'http://localhost:8404/metrics',
                    'namespace': 'haproxy',
                    'metrics': [METRIC_MAP],
                    'send_histograms_buckets': True,
                    'send_distribution_counts_as_monotonic': True,
                    'send_distribution_sums_as_monotonic': True,
                }
            },
            default_namespace='haproxy',
        )
