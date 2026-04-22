# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .check import ExternalDNS
from .metrics import DEFAULT_METRICS


class ExternalDNSCheck(OpenMetricsBaseCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            return ExternalDNS(name, init_config, instances)
        else:
            return super(ExternalDNSCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances=None):
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(ExternalDNSCheck, self).__init__(name, init_config, instances=generic_instances)

    def create_generic_instances(self, instances):
        """Transform each ExternalDNS instance into a OpenMetricsBaseCheck instance."""
        generic_instances = []
        for instance in instances:
            transformed_instance = self._create_external_dns_instance(instance)
            generic_instances.append(transformed_instance)

        return generic_instances

    def _create_external_dns_instance(self, instance):
        """Set up external_dns instance so it can be used in OpenMetricsBaseCheck."""
        endpoint = instance.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError("Unable to find prometheus endpoint in config file.")

        metrics = [DEFAULT_METRICS]
        metrics.extend(instance.get('metrics', []))

        # Rename 'host' label to 'http_host' since 'host' is a reserved Datadog tag
        labels_mapper = {'host': 'http_host'}
        labels_mapper.update(instance.get('labels_mapper', {}))

        instance.update(
            {
                'prometheus_url': endpoint,
                'namespace': 'external_dns',
                'metrics': metrics,
                'labels_mapper': labels_mapper,
            }
        )

        return instance
