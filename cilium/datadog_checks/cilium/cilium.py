# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .metrics import AGENT_METRICS, OPERATOR_METRICS


class CiliumCheck(OpenMetricsBaseCheck):
    """
    Collect Cilium metrics from Prometheus endpoint
    """

    def __init__(self, name, init_config, instances):
        instance = instances[0]

        agent_endpoint = instance.get('agent_endpoint')
        operator_endpoint = instance.get('operator_endpoint')

        # Cannot have both cilium-agent and cilium-operator metrics enabled
        if agent_endpoint and operator_endpoint:
            raise ConfigurationError("Only one endpoint needs to be specified")

        # Must have at least one endpoint enabled
        if not agent_endpoint and not operator_endpoint:
            raise ConfigurationError("Must provide at least one endpoint")

        if operator_endpoint:
            endpoint = operator_endpoint
            metrics = [OPERATOR_METRICS]
        else:
            endpoint = agent_endpoint
            metrics = [AGENT_METRICS]

        metrics.extend(instance.get('metrics', []))

        instance.update(
            {
                'prometheus_url': endpoint,
                'namespace': 'cilium',
                'metrics': metrics,
                'prometheus_timeout': instance.get('timeout', 10),
            }
        )

        super(CiliumCheck, self).__init__(name, init_config, [instance])
