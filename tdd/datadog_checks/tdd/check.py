# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck
from datadog_checks.tdd.api_factory import make_api_client


class TddCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'tdd'

    def __init__(self, name, init_config, instances):
        super(TddCheck, self).__init__(name, init_config, instances)
        self._mongo_version = None
        self._api_client, self._error = make_api_client(self, self.instance)

    def check(self, _):
        if self._api_client is None:
            self.log.debug('Api Client is None: %s', self._error)
            self.service_check("can_connect", TddCheck.CRITICAL)
        else:
            service_check = self._api_client.report_service_check()
            if service_check == AgentCheck.OK:
                self._api_client.report_metadata()
                self._api_client.report_metrics()
