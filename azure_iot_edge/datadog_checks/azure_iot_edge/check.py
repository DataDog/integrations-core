# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import cast

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck

from .config import Config
from .types import Instance


class AzureIoTEdgeCheck(AgentCheck):
    __NAMESPACE__ = 'azure.iot_edge'  # Child of `azure.` namespace.

    def __init__(self, name, init_config, instances):
        # type: (str, dict, list) -> None
        super(AzureIoTEdgeCheck, self).__init__(name, init_config, instances)
        self._config = Config(cast(Instance, self.instance), check_namespace=self.__NAMESPACE__)
        self._edge_hub_check = OpenMetricsBaseCheck(name, init_config, [self._config.edge_hub_instance])
        self._edge_agent_check = OpenMetricsBaseCheck(name, init_config, [self._config.edge_agent_instance])

    def check(self, _):
        # type: (dict) -> None
        self._check_daemon_health()

        # Sync Agent-assigned check ID so that metrics of these sub-checks are reported as coming from this check.
        self._edge_hub_check.check_id = self.check_id
        self._edge_agent_check.check_id = self.check_id

        self._edge_hub_check.check(self._config.edge_hub_instance)
        self._edge_agent_check.check(self._config.edge_agent_instance)

    def _check_daemon_health(self):
        # type: () -> None
        try:
            _ = self.http.get(self._config.security_daemon_management_api_url)
        except Exception as exc:
            status = self.CRITICAL
            message = str(exc)
        else:
            # The endpoint is responding, which means the management API server is running and accessible to the Agent,
            # so it's fair to assume that the security daemon is running and in good shape.
            status = self.OK
            message = ''

        self.service_check('security_daemon.can_connect', status, message=message, tags=self._config.tags)
