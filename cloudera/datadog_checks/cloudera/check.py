# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.cloudera.api.factory import make_api

from .common import CAN_CONNECT
from .config_models import ConfigMixin


class ClouderaCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        super(ClouderaCheck, self).__init__(name, init_config, instances)
        self.client = None
        self.latest_event_query_utc = get_timestamp()
        self.check_initializations.append(self._create_client)

    @AgentCheck.metadata_entrypoint
    def _create_client(self):
        self.can_connect_tags = [f'api_url:{self.config.api_url}']
        if self.config.tags is not None:
            for tag in self.config.tags:
                self.can_connect_tags.append(tag)

        try:
            self.client = make_api(self)
        except Exception as e:
            message = f"Cloudera API Client is none: {e}"
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL, message=message, tags=self.can_connect_tags)
            self.log.error(message)
            raise

    def check(self, _):
        try:
            self.client.collect_data()
            self.service_check(CAN_CONNECT, AgentCheck.OK, tags=self.can_connect_tags)
        except Exception as e:
            message = f'Cloudera check raised an exception: {e}'
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL, message=message, tags=self.can_connect_tags)
            self.log.error(message)
