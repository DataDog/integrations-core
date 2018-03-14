# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.prometheus import GenericPrometheusCheck
from datadog_checks.errors import CheckException

from .metrics import METRIC_MAP, TYPE_OVERRIDES

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
                'metrics': [METRIC_MAP],
                'type_overrides': TYPE_OVERRIDES,
            }
        }
        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances, default_config, 'linkerd')

    def check(self, instance):
        instance_name = instance.get('name')
        if instance_name is not None:
            tags = instance.get('tags', [])
            tags.append("linkerd_instance:{}".format(instance_name))
            instance['tags'] = tags

        GenericPrometheusCheck.check(self, instance)
