# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import cast

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck

from .config import Config
from .types import Instance


class AzureIoTEdgeCheck(AgentCheck):
    __NAMESPACE__ = 'azure.iot_edge'  # Child of `azure.` namespace.

    def __init__(self, name, init_config, instances):
        super(AzureIoTEdgeCheck, self).__init__(name, init_config, instances)
        self._config = Config(cast(Instance, self.instance), check_namespace=self.__NAMESPACE__)
        self._edge_hub_check = OpenMetricsBaseCheck(name, init_config, [self._config.edge_hub_instance])
        self._edge_agent_check = OpenMetricsBaseCheck(name, init_config, [self._config.edge_agent_instance])

        # Need a custom metric transformer due to version info being located in a JSON-encoded string.
        edge_agent_metric_transformers = {'edgeAgent_metadata': self._transform_version_metadata}
        scraper_config = self._edge_agent_check.get_scraper_config(self._config.edge_agent_instance)
        scraper_config['_default_metric_transformers'].update(edge_agent_metric_transformers)

    def _transform_version_metadata(self, metric, scraper_config):
        """
        Submit version metadata from an Edge Agent metadata metric instance.

        Metadata metric look like this:

        ```
        edgeAgent_metadata{...,edge_agent_version="...",host_information="{\"...\", \"Version\": \"1.0.10~rc2\"}"}
        ```

        See: https://github.com/Azure/iotedge/blob/1.0.10-rc2/doc/BuiltInMetrics.md#edgeagent

        NOTE: we want the Security Manager version, not the Edge Agent version.
        """
        labels = metric.samples[0][OpenMetricsBaseCheck.SAMPLE_LABELS]  # type: dict

        host_information = labels.get('host_information')
        if host_information is None:
            self.log.debug('Label "host_information" not found, skipping version metadata')
            return

        try:
            host_info = json.loads(host_information)  # type: dict
        except json.JSONDecodeError as exc:
            self.log.debug('Error decoding host information: %r', exc)
            return

        iot_edge_runtime_version = host_info.get('Version')
        if iot_edge_runtime_version is None:
            self.log.debug('Key "Version" not found in host_information, skipping version metadata')
            return

        self.set_metadata('version', iot_edge_runtime_version)

    def check(self, _):
        self._check_security_manager_health()

        # NOTE: This check consumes configuration from a single instance, and then delegates the Edge Agent and Edge Hub
        # Prometheus endpoints checks to to two OpenMetrics checks, using a composition approach.
        # Compared to requiring separate instances for monitor the Edge Agent, Edge Hub, and the Security Manager,
        # we keep the "1 instance = 1 IoT Edge device" mental model, which provides better configuration UX for users
        # (as having to configure 3 separate instances is more error-prone).
        # The composition approach also hopefully makes the code more natural and easier to understand, compared
        # to subclassing from OpenMetricsBaseCheck and having to dig into its internals such as `.process()` and
        # scraper configurations.

        # Sync Agent-assigned check ID so that metrics of these sub-checks are reported as coming from this check.
        self._edge_hub_check.check_id = self.check_id
        self._edge_agent_check.check_id = self.check_id

        self._edge_hub_check.check(self._config.edge_hub_instance)
        self._edge_agent_check.check(self._config.edge_agent_instance)

    def _check_security_manager_health(self):
        try:
            _ = self.http.get(self._config.security_manager_management_api_url)
        except Exception as exc:
            status = self.CRITICAL
            message = str(exc)
        else:
            # The endpoint is responding, which means the management API server is running and accessible to the Agent,
            # so it's fair to assume that the security manager is running and in good shape.
            status = self.OK
            message = ''

        self.service_check('security_manager.can_connect', status, message=message, tags=self._config.tags)
