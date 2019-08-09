# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

DEFAULT_METRICS = {
    'external_dns_registry_endpoints_total': 'registry.endpoints.total',
    'external_dns_source_endpoints_total': 'source.endpoints.total',
    'source_errors_total': 'source.errors.total',
    'registry_errors_total': 'registry.errors.total',
}


class ExternalDNSCheck(OpenMetricsBaseCheck):
    """
    Collect ExternalDNS metrics from its Prometheus endpoint
    """

    def __init__(self, name, init_config, agentConfig, instances=None):
        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(ExternalDNSCheck, self).__init__(name, init_config, agentConfig, instances=generic_instances)

    def create_generic_instances(self, instances):
        """
        Transform each ExternalDNS instance into a OpenMetricsBaseCheck instance
        """
        generic_instances = []
        for instance in instances:
            transformed_instance = self._create_external_dns_instance(instance)
            generic_instances.append(transformed_instance)

        return generic_instances

    def _create_external_dns_instance(self, instance):
        """
        Set up externaldns instance so it can be used in OpenMetricsBaseCheck
        """
        endpoint = instance.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError("Unable to find prometheus url in config file.")

        metrics = [DEFAULT_METRICS]
        metrics.extend(instance.get('metrics', []))

        instance.update({'prometheus_url': endpoint, 'namespace': 'external_dns', 'metrics': metrics})

        return instance
