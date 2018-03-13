# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    # Agent5 compatibility layer
    from datadog_checks.checks.prometheus import GenericPrometheusCheck
except ImportError:
    from checks.prometheus_check import GenericPrometheusCheck

class LinkerdCheck(GenericPrometheusCheck):
    """
    Collect linkerd metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        labels_mapper = {
            'rt' : 'linkerd_router',
            'client': 'linkerd_client',
            'service': 'linkerd_service',
        }

        default_config = {
            'linkerd': {
                'labels_mapper': labels_mapper,
            }
        }

        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances, default_config, 'linkerd')

    def check(self, instance):
        GenericPrometheusCheck.check(self, instance)
