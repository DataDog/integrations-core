# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.base.errors import ConfigurationError

from .metrics import ADDITIONAL_METRICS_MAP, INSTANCE_DEFAULT_METRICS, MANAGER_METRICS


class ScyllaCheck(OpenMetricsBaseCheck):
    """
    Collect Scylla metrics from Prometheus endpoint
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):

        instance = instances[0]

        instance_endpoint = instance.get('instance_endpoint')
        manager_endpoint = instance.get('manager_endpoint')

        # Cannot have both cilium-instance and cilium-manager metrics enabled
        if instance_endpoint and manager_endpoint:
            raise ConfigurationError("Only one endpoint can be specified per instance")

        # Must have at least one endpoint enabled
        if not instance_endpoint and not manager_endpoint:
            raise ConfigurationError("Must provide at least one endpoint per instance")

        if 'instance_endpoint' in instance:
            endpoint = instance.get('instance_endpoint')
            namespace = 'scylla'

            # extract additional metrics requested and validate the correct names
            metric_groups = instance.get('metric_groups', [])
            additional_metrics = []
            if metric_groups:
                errors = []
                for group in metric_groups:
                    try:
                        additional_metrics.append(ADDITIONAL_METRICS_MAP[group])
                    except KeyError:
                        errors.append(group)

                if errors:
                    raise ConfigurationError(
                        'Invalid metric_groups found in scylla conf.yaml: {}'.format(', '.join(errors))
                    )

            metrics = INSTANCE_DEFAULT_METRICS + additional_metrics

        else:
            endpoint = instance.get('manager_endpoint')
            metrics = [MANAGER_METRICS]
            namespace = 'scylla.manager'

        tags = instance.get('tags', [])
        endpoint_host = endpoint.split(':')[0]
        tags.append('endpoint_host:{}'.format(endpoint_host))

        instance.update(
            {
                'prometheus_url': endpoint,
                'namespace': namespace,
                'metrics': metrics,
                'tags': tags,
            }
        )

        super(ScyllaCheck, self).__init__(name, init_config, instances=[instance])

#    def check(self, instance):
#        """
#        Process all configured endpoints
#        """
#        instance_endpoint = self.instance.get('instance_endpoint')
#        if instance_endpoint:
#            instance_config = self.config_map[instance_endpoint]
#
#            self.process(instance_config)
#
#        manager_endpoint = self.instance.get('manager_endpoint')
#        if manager_endpoint:
#            manager_config = self.config_map[manager_endpoint]
#
#            self.process(manager_config)
