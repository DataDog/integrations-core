# (C) Datadog, Inc. 2020-present
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
            response_wrapper = self.http.get(self._mc_health_check_endpoint)
            response_wrapper.raise_for_status()
            response = response_wrapper.json()
        except Exception:
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, tags=tags)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.OK, tags=tags)

        status = None
        # Hazelcast 4 and 5 have different responses to this healthcheck endpoint
        if "status" in response:
            # hazelcast 5:
            # I cannot find documentation on this endpoint for management center 5.3 but it
            # does not represent "cluster status" because that is documented and available at a
            # different route:
            # https://docs.hazelcast.com/management-center/5.3/integrate/cluster-metrics#operation/getAllClustersStatus
            # It is probably the same as in 4.0 and just represents whether the management center
            # is available.
            status = response["status"]
        elif "managementCenterState" in response:
            # hazelcast 4:
            # https://docs.hazelcast.org/docs/management-center/4.0.1/manual/html/index.html#enabling-health-check-endpoint
            # "This endpoint responds with 200 OK HTTP status code once the Management Center web
            # application has started"
            status = response["managementCenterState"]

        self.service_check(self.SERVICE_CHECK_MC_CLUSTER_STATE, self._mc_cluster_states.get(status), tags=tags)
