# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import six

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_timestamp

from .api_client_factory import make_api_client
from .common import CAN_CONNECT
from .config_models import ConfigMixin


class ClouderaCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        if six.PY2:
            raise ConfigurationError(
                "This version of the integration is only available when using py3. "
                "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                "for more information."
            )
        super(ClouderaCheck, self).__init__(name, init_config, instances)
        self.client = None
        self.latest_event_query_utc = get_timestamp()
        self.check_initializations.append(self._create_client)

    def _create_client(self):
        try:
            self.client = make_api_client(self, self.config)
        except Exception as e:
            self.log.error("Cloudera API Client is none: %s", e)
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)
            raise

    def check(self, _):
        try:
            self.client.collect_data()
            self.service_check(CAN_CONNECT, AgentCheck.OK)
        except Exception as e:
            self.log.error('Cloudera check raised an exception: %s', e)
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)
