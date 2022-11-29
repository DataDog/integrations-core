# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError

from .api_client_factory import make_api_client
from .common import CAN_CONNECT
from .config_models import ConfigMixin


class ClouderaCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        if PY2:
            raise ConfigurationError(
                "This version of the integration is only available when using py3. "
                "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                "for more information."
            )

        super(ClouderaCheck, self).__init__(name, init_config, instances)
        self.client = None
        self.check_initializations.append(self._create_client)

    def _create_client(self):
        try:
            client = make_api_client(self, self.config)
        except Exception as e:
            self.log.error(f"Cloudera API Client is none: {e}")
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)
            raise

        self.client = client
        self.custom_tags = self.config.tags  # TODO: Don't need self.custom_tags

    def check(self, _):
        self.client.collect_data()
        self.service_check(CAN_CONNECT, AgentCheck.OK)
