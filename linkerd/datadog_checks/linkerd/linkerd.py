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
        default_config = {
            'linkerd': {
                'metrics': [DEFAULT_METRICS],
                'type_overrides': DEFAULT_METRICS_TYPES,
                'labels_mapper': TAGS_MAPPER,
            }
        }

        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances, default_config, 'linkerd')

    def check(self, instance):
        GenericPrometheusCheck.check(self, instance)
