# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck, is_affirmative

from .metrics import AGENT_METRICS, OPERATOR_METRICS


class CiliumCheck(OpenMetricsBaseCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import CiliumCheckV2

            return CiliumCheckV2(name, init_config, instances)
        else:
            return super(CiliumCheck, cls).__new__(cls)

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
                'metadata_metric_name': 'cilium_version',
                'metadata_label_map': {'version': 'version'},
            }
        )

        super(CiliumCheck, self).__init__(name, init_config, [instance])
