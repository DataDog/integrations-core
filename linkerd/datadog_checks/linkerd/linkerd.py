# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib

# 3rd party

# project
try:
    # Agent5 compatibility layer
    from datadog_checks.checks.prometheus import GenericPrometheusCheck
except ImportError:
    from checks.prometheus_check import GenericPrometheusCheck
from .metrics import DEFAULT_METRICS, DEFAULT_METRICS_TYPES, TAGS_MAPPER

class LinkerdCheck(GenericPrometheusCheck):
    """
    Collect linkerd metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):

        # Linkerd allows you to add a prefix for the metrics ingit the configuration
        prefix = init_config.get("linkerd_prometheus_prefix", '')

        metrics_mapper = self.prefix_metrics(DEFAULT_METRICS, prefix)
        type_overrides = self.prefix_metrics(DEFAULT_METRICS_TYPES, prefix)

        default_config = {
            'linkerd': {
                'metrics': [metrics_mapper],
                'type_overrides': type_overrides,
                'labels_mapper': TAGS_MAPPER,
            }
        }

        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances, default_config, 'linkerd')

    def check(self, instance):
        GenericPrometheusCheck.check(self, instance)

    def prefix_metrics(self, metrics, prefix):
        prefixed_metrics = {}
        for m in metrics:
            prefixed_metrics[prefix + m] = metrics[m]
        return prefixed_metrics
