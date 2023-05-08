# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .metrics import DEFAULT_METRICS, GO_METRICS


class CoreDNSCheck(OpenMetricsBaseCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    METRIC_PREFIX = 'coredns.'

    DEFAULT_METRIC_LIMIT = 0

    """
    Collect CoreDNS metrics from its Prometheus endpoint
    """

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import CoreDNS

            return CoreDNS(name, init_config, instances)
        else:
            return super(CoreDNSCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances=None):

        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(CoreDNSCheck, self).__init__(name, init_config, instances=generic_instances)

    def create_generic_instances(self, instances):
        """
        Transform each CoreDNS instance into a OpenMetricsBaseCheck instance
        """
        generic_instances = []
        for instance in instances:
            transformed_instance = self._create_core_dns_instance(instance)
            generic_instances.append(transformed_instance)

        return generic_instances

    def _create_core_dns_instance(self, instance):
        """
        Set up coredns instance so it can be used in OpenMetricsBaseCheck
        """
        endpoint = instance.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError("Unable to find prometheus endpoint in config file.")

        metrics = [DEFAULT_METRICS, GO_METRICS]
        metrics.extend(instance.get('metrics', []))

        instance.update({'prometheus_url': endpoint, 'namespace': 'coredns', 'metrics': metrics})

        return instance
