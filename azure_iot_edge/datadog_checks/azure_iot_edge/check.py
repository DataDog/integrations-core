# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import cast

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck

from .config import Config
from .types import Instance


class AzureIotEdgeCheck(AgentCheck):
    __NAMESPACE__ = 'azure_iot_edge'

    def __init__(self, name, init_config, instances):
        # type: (str, dict, list) -> None
        super(AzureIotEdgeCheck, self).__init__(name, init_config, instances)
        self._config = Config(cast(Instance, self.instance), check_namespace=self.__NAMESPACE__)
        self._edge_hub_check = OpenMetricsBaseCheck(name, init_config, [self._config.edge_hub_instance])
        self._edge_agent_check = OpenMetricsBaseCheck(name, init_config, [self._config.edge_agent_instance])

    def check(self, _):
        # type: (dict) -> None
        # Sync Agent-assigned check ID so that metrics of these sub-checks are reported as coming from this check.
        self._edge_hub_check.check_id = self.check_id
        self._edge_agent_check.check_id = self.check_id

        self._edge_hub_check.check(self._config.edge_hub_instance)
        self._edge_agent_check.check(self._config.edge_agent_instance)

        self._check_daemon_health()

    def _check_daemon_health(self):
        # type: () -> None
        pass  # TODO
