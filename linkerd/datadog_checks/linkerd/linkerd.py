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
from .metrics import DEFAULT_METRICS, DEFAULT_METRICS_TYPES

class LinkerdCheck(GenericPrometheusCheck):
    """
    Collect linkerd metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):

        default_config = {
            'linkerd': {
                'metrics': [],
                'type_overrides': {},
            }
        }

        metrics_mapper = {}
        type_overrides = {}

        # Linkerd allows you to add a prefix for the metrics ingit the configuration
        prefix = init_config.get("linkerd_prometheus_prefix", '')
        for m in DEFAULT_METRICS:
            metrics_mapper[prefix + m] = DEFAULT_METRICS[m]
        for m in DEFAULT_METRICS_TYPES:
            type_overrides[prefix + m] = DEFAULT_METRICS_TYPES[m]

        default_config['linkerd']['metrics'].append(metrics_mapper)
        default_config['linkerd']['type_overrides'] = type_overrides

        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances, default_config, 'linkerd')

    def check(self, instance):
        GenericPrometheusCheck.check(self, instance)
