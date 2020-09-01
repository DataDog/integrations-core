# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck, ConfigurationError, OpenMetricsBaseCheck
from datadog_checks.base.types import InstanceType

from .metrics import EDGE_AGENT_METRICS, EDGE_HUB_METRICS


class AzureIotEdgeCheck(AgentCheck):
    __NAMESPACE__ = 'azure_iot_edge'

    def __init__(self, name, init_config, instances):
        # type: (str, dict, list) -> None
        super(AzureIotEdgeCheck, self).__init__(name, init_config, instances)

        self._edge_hub_instance = self._create_prometheus_instance(namespace='edge_hub', metrics=EDGE_HUB_METRICS)
        self._edge_agent_instance = self._create_prometheus_instance(namespace='edge_agent', metrics=EDGE_AGENT_METRICS)

        self._edge_hub_check = OpenMetricsBaseCheck(name, init_config, [self._edge_hub_instance])
        self._edge_agent_check = OpenMetricsBaseCheck(name, init_config, [self._edge_agent_instance])

    def _create_prometheus_instance(self, namespace, metrics):
        # type: (str, list) -> InstanceType
        config = self.instance.get(namespace)
        if config is None:
            raise ConfigurationError('Key {!r} is required'.format(namespace))

        endpoint = config.get('prometheus_url')
        if endpoint is None:
            raise ConfigurationError('{}: key "prometheus_url" is missing'.format(namespace))

        tags = self.instance.get('tags', [])

        return {
            'prometheus_url': endpoint,
            'namespace': '{}.{}'.format(self.__NAMESPACE__, namespace),
            'metrics': metrics,
            'tags': tags,
        }

    def check(self, _):
        # type: (dict) -> None
        self._edge_hub_check.check(self._edge_hub_instance)
        self._edge_agent_check.check(self._edge_agent_instance)
        self._check_daemon_health()

    def _check_daemon_health(self):
        # type: () -> None
        pass  # TODO
