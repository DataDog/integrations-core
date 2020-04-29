# (C) Datadog, Inc. 2020-present
# changed
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

from . import utils


class HazelcastCheck(AgentCheck):
    __NAMESPACE__ = 'hazelcast'
    SERVICE_CHECK_CONNECT = 'can_connect'
    SERVICE_CHECK_MC_CLUSTER_STATE = 'mc_cluster_state'

    def __init__(self, name, init_config, instances):
        super(HazelcastCheck, self).__init__(name, init_config, instances)

        self._mc_health_check_endpoint = self.instance.get('mc_health_check_endpoint', '')
        if self._mc_health_check_endpoint and not self._mc_health_check_endpoint.startswith('http'):
            self._mc_health_check_endpoint = 'http://{}'.format(self._mc_health_check_endpoint)

        self._mc_cluster_states = utils.ServiceCheckStatus(
            utils.MC_CLUSTER_STATES, self.instance.get('mc_cluster_states', {})
        )

        self._tags = tuple(self.instance.get('tags', []))

    def check(self, _):
        self.process_mc_health_check()

    def process_mc_health_check(self):
        url = self._mc_health_check_endpoint
        if not url:
            return

        tags = ['endpoint:{}'.format(url)]
        tags.extend(self._tags)

        try:
            response = self.http.get(self._mc_health_check_endpoint)
            response.raise_for_status()
            status = response.json()
        except Exception:
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, tags=tags)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.OK, tags=tags)

        self.service_check(
            self.SERVICE_CHECK_MC_CLUSTER_STATE, self._mc_cluster_states.get(status['managementCenterState']), tags=tags
        )
