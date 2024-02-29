# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import PY2

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.base.errors import ConfigurationError

from .metrics import METRICS_MAP


class DatadogClusterAgentCheck(OpenMetricsBaseCheck):
    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if instance.get('openmetrics_endpoint'):
            if PY2:
                raise ConfigurationError(
                    'This version of the integration is only available when using Python 3. '
                    'Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3/ '
                    'for more information or use the older style config.'
                )
            # TODO: when we drop Python 2 move this import up top
            from .check_v2 import DatadogClusterAgentCheckV2

            return DatadogClusterAgentCheckV2(name, init_config, instances)

        return super(DatadogClusterAgentCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(DatadogClusterAgentCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                'datadog.cluster_agent': {
                    'prometheus_url': 'http://localhost:5000/metrics',
                    'namespace': 'datadog.cluster_agent',
                    'metrics': [METRICS_MAP],
                    'label_joins': {
                        'leader_election_is_leader': {
                            'labels_to_match': ['*'],
                            'labels_to_get': ['is_leader'],
                        }
                    },
                    'send_histograms_buckets': True,
                    'send_distribution_counts_as_monotonic': True,
                    'send_distribution_sums_as_monotonic': True,
                }
            },
            default_namespace='datadog.cluster_agent',
        )
